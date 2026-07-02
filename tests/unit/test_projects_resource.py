"""Unit tests for ProjectsResource."""


async def test_create_project(megaplan_api, projects):
    """Test creating a project."""
    megaplan_api.post("project", data={"id": 1, "contentType": "Project", "name": "Test"})

    project = await projects.create({"name": "Test"})

    assert project.id == 1
    assert project.name == "Test"


async def test_list_projects(megaplan_api, projects):
    """Test listing projects."""
    megaplan_api.get("project", data=[{"id": 1, "contentType": "Project", "name": "Project 1"}])

    result = await projects.list()

    assert len(result) == 1
    assert result[0].id == 1


async def test_get_project(megaplan_api, projects):
    """Test getting a project by ID."""
    megaplan_api.get("project/1", data={"id": 1, "contentType": "Project", "name": "Test"})

    project = await projects.get(1)

    assert project.id == 1


async def test_get_deals(megaplan_api, projects):
    """Test getting project deals."""
    megaplan_api.get("project/1/deals", data=[{"id": 10, "contentType": "Deal", "name": "Deal 1"}])

    deals = await projects.get_deals(1)

    assert len(deals) == 1
    assert deals[0].id == 10


async def test_get_full_details(megaplan_api, projects):
    """Test getting full project details with related entities."""
    # Mock main project with milestones field
    megaplan_api.get(
        "project/1",
        data={
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
    )

    # Mock deals
    megaplan_api.get(
        "project/1/deals", data=[{"id": 20, "contentType": "Deal", "name": "Test Deal"}]
    )

    # Mock issues
    megaplan_api.get(
        "project/1/issues", data=[{"id": 30, "contentType": "Task", "name": "Issue 1"}]
    )

    # Mock actual issues
    megaplan_api.get(
        "project/1/actualIssues",
        data=[{"id": 31, "contentType": "Task", "name": "Actual Issue"}],
    )

    # Mock comments
    megaplan_api.get(
        "project/1/comments",
        data=[{"id": 1, "contentType": "Comment", "text": "Test comment"}],
    )

    # Mock history
    megaplan_api.get("project/1/history", data=[{"id": 1, "action": "created"}])

    # Mock auditors
    megaplan_api.get("project/1/auditors", data=[{"id": 15, "contentType": "Employee"}])

    # Mock executors
    megaplan_api.get("project/1/executors", data=[{"id": 16, "contentType": "Employee"}])

    # Mock milestones
    megaplan_api.get("project/1/milestones", data=[{"id": 1, "name": "Milestone 1"}])

    # Mock responsible employee
    megaplan_api.get(
        "employee/10",
        data={"id": 10, "contentType": "Employee", "firstName": "John", "lastName": "Doe"},
    )

    # Mock owner employee
    megaplan_api.get(
        "employee/11",
        data={"id": 11, "contentType": "Employee", "firstName": "Jane", "lastName": "Smith"},
    )

    full_details = await projects.get_full_details(
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


async def test_get_milestones(megaplan_api, projects):
    """Test getting project milestones via get_full_details."""
    # Mock project with milestones field
    megaplan_api.get(
        "project/1",
        data={
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
    )

    milestones = await projects.get_milestones(project_id=1)

    assert len(milestones) == 1
    assert milestones[0].id == 1
    assert milestones[0].name == "Phase 1"
    assert milestones[0].type == "report"


async def test_get_milestones_500_error(megaplan_api, projects):
    """Test handling 500 error when getting milestones via get_full_details."""
    # Mock project endpoint returning 500 error
    megaplan_api.get(
        "project/1",
        status=500,
        json={"meta": {"status": 500, "errors": ["Internal Server Error"]}},
    )

    # Should return empty list instead of raising exception
    milestones = await projects.get_milestones(project_id=1)

    assert milestones == []


async def test_add_milestone_dict(megaplan_api, projects):
    """Test adding milestone using dict."""
    megaplan_api.post(
        "project/1/milestones",
        data={
            "id": 1,
            "contentType": "Milestone",
            "name": "Phase 1",
            "description": "First phase milestone",
            "type": "report",
            "date": "2026-02-01T10:00:00Z",
        },
    )

    milestone = await projects.add_milestone(
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


async def test_add_milestone_model(megaplan_api, projects):
    """Test adding milestone using Milestone model."""
    from megaplan_sdk.models.milestone import Milestone

    megaplan_api.post(
        "project/1/milestones",
        data={
            "id": 2,
            "contentType": "Milestone",
            "name": "Release 1.0",
            "description": "Release milestone",
            "type": "reminder",
            "date": "2026-03-01T10:00:00Z",
        },
    )

    milestone_data = Milestone(
        name="Release 1.0",
        description="Release milestone",
        type="reminder",
        date="2026-03-01T10:00:00Z",
    )
    milestone = await projects.add_milestone(project_id=1, milestone_data=milestone_data)

    assert milestone.id == 2
    assert milestone.name == "Release 1.0"
    assert milestone.description == "Release milestone"
    assert milestone.type == "reminder"


async def test_get_available_parents(megaplan_api, projects):
    """Test getting available parent projects for a new project."""
    megaplan_api.get(
        "project/availableParents",
        data=[
            {"id": 1, "contentType": "Project", "name": "Parent Project 1"},
            {"id": 2, "contentType": "Project", "name": "Parent Project 2"},
        ],
    )

    parents = await projects.get_available_parents()

    assert len(parents) == 2
    assert parents[0].id == 1
    assert parents[0].name == "Parent Project 1"
    assert parents[1].id == 2
    assert parents[1].name == "Parent Project 2"


async def test_get_available_parents_with_limit(megaplan_api, projects):
    """Test getting available parents with limit parameter."""
    megaplan_api.get(
        "project/availableParents",
        data=[
            {"id": 1, "contentType": "Project", "name": "Parent Project 1"},
        ],
    )

    parents = await projects.get_available_parents(limit=5)

    assert len(parents) == 1
    assert parents[0].id == 1


async def test_get_available_parents_with_template_filter(megaplan_api, projects):
    """Test getting available parents with isTemplate filter."""
    megaplan_api.get(
        "project/availableParents",
        data=[
            {"id": 1, "contentType": "Project", "name": "Regular Project"},
        ],
    )

    parents = await projects.get_available_parents(is_template=False)

    assert len(parents) == 1
    assert parents[0].name == "Regular Project"


async def test_get_available_parents_for_project(megaplan_api, projects):
    """Test getting available parents for a specific project."""
    megaplan_api.get(
        "project/123/availableParents",
        data=[
            {"id": 10, "contentType": "Project", "name": "Project A"},
            {"id": 20, "contentType": "Project", "name": "Project B"},
        ],
    )

    parents = await projects.get_available_parents_for(123)

    assert len(parents) == 2
    assert parents[0].id == 10
    assert parents[0].name == "Project A"
    assert parents[1].id == 20
    assert parents[1].name == "Project B"


async def test_get_available_parents_for_project_with_params(megaplan_api, projects):
    """Test getting available parents for project with all parameters."""
    megaplan_api.get(
        "project/456/availableParents",
        data=[{"id": 1, "contentType": "Project", "name": "Parent"}],
    )

    parents = await projects.get_available_parents_for(project_id=456, limit=10, is_template=False)

    assert len(parents) == 1


async def test_get_available_parents_empty_result(megaplan_api, projects):
    """Test getting available parents when none available."""
    megaplan_api.get("project/availableParents", data=[])

    parents = await projects.get_available_parents()

    assert len(parents) == 0
    assert parents == []


async def test_get_all_participants(megaplan_api, projects):
    """Test getting all participants of a project."""
    megaplan_api.get(
        "project/123/allParticipants",
        data=[
            {"id": 1, "contentType": "Employee", "firstName": "John", "lastName": "Doe"},
            {"id": 2, "contentType": "Employee", "firstName": "Jane", "lastName": "Smith"},
        ],
    )

    participants = await projects.get_all_participants(project_id=123)

    assert len(participants) == 2
    assert participants[0].id == 1
    assert participants[0].content_type == "Employee"
    assert participants[0].first_name == "John"


async def test_get_all_participants_mixed_types(megaplan_api, projects):
    """Test getting all participants with mixed types."""
    megaplan_api.get(
        "project/456/allParticipants",
        data=[
            {"id": 1, "contentType": "Employee", "firstName": "John"},
            {"id": 2, "contentType": "ContractorHuman", "firstName": "Bob"},
            {"id": 3, "contentType": "Group", "name": "Team A"},
        ],
    )

    participants = await projects.get_all_participants(project_id=456)

    assert len(participants) == 3

    from megaplan_sdk.models.contractor import ContractorHuman
    from megaplan_sdk.models.employee import Employee
    from megaplan_sdk.models.group import Group

    assert isinstance(participants[0], Employee)
    assert isinstance(participants[1], ContractorHuman)
    assert isinstance(participants[2], Group)


async def test_get_all_participants_empty(megaplan_api, projects):
    """Test getting all participants when project has no participants."""
    megaplan_api.get("project/789/allParticipants", data=[])

    participants = await projects.get_all_participants(project_id=789)

    assert len(participants) == 0


async def test_list_projects_with_filter(megaplan_api, projects):
    """Test listing projects with a filter parameter."""
    megaplan_api.get(
        "project", data=[{"id": 5, "contentType": "Project", "name": "Filtered Project"}]
    )

    from megaplan_sdk.filter_builder import ProjectFilterBuilder

    f = ProjectFilterBuilder().field("name").contains("Filtered").build()
    result = await projects.list(filter=f)

    assert len(result) == 1
    assert result[0].id == 5
    assert result[0].name == "Filtered Project"


async def test_list_projects_filter_none(megaplan_api, projects):
    """Test that list() works without filter (backward compat)."""
    megaplan_api.get("project", data=[{"id": 1, "contentType": "Project", "name": "Project A"}])

    result = await projects.list()

    assert len(result) == 1
    assert result[0].name == "Project A"
