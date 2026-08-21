"""Incremental synchronization of todos.

The Todo entity has no ``timeUpdated`` and the API has no "changed after"
filter, so "what changed" cannot be asked for directly. TodoSync answers it by
keeping a cursor over ids for new todos and a fingerprint per known todo for
changed ones. State is serializable and owned by the caller — the SDK stores
nothing itself.

The primary channel for todo changes on a live account is the "events"
webhook stream. TodoSync exists for the initial load and as a safety net for
missed webhooks, not as a replacement for them.

Honest limitation: a todo that changes while it sits outside the current
window (see ``_in_window``), and whose change is not otherwise caught by a
webhook, will not be detected until the window is widened enough to see it
again — ``TodoSync`` does not (and, without a "changed after" filter, cannot)
scan the whole account on every poll.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from megaplan_sdk.models.todo import Todo, TodoWhen
from megaplan_sdk.resources.todos import TodosResource

# Fields that count as a meaningful change. This is a fixed, public contract,
# not `Todo`'s full field set: hashing the whole payload would turn any new
# server-side field into a fake "updated" for every todo the moment the SDK
# starts seeing it, since the server adds fields over time.
FINGERPRINT_FIELDS = (
    "name",
    "status",
    "when",
    "responsible",
    "is_dropped",
    "time_finished",
    "description",
)


def _fingerprint(todo: Todo) -> str:
    """Hash of the fields in :data:`FINGERPRINT_FIELDS`.

    A fixed field list is used deliberately: hashing the whole payload would
    turn any new server-side field into a fake "updated" for every todo.
    """
    dump = todo.model_dump(mode="json")
    payload = {name: dump.get(name) for name in FINGERPRINT_FIELDS}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _when_reference_date(when: TodoWhen) -> date | None:
    """The one calendar date used to test a todo against the sync window.

    Prefers the start bound, falls back to the end bound, and returns None
    when neither bound resolves to a usable date — malformed or missing data
    degrades to "unknown", the same way `TodoWhen` itself does.
    """
    if when.is_all_day:
        bound = when.start_date or when.end_date
        return bound.date if bound else None

    at = when.start_datetime or when.end_datetime
    if at is None:
        return None
    try:
        return datetime.fromisoformat(at.value).date()
    except ValueError:
        return None


def _in_window(todo: Todo, today: date, window_days: int) -> bool:
    """Whether a todo counts as part of the current sync window.

    An unfinished todo is always in scope: it is still actionable no matter
    when it is scheduled, so there is no window to apply. A finished/dropped
    todo only counts when its `when` resolves to a date within `window_days`
    of `today`; one with no resolvable `when` drops out of scope entirely.
    """
    if not todo.is_finished():
        return True
    if todo.when is None:
        return False
    reference = _when_reference_date(todo.when)
    if reference is None:
        return False
    return abs((reference - today).days) <= window_days


@dataclass
class TodoSyncState:
    """Serializable sync state. Persisting it across polls is the caller's job.

    Attributes:
        cursor_id: Highest todo id observed by any poll so far.
        fingerprints: `_fingerprint()` result per todo id, for todos seen in
            the most recent poll's window. Ids that fall out of the window
            are dropped from here (see `TodoSync.poll`), so this dict does
            not grow without bound on an active account.
    """

    cursor_id: int | None = None
    fingerprints: dict[int, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Plain-JSON form of the state, safe to pass to `json.dumps`."""
        return {
            "cursor_id": self.cursor_id,
            "fingerprints": {str(todo_id): fp for todo_id, fp in self.fingerprints.items()},
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TodoSyncState:
        """Restore state produced by :meth:`to_dict`."""
        return cls(
            cursor_id=payload.get("cursor_id"),
            fingerprints={int(k): v for k, v in payload.get("fingerprints", {}).items()},
        )


@dataclass
class TodoChanges:
    """What changed since the previous poll."""

    created: list[Todo]
    updated: list[Todo]
    deleted: list[int]
    state: TodoSyncState


class TodoSync:
    """Incremental sync over todos, compensating for the missing `timeUpdated`.

    See the module docstring for why this exists and what it cannot detect.
    """

    def __init__(self, todos: TodosResource, window_days: int = 30) -> None:
        """Initialize the sync helper.

        Args:
            todos: Resource used to fetch todos. A resource, not a client, is
                accepted here to keep this decoupled from client wiring.
            window_days: How many days on either side of today count as
                in-scope for a finished/dropped todo (see `_in_window`).
                Unfinished todos are always in scope regardless of this
                value.
        """
        self._todos = todos
        self._window_days = window_days

    async def poll(self, state: TodoSyncState | None = None) -> TodoChanges:
        """Fetch todos and diff them against `state`.

        There is no server-side filter that can be trusted to return only
        changed or in-window todos — an unrecognized filter field is
        silently ignored, and the server answers with the unfiltered list
        instead of an error — so every todo the account exposes is paged
        through, and the window is applied client-side to the result.

        Args:
            state: State from a previous poll, or None for the first poll —
                in which case every in-window todo is reported as created.

        Returns:
            Created/updated/deleted todos, plus the state to pass into the
            next `poll()` call.
        """
        state = state or TodoSyncState()
        today = datetime.now(UTC).date()

        seen: dict[int, Todo] = {}
        async for todo in self._todos.iterate():
            if _in_window(todo, today, self._window_days):
                seen[todo.id] = todo

        created: list[Todo] = []
        updated: list[Todo] = []
        fingerprints: dict[int, str] = {}
        for todo_id, todo in seen.items():
            fingerprint = _fingerprint(todo)
            fingerprints[todo_id] = fingerprint
            previous = state.fingerprints.get(todo_id)
            if previous is None:
                created.append(todo)
            elif previous != fingerprint:
                updated.append(todo)

        deleted = [todo_id for todo_id in state.fingerprints if todo_id not in seen]

        cursor_candidates = list(seen)
        if state.cursor_id is not None:
            cursor_candidates.append(state.cursor_id)
        cursor_id = max(cursor_candidates) if cursor_candidates else None

        new_state = TodoSyncState(cursor_id=cursor_id, fingerprints=fingerprints)
        return TodoChanges(created=created, updated=updated, deleted=deleted, state=new_state)
