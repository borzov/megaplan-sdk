"""EntityTodosMixin — get_todos() facades on five resources (/{entity}/{id}/todos).

Routes come from the RAML spec and were confirmed working by a live-account
probe for deal/task/project/employee (task 12). Contractor is the odd one
out: ``GET /contractor/{id}/todos`` 500s (task 12b) — but ``GET
/contractorCompany|contractorHuman/{id}/todos`` (the concrete subtype)
works, confirmed live 2026-08-21 — see ``ContractorsResource``'s docstring.
"""

import inspect

import pytest

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


async def test_task_todos_forwards_page_after(megaplan_api, tasks):
    """get_todos(page_after=...) is not silently dropped, unlike before this fix."""
    route = megaplan_api.get("task/1/todos", data=[])

    await tasks.get_todos(1, page_after={"contentType": "Todo", "id": 9})

    assert "pageAfter" in str(route.calls[0].request.url)


async def test_project_todos_hit_the_subresource(megaplan_api, projects):
    route = megaplan_api.get("project/42/todos", data=[TODO])

    items = await projects.get_todos(42)

    assert route.called
    assert [t.id for t in items] == [501]


async def test_contractor_todos_hit_the_concrete_subtype_route(megaplan_api, contractors):
    """GET /contractor/{id}/todos 500s; the concrete subtype route is what's actually called."""
    route = megaplan_api.get("contractorCompany/1001786/todos", data=[TODO])

    items = await contractors.get_todos(1001786, content_type="ContractorCompany")

    assert route.called
    assert [t.id for t in items] == [501]


async def test_contractor_todos_resolve_content_type_when_omitted(megaplan_api, contractors):
    """Without content_type, one extra get() resolves the subtype first."""
    megaplan_api.get("contractor/1001581", data={"id": 1001581, "contentType": "ContractorHuman"})
    route = megaplan_api.get("contractorHuman/1001581/todos", data=[TODO])

    items = await contractors.get_todos(1001581)

    assert route.called
    assert [t.id for t in items] == [501]


async def test_employee_todos_hit_the_subresource(megaplan_api, employees):
    route = megaplan_api.get("employee/1000003/todos", data=[TODO])

    items = await employees.get_todos(1000003)

    assert route.called
    assert [t.id for t in items] == [501]


async def test_get_todos_keeps_each_resources_own_id_keyword(
    megaplan_api, tasks, deals, projects, employees
):
    """The published keyword (README: ``deal_id=``, ``task_id=``, ...) still binds.

    A foreign keyword raises the ordinary ``TypeError`` a dedicated method
    would — the lifted method does not accept every resource's keyword at once.
    Positional calls are covered by the route tests above.
    """
    resources = (
        (tasks, "task", "task_id", "deal_id"),
        (deals, "deal", "deal_id", "task_id"),
        (projects, "project", "project_id", "task_id"),
        (employees, "employee", "employee_id", "task_id"),
    )
    for resource, segment, own_keyword, foreign_keyword in resources:
        megaplan_api.get(f"{segment}/1/todos", data=[])

        params = list(inspect.signature(resource.get_todos).parameters)
        assert params[0] == own_keyword

        await resource.get_todos(**{own_keyword: 1})

        with pytest.raises(TypeError, match="unexpected keyword argument"):
            await resource.get_todos(**{foreign_keyword: 1})


async def test_todos_have_no_get_todos(todos):
    """A todo's todos were never wrapped: ``GET /todo/{id}/todos`` is not a route.

    The method lives on a shared mixin, so it must behave as absent here rather
    than reach the server.
    """
    assert "get_todos" not in todos.__class__.__dict__
    with pytest.raises(AttributeError):
        await todos.get_todos(1)


async def test_employees_have_no_get_comments(employees):
    """Employees never had ``get_comments``; lifting it must not add one.

    Whether ``GET /employee/{id}/comments`` exists is unverified, so the call
    fails as a missing attribute instead of hitting that route.
    """
    assert "get_comments" not in employees.__class__.__dict__
    with pytest.raises(AttributeError):
        await employees.get_comments(1)
