"""Unit tests for expand functionality."""

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.deals import DealsResource
from megaplan_sdk.resources.tasks import TasksResource


@pytest.mark.asyncio
@respx.mock
async def test_expand_valid_fields():
    """Test expand with valid fields."""
    # Mock deals list
    respx.get("https://example.com/api/v3/deal").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {
                        "id": 1,
                        "contentType": "Deal",
                        "name": "Deal 1",
                        "responsible": {"id": 10, "contentType": "Employee"},
                        "contractor": {"id": 20, "contentType": "Contractor"},
                    },
                ],
            },
        )
    )

    # Mock employee
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

    # Mock contractor
    respx.get("https://example.com/api/v3/contractor/20").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 20, "contentType": "Contractor", "name": "Test Corp"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = DealsResource(http_client)
        deals = await resource.list(expand=["responsible", "contractor"])

        assert len(deals) == 1
        assert deals[0].deal.id == 1
        assert deals[0].responsible_details is not None
        assert deals[0].responsible_details.first_name == "John"
        assert deals[0].contractor_details is not None
        assert deals[0].contractor_details.name == "Test Corp"


@pytest.mark.asyncio
@respx.mock
async def test_expand_invalid_field():
    """Test expand with invalid field (should be ignored, not raise error)."""
    respx.get("https://example.com/api/v3/task").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {
                        "id": 1,
                        "contentType": "Task",
                        "name": "Task 1",
                        "responsible": {"id": 10, "contentType": "Employee"},
                    },
                ],
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
        # "invalid_field" should be ignored, "responsible" should work
        tasks = await resource.list(expand=["responsible", "invalid_field"])

        assert len(tasks) == 1
        assert tasks[0].task.id == 1
        assert tasks[0].responsible_details is not None
        assert tasks[0].responsible_details.first_name == "John"


@pytest.mark.asyncio
@respx.mock
async def test_expand_batch_loading():
    """Test that expand uses batch loading for multiple entities."""
    # Mock tasks with same responsible
    respx.get("https://example.com/api/v3/task").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
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
            },
        )
    )

    # Employee should be loaded only once (batch loading)
    employee_mock = respx.get("https://example.com/api/v3/employee/10").mock(
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
        tasks = await resource.list(expand=["responsible"])

        assert len(tasks) == 2
        assert tasks[0].responsible_details is not None
        assert tasks[1].responsible_details is not None
        # Employee should be fetched only once (batch loading)
        assert employee_mock.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_expand_caching():
    """Test that expand uses cache for repeated entity IDs."""
    from megaplan_sdk.cache import EntityCache

    # Mock tasks
    respx.get("https://example.com/api/v3/task").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {
                        "id": 1,
                        "contentType": "Task",
                        "name": "Task 1",
                        "responsible": {"id": 10, "contentType": "Employee"},
                    },
                ],
            },
        )
    )

    # Employee should be loaded only once (cached on second expand)
    employee_mock = respx.get("https://example.com/api/v3/employee/10").mock(
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

    cache = EntityCache(max_size=100, ttl=300)

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client, cache=cache)

        # First expand - should fetch
        tasks1 = await resource.list(expand=["responsible"])
        assert len(tasks1) == 1
        assert tasks1[0].responsible_details is not None

        # Second expand - should use cache
        tasks2 = await resource.list(expand=["responsible"])
        assert len(tasks2) == 1
        assert tasks2[0].responsible_details is not None

        # Employee should be fetched only once (cached on second call)
        assert employee_mock.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_expand_empty_list():
    """Test expand with empty list of entities."""
    respx.get("https://example.com/api/v3/task").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": []},
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = await resource.list(expand=["responsible"])

        assert len(tasks) == 0


@pytest.mark.asyncio
@respx.mock
async def test_expand_none_expand():
    """Test that expand=None returns original list without changes."""
    respx.get("https://example.com/api/v3/task").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {
                        "id": 1,
                        "contentType": "Task",
                        "name": "Task 1",
                        "responsible": {"id": 10, "contentType": "Employee"},
                    },
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = await resource.list(expand=None)

        assert len(tasks) == 1
        assert tasks[0].id == 1
        # Should be Task, not TaskFullDetails
        assert not hasattr(tasks[0], "responsible_details")


@pytest.mark.asyncio
@respx.mock
async def test_expand_list_entities():
    """Test _expand_list_entities with different configurations."""
    respx.get("https://example.com/api/v3/task").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {
                        "id": 1,
                        "contentType": "Task",
                        "name": "Task 1",
                        "responsible": {"id": 10, "contentType": "Employee"},
                        "owner": {"id": 11, "contentType": "Employee"},
                    },
                ],
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
        tasks = await resource.list(expand=["responsible", "owner"])

        assert len(tasks) == 1
        assert tasks[0].responsible_details is not None
        assert tasks[0].responsible_details.first_name == "John"
        assert tasks[0].owner_details is not None
        assert tasks[0].owner_details.first_name == "Jane"


@pytest.mark.asyncio
@respx.mock
async def test_expand_entities_missing_field():
    """Test expand with entities missing the field to expand."""
    respx.get("https://example.com/api/v3/task").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
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
        tasks = await resource.list(expand=["responsible"])

        assert len(tasks) == 2
        assert tasks[0].responsible_details is None  # Task 1 has no responsible
        assert tasks[1].responsible_details is not None  # Task 2 has responsible
        assert tasks[1].responsible_details.first_name == "John"
