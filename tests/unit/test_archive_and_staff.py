"""Coverage of archived tasks and the two employee directories."""

import json
from typing import Any, cast
from urllib.parse import unquote

import pytest
from httpx import Request, Response

from megaplan_sdk import MegaplanError, Page, TaskQuery
from megaplan_sdk.models.task import Task


def params(request: Request) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(unquote(request.url.query.decode()) or "{}"))


def ref(kind: str, identifier: int | str) -> dict[str, Any]:
    return {"contentType": kind, "id": identifier}


def page(rows: list[dict[str, Any]]) -> Response:
    return Response(200, json={"data": rows})


async def test_archive_query_keeps_statuses_and_groups_text(tasks, megaplan_api):
    route = megaplan_api.get("task", data=[ref("Task", 7), ref("Project", 7), ref("Task", 7)])
    query = TaskQuery().include_archive().search("needle", ["name", "statement"]).statuses("done")
    rows = await tasks.list_by(query)
    assert [(r.content_type, r.id) for r in rows] == [("Project", 7), ("Task", 7)]
    q = params(route.calls.last.request)
    assert q["statuses"] == ["done"] and "q" not in q
    group = q["filter"]["config"]["termGroup"]
    status, *search = group["terms"]
    assert group["join"] == "or" and status["contentType"] == "FilterTermEnum"
    assert [t["field"] for t in search] == ["name", "statement"]


async def test_archive_iterator_uses_last_raw_row(tasks, megaplan_api):
    a, b, c, d = [ref("Task", n) for n in range(1, 5)]
    route = megaplan_api.router.get(megaplan_api._url("task")).mock(
        side_effect=[page([a, b, a]), page([a, a, b]), page([b, c, d]), page([])]
    )
    assert [x.id async for x in tasks.iterate(limit=3, include_archive=True)] == [1, 2, 3, 4]
    assert [params(call.request).get("pageAfter") for call in route.calls] == [None, a, b, d]


async def test_archive_stuck_cursor_and_filter_conflict(tasks, megaplan_api):
    with pytest.raises(ValueError, match="filter"):
        await tasks.list(filter="saved", include_archive=True)
    megaplan_api.get("task", data=[ref("Task", 1)])
    it = tasks.iterate(include_archive=True, limit=1)
    assert (await anext(it)).id == 1
    with pytest.raises(MegaplanError, match="cursor"):
        await anext(it)


async def test_archive_probe_distinguishes_missing_keys_and_failures(tasks, megaplan_api):
    a, b = ref("Task", 7), ref("Project", 7)
    megaplan_api.get("task", data=[a])
    route = megaplan_api.get("project/7", data=b)
    megaplan_api.get("task/9", status=404)
    assert await tasks.find_missing_in_archive(
        links=[Task.model_validate(a), b, b, ref("Task", 9)]
    ) == [b]
    assert route.call_count == 1
    megaplan_api.get("task/8", data=ref("Task", 8))
    assert await tasks.find_missing_in_archive([7, 8, 9, 8]) == [8]
    megaplan_api.get("task/10", status=403)
    with pytest.raises(MegaplanError) as denied:
        await tasks.find_missing_in_archive([10])
    assert denied.value.status_code == 403


async def test_staff_combines_directories_across_pages(employees, megaplan_api):
    megaplan_api.get(
        "employeeFilter", data=[ref("EmployeeFilter", "all"), ref("EmployeeFilter", "not_working")]
    )
    groups = {"all": list(range(1, 103)), "not_working": list(range(103, 206))}

    def respond(req):
        q = params(req)
        ids = groups[q["filter"]["id"]]
        start = ids.index(q["pageAfter"]["id"]) + 1 if q.get("pageAfter") else 0
        return page([ref("Employee", i) for i in ids[start : start + q["limit"]]])

    megaplan_api.router.get(megaplan_api._url("employee")).mock(side_effect=respond)
    rows = [e.id async for e in employees.iterate(include_dismissed=True)]
    assert rows == list(range(1, 206))
    for after, expected in [(100, [101, 102, 103]), (102, [103, 104, 105]), (104, [105, 106, 107])]:
        part = await employees.list(limit=3, include_dismissed=True, page=Page(after=after))
        assert [e.id for e in part] == expected


async def test_unavailable_dismissed_filter_is_explicit(employees, megaplan_api):
    megaplan_api.get("employeeFilter", data=[ref("EmployeeFilter", "all")])
    with pytest.raises(NotImplementedError, match="not_working"):
        await employees.list(include_dismissed=True)


async def test_staff_strict_fields_fail_before_read(employees, megaplan_api):
    before = len(megaplan_api.router.calls)
    with pytest.raises(ValueError):
        await anext(
            employees.iterate(include_dismissed=True, fields=["newField"], fields_strict=True)
        )
    assert len(megaplan_api.router.calls) == before


async def test_archive_continue_from_public_page(tasks, megaplan_api):
    route = megaplan_api.router.get(megaplan_api._url("task")).mock(
        side_effect=[page([ref("Task", 2)]), page([ref("Project", 3)]), page([])]
    )
    assert [
        t.id async for t in tasks.iterate(include_archive=True, limit=1, page=Page(after=1))
    ] == [2, 3]
    assert [params(call.request)["pageAfter"] for call in route.calls] == [
        ref("Task", 1),
        ref("Task", 2),
        ref("Project", 3),
    ]
