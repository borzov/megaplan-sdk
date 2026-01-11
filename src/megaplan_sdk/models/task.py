"""Task models for Megaplan SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateTime, TimestampMixin

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

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class TaskFullDetails(BaseModel):
    """Full task details with all related entities.

    Attributes:
        task: Main task entity.
        sub_tasks: List of subtasks (if requested).
        actual_sub_tasks: List of actual subtasks (if requested).
        comments: List of comments (if requested).
        history: Change history entries (if requested).
        auditors: List of auditors (if requested).
        executors: List of executors/co-performers (if requested).
        milestones: List of milestones (if requested).
        responsible_details: Full responsible employee details (if requested).
        owner_details: Full owner employee details (if requested).
    """

    task: Task
    sub_tasks: list[Any] | None = None
    actual_sub_tasks: list[Any] | None = None
    comments: list[Any] | None = None
    history: list[dict[str, Any]] | None = None
    auditors: list[Any] | None = None
    executors: list[Any] | None = None
    milestones: list[Milestone] | None = None
    responsible_details: Any | None = None
    owner_details: Any | None = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


# Rebuild models after Milestone is defined to resolve forward references
def _rebuild_task_models() -> None:
    """Rebuild TaskFullDetails model after Milestone is imported."""
    from megaplan_sdk.models.milestone import Milestone  # noqa: F401

    # Rebuild with force to ensure forward references are resolved
    TaskFullDetails.model_rebuild(force=True)


# Auto-rebuild on import
_rebuild_task_models()
