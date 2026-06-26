"""Unit tests for DealsResource."""

import json

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
                    "manager": {"id": 10, "contentType": "Employee"},
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
            include_manager_details=True,
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

        assert full_details.manager_details is not None
        assert full_details.manager_details.first_name == "John"

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


@pytest.mark.asyncio
@respx.mock
async def test_get_all_participants():
    """Test getting all participants of a deal."""
    respx.get("https://example.com/api/v3/deal/123/allParticipants").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 1, "contentType": "Employee", "firstName": "John", "lastName": "Doe"},
                    {"id": 2, "contentType": "Employee", "firstName": "Jane", "lastName": "Smith"},
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = DealsResource(http_client)
        participants = await resource.get_all_participants(deal_id=123)

        assert len(participants) == 2
        assert participants[0].id == 1
        assert participants[0].content_type == "Employee"
        assert participants[0].first_name == "John"
        assert participants[1].id == 2
        assert participants[1].first_name == "Jane"


@pytest.mark.asyncio
@respx.mock
async def test_get_all_participants_empty():
    """Test getting all participants when deal has no participants."""
    respx.get("https://example.com/api/v3/deal/789/allParticipants").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": []},
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = DealsResource(http_client)
        participants = await resource.get_all_participants(deal_id=789)

        assert len(participants) == 0


@pytest.mark.asyncio
@respx.mock
async def test_get_all_participants_with_pagination():
    """Test getting all participants with pagination params."""
    respx.get(
        "https://example.com/api/v3/deal/123/allParticipants?"
        "{%22limit%22:%2050}"
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Employee", "firstName": "John"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = DealsResource(http_client)
        participants = await resource.get_all_participants(deal_id=123, limit=50)

        assert len(participants) == 1
        assert participants[0].first_name == "John"


@pytest.mark.asyncio
@respx.mock
async def test_list_defaults_to_timecreated_desc():
    """Test that list() defaults to timeCreated DESC sorting."""
    import json
    import urllib.parse

    route = respx.get("https://example.com/api/v3/deal").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": []})
    )
    async with HTTPClient("https://example.com", access_token="token") as http:
        await DealsResource(http).list(limit=5)
    query_str = route.calls.last.request.url.query.decode()
    sent = json.loads(urllib.parse.unquote(query_str))
    assert sent["sortBy"] == [
        {"contentType": "SortField", "fieldName": "timeCreated", "desc": True}
    ]


@pytest.mark.asyncio
@respx.mock
async def test_list_empty_sort_opts_out():
    """Test that sort_by=[] opts out of default sorting."""
    import urllib.parse

    route = respx.get("https://example.com/api/v3/deal").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": []})
    )
    async with HTTPClient("https://example.com", access_token="token") as http:
        await DealsResource(http).list(limit=5, sort_by=[])
    query_str = route.calls.last.request.url.query.decode()
    assert "sortBy" not in urllib.parse.unquote(query_str)


@pytest.mark.asyncio
@respx.mock
async def test_q_is_converted_to_name_filter():
    """Test that q= is converted to a FilterBuilder name filter, never sent raw."""
    import urllib.parse

    route = respx.get("https://example.com/api/v3/deal").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": []})
    )
    async with HTTPClient("https://example.com", access_token="token") as http:
        await DealsResource(http).list(q="ДВФМ", limit=5)
    query_str = route.calls.last.request.url.query.decode()
    unquoted = urllib.parse.unquote(query_str)
    assert '"q"' not in unquoted  # raw q must never be sent
    parsed = json.loads(unquoted)
    term = parsed["filter"]["config"]["termGroup"]["terms"][0]
    assert term["field"] == "name"
    assert term["comparison"] == "contains"
    assert term["value"] == "ДВФМ"


@pytest.mark.asyncio
async def test_q_in_description_raises():
    """Test that q_in with unsupported field raises NotImplementedError."""
    async with HTTPClient("https://example.com", access_token="token") as http:
        with pytest.raises(NotImplementedError):
            await DealsResource(http).list(q="x", q_in=["description"])


@pytest.mark.asyncio
async def test_q_with_filter_raises():
    """Test that passing both q and filter raises ValueError."""
    async with HTTPClient("https://example.com", access_token="token") as http:
        with pytest.raises(ValueError):
            await DealsResource(http).list(q="x", filter="incoming")


@pytest.mark.asyncio
@respx.mock
async def test_get_many_returns_dict_by_id_and_drops_missing():
    """get_many returns dict[id->Deal]; ids absent from response are dropped."""
    route = respx.post("https://example.com/api/v3/bulk/getEntitiesByLinks").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200, "errors": [], "pagination": []},
                "data": [
                    {"contentType": "Deal", "id": "2001001", "name": "Deal A"},
                    {"contentType": "Deal", "id": "2001002", "name": "Deal B"},
                ],
            },
        )  # note: requested 99999999 is absent
    )
    async with HTTPClient("https://example.com", access_token="token") as http:
        result = await DealsResource(http).get_many([2001001, 2001002, 99999999])
    assert set(result.keys()) == {2001001, 2001002}
    assert result[2001001].name == "Deal A"
    body = json.loads(route.calls.last.request.content)
    assert isinstance(body, list)
    assert {"contentType": "Deal", "id": "2001001"} in body
