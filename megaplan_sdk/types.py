"""Type definitions for Megaplan SDK."""

from typing import Any

from typing_extensions import TypedDict


class LinkEntity(TypedDict, total=False):
    """Link entity for references (only contentType and id)."""

    contentType: str
    id: int


class TaskFilterConfig(TypedDict, total=False):
    """Task filter configuration."""

    pass  # Will be extended based on API documentation


class TradeFilterConfig(TypedDict, total=False):
    """Trade filter configuration."""

    pass  # Will be extended based on API documentation


class ProjectFilterConfig(TypedDict, total=False):
    """Project filter configuration."""

    pass  # Will be extended based on API documentation


FilterType = int | str | TaskFilterConfig | TradeFilterConfig | ProjectFilterConfig


class RequestParams(TypedDict, total=False):
    """Common request parameters."""

    filter: FilterType | None
    limit: int | None
    pageAfter: LinkEntity | None
    pageBefore: LinkEntity | None
    pageWith: LinkEntity | None
    fields: Any | None
    sortBy: list[dict[str, str]] | None
    onlyRequestedFields: bool | None


class AuthTokenResponse(TypedDict):
    """OAuth2 token response."""

    access_token: str
    expires_in: int
    token_type: str
    scope: str | None
    refresh_token: str | None
