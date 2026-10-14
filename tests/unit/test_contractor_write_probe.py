"""The live probe is opt-in and cleans up only its own fresh objects."""

import importlib
import json
from pathlib import Path

import pytest
from httpx import Response

from megaplan_sdk.client import MegaplanClient


def probe_module():
    assert Path("scripts/verify_contractor_writes.py").exists()
    return importlib.import_module("scripts.verify_contractor_writes")


def test_probe_requires_explicit_write_optin():
    module = probe_module()
    with pytest.raises(SystemExit):
        module.parse_args(["--contractor-type-id", "1", "--audit-path", "/tmp/audit"])


async def test_probe_exercises_partial_updates_and_cleans_up(megaplan_api, tmp_path):
    module = probe_module()
    states = {}

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
        states["payer"] = {
            "id": 201,
            "contractor": {"id": 101, "contentType": "ContractorCompany"},
            **json.loads(request.content),
        }
        return Response(200, json={"data": states["payer"]})

    def get_company(request):
        return Response(200, json={"data": states["company"]})

    def get_payer(request):
        return Response(200, json={"data": states["payer"]})

    def get_auto(request):
        return Response(200, json={"data": states["auto"]})

    def update_company(request):
        states["company"].update(json.loads(request.content))
        return Response(200, json={"data": states["company"]})

    def update_payer(request):
        states["payer"].update(json.loads(request.content))
        return Response(200, json={"data": states["payer"]})

    megaplan_api.router.post(f"{megaplan_api.base_url}/api/v3/contractorCompany").mock(
        side_effect=create_company
    )
    megaplan_api.router.post(f"{megaplan_api.base_url}/api/v3/contractor/101/payers").mock(
        side_effect=create_payer
    )
    megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/contractor/101").mock(
        side_effect=get_company
    )
    megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/payer/201").mock(side_effect=get_payer)
    megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/payer/200").mock(side_effect=get_auto)
    megaplan_api.router.post(f"{megaplan_api.base_url}/api/v3/contractorCompany/101").mock(
        side_effect=update_company
    )
    megaplan_api.router.post(f"{megaplan_api.base_url}/api/v3/payer/201").mock(
        side_effect=update_payer
    )

    def delete_payer(request):
        states["payer"]["isDropped"] = True
        return Response(200, json={"data": ""})

    def delete_company(request):
        states["company"]["isDropped"] = True
        states["auto"]["isDropped"] = True
        return Response(200, json={"data": ""})

    payer_delete = megaplan_api.router.delete(f"{megaplan_api.base_url}/api/v3/payer/201").mock(
        side_effect=delete_payer
    )
    company_delete = megaplan_api.router.delete(
        f"{megaplan_api.base_url}/api/v3/contractorCompany/101"
    ).mock(side_effect=delete_company)
    async with MegaplanClient(megaplan_api.base_url, access_token="test", max_retries=0) as client:
        report = await module.probe(
            client, contractor_type_id=1, audit_path=tmp_path / "audit", actor="tester"
        )
    assert report["partial_payer_preserves_bank"]
    assert report["contact_array_replaced"]
    assert report["cleanup_payer"] and report["cleanup_contractor"]
    assert report["cleanup_auto_payers"]
    assert payer_delete.call_count == company_delete.call_count == 1
    assert json.loads(company_delete.calls[0].request.content)["mode"] == "only_fake_drop"
