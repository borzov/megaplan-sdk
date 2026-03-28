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

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class DateTime(BaseModel):
    """DateTime model for date/time fields.

    Megaplan API returns dates as objects with contentType and value.

    Attributes:
        content_type: Always "DateTime".
        value: ISO 8601 datetime string.
    """

    content_type: str = Field(alias="contentType", default="DateTime")
    value: str

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Money(BaseModel):
    """Money model for monetary value fields.

    Megaplan API returns monetary values as structured objects with
    currency, value, and optional exchange rate information.

    Attributes:
        content_type: Always "Money".
        currency: ISO 4217 currency code (e.g., "RUB", "USD").
        value: Amount in the original currency.
        value_in_main: Amount converted to the main company currency.
        rate: Exchange rate relative to the main currency.

    Example:
        >>> money = Money(contentType="Money", currency="RUB", value=18055000)
        >>> money.value
        18055000
        >>> money.currency
        'RUB'
    """

    content_type: str = Field(alias="contentType", default="Money")
    currency: str = ""
    value: float | int | None = None
    value_in_main: float | int | None = Field(None, alias="valueInMain")
    rate: float | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


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

    Megaplan API returns timestamps using the field names ``timeCreated``
    and ``timeUpdated`` (not ``createdAt``/``updatedAt``).

    Attributes:
        time_created: Entity creation timestamp (API field: ``timeCreated``).
        time_updated: Entity last update timestamp (API field: ``timeUpdated``).
    """

    time_created: str | DateTime | None = Field(alias="timeCreated", default=None)
    time_updated: str | DateTime | None = Field(alias="timeUpdated", default=None)
