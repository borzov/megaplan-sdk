"""Group model for Megaplan SDK."""

from __future__ import annotations

from pydantic import ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity


class Group(BaseEntity):
    """Group entity for organizing participants.

    Used to group entities by some attribute (e.g., department, role).

    Attributes:
        id: Group identifier.
        content_type: Entity content type (always "Group").
        name: Group name.
        children: List of child entities in this group.
        children_count: Number of entities in this group.
    """

    content_type: str = Field(alias="contentType", default="Group")
    name: str | None = None
    children: list[BaseEntity] | None = None
    children_count: int | None = Field(alias="childrenCount", default=None)

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    def display_name(self) -> str:
        """Get display name for the group.

        Returns:
            Group name or fallback identifier.
        """
        return self.name or f"Group#{self.id}"

    def __str__(self) -> str:
        """Return display name for string representation."""
        return self.display_name()
