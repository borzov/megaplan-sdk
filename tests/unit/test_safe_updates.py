"""Preview/apply protects against stale writes and preserves an audit trail."""

import asyncio
import json

import httpx
import pytest
from httpx import Response


def card(**fields):
    return {"id": 1, "contentType": "ContractorCompany", "name": "Before", **fields}


async def test_safe_apply_uses_concrete_write_route(contractors, megaplan_api, tmp_path):
    megaplan_api.get("contractor/1", data=card())
    preview = await contractors.update(1, {"name": "After"}, dry_run=True)
    route = megaplan_api.post("contractorCompany/1", data=card(name="After"))
    assert (
        await contractors.apply_update(preview, audit_path=tmp_path / "audit", actor="tester")
    ).name == "After"
    assert route.call_count == 1


async def test_preview_has_diff_and_never_posts(contractors, megaplan_api):
    megaplan_api.get("contractor/1", data=card())
    preview = await contractors.update(1, {"name": "After"}, dry_run=True)
    assert preview.changes[0].field == "name"
    assert preview.changes[0].before == "Before"
    assert preview.changes[0].after == "After"
    assert preview.changes[0].before_exists
    assert preview.patch == {"name": "After"}
    preview.patch["name"] = "Mutated"
    assert preview.patch["name"] == "After"


async def test_apply_writes_patch_and_two_audit_records(contractors, megaplan_api, tmp_path):
    megaplan_api.get("contractor/1", data=card())
    preview = await contractors.update(1, {"name": "After"}, dry_run=True)
    post = megaplan_api.post("contractorCompany/1", data=card(name="After"))
    path = tmp_path / "audit.jsonl"
    result = await contractors.apply_update(preview, audit_path=path, actor="tester")
    assert result.name == "After"
    assert json.loads(post.calls[0].request.content) == {
        "name": "After",
        "contentType": "ContractorCompany",
    }
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["event"] for r in records] == ["intent", "result"]
    assert records[0]["operation_id"] == records[1]["operation_id"]
    assert records[0]["actor"] == "tester"
    assert records[1]["response"]["data"]["name"] == "After"


async def test_conflict_prevents_post(contractors, megaplan_api, tmp_path):
    route = megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/contractor/1").mock(
        side_effect=[
            Response(200, json={"data": card()}),
            Response(200, json={"data": card(name="Someone else")}),
        ]
    )
    preview = await contractors.update(1, {"name": "After"}, dry_run=True)
    from megaplan_sdk.exceptions import UpdateConflictError

    with pytest.raises(UpdateConflictError):
        await contractors.apply_update(preview, audit_path=tmp_path / "audit", actor="tester")
    assert route.call_count == 2


async def test_noop_does_not_write_or_create_audit(contractors, megaplan_api, tmp_path):
    megaplan_api.get("contractor/1", data=card())
    preview = await contractors.update(1, {"name": "Before"}, dry_run=True)
    assert not preview.changes
    path = tmp_path / "audit"
    result = await contractors.apply_update(preview, audit_path=path, actor="tester")
    assert result.name == "Before"
    assert not path.exists()


async def test_missing_null_and_empty_are_distinct(contractors, megaplan_api):
    megaplan_api.get("contractor/1", data=card(description=None))
    preview = await contractors.update(1, {"description": "", "position": None}, dry_run=True)
    changes = {c.field: c for c in preview.changes}
    assert changes["description"].before is None and changes["description"].before_exists
    assert changes["description"].after == ""
    assert not changes["position"].before_exists
    assert preview.patch["position"] is None


async def test_preview_rejects_unknown_readonly_and_deprecated_fields(contractors, megaplan_api):
    megaplan_api.get("contractor/1", data=card(countDeals=10, inn=None))
    for patch in [{"typo": "x"}, {"countDeals": 2}, {"inn": "123"}]:
        with pytest.raises(ValueError):
            await contractors.update(1, patch, dry_run=True)


async def test_custom_fields_are_preserved_in_preview(contractors, megaplan_api):
    key = "Category123CustomFieldExample"
    megaplan_api.get("contractor/1", data=card(**{key: ""}))
    preview = await contractors.update(1, {key: "new"}, dry_run=True)
    assert preview.patch == {key: "new"}
    assert preview.changes[0].before == ""


