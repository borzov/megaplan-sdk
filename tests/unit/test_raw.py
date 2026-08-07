"""Tests for MegaplanClient.raw() — calling endpoints that have no resource yet.

Reported as #BUG-1 ("_http.get(params=...) → 422"). The transport was fine; what
was missing is a public, supported way to reach an uncovered endpoint without
hand-building the Megaplan query literal.
"""

import json
from collections.abc import AsyncIterator
from urllib.parse import unquote

import pytest
from httpx import Response

from megaplan_sdk.client import MegaplanClient
from megaplan_sdk.exceptions import NotFoundError


@pytest.fixture
async def client(megaplan_api, access_token: str) -> AsyncIterator[MegaplanClient]:
    """Client wired to the mocked API."""
    async with MegaplanClient(megaplan_api.base_url, access_token=access_token) as instance:
        yield instance


async def test_raw_get_encodes_query_as_megaplan_literal(megaplan_api, client):
    """The dict is sent as Megaplan's ?{"limit": 3} literal, not as key=value pairs."""
    route = megaplan_api.get("notification", data=[{"contentType": "Notification", "id": "1"}])

    await client.raw("GET", "/api/v3/notification", query={"limit": 3})

    assert route.call_count == 1
    sent_query = unquote(route.calls[0].request.url.query.decode())
    assert sent_query == json.dumps({"limit": 3})


async def test_raw_returns_full_envelope(megaplan_api, client):
    """Callers get meta and data — meta carries pagination and server errors."""
    megaplan_api.get("notification", data=[{"contentType": "Notification", "id": "7"}])

    body = await client.raw("GET", "/api/v3/notification", query={"limit": 1})

    assert body["data"] == [{"contentType": "Notification", "id": "7"}]
    assert body["meta"]["status"] == 200


async def test_raw_post_sends_json_body(megaplan_api, client):
    """POST bodies pass through untouched (bulk, mass actions, custom endpoints)."""
    route = megaplan_api.post("bulk", data=[])
    payload = {"contentType": "BulkApiCall", "calls": []}

    await client.raw("POST", "/api/v3/bulk", json=payload)

    assert route.call_count == 1
    assert json.loads(route.calls[0].request.content) == payload


async def test_raw_maps_errors_to_sdk_exceptions(megaplan_api, client):
    """Errors surface as SDK exceptions, with retries and auth handled as usual."""
    megaplan_api.router.request("GET", f"{megaplan_api.base_url}/api/v3/nope").mock(
        return_value=Response(404, json={"meta": {"status": 404, "errors": []}})
    )

    with pytest.raises(NotFoundError):
        await client.raw("GET", "/api/v3/nope")


async def test_raw_without_query_sends_no_query_string(megaplan_api, client):
    """Omitting query means a bare URL — no empty literal appended."""
    route = megaplan_api.get("notification/counter", data={"contentType": "Counter", "count": 2})

    await client.raw("GET", "/api/v3/notification/counter")

    assert route.calls[0].request.url.query == b""
