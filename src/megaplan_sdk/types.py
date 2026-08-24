"""Type definitions for Megaplan SDK."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from typing_extensions import TypedDict

from megaplan_sdk.models.auth import AuthTokenResponse


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


TokenRefreshCallback = Callable[[AuthTokenResponse], None | Awaitable[None]]
"""Application hook invoked with every freshly issued token pair.

May be a plain function or a coroutine function; an awaitable return value
is awaited. It runs while the internal refresh lock is held, so it must not
call back into the client (a refresh-reachable call would deadlock) and
should return quickly, since it serializes behind every other request. See
``MegaplanClient(on_token_refresh=...)``.
"""


class TokenProvider(Protocol):
    """Source of access tokens for the transport (0.6.2 auto-refresh).

    Implemented by :class:`~megaplan_sdk.auth.AuthManager`. ``HTTPClient``
    depends only on this narrow interface, so the transport never imports
    the auth layer and no import cycle is created.
    """

    async def ensure_valid_token(self) -> str | None:
        """Return the token to send with a new request.

        Refreshes proactively when the expiry is known and imminent. An
        unknown expiry is never a reason to refresh: a token restored from
        outside has no expiry, and a 401 is the only reliable signal for it.

        Returns:
            The token to send, or None when the client is unauthenticated.

        Raises:
            AuthenticationError: If the token is known to be expired and
                cannot be refreshed.
        """
        ...

    async def refresh_expired_token(self, rejected_token: str | None) -> str | None:
        """Obtain a replacement for a token the server rejected with 401.

        Args:
            rejected_token: The token that was sent and rejected. Lets the
                provider detect that a concurrent caller already refreshed.

        Returns:
            A usable token, or None when refreshing is impossible.

        Raises:
            AuthenticationError: If the refresh token itself was rejected.
        """
        ...
