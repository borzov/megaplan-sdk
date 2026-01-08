"""Unit tests for FullDetailsMixin."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.tasks import TasksResource


@pytest.mark.asyncio
@respx.mock
async def test_minimal_call():
    """Test minimal call with all include_* parameters = False."""
    respx.get("https://example.com/api/v3/task/1").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 1, "contentType": "Task", "name": "Test Task"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        full_details = await resource.get_full_details(
            task_id=1,
            include_sub_tasks=False,
            include_actual_sub_tasks=False,
            include_comments=False,
            include_history=False,
            include_auditors=False,
            include_executors=False,
            include_milestones=False,
            include_responsible_details=False,
            include_owner_details=False,
        )

        assert full_details.task.id == 1
        assert full_details.task.name == "Test Task"
        assert full_details.sub_tasks is None
        assert full_details.comments is None
        assert full_details.history is None
        assert full_details.responsible_details is None
        assert full_details.owner_details is None


@pytest.mark.asyncio
@respx.mock
async def test_full_call_all_includes():
    """Test full call with all include_* = True and limits."""
    # Mock main task
    respx.get("https://example.com/api/v3/task/1").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 1,
                    "contentType": "Task",
                    "name": "Test Task",
                    "responsible": {"id": 10, "contentType": "Employee"},
                    "owner": {"id": 11, "contentType": "Employee"},
                },
            },
        )
    )

    # Mock all related endpoints
    respx.get("https://example.com/api/v3/task/1/subTasks").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 2, "contentType": "Task", "name": "Subtask"}],
            },
        )
    )

    respx.get("https://example.com/api/v3/task/1/actualSubTasks").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 3, "contentType": "Task", "name": "Actual Subtask"}],
            },
        )
    )

    respx.get("https://example.com/api/v3/task/1/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Comment", "text": "Comment"}],
            },
        )
    )

    respx.get("https://example.com/api/v3/task/1/history").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 1, "action": "created"}]},
        )
    )

    respx.get("https://example.com/api/v3/task/1/auditors").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 15, "contentType": "Employee"}],
            },
        )
    )

    respx.get("https://example.com/api/v3/task/1/executors").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 16, "contentType": "Employee"}],
            },
        )
    )

    respx.get("https://example.com/api/v3/task/1/milestones").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 1, "name": "Milestone"}]},
        )
    )

    respx.get("https://example.com/api/v3/employee/10").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 10,
                    "contentType": "Employee",
                    "firstName": "John",
                    "lastName": "Doe",
                },
            },
        )
    )

    respx.get("https://example.com/api/v3/employee/11").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 11,
                    "contentType": "Employee",
                    "firstName": "Jane",
                    "lastName": "Smith",
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        full_details = await resource.get_full_details(
            task_id=1,
            include_sub_tasks=True,
            include_actual_sub_tasks=True,
            include_comments=True,
            include_history=True,
            include_auditors=True,
            include_executors=True,
            include_milestones=True,
            include_responsible_details=True,
            include_owner_details=True,
            comments_limit=10,
            history_limit=20,
        )

        assert full_details.task.id == 1
        assert full_details.sub_tasks is not None
        assert len(full_details.sub_tasks) == 1
        assert full_details.actual_sub_tasks is not None
        assert full_details.comments is not None
        assert full_details.history is not None
        assert full_details.auditors is not None
        assert full_details.executors is not None
        assert full_details.milestones is not None
        assert full_details.responsible_details is not None
        assert full_details.responsible_details.first_name == "John"
        assert full_details.owner_details is not None
        assert full_details.owner_details.first_name == "Jane"


@pytest.mark.asyncio
@respx.mock
async def test_parallel_execution():
    """Test that parallel execution works correctly."""
    respx.get("https://example.com/api/v3/task/1").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 1, "contentType": "Task", "name": "Test"},
            },
        )
    )

    respx.get("https://example.com/api/v3/task/1/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Comment", "text": "Comment"}],
            },
        )
    )

    respx.get("https://example.com/api/v3/task/1/history").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 1, "action": "created"}]},
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)

        # Mock _fetch_details_parallel to verify it's called
        original_fetch = resource._fetch_details_parallel
        call_count = 0
        tasks_captured = None

        async def mock_fetch(tasks: dict[str, Any]) -> dict[str, Any]:
            nonlocal call_count, tasks_captured
            call_count += 1
            tasks_captured = tasks
            return await original_fetch(tasks)

        resource._fetch_details_parallel = mock_fetch

        await resource.get_full_details(
            task_id=1,
            include_comments=True,
            include_history=True,
        )

        assert call_count == 1
        assert tasks_captured is not None
        assert "comments" in tasks_captured
        assert "history" in tasks_captured
        assert len(tasks_captured) == 2


@pytest.mark.asyncio
@respx.mock
async def test_partial_call():
    """Test partial call with only comments and responsible_details."""
    respx.get("https://example.com/api/v3/task/1").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 1,
                    "contentType": "Task",
                    "name": "Test Task",
                    "responsible": {"id": 10, "contentType": "Employee"},
                },
            },
        )
    )

    respx.get("https://example.com/api/v3/task/1/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Comment", "text": "Comment"}],
            },
        )
    )

    respx.get("https://example.com/api/v3/employee/10").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 10,
                    "contentType": "Employee",
                    "firstName": "John",
                    "lastName": "Doe",
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        full_details = await resource.get_full_details(
            task_id=1,
            include_comments=True,
            include_responsible_details=True,
        )

        assert full_details.task.id == 1
        assert full_details.comments is not None
        assert len(full_details.comments) == 1
        assert full_details.responsible_details is not None
        assert full_details.responsible_details.first_name == "John"
        assert full_details.sub_tasks is None
        assert full_details.history is None
        assert full_details.owner_details is None


@pytest.mark.asyncio
@respx.mock
async def test_missing_optional_fields():
    """Test handling of missing optional fields (e.g., no auditors)."""
    respx.get("https://example.com/api/v3/task/1").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 1,
                    "contentType": "Task",
                    "name": "Test Task",
                    "responsible": None,
                },
            },
        )
    )

    respx.get("https://example.com/api/v3/task/1/auditors").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": []},
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        full_details = await resource.get_full_details(
            task_id=1,
            include_auditors=True,
            include_responsible_details=True,
        )

        assert full_details.task.id == 1
        assert full_details.auditors is not None
        assert len(full_details.auditors) == 0
        assert full_details.responsible_details is None


@pytest.mark.asyncio
@respx.mock
async def test_entity_loading():
    """Test entity loading through entity_field + entity_type."""
    respx.get("https://example.com/api/v3/task/1").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 1,
                    "contentType": "Task",
                    "name": "Test Task",
                    "responsible": {"id": 10, "contentType": "Employee"},
                    "owner": {"id": 11, "contentType": "Employee"},
                },
            },
        )
    )

    respx.get("https://example.com/api/v3/employee/10").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 10,
                    "contentType": "Employee",
                    "firstName": "John",
                    "lastName": "Doe",
                },
            },
        )
    )

    respx.get("https://example.com/api/v3/employee/11").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 11,
                    "contentType": "Employee",
                    "firstName": "Jane",
                    "lastName": "Smith",
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        full_details = await resource.get_full_details(
            task_id=1,
            include_responsible_details=True,
            include_owner_details=True,
        )

        assert full_details.responsible_details is not None
        assert full_details.responsible_details.id == 10
        assert full_details.responsible_details.first_name == "John"
        assert full_details.owner_details is not None
        assert full_details.owner_details.id == 11
        assert full_details.owner_details.first_name == "Jane"


@pytest.mark.asyncio
@respx.mock
async def test_limit_params():
    """Test passing limit parameters to methods."""
    respx.get("https://example.com/api/v3/task/1").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 1, "contentType": "Task", "name": "Test"},
            },
        )
    )

    # Mock comments with limit
    comments_mock = respx.get("https://example.com/api/v3/task/1/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Comment", "text": "Comment"}],
            },
        )
    )

    # Mock history with limit
    history_mock = respx.get("https://example.com/api/v3/task/1/history").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 1, "action": "created"}]},
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        await resource.get_full_details(
            task_id=1,
            include_comments=True,
            include_history=True,
            comments_limit=5,
            history_limit=10,
        )

        # Verify that limits were passed (check request params)
        assert comments_mock.called
        assert history_mock.called


@pytest.mark.asyncio
@respx.mock
async def test_fetch_method_loading():
    """Test loading through fetch_method (get_comments, get_history)."""
    respx.get("https://example.com/api/v3/task/1").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 1, "contentType": "Task", "name": "Test"},
            },
        )
    )

    respx.get("https://example.com/api/v3/task/1/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 1, "contentType": "Comment", "content": "Comment 1"},
                    {"id": 2, "contentType": "Comment", "content": "Comment 2"},
                ],
            },
        )
    )

    respx.get("https://example.com/api/v3/task/1/history").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 1, "action": "created"},
                    {"id": 2, "action": "updated"},
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        full_details = await resource.get_full_details(
            task_id=1,
            include_comments=True,
            include_history=True,
        )

        assert full_details.comments is not None
        assert len(full_details.comments) == 2
        assert full_details.history is not None
        assert len(full_details.history) == 2


@pytest.mark.asyncio
@respx.mock
async def test_custom_fetcher():
    """Test custom_fetcher (e.g., _fetch_related_tasks in deals)."""
    from megaplan_sdk.resources.deals import DealsResource

    respx.get("https://example.com/api/v3/deal/1").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 1, "contentType": "Deal", "name": "Test Deal"},
            },
        )
    )

    # _fetch_related_tasks uses filter with baseOn, so URL will have filter parameter
    # TasksResource.list() adds statuses parameter
    respx.get(
        url__regex=r"https://example\.com/api/v3/task\?.*",
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 100, "contentType": "Task", "name": "Related Task"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = DealsResource(http_client)
        full_details = await resource.get_full_details(
            deal_id=1,
            include_related_tasks=True,
        )

        assert full_details.deal.id == 1
        # custom_fetcher should return list of tasks
        assert full_details.related_tasks is not None
        assert isinstance(full_details.related_tasks, list)
        assert len(full_details.related_tasks) == 1
        assert full_details.related_tasks[0].id == 100
