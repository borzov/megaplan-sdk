"""Unit tests for HTTP client."""

from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from megaplan_sdk.exceptions import NotFoundError
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


# --- FR-C: binary download for attachments ---


async def test_get_binary_downloads_with_bearer_header(megaplan_api, base_url, access_token):
    """FR-C: get_binary joins base_url, sends Bearer, returns raw bytes."""
    route = megaplan_api.get(f"{base_url}/attach/SdfFileM_File/File/237/81/pic.png")
    route.mock(return_value=Response(200, content=b"\x89PNG-bytes"))

    async with HTTPClient(base_url, access_token=access_token) as client:
        data = await client.get_binary("/attach/SdfFileM_File/File/237/81/pic.png")

    assert data == b"\x89PNG-bytes"
    assert route.calls.last.request.headers["Authorization"] == f"Bearer {access_token}"


async def test_stream_binary_yields_chunks(megaplan_api, base_url, access_token):
    """FR-C: stream_binary exposes aiter_bytes for large files."""
    route = megaplan_api.get(f"{base_url}/attach/big.bin")
    route.mock(return_value=Response(200, content=b"A" * 1024))

    chunks: list[bytes] = []
    async with HTTPClient(base_url, access_token=access_token) as client:
        async with client.stream_binary("/attach/big.bin") as response:
            async for chunk in response.aiter_bytes():
                chunks.append(chunk)

    assert b"".join(chunks) == b"A" * 1024


async def test_get_binary_maps_errors(megaplan_api, base_url, access_token):
    """FR-C: HTTP 404 becomes NotFoundError, not a bare httpx error."""
    route = megaplan_api.get(f"{base_url}/attach/gone.png")
    route.mock(return_value=Response(404, content=b""))

    async with HTTPClient(base_url, access_token=access_token) as client:
        with pytest.raises(NotFoundError):
            await client.get_binary("/attach/gone.png")


# --- Same-origin/HTTPS policy for absolute binary URLs (security) ---


async def test_get_binary_absolute_same_origin_https_passes_through(
    megaplan_api, base_url, access_token
):
    """An absolute https:// URL matching base_url's host is followed and downloads."""
    absolute_url = f"{base_url}/attach/File/1/2/report.pdf"
    route = megaplan_api.get(absolute_url)
    route.mock(return_value=Response(200, content=b"same-origin-bytes"))

    async with HTTPClient(base_url, access_token=access_token) as client:
        data = await client.get_binary(absolute_url)

    assert data == b"same-origin-bytes"
    assert route.calls.last.request.headers["Authorization"] == f"Bearer {access_token}"


async def test_get_binary_absolute_cross_host_raises(megaplan_api, base_url, access_token):
    """A cross-host absolute URL must be rejected; no request is made (SSRF/token-leak guard)."""
    evil_url = "https://evil.example.com/attach/File/1/2/report.pdf"

    async with HTTPClient(base_url, access_token=access_token) as client:
        with pytest.raises(ValueError, match="host"):
            await client.get_binary(evil_url)

    assert not respx.calls


async def test_get_binary_absolute_http_raises_without_allow_http(
    megaplan_api, base_url, access_token
):
    """A plaintext http:// absolute URL must be rejected unless allow_http=True."""
    insecure_url = base_url.replace("https://", "http://") + "/attach/File/1/2/report.pdf"

    async with HTTPClient(base_url, access_token=access_token) as client:
        with pytest.raises(ValueError, match="HTTPS"):
            await client.get_binary(insecure_url)

    assert not respx.calls


async def test_get_binary_without_access_token_sends_no_authorization_header(
    megaplan_api, base_url
):
    """HTTPClient built without access_token must not send Authorization on binary GET."""
    route = megaplan_api.get(f"{base_url}/attach/anon.png")
    route.mock(return_value=Response(200, content=b"anon-bytes"))

    async with HTTPClient(base_url) as client:
        data = await client.get_binary("/attach/anon.png")

    assert data == b"anon-bytes"
    assert "Authorization" not in route.calls.last.request.headers
