"""Unit tests for seam interfaces: post_form, restore_token, open, list_related_to."""

import httpx
import pytest

from megaplan_sdk.auth import AuthManager
from megaplan_sdk.exceptions import AuthenticationError
from megaplan_sdk.http_client import HTTPClient

OAUTH_RESPONSE = {
    "access_token": "new_token",
    "expires_in": 172800,
    "token_type": "bearer",
    "refresh_token": "refresh_123",
}


class TestPostForm:
    """post_form returns parsed JSON and owns transport errors."""

    async def test_returns_parsed_dict(self, megaplan_api, http_client):
        megaplan_api.post("auth/access_token", json=OAUTH_RESPONSE)

        result = await http_client.post_form(
            f"{megaplan_api.base_url}/api/v3/auth/access_token",
            data={"grant_type": "password"},
        )

        assert isinstance(result, dict)
        assert result["access_token"] == "new_token"

    async def test_http_error_raises_authentication_error(self, megaplan_api, http_client):
        megaplan_api.post("auth/access_token", status=401, json={"error": "invalid_grant"})

        with pytest.raises(AuthenticationError):
            await http_client.post_form(
                f"{megaplan_api.base_url}/api/v3/auth/access_token",
                data={"grant_type": "password"},
            )

    async def test_network_error_raises_authentication_error(self, megaplan_api, http_client):
        megaplan_api.router.post(f"{megaplan_api.base_url}/api/v3/auth/access_token").mock(
            side_effect=httpx.ConnectError("boom")
        )

        with pytest.raises(AuthenticationError):
            await http_client.post_form(
                f"{megaplan_api.base_url}/api/v3/auth/access_token",
                data={"grant_type": "password"},
            )


class TestRestoreToken:
    """AuthManager.restore_token replaces direct private-attribute writes."""

    async def test_restore_token_sets_manager_and_http_state(self, megaplan_api, http_client):
        manager = AuthManager(http_client)

        manager.restore_token("restored_token")

        assert manager.get_access_token() == "restored_token"
        # The HTTP client must send the restored token
        route = megaplan_api.get("task/1", data={"id": 1, "contentType": "Task"})
        await http_client.get("/api/v3/task/1")
        auth_header = route.calls.last.request.headers.get("authorization")
        assert auth_header == "Bearer restored_token"


class TestHTTPClientOpen:
    """HTTPClient.open() is the public counterpart of the context manager entry."""

    async def test_open_makes_client_usable_without_context_manager(self, megaplan_api):
        megaplan_api.get("task/1", data={"id": 1, "contentType": "Task"})

        client = HTTPClient(megaplan_api.base_url, access_token="token")
        try:
            await client.open()
            result = await client.get("/api/v3/task/1")
            assert result["data"]["id"] == 1
        finally:
            await client.close()


class TestRelatedTasksUseLinkedTasks:
    """include_related_tasks must go through the linkedTasks subresource.

    The tasks-by-deal *filter* does not exist (verified 2026-07-02, ruvents:
    every baseOn wire format is either silently ignored — returning ALL account
    tasks — or rejected with 422). The subresource does (verified 2026-08-05),
    so the deal's tasks must be read from there and never from a filtered list.
    """

    async def test_include_related_tasks_calls_linked_tasks_route(self, megaplan_api, deals):
        megaplan_api.get("deal/5", data={"id": 5, "contentType": "Deal", "name": "Deal"})
        linked = megaplan_api.get(
            "deal/5/linkedTasks", data=[{"id": 7, "contentType": "Task", "name": "Linked"}]
        )
        listing = megaplan_api.get("task", data=[{"id": 999, "contentType": "Task"}])

        details = await deals.get_full_details(5, include_related_tasks=True)

        assert linked.call_count == 1
        assert listing.call_count == 0, "deal tasks must not come from the task list endpoint"
        assert [task.id for task in details.related_tasks] == [7]
