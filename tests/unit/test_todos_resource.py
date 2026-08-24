"""Tests for TodosResource — reads and writes over todos ("Дела").

Read routes were confirmed by a live-account probe (2026-08-21): GET todo,
GET todo/{id}, GET todo/{id}/deals, GET todo/{id}/issues (note: issues, not
tasks — that is what test_linked_tasks_use_issues_subresource guards against),
GET todo/search, GET todo/busyDays, GET todo/{id}/comments.

Write routes were confirmed by a second live-account probe (2026-08-21, Task
7): POST todo (create), POST todo/{id} (update), DELETE todo/{id} — all 200.
POST todo/{id}/finish, /renew, /take (as dedicated routes) all 404 "No route
found" — those hypothesized routes do not exist.

A third live-account probe (2026-08-21, Task 7b) found the real action route:
the unified POST todo/{id}/doAction, documented in RAML and shared with Tasks
and Projects. Confirmed 200 for TodoFinishActionRequest (status changes;
resultText shows up as a Comment on the todo, not a Todo field) and
TodoRenewActionRequest (reverts a finished todo back to "scheduled" — 403s
"No act_renew rights" on a non-finished todo, which is server-side state
gating, not a broken route) and TodoTakeActionRequest (sets `responsible` to
the current user). TodoAcceptInvitationActionRequest/
TodoRejectInvitationActionRequest both 403 "No act_accept_invite/
act_reject_invite rights" from a single-account probe — the acting account is
never an invited participant on its own todo, so success could not be
confirmed, and TodoDeleteRepeatableActionRequest was not reachable either: no
`when` shape accepted by POST todo produces a repeating todo to test it on
(still 422, same as Task 1/7). None of those three actions are implemented.

Writes on live Todo were observed to be eventually consistent: a POST
returns 200 with the intended state immediately, but a GET issued right after
can still show the previous value for a few seconds before catching up
(worse under several rapid concurrent writes to the same todo). This is a
server-side characteristic, not something the SDK compensates for.
"""

import json
from urllib.parse import unquote

import pytest

from megaplan_sdk.constants import ContentType

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


async def test_list_passes_sort_by(megaplan_api, todos):
    route = megaplan_api.get("todo", data=[])

    await todos.list(
        sort_by=[{"contentType": "SortField", "fieldName": "timeCreated", "desc": True}],
    )

    query = sent_query(route)
    assert query["sortBy"] == [
        {"contentType": "SortField", "fieldName": "timeCreated", "desc": True}
    ]


async def test_list_q_is_converted_to_name_filter(megaplan_api, todos):
    """Regression guard for #5 (task 12b).

    Confirmed on the live stand: a raw ``q=`` is silently ignored by
    ``GET /todo`` — a filtered and an unfiltered call returned the same 50
    rows, none matching the needle. Same #11-class trap already fixed for
    tasks/deals: ``q`` must be converted to a real ``TodoFilter`` name
    filter, never sent raw.
    """
    route = megaplan_api.get("todo", data=[])

    await todos.list(q="звонок")

    query = sent_query(route)
    assert "q" not in query
    term = query["filter"]["config"]["termGroup"]["terms"][0]
    assert term["field"] == "name"
    assert term["comparison"] == "contains"
    assert term["value"] == "звонок"


async def test_list_q_with_filter_raises(todos):
    """Passing both q and filter is ambiguous — reject it, like tasks/deals do."""
    with pytest.raises(ValueError):
        await todos.list(q="x", filter={"contentType": "TodoFilter", "id": 1})


