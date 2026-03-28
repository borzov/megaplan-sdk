"""Contractor models for Megaplan SDK."""

from typing import Any

from pydantic import ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import TimestampMixin


class Contractor(BaseEntity, TimestampMixin):
    """Base contractor entity.

    Attributes:
        id: Contractor identifier.
        content_type: Entity content type (Contractor, ContractorCompany, ContractorHuman).
        name: Contractor name.
        email: Email address.
        phone: Phone number.
        site: Website URL.
        description: Contractor description.
        category: Contractor category.
        manager: Responsible manager.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        status: Contractor status.
        tags: List of tags.
        custom_fields: Custom field values.
    """

    content_type: str = Field(alias="contentType", default="Contractor")
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    site: str | None = None
    description: str | None = None
    category: BaseEntity | None = None
    manager: BaseEntity | None = None
    status: str | None = None
    tags: list[BaseEntity | str] | None = None  # Can be Tag entities or strings
    custom_fields: dict[str, Any] | None = Field(alias="customFields", default=None)

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    def display_name(self) -> str:
        """Get display name for contractor.

        Returns:
            Contractor name or fallback ID representation.

        Examples:
            >>> contractor = Contractor(id=1, name="ACME Corp")
            >>> contractor.display_name()
            'ACME Corp'
        """
        return self.name or f"Contractor#{self.id}"

    def __str__(self) -> str:
        """Return display name for string representation.

        Returns:
            Display name.

        Examples:
            >>> contractor = Contractor(id=1, name="ACME Corp")
            >>> str(contractor)
            'ACME Corp'
        """
        return self.display_name()


class ContractorCompany(Contractor):
    """Company contractor entity.

    Attributes:
        content_type: Entity content type (always "ContractorCompany").
        inn: Tax identification number (INN).
        kpp: Tax registration reason code (KPP).
        ogrn: Primary state registration number (OGRN).
        legal_name: Legal company name.
        legal_address: Legal address.
        actual_address: Actual address.
    """

    content_type: str = Field(alias="contentType", default="ContractorCompany")
    inn: str | None = None
    kpp: str | None = None
    ogrn: str | None = None
    legal_name: str | None = Field(alias="legalName", default=None)
    legal_address: str | None = Field(alias="legalAddress", default=None)
    actual_address: str | None = Field(alias="actualAddress", default=None)


class ContractorHuman(Contractor):
    """Human contractor entity (individual).

    Attributes:
        content_type: Entity content type (always "ContractorHuman").
        first_name: First name.
        middle_name: Middle name.
        last_name: Last name.
        birthday: Birth date.
        passport: Passport information.
    """

    content_type: str = Field(alias="contentType", default="ContractorHuman")
    first_name: str | None = Field(alias="firstName", default=None)
    middle_name: str | None = Field(alias="middleName", default=None)
    last_name: str | None = Field(alias="lastName", default=None)
    birthday: str | None = None
    passport: str | None = None

    def display_name(self) -> str:
        """Get display name for human contractor.

        Returns:
            Full name or name field or fallback ID representation.

        Examples:
            >>> human = ContractorHuman(
            ...     id=1, first_name="John", last_name="Doe"
            ... )
            >>> human.display_name()
            'John Doe'
        """
        # Try to build from first/last name
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)

        if parts:
            return " ".join(parts)

        # Fallback to name field or ID
        return self.name or f"Contractor#{self.id}"
