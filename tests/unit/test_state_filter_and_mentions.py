"""Consumer-facing state and comment helpers."""

import json
from urllib.parse import unquote

from httpx import Response

from megaplan_sdk.models.employee import Employee


async def test_state_filter_keeps_paging_over_nonmatches(deals, megaplan_api):
    rows = [
        {"id": n, "state": {"id": n, "name": name, "program": {"id": n, "contentType": "Program"}}}
        for n, name in enumerate(["One", "Two", "Договор 👩‍💻️", "Договор"], start=1)
    ]

    def respond(req):
        q = json.loads(unquote(req.url.query.decode()))
        assert "state" in q["fields"]
        offset = q.get("pageAfter", {}).get("id", 0)
        return Response(200, json={"data": rows[offset : offset + q["limit"]]})

    megaplan_api.router.get(megaplan_api._url("deal")).mock(side_effect=respond)
    opts = {"state_in": ["договор"], "only_requested_fields": True, "fields": ["name"], "limit": 2}
    assert await deals.list(**opts) == []
    assert [r.id async for r in deals.iterate(**opts)] == [3, 4]
    assert opts["fields"] == ["name"]


def test_mention_escapes_name(comments):
    employee = Employee(id=13, name="A & <B>")
    assert (
        comments.mention(employee)
        == '<megaplan:mention to="Employee/13">A &amp; &lt;B&gt;</megaplan:mention>'
    )


def test_unsupported_task_text_term_warns_without_changing_request():
    import pytest

    from megaplan_sdk import FilterBuilder

    with pytest.warns(UserWarning, match="statement"):
        config = FilterBuilder("TaskFilter").field("description").contains("sample").build()
    assert config["config"]["termGroup"]["terms"][0]["field"] == "description"


async def test_list_projection_distinguishes_missing_and_returned_null(tasks, megaplan_api):
    megaplan_api.get("task", data=[{"id": 1}, {"id": 2, "timeCreated": None}])
    missing, returned_null = await tasks.list()
    assert missing.time_created is returned_null.time_created is None
    assert "time_created" not in missing.model_fields_set
    assert "time_created" in returned_null.model_fields_set
