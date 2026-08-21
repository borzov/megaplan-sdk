"""EntityTodosMixin — get_todos() facades on four resources (/{entity}/{id}/todos).

Routes come from the RAML spec and were confirmed working by a live-account
probe for deal/task/project/employee (task 12). Contractor is deliberately
absent: ``GET /contractor/{id}/todos`` 500s on the live server (task 12b,
see ``ContractorsResource``'s docstring) — the SDK does not expose it.
"""

TODO = {
    "contentType": "Todo",
    "id": "501",
    "name": "Созвон",
    "status": {"contentType": "TodoStatus", "id": "1", "masterType": "scheduled"},
    "timeCreated": {"contentType": "DateTime", "value": "2026-08-20T09:00:00+00:00"},
}


async def test_deal_todos_hit_the_subresource(megaplan_api, deals):
    route = megaplan_api.get("deal/86/todos", data=[TODO])

    items = await deals.get_todos(86)

    assert route.called
    assert [t.id for t in items] == [501]


async def test_task_todos_hit_the_subresource(megaplan_api, tasks):
    route = megaplan_api.get("task/1006256/todos", data=[TODO])

    items = await tasks.get_todos(1006256)

    assert route.called
    assert items[0].name == "Созвон"


async def test_project_todos_hit_the_subresource(megaplan_api, projects):
    route = megaplan_api.get("project/42/todos", data=[TODO])

    items = await projects.get_todos(42)

    assert route.called
    assert [t.id for t in items] == [501]


def test_contractors_has_no_get_todos(contractors):
    """Removed in 0.6.1 (task 12b, #2): GET /contractor/{id}/todos 500s on the live server."""
    assert not hasattr(contractors, "get_todos")


async def test_employee_todos_hit_the_subresource(megaplan_api, employees):
    route = megaplan_api.get("employee/1000003/todos", data=[TODO])

    items = await employees.get_todos(1000003)

    assert route.called
    assert [t.id for t in items] == [501]
