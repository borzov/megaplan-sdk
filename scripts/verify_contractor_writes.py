"""Opt-in live probe using only newly created, clearly marked test objects.

The probe checks partial updates, null/empty clearing, contact array replacement
and available signatory fields. It removes both payers and soft-drops its company
in finally. Credentials come from the environment or an explicit env file;
only parameter names and aggregate results are printed.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import re
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from megaplan_sdk import MegaplanClient, NotFoundError, ValidationError
from megaplan_sdk.models.contractor import Contractor
from megaplan_sdk.models.payer import Payer, PayerPatch
from megaplan_sdk.updates import _append_audit

PREFIX = "ТЕСТ SDK, не трогать"


_PAYER_FIELDS = {field.alias or key for key, field in PayerPatch.model_fields.items()}
_CUSTOM = re.compile(r"Category\d+CustomField\w+")
_SIGNATORIES = {
    "FioPodpisanta": "фио подписанта",
    "DolzhnostPodpisanta": "должность подписанта",
    "NaOsnovanii": "на основании",
}


def _business_fields(payer: Payer) -> dict[str, Any]:
    return {
        key: value
        for key, value in payer.model_dump(by_alias=True, exclude_unset=True).items()
        if key in _PAYER_FIELDS or _CUSTOM.fullmatch(key)
    }


def _test_value(field: str, kind: str, marker: str, alternate: bool = False) -> str:
    # Two distinct synthetic values allow each populated field to be changed and restored.
    digits = "2" if alternate else "1"
    if field == "inn":
        values = (
            ("990000000115", "990000000299") if kind == "Natural" else ("9900000017", "9900000024")
        )
        return values[int(alternate)]
    if field == "ogrn":
        return "1269900000028" if alternate else "1269900000017"
    widths = {
        "kpp": 9,
        "bik": 9,
        "currentAccount": 20,
        "correspondentAccount": 20,
    }
    if field in widths:
        return digits * widths[field]
    return f"{marker} {field} {digits}"


def _applicable_fields(
    definitions: list[dict[str, Any]], current: dict[str, Any], country: str, kind: str
) -> tuple[list[str], dict[str, str]]:
    fields: list[str] = []
    signatory_definitions: dict[str, list[dict[str, Any]]] = {suffix: [] for suffix in _SIGNATORIES}
    for definition in definitions:
        parts = str(definition.get("id", "")).split(".")
        if len(parts) != 4 or parts[0] != "payers" or parts[2:] != [country, kind]:
            raise RuntimeError(f"Unrecognized {kind} payer field definition")
        alias = parts[1]
        if alias.isascii() and alias.isdecimal():
            # On RU/Legal the numeric id and the card's JSON alias differ.
            # Match the field's documented label to a single known card alias.
            label = str(definition.get("hrName", "")).strip().casefold()
            if country == "RU" and kind == "Legal":
                label = label.removesuffix(" россия юр. лицо")
                for suffix, expected in _SIGNATORIES.items():
                    if label == expected:
                        signatory_definitions[suffix].append(definition)
            continue
        settings = definition.get("settings") or []
        if settings and all(
            item.get("readOnly") or item.get("enabled") is False for item in settings
        ):
            continue
        if alias not in _PAYER_FIELDS - {"country", "type"}:
            raise RuntimeError(f"No editable payer alias for {alias}")
        fields.append(alias)
    if not fields:
        raise RuntimeError(f"No editable requisites in {country}/{kind} extraFields")
    if kind == "Natural":
        fields.extend(key for key in ("firstName", "lastName") if key in current)

    statuses = {}
    for suffix, matches in signatory_definitions.items():
        keys = [key for key in current if re.fullmatch(r"Category\d+CustomField" + suffix, key)]
        if not keys and not matches:
            statuses[suffix] = "not_applicable"
            continue
        statuses[suffix] = "unverified"
        if len(keys) != 1 or len(matches) != 1 or matches[0].get("contentType") != "StringField":
            continue
        settings = matches[0].get("settings") or []
        if settings and all(s.get("readOnly") or s.get("enabled") is False for s in settings):
            statuses[suffix] = "disabled"
            continue
        if not settings or not all(
            s.get("enabled") is True and s.get("readOnly") is False for s in settings
        ):
            continue
        if current[keys[0]] is None or isinstance(current[keys[0]], str):
            fields.append(keys[0])
            statuses[suffix] = "verified"
    return list(dict.fromkeys(fields)), statuses


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
                row = response["data"]
                expected_type = "ContractorCompany" if remember == "company" else "Payer"
                if row.get("contentType") != expected_type:
                    raise RuntimeError("Unexpected entity type in create response")
                owned[remember] = int(row["id"])
                if remember == "company":
                    if row.get("name") != marker:
                        raise RuntimeError("Unexpected test company marker in create response")
                    automatic_payers.update(
                        int(link["id"])
                        for link in row.get("payers", [])
                        if link.get("contentType") == "Payer"
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

    def require_company(company: Contractor) -> None:
        if (company.content_type, company.id, company.name) != (
            "ContractorCompany",
            owned["company"],
            marker,
        ):
            raise RuntimeError("Test company identity or marker changed")

    def require_payer(payer: Payer, payer_id: int) -> None:
        owner = payer.contractor
        if (
            payer.content_type != "Payer"
            or payer.id != payer_id
            or not owner
            or (owner.content_type, owner.id) != ("ContractorCompany", owned["company"])
        ):
            raise RuntimeError("Test payer identity or ownership changed")

    async def patch_payer(payer_id: int, field: str, value: str | None) -> dict[str, Any]:
        preview = await client.payers.update(payer_id, {field: value}, dry_run=True)
        payer = Payer.model_validate(preview.source)
        require_payer(payer, payer_id)
        before = _business_fields(payer)
        await client.payers.apply_update(preview, audit_path=audit_path, actor=actor)
        after = _business_fields(await client.payers.get(payer_id))
        missing = object()
        changed = sorted(
            key
            for key in before.keys() | after.keys()
            if key != field and before.get(key, missing) != after.get(key, missing)
        )
        if changed:
            raise RuntimeError(f"Patch of {field} changed other payer fields: {', '.join(changed)}")
        return after

    async def verify_payer(kind: Literal["Legal", "Natural"], payer_id: int) -> list[str]:
        payer = await client.payers.get(payer_id)
        require_payer(payer, payer_id)
        if not payer.country or payer.type != kind:
            raise RuntimeError(
                f"Created payer did not provide the expected country/type for {kind}"
            )
        definitions = await client.payers.extra_fields(payer.country.id, kind)
        current = _business_fields(payer)
        fields, signatories = _applicable_fields(definitions, current, payer.country.id, kind)

        # Populate all fields so a partial POST that resets a sibling is observable.
        for field in fields:
            if not current.get(field):
                value = _test_value(field, kind, marker)
                current = await patch_payer(payer_id, field, value)
                if current.get(field) != value:
                    raise RuntimeError(f"Could not seed {kind} payer field {field}")
        for field in fields:
            baseline = current[field]
            value = _test_value(field, kind, marker, alternate=True)
            if baseline == value:
                value = _test_value(field, kind, marker)
            changed = await patch_payer(payer_id, field, value)
            if changed.get(field) != value:
                raise RuntimeError(f"Partial update of {kind} payer field {field} did not persist")
            restored = await patch_payer(payer_id, field, baseline)
            if restored != current:
                raise RuntimeError(f"Restoration of {kind} payer field {field} failed")

        if kind == "Legal" and "bank" in fields:
            for label, clearing_value in [("empty_string", ""), ("null", None)]:
                try:
                    cleared = await patch_payer(payer_id, "bank", clearing_value)
                except ValidationError:
                    if clearing_value is not None:
                        raise
                    report["null_result"] = "rejected"
                    report["null_clears"] = False
                    continue
                state = (
                    "missing"
                    if "bank" not in cleared
                    else "null"
                    if cleared["bank"] is None
                    else "empty"
                    if cleared["bank"] == ""
                    else "populated"
                )
                report[f"{label}_result"] = state
                report[f"{label}_clears"] = state != "populated"
                if state == "populated":
                    raise RuntimeError(f"{label} did not clear the populated bank")
                if await patch_payer(payer_id, "bank", current["bank"]) != current:
                    raise RuntimeError("Restoring the bank after clearing failed")
        report["signatory_status"][kind] = signatories
        return fields

    async def patch_company(data: dict[str, Any]) -> None:
        preview = await client.contractors.update(owned["company"], data, dry_run=True)
        require_company(Contractor.model_validate(preview.source))
        await client.contractors.apply_update(preview, audit_path=audit_path, actor=actor)

    async def cleanup_payer(payer_id: int, label: str) -> None:
        try:
            payer = await client.payers.get(payer_id)
        except NotFoundError:
            return
        require_payer(payer, payer_id)
        if payer.is_dropped:
            return
        await raw_step(label, "DELETE", f"/api/v3/payer/{payer_id}")
        try:
            remaining = await client.payers.get(payer_id)
        except NotFoundError:
            return
        if (remaining.content_type, remaining.id, remaining.is_dropped) != (
            "Payer",
            payer_id,
            True,
        ):
            raise RuntimeError("Payer deletion was not confirmed")

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
        report["payer_fields"] = {}
        report["signatory_status"] = {}
        kinds: tuple[Literal["Legal", "Natural"], ...] = ("Legal", "Natural")
        for kind in kinds:
            require_company(await client.contractors.get(owned["company"]))
            await raw_step(
                f"create {kind} payer",
                "POST",
                f"/api/v3/contractor/{owned['company']}/payers",
                {
                    "contentType": "Payer",
                    "type": kind,
                    "country": {"contentType": "Country", "id": "RU"},
                    "name": marker,
                    **({"firstName": marker} if kind == "Natural" else {}),
                },
                remember=kind,
            )
            report["payer_fields"][kind] = await verify_payer(kind, owned[kind])
        legal_fields = report["payer_fields"]["Legal"]
        report["partial_payer_preserves_bank"] = "bank" in legal_fields
        report["custom_field_checked"] = any(_CUSTOM.fullmatch(key) for key in legal_fields)
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
        for kind in ("Natural", "Legal"):
            if kind not in owned:
                continue
            payer_id = owned[kind]
            try:
                await cleanup_payer(payer_id, f"delete owned {kind} payer")
            except Exception as exc:
                cleanup_errors.append(f"payer/{payer_id}: {type(exc).__name__}")
        report["cleanup_payer"] = not cleanup_errors
        if "company" in owned:
            try:
                current_company = await client.contractors.get(owned["company"])
                require_company(current_company)
                await raw_step(
                    "soft drop owned company",
                    "DELETE",
                    f"/api/v3/contractorCompany/{owned['company']}",
                    {"contentType": "DeleteActionRequest", "mode": "only_fake_drop"},
                )
                try:
                    remaining_company = await client.contractors.get(owned["company"])
                    require_company(remaining_company)
                    report["cleanup_contractor"] = remaining_company.is_dropped is True
                except NotFoundError:
                    report["cleanup_contractor"] = True
                if not report["cleanup_contractor"]:
                    raise RuntimeError("Soft deletion was not confirmed")
            except Exception as exc:
                cleanup_errors.append(f"contractorCompany/{owned['company']}: {type(exc).__name__}")
        auto_errors = []
        for payer_id in sorted(automatic_payers):
            try:
                await cleanup_payer(payer_id, "delete automatic test payer")
            except Exception as exc:
                auto_errors.append(f"payer/{payer_id}: {type(exc).__name__}")
        report["cleanup_auto_payers"] = not auto_errors
        cleanup_errors.extend(auto_errors)
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
