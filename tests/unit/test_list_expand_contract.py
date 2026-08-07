"""Contract for expand= on list endpoints (#BUG-2, breaking change in 0.6.0).

Reported symptom: ``deals.list(fields=[...], expand=["manager"])`` looked like it
lost every field — ``model_dump()`` returned a different shape and ``d["id"]``
was None. Root cause: list() wrapped entities into DealFullDetails, so the dump
described the container, not the deal.

Contract now: expand never changes the object type. It loads the referenced
entities in place, so a deal stays a Deal — with or without expand.
"""

from megaplan_sdk.models.deal import Deal
from megaplan_sdk.models.employee import Employee
from megaplan_sdk.models.task import Task

DEAL = {
    "id": 1965,
    "contentType": "Deal",
    "name": "1042",
    "state": {"contentType": "ProgramState", "id": "108", "name": "Новая заявка"},
    "manager": {"contentType": "Employee", "id": 1000056},
}

MANAGER = {
    "id": 1000056,
    "contentType": "Employee",
    "firstName": "Максим",
    "lastName": "Гусев",
}

FIELDS = ["name", "state", "manager"]


async def test_expand_keeps_the_entity_type(megaplan_api, deals):
    """The negative control from the bug report: same type, same fields, same ids."""
    megaplan_api.get("deal", data=[DEAL])
    megaplan_api.get("employee/1000056", data=MANAGER)

    plain = await deals.list(limit=1, fields=FIELDS)
    expanded = await deals.list(limit=1, fields=FIELDS, expand=["manager"])

    assert isinstance(expanded[0], Deal)
    assert expanded[0].id == plain[0].id

    plain_dump = plain[0].model_dump(by_alias=True)
    expanded_dump = expanded[0].model_dump(by_alias=True)
    lost = [field for field in FIELDS if plain_dump.get(field) and not expanded_dump.get(field)]
    assert not lost, f"expand lost fields: {lost}"
    assert expanded_dump["id"] == 1965
    assert expanded_dump["state"]["name"] == "Новая заявка"


async def test_expand_fills_the_reference_in_place(megaplan_api, deals):
    """The expanded reference carries the full entity, not a bare {contentType, id}."""
    megaplan_api.get("deal", data=[DEAL])
    megaplan_api.get("employee/1000056", data=MANAGER)

    expanded = await deals.list(limit=1, expand=["manager"])

    manager = expanded[0].manager
    assert manager is not None
    assert manager.last_name == "Гусев"
    assert manager.display_name() == "Максим Гусев"


async def test_expand_is_opt_in_and_leaves_plain_listing_untouched(megaplan_api, deals):
    """Without expand the reference stays bare; with it, the full entity is loaded."""
    megaplan_api.get("deal", data=[DEAL])
    megaplan_api.get("employee/1000056", data=MANAGER)

    expanded = await deals.list(limit=1, expand=["manager"])
    plain = await deals.list(limit=1)

    assert isinstance(expanded[0].manager, Employee)
    assert expanded[0].manager.last_name == "Гусев"
    assert not isinstance(plain[0].manager, Employee), "plain listing keeps the bare reference"


async def test_iterate_yields_the_entity_type_with_expand(megaplan_api, tasks):
    """iterate(expand=...) must yield Task, matching its annotation."""
    megaplan_api.get(
        "task",
        data=[
            {
                "id": 1,
                "contentType": "Task",
                "name": "Task",
                "owner": {"contentType": "Employee", "id": 1000056},
            }
        ],
    )
    megaplan_api.get("employee/1000056", data=MANAGER)

    collected = [task async for task in tasks.iterate(limit=100, expand=["owner"])]

    assert len(collected) == 1
    assert isinstance(collected[0], Task)
    assert collected[0].owner is not None
    assert collected[0].owner.last_name == "Гусев"
