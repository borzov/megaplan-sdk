"""Project models for Megaplan SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateTime, MainEntityProxyMixin, TimestampMixin

if TYPE_CHECKING:
    from megaplan_sdk.models.milestone import Milestone


class ProjectFilter(BaseModel):
    """Project filter configuration.

    Can be used as filter ID (integer) or filter configuration (dict).
    """

    id: int | None = None
    config: dict[str, Any] | None = None


class Project(TimestampMixin):
    """Project model.

    Represents a project in Megaplan with all its properties.
    """

    id: int
    content_type: str = Field(alias="contentType", default="Project")
    name: str | None = None
    description: str | None = None
    status: str | None = None
    owner: BaseEntity | None = None
    responsible: BaseEntity | None = None
    deadline: str | DateTime | dict[str, Any] | None = None  # Can be DateOnly, DateTime, or string
    actual_finish: str | DateTime | None = Field(alias="actualFinish", default=None)
    parent: BaseEntity | None = None
    priority: str | None = None
    tags: list[BaseEntity] | None = None
    attaches: list[BaseEntity] | None = None
    todos: list[BaseEntity] | None = None
    comments_count: int | None = Field(alias="commentsCount", default=None)

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ProjectFullDetails(MainEntityProxyMixin, BaseModel):
    """Full project details with all related entities.

    Attribute access falls through to the wrapped ``project`` (#25): both
    ``details.project.owner`` and ``details.owner`` resolve identically.

    ``owner``/``responsible`` prefer the loaded ``*_details`` when expand
    populated them, falling back to the raw wire reference otherwise (#25).

    Attributes:
        project: Main project entity.
        deals: List of associated deals (if requested).
        issues: List of tasks/issues (if requested).
        actual_issues: List of actual tasks/issues (if requested).
        comments: List of comments (if requested).
        history: Journal entries (if requested), parsed the same way as
            get_history(): typed Changeset/BasedOnHistory, unknown types as dict.
        auditors: List of auditors (if requested).
        executors: List of executors/co-performers (if requested).
        milestones: List of milestones (if requested).
        responsible_details: Full responsible employee details (if requested).
        owner_details: Full owner employee details (if requested).
    """

    _main_field: ClassVar[str] = "project"

    project: Project
    deals: list[Any] | None = None
    issues: list[Any] | None = None
    actual_issues: list[Any] | None = None
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
        """Loaded owner (``owner_details``) or the raw ``project.owner`` reference."""
        return self.owner_details if self.owner_details is not None else self.project.owner

    @property
    def responsible(self) -> Any:
        """Loaded responsible (``responsible_details``) or the raw reference."""
        return (
            self.responsible_details
            if self.responsible_details is not None
            else self.project.responsible
        )


# Rebuild models after Milestone is defined to resolve forward references
def _rebuild_project_models() -> None:
    """Rebuild ProjectFullDetails model after Milestone is imported."""
    from megaplan_sdk.models.milestone import Milestone  # noqa: F401

    # Direct call needed because import must happen before rebuild
    ProjectFullDetails.model_rebuild(force=True)


# Auto-rebuild on import
_rebuild_project_models()
