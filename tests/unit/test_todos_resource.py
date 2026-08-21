"""Tests for TodosResource — reads and writes over todos ("Дела").

Read routes were confirmed by a live-account probe (2026-08-21): GET todo,
GET todo/{id}, GET todo/{id}/deals, GET todo/{id}/issues (note: issues, not
tasks — that is what test_linked_tasks_use_issues_subresource guards against),
GET todo/search, GET todo/busyDays, GET todo/{id}/comments.

Write routes were confirmed by a second live-account probe (2026-08-21, Task
7): POST todo (create), POST todo/{id} (update), DELETE todo/{id} — all 200.
POST todo/{id}/finish, /renew, /take all 404 "No route found" — those are not
real routes (a hypothesis from the RAML action-request types that Task 1's
probe disproved), so no finish()/renew()/take() actions are implemented that
way. A plain status update via POST todo/{id} was verified separately to
persist (confirmed by polling GET after the write) — see finish() below,
which is thin sugar over update().

Writes on live Todo were observed to be eventually consistent: a POST
returns 200 with the intended state immediately, but a GET issued right after
can still show the previous value for a few seconds before catching up
(worse under several rapid concurrent writes to the same todo). This is a
server-side characteristic, not something the SDK compensates for.
"""

import json
from urllib.parse import unquote

TODO = {
    "contentType": "Todo",
    "id": "501",
    "name": "Созвон",
    "status": {"contentType": "TodoStatus", "id": "1", "masterType": "scheduled"},
    "timeCreated": {"contentType": "DateTime", "value": "2026-08-20T09:00:00+00:00"},
}


def sent_query(route) -> dict:
    """Decode Megaplan's query literal from a recorded request."""
    return json.loads(unquote(route.calls[0].request.url.query.decode()))


async def test_list_parses_todos(megaplan_api, todos):
    megaplan_api.get("todo", data=[TODO])

    items = await todos.list(limit=10)

    assert [t.id for t in items] == [501]
    assert items[0].is_finished() is False


async def test_list_sends_limit_as_megaplan_literal(megaplan_api, todos):
    """Query goes out as ?{"limit": 10}, not as key=value pairs."""
    route = megaplan_api.get("todo", data=[])

    await todos.list(limit=10)

    assert sent_query(route) == {"limit": 10}


async def test_list_passes_ad_hoc_filter_through_untouched(megaplan_api, todos):
    """filter= is a pure pass-through; the SDK does not validate its shape."""
    route = megaplan_api.get("todo", data=[])

    await todos.list(filter={"contentType": "TodoFilter", "id": 7})

    assert sent_query(route) == {"filter": {"contentType": "TodoFilter", "id": 7}}


async def test_list_passes_q_and_sort_by(megaplan_api, todos):
    route = megaplan_api.get("todo", data=[])

    await todos.list(q="звонок", sort_by=[{"field": "timeCreated", "order": "desc"}])

    query = sent_query(route)
    assert query["q"] == "звонок"
    assert query["sortBy"] == [{"field": "timeCreated", "order": "desc"}]


async def test_get_returns_single_todo(megaplan_api, todos):
    megaplan_api.get("todo/501", data=TODO)

    todo = await todos.get(501)

    assert todo.display_name() == "Созвон"


async def test_iterate_paginates_with_page_after(megaplan_api, todos):
    """Auto-pagination uses Todo references, like every other resource."""
    first = dict(TODO)
    second = dict(TODO, id="502")
    responses = [[first, second], []]

    def handler(request):
        from httpx import Response

        return Response(200, json={"meta": {"status": 200}, "data": responses.pop(0)})

    megaplan_api.router.request("GET", f"{megaplan_api.base_url}/api/v3/todo").mock(
        side_effect=handler
    )

    collected = [item.id async for item in todos.iterate(limit=2)]

    assert collected == [501, 502]


async def test_search_returns_base_entities(megaplan_api, todos):
    megaplan_api.get(
        "todo/search",
        data=[{"contentType": "Todo", "id": "501", "name": "Созвон"}],
    )

    results = await todos.search("Созвон")

    assert [r.id for r in results] == [501]
    assert results[0].name == "Созвон"


