"""The live probe is opt-in and cleans up only its own fresh objects."""

import importlib
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from httpx import Response

from megaplan_sdk.client import MegaplanClient


def probe_module() -> ModuleType:
    assert Path("scripts/verify_contractor_writes.py").exists()
    return importlib.import_module("scripts.verify_contractor_writes")


def test_probe_requires_explicit_write_optin():
    module = probe_module()
    with pytest.raises(SystemExit):
        module.parse_args(["--contractor-type-id", "1", "--audit-path", "/tmp/audit"])


@pytest.mark.parametrize("damage", [False, True])
async def test_probe_exercises_partial_updates_and_cleans_up(megaplan_api, tmp_path, damage):
    module = probe_module()
    states: dict[str | int, dict[str, Any]] = {}

    def create_company(request):
        states["company"] = {
            "id": 101,
            "payers": [{"contentType": "Payer", "id": 200}],
            **json.loads(request.content),
        }
        states["auto"] = {
            "contentType": "Payer",
            "id": 200,
            "isDropped": False,
            "contractor": {"contentType": "ContractorCompany", "id": 101},
        }
        return Response(200, json={"data": states["company"]})

    def create_payer(request):
        payload = json.loads(request.content)
        kind = payload["type"]
        payer_id = 201 if kind == "Legal" else 202
        states[payer_id] = {
            "id": payer_id,
            "contractor": {"id": 101, "contentType": "ContractorCompany"},
            "address": None,
            **payload,
        }
        if kind == "Legal":
            for key in ("FioPodpisanta", "DolzhnostPodpisanta", "NaOsnovanii", "Other"):
                states[payer_id]["Category71CustomField" + key] = ""
        return Response(200, json={"data": states[payer_id]})

    def get_company(request):
        return Response(200, json={"data": states["company"]})

    def get_payer(request):
        return Response(200, json={"data": states[int(request.url.path.split("/")[-1])]})

    def get_auto(request):
        return Response(200, json={"data": states["auto"]})

    def update_company(request):
        states["company"].update(json.loads(request.content))
        return Response(200, json={"data": states["company"]})

    def update_payer(request):
        payer_id = int(request.url.path.split("/")[-1])
        payload = json.loads(request.content)
        assert len(payload) == 2
        states[payer_id].update(payload)
        if damage and payer_id == 202 and "inn" in payload:
            # Dropping a null key must be detected even though both .get() values are None.
            states[payer_id].pop("address", None)
        return Response(200, json={"data": states[payer_id]})

    for kind, keys in [
        ("Legal", ("name", "inn", "bank", "100", "101", "102")),
        ("Natural", ("name", "inn")),
    ]:
        megaplan_api.get(
            f"payer/extraFields/RU/{kind}",
            data=[
                {
                    "id": f"payers.{key}.RU.{kind}",
                    "contentType": "StringField",
                    "hrName": {
                        "100": "ФИО подписанта Россия юр. лицо",
                        "101": "Должность подписанта Россия юр. лицо",
                        "102": "На основании Россия юр. лицо",
                    }.get(key, key),
                    "settings": [{"enabled": True, "readOnly": False}],
                }
                for key in keys
            ],
        )
    megaplan_api.router.post(f"{megaplan_api.base_url}/api/v3/contractorCompany").mock(
        side_effect=create_company
    )
    megaplan_api.router.post(f"{megaplan_api.base_url}/api/v3/contractor/101/payers").mock(
        side_effect=create_payer
    )
    megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/contractor/101").mock(
        side_effect=get_company
    )
    for payer_id in (201, 202):
        megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/payer/{payer_id}").mock(
            side_effect=get_payer
        )
    megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/payer/200").mock(side_effect=get_auto)
    megaplan_api.router.post(f"{megaplan_api.base_url}/api/v3/contractorCompany/101").mock(
        side_effect=update_company
    )
    for payer_id in (201, 202):
        megaplan_api.router.post(f"{megaplan_api.base_url}/api/v3/payer/{payer_id}").mock(
            side_effect=update_payer
        )

    def delete_payer(request):
        states[int(request.url.path.split("/")[-1])]["isDropped"] = True
        return Response(200, json={"data": ""})

    def delete_company(request):
        states["company"]["isDropped"] = True
        states["auto"]["isDropped"] = True
        return Response(200, json={"data": ""})

    payer_delete = [
        megaplan_api.router.delete(f"{megaplan_api.base_url}/api/v3/payer/{payer_id}").mock(
            side_effect=delete_payer
        )
        for payer_id in (201, 202)
    ]
    company_delete = megaplan_api.router.delete(
        f"{megaplan_api.base_url}/api/v3/contractorCompany/101"
    ).mock(side_effect=delete_company)
    async with MegaplanClient(megaplan_api.base_url, access_token="test", max_retries=0) as client:
        probe = module.probe(
            client, contractor_type_id=1, audit_path=tmp_path / "audit", actor="tester"
        )
        if damage:
            with pytest.raises(RuntimeError, match="address"):
                await probe
        else:
            report = await probe
            assert set(report["payer_fields"]["Legal"]) == {
                "name",
                "inn",
                "bank",
                "Category71CustomFieldFioPodpisanta",
                "Category71CustomFieldDolzhnostPodpisanta",
                "Category71CustomFieldNaOsnovanii",
            }
            assert set(report["payer_fields"]["Natural"]) >= {"name", "inn"}
            assert report["empty_string_result"] == "empty"
            assert report["null_result"] == "null"
            assert report["partial_payer_preserves_bank"]
            assert report["contact_array_replaced"]
            assert report["cleanup_payer"] and report["cleanup_contractor"]
            assert report["cleanup_auto_payers"]
    assert [route.call_count for route in payer_delete] == [1, 1]
    assert company_delete.call_count == 1
    assert json.loads(company_delete.calls[0].request.content)["mode"] == "only_fake_drop"


