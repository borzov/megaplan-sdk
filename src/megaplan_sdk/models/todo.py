"""Todo ("Дела") models.

``when`` arrives in two shapes discriminated by contentType: IntervalDates for
all-day items (DateOnly bounds) and IntervalTime for timed ones (DateTime
bounds). Both are exposed through one TodoWhen so callers do not branch on the
wire format.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateOnly, DateTime

FINISHED_MASTER_TYPES = frozenset({"finished", "success", "fail", "finish_without_result"})


def _bound_shape(bound: dict[str, Any] | None) -> str | None:
    """Infer a `when` bound's shape from its own keys, not from an outer tag.

    Returns "date" for DateOnly-shaped bounds (year/month/day), "time" for
    DateTime-shaped bounds (value), or None when the bound is empty or
    carries neither set of keys.
    """
    if not bound:
        return None
    if "value" in bound:
        return "time"
    if any(key in bound for key in ("year", "month", "day")):
        return "date"
    return None


class TodoStatus(BaseEntity):
    """Status of a todo."""

    content_type: str = Field(alias="contentType", default=ContentType.TODO_STATUS)
    name: str | None = None
    master_type: str | None = Field(alias="masterType", default=None)


class TodoCategory(BaseEntity):
    """Category of a todo (event, meeting, call, todo, private)."""

    content_type: str = Field(alias="contentType", default="TodoCategory")
    name: str | None = None
    master_type: str | None = Field(alias="masterType", default=None)


class TodoWhen(BaseModel):
    """When a todo happens — an all-day date range or a timed interval.

    ``content_type`` has no default and stays optional: an SDK must survive
    unexpected server payloads (every model here uses ``extra="allow"`` for
    the same reason), so a `when` object missing its `contentType` must not
    fail the whole `Todo` it belongs to. When `content_type` is missing or
    unrecognized, the shape is inferred from the bounds' own keys instead
    (DateOnly carries year/month/day, DateTime carries value — see
    `_bound_shape`). If neither the tag nor the bounds resolve the shape,
    `is_all_day` defaults to False and the accessor properties return None
    rather than raise — malformed data degrades to "unknown", never to an
    exception.
    """

    content_type: str | None = Field(alias="contentType", default=None)
    from_: dict[str, Any] | None = Field(alias="from", default=None)
    to: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @property
    def is_all_day(self) -> bool:
        """True when the interval is expressed in calendar dates.

        Falls back to inferring the shape from the bounds themselves when
        `content_type` is missing or not one of the two known tags.
        """
        if self.content_type == "IntervalDates":
            return True
        if self.content_type == "IntervalTime":
            return False
        shape = _bound_shape(self.from_) or _bound_shape(self.to)
        return shape == "date"

    @property
    def start_date(self) -> DateOnly | None:
        """Start as a calendar date, or None for a timed/unrecognized interval.

        DateOnly has no required fields, so construction cannot raise here.
        """
        return DateOnly(**self.from_) if self.is_all_day and self.from_ else None

    @property
    def start_datetime(self) -> DateTime | None:
        """Start as a datetime, or None for an all-day/unrecognized interval."""
        if self.is_all_day or not self.from_:
            return None
        try:
            return DateTime(**self.from_)
        except ValidationError:
            return None

    @property
    def end_date(self) -> DateOnly | None:
        """End as a calendar date, or None for a timed/unrecognized interval."""
        return DateOnly(**self.to) if self.is_all_day and self.to else None

    @property
    def end_datetime(self) -> DateTime | None:
        """End as a datetime, or None for an all-day/unrecognized interval."""
        if self.is_all_day or not self.to:
            return None
        try:
            return DateTime(**self.to)
        except ValidationError:
            return None


class Todo(BaseEntity):
    """A todo ("Дело")."""

    content_type: str = Field(alias="contentType", default=ContentType.TODO)
    name: str | None = None
    status: TodoStatus | None = None
    category: TodoCategory | None = None
    when: TodoWhen | None = None
    responsible: BaseEntity | None = None
    user_created: BaseEntity | None = Field(alias="userCreated", default=None)
    time_created: DateTime | None = Field(alias="timeCreated", default=None)
    time_finished: DateTime | None = Field(alias="timeFinished", default=None)
    is_dropped: bool = Field(alias="isDropped", default=False)
    is_overdue: bool = Field(alias="isOverdue", default=False)
    description: str | None = None
    relations: list[BaseEntity] = Field(default_factory=list)
    comments_count: int | None = Field(alias="commentsCount", default=None)

    def is_finished(self) -> bool:
        """Whether the todo is closed, by status master type.

        A todo can be finished without a result (e.g. cancelled), in which
        case ``time_finished`` may still be empty — so status master type is
        the only reliable signal, not the timestamp.
        """
        return bool(self.status and self.status.master_type in FINISHED_MASTER_TYPES)

    def display_name(self) -> str:
        """Human-readable name."""
        return self.name or f"Todo#{self.id}"

    def __str__(self) -> str:
        """Return display name for string representation."""
        return self.display_name()
