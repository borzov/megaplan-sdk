"""Unit tests for MegaplanClient auto-refresh wiring (0.6.2)."""

import pytest
import respx
from httpx import Response

from megaplan_sdk.client import MegaplanClient
from megaplan_sdk.models.auth import AuthTokenResponse

BASE = "https://example.megaplan.ru"
TOKEN_URL = f"{BASE}/api/v3/auth/access_token"
TASK_URL = f"{BASE}/api/v3/task/1"


def _token_payload(access: str, refresh: str = "refresh-2") -> dict:
    """Build an OAuth2 token endpoint payload."""
    return {
        "access_token": access,
        "expires_in": 3600,
        "token_type": "bearer",
        "refresh_token": refresh,
    }


@respx.mock
async def test_client_starts_from_refresh_token_alone():
    """A restart can be recovered from a persisted refresh token only."""
    token_route = respx.post(TOKEN_URL).mock(
        return_value=Response(200, json=_token_payload("fresh"))
    )
    task_route = respx.get(TASK_URL).mock(return_value=Response(200, json={"data": {"id": 1}}))

    async with MegaplanClient(BASE, refresh_token="saved-refresh") as client:
        await client._http.get("/api/v3/task/1")

    assert token_route.call_count == 1
    assert task_route.calls[0].request.headers["Authorization"] == "Bearer fresh"


@respx.mock
async def test_access_token_only_client_does_not_refresh():
    """A client given just an access token keeps working without refreshing."""
    token_route = respx.post(TOKEN_URL).mock(
        return_value=Response(200, json=_token_payload("fresh"))
    )
    task_route = respx.get(TASK_URL).mock(return_value=Response(200, json={"data": {"id": 1}}))

    async with MegaplanClient(BASE, access_token="given") as client:
        await client._http.get("/api/v3/task/1")

    assert not token_route.called
    assert task_route.calls[0].request.headers["Authorization"] == "Bearer given"


@respx.mock
async def test_sync_callback_receives_rotated_pair():
    """A plain function callback is called with the new token pair."""
    respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload("fresh", "rot-9")))
    respx.get(TASK_URL).mock(return_value=Response(200, json={"data": {"id": 1}}))

    seen: list[AuthTokenResponse] = []

    async with MegaplanClient(BASE, refresh_token="saved", on_token_refresh=seen.append) as client:
        await client._http.get("/api/v3/task/1")

    assert len(seen) == 1
    assert seen[0].access_token == "fresh"
    assert seen[0].refresh_token == "rot-9"


@respx.mock
async def test_async_callback_is_awaited():
    """A coroutine function callback is awaited."""
    respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload("fresh", "rot-9")))
    respx.get(TASK_URL).mock(return_value=Response(200, json={"data": {"id": 1}}))

    seen: list[str] = []

    async def _persist(token: AuthTokenResponse) -> None:
        seen.append(token.refresh_token or "")

    async with MegaplanClient(BASE, refresh_token="saved", on_token_refresh=_persist) as client:
        await client._http.get("/api/v3/task/1")

    assert seen == ["rot-9"]


@respx.mock
async def test_failing_callback_does_not_break_the_request(caplog: pytest.LogCaptureFixture):
    """A callback that raises is logged, but the request still succeeds."""
    respx.post(TOKEN_URL).mock(return_value=Response(200, json=_token_payload("fresh")))
    respx.get(TASK_URL).mock(return_value=Response(200, json={"data": {"id": 1}}))

    def _explode(token: AuthTokenResponse) -> None:
        raise RuntimeError("disk full")

    async with MegaplanClient(BASE, refresh_token="saved", on_token_refresh=_explode) as client:
        result = await client._http.get("/api/v3/task/1")

    assert result["data"]["id"] == 1
    assert "on_token_refresh" in caplog.text
