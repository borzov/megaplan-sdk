"""Probe list projections with authenticated GET requests and emit JSON lines.

Set MEGAPLAN_URL and either MEGAPLAN_ACCESS_TOKEN or MEGAPLAN_USERNAME and
MEGAPLAN_PASSWORD. Example: python scripts/probe_list_fields.py task statement
description. Omit the field names to check model aliases and the route registry.
For contractorCompany/search, supply --query with known matching text.
"""

import argparse
import asyncio
import json
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx
from pydantic import BaseModel

from megaplan_sdk import (
    Contractor,
    ContractorCompany,
    ContractorHuman,
    Deal,
    Employee,
    MegaplanClient,
    Payer,
    Project,
    Task,
    Todo,
)
from megaplan_sdk.exceptions import MegaplanError
from megaplan_sdk.list_fields import CONFIRMED_LIST_FIELDS, REJECTED_LIST_FIELDS

_MODELS: dict[str, type[BaseModel]] = {
    "contractor": Contractor,
    "contractorCompany": ContractorCompany,
    "contractorHuman": ContractorHuman,
    "contractorCompany/search": Contractor,
    "deal": Deal,
    "employee": Employee,
    "payer": Payer,
    "project": Project,
    "task": Task,
    "todo": Todo,
}


async def probe_fields(
    client: MegaplanClient, route: str, fields: list[str], *, q: str | None = None
) -> AsyncIterator[dict[str, Any]]:
    """Probe each name with limit=1, exposing only route, field, outcome and status."""
    query: dict[str, Any] = {"limit": 1}
    if route == "contractorCompany/search":
        if not q or not q.strip():
            raise ValueError("Contractor search needs a query with a known match.")
        query["q"] = q
    elif route not in _MODELS or q is not None:
        raise ValueError("Choose a supported list route; only contractor search accepts q.")

    async def read(options: dict[str, Any]) -> tuple[int | None, list[Any] | None]:
        try:
            body = await client.raw("GET", f"/api/v3/{route}", query=options)
        except MegaplanError as exc:
            return exc.status_code, None
        except (httpx.RequestError, ValueError):
            return None, None
        rows = body.get("data")
        return 200, rows if isinstance(rows, list) else None

    # A failing baseline (permissions, invalid search criteria, etc.) provides
    # no evidence about any individual field, even if the status is 422.
    baseline_status, baseline_rows = await read(query)
    for field in fields:
        status = baseline_status
        outcome = "undetermined"
        if baseline_rows is not None:
            options = {**query, "fields": [field]}
            status, rows = await read(options)
            if status == 422:
                outcome = "rejected"
            elif rows is not None:
                if route == "contractorCompany/search":
                    # Search silently accepts unknown names. Verify the field
                    # actually appears when explicitly requested on its own.
                    status, rows = await read({**options, "onlyRequestedFields": True})
                    if rows and isinstance(rows[0], dict) and field in rows[0]:
                        outcome = "accepted"
                else:
                    outcome = "accepted"
        yield {"route": route, "field": field, "outcome": outcome, "status": status}


async def main() -> None:
    """Run a read-only probe using environment credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("route", choices=_MODELS)
    parser.add_argument("fields", nargs="*", help="API field names (model aliases by default)")
    parser.add_argument("--query", help="Known matching text for contractorCompany/search")
    args = parser.parse_args()
    url = os.environ.get("MEGAPLAN_URL")
    if not url:
        parser.error("Set MEGAPLAN_URL.")
    if (args.route == "contractorCompany/search") != bool(args.query and args.query.strip()):
        parser.error("--query is required for contractorCompany/search and applies only there.")
    aliases = {attr.alias or name for name, attr in _MODELS[args.route].model_fields.items()}
    fields = args.fields or sorted(
        aliases | CONFIRMED_LIST_FIELDS[args.route] | REJECTED_LIST_FIELDS[args.route]
    )
    try:
        async with MegaplanClient(
            url,
            access_token=os.environ.get("MEGAPLAN_ACCESS_TOKEN"),
            username=os.environ.get("MEGAPLAN_USERNAME"),
            password=os.environ.get("MEGAPLAN_PASSWORD"),
            max_retries=0,
            log_level="CRITICAL",
        ) as client:
            async for result in probe_fields(client, args.route, fields, q=args.query):
                print(json.dumps(result), flush=True)
    except (MegaplanError, httpx.RequestError, ValueError) as exc:
        parser.exit(1, f"Could not open probe: {type(exc).__name__}\n")


if __name__ == "__main__":
    asyncio.run(main())
