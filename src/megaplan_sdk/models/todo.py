"""Todo ("Дела") models.

``when`` arrives in two shapes discriminated by contentType: IntervalDates for
all-day items (DateOnly bounds) and IntervalTime for timed ones (DateTime
bounds). Both are exposed through one TodoWhen so callers do not branch on the
wire format.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateOnly, DateTime

FINISHED_MASTER_TYPES = frozenset({"finished", "success", "fail", "finish_without_result"})


class TodoStatus(BaseEntity):
    """Status of a todo."""

    name: str | None = None
    master_type: str | None = Field(alias="masterType", default=None)


class TodoCategory(BaseEntity):
    """Category of a todo (event, meeting, call, todo, private)."""

    name: str | None = None
    master_type: str | None = Field(alias="masterType", default=None)


class TodoWhen(BaseModel):
    """When a todo happens — an all-day date range or a timed interval."""

    content_type: str = Field(alias="contentType", default="IntervalTime")
    from_: dict[str, Any] | None = Field(alias="from", default=None)
    to: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @property
    def is_all_day(self) -> bool:
        """True when the interval is expressed in calendar dates."""
        return self.content_type == "IntervalDates"

    @property
    def start_date(self) -> DateOnly | None:
        """Start as a calendar date, or None for a timed interval."""
        return DateOnly(**self.from_) if self.is_all_day and self.from_ else None

    @property
    def start_datetime(self) -> DateTime | None:
        """Start as a datetime, or None for an all-day interval."""
        return DateTime(**self.from_) if not self.is_all_day and self.from_ else None

    @property
    def end_date(self) -> DateOnly | None:
        """End as a calendar date, or None for a timed interval."""
        return DateOnly(**self.to) if self.is_all_day and self.to else None

    @property
    def end_datetime(self) -> DateTime | None:
        """End as a datetime, or None for an all-day interval."""
        return DateTime(**self.to) if not self.is_all_day and self.to else None


class Todo(BaseEntity):
    """A todo ("Дело")."""

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
        return self.display_name()
