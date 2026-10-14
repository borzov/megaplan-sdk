"""Reviewed updates and durable JSONL audit, separate from ordinary SDK logs."""

import asyncio
import json
import os
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from megaplan_sdk.exceptions import MegaplanError, UpdateAuditError, UpdateConflictError
from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.models.update import UpdateFieldChange, UpdatePreview

_CUSTOM_FIELD = re.compile(r"^Category\d+CustomField\w+$")
_AUDIT_LOCK = threading.Lock()
_REFERENCE_FIELDS = {
    "company",
    "type",
    "responsibles",
    "advertisingWay",
    "activityType",
    "status",
    "partners",
    "competitors",
    "country",
    "tags",
}


def normalize_patch(
    data: dict[str, Any] | BaseModel,
    model: type[BaseModel],
    current: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate writable keys and serialize only explicitly supplied values.

    Dynamic fields must already exist in the current API card; unknown names
    are rejected rather than assuming numeric extraFields ids map to aliases.
    """
    raw = (
        data.model_dump(by_alias=True, exclude_unset=True)
        if isinstance(data, BaseModel)
        else dict(data)
    )
    allowed = {
        key for name, item in model.model_fields.items() for key in (name, item.alias or name)
    }
    for key in raw:
        if key not in allowed and not (
            _CUSTOM_FIELD.fullmatch(key) and current is not None and key in current
        ):
            raise ValueError(f"Unknown or read-only update field: {key}")
    patch = model.model_validate(raw).model_dump(by_alias=True, exclude_unset=True)
    if isinstance(patch.get("country"), dict):
        patch["country"].setdefault("contentType", "Country")
    return patch


def _canonical(value: Any, *, reference: bool = False) -> Any:
    if isinstance(value, dict):
        if reference and value.get("contentType") and "id" in value:
            return {"contentType": value["contentType"], "id": str(value["id"])}
        return {key: str(item) if key == "id" else _canonical(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonical(item, reference=reference) for item in value]
    return value


def field_changes(source: dict[str, Any], patch: dict[str, Any]) -> list[UpdateFieldChange]:
    """Compute a diff without conflating an absent key with explicit null."""
    return [
        UpdateFieldChange(key, source.get(key), value, key in source)
        for key, value in patch.items()
        if key not in source
        or _canonical(source[key], reference=key in _REFERENCE_FIELDS)
        != _canonical(value, reference=key in _REFERENCE_FIELDS)
    ]


def _snapshot(source: dict[str, Any], model: type[BaseModel]) -> dict[str, Any]:
    keys = {item.alias or name for name, item in model.model_fields.items()}
    keys.update(key for key in source if _CUSTOM_FIELD.fullmatch(key))
    keys.update(("timeUpdated", "isDropped", "mergeInProgress"))
    return {
        key: _canonical(source[key], reference=key in _REFERENCE_FIELDS)
        for key in keys
        if key in source
    }


async def prepare_update(
    http: HTTPClient,
    path: str,
    entity_id: int,
    data: dict[str, Any] | BaseModel,
    model: type[BaseModel],
    content_types: tuple[str, ...],
) -> UpdatePreview:
    """Read a fresh card and prepare an immutable, account-bound preview."""
    source = (await http.get(path))["data"]
    entity_type = source.get("contentType")
    if entity_type not in content_types or str(source.get("id")) != str(entity_id):
        raise ValueError("API returned a different entity for the update preview")
    patch = normalize_patch(data, model, source)
    payload = json.dumps(
        {"origin": http.base_url, "source": source, "patch": patch}, ensure_ascii=False
    )
    return UpdatePreview(entity_type, entity_id, payload)


def _sanitize_audit(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if key.lower()
            in (
                "authorization",
                "password",
                "access_token",
                "refresh_token",
                "token",
                "accesstoken",
                "refreshtoken",
            )
            else _sanitize_audit(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_audit(item) for item in value]
    return value


def _append_audit(path: str | os.PathLike[str], record: dict[str, Any]) -> None:
    line = (json.dumps(_sanitize_audit(record), ensure_ascii=False) + "\n").encode()
    # One append syscall keeps records together. The lock also serializes fsync
    # for concurrent operations in this process; the file is private on creation.
    with _AUDIT_LOCK:
        created = not Path(path).exists()
        fd = os.open(Path(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            remaining = memoryview(line)
            while remaining:
                written = os.write(fd, remaining)
                if written == 0:
                    raise OSError("Incomplete audit record")
                remaining = remaining[written:]
            os.fsync(fd)
            if created and os.name == "posix":
                parent = os.open(Path(path).parent, os.O_RDONLY)
                try:
                    os.fsync(parent)
                finally:
                    os.close(parent)
        finally:
            os.close(fd)


async def apply_update(
    http: HTTPClient,
    path: str,
    preview: UpdatePreview,
    model: type[BaseModel],
    content_types: tuple[str, ...],
    audit_path: str | os.PathLike[str],
    actor: str,
    *,
    post_path: str | None = None,
) -> dict[str, Any]:
    """Recheck the source state, persist intent, then send one reviewed POST.

    This is optimistic client-side checking, not an atomic server lock.
    Network/5xx retries are disabled because the write outcome can be unknown.
    """
    if not actor.strip():
        raise ValueError("actor must identify the update operator")
    source = preview.source
    if (
        preview.origin != http.base_url
        or preview.entity_type not in content_types
        or source.get("contentType") != preview.entity_type
        or str(source.get("id")) != str(preview.entity_id)
    ):
        raise ValueError("Preview belongs to a different account or entity")
    patch = normalize_patch(preview.patch, model, source)
    current = (await http.get(path))["data"]
    if (
        current.get("contentType") != preview.entity_type
        or str(current.get("id")) != str(preview.entity_id)
        or _snapshot(current, model) != _snapshot(source, model)
    ):
        raise UpdateConflictError("Profile changed since the preview; prepare a new preview")
    changes = field_changes(current, patch)
    if not changes:
        return {"data": current}
    operation_id = str(uuid.uuid4())
    common = {
        "operation_id": operation_id,
        "actor": actor,
        "entity_type": preview.entity_type,
        "entity_id": preview.entity_id,
        "diff": [change.__dict__ for change in changes],
    }

    async def audit(event: str, **details: Any) -> None:
        record = {**common, "time": datetime.now(UTC).isoformat(), "event": event, **details}
        task = asyncio.create_task(asyncio.to_thread(_append_audit, audit_path, record))
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            # Finish the small local append before propagating cancellation.
            await task
            raise

    await audit("intent")
    try:
        response = await http.post(
            post_path or path,
            json_data={**patch, "contentType": preview.entity_type},
            retry_on_error=False,
        )
    except (Exception, asyncio.CancelledError) as exc:
        status = exc.status_code if isinstance(exc, MegaplanError) else None
        try:
            await audit(
                "error",
                error_type=type(exc).__name__,
                status=status,
                outcome="rejected"
                if status and 400 <= status < 500 and status != 408
                else "unknown",
                response=exc.response if isinstance(exc, MegaplanError) else None,
            )
        except Exception as audit_exc:
            raise UpdateAuditError(
                "Request failed and its outcome could not be audited; do not replay blindly",
                server_changed=None,
                operation_id=operation_id,
            ) from audit_exc
        if isinstance(exc, asyncio.CancelledError):
            raise
        if not status or status == 408 or status >= 500:
            raise UpdateAuditError(
                "Update outcome is unknown; inspect the entity and audit before retrying",
                server_changed=None,
                operation_id=operation_id,
                response=exc.response if isinstance(exc, MegaplanError) else None,
            ) from exc
        raise
    try:
        await audit("result", response=response, outcome="confirmed")
    except Exception as exc:
        raise UpdateAuditError(
            "Server accepted the update, but writing its audit result failed; do not replay",
            server_changed=True,
            operation_id=operation_id,
            response=response,
        ) from exc
    return response
