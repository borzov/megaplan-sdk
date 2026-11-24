"""Read-only acceptance checks for the 0.8.0 client on a populated account."""

import os
import re
from collections import defaultdict
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio

from megaplan_sdk import MegaplanClient, TaskQuery

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.getenv("MEGAPLAN_LIVE_READ_080") != "1",
        reason="Enable with MEGAPLAN_LIVE_READ_080=1 on a populated account",
    ),
]


@pytest_asyncio.fixture
async def live_client() -> AsyncIterator[MegaplanClient]:
    async with MegaplanClient(
        os.environ["MEGAPLAN_URL"],
        username=os.getenv("MEGAPLAN_USERNAME"),
        password=os.getenv("MEGAPLAN_PASSWORD"),
        access_token=os.getenv("MEGAPLAN_ACCESS_TOKEN"),
    ) as client:
        yield client


async def test_completed_task_search(live_client: MegaplanClient) -> None:
    tasks = live_client.tasks
    rows = await tasks.list(include_archive=True, statuses=["completed"], limit=5, fields=["name"])
    sample = next((row for row in rows if row.name), None)
    if sample is None or not sample.name:
        pytest.skip("Requires a completed task with a name")
    for fields in (["name"], ["name", "statement"]):
        query = TaskQuery().include_archive().statuses("completed").search(sample.name, fields)
        assert any(row.id == sample.id for row in await tasks.list_by(query.limit(100)))
        assert not await tasks.list(include_archive=True, q=uuid4().hex, q_in=fields)


async def test_staff_and_mixed_cards(live_client: MegaplanClient) -> None:
    active = {employee.id async for employee in live_client.employees.iterate()}
    staff = [
        employee
        async for employee in live_client.employees.iterate(include_dismissed=True, limit=7)
    ]
    ids = {employee.id for employee in staff}
    assert active <= ids and len(ids) == len(staff)
    tasks = await live_client.tasks.list(limit=1)
    if not tasks or not staff:
        pytest.skip("Requires a task and an employee visible to the current user")
    links = [tasks[0], staff[0], tasks[0]]
    result = await live_client.get_entities_by_links(links)
    task_key = (tasks[0].content_type, tasks[0].id)
    staff_key = (staff[0].content_type, staff[0].id)
    keys = [task_key, staff_key, task_key]
    assert [(row["contentType"], int(row["id"])) for row in result.items] == keys
    assert not result.missing
    assert result.resolved_via == {keys[0]: "bulk", keys[1]: "get"}


async def test_exact_inn_owners(live_client: MegaplanClient) -> None:
    owners: dict[str, set[tuple[str, int]]] = defaultdict(set)
    by_kpp: dict[tuple[str, str], set[tuple[str, int]]] = defaultdict(set)
    async for payer in live_client.payers.iterate(fields=["inn", "kpp", "contractor", "isDropped"]):
        owner = payer.contractor
        inn = (payer.inn or "").replace(" ", "")
        if payer.is_dropped or not re.fullmatch(r"(?:[0-9]{10}|[0-9]{12})", inn) or owner is None:
            continue
        if owner.content_type in ("ContractorCompany", "ContractorHuman"):
            key = (owner.content_type, owner.id)
            owners[inn].add(key)
            if payer.kpp:
                by_kpp[(inn, payer.kpp)].add(key)
    if not owners:
        pytest.skip("Requires an active payer with a valid INN")
    inn = max(
        owners,
        key=lambda code: (len(owners[code]), any(t == "ContractorHuman" for t, _ in owners[code])),
    )
    cards = await live_client.contractors.find_by_inn(inn)
    assert len(cards) == len(owners[inn]) and {(c.content_type, c.id) for c in cards} == owners[inn]
    if by_kpp:
        code, kpp = next(iter(by_kpp))
        cards = await live_client.contractors.find_by_inn(code, kpp)
        assert {(c.content_type, c.id) for c in cards} == by_kpp[(code, kpp)]
    missing = next(code for n in range(len(owners) + 1) if (code := f"{n:012d}") not in owners)
    assert not await live_client.contractors.find_by_inn(missing)
