"""Participant types for Megaplan SDK.

This module provides union types and parsing utilities for participant entities
returned by allParticipants endpoints.
"""

from __future__ import annotations

from typing import Any

from megaplan_sdk.constants import ContentType
from megaplan_sdk.models.contractor import ContractorHuman
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.models.group import Group

Participant = Employee | ContractorHuman | Group
"""Union type for participants in tasks and projects.

Participants can be:
- Employee: An employee of the organization
- ContractorHuman: A human contractor (individual)
- Group: A group of participants (e.g., department)
"""


def parse_participant(data: dict[str, Any]) -> Participant:
    """Parse participant data into appropriate model based on contentType.

    Args:
        data: Raw participant data from API response.

    Returns:
        Parsed participant as Employee, ContractorHuman, or Group.

    Raises:
        ValueError: If contentType is unknown or missing.

    Examples:
        >>> data = {"contentType": "Employee", "id": 123, "firstName": "John"}
        >>> participant = parse_participant(data)
        >>> isinstance(participant, Employee)
        True
    """
    content_type = data.get("contentType")

    if content_type == ContentType.EMPLOYEE:
        return Employee(**data)
    elif content_type == ContentType.CONTRACTOR_HUMAN:
        return ContractorHuman(**data)
    elif content_type == ContentType.GROUP:
        return Group(**data)
    else:
        raise ValueError(f"Unknown participant contentType: {content_type}")


def parse_participants(data_list: list[dict[str, Any]]) -> list[Participant]:
    """Parse list of participant data into appropriate models.

    Args:
        data_list: List of raw participant data from API response.

    Returns:
        List of parsed participants.

    Examples:
        >>> data = [
        ...     {"contentType": "Employee", "id": 1, "firstName": "John"},
        ...     {"contentType": "Group", "id": 2, "name": "Developers"},
        ... ]
        >>> participants = parse_participants(data)
        >>> len(participants)
        2
    """
    return [parse_participant(item) for item in data_list]
