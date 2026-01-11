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
    # Mock main task with milestones field
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
                    "milestones": [
                        {
                            "id": 100,
                            "contentType": "Milestone",
                            "name": "Test Milestone",
                            "type": "report",
                            "date": "2026-02-01T10:00:00Z",
                        }
                    ],
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


@pytest.mark.asyncio
@respx.mock
async def test_get_milestones():
    """Test getting task milestones via get_full_details."""
    # Mock task with milestones field
    respx.get(url__regex=r"https://example\.com/api/v3/task/1\?.*").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 1,
                    "contentType": "Task",
                    "name": "Test Task",
                    "milestones": [
                        {
                            "id": 1,
                            "contentType": "Milestone",
                            "name": "Release 1.0",
                            "description": "Release milestone",
                            "type": "report",
                            "date": "2026-02-01T10:00:00Z",
                        }
                    ],
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        milestones = await resource.get_milestones(task_id=1)

        assert len(milestones) == 1
        assert milestones[0].id == 1
        assert milestones[0].name == "Release 1.0"
        assert milestones[0].type == "report"


@pytest.mark.asyncio
@respx.mock
async def test_get_milestones_500_error():
    """Test handling 500 error when getting milestones via get_full_details."""
    from megaplan_sdk.exceptions import ServerError

    # Mock task endpoint returning 500 error
    respx.get(url__regex=r"https://example\.com/api/v3/task/1\?.*").mock(
        return_value=Response(500, json={"meta": {"status": 500, "errors": ["Internal Server Error"]}})
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        # Should return empty list instead of raising exception
        milestones = await resource.get_milestones(task_id=1)

        assert milestones == []


@pytest.mark.asyncio
@respx.mock
async def test_add_milestone_dict():
    """Test adding milestone using dict."""
    respx.post("https://example.com/api/v3/task/1/milestones").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 1,
                    "contentType": "Milestone",
                    "name": "Release 1.0",
                    "description": "Release milestone",
                    "type": "report",
                    "date": "2026-02-01T10:00:00Z",
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        milestone = await resource.add_milestone(
            task_id=1,
            milestone_data={
                "name": "Release 1.0",
                "description": "Release milestone",
                "type": "report",
                "date": "2026-02-01T10:00:00Z",
            },
        )

        assert milestone.id == 1
        assert milestone.name == "Release 1.0"
        assert milestone.description == "Release milestone"
        assert milestone.type == "report"


@pytest.mark.asyncio
@respx.mock
async def test_add_milestone_model():
    """Test adding milestone using Milestone model."""
    from megaplan_sdk.models.milestone import Milestone

    respx.post("https://example.com/api/v3/task/1/milestones").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 2,
                    "contentType": "Milestone",
                    "name": "Phase 1",
                    "description": "First phase milestone",
                    "type": "reminder",
                    "date": "2026-03-01T10:00:00Z",
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        milestone_data = Milestone(
            name="Phase 1",
            description="First phase milestone",
            type="reminder",
            date="2026-03-01T10:00:00Z",
        )
        milestone = await resource.add_milestone(task_id=1, milestone_data=milestone_data)

        assert milestone.id == 2
        assert milestone.name == "Phase 1"
        assert milestone.description == "First phase milestone"
        assert milestone.type == "reminder"
