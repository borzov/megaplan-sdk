"""Typed contractor profiles, payers, and contact info.

Fixtures are the anonymized card/payer payloads from docs/sdk_samples.zip.
Status and birthday strings stay accepted so older callers do not break.
"""

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from megaplan_sdk.models.base import BaseEntity
from megaplan_sdk.models.common import DateOnly, DateTime
from megaplan_sdk.models.contact import Address, AddressType, ContactInfo
from megaplan_sdk.models.contractor import Contractor, ContractorCompany, ContractorHuman
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.models.payer import Country, Payer, PayerCreate, PayerPatch

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "contractors"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_dict_access_preserves_missing_and_nested_lookups():
    payer = Payer(id=1, country={"id": "RU"}, inn=None)
    assert payer.get("ogrn", "missing") == "missing"
    assert payer.get("inn", "missing") is None
    assert payer["country"]["id"] == "RU"
    with pytest.raises(KeyError):
        _ = payer["ogrn"]


def test_previous_extra_alias_attributes_remain_readable():
    company = ContractorCompany.model_validate(load_fixture("company_multi_payer.json"))
    assert company.contactInfo[0]["value"] == company.contact_info[0].value
    assert company.countDeals == company.count_deals
    assert company.lastDealDate["value"] == company.last_deal_date.value


def test_payer_display_name_and_string():
    assert Payer(id=1, name="Test").display_name() == "Test"
    assert str(Payer(id=1, type="Natural", firstName="First", lastName="Last")) == "First Last"
    assert str(Payer(id=1)) == "Payer#1"


def test_company_card_types_payers_contacts_and_responsibles():
    """A company card exposes payers, contacts, and an employee responsible."""
    company = ContractorCompany.model_validate(load_fixture("company_multi_payer.json"))

    assert company.content_type == "ContractorCompany"
    assert company.payers is not None and len(company.payers) == 2
    assert all(isinstance(payer, Payer) for payer in company.payers)
    assert [payer.type for payer in company.payers] == ["Legal", "Legal"]
    assert company.payers[1].inn == "9999999999"
    assert company.payers[1].country.id == "RU"
    assert company.payers[1].model_extra["Category715CustomFieldFioPodpisanta"]
    assert company.contact_info is not None
    assert isinstance(company.contact_info[0], ContactInfo)
    assert company.contact_info[0].type == "phone"
    assert company.responsibles is not None
    assert isinstance(company.responsibles[0], Employee)
    assert company.count_deals == 1
    assert isinstance(company.last_deal_date, DateTime)
    assert company.is_dropped is False
    assert company.status is None
    assert company.birthday is None
    assert not hasattr(company, "primary_payer")


def test_address_card_accepts_nested_address_type():
    """Archive addresses nest AddressType under type and keep the free-form value."""
    company = ContractorCompany.model_validate(load_fixture("company_address.json"))

    assert company.contact_info is not None
    link, address = company.contact_info
    assert isinstance(link, ContactInfo)
    assert link.is_main is True
    assert isinstance(link.subject, BaseEntity)
    assert isinstance(address, Address)
    assert isinstance(address.type, AddressType)
    assert address.type.id == "1"
    assert address.value == "<value:58>"
    assert address.is_main is None


def test_human_card_types_natural_payer_without_recursing_into_contractor():
    """A human card types its natural payer, and the payer link stays a BaseEntity."""
    human = ContractorHuman.model_validate(load_fixture("human.json"))

    assert human.content_type == "ContractorHuman"
    assert human.first_name == "<firstName:15>"
    assert human.payers is not None and human.payers[0].type == "Natural"
    contractor = human.payers[0].contractor
    assert isinstance(contractor, BaseEntity)
    assert not isinstance(contractor, Contractor)
    assert contractor.content_type == "ContractorHuman"
    assert contractor.id == 1001581


def test_standalone_payers_keep_empty_strings_and_custom_fields():
    """Empty requisites stay empty strings, and account custom fields survive dump."""
    empty = Payer.model_validate(load_fixture("payer_legal_empty.json"))
    filled = Payer.model_validate(load_fixture("payer_legal_filled.json"))
    natural = Payer.model_validate(load_fixture("payer_natural.json"))

    assert empty.inn == ""
    assert empty.bank == ""
    assert empty.country.id == "RU"
    assert empty.country.name == "<name:6>"
    assert empty.model_extra["Category715CustomFieldDolzhnostPodpisanta"] == ""
    dumped = filled.model_dump(by_alias=True)
    assert dumped["Category715CustomFieldNaOsnovanii"].startswith("<Category715")
    assert dumped["ogrn"] == "9999999999999"
    assert dumped["legalAddress"] == "<legalAddress:64>"
    assert natural.type == "Natural"
    assert natural.first_name == "<firstName:15>"
    assert natural.last_name == ""
    assert natural.contractor.content_type == "ContractorHuman"


def test_payer_reading_allows_a_partial_reference():
    """List and reference payloads may omit fields that creation requires."""
    payer = Payer.model_validate({"contentType": "Payer", "id": "1000002", "name": "<name:13>"})

    assert payer.id == 1000002
    assert payer.type is None
    assert payer.country is None


def test_country_accepts_string_id_that_base_entity_rejects():
    """Country.id is a code such as RU, not the numeric BaseEntity identifier."""
    country = Country.model_validate(
        {"contentType": "Country", "id": "RU", "name": "<name:6>", "isDefault": True}
    )

    assert country.id == "RU"
    assert country.is_default is True
    with pytest.raises(ValidationError):
        BaseEntity.model_validate({"contentType": "Country", "id": "RU"})


