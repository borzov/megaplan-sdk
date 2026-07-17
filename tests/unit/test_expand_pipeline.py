"""Unit tests for the declarative expand pipeline (ExpandRule + _expand_and_wrap)."""

import dataclasses
import logging

import pytest

from megaplan_sdk.models.department import Department
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.models.task import Task, TaskFullDetails
from megaplan_sdk.resources._expand import ExpandRule
from megaplan_sdk.resources.base import BaseResource

EMPLOYEE_10 = {
    "id": 10,
    "contentType": "Employee",
    "firstName": "John",
    "lastName": "Doe",
}

DEPARTMENT_5 = {"id": 5, "contentType": "Department", "name": "Development"}


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


async def test_wrap_mode_builds_details_containers(megaplan_api, http_client):
    """Wrap mode loads requested fields and wraps entities into _details_model."""
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

    resource = WrapModeResource(http_client)
    result = await resource._expand_and_wrap(tasks, ["responsible"])

    assert isinstance(result[0], TaskFullDetails)
    assert result[0].task is tasks[0]
    assert result[0].responsible_details is not None
    assert result[0].responsible_details.first_name == "John"
    # "owner" was not requested: declared but unexpanded fields stay None
    assert result[0].owner_details is None


async def test_wrap_mode_missing_reference_yields_none(megaplan_api, http_client):
    """Entities without the reference get None in the details field."""
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

    resource = WrapModeResource(http_client)
    result = await resource._expand_and_wrap(tasks, ["responsible"])

    assert result[0].responsible_details is None
    assert result[1].responsible_details is not None


async def test_expand_none_returns_entities_unchanged(http_client):
    """expand=None short-circuits: the same objects come back, no HTTP calls."""
    tasks = [Task(**{"id": 1, "contentType": "Task", "name": "Task 1"})]

    resource = WrapModeResource(http_client)
    result = await resource._expand_and_wrap(tasks, None)

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
    result = await resource._expand_and_wrap(employees, ["department", "invalid_field"])

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


# --- #36: warn when fields=[...] came back server-deduplicated ---


async def test_list_warns_on_deduplicated_owner_refs(megaplan_api, tasks, caplog):
    """#36: same owner id both named and bare in one page triggers a warning."""
    megaplan_api.get(
        "task",
        data=[
            {
                "id": 1,
                "contentType": "Task",
                "owner": {"contentType": "Employee", "id": 9, "name": "Гусев Максим"},
            },
            {
                "id": 2,
                "contentType": "Task",
                "owner": {"contentType": "Employee", "id": 9},
            },
        ],
    )

    with caplog.at_level(logging.WARNING, logger="megaplan_sdk"):
        await tasks.list(fields=["owner"])

    assert any("expand=['owner']" in record.message for record in caplog.records)


async def test_list_no_warning_when_expand_used(megaplan_api, tasks, caplog):
    """#36: expand=['owner'] resolves everything — no warning."""
    megaplan_api.get(
        "task",
        data=[
            {
                "id": 1,
                "contentType": "Task",
                "owner": {"contentType": "Employee", "id": 9, "name": "Гусев Максим"},
            },
            {
                "id": 2,
                "contentType": "Task",
                "owner": {"contentType": "Employee", "id": 9},
            },
        ],
    )
    megaplan_api.get(
        "employee/9", data={"contentType": "Employee", "id": 9, "name": "Гусев Максим"}
    )

    with caplog.at_level(logging.WARNING, logger="megaplan_sdk"):
        await tasks.list(fields=["owner"], expand=["owner"])

    assert not any("#36" in record.message for record in caplog.records)


async def test_list_no_warning_on_distinct_owners(megaplan_api, tasks, caplog):
    """#36: different employees, all named — no false positive."""
    megaplan_api.get(
        "task",
        data=[
            {
                "id": 1,
                "contentType": "Task",
                "owner": {"contentType": "Employee", "id": 9, "name": "Гусев Максим"},
            },
            {
                "id": 2,
                "contentType": "Task",
                "owner": {"contentType": "Employee", "id": 10, "name": "Иван Петров"},
            },
        ],
    )

    with caplog.at_level(logging.WARNING, logger="megaplan_sdk"):
        await tasks.list(fields=["owner"])

    assert not any("#36" in record.message for record in caplog.records)
