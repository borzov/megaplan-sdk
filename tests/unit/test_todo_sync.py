"""Tests for TodoSync — incremental sync over todos without ``timeUpdated``.

TODO below mirrors the fixture in test_todos_resource.py: an unfinished todo
(``masterType: scheduled``) with no ``when``. Being unfinished, it is always
in scope for TodoSync regardless of window_days — that is what lets these
tests avoid juggling dates for the common cases, and window-dependent tests
below build their own ``when`` payloads for the current day explicitly.
"""

import json
from datetime import date

from megaplan_sdk.models.todo import Todo
from megaplan_sdk.sync.todos import TodoSync, TodoSyncState, _fingerprint

TODO = {
    "contentType": "Todo",
    "id": "501",
    "name": "Созвон",
    "status": {"contentType": "TodoStatus", "id": "1", "masterType": "scheduled"},
    "timeCreated": {"contentType": "DateTime", "value": "2026-08-20T09:00:00+00:00"},
}

# A second, independent todo — used wherever a test needs a non-empty server
# response while one specific todo disappears or changes, so the scenario
# under test is not confused with "the server returned nothing at all"
# (see TodoChanges.looks_truncated).
TODO_2 = {
    "contentType": "Todo",
    "id": "502",
    "name": "Второй",
    "status": {"contentType": "TodoStatus", "id": "1", "masterType": "scheduled"},
    "timeCreated": {"contentType": "DateTime", "value": "2026-08-20T09:00:00+00:00"},
}


def _when_today() -> dict:
    """A ``when`` payload (all-day) anchored on today, safely inside any window."""
    today = date.today()
    bound = {"contentType": "DateOnly", "year": today.year, "month": today.month, "day": today.day}
    return {"contentType": "IntervalDates", "from": bound, "to": bound}


def _when_time_today() -> dict:
    """A timed (non-all-day) `when` payload anchored on today."""
    at = {"contentType": "DateTime", "value": f"{date.today().isoformat()}T10:00:00+00:00"}
    return {"contentType": "IntervalTime", "from": at, "to": at}


def _when_time_unparseable() -> dict:
    """A timed `when` payload whose bound value is not valid ISO 8601."""
    at = {"contentType": "DateTime", "value": "not-a-date"}
    return {"contentType": "IntervalTime", "from": at, "to": at}


FINISHED_STATUS = {"contentType": "TodoStatus", "id": "2", "masterType": "finished"}


async def test_first_poll_reports_everything_as_created(megaplan_api, todos):
    megaplan_api.get("todo", data=[TODO])

    changes = await TodoSync(todos).poll()

    assert [t.id for t in changes.created] == [501]
    assert changes.updated == [] and changes.deleted == []


async def test_unchanged_todo_is_not_reported_again(megaplan_api, todos):
    megaplan_api.get("todo", data=[TODO])
    sync = TodoSync(todos)

    first = await sync.poll()
    second = await sync.poll(first.state)

    assert second.created == [] and second.updated == []


async def test_changed_field_produces_update(megaplan_api, todos):
    megaplan_api.get("todo", data=[TODO])
    sync = TodoSync(todos)
    first = await sync.poll()

    megaplan_api.get("todo", data=[{**TODO, "name": "Созвон перенесён"}])
    second = await sync.poll(first.state)

    assert [t.name for t in second.updated] == ["Созвон перенесён"]


async def test_disappeared_todo_is_reported_deleted(megaplan_api, todos):
    """A todo missing from an otherwise non-empty response is a real
    deletion — unlike the whole response going empty, see
    test_empty_response_with_nonempty_snapshot_does_not_delete_everything.
    """
    megaplan_api.get("todo", data=[TODO, TODO_2])
    sync = TodoSync(todos)
    first = await sync.poll()

    megaplan_api.get("todo", data=[TODO_2])
    second = await sync.poll(first.state)

    assert second.deleted == [501]
    assert second.looks_truncated is False


async def test_empty_response_with_nonempty_snapshot_does_not_delete_everything(
    megaplan_api, todos
):
    """A fully empty response after a non-empty snapshot reads as a suspect
    response (permission hiccup, empty page, pagination cut short), not a
    mass deletion: nothing is reported deleted, and state is handed back
    untouched so the caller can safely retry without losing its snapshot.
    """
    megaplan_api.get("todo", data=[TODO])
    sync = TodoSync(todos)
    first = await sync.poll()

    megaplan_api.get("todo", data=[])
    second = await sync.poll(first.state)

    assert second.deleted == []
    assert second.created == [] and second.updated == []
    assert second.looks_truncated is True
    assert second.state == first.state


