"""Typed entity journal and deal link events (block C of 0.6.0).

Shapes verified on the stand 2026-08-05: /deal/{id}/history returns a mixed
stream of Changeset, Comment, TriggerLogSet and BasedOnHistory. BasedOnHistory
is the link/unlink record — undocumented, but the only way to learn *which*
link changed without diffing two states of the deal.
"""

from megaplan_sdk.models.history import BasedOnHistory, Changeset

CHANGESET = {
    "contentType": "Changeset",
    "id": "27786",
    "timeCreated": {"contentType": "DateTime", "value": "2025-08-08T08:07:24+00:00"},
    "type": "",
    "author": {"contentType": "Employee", "id": "1000003"},
    "changes": [
        {
            "contentType": "FieldChange",
            "field": "auditors",
            "description": "Борзов Максим добавил аудитора",
            "timeCreated": {"contentType": "DateTime", "value": "2025-08-08T08:07:24+00:00"},
            "oldValue": None,
            "newValue": [{"contentType": "Employee", "id": "1000055"}],
            "changedEntity": {"contentType": "Deal", "id": "219"},
            "author": {"contentType": "Employee", "id": "1000003"},
        }
    ],
}

LINK = {
    "contentType": "BasedOnHistory",
    "id": "1096",
    "timeCreated": {"contentType": "DateTime", "value": "2021-11-23T12:21:50+00:00"},
    "basedModel": {"contentType": "Deal", "id": "86"},
    "generatedModel": {"contentType": "Deal", "id": "219"},
    "user": {"contentType": "Employee", "id": "1000011"},
    "unlink": False,
    "description": "Борзов Максим привязал сделку",
}

UNLINK = {
    "contentType": "BasedOnHistory",
    "id": "1107",
    "timeCreated": {"contentType": "DateTime", "value": "2021-11-23T12:56:33+00:00"},
    "basedModel": {"contentType": "Deal", "id": "219"},
    "generatedModel": {"contentType": "Task", "id": "1000878"},
    "user": {"contentType": "Employee", "id": "1000011"},
    "unlink": True,
    "description": "Борзов Максим удалил связь со сделкой",
}

TRIGGER_LOG = {"contentType": "TriggerLogSet", "id": "3316"}


async def test_history_parses_changesets_with_field_changes(megaplan_api, deals):
    """A Changeset carries the individual field changes, typed."""
    megaplan_api.get("deal/219/history", data=[CHANGESET])

    entries = await deals.get_history(deal_id=219)

    entry = entries[0]
    assert isinstance(entry, Changeset)
    assert entry.id == 27786
    assert entry.changes is not None
    change = entry.changes[0]
    assert change.field == "auditors"
    assert change.old_value is None
    assert change.new_value == [{"contentType": "Employee", "id": "1000055"}]
    assert change.author is not None and change.author.id == 1000003


async def test_history_parses_link_records(megaplan_api, deals):
    """BasedOnHistory is the link/unlink record; unlink tells them apart."""
    megaplan_api.get("deal/219/history", data=[LINK, UNLINK])

    linked, unlinked = await deals.get_history(deal_id=219)

    assert isinstance(linked, BasedOnHistory)
    assert linked.unlink is False
    assert linked.based_model is not None and linked.based_model.id == 86
    assert linked.generated_model is not None and linked.generated_model.id == 219
    assert unlinked.unlink is True


async def test_history_keeps_unknown_entry_types_as_dicts(megaplan_api, deals):
    """The stream is open-ended; unknown contentTypes must not break parsing."""
    megaplan_api.get("deal/219/history", data=[TRIGGER_LOG])

    entries = await deals.get_history(deal_id=219)

    assert entries[0] == TRIGGER_LOG


async def test_history_raw_returns_untouched_payloads(megaplan_api, deals):
    """raw=True keeps the pre-0.6.0 behaviour for existing consumers."""
    megaplan_api.get("deal/219/history", data=[CHANGESET, LINK])

    entries = await deals.get_history(deal_id=219, raw=True)

    assert entries == [CHANGESET, LINK]


async def test_link_events_extract_the_other_side(megaplan_api, deals):
    """Each event says what was linked, by whom, and in which direction."""
    megaplan_api.get("deal/219/history", data=[CHANGESET, LINK, UNLINK])

    events = await deals.get_link_events(deal_id=219)

    assert [event.unlink for event in events] == [False, True]

    linked, unlinked = events
    assert linked.other.content_type == "Deal"
    assert linked.other.id == 86, "deal 219 was generated from deal 86"
    assert linked.is_source is False
    assert linked.user is not None and linked.user.id == 1000011
    assert unlinked.other.id == 1000878
    assert unlinked.is_source is True, "deal 219 is the basedModel of that link"


async def test_link_events_since_id_returns_only_newer_records(megaplan_api, deals):
    """Polling stores the last seen id; older records must not come back."""
    megaplan_api.get("deal/219/history", data=[LINK, UNLINK])

    events = await deals.get_link_events(deal_id=219, since_id=1096)

    assert [event.id for event in events] == [1107]


async def test_iterate_history_walks_pages(megaplan_api, deals):
    """Auto-pagination over the mixed journal stream."""
    from httpx import Response

    pages = [[LINK, UNLINK], [CHANGESET]]

    def handler(request):
        page = pages.pop(0) if pages else []
        return Response(200, json={"meta": {"status": 200}, "data": page})

    megaplan_api.router.request("GET", f"{megaplan_api.base_url}/api/v3/deal/219/history").mock(
        side_effect=handler
    )

    entries = [entry async for entry in deals.iterate_history(deal_id=219, limit=2)]

    assert [type(entry).__name__ for entry in entries] == [
        "BasedOnHistory",
        "BasedOnHistory",
        "Changeset",
    ]


async def test_get_linked_deals_reads_the_subresource(megaplan_api, deals):
    """Related deals come from /deal/{id}/linkedDeals (verified on the stand)."""
    route = megaplan_api.get(
        "deal/86/linkedDeals",
        data=[{"id": 219, "contentType": "Deal", "name": "Процесс"}],
    )

    linked = await deals.get_linked_deals(deal_id=86, limit=10)

    assert route.call_count == 1
    assert [deal.id for deal in linked] == [219]


async def test_get_linked_tasks_and_actual_variant(megaplan_api, deals):
    """Both linkedTasks and actualLinkedTasks are exposed."""
    all_route = megaplan_api.get(
        "deal/86/linkedTasks", data=[{"id": 1, "contentType": "Task", "name": "T1"}]
    )
    actual_route = megaplan_api.get(
        "deal/86/actualLinkedTasks", data=[{"id": 2, "contentType": "Task", "name": "T2"}]
    )

    assert [task.id for task in await deals.get_linked_tasks(deal_id=86)] == [1]
    assert [task.id for task in await deals.get_actual_linked_tasks(deal_id=86)] == [2]
    assert all_route.call_count == 1
    assert actual_route.call_count == 1


async def test_get_based_on_linked_deals_returns_ids(megaplan_api, deals):
    """The endpoint answers with a BasedOnDealIds envelope, not entities."""
    megaplan_api.get(
        "deal/86/basedOnLinkedDeals",
        data={"contentType": "BasedOnDealIds", "value": ["219", "220", "221"]},
    )

    ids = await deals.get_based_on_linked_deals(deal_id=86)

    assert ids == [219, 220, 221]
