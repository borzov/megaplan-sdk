"""Typed journal and link events for tasks, projects, contractors and todos.

Block from task 8 (0.6.1): the typed-journal facade that 0.6.0 shipped for
``deals`` (``get_history(raw=False)``, ``iterate_history()``,
``get_link_events()``) is rolled out to every other entity whose API exposes
``/{entity}/{id}/history`` — verified in the RAML for task, project,
contractor and todo. This is the last contract change to the journal: from
here on, additions only.
"""

from megaplan_sdk.models.history import BasedOnHistory, Changeset

CHANGESET = {
    "contentType": "Changeset",
    "id": "9001",
    "timeCreated": {"contentType": "DateTime", "value": "2026-08-20T09:00:00+00:00"},
    "changes": [{"contentType": "FieldChange", "field": "name"}],
}


def _based_on(generated_content_type: str, generated_id: str) -> dict:
    """Build a BasedOnHistory unlink record generated from deal 219."""
    return {
        "contentType": "BasedOnHistory",
        "id": "1097",
        "timeCreated": {"contentType": "DateTime", "value": "2026-08-20T10:00:00+00:00"},
        "basedModel": {"contentType": "Deal", "id": "219"},
        "generatedModel": {"contentType": generated_content_type, "id": generated_id},
        "unlink": True,
    }


# --- tasks ---------------------------------------------------------------


async def test_task_history_is_typed(megaplan_api, tasks):
    megaplan_api.get("task/77/history", data=[CHANGESET])

    entries = await tasks.get_history(77)

    assert isinstance(entries[0], Changeset)


async def test_task_history_raw_keeps_dicts(megaplan_api, tasks):
    megaplan_api.get("task/77/history", data=[CHANGESET])

    entries = await tasks.get_history(77, raw=True)

    assert entries[0]["contentType"] == "Changeset"


async def test_task_link_events_report_unlink(megaplan_api, tasks):
    megaplan_api.get("task/77/history", data=[_based_on("Task", "77")])

    events = await tasks.get_link_events(77)

    assert events[0].unlink is True
    assert events[0].other.id == 219


async def test_task_iterate_history_yields_typed_entries(megaplan_api, tasks):
    megaplan_api.get("task/77/history", data=[CHANGESET])

    entries = [entry async for entry in tasks.iterate_history(77)]

    assert isinstance(entries[0], Changeset)


# --- projects --------------------------------------------------------------


async def test_project_history_is_typed(megaplan_api, projects):
    megaplan_api.get("project/55/history", data=[CHANGESET])

    entries = await projects.get_history(55)

    assert isinstance(entries[0], Changeset)


async def test_project_history_raw_keeps_dicts(megaplan_api, projects):
    megaplan_api.get("project/55/history", data=[CHANGESET])

    entries = await projects.get_history(55, raw=True)

    assert entries[0]["contentType"] == "Changeset"


async def test_project_link_events_report_unlink(megaplan_api, projects):
    megaplan_api.get("project/55/history", data=[_based_on("Project", "55")])

    events = await projects.get_link_events(55)

    assert events[0].unlink is True
    assert events[0].other.id == 219


async def test_project_iterate_history_yields_typed_entries(megaplan_api, projects):
    megaplan_api.get("project/55/history", data=[CHANGESET])

    entries = [entry async for entry in projects.iterate_history(55)]

    assert isinstance(entries[0], Changeset)


# --- contractors -------------------------------------------------------------


async def test_contractor_history_is_typed(megaplan_api, contractors):
    megaplan_api.get("contractor/66/history", data=[CHANGESET])

    entries = await contractors.get_history(66)

    assert isinstance(entries[0], Changeset)


async def test_contractor_history_raw_keeps_dicts(megaplan_api, contractors):
    megaplan_api.get("contractor/66/history", data=[CHANGESET])

    entries = await contractors.get_history(66, raw=True)

    assert entries[0]["contentType"] == "Changeset"


async def test_contractor_link_events_report_unlink(megaplan_api, contractors):
    megaplan_api.get("contractor/66/history", data=[_based_on("Contractor", "66")])

    events = await contractors.get_link_events(66)

    assert events[0].unlink is True
    assert events[0].other.id == 219


async def test_contractor_iterate_history_yields_typed_entries(megaplan_api, contractors):
    megaplan_api.get("contractor/66/history", data=[CHANGESET])

    entries = [entry async for entry in contractors.iterate_history(66)]

    assert isinstance(entries[0], Changeset)


# --- todos -------------------------------------------------------------------


async def test_todo_history_is_typed(megaplan_api, todos):
    megaplan_api.get("todo/88/history", data=[CHANGESET])

    entries = await todos.get_history(88)

    assert isinstance(entries[0], Changeset)


async def test_todo_history_raw_keeps_dicts(megaplan_api, todos):
    megaplan_api.get("todo/88/history", data=[CHANGESET])

    entries = await todos.get_history(88, raw=True)

    assert entries[0]["contentType"] == "Changeset"


async def test_todo_link_events_report_unlink(megaplan_api, todos):
    megaplan_api.get("todo/88/history", data=[_based_on("Todo", "88")])

    events = await todos.get_link_events(88)

    assert events[0].unlink is True
    assert events[0].other.id == 219


async def test_todo_iterate_history_yields_typed_entries(megaplan_api, todos):
    megaplan_api.get("todo/88/history", data=[CHANGESET])

    entries = [entry async for entry in todos.iterate_history(88)]

    assert isinstance(entries[0], Changeset)


# --- sanity: BasedOnHistory type is importable and matches raw shape --------


async def test_based_on_history_model_parses_unlink_flag():
    entry = BasedOnHistory(**_based_on("Task", "77"))

    assert entry.unlink is True
    assert entry.generated_model is not None
    assert entry.generated_model.id == 77


# --- get_full_details(include_history=True) must not choke on typed entries -

# Regression for a live bug shipped with 0.6.0: DealFullDetails.history (and,
# before this fix, TaskFullDetails.history / ProjectFullDetails.history) was
# typed as list[dict[str, Any]], but get_full_details() feeds it straight from
# get_history(), which returns typed Changeset/BasedOnHistory entries for any
# journal record with a known contentType. Pydantic validation raised on a
# real journal payload. The earlier version of this test suite only ever fed
# get_full_details() a history entry without "contentType" (e.g.
# {"id": 1, "action": "created"}), which parse_history_entry passes through
# unchanged as a dict — that shape hid the bug entirely.


async def test_deal_full_details_history_is_typed(megaplan_api, deals):
    megaplan_api.get("deal/1", data={"id": 1, "contentType": "Deal", "name": "Test Deal"})
    megaplan_api.get("deal/1/history", data=[CHANGESET])

    details = await deals.get_full_details(deal_id=1, include_history=True)

    assert details.history is not None
    assert isinstance(details.history[0], Changeset)


async def test_task_full_details_history_is_typed(megaplan_api, tasks):
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task", "name": "Test Task"})
    megaplan_api.get("task/1/history", data=[CHANGESET])

    details = await tasks.get_full_details(task_id=1, include_history=True)

    assert details.history is not None
    assert isinstance(details.history[0], Changeset)


async def test_project_full_details_history_is_typed(megaplan_api, projects):
    megaplan_api.get("project/1", data={"id": 1, "contentType": "Project", "name": "Test Project"})
    megaplan_api.get("project/1/history", data=[CHANGESET])

    details = await projects.get_full_details(project_id=1, include_history=True)

    assert details.history is not None
    assert isinstance(details.history[0], Changeset)
