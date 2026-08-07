"""Common models for Megaplan SDK."""

import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field


class MainEntityProxyMixin:
    """Delegate unknown attribute access to a wrapped main entity (#25).

    ``*FullDetails`` containers wrap the primary entity (Task/Deal/Project)
    under a named field (``task``/``deal``/``project``). Without delegation,
    code written for the plain entity (``task.owner.name``) breaks the moment
    ``expand=`` switches the return type to a container. This mixin proxies any
    attribute missing on the container to the wrapped entity, so both
    ``details.task.owner`` and ``details.owner`` work.

    Subclasses set ``_main_field`` to the wrapped field's name. Container fields
    and explicit container extras always win; only genuinely missing attributes
    are delegated.
    """

    _main_field: ClassVar[str]

    def __getattr__(self, item: str) -> Any:
        try:
            return super().__getattr__(item)  # type: ignore[misc]
        except AttributeError:
            if not item.startswith("_"):
                main = self.__dict__.get(type(self)._main_field)
                if main is not None:
                    return getattr(main, item)
            raise


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


class DateOnly(BaseModel):
    """Calendar date without a time component (birthdays, deadlines by day).

    The year can be missing or nonsense on real accounts, so ``month``/``day``
    stay usable independently of it and ``date`` is None when no valid calendar
    date can be built.

    Attributes:
        content_type: Always "DateOnly".
        year: Year, if the account has one.
        month: Month number.
        day: Day of month.
    """

    content_type: str = Field(alias="contentType", default="DateOnly")
    year: int | None = None
    month: int | None = None
    day: int | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @property
    def date(self) -> "datetime.date | None":
        """The value as ``datetime.date``, or None if it is not a valid date."""
        if self.year is None or self.month is None or self.day is None:
            return None
        try:
            return datetime.date(self.year, self.month, self.day)
        except ValueError:
            return None


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


class DateInterval(BaseModel):
    """Time interval model for work-time / duration fields.

    Megaplan API returns durations as objects with ``contentType`` and a
    ``value`` measured in **seconds**. This typed wrapper replaces the raw
    ``dict`` previously exposed on ``Comment.work_time`` (#16) and offers
    convenience accessors.

    Attributes:
        content_type: Always "DateInterval".
        value: Duration in seconds.

    Example:
        >>> interval = DateInterval(contentType="DateInterval", value=9000)
        >>> interval.value
        9000
        >>> interval.minutes
        150.0
        >>> interval.hours
        2.5
    """

    content_type: str = Field(alias="contentType", default="DateInterval")
    value: int = 0

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @property
    def seconds(self) -> int:
        """Duration in seconds (alias for ``value``)."""
        return self.value

    @property
    def minutes(self) -> float:
        """Duration in minutes."""
        return self.value / 60

    @property
    def hours(self) -> float:
        """Duration in hours."""
        return self.value / 3600


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
