"""Unit tests for error handling."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import Response

from megaplan_sdk.exceptions import ServerError, ValidationError
from megaplan_sdk.resources.base import BaseResource


async def test_rate_limit_error(megaplan_api, tasks):
    """Test RateLimitError (429) with retry-after header parsing."""
    # First request - rate limited
    route = megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/task")
    route.mock(
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

    # Should retry after 5 seconds and succeed
    result = await tasks.list()

    assert len(result) == 1
    assert result[0].id == 1


async def test_validation_error_parsing(megaplan_api, tasks):
    """Test ValidationError (422) parsing errors from response."""
    megaplan_api.post(
        "task",
        status=422,
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

    with pytest.raises(ValidationError) as exc_info:
        await tasks.create({"invalid": "data"})

    assert exc_info.value.status_code == 422
    assert len(exc_info.value.errors) == 2
    assert exc_info.value.errors[0]["field"] == "name"
    assert exc_info.value.errors[0]["message"] == "Name is required"


async def test_server_error_max_retries(megaplan_api, tasks):
    """Test ServerError (5xx) with max_retries and exponential backoff."""
    # Mock 3 server errors, then success
    route = megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/task")
    route.mock(
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

    # Should retry 3 times with exponential backoff, then succeed
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await tasks.list()

        assert len(result) == 1
        # Should have slept for backoff (2^0, 2^1, 2^2 seconds)
        assert mock_sleep.call_count == 3


async def test_server_error_exceeds_max_retries(megaplan_api, tasks):
    """Test ServerError when max_retries is exceeded."""
    # Mock 4 server errors (more than max_retries=3)
    route = megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/task")
    route.mock(
        side_effect=[
            Response(500),
            Response(500),
            Response(500),
            Response(500),
        ]
    )

    with pytest.raises(ServerError) as exc_info:
        await tasks.list()

    assert exc_info.value.status_code == 500


async def test_fetch_details_parallel_partial_failure(http_client):
    """Test _fetch_details_parallel handles partial failures correctly."""

    class TestResource(BaseResource):
        pass

    async def failing_task():
        raise ValueError("Test error")

    async def success_task():
        return "success"

    async def another_success_task():
        return "another success"

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


async def test_rate_limit_error_retry_after_date(megaplan_api, tasks):
    """Test RateLimitError with Retry-After as date string (defaults to 60s)."""
    route = megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/task")
    route.mock(
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

    # Should default to 60s wait when Retry-After is date string
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await tasks.list()

        assert len(result) == 1
        # Should have slept (defaults to 60s for date strings)
        assert mock_sleep.call_count == 1


async def test_server_error_with_retry_after_header(megaplan_api, tasks):
    """Test ServerError with Retry-After header."""
    route = megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/task")
    route.mock(
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

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await tasks.list()

        assert len(result) == 1
        # Should have slept for 10 seconds (from Retry-After header)
        assert mock_sleep.call_count == 1
        # Verify sleep was called with 10
        mock_sleep.assert_called_with(10)
