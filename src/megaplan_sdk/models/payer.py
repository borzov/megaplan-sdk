"""Payer models for Megaplan SDK."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.contact import AliasItemAccess

PayerKind = Literal["Legal", "Natural"]


class Country(BaseModel):
    """Country reference.

    ``id`` is a country code such as ``RU``. ``BaseEntity.id`` is numeric and
    cannot store that code.

    Attributes:
        content_type: Always "Country".
        id: Country code.
        name: Country name.
        is_default: Whether this is the account's default country.
    """

    content_type: str = Field(alias="contentType", default="Country")
    id: str
    name: str | None = None
    is_default: bool | None = Field(alias="isDefault", default=None)

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class _PayerFields(BaseModel):
    """Requisites shared by payer reading, creation, and patch models.

    Account-specific custom fields are not declared here. ``extra="allow"``
    keeps them; the payers resource decides which ones may be written.
    """

    name: str | None = None
    bank: str | None = None
    bik: str | None = None
    inn: str | None = None
    edrpou: str | None = None
    correspondent_account: str | None = Field(alias="correspondentAccount", default=None)
    kpp: str | None = None
    ogrn: str | None = None
    first_name: str | None = Field(alias="firstName", default=None)
    last_name: str | None = Field(alias="lastName", default=None)
    address: str | None = None
    legal_address: str | None = Field(alias="legalAddress", default=None)
    current_account: str | None = Field(alias="currentAccount", default=None)
    mfo: str | None = None
    unp: str | None = None
    okpo: str | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Payer(AliasItemAccess, _PayerFields):
    """Payer returned by the API.

    ``type`` and ``country`` are required for creation, but list and card
    references may omit them. ``contractor`` stays a ``BaseEntity`` so a
    contractor profile does not expand through its own payers. An empty string
    is preserved and is not treated as null or a missing field.

    Attributes:
        id: Payer identifier.
        content_type: Always "Payer".
        name: Payer name.
        type: ``Legal`` or ``Natural``, when the response includes it.
        country: Payer country.
        is_dropped: Whether the payer is deleted.
        bank: Bank name.
        bik: Bank identifier code.
        inn: Tax identification number.
        edrpou: Ukrainian EDRPOU code.
        correspondent_account: Correspondent account.
        kpp: Tax registration reason code.
        ogrn: Primary state registration number.
        first_name: Given name of a natural payer.
        last_name: Family name of a natural payer.
        address: Address string.
        legal_address: Legal address string.
        current_account: Settlement account.
        mfo: MFO code.
        unp: UNP code.
        okpo: OKPO code.
        contractor: Owning contractor reference.
    """

    content_type: str = Field(alias="contentType", default="Payer")
    id: int
    type: PayerKind | None = None
    country: Country | None = None
    is_dropped: bool | None = Field(alias="isDropped", default=None)
    contractor: BaseEntity | None = None

    def display_name(self) -> str:
        """Return the payer name, full name, or identifier."""
        return (
            self.name
            or " ".join(part for part in (self.first_name, self.last_name) if part)
            or f"Payer#{self.id}"
        )

    def __str__(self) -> str:
        """Return the payer display name."""
        return self.display_name()


class PayerCreate(_PayerFields):
    """Payload for creating a payer.

    RAML requires ``type`` and ``country``. The other requisites depend on the
    country and payer kind and stay optional.

    Attributes:
        content_type: Always "Payer".
        type: ``Legal`` or ``Natural``.
        country: Payer country.
    """

    content_type: Literal["Payer"] = Field(alias="contentType", default="Payer")
    type: PayerKind
    country: Country


class PayerPatch(_PayerFields):
    """Partial payer update.

    Dump with ``exclude_unset=True`` so fields the caller did not send are
    omitted. An explicit ``None`` is kept: it asks to clear the field. Whether
    the server actually clears it depends on the field. Clearing optional
    ``bank`` was verified on a test payer; required fields cannot be cleared.

    Attributes:
        type: ``Legal`` or ``Natural``.
        country: Payer country.
    """

    type: PayerKind | None = None
    country: Country | None = None
