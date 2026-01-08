"""Helper functions for working with Megaplan SDK.

Provides convenience functions for creating BaseEntity objects and simplifying
common operations.
"""

from typing import Any

from megaplan_sdk.constants import ContentType


def make_entity(content_type: str, entity_id: int) -> dict[str, Any]:
    """Create a BaseEntity reference dictionary.

    Args:
        content_type: Entity content type (e.g., "Employee", "Project", "Task").
        entity_id: Entity identifier.

    Returns:
        Dictionary representing a BaseEntity reference.

    Examples:
        >>> make_entity("Employee", 123)
        {"contentType": "Employee", "id": 123}
        >>> make_entity("Project", 456)
        {"contentType": "Project", "id": 456}
    """
    return {"contentType": content_type, "id": entity_id}


def make_employee_entity(employee_id: int) -> dict[str, Any]:
    """Create an Employee BaseEntity reference.

    Args:
        employee_id: Employee identifier.

    Returns:
        Dictionary representing an Employee reference.

    Examples:
        >>> make_employee_entity(123)
        {"contentType": "Employee", "id": 123}
    """
    return make_entity(ContentType.EMPLOYEE, employee_id)


def make_project_entity(project_id: int) -> dict[str, Any]:
    """Create a Project BaseEntity reference.

    Args:
        project_id: Project identifier.

    Returns:
        Dictionary representing a Project reference.

    Examples:
        >>> make_project_entity(456)
        {"contentType": "Project", "id": 456}
    """
    return make_entity(ContentType.PROJECT, project_id)


def make_task_entity(task_id: int) -> dict[str, Any]:
    """Create a Task BaseEntity reference.

    Args:
        task_id: Task identifier.

    Returns:
        Dictionary representing a Task reference.

    Examples:
        >>> make_task_entity(789)
        {"contentType": "Task", "id": 789}
    """
    return make_entity(ContentType.TASK, task_id)


def make_deal_entity(deal_id: int) -> dict[str, Any]:
    """Create a Deal BaseEntity reference.

    Args:
        deal_id: Deal identifier.

    Returns:
        Dictionary representing a Deal reference.

    Examples:
        >>> make_deal_entity(101)
        {"contentType": "Deal", "id": 101}
    """
    return make_entity(ContentType.DEAL, deal_id)


def make_contractor_entity(contractor_id: int) -> dict[str, Any]:
    """Create a Contractor BaseEntity reference.

    Args:
        contractor_id: Contractor identifier.

    Returns:
        Dictionary representing a Contractor reference.

    Examples:
        >>> make_contractor_entity(202)
        {"contentType": "Contractor", "id": 202}
    """
    return make_entity(ContentType.CONTRACTOR, contractor_id)
