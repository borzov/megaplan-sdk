"""Integration tests for MegaplanClient."""

import os

import pytest
import respx
from httpx import Response

from megaplan_sdk.client import MegaplanClient


@pytest.mark.asyncio
@respx.mock
async def test_full_workflow():
    """Test full workflow with mocked HTTP."""
    respx.post("https://example.com/api/v3/auth/access_token").mock(
        return_value=Response(
            200,
            json={
                "access_token": "test_token",
                "expires_in": 3600,
                "token_type": "bearer",
                "refresh_token": "refresh",
            },
        )
    )

    respx.get(url__regex=r"https://example\.com/api/v3/task\?.*").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Task", "name": "Test Task"}],
            },
        )
    )

    respx.get("https://example.com/api/v3/project").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Project", "name": "Test Project"}],
            },
        )
    )

    async with MegaplanClient(
        base_url="https://example.com",
        username="user@example.com",
        password="password",
    ) as client:
        tasks = await client.tasks.list(limit=10)
        assert len(tasks) == 1

        projects = await client.projects.list()
        assert len(projects) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_login():
    """Test real login with env vars (requires MEGAPLAN_URL, MEGAPLAN_USERNAME, MEGAPLAN_PASSWORD)."""
    base_url = os.getenv("MEGAPLAN_URL")
    username = os.getenv("MEGAPLAN_USERNAME")
    password = os.getenv("MEGAPLAN_PASSWORD")

    if not all([base_url, username, password]):
        pytest.skip("Missing MEGAPLAN_URL, MEGAPLAN_USERNAME, or MEGAPLAN_PASSWORD env vars")

    async with MegaplanClient(
        base_url=base_url,
        username=username,
        password=password,
    ) as client:
        # Verify authentication worked
        assert client.auth.get_access_token() is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_list_tasks():
    """Test real list() tasks with actual API (requires env vars)."""
    base_url = os.getenv("MEGAPLAN_URL")
    username = os.getenv("MEGAPLAN_USERNAME")
    password = os.getenv("MEGAPLAN_PASSWORD")

    if not all([base_url, username, password]):
        pytest.skip("Missing MEGAPLAN_URL, MEGAPLAN_USERNAME, or MEGAPLAN_PASSWORD env vars")

    async with MegaplanClient(
        base_url=base_url,
        username=username,
        password=password,
    ) as client:
        tasks = await client.tasks.list(limit=10)

        # Should return list (may be empty)
        assert isinstance(tasks, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_get_task():
    """Test real get() task by ID (requires env vars and existing task ID)."""
    base_url = os.getenv("MEGAPLAN_URL")
    username = os.getenv("MEGAPLAN_USERNAME")
    password = os.getenv("MEGAPLAN_PASSWORD")
    test_task_id = os.getenv("MEGAPLAN_TEST_TASK_ID")

    if not all([base_url, username, password]):
        pytest.skip("Missing MEGAPLAN_URL, MEGAPLAN_USERNAME, or MEGAPLAN_PASSWORD env vars")

    if not test_task_id:
        pytest.skip("Missing MEGAPLAN_TEST_TASK_ID env var")

    async with MegaplanClient(
        base_url=base_url,
        username=username,
        password=password,
    ) as client:
        task = await client.tasks.get(int(test_task_id))

        assert task.id == int(test_task_id)
        assert task.content_type == "Task"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_cache_integration():
    """Test cache integration in real conditions (requires env vars)."""
    base_url = os.getenv("MEGAPLAN_URL")
    username = os.getenv("MEGAPLAN_USERNAME")
    password = os.getenv("MEGAPLAN_PASSWORD")

    if not all([base_url, username, password]):
        pytest.skip("Missing MEGAPLAN_URL, MEGAPLAN_USERNAME, or MEGAPLAN_PASSWORD env vars")

    async with MegaplanClient(
        base_url=base_url,
        username=username,
        password=password,
        cache_ttl=300,
        cache_max_size=100,
    ) as client:
        # First request - should fetch from API
        tasks1 = await client.tasks.list(limit=5)

        # Second request - should use cache if same query
        tasks2 = await client.tasks.list(limit=5)

        # Both should return same results
        assert len(tasks1) == len(tasks2)

        # Check cache stats
        stats = client.cache.stats() if client.cache else None
        if stats:
            assert stats["size"] >= 0
            assert "types" in stats
