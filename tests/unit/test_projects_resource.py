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
    # Mock main project with milestones field
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


@pytest.mark.asyncio
@respx.mock
async def test_get_milestones():
    """Test getting project milestones via get_full_details."""
    # Mock project with milestones field
    respx.get(url__regex=r"https://example\.com/api/v3/project/1\?.*").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 1,
                    "contentType": "Project",
                    "name": "Test Project",
                    "milestones": [
                        {
                            "id": 1,
                            "contentType": "Milestone",
                            "name": "Phase 1",
                            "description": "First phase milestone",
                            "type": "report",
                            "date": "2026-02-01T10:00:00Z",
                        }
                    ],
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        milestones = await resource.get_milestones(project_id=1)

        assert len(milestones) == 1
        assert milestones[0].id == 1
        assert milestones[0].name == "Phase 1"
        assert milestones[0].type == "report"


@pytest.mark.asyncio
@respx.mock
async def test_get_milestones_500_error():
    """Test handling 500 error when getting milestones via get_full_details."""
    # Mock project endpoint returning 500 error
    respx.get(url__regex=r"https://example\.com/api/v3/project/1\?.*").mock(
        return_value=Response(500, json={"meta": {"status": 500, "errors": ["Internal Server Error"]}})
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        # Should return empty list instead of raising exception
        milestones = await resource.get_milestones(project_id=1)

        assert milestones == []


@pytest.mark.asyncio
@respx.mock
async def test_add_milestone_dict():
    """Test adding milestone using dict."""
    respx.post("https://example.com/api/v3/project/1/milestones").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 1,
                    "contentType": "Milestone",
                    "name": "Phase 1",
                    "description": "First phase milestone",
                    "type": "report",
                    "date": "2026-02-01T10:00:00Z",
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        milestone = await resource.add_milestone(
            project_id=1,
            milestone_data={
                "name": "Phase 1",
                "description": "First phase milestone",
                "type": "report",
                "date": "2026-02-01T10:00:00Z",
            },
        )

        assert milestone.id == 1
        assert milestone.name == "Phase 1"
        assert milestone.description == "First phase milestone"
        assert milestone.type == "report"


@pytest.mark.asyncio
@respx.mock
async def test_add_milestone_model():
    """Test adding milestone using Milestone model."""
    from megaplan_sdk.models.milestone import Milestone

    respx.post("https://example.com/api/v3/project/1/milestones").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 2,
                    "contentType": "Milestone",
                    "name": "Release 1.0",
                    "description": "Release milestone",
                    "type": "reminder",
                    "date": "2026-03-01T10:00:00Z",
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        milestone_data = Milestone(
            name="Release 1.0",
            description="Release milestone",
            type="reminder",
            date="2026-03-01T10:00:00Z",
        )
        milestone = await resource.add_milestone(project_id=1, milestone_data=milestone_data)

        assert milestone.id == 2
        assert milestone.name == "Release 1.0"
        assert milestone.description == "Release milestone"
        assert milestone.type == "reminder"


@pytest.mark.asyncio
@respx.mock
async def test_get_available_parents():
    """Test getting available parent projects for a new project."""
    respx.get("https://example.com/api/v3/project/availableParents").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 1, "contentType": "Project", "name": "Parent Project 1"},
                    {"id": 2, "contentType": "Project", "name": "Parent Project 2"},
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        parents = await resource.get_available_parents()

        assert len(parents) == 2
        assert parents[0].id == 1
        assert parents[0].name == "Parent Project 1"
        assert parents[1].id == 2
        assert parents[1].name == "Parent Project 2"


@pytest.mark.asyncio
@respx.mock
async def test_get_available_parents_with_limit():
    """Test getting available parents with limit parameter."""
    respx.get("https://example.com/api/v3/project/availableParents?{%22limit%22:%205}").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 1, "contentType": "Project", "name": "Parent Project 1"},
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        parents = await resource.get_available_parents(limit=5)

        assert len(parents) == 1
        assert parents[0].id == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_available_parents_with_template_filter():
    """Test getting available parents with isTemplate filter."""
    respx.get(
        "https://example.com/api/v3/project/availableParents?{%22isTemplate%22:%20false}"
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 1, "contentType": "Project", "name": "Regular Project"},
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        parents = await resource.get_available_parents(is_template=False)

        assert len(parents) == 1
        assert parents[0].name == "Regular Project"


@pytest.mark.asyncio
@respx.mock
async def test_get_available_parents_for_project():
    """Test getting available parents for a specific project."""
    respx.get("https://example.com/api/v3/project/123/availableParents").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 10, "contentType": "Project", "name": "Project A"},
                    {"id": 20, "contentType": "Project", "name": "Project B"},
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        parents = await resource.get_available_parents_for(123)

        assert len(parents) == 2
        assert parents[0].id == 10
        assert parents[0].name == "Project A"
        assert parents[1].id == 20
        assert parents[1].name == "Project B"


@pytest.mark.asyncio
@respx.mock
async def test_get_available_parents_for_project_with_params():
    """Test getting available parents for project with all parameters."""
    respx.get(
        "https://example.com/api/v3/project/456/availableParents?"
        "{%22limit%22:%2010,%20%22isTemplate%22:%20false}"
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Project", "name": "Parent"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        parents = await resource.get_available_parents_for(
            project_id=456, limit=10, is_template=False
        )

        assert len(parents) == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_available_parents_empty_result():
    """Test getting available parents when none available."""
    respx.get("https://example.com/api/v3/project/availableParents").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": []},
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ProjectsResource(http_client)
        parents = await resource.get_available_parents()

        assert len(parents) == 0
        assert parents == []
