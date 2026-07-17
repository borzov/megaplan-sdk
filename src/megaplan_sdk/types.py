"""Type definitions for Megaplan SDK."""

from typing import Any

from typing_extensions import TypedDict


class LinkEntity(TypedDict, total=False):
    """Link entity for references (only contentType and id)."""

    contentType: str
    id: int


class TaskFilterConfig(TypedDict, total=False):
    """Task filter configuration.

    Can contain FilterConfig with termGroup for complex filtering.
    Example:
        {
            "contentType": "FilterConfig",
            "termGroup": {
                "contentType": "FilterTermGroup",
                "join": "and",
                "terms": [
                    {
                        "contentType": "FilterTermString",
                        "field": "name",
                        "comparison": "contains",
                        "value": "договор"
                    }
                ]
            }
        }
    """

    contentType: str  # "FilterConfig"
    termGroup: dict[str, Any]  # FilterTermGroup
    filterId: int | str | None


class TradeFilterConfig(TypedDict, total=False):
    """Trade filter configuration.

    Can contain FilterConfig with termGroup for complex filtering.
    Example:
        {
            "contentType": "FilterConfig",
            "termGroup": {
                "contentType": "FilterTermGroup",
                "join": "and",
                "terms": [
                    {
                        "contentType": "FilterTermString",
                        "field": "name",
                        "comparison": "contains",
                        "value": "Leader"
                    }
                ]
            }
        }
    """

    contentType: str  # "FilterConfig"
    termGroup: dict[str, Any]  # FilterTermGroup
    filterId: int | str | None


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


class AuthTokenPayload(TypedDict):
    """OAuth2 token endpoint wire payload (internal)."""

    access_token: str
    expires_in: int
    token_type: str
    scope: str | None
    refresh_token: str | None
