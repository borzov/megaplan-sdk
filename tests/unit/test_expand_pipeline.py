"""Unit tests for the declarative expand pipeline (ExpandRule + _expand_references)."""

import dataclasses

import pytest

from megaplan_sdk.models.department import Department
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.models.task import Task
from megaplan_sdk.resources._expand import ExpandRule
from megaplan_sdk.resources.base import BaseResource

EMPLOYEE_10 = {
    "id": 10,
    "contentType": "Employee",
    "firstName": "John",
    "lastName": "Doe",
}

DEPARTMENT_5 = {"id": 5, "contentType": "Department", "name": "Development"}


class TaskLikeResource(BaseResource):
    """Fake resource declaring two expandable employee references."""

    _expand_rules = {
        "responsible": ExpandRule("employee", Employee),
        "owner": ExpandRule("employee", Employee),
    }


class ReplaceModeResource(BaseResource):
    """Fake resource with references to two different entity types."""

    _expand_rules = {
        "department": ExpandRule("department", Department),
        "manager": ExpandRule("employee", Employee),
    }


def test_expand_rule_is_frozen():
    """ExpandRule is an immutable declaration of how a reference is loaded."""
    rule = ExpandRule("employee", Employee)

    assert rule.entity_type == "employee"
    assert rule.model is Employee

    with pytest.raises(dataclasses.FrozenInstanceError):
        rule.entity_type = "department"  # type: ignore[misc]


async def test_only_requested_fields_are_expanded(megaplan_api, http_client):
    """Declared but unrequested references stay as they came from the server."""
    megaplan_api.get("employee/10", data=EMPLOYEE_10)

    tasks = [
        Task(
            **{
                "id": 1,
                "contentType": "Task",
                "name": "Task 1",
                "responsible": {"id": 10, "contentType": "Employee"},
                "owner": {"id": 10, "contentType": "Employee"},
            }
        )
    ]

    resource = TaskLikeResource(http_client)
    result = await resource._expand_references(tasks, ["responsible"])

    assert isinstance(result[0], Task)
    assert isinstance(result[0].responsible, Employee)
    assert result[0].responsible.first_name == "John"
    assert not isinstance(result[0].owner, Employee)


async def test_entities_without_the_reference_are_left_alone(megaplan_api, http_client):
    """A missing reference is not an error and not a fabricated empty entity."""
    megaplan_api.get("employee/10", data=EMPLOYEE_10)

    tasks = [
        Task(**{"id": 1, "contentType": "Task", "name": "No responsible"}),
        Task(
            **{
                "id": 2,
                "contentType": "Task",
                "name": "With responsible",
                "responsible": {"id": 10, "contentType": "Employee"},
            }
        ),
    ]

    resource = TaskLikeResource(http_client)
    result = await resource._expand_references(tasks, ["responsible"])

    assert result[0].responsible is None
    assert isinstance(result[1].responsible, Employee)


async def test_expand_none_returns_entities_unchanged(http_client):
    """expand=None short-circuits: the same objects come back, no HTTP calls."""
    tasks = [Task(**{"id": 1, "contentType": "Task", "name": "Task 1"})]

    resource = TaskLikeResource(http_client)
    result = await resource._expand_references(tasks, None)

    assert result is tasks


async def test_replace_mode_replaces_fields_immutably(megaplan_api, http_client):
    """Replace mode swaps reference fields for loaded entities on new copies."""
    megaplan_api.get("department/5", data=DEPARTMENT_5)

    employees = [
        Employee(
            **{
                "id": 1,
                "contentType": "Employee",
                "firstName": "Jane",
                "department": {"id": 5, "contentType": "Department"},
            }
        )
    ]

    resource = ReplaceModeResource(http_client)
    result = await resource._expand_references(employees, ["department", "invalid_field"])

    assert isinstance(result[0], Employee)
    assert result[0].department is not None
    assert result[0].department.name == "Development"
    # The original entity is untouched: replace mode must not mutate
    assert result[0] is not employees[0]
    assert employees[0].department is not None
    assert employees[0].department.name is None


async def test_employees_list_expand_replaces_department(megaplan_api, employees):
    """Public seam: employees.list(expand=...) returns Employee with full Department."""
    megaplan_api.get(
        "employee",
        data=[
            {
                "id": 1,
                "contentType": "Employee",
                "firstName": "Jane",
                "lastName": "Smith",
                "department": {"id": 5, "contentType": "Department"},
            }
        ],
    )
    megaplan_api.get("department/5", data=DEPARTMENT_5)

    result = await employees.list(expand=["department"])

    assert len(result) == 1
    assert isinstance(result[0], Employee)
    assert result[0].department is not None
    assert result[0].department.name == "Development"
