"""Unit tests for expand on list endpoints (replace mode since 0.6.0, #BUG-2)."""

from megaplan_sdk.cache import EntityCache
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.resources.tasks import TasksResource

JOHN = {"id": 10, "contentType": "Employee", "firstName": "John", "lastName": "Doe"}
JANE = {"id": 11, "contentType": "Employee", "firstName": "Jane", "lastName": "Smith"}


async def test_expand_valid_fields(megaplan_api, deals):
    """Test expand with valid fields."""
    megaplan_api.get(
        "deal",
        data=[
            {
                "id": 1,
                "contentType": "Deal",
                "name": "Deal 1",
                "manager": {"id": 10, "contentType": "Employee"},
                "contractor": {"id": 20, "contentType": "Contractor"},
            },
        ],
    )
    megaplan_api.get("employee/10", data=JOHN)
    megaplan_api.get(
        "contractor/20", data={"id": 20, "contentType": "Contractor", "name": "Test Corp"}
    )

    result = await deals.list(expand=["manager", "contractor"])

    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].manager is not None
    assert result[0].manager.first_name == "John"
    assert result[0].contractor is not None
    assert result[0].contractor.name == "Test Corp"


async def test_expand_invalid_field(megaplan_api, tasks):
    """Test expand with invalid field (should be ignored, not raise error)."""
    megaplan_api.get(
        "task",
        data=[
            {
                "id": 1,
                "contentType": "Task",
                "name": "Task 1",
                "responsible": {"id": 10, "contentType": "Employee"},
            },
        ],
    )
    megaplan_api.get("employee/10", data=JOHN)

    # "invalid_field" should be ignored, "responsible" should work
    result = await tasks.list(expand=["responsible", "invalid_field"])

    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].responsible is not None
    assert result[0].responsible.first_name == "John"


async def test_expand_batch_loading(megaplan_api, tasks):
    """Test that expand uses batch loading for multiple entities."""
    megaplan_api.get(
        "task",
        data=[
            {
                "id": 1,
                "contentType": "Task",
                "name": "Task 1",
                "responsible": {"id": 10, "contentType": "Employee"},
            },
            {
                "id": 2,
                "contentType": "Task",
                "name": "Task 2",
                "responsible": {"id": 10, "contentType": "Employee"},
            },
        ],
    )
    employee_route = megaplan_api.get("employee/10", data=JOHN)

    result = await tasks.list(expand=["responsible"])

    assert len(result) == 2
    assert isinstance(result[0].responsible, Employee)
    assert isinstance(result[1].responsible, Employee)
    # Employee should be fetched only once (batch loading)
    assert employee_route.call_count == 1


async def test_expand_caching(megaplan_api, http_client):
    """Test that expand uses cache for repeated entity IDs."""
    megaplan_api.get(
        "task",
        data=[
            {
                "id": 1,
                "contentType": "Task",
                "name": "Task 1",
                "responsible": {"id": 10, "contentType": "Employee"},
            },
        ],
    )
    employee_route = megaplan_api.get("employee/10", data=JOHN)

    cache = EntityCache(max_size=100, ttl=300)
    resource = TasksResource(http_client, cache=cache)

    # First expand - should fetch
    tasks1 = await resource.list(expand=["responsible"])
    assert len(tasks1) == 1
    assert isinstance(tasks1[0].responsible, Employee)

    # Second expand - should use cache
    tasks2 = await resource.list(expand=["responsible"])
    assert len(tasks2) == 1
    assert isinstance(tasks2[0].responsible, Employee)

    # Employee should be fetched only once (cached on second call)
    assert employee_route.call_count == 1


async def test_expand_empty_list(megaplan_api, tasks):
    """Test expand with empty list of entities."""
    megaplan_api.get("task", data=[])

    result = await tasks.list(expand=["responsible"])

    assert len(result) == 0


async def test_expand_none_expand(megaplan_api, tasks):
    """Test that expand=None returns original list without changes."""
    megaplan_api.get(
        "task",
        data=[
            {
                "id": 1,
                "contentType": "Task",
                "name": "Task 1",
                "responsible": {"id": 10, "contentType": "Employee"},
            },
        ],
    )

    result = await tasks.list(expand=None)

    assert len(result) == 1
    assert result[0].id == 1
    # The bare reference is kept: nothing was requested
    assert not isinstance(result[0].responsible, Employee)


async def test_expand_list_entities(megaplan_api, tasks):
    """Test expand pipeline with several fields at once."""
    megaplan_api.get(
        "task",
        data=[
            {
                "id": 1,
                "contentType": "Task",
                "name": "Task 1",
                "responsible": {"id": 10, "contentType": "Employee"},
                "owner": {"id": 11, "contentType": "Employee"},
            },
        ],
    )
    megaplan_api.get("employee/10", data=JOHN)
    megaplan_api.get("employee/11", data=JANE)

    result = await tasks.list(expand=["responsible", "owner"])

    assert len(result) == 1
    assert result[0].responsible is not None
    assert result[0].responsible.first_name == "John"
    assert result[0].owner is not None
    assert result[0].owner.first_name == "Jane"


async def test_expand_entities_missing_field(megaplan_api, tasks):
    """Test expand with entities missing the field to expand."""
    megaplan_api.get(
        "task",
        data=[
            {
                "id": 1,
                "contentType": "Task",
                "name": "Task 1",
                "responsible": None,  # No responsible
            },
            {
                "id": 2,
                "contentType": "Task",
                "name": "Task 2",
                "responsible": {"id": 10, "contentType": "Employee"},
            },
        ],
    )
    megaplan_api.get("employee/10", data=JOHN)

    result = await tasks.list(expand=["responsible"])

    assert len(result) == 2
    assert result[0].responsible is None  # Task 1 has no responsible
    assert result[1].responsible is not None  # Task 2 has responsible
    assert result[1].responsible.first_name == "John"
