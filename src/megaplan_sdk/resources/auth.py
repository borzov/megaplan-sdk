"""Authentication resource for Megaplan API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from megaplan_sdk.auth import AuthManager
from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.base import BaseResource

if TYPE_CHECKING:
    from megaplan_sdk.cache import EntityCache


class AuthResource(BaseResource):
    """Resource for OAuth2 authentication."""

    def __init__(self, http_client: HTTPClient, cache: EntityCache | None = None) -> None:
        """Initialize auth resource.

        Args:
            http_client: HTTP client for making requests.
            cache: Optional entity cache.
        """
        super().__init__(http_client, cache=cache)
        self._auth_manager = AuthManager(http_client)

    async def authenticate(self, username: str, password: str) -> str:
        """Authenticate with username and password.

        Args:
            username: User email or username.
            password: User password.

        Returns:
            Access token.
        """
        return await self._auth_manager.authenticate(username, password)

    async def refresh_token(self, refresh_token: str | None = None) -> str:
        """Refresh access token.

        Args:
            refresh_token: Optional refresh token. Uses stored token if not provided.

        Returns:
            New access token.
        """
        return await self._auth_manager.refresh(refresh_token)

    async def ensure_authenticated(self, username: str, password: str) -> str:
        """Ensure we have a valid access token.

        Args:
            username: Username for authentication.
            password: Password for authentication.

        Returns:
            Valid access token.
        """
        return await self._auth_manager.ensure_authenticated(username, password)

    def get_access_token(self) -> str | None:
        """Get current access token.

        Returns:
            Access token or None if not authenticated.
        """
        return self._auth_manager.get_access_token()

    def clear_tokens(self) -> None:
        """Clear stored tokens."""
        self._auth_manager.clear_tokens()
