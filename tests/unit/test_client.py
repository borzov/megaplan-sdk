"""Unit tests for MegaplanClient."""

import pytest

from megaplan_sdk.client import MegaplanClient


@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization."""
    client = MegaplanClient(
        base_url="https://example.com",
        username="user@example.com",
        password="password",
    )

    assert client.base_url == "https://example.com"
    assert client.username == "user@example.com"
    assert client.tasks is not None
    assert client.projects is not None
    assert client.deals is not None
    assert client.files is not None
    assert client.auth is not None

    await client.close()


@pytest.mark.asyncio
async def test_client_with_token():
    """Test client with access token."""
    client = MegaplanClient(
        base_url="https://example.com",
        access_token="test_token",
    )

    assert client._http.access_token == "test_token"
    await client.close()


@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client as context manager."""
    async with MegaplanClient(base_url="https://example.com", access_token="token") as client:
        assert client._http._client is not None
