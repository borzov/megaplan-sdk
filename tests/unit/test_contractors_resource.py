"""Unit tests for ContractorsResource."""

import json
from urllib.parse import unquote

import pytest
from httpx import Response


async def test_iterate_uses_last_contractor_subtype(megaplan_api, contractors):
    """A page cursor must carry the concrete subtype, not Contractor."""
    pages = [
        [
            {"id": 1, "contentType": "ContractorCompany"},
            {"id": 2, "contentType": "ContractorHuman"},
        ],
        [{"id": 3, "contentType": "ContractorCompany"}],
    ]
    route = megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/contractor").mock(
        side_effect=[Response(200, json={"data": page}) for page in pages]
    )
    result = [item async for item in contractors.iterate(limit=2)]
    assert [item.id for item in result] == [1, 2, 3]
    query = json.loads(unquote(route.calls[1].request.url.query.decode()))
    assert query["pageAfter"] == {"contentType": "ContractorHuman", "id": 2}


async def test_search_parses_both_types(megaplan_api, contractors):
    """The concrete search route can return either contractor subtype."""
    route = megaplan_api.get(
        "contractorCompany/search",
        data=[
            {"id": 1, "contentType": "ContractorCompany", "name": "Company"},
            {"id": 2, "contentType": "ContractorHuman", "firstName": "Person"},
        ],
    )
    result = await contractors.search("needle", limit=5)
    assert [item.content_type for item in result] == ["ContractorCompany", "ContractorHuman"]
    assert json.loads(unquote(route.calls[0].request.url.query.decode())) == {
        "q": "needle",
        "limit": 5,
    }


async def test_legacy_list_search_uses_working_endpoint(megaplan_api, contractors):
    """The existing list(q=...) signature remains a working search shortcut."""
    megaplan_api.get(
        "contractorCompany/search", data=[{"id": 1, "contentType": "ContractorCompany"}]
    )
    result = await contractors.list(q="needle", limit=5)
    assert result[0].id == 1


async def test_search_iteration_keeps_concrete_cursor(megaplan_api, contractors):
    route = megaplan_api.router.get(
        f"{megaplan_api.base_url}/api/v3/contractorCompany/search"
    ).mock(
        side_effect=[
            Response(200, json={"data": [{"id": 1, "contentType": "ContractorHuman"}]}),
            Response(200, json={"data": []}),
        ]
    )
    assert [c.id async for c in contractors.iterate_search("needle", limit=1)] == [1]
    query = json.loads(unquote(route.calls[1].request.url.query.decode()))
    assert query["pageAfter"]["contentType"] == "ContractorHuman"


async def test_search_category_does_not_silently_drop_constraint(contractors):
    with pytest.raises(NotImplementedError, match="category"):
        await contractors.list(q="needle", category_id=1)


async def test_create_contractor_uses_concrete_route(contractors, megaplan_api):
    megaplan_api.post("contractorCompany", data={"contentType": "ContractorCompany", "id": 1})
    assert (await contractors.create({"contentType": "ContractorCompany", "name": "Test"})).id == 1


async def test_search_preserves_reserved_characters_in_name(contractors, megaplan_api):
    route = megaplan_api.get("contractorCompany/search", data=[])
    query = "ООО #1 & 100%22"
    await contractors.search(query)
    sent = route.calls[0].request.url
    assert not sent.fragment
    assert json.loads(unquote(sent.query.decode()))["q"] == query


async def test_list_contractors(megaplan_api, contractors):
    """Test listing contractors."""
    megaplan_api.get(
        "contractor",
        data=[
            {"id": 1, "contentType": "ContractorCompany", "name": "Company 1"},
            {"id": 2, "contentType": "ContractorHuman", "name": "Person 1"},
        ],
    )

    result = await contractors.list()

    assert len(result) == 2
    assert result[0].id == 1
    assert result[0].name == "Company 1"
    assert result[1].id == 2


async def test_get_contractor(megaplan_api, contractors):
    """Test getting a contractor by ID."""
    megaplan_api.get(
        "contractor/1",
        data={"id": 1, "contentType": "ContractorCompany", "name": "Test Company"},
    )

    contractor = await contractors.get(1)

    assert contractor.id == 1
    assert contractor.name == "Test Company"


async def test_get_deals(megaplan_api, contractors):
    """Test getting contractor deals."""
    megaplan_api.get(
        "contractor/1/deals",
        data=[
            {"id": 10, "contentType": "Deal", "name": "Deal 1"},
            {"id": 20, "contentType": "Deal", "name": "Deal 2"},
        ],
    )

    deals = await contractors.get_deals(1)

    assert len(deals) == 2
    assert deals[0].id == 10
    assert deals[0].name == "Deal 1"
    assert deals[1].id == 20
    assert deals[1].name == "Deal 2"


