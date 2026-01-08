"""Unit tests for error handling."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from megaplan_sdk.exceptions import (
    RateLimitError,
    ServerError,
    ValidationError,
)
from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.base import BaseResource
from megaplan_sdk.resources.tasks import TasksResource


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_error():
    """Test RateLimitError (429) with retry-after header parsing."""
    # First request - rate limited
    respx.get("https://example.com/api/v3/task").mock(
        side_effect=[
            Response(429, headers={"Retry-After": "5"}),
            Response(
                200,
                json={
                    "meta": {"status": 200},
                    "data": [{"id": 1, "contentType": "Task", "name": "Task 1"}],
                },
            ),
        ]
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        # Should retry after 5 seconds and succeed
        tasks = await resource.list()

        assert len(tasks) == 1
        assert tasks[0].id == 1


@pytest.mark.asyncio
@respx.mock
async def test_validation_error_parsing():
    """Test ValidationError (422) parsing errors from response."""
    respx.post("https://example.com/api/v3/task").mock(
        return_value=Response(
            422,
            json={
                "meta": {
                    "status": 422,
                    "errors": [
                        {"field": "name", "message": "Name is required"},
                        {"field": "status", "message": "Invalid status"},
                    ],
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)

        with pytest.raises(ValidationError) as exc_info:
            await resource.create({"invalid": "data"})

        assert exc_info.value.status_code == 422
        assert len(exc_info.value.errors) == 2
        assert exc_info.value.errors[0]["field"] == "name"
        assert exc_info.value.errors[0]["message"] == "Name is required"


@pytest.mark.asyncio
@respx.mock
async def test_server_error_max_retries():
    """Test ServerError (5xx) with max_retries and exponential backoff."""
    # Mock 3 server errors, then success
    respx.get("https://example.com/api/v3/task").mock(
        side_effect=[
            Response(500),
            Response(500),
            Response(500),
            Response(
                200,
                json={
                    "meta": {"status": 200},
                    "data": [{"id": 1, "contentType": "Task", "name": "Task 1"}],
                },
            ),
        ]
    )

    async with HTTPClient(
        "https://example.com", access_token="token", max_retries=3
    ) as http_client:
        resource = TasksResource(http_client)

        # Should retry 3 times with exponential backoff, then succeed
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            tasks = await resource.list()

            assert len(tasks) == 1
            # Should have slept for backoff (2^0, 2^1, 2^2 seconds)
            assert mock_sleep.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_server_error_exceeds_max_retries():
    """Test ServerError when max_retries is exceeded."""
    # Mock 4 server errors (more than max_retries=3)
    respx.get("https://example.com/api/v3/task").mock(
        side_effect=[
            Response(500),
            Response(500),
            Response(500),
            Response(500),
        ]
    )

    async with HTTPClient(
        "https://example.com", access_token="token", max_retries=3
    ) as http_client:
        resource = TasksResource(http_client)

        with pytest.raises(ServerError) as exc_info:
            await resource.list()

        assert exc_info.value.status_code == 500


@pytest.mark.asyncio
@respx.mock
async def test_fetch_details_parallel_partial_failure():
    """Test _fetch_details_parallel handles partial failures correctly."""
    from megaplan_sdk.resources.base import BaseResource

    class TestResource(BaseResource):
        pass

    async def failing_task():
        raise ValueError("Test error")

    async def success_task():
        return "success"

    async def another_success_task():
        return "another success"

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TestResource(http_client)

        tasks = {
            "failing": failing_task(),
            "success": success_task(),
            "another": another_success_task(),
        }

        results = await resource._fetch_details_parallel(tasks)

        # Failing task should result in None
        assert results["failing"] is None
        # Other tasks should succeed
        assert results["success"] == "success"
        assert results["another"] == "another success"


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_error_retry_after_date():
    """Test RateLimitError with Retry-After as date string (defaults to 60s)."""
    respx.get("https://example.com/api/v3/task").mock(
        side_effect=[
            Response(429, headers={"Retry-After": "Wed, 21 Oct 2025 07:28:00 GMT"}),
            Response(
                200,
                json={
                    "meta": {"status": 200},
                    "data": [{"id": 1, "contentType": "Task", "name": "Task 1"}],
                },
            ),
        ]
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)

        # Should default to 60s wait when Retry-After is date string
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            tasks = await resource.list()

            assert len(tasks) == 1
            # Should have slept (defaults to 60s for date strings)
            assert mock_sleep.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_server_error_with_retry_after_header():
    """Test ServerError with Retry-After header."""
    respx.get("https://example.com/api/v3/task").mock(
        side_effect=[
            Response(503, headers={"Retry-After": "10"}),
            Response(
                200,
                json={
                    "meta": {"status": 200},
                    "data": [{"id": 1, "contentType": "Task", "name": "Task 1"}],
                },
            ),
        ]
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            tasks = await resource.list()

            assert len(tasks) == 1
            # Should have slept for 10 seconds (from Retry-After header)
            assert mock_sleep.call_count == 1
            # Verify sleep was called with 10
            mock_sleep.assert_called_with(10)
