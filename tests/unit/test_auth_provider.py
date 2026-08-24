"""Unit tests for the TokenProvider surface of AuthManager (0.6.2 auto-refresh)."""

import time

import pytest
import respx
from httpx import Response

from megaplan_sdk.auth import AuthManager
from megaplan_sdk.exceptions import AuthenticationError
from megaplan_sdk.http_client import HTTPClient

TOKEN_URL = "https://example.com/api/v3/auth/access_token"


def _token_payload(access: str, refresh: str = "refresh-2", expires_in: int = 3600) -> dict:
    """Build an OAuth2 token endpoint payload."""
    return {
        "access_token": access,
        "expires_in": expires_in,
        "token_type": "bearer",
        "refresh_token": refresh,
    }


@respx.mock
async def test_ensure_valid_token_keeps_token_with_unknown_expiry():
    """A token restored from outside has no expiry and must not trigger a refresh."""
    route = respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload("new")))

    async with HTTPClient("https://example.com") as http:
        auth = AuthManager(http)
        auth.restore_token("restored-token")

        assert await auth.ensure_valid_token() == "restored-token"
        assert not route.called


@respx.mock
async def test_ensure_valid_token_refreshes_expired_token():
    """A known-expired token with a refresh token is refreshed proactively."""
    route = respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload("fresh")))

    async with HTTPClient("https://example.com") as http:
        auth = AuthManager(http)
        auth._access_token = "stale"
        auth._refresh_token = "refresh-1"
        auth._expires_at = time.time() - 10

        assert await auth.ensure_valid_token() == "fresh"
        assert route.call_count == 1
        assert http.access_token == "fresh"


@respx.mock
async def test_ensure_valid_token_raises_without_refresh_token():
    """An expired token with nothing to refresh with fails early and explains why."""
    async with HTTPClient("https://example.com") as http:
        auth = AuthManager(http)
        auth._access_token = "stale"
        auth._expires_at = time.time() - 10

        with pytest.raises(AuthenticationError, match="Re-authenticate"):
            await auth.ensure_valid_token()


@respx.mock
async def test_refresh_expired_token_reuses_concurrent_result():
    """If another coroutine already replaced the token, no network call is made."""
    route = respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload("other")))

    async with HTTPClient("https://example.com") as http:
        auth = AuthManager(http)
        auth._access_token = "current"
        auth._refresh_token = "refresh-1"

        assert await auth.refresh_expired_token("rejected-older-token") == "current"
        assert not route.called


@respx.mock
async def test_refresh_expired_token_refreshes_rejected_token():
    """The token the server rejected is the current one, so a refresh happens."""
    route = respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload("fresh")))

    async with HTTPClient("https://example.com") as http:
        auth = AuthManager(http)
        auth._access_token = "rejected"
        auth._refresh_token = "refresh-1"

        assert await auth.refresh_expired_token("rejected") == "fresh"
        assert route.call_count == 1


@respx.mock
async def test_refresh_expired_token_returns_none_without_refresh_token():
    """No refresh token at all: the transport must surface the original 401."""
    async with HTTPClient("https://example.com") as http:
        auth = AuthManager(http)
        auth._access_token = "rejected"

        assert await auth.refresh_expired_token("rejected") is None


@respx.mock
async def test_dead_refresh_token_explains_rotation():
    """A rotated-away refresh token yields an actionable AuthenticationError."""
    respx.post(TOKEN_URL).mock(return_value=Response(400, json={"error": "invalid_grant"}))

    async with HTTPClient("https://example.com") as http:
        auth = AuthManager(http)
        auth._access_token = "rejected"
        auth._refresh_token = "stale-refresh"

        with pytest.raises(AuthenticationError, match="single-use"):
            await auth.refresh_expired_token("rejected")


@respx.mock
async def test_ensure_authenticated_prefers_refresh_over_password():
    """An expired token with a live refresh token must not re-send the password."""
    captured: list[dict] = []

    def _capture(request):
        captured.append(dict(x.split("=", 1) for x in request.content.decode().split("&")))
        return Response(200, json=_token_payload("fresh"))

    respx.post(TOKEN_URL).mock(side_effect=_capture)

    async with HTTPClient("https://example.com") as http:
        auth = AuthManager(http)
        auth._access_token = "stale"
        auth._refresh_token = "refresh-1"
        auth._expires_at = time.time() - 10

        assert await auth.ensure_authenticated("user@example.com", "secret") == "fresh"

    assert len(captured) == 1
    assert captured[0]["grant_type"] == "refresh_token"


@respx.mock
async def test_ensure_authenticated_falls_back_to_password():
    """A dead refresh token falls back to username/password authentication."""
    grant_types: list[str] = []

    def _capture(request):
        body = dict(x.split("=", 1) for x in request.content.decode().split("&"))
        grant_types.append(body["grant_type"])
        if body["grant_type"] == "refresh_token":
            return Response(400, json={"error": "invalid_grant"})
        return Response(200, json=_token_payload("fresh"))

    respx.post(TOKEN_URL).mock(side_effect=_capture)

    async with HTTPClient("https://example.com") as http:
        auth = AuthManager(http)
        auth._access_token = "stale"
        auth._refresh_token = "stale-refresh"
        auth._expires_at = time.time() - 10

        assert await auth.ensure_authenticated("user@example.com", "secret") == "fresh"

    assert grant_types == ["refresh_token", "password"]


@respx.mock
async def test_ensure_authenticated_returns_live_token_untouched():
    """A token that is still valid is returned without any network call."""
    route = respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload("fresh")))

    async with HTTPClient("https://example.com") as http:
        auth = AuthManager(http)
        auth._access_token = "live"
        auth._expires_at = time.time() + 3600

        assert await auth.ensure_authenticated("user@example.com", "secret") == "live"
        assert not route.called
