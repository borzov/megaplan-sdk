"""Unit tests for ProjectsResource."""

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.projects import ProjectsResource


@pytest.mark.asyncio
@respx.mock
async def test_create_project():
    """Test creating a project."""
    respx.post("https://example.com/api/v3/project").mock(
        return_value=Response(
            200, json={"meta": {"status": 200}, "data": {"id": 1, "contentType": "Project", "name": "Test"}}
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        project = await resource.create({"name": "Test"})

        assert project.id == 1
        assert project.name == "Test"


@pytest.mark.asyncio
@respx.mock
async def test_list_projects():
    """Test listing projects."""
    respx.get("https://example.com/api/v3/project").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Project", "name": "Project 1"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        projects = await resource.list()

        assert len(projects) == 1
        assert projects[0].id == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_project():
    """Test getting a project by ID."""
    respx.get("https://example.com/api/v3/project/1").mock(
        return_value=Response(
            200, json={"meta": {"status": 200}, "data": {"id": 1, "contentType": "Project", "name": "Test"}}
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        project = await resource.get(1)

        assert project.id == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_deals():
    """Test getting project deals."""
    respx.get("https://example.com/api/v3/project/1/deals").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 10, "contentType": "Deal", "name": "Deal 1"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        deals = await resource.get_deals(1)

        assert len(deals) == 1
        assert deals[0].id == 10


@pytest.mark.asyncio
@respx.mock
async def test_get_full_details():
    """Test getting full project details with related entities."""
    # Mock main project
    respx.get("https://example.com/api/v3/project/1").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 1,
                    "contentType": "Project",
                    "name": "Test Project",
                    "responsible": {"id": 10, "contentType": "Employee"},
                    "owner": {"id": 11, "contentType": "Employee"},
                },
            },
        )
    )

    # Mock deals
    respx.get("https://example.com/api/v3/project/1/deals").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 20, "contentType": "Deal", "name": "Test Deal"}],
            },
        )
    )

    # Mock issues
    respx.get("https://example.com/api/v3/project/1/issues").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 30, "contentType": "Task", "name": "Issue 1"}],
            },
        )
    )

    # Mock actual issues
    respx.get("https://example.com/api/v3/project/1/actualIssues").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 31, "contentType": "Task", "name": "Actual Issue"}],
            },
        )
    )

    # Mock comments
    respx.get("https://example.com/api/v3/project/1/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Comment", "text": "Test comment"}],
            },
        )
    )

    # Mock history
    respx.get("https://example.com/api/v3/project/1/history").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 1, "action": "created"}]},
        )
    )

    # Mock auditors
    respx.get("https://example.com/api/v3/project/1/auditors").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 15, "contentType": "Employee"}]},
        )
    )

    # Mock executors
    respx.get("https://example.com/api/v3/project/1/executors").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 16, "contentType": "Employee"}]},
        )
    )

    # Mock milestones
    respx.get("https://example.com/api/v3/project/1/milestones").mock(
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
        resource = ProjectsResource(http_client)
        full_details = await resource.get_full_details(
            project_id=1,
            include_deals=True,
            include_issues=True,
            include_actual_issues=True,
            include_comments=True,
            include_history=True,
            include_auditors=True,
            include_executors=True,
            include_milestones=True,
            include_responsible_details=True,
            include_owner_details=True,
        )

        # Check main project
        assert full_details.project.id == 1
        assert full_details.project.name == "Test Project"

        # Check related data
        assert full_details.deals is not None
        assert len(full_details.deals) == 1
        assert full_details.deals[0].name == "Test Deal"

        assert full_details.issues is not None
        assert len(full_details.issues) == 1

        assert full_details.actual_issues is not None
        assert len(full_details.actual_issues) == 1

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
