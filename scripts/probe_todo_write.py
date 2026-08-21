"""Probe the Todo routes on a live account (0.6.1).

RAML documents neither GET /todo/{id} nor the action endpoints, so the shape of
TodosResource is decided here. Creates its own [SDK-TEST] entities and removes
them in finally — the stand is a production account.
"""

import asyncio
import os

from megaplan_sdk import MegaplanClient

TEST_PREFIX = "[SDK-TEST]"


async def probe(client: MegaplanClient) -> None:
    """Attempt every candidate Todo route and print a route/status table."""
    results: list[tuple[str, str]] = []

    async def attempt(label: str, method: str, path: str, **kw) -> dict | None:
        try:
            body = await client.raw(method, path, **kw)
            results.append((label, "200"))
            return body
        except Exception as exc:  # noqa: BLE001 — probe records failures
            results.append((label, type(exc).__name__ + ": " + str(exc)[:120]))
            return None

    created = await attempt(
        "POST /todo",
        "POST",
        "/api/v3/todo",
        json={"contentType": "Todo", "name": f"{TEST_PREFIX} probe"},
    )
    todo_id = int(created["data"]["id"]) if created else None

    try:
        if todo_id:
            await attempt("GET /todo/{id}", "GET", f"/api/v3/todo/{todo_id}")
            await attempt(
                "POST /todo/{id}",
                "POST",
                f"/api/v3/todo/{todo_id}",
                json={"contentType": "Todo", "name": f"{TEST_PREFIX} probe upd"},
            )
            for action, payload in (
                ("finish", {"contentType": "TodoFinishActionRequest"}),
                ("renew", {"contentType": "TodoRenewActionRequest"}),
                ("take", {"contentType": "TodoTakeActionRequest"}),
            ):
                await attempt(
                    f"POST /todo/{{id}}/{action}",
                    "POST",
                    f"/api/v3/todo/{todo_id}/{action}",
                    json=payload,
                )
            await attempt("GET /todo/{id}/history", "GET", f"/api/v3/todo/{todo_id}/history")
    finally:
        if todo_id:
            await attempt("DELETE /todo/{id}", "DELETE", f"/api/v3/todo/{todo_id}")

    for label, status in results:
        print(f"{label:35} {status}")


async def main() -> None:
    """Authenticate and run the route probe."""
    async with MegaplanClient(
        base_url=os.environ["MEGAPLAN_URL"],
        username=os.environ["MEGAPLAN_USERNAME"],
        password=os.environ["MEGAPLAN_PASSWORD"],
    ) as client:
        await probe(client)


if __name__ == "__main__":
    asyncio.run(main())