async def test_list_q_in_unsupported_field_raises(todos):
    """q_in with a field the server can't filter on raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        await todos.list(q="x", q_in=["description"])


async def test_list_rejects_sort_by_with_wrong_key_name(megaplan_api, todos):
    """Regression guard for #4 (task 12b).

    Confirmed on the live stand: ``sort_by=[{"field": "timeCreated", ...}]``
    (the plausible-looking but wrong key) 422s with ``'array' is not
    assignable to 'SortField[]'`` — the API expects ``fieldName``, not
    ``field``. The correct key (``fieldName``) works fine and needed no
    other change; this only catches the common mistake early with a clear
    message instead of the cryptic server 422.
    """
    with pytest.raises(ValueError, match="fieldName"):
        await todos.list(sort_by=[{"contentType": "SortField", "field": "timeCreated"}])


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

    days = await todos.busy_days()

    assert route.called
    assert days == [{"date": "2026-08-20", "count": 3}]
    assert route.calls[0].request.url.query == b""


async def test_busy_days_passes_filter_through_untouched(megaplan_api, todos):
    """Regression guard for #3 (task 12b).

    RAML has no from/to date params on ``/todo/busyDays`` — only
    ``filter``/``q``/pagination/``sortBy``. The old ``from_date``/``to_date``
    signature 422'd on every call (``There is extra field "from"...``);
    confirmed on the live stand that a plain call with no params (or an
    ad-hoc ``TodoFilter``) is what the endpoint actually accepts.
    """
    route = megaplan_api.get("todo/busyDays", data=[])

    await todos.busy_days(filter={"contentType": "TodoFilter", "id": 7})

    assert sent_query(route) == {"filter": {"contentType": "TodoFilter", "id": 7}}


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
    assert body == {"name": "Перенесённый созвон", "id": "501"}


async def test_update_body_carries_id_to_avoid_orphan_creation_bug(megaplan_api, todos):
    """Regression test for the orphan-creation bug (task 12b, #1).

    Confirmed on the live stand: ``POST /todo/{id}`` *without* ``"id"`` in the
    JSON body ignores the path id entirely and creates a brand-new Todo
    instead of updating the existing one (server returns 200 with a
    different ``data.id``). With ``"id"`` in the body, the same POST updates
    in place. ``TodosResource.update()`` must always inject it, so callers
    never have to remember the workaround themselves.
    """
    route = megaplan_api.post("todo/501", data={**TODO, "name": "Обновлено"})

    await todos.update(501, {"name": "Обновлено"})

    body = json.loads(route.calls[0].request.content)
    assert body["id"] == "501"


async def test_update_does_not_mutate_callers_dict(megaplan_api, todos):
    """update() must not mutate the caller's todo_data in place (immutability)."""
    megaplan_api.post("todo/501", data={**TODO, "name": "Обновлено"})
    todo_data = {"name": "Обновлено"}

    await todos.update(501, todo_data)

    assert todo_data == {"name": "Обновлено"}


async def test_update_overrides_caller_supplied_id_with_the_path_id(megaplan_api, todos):
    """A caller-supplied 'id' must not win over the id in the path (#1 fix guard)."""
    route = megaplan_api.post("todo/501", data={**TODO, "name": "Обновлено"})

    await todos.update(501, {"name": "Обновлено", "id": "999"})

    body = json.loads(route.calls[0].request.content)
    assert body["id"] == "501"


async def test_delete_sends_delete_to_todo_id(megaplan_api, todos):
    route = megaplan_api.delete("todo/501")

    await todos.delete(501)

    assert route.called


async def test_finish_sends_do_action_with_all_fields(megaplan_api, todos):
    """finish() posts a TodoFinishActionRequest to the shared doAction route."""
    finished = {
        **TODO,
        "status": {"contentType": "TodoStatus", "id": "3", "masterType": "success"},
    }
    route = megaplan_api.post("todo/501/doAction", data=finished)

    todo = await todos.finish(
        501,
        status_id=3,
        result_text="Готово",
        result_attaches=[{"contentType": "File", "id": 42}],
        notify_contractors=True,
    )

    assert todo.is_finished() is True
    body = json.loads(route.calls[0].request.content)
    assert body == {
        "contentType": "TodoFinishActionRequest",
        "status": {"contentType": "TodoStatus", "id": "3"},
        "resultText": "Готово",
        "resultAttaches": [{"contentType": "File", "id": 42}],
        "notifyContractors": True,
    }


async def test_finish_with_no_args_sends_only_content_type(megaplan_api, todos):
    """Every finish() field is optional; omitting them all sends a bare request."""
    route = megaplan_api.post("todo/501/doAction", data=TODO)

    await todos.finish(501)

    body = json.loads(route.calls[0].request.content)
    assert body == {"contentType": "TodoFinishActionRequest"}


async def test_renew_sends_do_action_renew(megaplan_api, todos):
    """renew() posts a bare TodoRenewActionRequest — it has no other fields."""
    route = megaplan_api.post("todo/501/doAction", data=TODO)

    todo = await todos.renew(501)

    assert todo.id == 501
    body = json.loads(route.calls[0].request.content)
    assert body == {"contentType": "TodoRenewActionRequest"}


async def test_take_sends_do_action_take(megaplan_api, todos):
    """take() posts a bare TodoTakeActionRequest — it has no other fields."""
    taken = {**TODO, "responsible": {"contentType": "Employee", "id": "7"}}
    route = megaplan_api.post("todo/501/doAction", data=taken)

    todo = await todos.take(501)

    assert todo.id == 501
    body = json.loads(route.calls[0].request.content)
    assert body == {"contentType": "TodoTakeActionRequest"}


def test_todo_content_type_constants_match_the_wire_values():
    """The action bodies are built from constants, not scattered literals."""
    assert ContentType.TODO_STATUS == "TodoStatus"
    assert ContentType.TODO_FINISH_ACTION_REQUEST == "TodoFinishActionRequest"
    assert ContentType.TODO_RENEW_ACTION_REQUEST == "TodoRenewActionRequest"
    assert ContentType.TODO_TAKE_ACTION_REQUEST == "TodoTakeActionRequest"
