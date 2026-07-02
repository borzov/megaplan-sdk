"""Unit tests for TaskQuery: invalid combinations fail at construction time."""

import json
from urllib.parse import unquote

import pytest

from megaplan_sdk import Page, TaskQuery


def query_params(route) -> dict:
    return json.loads(unquote(route.calls.last.request.url.query.decode()))


class TestConstructionTimeValidation:
    """Every rule tasks.list() enforces at call time fires here at build time."""

    def test_search_and_filter_are_mutually_exclusive(self):
        with pytest.raises(ValueError, match="not both"):
            TaskQuery().search("x").filter(5)
        with pytest.raises(ValueError, match="not both"):
            TaskQuery().filter(5).search("x")

    def test_invalid_status_rejected_immediately(self):
        with pytest.raises(ValueError, match="Invalid task status"):
            TaskQuery().statuses("bogus")

    def test_unsupported_sort_field_rejected_with_suggestion(self):
        with pytest.raises(ValueError, match="activity"):
            TaskQuery().sort_by("timeUpdated")

    def test_search_in_unfilterable_field_rejected(self):
        with pytest.raises(NotImplementedError, match="silently ignored"):
            TaskQuery().search("x", in_=["description"])

    def test_unsupported_field_rejected_with_suggestion(self):
        """#32: foreign-API synonyms in fields raise with real replacements."""
        with pytest.raises(ValueError, match="statusChangeTime"):
            TaskQuery().fields("timeUpdated")

    def test_created_at_synonym_suggests_time_created(self):
        """#32: createdAt-style synonyms point to timeCreated."""
        with pytest.raises(ValueError, match="timeCreated"):
            TaskQuery().fields("createdAt")

    def test_unknown_and_custom_fields_pass(self):
        """#32: unknown/custom fields are NOT rejected (no reliable allowlist)."""
        query = TaskQuery().fields("commentsCount", "Category1000001CustomFieldFoo")
        kwargs = query.as_list_kwargs()
        assert kwargs["fields"] == ["commentsCount", "Category1000001CustomFieldFoo"]


class TestListBy:
    async def test_list_by_sends_built_params(self, megaplan_api, tasks):
        route = megaplan_api.get("task", data=[{"id": 1, "contentType": "Task", "name": "T"}])

        query = (
            TaskQuery()
            .statuses("assigned", "accepted")
            .sort_by("timeCreated", desc=True)
            .limit(25)
            .page(Page(after=100))
        )
        result = await tasks.list_by(query)

        assert len(result) == 1
        params = query_params(route)
        assert params["statuses"] == ["assigned", "accepted"]
        assert params["sortBy"] == [
            {"contentType": "SortField", "fieldName": "timeCreated", "desc": True}
        ]
        assert params["limit"] == 25
        assert params["pageAfter"] == {"contentType": "Task", "id": 100}

    async def test_search_builds_name_filter(self, megaplan_api, tasks):
        route = megaplan_api.get("task", data=[])

        await tasks.list_by(TaskQuery().search("договор"))

        params = query_params(route)
        assert params["filter"]["contentType"] == "TaskFilter"
        terms = params["filter"]["config"]["termGroup"]["terms"]
        assert terms[0]["field"] == "name"
        assert terms[0]["value"] == "договор"

    async def test_with_time_fields_requests_date_fields(self, megaplan_api, tasks):
        from megaplan_sdk import DEFAULT_TASK_LIST_FIELDS

        route = megaplan_api.get("task", data=[])

        await tasks.list_by(TaskQuery().with_time_fields())

        params = query_params(route)
        assert params["fields"] == list(DEFAULT_TASK_LIST_FIELDS)

    async def test_default_sort_is_newest_first(self, megaplan_api, tasks):
        route = megaplan_api.get("task", data=[])

        await tasks.list_by(TaskQuery())

        params = query_params(route)
        assert params["sortBy"] == [
            {"contentType": "SortField", "fieldName": "timeCreated", "desc": True}
        ]
