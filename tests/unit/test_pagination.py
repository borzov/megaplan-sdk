"""Unit tests for the Page pagination type."""

import json
from urllib.parse import unquote

import pytest

from megaplan_sdk import Page


def query_params(route) -> dict:
    return json.loads(unquote(route.calls.last.request.url.query.decode()))


class TestPageConstruction:
    """Page names exactly one position — invalid combinations are inexpressible."""

    def test_requires_exactly_one_position(self):
        with pytest.raises(ValueError, match="exactly one"):
            Page()
        with pytest.raises(ValueError, match="exactly one"):
            Page(after=1, before=2)

    def test_single_position_accepted(self):
        assert Page(after=5).after == 5
        assert Page(before=5).before == 5
        assert Page(with_=5).with_ == 5


class TestPageInListMethods:
    async def test_page_after_int_is_coerced_to_entity_link(self, megaplan_api, tasks):
        route = megaplan_api.get("task", data=[])

        await tasks.list(page=Page(after=5), sort_by=[])

        params = query_params(route)
        assert params["pageAfter"] == {"contentType": "Task", "id": 5}

    async def test_page_before_link_passes_through(self, megaplan_api, employees):
        route = megaplan_api.get("employee", data=[])

        await employees.list(page=Page(before={"contentType": "Employee", "id": 3}))

        params = query_params(route)
        assert params["pageBefore"] == {"contentType": "Employee", "id": 3}

    async def test_page_conflicts_with_legacy_quad(self, tasks):
        with pytest.raises(ValueError, match="not both"):
            await tasks.list(page=Page(after=5), page_after={"contentType": "Task", "id": 1})
