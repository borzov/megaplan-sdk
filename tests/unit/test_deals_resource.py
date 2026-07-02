"""Unit tests for DealsResource."""

import json

import pytest


async def test_create_deal(megaplan_api, deals):
    """Test creating a deal."""
    megaplan_api.post("deal", data={"id": 1, "contentType": "Deal", "name": "Test"})

    deal = await deals.create({"name": "Test"})

    assert deal.id == 1
    assert deal.name == "Test"


async def test_list_deals(megaplan_api, deals):
    """Test listing deals."""
    megaplan_api.get("deal", data=[{"id": 1, "contentType": "Deal", "name": "Deal 1"}])

    result = await deals.list()

    assert len(result) == 1
    assert result[0].id == 1


async def test_apply_transition(megaplan_api, deals):
    """Test applying transition to deal."""
    megaplan_api.post(
        "deal/1/applyTransition", data={"id": 1, "contentType": "Deal", "name": "Test"}
    )

    deal = await deals.apply_transition(1, 5)

    assert deal.id == 1


async def test_get_full_details(megaplan_api, deals):
    """Test getting full deal details with related entities."""
    # Mock main deal
    megaplan_api.get(
        "deal/1",
        data={
            "id": 1,
            "contentType": "Deal",
            "name": "Test Deal",
            "manager": {"id": 10, "contentType": "Employee"},
            "contractor": {"id": 20, "contentType": "Contractor"},
        },
    )

    # Mock comments
    megaplan_api.get(
        "deal/1/comments",
        data=[{"id": 1, "contentType": "Comment", "content": "Test comment"}],
    )

    # Mock history
    megaplan_api.get(
        "deal/1/history",
        data=[{"id": 1, "action": "created"}],
    )

    # Mock status history
    megaplan_api.get(
        "deal/1/statusHistory",
        data=[{"id": 1, "status": "new"}],
    )

    # Mock auditors
    megaplan_api.get(
        "deal/1/auditors",
        data=[{"id": 15, "contentType": "Employee"}],
    )

    # Mock responsible employee
    megaplan_api.get(
        "employee/10",
        data={
            "id": 10,
            "contentType": "Employee",
            "firstName": "John",
            "lastName": "Doe",
        },
    )

    # Mock contractor
    megaplan_api.get(
        "contractor/20",
        data={"id": 20, "contentType": "Contractor", "name": "Test Contractor"},
    )

    # Mock related tasks - TasksResource.list() adds statuses parameter
    megaplan_api.get(
        "task",
        data=[{"id": 100, "contentType": "Task", "name": "Related Task"}],
    )

    full_details = await deals.get_full_details(
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


async def test_check_exists_true(megaplan_api, deals):
    """Test check_exists() returns True."""
    megaplan_api.get("deal/checkDealExist", data={"exists": True})

    exists = await deals.check_exists({"name": "Test Deal"})

    assert exists is True


async def test_check_exists_false(megaplan_api, deals):
    """Test check_exists() returns False."""
    megaplan_api.get("deal/checkDealExist", data={"exists": False})

    exists = await deals.check_exists({"name": "Non-existent Deal"})

    assert exists is False


async def test_apply_trigger(megaplan_api, deals):
    """Test applying trigger to deal."""
    megaplan_api.post(
        "deal/1/applyTrigger", data={"id": 1, "contentType": "Deal", "name": "Test Deal"}
    )

    deal = await deals.apply_trigger(1, 10)

    assert deal.id == 1
    assert deal.name == "Test Deal"


async def test_get_all_participants(megaplan_api, deals):
    """Test getting all participants of a deal."""
    megaplan_api.get(
        "deal/123/allParticipants",
        data=[
            {"id": 1, "contentType": "Employee", "firstName": "John", "lastName": "Doe"},
            {"id": 2, "contentType": "Employee", "firstName": "Jane", "lastName": "Smith"},
        ],
    )

    participants = await deals.get_all_participants(deal_id=123)

    assert len(participants) == 2
    assert participants[0].id == 1
    assert participants[0].content_type == "Employee"
    assert participants[0].first_name == "John"
    assert participants[1].id == 2
    assert participants[1].first_name == "Jane"


async def test_get_all_participants_empty(megaplan_api, deals):
    """Test getting all participants when deal has no participants."""
    megaplan_api.get("deal/789/allParticipants", data=[])

    participants = await deals.get_all_participants(deal_id=789)

    assert len(participants) == 0


async def test_get_all_participants_with_pagination(megaplan_api, deals):
    """Test getting all participants with pagination params."""
    megaplan_api.get(
        "deal/123/allParticipants",
        data=[{"id": 1, "contentType": "Employee", "firstName": "John"}],
    )

    participants = await deals.get_all_participants(deal_id=123, limit=50)

    assert len(participants) == 1
    assert participants[0].first_name == "John"


async def test_list_defaults_to_timecreated_desc(megaplan_api, deals):
    """Test that list() defaults to timeCreated DESC sorting."""
    import json
    import urllib.parse

    route = megaplan_api.get("deal", data=[])
    await deals.list(limit=5)
    query_str = route.calls.last.request.url.query.decode()
    sent = json.loads(urllib.parse.unquote(query_str))
    assert sent["sortBy"] == [
        {"contentType": "SortField", "fieldName": "timeCreated", "desc": True}
    ]


async def test_list_empty_sort_opts_out(megaplan_api, deals):
    """Test that sort_by=[] opts out of default sorting."""
    import urllib.parse

    route = megaplan_api.get("deal", data=[])
    await deals.list(limit=5, sort_by=[])
    query_str = route.calls.last.request.url.query.decode()
    assert "sortBy" not in urllib.parse.unquote(query_str)


async def test_q_is_converted_to_name_filter(megaplan_api, deals):
    """Test that q= is converted to a FilterBuilder name filter, never sent raw."""
    import urllib.parse

    route = megaplan_api.get("deal", data=[])
    await deals.list(q="ДВФМ", limit=5)
    query_str = route.calls.last.request.url.query.decode()
    unquoted = urllib.parse.unquote(query_str)
    assert '"q"' not in unquoted  # raw q must never be sent
    parsed = json.loads(unquoted)
    term = parsed["filter"]["config"]["termGroup"]["terms"][0]
    assert term["field"] == "name"
    assert term["comparison"] == "contains"
    assert term["value"] == "ДВФМ"


async def test_q_in_description_raises(deals):
    """Test that q_in with unsupported field raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        await deals.list(q="x", q_in=["description"])


async def test_q_with_filter_raises(deals):
    """Test that passing both q and filter raises ValueError."""
    with pytest.raises(ValueError):
        await deals.list(q="x", filter="incoming")


async def test_get_many_returns_dict_by_id_and_drops_missing(megaplan_api, deals):
    """get_many returns dict[id->Deal]; ids absent from response are dropped."""
    route = megaplan_api.post(
        "bulk/getEntitiesByLinks",
        data=[
            {"contentType": "Deal", "id": "2001001", "name": "Deal A"},
            {"contentType": "Deal", "id": "2001002", "name": "Deal B"},
        ],
    )  # note: requested 99999999 is absent
    result = await deals.get_many([2001001, 2001002, 99999999])
    assert set(result.keys()) == {2001001, 2001002}
    assert result[2001001].name == "Deal A"
    body = json.loads(route.calls.last.request.content)
    assert isinstance(body, list)
    assert {"contentType": "Deal", "id": "2001001"} in body
