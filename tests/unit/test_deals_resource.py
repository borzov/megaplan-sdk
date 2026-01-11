"""Unit tests for DealsResource."""

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.deals import DealsResource


@pytest.mark.asyncio
@respx.mock
async def test_create_deal():
    """Test creating a deal."""
    respx.post("https://example.com/api/v3/deal").mock(
        return_value=Response(
            200, json={"meta": {"status": 200}, "data": {"id": 1, "contentType": "Deal", "name": "Test"}}
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = DealsResource(http_client)
        deal = await resource.create({"name": "Test"})

        assert deal.id == 1
        assert deal.name == "Test"


@pytest.mark.asyncio
@respx.mock
async def test_list_deals():
    """Test listing deals."""
    respx.get("https://example.com/api/v3/deal").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Deal", "name": "Deal 1"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = DealsResource(http_client)
        deals = await resource.list()

        assert len(deals) == 1
        assert deals[0].id == 1


@pytest.mark.asyncio
@respx.mock
async def test_apply_transition():
    """Test applying transition to deal."""
    respx.post("https://example.com/api/v3/deal/1/applyTransition").mock(
        return_value=Response(
            200, json={"meta": {"status": 200}, "data": {"id": 1, "contentType": "Deal", "name": "Test"}}
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = DealsResource(http_client)
        deal = await resource.apply_transition(1, 5)

        assert deal.id == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_full_details():
    """Test getting full deal details with related entities."""
    # Mock main deal
    respx.get("https://example.com/api/v3/deal/1").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 1,
                    "contentType": "Deal",
                    "name": "Test Deal",
                    "responsible": {"id": 10, "contentType": "Employee"},
                    "contractor": {"id": 20, "contentType": "Contractor"},
                },
            },
        )
    )

    # Mock comments
    respx.get("https://example.com/api/v3/deal/1/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Comment", "content": "Test comment"}],
            },
        )
    )

    # Mock history
    respx.get("https://example.com/api/v3/deal/1/history").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 1, "action": "created"}]},
        )
    )

    # Mock status history
    respx.get("https://example.com/api/v3/deal/1/statusHistory").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 1, "status": "new"}]},
        )
    )

    # Mock auditors
    respx.get("https://example.com/api/v3/deal/1/auditors").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": [{"id": 15, "contentType": "Employee"}]},
        )
    )

    # Mock responsible employee
    respx.get("https://example.com/api/v3/employee/10").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 10,
                    "contentType": "Employee",
                    "firstName": "John",
                    "lastName": "Doe",
                },
            },
        )
    )

    # Mock contractor
    respx.get("https://example.com/api/v3/contractor/20").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 20, "contentType": "Contractor", "name": "Test Contractor"},
            },
        )
    )

    # Mock related tasks - TasksResource.list() adds statuses parameter
    respx.get(
        url__regex=r"https://example\.com/api/v3/task\?.*",
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 100, "contentType": "Task", "name": "Related Task"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = DealsResource(http_client)
        full_details = await resource.get_full_details(
            deal_id=1,
            include_comments=True,
            include_history=True,
            include_status_history=True,
            include_auditors=True,
            include_responsible_details=True,
            include_contractor_details=True,
            include_related_tasks=True,
        )

        # Check main deal
        assert full_details.deal.id == 1
        assert full_details.deal.name == "Test Deal"

        # Check related data
        assert full_details.comments is not None
        assert len(full_details.comments) == 1
        assert full_details.comments[0].content == "Test comment"

        assert full_details.history is not None
        assert len(full_details.history) == 1

        assert full_details.status_history is not None
        assert len(full_details.status_history) == 1

        assert full_details.auditors is not None
        assert len(full_details.auditors) == 1

        assert full_details.responsible_details is not None
        assert full_details.responsible_details.first_name == "John"

        assert full_details.contractor_details is not None
        assert full_details.contractor_details.name == "Test Contractor"

        assert full_details.related_tasks is not None
        assert len(full_details.related_tasks) == 1
        assert full_details.related_tasks[0].name == "Related Task"


@pytest.mark.asyncio
@respx.mock
async def test_check_exists_true():
    """Test check_exists() returns True."""
    # Megaplan API uses JSON in query string: ?{"name":"Test Deal"}
    # Use regex to match any query string format
    respx.get(
        url__regex=r"https://example\.com/api/v3/deal/checkDealExist\?.*"
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"exists": True},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = DealsResource(http_client)
        exists = await resource.check_exists({"name": "Test Deal"})

        assert exists is True


@pytest.mark.asyncio
@respx.mock
async def test_check_exists_false():
    """Test check_exists() returns False."""
    # Megaplan API uses JSON in query string: ?{"name":"Non-existent Deal"}
    # Use regex to match any query string format
    respx.get(
        url__regex=r"https://example\.com/api/v3/deal/checkDealExist\?.*"
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"exists": False},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = DealsResource(http_client)
        exists = await resource.check_exists({"name": "Non-existent Deal"})

        assert exists is False


@pytest.mark.asyncio
@respx.mock
async def test_apply_trigger():
    """Test applying trigger to deal."""
    respx.post("https://example.com/api/v3/deal/1/applyTrigger").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 1, "contentType": "Deal", "name": "Test Deal"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = DealsResource(http_client)
        deal = await resource.apply_trigger(1, 10)

        assert deal.id == 1
        assert deal.name == "Test Deal"
