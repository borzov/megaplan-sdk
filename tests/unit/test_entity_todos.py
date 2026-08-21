"""EntityTodosMixin — get_todos() facades on five resources (/{entity}/{id}/todos).

Routes come from the RAML spec and were not confirmed by a live-account
probe — see Task 12 for that verification.
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


async def test_contractor_todos_hit_the_subresource(megaplan_api, contractors):
    route = megaplan_api.get("contractor/7/todos", data=[TODO])

    items = await contractors.get_todos(7)

    assert route.called
    assert [t.id for t in items] == [501]


async def test_employee_todos_hit_the_subresource(megaplan_api, employees):
    route = megaplan_api.get("employee/1000003/todos", data=[TODO])

    items = await employees.get_todos(1000003)

    assert route.called
    assert [t.id for t in items] == [501]
