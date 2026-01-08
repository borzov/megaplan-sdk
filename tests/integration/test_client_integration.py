"""Integration tests for MegaplanClient."""

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