async def test_cleanup_checks_each_automatic_payer_after_company_verification_failure(
    megaplan_api, tmp_path
):
    created: dict[str, Any] = {}

    def create_company(request):
        created.update(
            json.loads(request.content),
            id=101,
            payers=[
                {"contentType": "Payer", "id": 200},
                {"contentType": "Payer", "id": 201},
                {"contentType": "Payer", "id": 202},
                {"contentType": "Other", "id": 203},
            ],
        )
        return Response(200, json={"data": created})

    megaplan_api.post("contractorCompany").mock(side_effect=create_company)
    megaplan_api.get("contractor/101").mock(
        side_effect=lambda request: Response(
            200, json={"data": {**created, "contentType": "ContractorHuman"}}
        )
    )
    create = megaplan_api.post("contractor/101/payers", status=403)
    drop = megaplan_api.delete("contractorCompany/101", status=403)
    forbidden = megaplan_api.delete("payer/200", status=403)
    unrelated = megaplan_api.get("payer/203", status=404)
    owner = {"contentType": "ContractorCompany", "id": 101}
    megaplan_api.get(
        "payer/200",
        data={
            "contentType": "Payer",
            "id": 200,
            "contractor": {**owner, "contentType": "ContractorHuman"},
        },
    )
    good = {"contentType": "Payer", "id": 201, "contractor": owner}
    megaplan_api.get("payer/201").mock(
        side_effect=[
            Response(200, json={"data": good}),
            Response(200, json={"data": {**good, "isDropped": True}}),
        ]
    )
    confirmed = megaplan_api.delete("payer/201", data={})
    missing = megaplan_api.get("payer/202", status=404)
    async with MegaplanClient(megaplan_api.base_url, access_token="test", max_retries=0) as client:
        with pytest.raises(RuntimeError, match="Cleanup incomplete"):
            await probe_module().probe(
                client, contractor_type_id=1, audit_path=tmp_path / "audit", actor="tester"
            )
    assert not (create.called or drop.called or forbidden.called or unrelated.called)
    assert confirmed.call_count == missing.call_count == 1


async def test_probe_refuses_reassigned_payer_with_same_numeric_owner_id(megaplan_api, tmp_path):
    created: dict[str, Any] = {}
    dropped = False

    def create_company(request):
        created.update(json.loads(request.content), id=100)
        return Response(200, json={"data": created})

    def drop_company(request):
        nonlocal dropped
        dropped = True
        return Response(200, json={"data": {}})

    megaplan_api.post("contractorCompany").mock(side_effect=create_company)
    megaplan_api.get("contractor/100").mock(
        side_effect=lambda request: Response(200, json={"data": {**created, "isDropped": dropped}})
    )
    megaplan_api.delete("contractorCompany/100").mock(side_effect=drop_company)
    payer = {
        "contentType": "Payer",
        "id": 101,
        "type": "Legal",
        "country": {"id": "RU"},
        "contractor": {"contentType": "ContractorCompany", "id": 100},
    }
    moved = {**payer, "contractor": {"contentType": "ContractorHuman", "id": 100}}
    megaplan_api.post("contractor/100/payers", data=payer)
    first = True

    def read_payer(request):
        nonlocal first
        row = payer if first else moved
        first = False
        return Response(200, json={"data": row})

    megaplan_api.get("payer/101").mock(side_effect=read_payer)
    megaplan_api.get("payer/extraFields/RU/Legal", data=[{"id": "payers.inn.RU.Legal"}])
    update = megaplan_api.post("payer/101", status=403)
    delete = megaplan_api.delete("payer/101", status=403)
    async with MegaplanClient(megaplan_api.base_url, access_token="test", max_retries=0) as client:
        with pytest.raises(RuntimeError, match="Cleanup incomplete"):
            await probe_module().probe(
                client, contractor_type_id=1, audit_path=tmp_path / "audit", actor="tester"
            )
    assert not (update.called or delete.called)
    assert dropped


def test_probe_skips_unverified_disabled_and_ambiguous_signatory_fields():
    current = {
        "Category71CustomFieldFioPodpisanta": "",
        "Category72CustomFieldFioPodpisanta": "",
        "Category71CustomFieldDolzhnostPodpisanta": "",
        "Category71CustomFieldNaOsnovanii": "",
        "Category71CustomFieldOther": "",
    }
    definitions = [
        {"id": "payers.inn.RU.Legal"},
        {
            "id": "payers.100.RU.Legal",
            "hrName": "ФИО подписанта Россия юр. лицо",
            "contentType": "StringField",
            "settings": [{"enabled": True, "readOnly": False}],
        },
        {
            "id": "payers.101.RU.Legal",
            "hrName": "Должность подписанта Россия юр. лицо",
            "contentType": "StringField",
            "settings": [{"enabled": False, "readOnly": True}],
        },
        {
            "id": "payers.102.RU.Legal",
            "hrName": "Без подтвержденной связи",
            "contentType": "StringField",
        },
    ]
    fields, statuses = probe_module()._applicable_fields(definitions, current, "RU", "Legal")
    assert fields == ["inn"]
    assert statuses == {
        "FioPodpisanta": "unverified",
        "DolzhnostPodpisanta": "disabled",
        "NaOsnovanii": "unverified",
    }
