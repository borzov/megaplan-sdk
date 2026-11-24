"""Public list projections and page sizes use the contract of the selected route."""

import json
from typing import Any, cast
from urllib.parse import unquote

import pytest
from httpx import Request, Response

from megaplan_sdk import MegaplanClient, TaskQuery


@pytest.fixture
async def client(megaplan_api):
    async with MegaplanClient(megaplan_api.base_url, access_token="test", max_retries=0) as sdk:
        yield sdk


def params(request: Request) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(unquote(request.url.query.decode()) or "{}"))


@pytest.mark.parametrize(
    "resource,route",
    [
        ("tasks", "task"),
        ("deals", "deal"),
        ("todos", "todo"),
        ("contractors", "contractor"),
        ("payers", "payer"),
    ],
)
async def test_oversized_page_rejected_before_http(client, megaplan_api, resource, route):
    endpoint = megaplan_api.get(route, data=[])
    api = getattr(client, resource)
    with pytest.raises(ValueError, match=r"iterate\(limit=100\)"):
        await api.list(limit=500)
    with pytest.raises(ValueError, match=r"iterate\(limit=100\)"):
        await anext(api.iterate(limit=500))
    assert endpoint.call_count == 0
    await api.list()
    assert "limit" not in params(endpoint.calls.last.request)


@pytest.mark.parametrize(
    "resource,route,kind,last_kind",
    [
        ("tasks", "task", "Task", "Project"),
        ("deals", "deal", "Deal", "Deal"),
    ],
)
async def test_page_of_100_preserves_boundary_link(
    client, megaplan_api, resource, route, kind, last_kind
):
    rows = [{"contentType": kind, "id": i} for i in range(1, 102)]
    rows[99]["contentType"] = last_kind

    def list_page(request):
        query = params(request)
        assert query["limit"] == 100
        if "pageAfter" in query:
            assert query["pageAfter"] == rows[99]
            return Response(200, json={"data": rows[100:]})
        return Response(200, json={"data": rows[:100]})

    endpoint = megaplan_api.get(route).mock(side_effect=list_page)
    found = [obj.id async for obj in getattr(client, resource).iterate(limit=100)]
    assert found == list(range(1, 102))
    assert endpoint.call_count == 2


@pytest.mark.parametrize(
    "resource,route,rejected,known",
    [
        ("tasks", "task", "description", "textStatement"),
        ("deals", "deal", "deadline", "description"),
        ("employees", "employee", "isDropped", "isWorking"),
        ("projects", "project", "priority", "deadline"),
        ("payers", "payer", "contentType", "inn"),
        ("todos", "todo", "contentType", "description"),
        ("contractors", "contractor", "email", "contactInfo"),
    ],
)
async def test_list_and_iterate_validate_route_fields(
    client, megaplan_api, resource, route, rejected, known
):
    endpoint = megaplan_api.get(route, data=[])
    api = getattr(client, resource)
    for field, strict in [(rejected, False), ("CustomFieldFoo", True)]:
        with pytest.raises(ValueError, match=field):
            await api.list(fields=[field], fields_strict=strict)
        with pytest.raises(ValueError, match=field):
            await anext(api.iterate(fields=[field], fields_strict=strict))
    assert endpoint.call_count == 0
    await api.list(fields=[known], fields_strict=True)
    query = params(endpoint.calls.last.request)
    assert query["fields"] == [known]
    assert "fields_strict" not in query
    await api.list(fields=["CustomFieldFoo"])
    assert params(endpoint.calls.last.request)["fields"] == ["CustomFieldFoo"]
    assert endpoint.call_count == 2


async def test_search_has_a_different_projection_than_browsing(client, megaplan_api):
    endpoint = megaplan_api.get("contractorCompany/search", data=[])
    for search in [client.contractors.list, client.contractors.search]:
        with pytest.raises(ValueError, match="UnknownField"):
            await search(q="sample", fields=["UnknownField"], fields_strict=True)
        await search(q="sample", fields=["contentType"], fields_strict=True)
    assert endpoint.call_count == 2
    with pytest.raises(ValueError, match="contentType"):
        await client.contractors.list(fields=["contentType"])


def test_query_validates_eagerly_in_either_order():
    with pytest.raises(ValueError, match="statement"):
        TaskQuery().fields("description")
    with pytest.raises(ValueError, match="UnknownField"):
        TaskQuery().fields_strict().fields("UnknownField")
    with pytest.raises(ValueError, match="UnknownField"):
        TaskQuery().fields("UnknownField").fields_strict()
    with pytest.raises(ValueError, match=r"iterate\(limit=100\)"):
        TaskQuery().limit(101)


async def test_query_forwards_strict_fields(client, megaplan_api):
    endpoint = megaplan_api.get("task", data=[])
    query = TaskQuery().with_time_fields().fields("statement", "deals").fields_strict()
    assert query.as_list_kwargs()["fields_strict"] is True
    await client.tasks.list_by(query)
    assert "deals" in params(endpoint.calls.last.request)["fields"]


async def test_error_suggests_working_employee_status(client):
    with pytest.raises(ValueError, match="isWorking"):
        await client.employees.list(fields=["isDropped"])


async def test_uncapped_route_keeps_user_limit(client, megaplan_api):
    endpoint = megaplan_api.get("employee", data=[])
    await client.employees.list(limit=500)
    assert params(endpoint.calls.last.request)["limit"] == 500


def test_subtype_list_projections_are_independent():
    from megaplan_sdk.list_fields import validate_list_options

    validate_list_options("contractorHuman", ["firstName"], fields_strict=True)
    with pytest.raises(ValueError, match="firstName"):
        validate_list_options("contractorCompany", ["firstName"], fields_strict=True)
    with pytest.raises(ValueError, match="inn"):
        validate_list_options("contractorCompany", ["inn"])
    validate_list_options("contractor", ["inn"])


async def test_content_type_error_explains_default_projection(client):
    with pytest.raises(ValueError, match="included automatically"):
        await client.tasks.list(fields=["contentType"])