async def test_search_sends_q_query_param(megaplan_api, todos):
    route = megaplan_api.get("todo/search", data=[])

    await todos.search("звонок")

    assert sent_query(route) == {"q": "звонок"}


async def test_busy_days_returns_raw_dicts(megaplan_api, todos):
    """No typed model exists for TodosBusyDay yet; raw payload is returned as-is."""
    route = megaplan_api.get(
        "todo/busyDays",
        data=[{"date": "2026-08-20", "count": 3}],
    )

    days = await todos.busy_days(from_date="2026-08-01", to_date="2026-08-31")

    assert route.called
    assert days == [{"date": "2026-08-20", "count": 3}]
    assert sent_query(route) == {"from": "2026-08-01", "to": "2026-08-31"}


async def test_get_comments_uses_comments_subresource(megaplan_api, todos):
    megaplan_api.get(
        "todo/501/comments",
        data=[{"contentType": "Comment", "id": "1", "content": "Отлично"}],
    )

    comments = await todos.get_comments(501)

    assert [c.id for c in comments] == [1]
    assert comments[0].content == "Отлично"


async def test_linked_deals_use_deals_subresource(megaplan_api, todos):
    route = megaplan_api.get("todo/501/deals", data=[{"contentType": "Deal", "id": "9"}])

    deals = await todos.get_linked_deals(501)

    assert route.called
    assert [d.id for d in deals] == [9]


async def test_linked_tasks_use_issues_subresource(megaplan_api, todos):
    """The API calls a todo's tasks "issues", not "tasks"."""
    route = megaplan_api.get("todo/501/issues", data=[{"contentType": "Task", "id": "77"}])

    tasks = await todos.get_linked_tasks(501)

    assert route.called
    assert [t.id for t in tasks] == [77]


def test_todo_resource_is_exported_from_the_package():
    """Consumers import the resource from megaplan_sdk, not from internals."""
    from megaplan_sdk import TodosResource  # noqa: F401


async def test_create_sends_content_type_and_name(megaplan_api, todos):
    route = megaplan_api.post("todo", data={**TODO, "id": "600"})

    todo = await todos.create(name="Созвон с клиентом")

    assert todo.id == 600
    body = json.loads(route.calls[0].request.content)
    assert body["contentType"] == "Todo"
    assert body["name"] == "Созвон с клиентом"


async def test_create_passes_extra_fields_through(megaplan_api, todos):
    """**fields is a pure pass-through, in API notation (e.g. responsible)."""
    route = megaplan_api.post("todo", data={**TODO, "id": "600"})

    await todos.create(name="Созвон", responsible={"contentType": "Employee", "id": 5})

    body = json.loads(route.calls[0].request.content)
    assert body["responsible"] == {"contentType": "Employee", "id": 5}


async def test_update_sends_post_to_todo_id(megaplan_api, todos):
    route = megaplan_api.post("todo/501", data={**TODO, "name": "Перенесённый созвон"})

    todo = await todos.update(501, {"name": "Перенесённый созвон"})

    assert todo.name == "Перенесённый созвон"
    body = json.loads(route.calls[0].request.content)
    assert body == {"name": "Перенесённый созвон"}


async def test_delete_sends_delete_to_todo_id(megaplan_api, todos):
    route = megaplan_api.delete("todo/501")

    await todos.delete(501)

    assert route.called


async def test_finish_updates_status_via_plain_update(megaplan_api, todos):
    """finish() has no dedicated action route (confirmed 404) — it is sugar
    over update() that only changes `status`, confirmed on a live account to
    actually persist.
    """
    finished = {
        **TODO,
        "status": {"contentType": "TodoStatus", "id": "2", "masterType": "finished"},
    }
    route = megaplan_api.post("todo/501", data=finished)

    todo = await todos.finish(501, status_id=2)

    assert todo.is_finished() is True
    body = json.loads(route.calls[0].request.content)
    assert body == {"status": {"contentType": "TodoStatus", "id": "2"}}
