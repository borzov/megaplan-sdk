"""Opt-in live probe using only newly created, clearly marked test objects.

The probe checks partial updates, null/empty clearing, contact array replacement
and available signatory fields. It removes its payer and soft-drops its company
in finally. Credentials come from the environment or an explicit env file;
only parameter names and aggregate results are printed.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from megaplan_sdk import MegaplanClient, NotFoundError, ValidationError
from megaplan_sdk.updates import _append_audit

PREFIX = "ТЕСТ SDK, не трогать"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Require an explicit opt-in and a chosen account contractor type."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-test-writes", action="store_true", required=True)
    parser.add_argument("--contractor-type-id", type=int, required=True)
    parser.add_argument("--audit-path", type=Path, required=True)
    parser.add_argument("--actor", default=getpass.getuser())
    parser.add_argument(
        "--env-file", type=Path, default=Path(__file__).resolve().parents[1] / ".env.local"
    )
    parser.add_argument("--base-url", default=None)
    return parser.parse_args(argv)


async def probe(
    client: MegaplanClient,
    *,
    contractor_type_id: int,
    audit_path: Path,
    actor: str,
) -> dict[str, Any]:
    """Exercise reviewed writes on owned test objects and clean them up.

    Args:
        client: Authenticated client configured with max_retries=0.
        contractor_type_id: Existing ContractorType ID selected for this account.
        audit_path: JSONL file in an existing private directory.
        actor: Operator identity.

    Returns:
        Aggregate check results and created IDs for audit reconciliation.

    Raises:
        RuntimeError: A check or cleanup failed; inspect the local audit.
    """
    if client._http.max_retries != 0:
        raise ValueError("The live write probe requires max_retries=0")
    marker = f"{PREFIX} {uuid.uuid4().hex[:12]}"
    owned: dict[str, int] = {}
    automatic_payers: set[int] = set()
    report: dict[str, Any] = {"marker": marker}

    async def raw_step(
        label: str,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        remember: str | None = None,
    ) -> dict[str, Any]:
        op = str(uuid.uuid4())
        common = {
            "operation_id": op,
            "actor": actor,
            "label": label,
            "path": path,
            "owned_ids": dict(owned),
        }
        await asyncio.to_thread(
            _append_audit,
            audit_path,
            {
                **common,
                "event": "probe_intent",
                "time": datetime.now(UTC).isoformat(),
                "request": payload,
            },
        )
        try:
            response = await client.raw(method, path, json=payload)
            if remember is not None:
                owned[remember] = int(response["data"]["id"])
                if remember == "company":
                    automatic_payers.update(
                        int(p["id"]) for p in response["data"].get("payers", [])
                    )
        except Exception as exc:
            await asyncio.to_thread(
                _append_audit,
                audit_path,
                {
                    **common,
                    "event": "probe_error",
                    "time": datetime.now(UTC).isoformat(),
                    "error_type": type(exc).__name__,
                    "outcome": "unknown",
                    "owned_ids": dict(owned),
                },
            )
            raise
        await asyncio.to_thread(
            _append_audit,
            audit_path,
            {
                **common,
                "event": "probe_result",
                "time": datetime.now(UTC).isoformat(),
                "response": response,
                "owned_ids": dict(owned),
            },
        )
        return response

    async def patch_payer(data: dict[str, Any]) -> None:
        preview = await client.payers.update(owned["payer"], data, dry_run=True)
        await client.payers.apply_update(preview, audit_path=audit_path, actor=actor)

    async def patch_company(data: dict[str, Any]) -> None:
        preview = await client.contractors.update(owned["company"], data, dry_run=True)
        await client.contractors.apply_update(preview, audit_path=audit_path, actor=actor)

    try:
        await raw_step(
            "create company",
            "POST",
            "/api/v3/contractorCompany",
            {
                "contentType": "ContractorCompany",
                "name": marker,
                "description": marker,
                "type": {"contentType": "ContractorType", "id": contractor_type_id},
            },
            remember="company",
        )
        await raw_step(
            "create payer",
            "POST",
            f"/api/v3/contractor/{owned['company']}/payers",
            {
                "contentType": "Payer",
                "type": "Legal",
                "country": {"contentType": "Country", "id": "RU"},
                "name": marker,
                "bank": "SDK test bank",
            },
            remember="payer",
        )
        initial = await client.payers.get(owned["payer"])
        await patch_payer({"name": marker + " updated"})
        after = await client.payers.get(owned["payer"])
        report["partial_payer_preserves_bank"] = after.bank == initial.bank
        if not report["partial_payer_preserves_bank"]:
            raise RuntimeError("Partial payer POST erased an unspecified field")
        await patch_payer({"bank": ""})
        report["empty_string_clears"] = (await client.payers.get(owned["payer"])).bank in ("", None)
        if not report["empty_string_clears"]:
            raise RuntimeError("Empty-string clearing did not clear the optional bank")
        try:
            await patch_payer({"bank": None})
            report["null_clears"] = (await client.payers.get(owned["payer"])).bank in ("", None)
            if not report["null_clears"]:
                raise RuntimeError("Null was accepted but did not clear the optional bank")
        except ValidationError:
            report["null_clears"] = False
        await patch_payer({"bank": "SDK test bank"})
        payer = await client.payers.get(owned["payer"])
        custom = next(
            (
                key
                for key, value in (payer.model_extra or {}).items()
                if key.startswith("Category") and "CustomField" in key and isinstance(value, str)
            ),
            None,
        )
        report["custom_field_checked"] = custom is not None
        if custom is not None:
            await patch_payer({custom: marker})
            if (await client.payers.get(owned["payer"])).model_extra[custom] != marker:
                raise RuntimeError("Custom payer field did not persist")
            await patch_payer({custom: ""})
        company = await client.contractors.get(owned["company"])
        await patch_company({"description": marker + " updated"})
        report["partial_company_preserves_name"] = (
            await client.contractors.get(owned["company"])
        ).name == company.name
        if not report["partial_company_preserves_name"]:
            raise RuntimeError("Partial company POST erased its name")
        two = [
            {"contentType": "ContactInfo", "type": "email", "value": "sdk-one@example.invalid"},
            {"contentType": "ContactInfo", "type": "email", "value": "sdk-two@example.invalid"},
        ]
        await patch_company({"contactInfo": two})
        await patch_company({"contactInfo": two[:1]})
        contacts = (await client.contractors.get(owned["company"])).contact_info or []
        report["contact_array_replaced"] = (
            len(contacts) == 1 and contacts[0].value == two[0]["value"]
        )
        if not report["contact_array_replaced"]:
            raise RuntimeError("Contact array replacement failed")
    finally:
        cleanup_errors: list[str] = []
        if "payer" in owned:
            try:
                current = await client.payers.get(owned["payer"])
                if not current.contractor or current.contractor.id != owned["company"]:
                    raise RuntimeError("Test payer ownership changed; refusing cleanup")
                await raw_step("delete owned payer", "DELETE", f"/api/v3/payer/{owned['payer']}")
                try:
                    report["cleanup_payer"] = (
                        await client.payers.get(owned["payer"])
                    ).is_dropped is True
                except NotFoundError:
                    report["cleanup_payer"] = True
                if not report["cleanup_payer"]:
                    raise RuntimeError("Payer deletion was not confirmed")
            except Exception as exc:
                cleanup_errors.append(f"payer/{owned['payer']}: {type(exc).__name__}")
        if "company" in owned:
            try:
                current = await client.contractors.get(owned["company"])
                if current.name != marker:
                    raise RuntimeError("Test company marker changed; refusing cleanup")
                await raw_step(
                    "soft drop owned company",
                    "DELETE",
                    f"/api/v3/contractorCompany/{owned['company']}",
                    {"contentType": "DeleteActionRequest", "mode": "only_fake_drop"},
                )
                try:
                    report["cleanup_contractor"] = (
                        await client.contractors.get(owned["company"])
                    ).is_dropped is True
                except NotFoundError:
                    report["cleanup_contractor"] = True
                if not report["cleanup_contractor"]:
                    raise RuntimeError("Soft deletion was not confirmed")
                for payer_id in automatic_payers:
                    try:
                        automatic = await client.payers.get(payer_id)
                    except NotFoundError:
                        continue
                    if not automatic.contractor or automatic.contractor.id != owned["company"]:
                        raise RuntimeError("Automatic test payer ownership changed")
                    if not automatic.is_dropped:
                        await raw_step(
                            "delete automatic test payer", "DELETE", f"/api/v3/payer/{payer_id}"
                        )
                        try:
                            remaining = await client.payers.get(payer_id)
                            if not remaining.is_dropped:
                                raise RuntimeError("Automatic test payer cleanup not confirmed")
                        except NotFoundError:
                            pass
                report["cleanup_auto_payers"] = True
            except Exception as exc:
                cleanup_errors.append(f"contractorCompany/{owned['company']}: {type(exc).__name__}")
        report["owned_ids"] = dict(owned)
        if cleanup_errors:
            raise RuntimeError("Cleanup incomplete; inspect audit: " + ", ".join(cleanup_errors))
    return report


async def main(argv: list[str] | None = None) -> None:
    """Load local credentials without printing them and run the opted-in probe."""
    args = parse_args(argv)
    if args.env_file.is_file():
        for raw in args.env_file.read_text().splitlines():
            if "=" in raw and not raw.lstrip().startswith("#"):
                key, value = raw.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    url = args.base_url or os.environ.get("MEGAPLAN_URL")
    if not url:
        raise ValueError("MEGAPLAN_URL or --base-url is required")
    async with MegaplanClient(
        url,
        username=os.environ.get("MEGAPLAN_USERNAME"),
        password=os.environ.get("MEGAPLAN_PASSWORD"),
        access_token=os.environ.get("MEGAPLAN_ACCESS_TOKEN"),
        max_retries=0,
    ) as client:
        result = await probe(
            client,
            contractor_type_id=args.contractor_type_id,
            audit_path=args.audit_path,
            actor=args.actor,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        detail = f" {error}" if isinstance(error, RuntimeError) else ""
        print(
            f"Probe failed: {type(error).__name__}.{detail} Inspect the private audit for owned IDs and cleanup.",
            file=sys.stderr,
        )
        sys.exit(1)
