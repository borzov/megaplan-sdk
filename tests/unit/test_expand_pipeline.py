"""Unit tests for the declarative expand pipeline (ExpandRule + _expand_and_wrap)."""

import dataclasses

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.models.department import Department
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.models.task import Task, TaskFullDetails
from megaplan_sdk.resources._expand import ExpandRule
from megaplan_sdk.resources.base import BaseResource
from megaplan_sdk.resources.employees import EmployeesResource

EMPLOYEE_10_RESPONSE = Response(
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

DEPARTMENT_5_RESPONSE = Response(
    200,
    json={
        "meta": {"status": 200},
        "data": {"id": 5, "contentType": "Department", "name": "Development"},
    },
)


class WrapModeResource(BaseResource):
    """Fake resource exercising wrap mode through class-level declarations."""

    _expand_rules = {
        "responsible": ExpandRule("employee", Employee, details_field="responsible_details"),
        "owner": ExpandRule("employee", Employee, details_field="owner_details"),
    }
    _details_model = TaskFullDetails
    _main_field = "task"


class ReplaceModeResource(BaseResource):
    """Fake resource exercising replace mode (no details model declared)."""

    _expand_rules = {
        "department": ExpandRule("department", Department),
        "manager": ExpandRule("employee", Employee),
    }


def test_expand_rule_is_frozen_with_optional_details_field():
    """ExpandRule is an immutable declaration; details_field defaults to None."""
    rule = ExpandRule("employee", Employee)

    assert rule.entity_type == "employee"
    assert rule.model is Employee
    assert rule.details_field is None

    with pytest.raises(dataclasses.FrozenInstanceError):
        rule.entity_type = "department"  # type: ignore[misc]


@pytest.mark.asyncio
@respx.mock
async def test_wrap_mode_builds_details_containers():
    """Wrap mode loads requested fields and wraps entities into _details_model."""
    respx.get("https://example.com/api/v3/employee/10").mock(return_value=EMPLOYEE_10_RESPONSE)

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

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = WrapModeResource(http_client)
        result = await resource._expand_and_wrap(tasks, ["responsible"])

    assert isinstance(result[0], TaskFullDetails)
    assert result[0].task is tasks[0]
    assert result[0].responsible_details is not None
    assert result[0].responsible_details.first_name == "John"
    # "owner" was not requested: declared but unexpanded fields stay None
    assert result[0].owner_details is None


@pytest.mark.asyncio
@respx.mock
async def test_wrap_mode_missing_reference_yields_none():
    """Entities without the reference get None in the details field."""
    respx.get("https://example.com/api/v3/employee/10").mock(return_value=EMPLOYEE_10_RESPONSE)

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

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = WrapModeResource(http_client)
        result = await resource._expand_and_wrap(tasks, ["responsible"])

    assert result[0].responsible_details is None
    assert result[1].responsible_details is not None


@pytest.mark.asyncio
async def test_expand_none_returns_entities_unchanged():
    """expand=None short-circuits: the same objects come back, no HTTP calls."""
    tasks = [Task(**{"id": 1, "contentType": "Task", "name": "Task 1"})]

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = WrapModeResource(http_client)
        result = await resource._expand_and_wrap(tasks, None)

    assert result is tasks


@pytest.mark.asyncio
@respx.mock
async def test_replace_mode_replaces_fields_immutably():
    """Replace mode swaps reference fields for loaded entities on new copies."""
    respx.get("https://example.com/api/v3/department/5").mock(return_value=DEPARTMENT_5_RESPONSE)

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

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = ReplaceModeResource(http_client)
        result = await resource._expand_and_wrap(employees, ["department", "invalid_field"])

    assert isinstance(result[0], Employee)
    assert result[0].department is not None
    assert result[0].department.name == "Development"
    # The original entity is untouched: replace mode must not mutate
    assert result[0] is not employees[0]
    assert employees[0].department is not None
    assert employees[0].department.name is None


@pytest.mark.asyncio
@respx.mock
async def test_employees_list_expand_replaces_department():
    """Public seam: employees.list(expand=...) returns Employee with full Department."""
    respx.get("https://example.com/api/v3/employee").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {
                        "id": 1,
                        "contentType": "Employee",
                        "firstName": "Jane",
                        "lastName": "Smith",
                        "department": {"id": 5, "contentType": "Department"},
                    }
                ],
            },
        )
    )
    respx.get("https://example.com/api/v3/department/5").mock(return_value=DEPARTMENT_5_RESPONSE)

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        employees = await EmployeesResource(http_client).list(expand=["department"])

    assert len(employees) == 1
    assert isinstance(employees[0], Employee)
    assert employees[0].department is not None
    assert employees[0].department.name == "Development"
