"""Unit tests for TasksResource."""

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.tasks import TasksResource


@pytest.mark.asyncio
@respx.mock
async def test_create_task():
    """Test creating a task."""
    respx.post("https://example.com/api/v3/task").mock(
        return_value=Response(
            200, json={"meta": {"status": 200}, "data": {"id": 1, "contentType": "Task", "name": "Test"}}
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        task = await resource.create({"name": "Test"})

        assert task.id == 1
        assert task.name == "Test"


@pytest.mark.asyncio
@respx.mock
async def test_list_tasks():
    """Test listing tasks."""
    # httpx URL-encodes the JSON query params
    # _build_list_params now filters None values from extra_params
    # So statuses=None won't be included in URL
    respx.get("https://example.com/api/v3/task?{%22limit%22:%2010}").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Task", "name": "Task 1"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = await resource.list(limit=10)

        assert len(tasks) == 1
        assert tasks[0].id == 1


@pytest.mark.asyncio
@respx.mock
async def test_list_tasks_with_q():
    """Test listing tasks with q parameter."""
    # q parameter is included in params via extra_params
    # None values are filtered, so statuses=None won't be in URL
    respx.get("https://example.com/api/v3/task?{%22limit%22:%2010,%20%22q%22:%20%22test%22}").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Task", "name": "Test task"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = await resource.list(limit=10, q="test")

        assert len(tasks) == 1
        assert tasks[0].id == 1
        assert tasks[0].name == "Test task"


@pytest.mark.asyncio
@respx.mock
async def test_get_task():
    """Test getting a task by ID."""
    respx.get("https://example.com/api/v3/task/1").mock(
        return_value=Response(
            200, json={"meta": {"status": 200}, "data": {"id": 1, "contentType": "Task", "name": "Test"}}
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        task = await resource.get(1)

        assert task.id == 1
        assert task.name == "Test"


@pytest.mark.asyncio
@respx.mock
async def test_update_task():
    """Test updating a task."""
    respx.post("https://example.com/api/v3/task/1").mock(
        return_value=Response(
            200, json={"meta": {"status": 200}, "data": {"id": 1, "contentType": "Task", "name": "Updated"}}
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        task = await resource.update(1, {"name": "Updated"})

        assert task.name == "Updated"


@pytest.mark.asyncio
@respx.mock
async def test_delete_task():
    """Test deleting a task."""
    respx.delete("https://example.com/api/v3/task/1").mock(
        return_value=Response(200, json={"meta": {"status": 200}})
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        await resource.delete(1)


@pytest.mark.asyncio
@respx.mock
async def test_get_sub_tasks():
    """Test getting subtasks."""
    respx.get("https://example.com/api/v3/task/1/subTasks").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 2, "contentType": "Task", "name": "Subtask"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        subtasks = await resource.get_sub_tasks(1)

        assert len(subtasks) == 1
        assert subtasks[0].id == 2


@pytest.mark.asyncio
@respx.mock
async def test_get_full_details():
    """Test getting full task details with related entities."""
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

    # Mock subtasks
    respx.get("https://example.com/api/v3/task/1/subTasks").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 2, "contentType": "Task", "name": "Subtask 1"}],
            },
        )
    )

    # Mock actual subtasks
    respx.get("https://example.com/api/v3/task/1/actualSubTasks").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 3, "contentType": "Task", "name": "Actual Subtask"}],
            },
        )
    )

    # Mock comments
    respx.get("https://example.com/api/v3/task/1/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Comment", "text": "Test comment"}],
            },
        )
    )

    # Mock history
    respx.get("https://example.com/api/v3/task/1/history").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 1, "action": "created"}]},
        )
    )

    # Mock auditors
    respx.get("https://example.com/api/v3/task/1/auditors").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 15, "contentType": "Employee"}]},
        )
    )

    # Mock executors
    respx.get("https://example.com/api/v3/task/1/executors").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 16, "contentType": "Employee"}]},
        )
    )

    # Mock milestones
    respx.get("https://example.com/api/v3/task/1/milestones").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 1, "name": "Milestone 1"}]},
        )
    )

    # Mock responsible employee
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

    # Mock owner employee
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
        )

        # Check main task
        assert full_details.task.id == 1
        assert full_details.task.name == "Test Task"

        # Check related data
        assert full_details.sub_tasks is not None
        assert len(full_details.sub_tasks) == 1
        assert full_details.sub_tasks[0].name == "Subtask 1"

        assert full_details.actual_sub_tasks is not None
        assert len(full_details.actual_sub_tasks) == 1

        assert full_details.comments is not None
        assert len(full_details.comments) == 1

        assert full_details.history is not None
        assert len(full_details.history) == 1

        assert full_details.auditors is not None
        assert len(full_details.auditors) == 1

        assert full_details.executors is not None
        assert len(full_details.executors) == 1

        assert full_details.milestones is not None
        assert len(full_details.milestones) == 1

        assert full_details.responsible_details is not None
        assert full_details.responsible_details.first_name == "John"

        assert full_details.owner_details is not None
        assert full_details.owner_details.first_name == "Jane"
