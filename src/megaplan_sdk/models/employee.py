"""Employee model for Megaplan SDK."""

from typing import Any

from pydantic import ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateTime, TimestampMixin


class Employee(BaseEntity, TimestampMixin):
    """Employee entity.

    Attributes:
        id: Employee identifier.
        content_type: Entity content type (always "Employee").
        first_name: First name.
        middle_name: Middle name.
        last_name: Last name.
        email: Email address.
        phone: Phone number.
        position: Job position.
        department: Department entity.
        manager: Direct manager entity.
        birthday: Birth date (DateOnly entity with year, month, day fields).
        hired_at: Hire date.
        fired_at: Termination date.
        status: Employment status (EmployeeStatus entity with name, masterType).
        avatar: Avatar image entity.
        is_admin: Whether employee has admin rights.
        is_client: Whether this is a client account.
        access_role: Access role entity.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        custom_fields: Custom field values.
    """

    content_type: str = Field(alias="contentType", default="Employee")
    first_name: str | None = Field(alias="firstName", default=None)
    middle_name: str | None = Field(alias="middleName", default=None)
    last_name: str | None = Field(alias="lastName", default=None)
    email: str | None = None
    phone: str | None = None
    position: str | None = None
    department: BaseEntity | None = None
    manager: BaseEntity | None = None
    birthday: dict[str, Any] | None = None  # DateOnly entity (year, month, day)
    hired_at: str | DateTime | None = Field(alias="hiredAt", default=None)
    fired_at: str | DateTime | None = Field(alias="firedAt", default=None)
    status: BaseEntity | None = None  # EmployeeStatus entity
    avatar: BaseEntity | None = None
    is_admin: bool | None = Field(alias="isAdmin", default=None)
    is_client: bool | None = Field(alias="isClient", default=None)
    access_role: BaseEntity | None = Field(alias="accessRole", default=None)
    custom_fields: dict[str, Any] | None = Field(alias="customFields", default=None)

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    def full_name(self, include_middle: bool = True) -> str:
        """Get full name of the employee.

        Args:
            include_middle: Include middle name (default: True).

        Returns:
            Full name string.

        Examples:
            >>> employee = Employee(
            ...     id=1, first_name="John", middle_name="A", last_name="Doe"
            ... )
            >>> employee.full_name()
            'John A Doe'
            >>> employee.full_name(include_middle=False)
            'John Doe'
        """
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if include_middle and self.middle_name:
            parts.append(self.middle_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else f"Employee#{self.id}"

    def display_name(self) -> str:
        """Get display name with position.

        Returns:
            Full name with position in parentheses.

        Examples:
            >>> employee = Employee(
            ...     id=1, first_name="John", last_name="Doe", position="CEO"
            ... )
            >>> employee.display_name()
            'John Doe (CEO)'
        """
        name = self.full_name(include_middle=False)
        if self.position:
            return f"{name} ({self.position})"
        return name

    def __str__(self) -> str:
        """Return display name for string representation.

        Returns:
            Display name with position.

        Examples:
            >>> employee = Employee(
            ...     id=1, first_name="John", last_name="Doe", position="CEO"
            ... )
            >>> str(employee)
            'John Doe (CEO)'
        """
        return self.display_name()
