"""Task models for Megaplan SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateTime, MainEntityProxyMixin, TimestampMixin

if TYPE_CHECKING:
    from megaplan_sdk.models.milestone import Milestone


class TaskFilter(BaseModel):
    """Task filter configuration.

    Can be used as filter ID (integer) or filter configuration (dict).
    """

    id: int | None = None
    config: dict[str, Any] | None = None


class Task(TimestampMixin):
    """Task model.

    Represents a task in Megaplan with all its properties.
    """

    id: int
    content_type: str = Field(alias="contentType", default="Task")
    name: str | None = None
    description: str | None = None
    status: str | None = None
    responsible: BaseEntity | None = None
    owner: BaseEntity | None = None
    deadline: str | DateTime | dict[str, Any] | None = None  # Can be DateOnly, DateTime, or string
    actual_finish: str | DateTime | None = Field(alias="actualFinish", default=None)
    parent: BaseEntity | None = None
    project: BaseEntity | None = None
    priority: str | None = None
    tags: list[BaseEntity] | None = None
    attaches: list[BaseEntity] | None = None
    todos: list[BaseEntity] | None = None
    activity: str | DateTime | None = None
    last_comment_time_created: str | DateTime | None = Field(
        alias="lastCommentTimeCreated", default=None
    )
    status_change_time: str | DateTime | None = Field(alias="statusChangeTime", default=None)
    actual_start: str | DateTime | None = Field(alias="actualStart", default=None)
    last_view: str | DateTime | None = Field(alias="lastView", default=None)
    comments_count: int | None = Field(alias="commentsCount", default=None)

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class TaskFullDetails(MainEntityProxyMixin, BaseModel):
    """Full task details with all related entities.

    Attribute access falls through to the wrapped ``task`` (#25): both
    ``details.task.owner`` and ``details.owner`` resolve identically, so code
    written for a plain ``Task`` keeps working under ``expand=``.

    ``owner``/``responsible`` prefer the loaded ``*_details`` when expand
    populated them, falling back to the raw wire reference otherwise — the
    list API embeds a repeated linked entity fully only at its first
    occurrence, so the raw reference alone is not reliable (#25).

    Attributes:
        task: Main task entity.
        sub_tasks: List of subtasks (if requested).
        actual_sub_tasks: List of actual subtasks (if requested).
        comments: List of comments (if requested).
        history: Journal entries (if requested), parsed the same way as
            get_history(): typed Changeset/BasedOnHistory, unknown types as dict.
        auditors: List of auditors (if requested).
        executors: List of executors/co-performers (if requested).
        milestones: List of milestones (if requested).
        responsible_details: Full responsible employee details (if requested).
        owner_details: Full owner employee details (if requested).
    """

    _main_field: ClassVar[str] = "task"

    task: Task
    sub_tasks: list[Any] | None = None
    actual_sub_tasks: list[Any] | None = None
    comments: list[Any] | None = None
    history: list[Any] | None = None
    auditors: list[Any] | None = None
    executors: list[Any] | None = None
    milestones: list[Milestone] | None = None
    responsible_details: Any | None = None
    owner_details: Any | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @property
    def owner(self) -> Any:
        """Loaded owner (``owner_details``) or the raw ``task.owner`` reference."""
        return self.owner_details if self.owner_details is not None else self.task.owner

    @property
    def responsible(self) -> Any:
        """Loaded responsible (``responsible_details``) or the raw reference."""
        return (
            self.responsible_details
            if self.responsible_details is not None
            else self.task.responsible
        )


# Rebuild models after Milestone is defined to resolve forward references
def _rebuild_task_models() -> None:
    """Rebuild TaskFullDetails model after Milestone is imported."""
    from megaplan_sdk.models.milestone import Milestone  # noqa: F401

    # Direct call needed because import must happen before rebuild
    TaskFullDetails.model_rebuild(force=True)


# Auto-rebuild on import
_rebuild_task_models()
