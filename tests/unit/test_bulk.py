"""POST /api/v3/bulk — batching N calls into one round trip (#FR-E).

Wire format and semantics verified on the stand 2026-08-07: results come back in
the order of ``calls`` and each carries its own ``meta.status``, so one 404 does
not fail the batch.
"""

import asyncio
import json
from collections.abc import AsyncIterator

import httpx
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


async def test_mixed_entity_links_restore_positions_and_record_missing(client, megaplan_api):
    from megaplan_sdk.models.base import BaseEntity

    task = {"contentType": "Task", "id": "1", "name": "Task one"}
    deal = {"contentType": "Deal", "id": 1, "name": "Deal one"}
    employee = {"contentType": "Employee", "id": "1", "customField": None}
    missing = {"contentType": "Task", "id": 20}
    route = megaplan_api.post("bulk/getEntitiesByLinks", data=[deal, task])
    single = megaplan_api.get("employee/1", data=employee)
    absent = megaplan_api.get("employee/20", status=404)
    absent_employee = {"contentType": "Employee", "id": 20}
    links = [
        task,
        employee,
        missing,
        deal,
        BaseEntity.model_validate(task),
        missing,
        absent_employee,
    ]
    result = await client.get_entities_by_links(iter(links))

    assert result.items == [task, employee, deal, task]
    assert result.missing == [missing, absent_employee]
    assert result.resolved_via == {("Task", 1): "bulk", ("Deal", 1): "bulk", ("Employee", 1): "get"}
    assert single.call_count == absent.call_count == route.call_count == 1
    assert json.loads(route.calls[0].request.content) == [
        {"contentType": "Task", "id": 1},
        missing,
        {"contentType": "Deal", "id": 1},
    ]


async def test_entity_links_empty_skip_raise_and_unordered(client, megaplan_api):
    from megaplan_sdk import MegaplanError

    assert (await client.get_entities_by_links([])).items == []
    first, second, absent = [{"contentType": "Task", "id": i} for i in [1, 2, 3]]
    megaplan_api.post("bulk/getEntitiesByLinks", data=[second, first])
    result = await client.get_entities_by_links(
        [first, second, absent, first], keep_order=False, on_missing="skip"
    )
    assert result.items == [second, first]
    assert result.missing == []
    with pytest.raises(MegaplanError, match="Task.*3") as exc:
        await client.get_entities_by_links([absent], on_missing="raise")
    assert exc.value.errors == [absent]
    with pytest.raises(ValueError, match="on_missing"):
        await client.get_entities_by_links([], on_missing="other")


async def test_entity_links_split_batch_at_25(client, megaplan_api):
    links = [{"contentType": "Task", "id": i} for i in range(26)]
    route = megaplan_api.post("bulk/getEntitiesByLinks", data=[])
    assert (await client.get_entities_by_links(links)).missing == links
    assert [len(json.loads(c.request.content)) for c in route.calls] == [25, 1]


@pytest.mark.parametrize("status", [403, 500])
async def test_employee_link_errors_propagate(megaplan_api, status):
    from megaplan_sdk import AuthorizationError, ServerError

    async with MegaplanClient(megaplan_api.base_url, max_retries=0, access_token="dummy") as api:
        megaplan_api.get("employee/10", status=status)
        with pytest.raises(AuthorizationError if status == 403 else ServerError):
            await api.get_entities_by_links([{"contentType": "Employee", "id": 10}])


async def test_employee_link_timeout_is_not_a_missing_card(megaplan_api):
    async with MegaplanClient(megaplan_api.base_url, max_retries=0, access_token="dummy") as api:
        megaplan_api.get("employee/10").mock(side_effect=httpx.ReadTimeout("timed out"))
        with pytest.raises(httpx.ReadTimeout):
            await api.get_entities_by_links([{"contentType": "Employee", "id": 10}])


async def test_employee_reads_limit_simultaneous_requests(client, megaplan_api):
    active = peak = 0

    async def employee(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        active -= 1
        return httpx.Response(
            200,
            json={"data": {"contentType": "Employee", "id": request.url.path.rsplit("/", 1)[-1]}},
        )

    links = [{"contentType": "Employee", "id": i} for i in range(26)]
    for link in links:
        megaplan_api.get(f"employee/{link['id']}").mock(side_effect=employee)
    result = await client.get_entities_by_links(links)
    assert len(result.items) == 26
    assert 1 < peak <= 8