def test_state_survives_serialization():
    """Round-trip through real json.dumps/json.loads, not just the dict form —
    this is exactly how a caller persists the state between polls.
    """
    state = TodoSyncState(cursor_id=501, fingerprints={501: "abc"})

    restored = TodoSyncState.from_dict(json.loads(json.dumps(state.to_dict())))

    assert restored.cursor_id == 501
    assert restored.fingerprints == {501: "abc"}


def test_new_server_field_does_not_fake_an_update():
    """Fingerprint covers a fixed field list, not the whole payload."""
    a = _fingerprint(Todo(**TODO))
    b = _fingerprint(Todo(**{**TODO, "someNewServerField": 42}))

    assert a == b


async def test_finishing_a_todo_produces_an_update_not_a_deletion(megaplan_api, todos):
    """A todo that changed from unfinished to finished is an update, as long as
    its `when` still falls inside the window — the server didn't drop it, its
    status changed, and TodoSync must not conflate the two.
    """
    megaplan_api.get("todo", data=[TODO])
    sync = TodoSync(todos)
    first = await sync.poll()

    finished = {**TODO, "status": FINISHED_STATUS, "when": _when_today()}
    megaplan_api.get("todo", data=[finished])
    second = await sync.poll(first.state)

    assert [t.id for t in second.updated] == [501]
    assert second.deleted == []


async def test_todo_leaving_window_is_dropped_from_state_not_reported_deleted(megaplan_api, todos):
    """A todo the server still returns, but which fell out of the window, must
    be dropped from the next snapshot (so it does not grow without bound)
    WITHOUT being reported in `deleted` — `deleted` is reserved for ids the
    server stops returning at all, and this one is still right there in the
    response.
    """
    megaplan_api.get("todo", data=[TODO])
    sync = TodoSync(todos)
    first = await sync.poll()
    assert first.state.fingerprints == {501: _fingerprint(Todo(**TODO))}

    # Finished, and with no `when` at all — falls out of the window entirely,
    # even though the server still has (and returns) the record.
    finished_no_when = {**TODO, "status": FINISHED_STATUS}
    megaplan_api.get("todo", data=[finished_no_when])
    second = await sync.poll(first.state)

    assert second.state.fingerprints == {}
    assert second.deleted == []
    assert second.created == [] and second.updated == []
    assert second.looks_truncated is False


async def test_finished_todo_with_timed_when_in_window_is_updated(megaplan_api, todos):
    """A timed (IntervalTime) `when`, not just an all-day one, is honored by the window."""
    megaplan_api.get("todo", data=[TODO])
    sync = TodoSync(todos)
    first = await sync.poll()

    finished = {**TODO, "status": FINISHED_STATUS, "when": _when_time_today()}
    megaplan_api.get("todo", data=[finished])
    second = await sync.poll(first.state)

    assert [t.id for t in second.updated] == [501]


async def test_finished_todo_with_unparseable_when_falls_out_of_window(megaplan_api, todos):
    """A `when` bound that cannot be parsed as a date degrades to "unknown",
    same as `TodoWhen` itself does, and drops the todo out of the window —
    but the server still returned it, so it is not `deleted`.
    """
    megaplan_api.get("todo", data=[TODO])
    sync = TodoSync(todos)
    first = await sync.poll()

    finished = {**TODO, "status": FINISHED_STATUS, "when": _when_time_unparseable()}
    megaplan_api.get("todo", data=[finished])
    second = await sync.poll(first.state)

    assert second.updated == [] and second.created == []
    assert second.deleted == []
    assert 501 not in second.state.fingerprints


async def test_finished_todo_with_empty_when_bounds_falls_out_of_window(megaplan_api, todos):
    """A timed `when` with no `from`/`to` at all resolves to no reference
    date, so the todo falls out of the window — again, not `deleted`.
    """
    megaplan_api.get("todo", data=[TODO])
    sync = TodoSync(todos)
    first = await sync.poll()

    finished = {**TODO, "status": FINISHED_STATUS, "when": {"contentType": "IntervalTime"}}
    megaplan_api.get("todo", data=[finished])
    second = await sync.poll(first.state)

    assert second.deleted == []
    assert 501 not in second.state.fingerprints


async def test_cursor_id_tracks_highest_seen_id_and_survives_empty_polls(megaplan_api, todos):
    megaplan_api.get("todo", data=[TODO])
    sync = TodoSync(todos)
    first = await sync.poll()
    assert first.state.cursor_id == 501

    megaplan_api.get("todo", data=[])
    second = await sync.poll(first.state)

    assert second.state.cursor_id == 501
    assert second.looks_truncated is True
