"""Entity journal models: field changes and link/unlink records.

``GET /api/v3/{entity}/{id}/history`` returns a mixed stream. The documented
types are Message, Comment, Changeset, SendingLog and LoyaltyActionLogSet, but a
live account also returns ``BasedOnHistory`` (link/unlink) and ``TriggerLogSet``
— verified 2026-08-05. Unknown types are therefore passed through as raw dicts
rather than dropped or coerced.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateTime


class FieldChange(BaseModel):
    """One field change inside a :class:`Changeset`.

    For array fields the server emits two changes instead of one: an addition
    (``old_value`` None, ``new_value`` the added entities) and a removal
    (``old_value`` the removed entities, ``new_value`` None). So a changeset
    already carries the delta — no diffing of two entity states required.

    Attributes:
        content_type: Always "FieldChange".
        field: Changed field name, e.g. "state" or "auditors".
        description: Human-readable description rendered by the server.
        time_created: When the change happened.
        old_value: Previous value (shape depends on the field).
        new_value: New value (shape depends on the field).
        changed_entity: Entity the field belongs to.
        author: Who made the change.
    """

    content_type: str = Field(alias="contentType", default="FieldChange")
    field: str | None = None
    description: str | None = None
    time_created: DateTime | None = Field(alias="timeCreated", default=None)
    old_value: Any | None = Field(alias="oldValue", default=None)
    new_value: Any | None = Field(alias="newValue", default=None)
    changed_entity: BaseEntity | None = Field(alias="changedEntity", default=None)
    author: BaseEntity | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Changeset(BaseModel):
    """A set of field changes recorded together.

    Attributes:
        content_type: Always "Changeset".
        id: Changeset identifier.
        time_created: When the changes were recorded.
        type: Changeset kind: create, drop, restore (may be empty).
        changes: Individual field changes.
        changes_count: Number of changes reported by the server.
        entity: Entity the changeset belongs to.
        generated_by: What produced the changeset (trigger, scenario, ...).
        author: Who made the changes.
    """

    content_type: str = Field(alias="contentType", default="Changeset")
    id: int | None = None
    time_created: DateTime | None = Field(alias="timeCreated", default=None)
    type: str | None = None
    changes: list[FieldChange] | None = None
    changes_count: int | None = Field(alias="changesCount", default=None)
    entity: BaseEntity | None = None
    generated_by: BaseEntity | None = Field(alias="generatedBy", default=None)
    author: BaseEntity | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class BasedOnHistory(BaseModel):
    """A link or unlink between two entities.

    Undocumented but stable: this is what the journal records when a deal is
    linked to another deal or task, when one entity is created on the basis of
    another, and when a link is removed (``unlink`` True).

    Attributes:
        content_type: Always "BasedOnHistory".
        id: Record identifier; ids grow monotonically, so the largest one seen
            is a usable polling cursor.
        time_created: When the link changed.
        based_model: Source entity of the link.
        generated_model: Entity created from / linked to the source.
        user: Who linked or unlinked.
        unlink: True for removal, False for creation of the link.
        description: Human-readable HTML description.
    """

    content_type: str = Field(alias="contentType", default="BasedOnHistory")
    id: int | None = None
    time_created: DateTime | None = Field(alias="timeCreated", default=None)
    based_model: BaseEntity | None = Field(alias="basedModel", default=None)
    generated_model: BaseEntity | None = Field(alias="generatedModel", default=None)
    user: BaseEntity | None = None
    unlink: bool = False
    description: str | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class LinkEvent(BaseModel):
    """A link change seen from one entity's point of view.

    Attributes:
        id: Underlying BasedOnHistory id (polling cursor).
        time: When the link changed.
        user: Who changed it.
        unlink: True when the link was removed.
        other: The entity on the other end of the link.
        is_source: True when this entity is the link's ``based_model``.
        description: Human-readable HTML description from the server.
    """

    id: int | None = None
    time: DateTime | None = None
    user: BaseEntity | None = None
    unlink: bool = False
    other: BaseEntity
    is_source: bool = False
    description: str | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


# Journal entry types the SDK parses; anything else stays a raw dict.
_HISTORY_MODELS: dict[str, type[BaseModel]] = {
    "Changeset": Changeset,
    "BasedOnHistory": BasedOnHistory,
}

HistoryEntry = Changeset | BasedOnHistory | dict[str, Any]


def parse_history_entry(payload: dict[str, Any]) -> HistoryEntry:
    """Parse one journal entry into its model, or keep it as a dict.

    Args:
        payload: Raw entry from the history endpoint.

    Returns:
        A typed entry for known contentTypes, the payload unchanged otherwise.
    """
    model = _HISTORY_MODELS.get(payload.get("contentType", ""))
    return model(**payload) if model is not None else payload  # type: ignore[return-value]
