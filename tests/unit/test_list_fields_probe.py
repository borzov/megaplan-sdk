"""Read-only field probes report only projection names and outcomes."""

import importlib
import json
from urllib.parse import unquote

import httpx
import pytest

from megaplan_sdk import MegaplanClient

probe_fields = importlib.import_module("scripts.probe_list_fields").probe_fields


async def test_probe_distinguishes_invalid_and_undetermined(megaplan_api):
    fields = ["statement", "description", "private", "server", "timeout"]

    def serve(request):
        query = json.loads(unquote(request.url.query.decode()))
        assert query["limit"] == 1
        assert "onlyRequestedFields" not in query
        field = query.get("fields", [None])[0]
        if field == "timeout":
            raise httpx.ReadTimeout("sensitive context")
        code = {"description": 422, "private": 403, "server": 500}.get(field, 200)
        return httpx.Response(code, json={"data": [{"statement": "sensitive contents"}]})

    megaplan_api.get("task").mock(side_effect=serve)
    async with MegaplanClient(megaplan_api.base_url, access_token="test", max_retries=0) as client:
        results = [r async for r in probe_fields(client, "task", fields)]
    assert [(r["field"], r["outcome"], r["status"]) for r in results] == [
        ("statement", "accepted", 200),
        ("description", "rejected", 422),
        ("private", "undetermined", 403),
        ("server", "undetermined", 500),
        ("timeout", "undetermined", None),
    ]
    assert all(r["route"] == "task" for r in results)
    assert "sensitive" not in repr(results)


@pytest.mark.parametrize("status", [403, 422, 500])
async def test_probe_unavailable_route_cannot_reject_fields(megaplan_api, status):
    endpoint = megaplan_api.get("contractorHuman", status=status)
    async with MegaplanClient(megaplan_api.base_url, access_token="test", max_retries=0) as client:
        results = [r async for r in probe_fields(client, "contractorHuman", ["name", "inn"])]
    assert all(r["outcome"] == "undetermined" and r["status"] == status for r in results)
    assert len(results) == 2
    assert endpoint.call_count == 1


async def test_search_omits_unknown_projection_even_on_200(megaplan_api):
    def serve(request):
        query = json.loads(unquote(request.url.query.decode()))
        assert query["q"] == "sample"
        return httpx.Response(200, json={"data": [{"id": 7, "contentType": "ContractorHuman"}]})

    megaplan_api.get("contractorCompany/search").mock(side_effect=serve)
    async with MegaplanClient(megaplan_api.base_url, access_token="test") as client:
        results = [
            r
            async for r in probe_fields(client, "contractorCompany/search", ["unknown"], q="sample")
        ]
    assert results[0]["outcome"] == "undetermined"


async def test_search_projection_failure_cannot_reject_accepted_name(megaplan_api):
    def serve(request):
        query = json.loads(unquote(request.url.query.decode()))
        if query.get("onlyRequestedFields"):
            return httpx.Response(422, json={"data": None})
        return httpx.Response(200, json={"data": [{"id": 7}]})

    megaplan_api.get("contractorCompany/search").mock(side_effect=serve)
    async with MegaplanClient(megaplan_api.base_url, access_token="test") as client:
        results = [
            r async for r in probe_fields(client, "contractorCompany/search", ["name"], q="sample")
        ]
    assert results[0]["outcome"] == "undetermined"
