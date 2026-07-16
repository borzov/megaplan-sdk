"""Manual verification of 0.5.0 changes against a live stand (#34, #35, FR-A/C).

Usage: MEGAPLAN_BASE_URL=... MEGAPLAN_ACCESS_TOKEN=... python scripts/verify_0_5_0_stand.py TASK_ID
"""

import asyncio
import os
import sys

from megaplan_sdk import MegaplanClient


async def main() -> None:
    task_id = int(sys.argv[1])
    async with MegaplanClient(
        os.environ["MEGAPLAN_BASE_URL"],
        access_token=os.environ["MEGAPLAN_ACCESS_TOKEN"],
    ) as mp:
        # 34: comments_count populated independently of comments_limit
        details = await mp.tasks.get_full_details(
            task_id=task_id,
            include_comments=True,
            comments_limit=5,
            include_auditors=True,
        )
        print(f"#34 comments_count={details.comments_count} len={len(details.comments or [])}")
        assert details.comments_count is not None

        # 35: auditors resolved to named Employees
        names = [getattr(a, "name", None) for a in details.auditors or []]
        print(f"#35 auditor names: {names}")
        assert all(names), "auditor names must be resolved"

        # 34 symmetric: deal/project cards accept fields=["commentsCount"]
        deals = await mp.deals.list(limit=1)
        if deals:
            deal_details = await mp.deals.get_full_details(deal_id=deals[0].id)
            print(f"#34 deal comments_count={deal_details.comments_count}")

        # FR-C: download first attach found on the task, if any
        attaches = details.task.attaches or []
        if attaches:
            data = await mp.attachments.download(attaches[0])
            print(f"#FR-C downloaded {len(data)} bytes")


if __name__ == "__main__":
    asyncio.run(main())
