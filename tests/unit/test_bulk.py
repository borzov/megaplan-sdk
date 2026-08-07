"""POST /api/v3/bulk — batching N calls into one round trip (#FR-E).

Wire format and semantics verified on the stand 2026-08-07: results come back in
the order of ``calls`` and each carries its own ``meta.status``, so one 404 does
not fail the batch.
"""

import json
from collections.abc import AsyncIterator

import pytest

from megaplan_sdk.client import MegaplanClient

LINKED_86 = {
    "meta": {"status": 200, "errors": []},
    "data": [{"contentType": "Deal", "id": "219", "name": "Процесс"}],
}
LINKED_219 = {"meta": {"status": 200, "errors": []}, "data": []}
NOT_FOUND = {
    "meta": {
        "status": 404,
        "errors": [{"field": None, "message": "Not Found Deal with id = 99999999"}],
    },
    "data": None,
}


@pytest.fixture
async def client(megaplan_api, access_token: str) -> AsyncIterator[MegaplanClient]:
    """Client wired to the mocked API."""
    async with MegaplanClient(megaplan_api.base_url, access_token=access_token) as instance:
        yield instance


async def test_bulk_sends_one_request_and_keeps_order(megaplan_api, client):
    """N calls, one round trip, results aligned with the calls by index."""
    route = megaplan_api.post("bulk", data=[LINKED_86, LINKED_219])

    results = await client.bulk(
        [
            {"method": "GET", "url": "/api/v3/deal/86/linkedDeals"},
            {"method": "GET", "url": "/api/v3/deal/219/linkedDeals"},
        ]
    )

    assert route.call_count == 1
    body = json.loads(route.calls[0].request.content)
    assert body["contentType"] == "BulkApiCall"
    assert [call["url"] for call in body["calls"]] == [
        "/api/v3/deal/86/linkedDeals",
        "/api/v3/deal/219/linkedDeals",
    ]
    assert body["calls"][0]["contentType"] == "ApiCall"
    assert len(results) == 2
    assert results[0].data[0]["id"] == "219"


async def test_bulk_reports_per_call_status(megaplan_api, client):
    """A failing call must not sink the batch — it reports its own status."""
    megaplan_api.post("bulk", data=[LINKED_86, NOT_FOUND])

    ok, missing = await client.bulk(
        [
            {"method": "GET", "url": "/api/v3/deal/86/linkedDeals"},
            {"method": "GET", "url": "/api/v3/deal/99999999"},
        ]
    )

    assert ok.status == 200
    assert ok.is_success is True
    assert missing.status == 404
    assert missing.is_success is False
    assert "Not Found" in missing.errors[0]["message"]


async def test_bulk_serializes_bodies(megaplan_api, client):
    """POST calls carry their body as the string the server expects."""
    route = megaplan_api.post("bulk", data=[LINKED_219])

    await client.bulk([{"method": "POST", "url": "/api/v3/deal/1", "body": {"name": "Новая"}}])

    body = json.loads(route.calls[0].request.content)
    assert json.loads(body["calls"][0]["body"]) == {"name": "Новая"}


async def test_linked_deals_many_batches_into_one_request(megaplan_api, deals):
    """The N+1 case the batch endpoint exists for: links of many deals at once."""
    route = megaplan_api.post("bulk", data=[LINKED_86, LINKED_219])

    linked = await deals.get_linked_deals_many([86, 219])

    assert route.call_count == 1
    assert [deal.id for deal in linked[86]] == [219]
    assert linked[219] == []


async def test_linked_deals_many_skips_failed_calls(megaplan_api, deals):
    """A deal the user cannot read yields no entry instead of a bogus empty list."""
    megaplan_api.post("bulk", data=[LINKED_86, NOT_FOUND])

    linked = await deals.get_linked_deals_many([86, 99999999])

    assert list(linked) == [86]
