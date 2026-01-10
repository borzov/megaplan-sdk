"""Milestone model for Megaplan SDK."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateTime, TimestampMixin


class Milestone(BaseEntity, TimestampMixin):
    """Milestone entity.

    Represents a milestone (веха) in Megaplan attached to a task or project.

    Attributes:
        id: Milestone identifier.
        content_type: Entity content type (always "Milestone").
        name: Milestone name.
        description: Milestone description (required when creating).
        completed: Whether milestone is completed.
        owner: Milestone creator (Employee reference).
        responsible: Milestone responsible person (Employee reference).
        type: Milestone type - "report", "reminder", or "note" (required when creating).
        date: Milestone date and time (required when creating).
            Can be DateTime object, dict, or ISO 8601 string.
        task: Associated task (Task reference).
        project: Associated project (Project reference).
        reminder: Reminder configuration.
        possible_actions: List of possible actions (e.g., ["act_milestone_edit"]).
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    content_type: str = Field(alias="contentType", default="Milestone")
    name: str | None = None
    description: str | None = None
    completed: bool | None = None
    owner: BaseEntity | None = None
    responsible: BaseEntity | None = None
    type: str | None = None  # "report", "reminder", "note"
    date: str | DateTime | dict[str, Any] | None = None
    task: BaseEntity | None = None
    project: BaseEntity | None = None
    reminder: dict[str, Any] | None = None
    possible_actions: list[str] | None = Field(alias="possibleActions", default=None)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    def display_name(self) -> str:
        """Get display name for milestone.

        Returns:
            Milestone name or fallback ID representation.

        Examples:
            >>> milestone = Milestone(id=1, name="Release 1.0")
            >>> milestone.display_name()
            'Release 1.0'
        """
        if self.name:
            return self.name
        if self.description:
            # Use first 50 chars of description
            desc = self.description[:50]
            return desc + "..." if len(self.description) > 50 else desc
        return f"Milestone#{self.id}"

    def __str__(self) -> str:
        """Return milestone display name.

        Returns:
            Milestone display name.

        Examples:
            >>> milestone = Milestone(id=1, name="Release 1.0")
            >>> str(milestone)
            'Release 1.0'
        """
        return self.display_name()
