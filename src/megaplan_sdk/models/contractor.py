"""Contractor models for Megaplan SDK."""

from typing import Any

from pydantic import ConfigDict, Field, field_validator

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateOnly, DateTime, TimestampMixin
from megaplan_sdk.models.contact import Address, AliasItemAccess, ContactInfo, parse_contact_item
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.models.payer import Payer


def _parse_responsible(item: Any) -> Any:
    """Parse a responsible as Employee, or as BaseEntity for every other type.

    Groups and contractor profiles stay ``BaseEntity``. Parsing them as
    contractor models would cycle through ``responsibles`` and ``payers``.
    """
    if not isinstance(item, dict):
        return item
    if item.get("contentType") == "Employee":
        return Employee.model_validate(item)
    return BaseEntity.model_validate(item)


class Contractor(AliasItemAccess, BaseEntity, TimestampMixin):
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
        status: Contractor status. A ContractorStatus reference or a legacy string.
        birthday: Birth date. A DateOnly value or a legacy string.
        tags: List of tags.
        custom_fields: Custom field values.
        payers: Payers linked to the contractor. None when the response omitted them.
        contact_info: Phones, emails, links, and addresses.
        responsibles: Employees, groups, or contractor references.
        count_deals: Number of deals.
        last_deal_date: Date of the last deal.
        is_dropped: Whether the contractor is deleted.
        merge_in_progress: Whether a merge involving this contractor is unfinished.
    """

    content_type: str = Field(alias="contentType", default="Contractor")
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    site: str | None = None
    description: str | None = None
    category: BaseEntity | None = None
    manager: BaseEntity | None = None
    status: BaseEntity | str | None = None
    birthday: DateOnly | str | None = None
    tags: list[BaseEntity | str] | None = None  # Can be Tag entities or strings
    custom_fields: dict[str, Any] | None = Field(alias="customFields", default=None)
    payers: list[Payer] | None = None
    contact_info: list[Address | ContactInfo] | None = Field(alias="contactInfo", default=None)
    responsibles: list[Employee | BaseEntity] | None = None
    count_deals: int | None = Field(alias="countDeals", default=None)
    last_deal_date: DateTime | None = Field(alias="lastDealDate", default=None)
    is_dropped: bool | None = Field(alias="isDropped", default=None)
    merge_in_progress: bool | None = Field(alias="mergeInProgress", default=None)

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @field_validator("contact_info", mode="before")
    @classmethod
    def _parse_contact_info(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return value
        return [parse_contact_item(item) for item in value]

    @field_validator("responsibles", mode="before")
    @classmethod
    def _parse_responsibles(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return value
        return [_parse_responsible(item) for item in value]

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

    ``inn``, ``kpp``, ``ogrn``, ``legal_name``, ``legal_address``, and
    ``actual_address`` are deprecated. Current cards keep legal details on
    ``payers``. The declarations stay so existing callers keep working.

    Attributes:
        content_type: Entity content type (always "ContractorCompany").
        inn: Deprecated tax identification number (INN).
        kpp: Deprecated tax registration reason code (KPP).
        ogrn: Deprecated primary state registration number (OGRN).
        legal_name: Deprecated legal company name.
        legal_address: Deprecated legal address.
        actual_address: Deprecated actual address.
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
        birthday: Birth date. A DateOnly value or a legacy string.
        passport: Passport information.
    """

    content_type: str = Field(alias="contentType", default="ContractorHuman")
    first_name: str | None = Field(alias="firstName", default=None)
    middle_name: str | None = Field(alias="middleName", default=None)
    last_name: str | None = Field(alias="lastName", default=None)
    birthday: DateOnly | str | None = None
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
