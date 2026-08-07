"""Client-side validation of deals.list(fields=[...]) (#BUG-3).

The deal list endpoint rejects a handful of field names with a raw 422 that
names no alternative. Verified against a live account 2026-08-07: `deadline`,
`createdAt`, `updatedAt` and `responsible` are rejected, while `description`,
`positions`, `comments` and the rest of the card fields are accepted.
"""

import pytest


async def test_deadline_is_rejected_before_the_request(megaplan_api, deals):
    """The 422 is predictable, so it should not cost a round trip."""
    route = megaplan_api.get("deal", data=[])

    with pytest.raises(ValueError, match="deadline"):
        await deals.list(limit=1, fields=["deadline"])

    assert route.call_count == 0


async def test_error_points_at_the_deal_field_that_exists(megaplan_api, deals):
    """Deals use `manager`, not `responsible` — say so instead of echoing 422."""
    with pytest.raises(ValueError, match="manager"):
        await deals.list(limit=1, fields=["responsible"])


async def test_foreign_timestamp_synonyms_are_rejected(megaplan_api, deals):
    """createdAt/updatedAt come from other CRM APIs; suggest the real names."""
    with pytest.raises(ValueError, match="timeCreated"):
        await deals.list(limit=1, fields=["createdAt"])

    with pytest.raises(ValueError, match="timeUpdated"):
        await deals.list(limit=1, fields=["updatedAt"])


async def test_supported_and_custom_fields_pass_through(megaplan_api, deals):
    """Only known-bad names are blocked: custom category fields must work."""
    route = megaplan_api.get("deal", data=[{"id": 1, "contentType": "Deal"}])

    await deals.list(
        limit=1,
        fields=["description", "manager", "Category1000075CustomFieldKodSdelki"],
    )

    assert route.call_count == 1
