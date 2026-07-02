"""OAuth2 authentication for Megaplan API."""

import asyncio
import time
from typing import cast

from megaplan_sdk.exceptions import AuthenticationError
from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.logging_config import logger
from megaplan_sdk.types import AuthTokenResponse


class AuthManager:
    """Manages OAuth2 authentication and token lifecycle.

    Handles token acquisition, refresh, and expiration tracking.
    Transport concerns live behind HTTPClient.post_form — this module
    only interprets token payloads.
    """

    def __init__(self, http_client: HTTPClient) -> None:
        """Initialize auth manager.

        Args:
            http_client: HTTP client for making requests.
        """
        self._http = http_client
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float | None = None
        self._refresh_lock = asyncio.Lock()

    def _apply_token_response(self, token_data: AuthTokenResponse) -> str:
        """Store a token endpoint payload and propagate the token to HTTP.

        Args:
            token_data: Parsed token endpoint response.

        Returns:
            The new access token.

        Raises:
            KeyError: If the payload lacks ``access_token``.
        """
        self._access_token = token_data["access_token"]
        self._refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 172800)
        self._expires_at = time.time() + expires_in
        self._http.set_access_token(self._access_token)
        return self._access_token

    async def authenticate(self, username: str, password: str) -> str:
        """Authenticate with username and password.

        Args:
            username: User email or username.
            password: User password.

        Returns:
            Access token.

        Raises:
            AuthenticationError: If authentication fails.
        """
        logger.info("Authentication attempt")

        try:
            response = await self._http.post_form(
                f"{self._http.base_url}/api/v3/auth/access_token",
                data={
                    "username": username,
                    "password": password,
                    "grant_type": "password",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            token_data = cast(AuthTokenResponse, response)
            access_token = self._apply_token_response(token_data)
        except KeyError as e:
            logger.error(f"Authentication response parsing error for {username}: {str(e)}")
            raise AuthenticationError(f"Invalid authentication response: {str(e)}") from e

        logger.info("Authentication successful")
        return access_token

    async def refresh(self, refresh_token: str | None = None) -> str:
        """Refresh access token.

        Args:
            refresh_token: Optional refresh token. Uses stored token if not provided.

        Returns:
            New access token.

        Raises:
            AuthenticationError: If refresh fails.
        """
        token = refresh_token or self._refresh_token
        if not token:
            logger.error("No refresh token available for token refresh")
            raise AuthenticationError("No refresh token available")

        logger.info("Refreshing access token")

        try:
            response = await self._http.post_form(
                f"{self._http.base_url}/api/v3/auth/access_token",
                data={
                    "refresh_token": token,
                    "grant_type": "refresh_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            token_data = cast(AuthTokenResponse, response)
            access_token = self._apply_token_response(token_data)
        except KeyError as e:
            logger.error(f"Token refresh response parsing error: {str(e)}")
            raise AuthenticationError(f"Invalid token refresh response: {str(e)}") from e

        logger.info("Token refresh successful")
        return access_token

    def restore_token(self, access_token: str, expires_at: float | None = None) -> None:
        """Restore a previously issued access token.

        The public way to seed the manager with an externally stored token
        (e.g. MegaplanClient(access_token=...)) — callers must not write
        private attributes.

        Args:
            access_token: OAuth2 access token.
            expires_at: Unix timestamp of expiry; None if unknown.
        """
        self._access_token = access_token
        self._expires_at = expires_at
        self._http.set_access_token(access_token)

    def get_access_token(self) -> str | None:
        """Get current access token.

        Returns:
            Access token or None if not authenticated.
        """
        return self._access_token

    def is_token_expired(self, buffer_seconds: int = 60) -> bool:
        """Check if token is expired or will expire soon.

        Args:
            buffer_seconds: Seconds before expiration to consider token expired.

        Returns:
            True if token is expired or will expire within buffer.
        """
        if not self._expires_at:
            return True
        return time.time() >= (self._expires_at - buffer_seconds)

    async def ensure_authenticated(self, username: str, password: str) -> str:
        """Ensure we have a valid access token.

        Authenticates if needed or refreshes token if expired.
        Uses lock to prevent race conditions when multiple requests
        try to refresh token simultaneously.

        Args:
            username: Username for authentication.
            password: Password for authentication.

        Returns:
            Valid access token.
        """
        if not self._access_token or self.is_token_expired():
            async with self._refresh_lock:
                # Double-check after acquiring lock
                # Another coroutine might have already refreshed the token
                if not self._access_token or self.is_token_expired():
                    if self._refresh_token and not self.is_token_expired(buffer_seconds=3600):
                        try:
                            return await self.refresh()
                        except AuthenticationError:
                            pass

                    return await self.authenticate(username, password)

        return self._access_token

    def clear_tokens(self) -> None:
        """Clear stored tokens."""
        self._access_token = None
        self._refresh_token = None
        self._expires_at = None
        self._http.set_access_token(None)
