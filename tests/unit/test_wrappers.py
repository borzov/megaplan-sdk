"""Unit tests for wrapper collapse: deals auditors via base helpers."""

import json


class TestDealsAuditorsViaBaseHelpers:
    """Deals auditors must go through the same seam as tasks/projects."""

    async def test_get_auditors_returns_list(self, megaplan_api, deals):
        route = megaplan_api.get(
            "deal/5/auditors",
            data=[{"id": 15, "contentType": "Employee"}],
        )

        auditors = await deals.get_auditors(5)

        assert route.call_count == 1
        assert len(auditors) == 1
        assert auditors[0]["id"] == 15

    async def test_add_auditor_sends_full_entity_link(self, megaplan_api, deals):
        route = megaplan_api.post(
            "deal/5/auditors",
            data={"id": 456, "contentType": "Employee"},
        )

        await deals.add_auditor(5, 456)

        body = json.loads(route.calls.last.request.content)
        assert body == {"id": 456, "contentType": "Employee"}

    async def test_remove_auditor_uses_deal_path_without_content_type(self, megaplan_api, deals):
        """API irregularity (RAML + verified on the stand 2026-07-02):
        DELETE /deal/{id}/auditors/{auditorId} — WITHOUT contentType, unlike
        /task/{id}/auditors/{contentType}/{auditorId}."""
        route = megaplan_api.delete("deal/5/auditors/456")

        await deals.remove_auditor(5, 456)

        assert route.call_count == 1
