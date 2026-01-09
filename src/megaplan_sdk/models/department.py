"""Department model for Megaplan SDK."""

from pydantic import ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import TimestampMixin


class Department(BaseEntity, TimestampMixin):
    """Department entity.

    Attributes:
        id: Department identifier.
        content_type: Entity content type (always "Department").
        name: Department name.
        parent: Parent department (if nested structure).
        manager: Department manager (Employee reference).
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    content_type: str = Field(alias="contentType", default="Department")
    name: str | None = None
    parent: BaseEntity | None = None
    manager: BaseEntity | None = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    def __str__(self) -> str:
        """Return department name for display.

        Returns:
            Department name or fallback ID representation.

        Examples:
            >>> dept = Department(id=1, name="Engineering")
            >>> str(dept)
            'Engineering'
        """
        return self.name or f"Department#{self.id}"
