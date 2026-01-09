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
    assert client.comments is not None
    assert client.contractors is not None
    assert client.employees is not None
    assert client.departments is not None
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


@pytest.mark.asyncio
async def test_client_passes_default_limits_to_resources():
    """Test that MegaplanClient passes default limits to resources."""
    client = MegaplanClient(
        base_url="https://example.megaplan.ru",
        access_token="test_token",
        default_comments_limit=30,
        default_history_limit=60,
    )

    # Verify resources received the defaults
    assert client.tasks._default_comments_limit == 30
    assert client.tasks._default_history_limit == 60
    assert client.projects._default_comments_limit == 30
    assert client.projects._default_history_limit == 60
    assert client.deals._default_comments_limit == 30
    assert client.deals._default_history_limit == 60

    # Other resources should have None (not affected)
    assert client.employees._default_comments_limit is None
    assert client.contractors._default_comments_limit is None

    await client.close()
