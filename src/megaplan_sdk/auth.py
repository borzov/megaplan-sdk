"""OAuth2 authentication for Megaplan API."""

import asyncio
import time
from typing import cast

from pydantic import ValidationError as PydanticValidationError

from megaplan_sdk.exceptions import AuthenticationError
from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.logging_config import logger
from megaplan_sdk.models.auth import AuthTokenResponse
from megaplan_sdk.types import AuthTokenPayload


class AuthManager:
    """Manages OAuth2 authentication and token lifecycle.

    Handles token acquisition, refresh, and expiration tracking.
    Transport concerns live behind HTTPClient.post_form — this module
    only interprets token payloads.
    """

    _REAUTH_HINT = (
        "The refresh token was rejected by the server. Refresh tokens are "
        "single-use and rotate on every refresh, so a stale one always fails. "
        "Re-authenticate with client.authenticate(username, password)."
    )

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

    def _apply_token_response(self, token_data: AuthTokenPayload) -> AuthTokenResponse:
        """Store a token endpoint payload and propagate the token to HTTP.

        Args:
            token_data: Parsed token endpoint response.

        Returns:
            The parsed token response (FR-A/FR-B).

        Raises:
            pydantic.ValidationError: If the payload lacks ``access_token``.
        """
        token_response = AuthTokenResponse(**token_data)
        self._access_token = token_response.access_token
        self._refresh_token = token_response.refresh_token
        self._expires_at = time.time() + token_response.expires_in
        self._http.set_access_token(self._access_token)
        return token_response

    async def authenticate(self, username: str, password: str) -> AuthTokenResponse:
        """Authenticate with username and password.

        Args:
            username: User email or username.
            password: User password.

        Returns:
            Full token response (access_token, refresh_token, expires_in).

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
            token_data = cast(AuthTokenPayload, response)
            token_response = self._apply_token_response(token_data)
        except (KeyError, PydanticValidationError) as e:
            logger.error(f"Authentication response parsing error for {username}: {str(e)}")
            raise AuthenticationError(f"Invalid authentication response: {str(e)}") from e

        logger.info("Authentication successful")
        return token_response

    async def refresh(self, refresh_token: str | None = None) -> AuthTokenResponse:
        """Refresh access token.

        Args:
            refresh_token: Optional refresh token. Uses stored token if not provided.

        Returns:
            Full token response (access_token, refresh_token, expires_in).

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
            token_data = cast(AuthTokenPayload, response)
            token_response = self._apply_token_response(token_data)
        except (KeyError, PydanticValidationError) as e:
            logger.error(f"Token refresh response parsing error: {str(e)}")
            raise AuthenticationError(f"Invalid token refresh response: {str(e)}") from e

        logger.info("Token refresh successful")
        return token_response

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

    async def _refresh_or_explain(self) -> str:
        """Refresh the access token, translating failures into actionable errors.

        Returns:
            The new access token.

        Raises:
            AuthenticationError: If the server rejected the refresh token.
        """
        try:
            return (await self.refresh()).access_token
        except AuthenticationError as e:
            logger.error("Token refresh rejected by the server")
            raise AuthenticationError(self._REAUTH_HINT) from e

    async def ensure_valid_token(self) -> str | None:
        """Return the token to send with a new request (TokenProvider).

        Returns:
            The token to send, or None when the client is unauthenticated.

        Raises:
            AuthenticationError: If the token is known to be expired and
                cannot be refreshed.
        """
        if self._expires_at is None:
            # Expiry unknown (token restored from outside): refreshing on a
            # guess would break clients constructed with access_token only.
            return self._access_token

        if not self.is_token_expired():
            return self._access_token

        async with self._refresh_lock:
            # Re-check: a concurrent request may have refreshed while waiting.
            if not self.is_token_expired():
                return self._access_token

            if not self._refresh_token:
                raise AuthenticationError(
                    "Access token has expired and no refresh token is available. "
                    "Re-authenticate with client.authenticate(username, password)."
                )

            return await self._refresh_or_explain()

    async def refresh_expired_token(self, rejected_token: str | None) -> str | None:
        """Replace a token the server rejected with 401 (TokenProvider).

        Args:
            rejected_token: The token that was sent and rejected.

        Returns:
            A usable token, or None when there is no refresh token.

        Raises:
            AuthenticationError: If the server rejected the refresh token.
        """
        async with self._refresh_lock:
            if self._access_token and self._access_token != rejected_token:
                # A concurrent request already refreshed; reuse its result
                # instead of spending a second refresh (and rotating twice).
                logger.debug("Token already refreshed by a concurrent request")
                return self._access_token

            if not self._refresh_token:
                return None

            return await self._refresh_or_explain()

    async def ensure_authenticated(self, username: str, password: str) -> str:
        """Ensure we have a valid access token.

        Prefers refreshing over re-sending the password: the refresh token
        is the cheaper and less sensitive credential. Falls back to
        username/password only when there is no refresh token or the server
        rejected it.

        Args:
            username: Username for authentication.
            password: Password for authentication.

        Returns:
            Valid access token.

        Raises:
            AuthenticationError: If neither refresh nor password succeeds.
        """
        if self._access_token and not self.is_token_expired():
            return self._access_token

        async with self._refresh_lock:
            # Double-check: another coroutine may have refreshed already.
            if self._access_token and not self.is_token_expired():
                return self._access_token

            if self._refresh_token:
                try:
                    return (await self.refresh()).access_token
                except AuthenticationError:
                    logger.warning(
                        "Refresh token rejected; falling back to password authentication"
                    )

            return (await self.authenticate(username, password)).access_token

    def clear_tokens(self) -> None:
        """Clear stored tokens."""
        self._access_token = None
        self._refresh_token = None
        self._expires_at = None
        self._http.set_access_token(None)
