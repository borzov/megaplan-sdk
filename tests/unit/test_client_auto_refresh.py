"""Unit tests for MegaplanClient auto-refresh wiring (0.6.2)."""

import respx
from httpx import Response

from megaplan_sdk.client import MegaplanClient

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
