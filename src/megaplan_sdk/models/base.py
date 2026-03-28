"""Base models for Megaplan SDK."""

from pydantic import BaseModel, ConfigDict, Field


class BaseEntity(BaseModel):
    """Base entity with contentType, id, and optional name.

    All Megaplan entities have ``contentType`` and ``id`` fields.
    Many API responses also include a ``name`` field even in reference
    objects, so it is captured here to avoid silent data loss.

    Unknown fields from the API are preserved in ``model_extra`` via
    ``extra="allow"``, which enables forward compatibility and prevents
    silent data loss when the API returns new fields.

    Attributes:
        content_type: Entity type identifier (e.g., "Employee", "Task").
        id: Entity numeric identifier.
        name: Optional display name returned by the API in many contexts.
    """

    content_type: str = Field(alias="contentType")
    id: int
    name: str | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")
