"""Payer routes and request payloads."""

import json
from urllib.parse import unquote

import httpx
import pytest

from megaplan_sdk.client import MegaplanClient
from megaplan_sdk.exceptions import ServerError


@pytest.fixture
async def payer_client(megaplan_api):
    async with MegaplanClient(megaplan_api.base_url, access_token="test") as client:
        yield client


async def test_payer_list_get_and_iteration(payer_client, megaplan_api):
    assert hasattr(payer_client, "payers")
    data = {
        "id": 1,
        "contentType": "Payer",
        "type": "Legal",
        "country": {"id": "RU", "contentType": "Country"},
    }
    route = megaplan_api.get("payer", data=[data])
    assert (await payer_client.payers.list(limit=5))[0].country.id == "RU"
    assert [p.id async for p in payer_client.payers.iterate(limit=5)] == [1]
    assert route.call_count == 2
    megaplan_api.get("payer/1", data=data)
    assert (await payer_client.payers.get(1)).type == "Legal"


async def test_payer_create_and_partial_update(payer_client, megaplan_api):
    assert hasattr(payer_client, "payers")
    data = {"id": 1, "contentType": "Payer", "inn": "123"}
    create = megaplan_api.post("contractor/5/payers", data=data)
    await payer_client.payers.create(5, {"type": "Legal", "country": {"id": "RU"}, "inn": "123"})
    payload = json.loads(create.calls[0].request.content)
    assert payload == {
        "contentType": "Payer",
        "type": "Legal",
        "country": {"contentType": "Country", "id": "RU"},
        "inn": "123",
    }
    megaplan_api.get("payer/1", data=data)
    update = megaplan_api.post("payer/1", data=data)
    await payer_client.payers.update(1, {"inn": ""})
    assert json.loads(update.calls[0].request.content) == {"contentType": "Payer", "inn": ""}


async def test_payer_required_create_fields_and_unknown_patch(payer_client, megaplan_api):
    assert hasattr(payer_client, "payers")
    with pytest.raises(ValueError):
        await payer_client.payers.create(5, {"name": "incomplete"})
    megaplan_api.get("payer/1", data={"id": 1, "contentType": "Payer"})
    with pytest.raises(ValueError, match="typo"):
        await payer_client.payers.update(1, {"typo": "value"})


async def test_payer_patch_rejects_identity_and_deletion_fields(payer_client, megaplan_api):
    megaplan_api.get("payer/1", data={"id": 1, "contentType": "Payer"})
    for patch in [
        {"contractor": {"contentType": "ContractorCompany", "id": 2}},
        {"isDropped": True},
        {"contentType": "Todo"},
    ]:
        with pytest.raises(ValueError):
            await payer_client.payers.update(1, patch, dry_run=True)


async def test_payer_extra_fields_and_delete(payer_client, megaplan_api):
    assert hasattr(payer_client, "payers")
    megaplan_api.get(
        "payer/extraFields", data=[{"id": "payers.inn.RU.Legal", "contentType": "StringField"}]
    )
    assert (await payer_client.payers.extra_fields())[0]["id"] == "payers.inn.RU.Legal"
    megaplan_api.get("payer/extraFields/RU/Legal", data=[])
    assert await payer_client.payers.extra_fields("RU", "Legal") == []
    with pytest.raises(ValueError):
        await payer_client.payers.extra_fields("RU")
    route = megaplan_api.delete("payer/1", data={})
    assert await payer_client.payers.delete(1) is None
    assert route.call_count == 1


async def test_contractor_payers_subresource(contractors, megaplan_api):
    assert hasattr(contractors, "get_payers")
    route = megaplan_api.get("contractor/5/payers", data=[{"id": 7, "contentType": "Payer"}])
    result = await contractors.get_payers(5, limit=2, page_after={"id": 6, "contentType": "Payer"})
    assert result[0].id == 7
    params = json.loads(unquote(route.calls[0].request.url.query.decode()))
    assert params["pageAfter"] == {"id": 6, "contentType": "Payer"}


async def test_post_can_disable_ambiguous_retry(http_client, megaplan_api):
    route = megaplan_api.post("payer/1", status=503, data={})
    with pytest.raises(ServerError):
        await http_client.post("/api/v3/payer/1", json_data={"inn": "123"}, retry_on_error=False)
    assert route.call_count == 1


async def test_post_can_disable_network_retry(http_client, megaplan_api):
    route = megaplan_api.router.post(f"{megaplan_api.base_url}/api/v3/payer/1").mock(
        side_effect=httpx.ReadTimeout("unknown write outcome")
    )
    with pytest.raises(httpx.ReadTimeout):
        await http_client.post("/api/v3/payer/1", json_data={"inn": "123"}, retry_on_error=False)
    assert route.call_count == 1
