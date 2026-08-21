"""Probe the Todo routes on a live account (0.6.1).

RAML documents neither GET /todo/{id} nor the action endpoints, so the shape of
TodosResource is decided here. Creates its own [SDK-TEST] entities and removes
them in finally — the stand is a production account.
"""

import asyncio
import os
import sys

from megaplan_sdk import MegaplanClient

TEST_PREFIX = "[SDK-TEST]"


async def probe(client: MegaplanClient) -> None:
    """Attempt every candidate Todo route and print a route/status table.

    Raises:
        SystemExit: if a [SDK-TEST] Todo was created but could not be torn
            down (id unparsable, or DELETE itself failed) — the entity is
            still live on the production stand and needs manual cleanup.
    """
    results: list[tuple[str, str]] = []
    unclean_teardown: str | None = None

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

    todo_id: int | None = None
    try:
        if created is not None:
            # Parse the id inside the guarded section: if POST /todo returned
            # 200 but the body has no usable "data.id", the entity still
            # exists on the production stand. Catching this here — instead of
            # letting it escape before try/finally — keeps every post-create
            # path reachable by teardown below.
            try:
                todo_id = int(created["data"]["id"])
            except (KeyError, TypeError, ValueError) as exc:
                unclean_teardown = (
                    f"could not parse id from POST /todo response ({exc}); "
                    f"raw response for manual cleanup: {created!r}"
                )

            if todo_id is not None:
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
        if todo_id is not None:
            deleted = await attempt("DELETE /todo/{id}", "DELETE", f"/api/v3/todo/{todo_id}")
            if deleted is None:
                unclean_teardown = (
                    f"DELETE /todo/{todo_id} failed — [SDK-TEST] Todo id={todo_id} "
                    "was NOT removed from the production stand, delete it manually"
                )

    for label, status in results:
        print(f"{label:35} {status}")

    if unclean_teardown is not None:
        print(f"TEARDOWN FAILED: {unclean_teardown}", file=sys.stderr)
        sys.exit(1)


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
