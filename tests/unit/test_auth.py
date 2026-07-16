"""Unit tests for authentication."""

import time

import pytest
import respx
from httpx import Response

from megaplan_sdk.auth import AuthManager
from megaplan_sdk.exceptions import AuthenticationError
from megaplan_sdk.http_client import HTTPClient


@pytest.mark.asyncio
@respx.mock
async def test_authenticate():
    """Test authentication."""
    respx.post("https://example.com/api/v3/auth/access_token").mock(
        return_value=Response(
            200,
            json={
                "access_token": "test_token",
                "expires_in": 3600,
                "token_type": "bearer",
                "refresh_token": "refresh_token",
            },
        )
    )

    async with HTTPClient("https://example.com") as http_client:
        auth_manager = AuthManager(http_client)
        token = await auth_manager.authenticate("user@example.com", "password")

        assert token.access_token == "test_token"
        assert auth_manager.get_access_token() == "test_token"
        assert not auth_manager.is_token_expired()


@pytest.mark.asyncio
@respx.mock
async def test_authenticate_failure():
    """Test authentication failure."""
    respx.post("https://example.com/api/v3/auth/access_token").mock(
        return_value=Response(401, json={"error": "Invalid credentials"})
    )

    async with HTTPClient("https://example.com") as http_client:
        auth_manager = AuthManager(http_client)
        with pytest.raises(AuthenticationError):
            await auth_manager.authenticate("user@example.com", "wrong_password")


@pytest.mark.asyncio
@respx.mock
async def test_token_expiration():
    """Test token expiration check."""
    async with HTTPClient("https://example.com") as http_client:
        auth_manager = AuthManager(http_client)
        auth_manager._access_token = "test_token"
        auth_manager._expires_at = time.time() - 100

        assert auth_manager.is_token_expired()


@pytest.mark.asyncio
@respx.mock
async def test_refresh_token():
    """Test token refresh."""
    respx.post("https://example.com/api/v3/auth/access_token").mock(
        return_value=Response(
            200,
            json={
                "access_token": "new_token",
                "expires_in": 3600,
                "token_type": "bearer",
                "refresh_token": "new_refresh",
            },
        )
    )

    async with HTTPClient("https://example.com") as http_client:
        auth_manager = AuthManager(http_client)
        auth_manager._refresh_token = "old_refresh"

        token = await auth_manager.refresh()
        assert token.access_token == "new_token"
        assert auth_manager.get_access_token() == "new_token"


@pytest.mark.asyncio
async def test_clear_tokens():
    """Test clearing tokens."""
    async with HTTPClient("https://example.com") as http_client:
        auth_manager = AuthManager(http_client)
        auth_manager._access_token = "test_token"
        auth_manager._refresh_token = "refresh_token"

        auth_manager.clear_tokens()
        assert auth_manager.get_access_token() is None


# --- FR-A / FR-B: full token response from authenticate/refresh ---


async def test_authenticate_returns_full_token_response(
    megaplan_api, base_url, access_token, auth_response
):
    """FR-B: authenticate() returns the full token payload, not just a str."""
    from megaplan_sdk.models.auth import AuthTokenResponse

    megaplan_api.post(f"{base_url}/api/v3/auth/access_token", json=auth_response)

    async with HTTPClient(base_url) as http:
        manager = AuthManager(http)
        token = await manager.authenticate("user@example.com", "password")

    assert isinstance(token, AuthTokenResponse)
    assert token.access_token == access_token
    assert token.refresh_token == "test_refresh_token_67890"
    assert token.expires_in == 172800
    assert token.token_type == "bearer"


async def test_refresh_returns_rotated_refresh_token(megaplan_api, base_url):
    """FR-A: refresh() surfaces the rotated refresh_token to the caller."""
    from megaplan_sdk.models.auth import AuthTokenResponse

    megaplan_api.post(
        f"{base_url}/api/v3/auth/access_token",
        json={
            "access_token": "new_access",
            "expires_in": 172800,
            "token_type": "bearer",
            "scope": None,
            "refresh_token": "rotated_refresh",
        },
    )

    async with HTTPClient(base_url) as http:
        manager = AuthManager(http)
        token = await manager.refresh(refresh_token="old_refresh")

    assert isinstance(token, AuthTokenResponse)
    assert token.access_token == "new_access"
    assert token.refresh_token == "rotated_refresh"


async def test_auth_token_response_exported():
    """FR-A: AuthTokenResponse is part of the public API."""
    import megaplan_sdk

    assert hasattr(megaplan_sdk, "AuthTokenResponse")
