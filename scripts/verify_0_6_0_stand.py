"""Manual verification of 0.6.0 against a live stand (read-only).

Covers: notifications (#FR-F), raw() (#BUG-1), linkedTasks/include_related_tasks,
expand replace mode (#BUG-2), dedup backfill (#BUG-4), fields validation (#BUG-3),
link events, bulk (#FR-E), DateOnly (#FR-G).

Usage:
    MEGAPLAN_BASE_URL=... MEGAPLAN_ACCESS_TOKEN=... \\
        python scripts/verify_0_6_0_stand.py DEAL_ID [DEAL_WITH_LINKS_ID]
"""

import asyncio
import os
import sys

from megaplan_sdk import MegaplanClient, normalize_state_name
from megaplan_sdk.exceptions import ValidationError
from megaplan_sdk.models.employee import Employee


async def main() -> None:
    deal_id = int(sys.argv[1])
    linked_deal_id = int(sys.argv[2]) if len(sys.argv) > 2 else deal_id

    async with MegaplanClient(
        os.environ["MEGAPLAN_BASE_URL"],
        access_token=os.environ["MEGAPLAN_ACCESS_TOKEN"],
    ) as mp:
        # FR-F: notifications carry the server-side mention flag
        notifications = await mp.notifications.list(limit=20)
        mentions = [n for n in notifications if n.is_mention]
        print(f"#FR-F notifications={len(notifications)} mentions={len(mentions)}")
        assert notifications, "no notifications returned"
        sample = notifications[0]
        print(f"        entity_ref={sample.entity_ref} sender={sample.sender}")
        counter = await mp.notifications.counter()
        print(f"        counter={counter.count} attributes={counter.attributes}")

        # BUG-1: raw() reaches an endpoint with no resource, no manual literal
        body = await mp.raw("GET", "/api/v3/todo", query={"limit": 2})
        print(f"#BUG-1 raw /todo status={body['meta']['status']} items={len(body['data'])}")

        # C1: the deal's tasks come from linkedTasks, matching tasksCount
        details = await mp.deals.get_full_details(deal_id=deal_id, include_related_tasks=True)
        counted = details.deal.model_dump(by_alias=True).get("tasksCount")
        print(f"#C1 tasksCount={counted} related_tasks={len(details.related_tasks or [])}")

        # BUG-2: expand keeps the type and loses no field
        fields = ["name", "state", "manager"]
        plain = (await mp.deals.list(limit=1, fields=fields))[0]
        expanded = (await mp.deals.list(limit=1, fields=fields, expand=["manager"]))[0]
        plain_dump = plain.model_dump(by_alias=True)
        expanded_dump = expanded.model_dump(by_alias=True)
        lost = [f for f in fields if plain_dump.get(f) and not expanded_dump.get(f)]
        print(f"#BUG-2 type={type(expanded).__name__} id={expanded_dump['id']} lost={lost}")
        assert type(plain) is type(expanded), "expand changed the entity type"
        assert not lost, f"expand lost fields: {lost}"
        if expanded.manager is not None:
            assert isinstance(expanded.manager, Employee), "manager was not expanded"

        # BUG-4: repeated references keep their name without expand
        listed = await mp.deals.list(limit=30, fields=["manager"])
        refs = [d.manager for d in listed if d.manager is not None]
        bare = [r for r in refs if not getattr(r, "name", None)]
        print(f"#BUG-4 manager refs={len(refs)} still bare={len(bare)}")

        # BUG-3: unsupported list fields fail on the client with an explanation
        try:
            await mp.deals.list(limit=1, fields=["deadline"])
            raise AssertionError("deadline must be rejected client-side")
        except ValueError as exc:
            print(f"#BUG-3 {exc}")
        try:
            await mp.raw("GET", "/api/v3/deal", query={"limit": 1, "fields": ["deadline"]})
            raise AssertionError("server unexpectedly accepted deadline")
        except ValidationError as exc:
            print(f"#BUG-3 server still says: {exc}")

        # Links: current state and the journal events behind it
        linked = await mp.deals.get_linked_deals(deal_id=linked_deal_id, limit=10)
        based_on = await mp.deals.get_based_on_linked_deals(deal_id=linked_deal_id)
        events = await mp.deals.get_link_events(deal_id=linked_deal_id)
        print(f"#links linkedDeals={[d.id for d in linked]} basedOn={based_on}")
        print(f"#links events={len(events)} unlink={[e.id for e in events if e.unlink]}")
        if events:
            newest = max(e.id for e in events if e.id is not None)
            assert not await mp.deals.get_link_events(
                deal_id=linked_deal_id, since_id=newest
            ), "since_id must exclude already-seen events"
            print(f"#links since_id={newest} → 0 new events")

        # FR-E: one request for many deals, per-call statuses
        many = await mp.deals.get_linked_deals_many([deal_id, linked_deal_id])
        results = await mp.bulk(
            [
                {"method": "GET", "url": f"/api/v3/deal/{linked_deal_id}/linkedDeals"},
                {"method": "GET", "url": "/api/v3/deal/99999999"},
            ]
        )
        print(f"#FR-E linked_many={ {k: len(v) for k, v in many.items()} }")
        print(f"#FR-E bulk statuses={[r.status for r in results]}")
        assert [r.status for r in results] == [200, 404], "partial failure must survive"

        # FR-G / NOTE-2: typed birthday and comparable state names
        employees = await mp.employees.list(limit=50)
        with_birthday = [e for e in employees if e.birthday is not None]
        if with_birthday:
            birthday = with_birthday[0].birthday
            print(f"#FR-G birthday month={birthday.month} day={birthday.day} date={birthday.date}")
        states = {normalize_state_name(getattr(d.state, "name", None)) for d in listed}
        print(f"#NOTE-2 normalized states={sorted(s for s in states if s)[:5]}")

    print("\nAll 0.6.0 stand checks passed.")


asyncio.run(main())
