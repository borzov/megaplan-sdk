"""Unit tests for HTTP client."""

from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from megaplan_sdk.exceptions import AuthenticationError, NotFoundError
from megaplan_sdk.http_client import HTTPClient


@pytest.mark.asyncio
@respx.mock
async def test_get_request():
    """Test GET request."""
    respx.get("https://example.com/api/v3/task").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": []})
    )

    async with HTTPClient("https://example.com") as client:
        response = await client.get("/api/v3/task")
        assert response["meta"]["status"] == 200


@pytest.mark.asyncio
@respx.mock
async def test_post_request():
    """Test POST request."""
    respx.post("https://example.com/api/v3/task").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": {"id": 1}})
    )

    async with HTTPClient("https://example.com") as client:
        response = await client.post("/api/v3/task", json_data={"name": "Test"})
        assert response["data"]["id"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_auth_header():
    """Test Authorization header injection."""
    respx.get("https://example.com/api/v3/task").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": []})
    )

    async with HTTPClient("https://example.com", access_token="test_token") as client:
        await client.get("/api/v3/task")
        request = respx.calls.last.request
        assert request.headers["Authorization"] == "Bearer test_token"


@pytest.mark.asyncio
@respx.mock
async def test_json_query_params():
    """Test JSON parameters in query string."""
    # httpx URL-encodes the JSON query params
    respx.get("https://example.com/api/v3/task?{%22limit%22:%205}").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": []})
    )

    async with HTTPClient("https://example.com") as client:
        await client.get("/api/v3/task", params={"limit": 5})


@pytest.mark.asyncio
@respx.mock
async def test_error_handling_404():
    """Test error handling for 404."""
    respx.get("https://example.com/api/v3/task/999").mock(
        return_value=Response(404, json={"meta": {"status": 404, "errors": []}})
    )

    async with HTTPClient("https://example.com") as client:
        with pytest.raises(NotFoundError):
            await client.get("/api/v3/task/999")


@pytest.mark.asyncio
@respx.mock
async def test_retry_on_500():
    """Test retry logic on 500 errors."""
    respx.get("https://example.com/api/v3/task").mock(
        side_effect=[
            Response(500, json={"meta": {"status": 500}}),
            Response(200, json={"meta": {"status": 200}, "data": []}),
        ]
    )

    async with HTTPClient("https://example.com", max_retries=2) as client:
        response = await client.get("/api/v3/task")
        assert response["meta"]["status"] == 200


def test_proxy_stored_in_client():
    """Test that proxy is stored in HTTPClient."""
    client = HTTPClient("https://example.com", proxy="http://proxy:8080")
    assert client._proxy == "http://proxy:8080"


def test_proxy_default_none():
    """Test that proxy defaults to None."""
    client = HTTPClient("https://example.com")
    assert client._proxy is None


@pytest.mark.asyncio
async def test_proxy_passed_to_async_client():
    """Test that proxy is passed to httpx.AsyncClient."""
    with patch("megaplan_sdk.http_client.httpx.AsyncClient") as mock_async_client:
        mock_instance = AsyncMock()
        mock_async_client.return_value = mock_instance

        client = HTTPClient("https://example.com", proxy="http://user:pass@proxy:8080")
        await client._ensure_client()

        mock_async_client.assert_called_once()
        call_kwargs = mock_async_client.call_args.kwargs
        assert call_kwargs["proxy"] == "http://user:pass@proxy:8080"


@pytest.mark.asyncio
async def test_proxy_none_passed_to_async_client():
    """Test that None proxy is passed to httpx.AsyncClient when not specified."""
    with patch("megaplan_sdk.http_client.httpx.AsyncClient") as mock_async_client:
        mock_instance = AsyncMock()
        mock_async_client.return_value = mock_instance

        client = HTTPClient("https://example.com")
        await client._ensure_client()

        mock_async_client.assert_called_once()
        call_kwargs = mock_async_client.call_args.kwargs
        assert call_kwargs["proxy"] is None
