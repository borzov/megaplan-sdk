"""Unit tests for FiltersResource."""

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.filters import FiltersResource


@pytest.mark.asyncio
@respx.mock
async def test_list_filters():
    """Test listing filters."""
    respx.get("https://example.com/api/v3/taskFilter").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 1, "contentType": "TaskFilter", "name": "Filter 1"},
                    {"id": 2, "contentType": "TaskFilter", "name": "Filter 2"},
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        filters = await resource.list("task")

        assert len(filters) == 2
        assert filters[0].id == 1
        assert filters[0].name == "Filter 1"
        assert filters[1].id == 2


@pytest.mark.asyncio
@respx.mock
async def test_list_filters_with_filters_param():
    """Test listing filters with filters parameter."""
    respx.get("https://example.com/api/v3/taskFilter?{%22filters%22:%20[%22123%22,%20%22456%22]}").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 123, "contentType": "TaskFilter", "name": "Filter 123"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        filters = await resource.list("task", filters=["123", "456"])

        assert len(filters) == 1
        assert filters[0].id == 123


@pytest.mark.asyncio
@respx.mock
async def test_get_filter():
    """Test getting filter by ID."""
    respx.get("https://example.com/api/v3/taskFilter/123").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 123, "contentType": "TaskFilter", "name": "Test Filter"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        filter_obj = await resource.get("task", 123)

        assert filter_obj.id == 123
        assert filter_obj.name == "Test Filter"


@pytest.mark.asyncio
@respx.mock
async def test_get_filter_string_id():
    """Test getting filter by string ID."""
    respx.get("https://example.com/api/v3/taskFilter/my_filter").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 1, "contentType": "TaskFilter", "name": "My Filter"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        filter_obj = await resource.get("task", "my_filter")

        assert filter_obj.id == 1
        assert filter_obj.name == "My Filter"


@pytest.mark.asyncio
@respx.mock
async def test_create_filter():
    """Test creating filter."""
    respx.post("https://example.com/api/v3/taskFilter/my_filter").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 1,
                    "contentType": "TaskFilter",
                    "name": "New Filter",
                    "config": {"status": "in_progress"},
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        filter_obj = await resource.create(
            "task",
            "my_filter",
            {"name": "New Filter", "config": {"status": "in_progress"}},
        )

        assert filter_obj.id == 1
        assert filter_obj.name == "New Filter"
        assert filter_obj.config == {"status": "in_progress"}


@pytest.mark.asyncio
@respx.mock
async def test_update_filter():
    """Test updating filter."""
    respx.post("https://example.com/api/v3/taskFilter/123").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 123, "contentType": "TaskFilter", "name": "Updated Filter"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        filter_obj = await resource.update("task", 123, {"name": "Updated Filter"})

        assert filter_obj.name == "Updated Filter"


@pytest.mark.asyncio
@respx.mock
async def test_delete_filter():
    """Test deleting filter."""
    respx.delete("https://example.com/api/v3/taskFilter/123").mock(
        return_value=Response(200, json={"meta": {"status": 200}})
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        await resource.delete("task", 123)


@pytest.mark.asyncio
@respx.mock
async def test_leave_filter():
    """Test leaving filter."""
    respx.post("https://example.com/api/v3/taskFilter/123/leave").mock(
        return_value=Response(200, json={"meta": {"status": 200}})
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        await resource.leave("task", 123)


@pytest.mark.asyncio
@respx.mock
async def test_get_settings():
    """Test getting filter settings."""
    respx.get("https://example.com/api/v3/taskFilter/123/newFilterSettings").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"setting1": "value1", "setting2": "value2"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        settings = await resource.get_settings("task", 123)

        assert settings.setting1 == "value1"  # type: ignore[attr-defined]
        assert settings.setting2 == "value2"  # type: ignore[attr-defined]


@pytest.mark.asyncio
@respx.mock
async def test_set_settings():
    """Test setting filter settings."""
    respx.post("https://example.com/api/v3/taskFilter/123/newFilterSettings").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"setting1": "new_value"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        settings = await resource.set_settings("task", 123, {"setting1": "new_value"})

        assert settings.setting1 == "new_value"  # type: ignore[attr-defined]


@pytest.mark.asyncio
@respx.mock
async def test_export_filter():
    """Test exporting filter data."""
    # HTTPClient converts params to JSON string in query, so filter=123 becomes ?{"filter":123}
    import json
    params_json = json.dumps({"filter": 123}, ensure_ascii=False)
    url = f"https://example.com/api/v3/taskFilter/export?{params_json}"
    respx.get(url).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"file": {"contentType": "File", "id": 456}},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        result = await resource.export("task", filter=123)

        assert result.file is not None
        assert result.file.id == 456  # type: ignore[union-attr]


@pytest.mark.asyncio
@respx.mock
async def test_export_filter_with_config():
    """Test exporting filter data with config."""
    respx.get(
        "https://example.com/api/v3/taskFilter/export?{%22filter%22:%20{%22status%22:%20%22in_progress%22}}"
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"file": None},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        result = await resource.export("task", filter={"status": "in_progress"})

        assert result.file is None


@pytest.mark.asyncio
@respx.mock
async def test_get_available_responsibles():
    """Test getting available responsibles."""
    respx.get("https://example.com/api/v3/taskFilter/availableResponsibles").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 1, "contentType": "Employee", "firstName": "John", "lastName": "Doe"},
                    {"id": 2, "contentType": "ContractorCompany", "name": "Company"},
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        responsibles = await resource.get_available_responsibles("task")

        assert len(responsibles) == 2
        assert responsibles[0].id == 1
        assert responsibles[1].id == 2


@pytest.mark.asyncio
@respx.mock
async def test_get_formula_variables():
    """Test getting formula variables."""
    respx.get("https://example.com/api/v3/taskFilter/formula/variables").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": ["variable1", "variable2", "variable3"],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        variables = await resource.get_formula_variables("task")

        assert len(variables) == 3
        assert "variable1" in variables
        assert "variable2" in variables
        assert "variable3" in variables


@pytest.mark.asyncio
@respx.mock
async def test_normalize_entity_type():
    """Test entity type normalization."""
    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)

        # Test common mappings
        assert resource._normalize_entity_type("task") == "taskFilter"
        assert resource._normalize_entity_type("deal") == "tradeFilter"
        assert resource._normalize_entity_type("trade") == "tradeFilter"
        assert resource._normalize_entity_type("employee") == "employeeFilter"
        assert resource._normalize_entity_type("project") == "projectFilter"

        # Test already normalized
        assert resource._normalize_entity_type("taskFilter") == "taskFilter"

        # Test unknown type (should add Filter suffix)
        assert resource._normalize_entity_type("unknown") == "unknownFilter"


@pytest.mark.asyncio
@respx.mock
async def test_list_different_entity_types():
    """Test listing filters for different entity types."""
    respx.get("https://example.com/api/v3/tradeFilter").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "TradeFilter", "name": "Deal Filter"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FiltersResource(http_client)
        filters = await resource.list("deal")

        assert len(filters) == 1
        assert filters[0].content_type == "TradeFilter"
