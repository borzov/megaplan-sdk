"""Unit tests for transport-level token auto-refresh (0.6.2)."""

import asyncio
import time

import httpx
import pytest
import respx
from httpx import Response

from megaplan_sdk.auth import AuthManager
from megaplan_sdk.exceptions import AuthenticationError
from megaplan_sdk.http_client import HTTPClient

BASE = "https://example.com"
TOKEN_URL = f"{BASE}/api/v3/auth/access_token"
TASK_URL = f"{BASE}/api/v3/task/1"


def _token_payload(access: str, refresh: str = "refresh-2", expires_in: int = 3600) -> dict:
    """Build an OAuth2 token endpoint payload."""
    return {
        "access_token": access,
        "expires_in": expires_in,
        "token_type": "bearer",
        "refresh_token": refresh,
    }


async def _wired(http: HTTPClient) -> AuthManager:
    """Attach an AuthManager to the transport as its token provider."""
    auth = AuthManager(http)
    http.set_token_provider(auth)
    return auth


@respx.mock
async def test_expired_token_is_refreshed_before_the_request():
    """A known-expired token is replaced before the request goes out."""
    respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload("fresh")))
    route = respx.get(TASK_URL).mock(return_value=Response(200, json={"data": {"id": 1}}))

    async with HTTPClient(BASE) as http:
        auth = await _wired(http)
        auth.restore_token("stale", expires_at=time.time() - 10)
        auth._refresh_token = "refresh-1"

        await http.get("/api/v3/task/1")

    assert route.calls[0].request.headers["Authorization"] == "Bearer fresh"


@respx.mock
async def test_401_triggers_refresh_and_one_retry():
    """A 401 refreshes the token and replays the request exactly once."""
    respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload("fresh")))
    route = respx.get(TASK_URL).mock(
        side_effect=[
            Response(401, json={"meta": {"status": 401}}),
            Response(200, json={"data": {"id": 1}}),
        ]
    )

    async with HTTPClient(BASE) as http:
        auth = await _wired(http)
        auth.restore_token("rejected")
        auth._refresh_token = "refresh-1"

        result = await http.get("/api/v3/task/1")

    assert result["data"]["id"] == 1
    assert route.call_count == 2
    assert route.calls[0].request.headers["Authorization"] == "Bearer rejected"
    assert route.calls[1].request.headers["Authorization"] == "Bearer fresh"


@respx.mock
async def test_second_401_is_not_retried_again():
    """A token that is rejected twice raises instead of looping."""
    respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload("fresh")))
    route = respx.get(TASK_URL).mock(return_value=Response(401, json={"meta": {"status": 401}}))

    async with HTTPClient(BASE) as http:
        auth = await _wired(http)
        auth.restore_token("rejected")
        auth._refresh_token = "refresh-1"

        with pytest.raises(AuthenticationError):
            await http.get("/api/v3/task/1")

    assert route.call_count == 2


@respx.mock
async def test_401_without_provider_behaves_as_before():
    """Without a token provider the transport keeps its 0.6.1 behaviour."""
    route = respx.get(TASK_URL).mock(return_value=Response(401, json={"meta": {"status": 401}}))

    async with HTTPClient(BASE, access_token="token") as http:
        with pytest.raises(AuthenticationError):
            await http.get("/api/v3/task/1")

    assert route.call_count == 1


@respx.mock
async def test_auto_refresh_works_with_max_retries_zero():
    """max_retries is the 5xx budget; it must not disable the auth retry."""
    respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload("fresh")))
    route = respx.get(TASK_URL).mock(
        side_effect=[
            Response(401, json={"meta": {"status": 401}}),
            Response(200, json={"data": {"id": 1}}),
        ]
    )

    async with HTTPClient(BASE, max_retries=0) as http:
        auth = await _wired(http)
        auth.restore_token("rejected")
        auth._refresh_token = "refresh-1"

        await http.get("/api/v3/task/1")

    assert route.call_count == 2


@respx.mock
async def test_parallel_requests_refresh_once():
    """Ten concurrent requests on an expired token cause exactly one refresh."""
    token_route = respx.post(TOKEN_URL).mock(
        return_value=Response(200, json=_token_payload("fresh"))
    )
    respx.get(TASK_URL).mock(return_value=Response(200, json={"data": {"id": 1}}))

    async with HTTPClient(BASE) as http:
        auth = await _wired(http)
        auth.restore_token("stale", expires_at=time.time() - 10)
        auth._refresh_token = "refresh-1"

        await asyncio.gather(*(http.get("/api/v3/task/1") for _ in range(10)))

    assert token_route.call_count == 1


@respx.mock
async def test_concurrent_401s_on_same_token_refresh_once():
    """Two requests rejected on the same token refresh exactly once.

    Regression test for a bug where the 401 handler re-read
    ``self._access_token`` at handling time instead of remembering the token
    it actually sent. Under that bug, whichever request's 401 handler ran
    after the other had already refreshed would pass the *new* token as
    "rejected", defeating AuthManager's already-refreshed check and causing
    a spurious second refresh that burns the (single-use) rotated refresh
    token.

    Both requests are held until they are both in flight (via an event),
    so both genuinely reach the 401 handler with the same original token
    rather than depending on undocumented event-loop scheduling order.
    """
    token_route = respx.post(TOKEN_URL).mock(
        return_value=Response(200, json=_token_payload("fresh"))
    )

    both_in_flight = asyncio.Event()
    arrivals = 0

    async def _task_response(request: httpx.Request) -> Response:
        nonlocal arrivals
        is_first_arrival = arrivals == 0
        arrivals += 1

        response = (
            Response(401, json={"meta": {"status": 401}})
            if request.headers["Authorization"] == "Bearer rejected"
            else Response(200, json={"data": {"id": 1}})
        )

        if is_first_arrival:
            # Hold the first request's response until the second request
            # has also landed, so both are answered based on the same
            # original (not-yet-refreshed) token.
            await both_in_flight.wait()
        else:
            both_in_flight.set()

        return response

    route = respx.get(TASK_URL).mock(side_effect=_task_response)

    async with HTTPClient(BASE) as http:
        auth = await _wired(http)
        auth.restore_token("rejected")
        auth._refresh_token = "refresh-1"

        results = await asyncio.gather(
            http.get("/api/v3/task/1"),
            http.get("/api/v3/task/1"),
        )

    assert all(result["data"]["id"] == 1 for result in results)
    assert route.call_count >= 3
    assert token_route.call_count == 1


@respx.mock
async def test_dead_refresh_token_surfaces_actionable_error():
    """When the refresh token is dead the caller is told to re-authenticate."""
    respx.post(TOKEN_URL).mock(return_value=Response(400, json={"error": "invalid_grant"}))
    respx.get(TASK_URL).mock(return_value=Response(401, json={"meta": {"status": 401}}))

    async with HTTPClient(BASE) as http:
        auth = await _wired(http)
        auth.restore_token("rejected")
        auth._refresh_token = "stale-refresh"

        with pytest.raises(AuthenticationError, match="single-use"):
            await http.get("/api/v3/task/1")
