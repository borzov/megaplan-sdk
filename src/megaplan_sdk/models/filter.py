"""Filter models for Megaplan SDK."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity


class BaseFilter(BaseModel):
    """Base filter model.

    All filters in Megaplan have common structure with id, contentType, name, and config.
    Note: id can be either integer or string (e.g., "incoming", "my_filter").
    """

    id: int | str
    content_type: str = Field(alias="contentType")
    name: str | None = None
    config: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class TaskFilter(BaseFilter):
    """Task filter model."""

    content_type: str = Field(alias="contentType", default="TaskFilter")


class TradeFilter(BaseFilter):
    """Trade/Deal filter model."""

    content_type: str = Field(alias="contentType", default="TradeFilter")


class EmployeeFilter(BaseFilter):
    """Employee filter model."""

    content_type: str = Field(alias="contentType", default="EmployeeFilter")


class ProjectFilter(BaseFilter):
    """Project filter model."""

    content_type: str = Field(alias="contentType", default="ProjectFilter")


class FilterExport(BaseModel):
    """Filter export result.

    When exporting filter data, API returns either a File entity (if export completed immediately)
    or None (if export was queued as a background job).
    """

    file: BaseEntity | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class UserSetting(BaseModel):
    """User filter settings.

    Represents user-specific settings for a filter.
    """

    # Structure will be determined from API responses
    # For now, accept any structure
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class NewFilterSettingsRequest(BaseModel):
    """Request for new filter settings.

    Used when setting filter settings via POST /api/v3/{entityType}Filter/{id}/newFilterSettings.
    """

    # Structure will be determined from API responses
    # For now, accept any structure
    model_config = ConfigDict(populate_by_name=True, extra="allow")
