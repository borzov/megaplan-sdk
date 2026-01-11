"""Common models for Megaplan SDK."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Pagination(BaseModel):
    """Pagination information from API response.

    Attributes:
        count: Total number of items.
        limit: Items per page.
    """

    count: int = 0
    limit: int = 100


class Meta(BaseModel):
    """Meta information from API response.

    Attributes:
        status: HTTP status code.
        errors: List of error details.
        pagination: Pagination information.
    """

    status: int = 200
    errors: list[dict[str, Any]] = Field(default_factory=list)
    pagination: Pagination | None = None


class File(BaseModel):
    """File model for file uploads and attachments.

    Attributes:
        id: File identifier.
        content_type: File content type.
        path: File path.
        mime_type: MIME type.
        name: File name.
        size: File size in bytes.
    """

    id: int
    content_type: str = Field(alias="contentType", default="File")
    path: str | None = None
    mime_type: str | None = Field(alias="mimeType", default=None)
    name: str | None = None
    size: int | None = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DateTime(BaseModel):
    """DateTime model for date/time fields.

    Megaplan API returns dates as objects with contentType and value.

    Attributes:
        content_type: Always "DateTime".
        value: ISO 8601 datetime string.
    """

    content_type: str = Field(alias="contentType", default="DateTime")
    value: str

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class SortField(BaseModel):
    """Sort field for API requests.

    Attributes:
        field: Field name to sort by.
        direction: Sort direction (asc or desc).
    """

    field: str
    direction: str = "asc"  # asc or desc


class TimestampMixin(BaseModel):
    """Mixin for entities with creation and update timestamps.

    Attributes:
        created_at: Entity creation timestamp.
        updated_at: Entity last update timestamp.
    """

    created_at: str | DateTime | None = Field(alias="createdAt", default=None)
    updated_at: str | DateTime | None = Field(alias="updatedAt", default=None)


def rebuild_model_with_forward_refs(
    model_class: type[BaseModel], force_rebuild: bool = True
) -> None:
    """Rebuild Pydantic model to resolve forward references.

    This function is used when a model uses TYPE_CHECKING imports and forward
    references that need to be resolved after all models are loaded.

    Args:
        model_class: Pydantic model class to rebuild.
        force_rebuild: Force rebuild even if already built (default: True).

    Examples:
        >>> from megaplan_sdk.models.project import ProjectFullDetails
        >>> rebuild_model_with_forward_refs(ProjectFullDetails)
    """
    model_class.model_rebuild(force=force_rebuild)
