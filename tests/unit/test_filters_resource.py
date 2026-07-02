"""Unit tests for FiltersResource."""


async def test_list_filters(megaplan_api, filters):
    """Test listing filters."""
    megaplan_api.get(
        "taskFilter",
        data=[
            {"id": 1, "contentType": "TaskFilter", "name": "Filter 1"},
            {"id": 2, "contentType": "TaskFilter", "name": "Filter 2"},
        ],
    )

    result = await filters.list("task")

    assert len(result) == 2
    assert result[0].id == 1
    assert result[0].name == "Filter 1"
    assert result[1].id == 2


async def test_list_filters_with_filters_param(megaplan_api, filters):
    """Test listing filters with filters parameter."""
    megaplan_api.get(
        "taskFilter",
        data=[{"id": 123, "contentType": "TaskFilter", "name": "Filter 123"}],
    )

    result = await filters.list("task", filters=["123", "456"])

    assert len(result) == 1
    assert result[0].id == 123


async def test_get_filter(megaplan_api, filters):
    """Test getting filter by ID."""
    megaplan_api.get(
        "taskFilter/123",
        data={"id": 123, "contentType": "TaskFilter", "name": "Test Filter"},
    )

    filter_obj = await filters.get("task", 123)

    assert filter_obj.id == 123
    assert filter_obj.name == "Test Filter"


async def test_get_filter_string_id(megaplan_api, filters):
    """Test getting filter by string ID."""
    megaplan_api.get(
        "taskFilter/my_filter",
        data={"id": 1, "contentType": "TaskFilter", "name": "My Filter"},
    )

    filter_obj = await filters.get("task", "my_filter")

    assert filter_obj.id == 1
    assert filter_obj.name == "My Filter"


async def test_create_filter(megaplan_api, filters):
    """Test creating filter."""
    megaplan_api.post(
        "taskFilter/my_filter",
        data={
            "id": 1,
            "contentType": "TaskFilter",
            "name": "New Filter",
            "config": {"status": "in_progress"},
        },
    )

    filter_obj = await filters.create(
        "task",
        "my_filter",
        {"name": "New Filter", "config": {"status": "in_progress"}},
    )

    assert filter_obj.id == 1
    assert filter_obj.name == "New Filter"
    assert filter_obj.config == {"status": "in_progress"}


async def test_update_filter(megaplan_api, filters):
    """Test updating filter."""
    megaplan_api.post(
        "taskFilter/123",
        data={"id": 123, "contentType": "TaskFilter", "name": "Updated Filter"},
    )

    filter_obj = await filters.update("task", 123, {"name": "Updated Filter"})

    assert filter_obj.name == "Updated Filter"


async def test_delete_filter(megaplan_api, filters):
    """Test deleting filter."""
    megaplan_api.delete("taskFilter/123")

    await filters.delete("task", 123)


async def test_leave_filter(megaplan_api, filters):
    """Test leaving filter."""
    megaplan_api.post("taskFilter/123/leave")

    await filters.leave("task", 123)


async def test_get_settings(megaplan_api, filters):
    """Test getting filter settings."""
    megaplan_api.get(
        "taskFilter/123/newFilterSettings",
        data={"setting1": "value1", "setting2": "value2"},
    )

    settings = await filters.get_settings("task", 123)

    assert settings.setting1 == "value1"  # type: ignore[attr-defined]
    assert settings.setting2 == "value2"  # type: ignore[attr-defined]


async def test_set_settings(megaplan_api, filters):
    """Test setting filter settings."""
    megaplan_api.post(
        "taskFilter/123/newFilterSettings",
        data={"setting1": "new_value"},
    )

    settings = await filters.set_settings("task", 123, {"setting1": "new_value"})

    assert settings.setting1 == "new_value"  # type: ignore[attr-defined]


async def test_export_filter(megaplan_api, filters):
    """Test exporting filter data."""
    megaplan_api.get(
        "taskFilter/export",
        data={"file": {"contentType": "File", "id": 456}},
    )

    result = await filters.export("task", filter=123)

    assert result.file is not None
    assert result.file.id == 456  # type: ignore[union-attr]


async def test_export_filter_with_config(megaplan_api, filters):
    """Test exporting filter data with config."""
    megaplan_api.get(
        "taskFilter/export",
        data={"file": None},
    )

    result = await filters.export("task", filter={"status": "in_progress"})

    assert result.file is None


async def test_get_available_responsibles(megaplan_api, filters):
    """Test getting available responsibles."""
    megaplan_api.get(
        "taskFilter/availableResponsibles",
        data=[
            {"id": 1, "contentType": "Employee", "firstName": "John", "lastName": "Doe"},
            {"id": 2, "contentType": "ContractorCompany", "name": "Company"},
        ],
    )

    responsibles = await filters.get_available_responsibles("task")

    assert len(responsibles) == 2
    assert responsibles[0].id == 1
    assert responsibles[1].id == 2


async def test_get_formula_variables(megaplan_api, filters):
    """Test getting formula variables."""
    megaplan_api.get(
        "taskFilter/formula/variables",
        data=["variable1", "variable2", "variable3"],
    )

    variables = await filters.get_formula_variables("task")

    assert len(variables) == 3
    assert "variable1" in variables
    assert "variable2" in variables
    assert "variable3" in variables


async def test_normalize_entity_type(filters):
    """Test entity type normalization."""
    # Test common mappings
    assert filters._normalize_entity_type("task") == "taskFilter"
    assert filters._normalize_entity_type("deal") == "tradeFilter"
    assert filters._normalize_entity_type("trade") == "tradeFilter"
    assert filters._normalize_entity_type("employee") == "employeeFilter"
    assert filters._normalize_entity_type("project") == "projectFilter"

    # Test already normalized
    assert filters._normalize_entity_type("taskFilter") == "taskFilter"

    # Test unknown type (should add Filter suffix)
    assert filters._normalize_entity_type("unknown") == "unknownFilter"


async def test_list_different_entity_types(megaplan_api, filters):
    """Test listing filters for different entity types."""
    megaplan_api.get(
        "tradeFilter",
        data=[{"id": 1, "contentType": "TradeFilter", "name": "Deal Filter"}],
    )

    result = await filters.list("deal")

    assert len(result) == 1
    assert result[0].content_type == "TradeFilter"