async def test_get_deals_with_limit(megaplan_api, contractors):
    """Test getting contractor deals with limit parameter."""
    megaplan_api.get(
        "contractor/123/deals",
        data=[{"id": 5, "contentType": "Deal", "name": "Limited Deal"}],
    )

    deals = await contractors.get_deals(123, limit=10)

    assert len(deals) == 1
    assert deals[0].id == 5


async def test_get_deals_empty(megaplan_api, contractors):
    """Test getting contractor deals when no deals exist."""
    megaplan_api.get("contractor/999/deals", data=[])

    deals = await contractors.get_deals(999)

    assert len(deals) == 0
    assert deals == []


async def test_get_todos_uses_concrete_subtype_route_when_content_type_given(
    megaplan_api, contractors
):
    """#hypothesis-confirmed: GET /contractor/{id}/todos 500s, the subtype route works.

    When the caller already knows the contentType (e.g. from a prior list()),
    no extra get() lookup should happen — only the subtype route is hit.
    """
    route = megaplan_api.get(
        "contractorCompany/1001786/todos",
        data=[{"id": 1, "contentType": "Todo", "name": "Follow up"}],
    )

    todos = await contractors.get_todos(1001786, content_type="ContractorCompany")

    assert len(todos) == 1
    assert todos[0].name == "Follow up"
    assert route.call_count == 1


async def test_get_todos_resolves_content_type_via_get_when_not_given(megaplan_api, contractors):
    """Without content_type, resolve it via one get() call first."""
    megaplan_api.get(
        "contractor/1001581",
        data={"id": 1001581, "contentType": "ContractorHuman", "name": "Ivanov"},
    )
    route = megaplan_api.get("contractorHuman/1001581/todos", data=[])

    todos = await contractors.get_todos(1001581)

    assert todos == []
    assert route.call_count == 1


async def test_get_history_hits_concrete_subtype_route(megaplan_api, contractors):
    """get_history() goes through contractorCompany/contractorHuman, not contractor."""
    route = megaplan_api.get(
        "contractorHuman/1001581/history",
        data=[{"contentType": "Changeset", "id": "1", "changes": []}],
    )

    entries = await contractors.get_history(1001581, content_type="ContractorHuman")

    assert len(entries) == 1
    assert route.call_count == 1


async def test_iterate_history_hits_concrete_subtype_route(megaplan_api, contractors):
    """iterate_history() resolves the subtype once, then paginates that route."""
    megaplan_api.get(
        "contractorCompany/1001786/history",
        data=[{"contentType": "Changeset", "id": "1", "changes": []}],
    )

    entries = [
        entry
        async for entry in contractors.iterate_history(1001786, content_type="ContractorCompany")
    ]

    assert len(entries) == 1


async def test_get_link_events_matches_concrete_content_type(megaplan_api, contractors):
    """The journal echoes back the concrete subtype, not the abstract 'Contractor' —
    is_source must be computed against that, not self._page_content_type.
    """
    link = {
        "contentType": "BasedOnHistory",
        "id": "5001",
        "timeCreated": {"contentType": "DateTime", "value": "2026-08-21T10:00:00+00:00"},
        "basedModel": {"contentType": "ContractorCompany", "id": "1001786"},
        "generatedModel": {"contentType": "Deal", "id": "219"},
        "user": {"contentType": "Employee", "id": "1000011"},
        "unlink": False,
        "description": "linked",
    }
    megaplan_api.get("contractorCompany/1001786/history", data=[link])

    events = await contractors.get_link_events(1001786, content_type="ContractorCompany")

    assert len(events) == 1
    event = events[0]
    assert event.is_source is True, "basedModel matches the concrete ContractorCompany type"
    assert event.other.content_type == "Deal"
    assert event.other.id == 219


async def test_resolve_subtype_rejects_unknown_content_type(contractors):
    """A contentType that isn't a known contractor subtype fails loudly."""
    import pytest

    with pytest.raises(ValueError, match="ContractorCompany"):
        await contractors._resolve_subtype(1, "SomethingElse")


async def test_search_history_uses_the_concrete_subtype_route(megaplan_api, contractors):
    """The abstract /contractor/{id} route 500s; the subtype route works."""
    lookup = megaplan_api.get("contractor/7", data={"contentType": "ContractorCompany", "id": "7"})
    route = megaplan_api.get("contractorCompany/7/history/search", data=[{"id": "1"}])

    result = await contractors.search_history(7, "договор")

    assert route.called
    assert lookup.called
    assert result == [{"id": "1"}]


async def test_search_history_skips_the_lookup_when_content_type_is_known(
    megaplan_api, contractors
):
    """Passing content_type avoids the extra GET."""
    lookup = megaplan_api.get("contractor/7", data={"contentType": "ContractorCompany", "id": "7"})
    route = megaplan_api.get("contractorHuman/7/history/search", data=[])

    await contractors.search_history(7, "договор", content_type="ContractorHuman")

    assert route.called
    assert not lookup.called