async def test_online_reference_changes_do_not_conflict(contractors, megaplan_api, tmp_path):
    common = {"contentType": "Employee", "id": "2", "name": "Person"}
    megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/contractor/1").mock(
        side_effect=[
            Response(200, json={"data": card(responsibles=[{**common, "isOnline": False}])}),
            Response(200, json={"data": card(responsibles=[{**common, "isOnline": True}])}),
        ]
    )
    preview = await contractors.update(1, {"name": "After"}, dry_run=True)
    megaplan_api.post("contractorCompany/1", data=card(name="After"))
    assert (
        await contractors.apply_update(preview, audit_path=tmp_path / "audit", actor="tester")
    ).name == "After"


async def test_audit_unavailable_prevents_post(contractors, megaplan_api, tmp_path):
    megaplan_api.get("contractor/1", data=card())
    preview = await contractors.update(1, {"name": "After"}, dry_run=True)
    with pytest.raises(OSError):
        await contractors.apply_update(preview, audit_path=tmp_path, actor="tester")


async def test_audit_failure_after_post_reports_changed_server(
    contractors, megaplan_api, tmp_path, monkeypatch
):
    megaplan_api.get("contractor/1", data=card())
    preview = await contractors.update(1, {"name": "After"}, dry_run=True)
    post = megaplan_api.post("contractorCompany/1", data=card(name="After"))
    from megaplan_sdk import updates
    from megaplan_sdk.exceptions import UpdateAuditError

    calls = []

    def fail_second(path, record):
        calls.append(record)
        if len(calls) == 2:
            raise OSError("disk full")

    monkeypatch.setattr(updates, "_append_audit", fail_second)
    with pytest.raises(UpdateAuditError) as exc:
        await contractors.apply_update(preview, audit_path=tmp_path / "audit", actor="tester")
    assert exc.value.server_changed is True
    assert post.call_count == 1


async def test_legacy_update_remains_direct_and_permissive(contractors, megaplan_api):
    route = megaplan_api.post("contractor/1", data=card(inn="old"))
    result = await contractors.update(1, {"inn": "old"})
    assert result.inn == "old"
    assert json.loads(route.calls[0].request.content) == {"inn": "old"}


async def test_nested_business_field_with_same_id_is_not_a_noop(contractors, megaplan_api):
    key = "Category123CustomFieldExample"
    old = {"contentType": "CustomValue", "id": "7", "value": "old"}
    megaplan_api.get("contractor/1", data=card(**{key: old}))
    preview = await contractors.update(1, {key: {**old, "value": "new"}}, dry_run=True)
    assert len(preview.changes) == 1


async def test_nested_business_edit_conflicts(contractors, megaplan_api, tmp_path):
    key = "Category123CustomFieldExample"
    old = {"contentType": "CustomValue", "id": "7", "value": "old"}
    megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/contractor/1").mock(
        side_effect=[
            Response(200, json={"data": card(**{key: old})}),
            Response(200, json={"data": card(**{key: {**old, "value": "changed"}})}),
        ]
    )
    preview = await contractors.update(1, {"name": "After"}, dry_run=True)
    from megaplan_sdk.exceptions import UpdateConflictError

    with pytest.raises(UpdateConflictError):
        await contractors.apply_update(preview, audit_path=tmp_path / "audit", actor="tester")


async def test_unknown_post_outcome_is_explicit_and_audited(contractors, megaplan_api, tmp_path):
    megaplan_api.get("contractor/1", data=card())
    preview = await contractors.update(1, {"name": "After"}, dry_run=True)
    route = megaplan_api.router.post(f"{megaplan_api.base_url}/api/v3/contractorCompany/1").mock(
        side_effect=httpx.ReadTimeout("write may have completed")
    )
    from megaplan_sdk.exceptions import UpdateAuditError

    path = tmp_path / "audit"
    with pytest.raises(UpdateAuditError) as exc:
        await contractors.apply_update(preview, audit_path=path, actor="tester")
    assert exc.value.server_changed is None
    assert route.call_count == 1
    assert json.loads(path.read_text().splitlines()[1])["outcome"] == "unknown"


async def test_cancelled_post_records_unknown_outcome(contractors, megaplan_api, tmp_path):
    megaplan_api.get("contractor/1", data=card())
    preview = await contractors.update(1, {"name": "After"}, dry_run=True)

    async def cancel(request):
        raise asyncio.CancelledError

    megaplan_api.router.post(f"{megaplan_api.base_url}/api/v3/contractorCompany/1").mock(
        side_effect=cancel
    )
    path = tmp_path / "audit"
    with pytest.raises(asyncio.CancelledError):
        await contractors.apply_update(preview, audit_path=path, actor="tester")
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(records) == 2
    assert records[1]["error_type"] == "CancelledError"
    assert records[1]["outcome"] == "unknown"