def test_payer_create_requires_type_and_country():
    """Creation checks the two fields RAML marks required; reading does not."""
    with pytest.raises(ValidationError):
        PayerCreate.model_validate({"contentType": "Payer", "name": "Acme"})

    created = PayerCreate.model_validate(
        {
            "contentType": "Payer",
            "type": "Legal",
            "country": {"contentType": "Country", "id": "RU"},
            "name": "Acme",
        }
    )

    assert created.type == "Legal"
    assert created.country.id == "RU"


def test_payer_patch_excludes_unset_but_keeps_explicit_null():
    """A partial patch must not invent defaults, and an explicit null is a clear."""
    patch = PayerPatch.model_validate({"inn": "7700000000", "kpp": None})

    assert patch.model_dump(by_alias=True, exclude_unset=True) == {
        "inn": "7700000000",
        "kpp": None,
    }
    assert "bank" not in patch.model_fields_set
    assert PayerPatch().model_dump(exclude_unset=True) == {}


@pytest.mark.parametrize(
    ("content_type", "model"),
    [("ContractorCompany", ContractorCompany), ("ContractorHuman", ContractorHuman)],
)
def test_status_and_birthday_accept_typed_values_and_legacy_strings(content_type, model):
    """RAML uses ContractorStatus and DateOnly; stored callers may still pass strings."""
    typed = model.model_validate(
        {
            "contentType": content_type,
            "id": 7,
            "status": {"contentType": "ContractorStatus", "id": "3", "name": "Active"},
            "birthday": {"contentType": "DateOnly", "year": 1991, "month": 4, "day": 12},
        }
    )
    legacy = model.model_validate(
        {
            "contentType": content_type,
            "id": 8,
            "status": "active",
            "birthday": "1991-04-12",
        }
    )

    assert isinstance(typed.status, BaseEntity)
    assert typed.status.id == 3
    assert typed.status.name == "Active"
    assert isinstance(typed.birthday, DateOnly)
    assert typed.birthday.date == date(1991, 4, 12)
    assert legacy.status == "active"
    assert legacy.birthday == "1991-04-12"


def test_address_accepts_city_street_house_without_type():
    """Employee contact addresses omit AddressType and send city/street/house instead."""
    address = Address.model_validate(
        {
            "contentType": "Address",
            "value": "",
            "city": {"contentType": "City", "id": "1000000", "name": "<name:6>"},
            "street": "",
            "house": "",
            "metro": None,
        }
    )

    assert address.type is None
    assert isinstance(address.city, BaseEntity)
    assert address.city.id == 1000000
    assert address.street == ""
    assert address.house == ""
    assert address.metro is None


def test_responsibles_follow_content_type_without_importing_contractors():
    """Groups and contractor companies stay BaseEntity so profile models do not recurse."""
    company = ContractorCompany.model_validate(
        {
            "contentType": "ContractorCompany",
            "id": 1,
            "responsibles": [
                {"contentType": "Employee", "id": 2, "firstName": "Ann"},
                {"contentType": "Group", "id": 3, "name": "Sales"},
                {"contentType": "ContractorCompany", "id": 4, "name": "Holding"},
                {"contentType": "ContractorHuman", "id": 5, "firstName": "Ivan"},
            ],
        }
    )

    employee, group, holding, person = company.responsibles
    assert isinstance(employee, Employee)
    assert employee.first_name == "Ann"
    assert isinstance(group, BaseEntity) and group.content_type == "Group"
    assert isinstance(holding, BaseEntity) and not isinstance(holding, Contractor)
    assert isinstance(person, BaseEntity) and person.content_type == "ContractorHuman"


def test_legacy_dict_access_still_reaches_payers_and_contact_info():
    """Former extra dicts keep get() and alias item access; they are not full dicts."""
    company = ContractorCompany.model_validate(load_fixture("company_multi_payer.json"))

    assert company.get("payers")[0]["id"] == company.payers[0].id
    assert company.get("missing", "fallback") == "fallback"
    assert company["contactInfo"][0]["value"] == company.contact_info[0].value
    assert company["payers"][1]["inn"] == "9999999999"
    with pytest.raises(KeyError):
        company["missing"]


def test_company_keeps_deprecated_requisite_declarations():
    """Old company requisite fields remain declared even though cards no longer send them."""
    company = ContractorCompany.model_validate(
        {
            "contentType": "ContractorCompany",
            "id": 9,
            "inn": "7700000000",
            "kpp": "770001001",
            "ogrn": "1027700000000",
            "legalName": "Acme LLC",
            "legalAddress": "Legal",
            "actualAddress": "Actual",
        }
    )

    assert company.inn == "7700000000"
    assert company.kpp == "770001001"
    assert company.ogrn == "1027700000000"
    assert company.legal_name == "Acme LLC"
    assert company.legal_address == "Legal"
    assert company.actual_address == "Actual"


def test_missing_payers_stay_missing_rather_than_an_empty_list():
    """An unrequested payers field is None; an empty list means the server sent one."""
    omitted = Contractor.model_validate({"contentType": "Contractor", "id": 1, "name": "A"})
    empty = Contractor.model_validate(
        {"contentType": "Contractor", "id": 2, "name": "B", "payers": []}
    )

    assert omitted.payers is None
    assert empty.payers == []
    assert omitted.merge_in_progress is None
