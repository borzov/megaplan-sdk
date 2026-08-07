"""Backfilling server-deduplicated references (#BUG-4).

The server embeds a repeated linked entity fully only at its first occurrence in
a response; every later mention — even in a different field of another item — is
reduced to a bare {contentType, id}. The full object is already in the payload,
so the SDK fills the repeats from it instead of making the consumer keep an
{id: name} dictionary or fetch the entities again.
"""

import logging

OWNER_FULL = {"contentType": "Employee", "id": 10, "name": "Гусев Максим", "lastName": "Гусев"}
OWNER_BARE = {"contentType": "Employee", "id": 10}


async def test_repeat_gets_the_name_from_the_first_occurrence(megaplan_api, tasks):
    """The second task's owner is bare on the wire but named after parsing."""
    megaplan_api.get(
        "task",
        data=[
            {"id": 1, "contentType": "Task", "name": "First", "owner": OWNER_FULL},
            {"id": 2, "contentType": "Task", "name": "Second", "owner": OWNER_BARE},
        ],
    )

    listed = await tasks.list(limit=2, fields=["owner"])

    assert listed[0].owner is not None and listed[0].owner.name == "Гусев Максим"
    assert listed[1].owner is not None and listed[1].owner.name == "Гусев Максим"


async def test_backfill_crosses_reference_fields(megaplan_api, tasks):
    """Dedup is per response, not per field: owner fills a bare responsible."""
    megaplan_api.get(
        "task",
        data=[
            {"id": 1, "contentType": "Task", "name": "First", "owner": OWNER_FULL},
            {"id": 2, "contentType": "Task", "name": "Second", "responsible": OWNER_BARE},
        ],
    )

    listed = await tasks.list(limit=2, fields=["owner", "responsible"])

    assert listed[1].responsible is not None
    assert listed[1].responsible.name == "Гусев Максим"


async def test_backfill_does_not_invent_names(megaplan_api, tasks):
    """A reference with no full occurrence anywhere stays bare — no guessing."""
    megaplan_api.get(
        "task",
        data=[
            {"id": 1, "contentType": "Task", "name": "First", "owner": OWNER_BARE},
            {
                "id": 2,
                "contentType": "Task",
                "name": "Second",
                "owner": {"contentType": "Employee", "id": 11},
            },
        ],
    )

    listed = await tasks.list(limit=2, fields=["owner"])

    assert listed[0].owner is not None and listed[0].owner.name is None
    assert listed[1].owner is not None and listed[1].owner.name is None


async def test_backfill_matches_on_content_type_too(megaplan_api, deals):
    """Same id, different entity type is a different entity."""
    megaplan_api.get(
        "deal",
        data=[
            {"id": 1, "contentType": "Deal", "name": "First", "manager": OWNER_FULL},
            {
                "id": 2,
                "contentType": "Deal",
                "name": "Second",
                "contractor": {"contentType": "Contractor", "id": 10},
            },
        ],
    )

    listed = await deals.list(limit=2, fields=["manager", "contractor"])

    assert listed[1].contractor is not None
    assert listed[1].contractor.name is None


async def test_no_dedup_warning_once_references_are_backfilled(megaplan_api, tasks, caplog):
    """#36's advice becomes unnecessary when the SDK already repaired the page."""
    megaplan_api.get(
        "task",
        data=[
            {"id": 1, "contentType": "Task", "name": "First", "owner": OWNER_FULL},
            {"id": 2, "contentType": "Task", "name": "Second", "owner": OWNER_BARE},
        ],
    )

    with caplog.at_level(logging.WARNING):
        await tasks.list(limit=2, fields=["owner"])

    assert "deduplicated" not in caplog.text
