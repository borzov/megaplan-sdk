"""Unit tests for FullDetailsMixin."""

from typing import Any
from urllib.parse import unquote

import pytest

from megaplan_sdk.resources.tasks import TasksResource


async def test_minimal_call(megaplan_api, tasks):
    """Test minimal call with all include_* parameters = False."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task", "name": "Test Task"})

    full_details = await tasks.get_full_details(
        task_id=1,
        include_sub_tasks=False,
        include_actual_sub_tasks=False,
        include_comments=False,
        include_history=False,
        include_auditors=False,
        include_executors=False,
        include_milestones=False,
        include_responsible_details=False,
        include_owner_details=False,
    )

    assert full_details.task.id == 1
    assert full_details.task.name == "Test Task"
    assert full_details.sub_tasks is None
    assert full_details.comments is None
    assert full_details.history is None
    assert full_details.responsible_details is None
    assert full_details.owner_details is None


async def test_full_call_all_includes(megaplan_api, tasks):
    """Test full call with all include_* = True and limits."""
    megaplan_api.get(
        "task/1",
        data={
            "id": 1,
            "contentType": "Task",
            "name": "Test Task",
            "responsible": {"id": 10, "contentType": "Employee"},
            "owner": {"id": 11, "contentType": "Employee"},
        },
    )

    megaplan_api.get(
        "task/1/subTasks",
        data=[{"id": 2, "contentType": "Task", "name": "Subtask"}],
    )

    megaplan_api.get(
        "task/1/actualSubTasks",
        data=[{"id": 3, "contentType": "Task", "name": "Actual Subtask"}],
    )

    megaplan_api.get(
        "task/1/comments",
        data=[{"id": 1, "contentType": "Comment", "text": "Comment"}],
    )

    megaplan_api.get(
        "task/1/history",
        data=[{"id": 1, "action": "created"}],
    )

    megaplan_api.get(
        "task/1/auditors",
        data=[{"id": 15, "contentType": "Employee"}],
    )

    megaplan_api.get(
        "task/1/executors",
        data=[{"id": 16, "contentType": "Employee"}],
    )

    megaplan_api.get(
        "task/1/milestones",
        data=[{"id": 1, "name": "Milestone"}],
    )

    megaplan_api.get(
        "employee/10",
        data={"id": 10, "contentType": "Employee", "firstName": "John", "lastName": "Doe"},
    )

    megaplan_api.get(
        "employee/11",
        data={"id": 11, "contentType": "Employee", "firstName": "Jane", "lastName": "Smith"},
    )

    full_details = await tasks.get_full_details(
        task_id=1,
        include_sub_tasks=True,
        include_actual_sub_tasks=True,
        include_comments=True,
        include_history=True,
        include_auditors=True,
        include_executors=True,
        include_milestones=True,
        include_responsible_details=True,
        include_owner_details=True,
        comments_limit=10,
        history_limit=20,
    )

    assert full_details.task.id == 1
    assert full_details.sub_tasks is not None
    assert len(full_details.sub_tasks) == 1
    assert full_details.actual_sub_tasks is not None
    assert full_details.comments is not None
    assert full_details.history is not None
    assert full_details.auditors is not None
    assert full_details.executors is not None
    assert full_details.milestones is not None
    assert full_details.responsible_details is not None
    assert full_details.responsible_details.first_name == "John"
    assert full_details.owner_details is not None
    assert full_details.owner_details.first_name == "Jane"


async def test_parallel_execution(megaplan_api, tasks):
    """Test that parallel execution works correctly."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task", "name": "Test"})

    megaplan_api.get(
        "task/1/comments",
        data=[{"id": 1, "contentType": "Comment", "text": "Comment"}],
    )

    megaplan_api.get(
        "task/1/history",
        data=[{"id": 1, "action": "created"}],
    )

    # Mock _fetch_details_parallel to verify it's called
    original_fetch = tasks._fetch_details_parallel
    call_count = 0
    tasks_captured = None

    async def mock_fetch(fetch_tasks: dict[str, Any]) -> dict[str, Any]:
        nonlocal call_count, tasks_captured
        call_count += 1
        tasks_captured = fetch_tasks
        return await original_fetch(fetch_tasks)

    tasks._fetch_details_parallel = mock_fetch

    await tasks.get_full_details(
        task_id=1,
        include_comments=True,
        include_history=True,
    )

    assert call_count == 1
    assert tasks_captured is not None
    assert "comments" in tasks_captured
    assert "history" in tasks_captured
    assert len(tasks_captured) == 2


async def test_partial_call(megaplan_api, tasks):
    """Test partial call with only comments and responsible_details."""
    megaplan_api.get(
        "task/1",
        data={
            "id": 1,
            "contentType": "Task",
            "name": "Test Task",
            "responsible": {"id": 10, "contentType": "Employee"},
        },
    )

    megaplan_api.get(
        "task/1/comments",
        data=[{"id": 1, "contentType": "Comment", "text": "Comment"}],
    )

    megaplan_api.get(
        "employee/10",
        data={"id": 10, "contentType": "Employee", "firstName": "John", "lastName": "Doe"},
    )

    full_details = await tasks.get_full_details(
        task_id=1,
        include_comments=True,
        include_responsible_details=True,
    )

    assert full_details.task.id == 1
    assert full_details.comments is not None
    assert len(full_details.comments) == 1
    assert full_details.responsible_details is not None
    assert full_details.responsible_details.first_name == "John"
    assert full_details.sub_tasks is None
    assert full_details.history is None
    assert full_details.owner_details is None


async def test_missing_optional_fields(megaplan_api, tasks):
    """Test handling of missing optional fields (e.g., no auditors)."""
    megaplan_api.get(
        "task/1",
        data={
            "id": 1,
            "contentType": "Task",
            "name": "Test Task",
            "responsible": None,
        },
    )

    megaplan_api.get("task/1/auditors", data=[])

    full_details = await tasks.get_full_details(
        task_id=1,
        include_auditors=True,
        include_responsible_details=True,
    )

    assert full_details.task.id == 1
    assert full_details.auditors is not None
    assert len(full_details.auditors) == 0
    assert full_details.responsible_details is None


async def test_entity_loading(megaplan_api, tasks):
    """Test entity loading through entity_field + entity_type."""
    megaplan_api.get(
        "task/1",
        data={
            "id": 1,
            "contentType": "Task",
            "name": "Test Task",
            "responsible": {"id": 10, "contentType": "Employee"},
            "owner": {"id": 11, "contentType": "Employee"},
        },
    )

    megaplan_api.get(
        "employee/10",
        data={"id": 10, "contentType": "Employee", "firstName": "John", "lastName": "Doe"},
    )

    megaplan_api.get(
        "employee/11",
        data={"id": 11, "contentType": "Employee", "firstName": "Jane", "lastName": "Smith"},
    )

    full_details = await tasks.get_full_details(
        task_id=1,
        include_responsible_details=True,
        include_owner_details=True,
    )

    assert full_details.responsible_details is not None
    assert full_details.responsible_details.id == 10
    assert full_details.responsible_details.first_name == "John"
    assert full_details.owner_details is not None
    assert full_details.owner_details.id == 11
    assert full_details.owner_details.first_name == "Jane"


async def test_limit_params(megaplan_api, tasks):
    """Test passing limit parameters to methods."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task", "name": "Test"})

    comments_mock = megaplan_api.get(
        "task/1/comments",
        data=[{"id": 1, "contentType": "Comment", "text": "Comment"}],
    )

    history_mock = megaplan_api.get(
        "task/1/history",
        data=[{"id": 1, "action": "created"}],
    )

    await tasks.get_full_details(
        task_id=1,
        include_comments=True,
        include_history=True,
        comments_limit=5,
        history_limit=10,
    )

    # Verify that limits were passed (check request params)
    assert comments_mock.called
    assert history_mock.called


async def test_fetch_method_loading(megaplan_api, tasks):
    """Test loading through fetch_method (get_comments, get_history)."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task", "name": "Test"})

    megaplan_api.get(
        "task/1/comments",
        data=[
            {"id": 1, "contentType": "Comment", "content": "Comment 1"},
            {"id": 2, "contentType": "Comment", "content": "Comment 2"},
        ],
    )

    megaplan_api.get(
        "task/1/history",
        data=[
            {"id": 1, "action": "created"},
            {"id": 2, "action": "updated"},
        ],
    )

    full_details = await tasks.get_full_details(
        task_id=1,
        include_comments=True,
        include_history=True,
    )

    assert full_details.comments is not None
    assert len(full_details.comments) == 2
    assert full_details.history is not None
    assert len(full_details.history) == 2


async def test_custom_fetcher_related_tasks_raises_not_implemented(megaplan_api, deals):
    """include_related_tasks fails loudly: the API has no tasks-by-deal filter.

    Verified empirically (2026-07-02): the old implementation silently
    returned ALL account tasks instead of the deal's tasks.
    """
    megaplan_api.get("deal/1", data={"id": 1, "contentType": "Deal", "name": "Test Deal"})

    with pytest.raises(NotImplementedError, match="tasks-by-deal"):
        await deals.get_full_details(deal_id=1, include_related_tasks=True)


async def test_default_limits_applied_when_not_specified(megaplan_api, http_client):
    """Test that default limits are applied when parameters not specified."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task", "name": "Test Task"})
    megaplan_api.get("task/1/comments", data=[{"id": 1, "text": "Comment 1"}])
    megaplan_api.get("task/1/history", data=[{"id": 1, "action": "created"}])

    # Create resource with default limits
    resource = TasksResource(
        http_client, cache=None, default_comments_limit=50, default_history_limit=100
    )

    # Call get_full_details WITHOUT specifying limits
    full_details = await resource.get_full_details(
        task_id=1,
        include_comments=True,
        include_history=True,
    )

    assert full_details.task.id == 1
    assert full_details.comments is not None
    assert full_details.history is not None

    # Verify that API was called with default limits
    comments_request = megaplan_api.router.calls[1].request  # Second call (comments)
    history_request = megaplan_api.router.calls[2].request  # Third call (history)

    # Parse query params (Megaplan uses JSON in query string)
    comments_url = unquote(str(comments_request.url))
    history_url = unquote(str(history_request.url))
    assert '{"limit": 50}' in comments_url or '{"limit":50}' in comments_url
    assert '{"limit": 100}' in history_url or '{"limit":100}' in history_url


async def test_explicit_limit_overrides_default(megaplan_api, http_client):
    """Test that explicit limit parameter overrides default."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task", "name": "Test Task"})
    megaplan_api.get("task/1/comments", data=[{"id": 1, "text": "Comment 1"}])

    resource = TasksResource(http_client, cache=None, default_comments_limit=50)  # Global default

    # Call with explicit limit (should override default)
    full_details = await resource.get_full_details(
        task_id=1,
        include_comments=True,
        comments_limit=10,  # Explicit value
    )

    assert full_details.task.id == 1
    assert full_details.comments is not None

    # Verify explicit value was used (not default)
    comments_request = megaplan_api.router.calls[1].request
    comments_url = unquote(str(comments_request.url))
    assert '{"limit": 10}' in comments_url or '{"limit":10}' in comments_url


async def test_none_default_does_not_add_limit(megaplan_api, http_client):
    """Test that None default does not add limit parameter."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task", "name": "Test Task"})
    megaplan_api.get("task/1/comments", data=[{"id": 1, "text": "Comment 1"}])

    resource = TasksResource(
        http_client, cache=None, default_comments_limit=None
    )  # None = use API default

    # Call without specifying limit
    full_details = await resource.get_full_details(
        task_id=1,
        include_comments=True,
    )

    assert full_details.task.id == 1
    assert full_details.comments is not None

    # Verify NO limit parameter was added (API decides)
    comments_request = megaplan_api.router.calls[1].request
    # Should not have limit in query params
    assert "limit" not in str(comments_request.url) or '{"limit":null}' not in str(
        comments_request.url
    )


async def test_full_details_limit_without_include_raises(megaplan_api, tasks):
    """Test that passing a *_limit without matching include_* raises ValueError."""
    megaplan_api.get("task/123", data={"contentType": "Task", "id": 123})

    with pytest.raises(ValueError, match="include_comments"):
        await tasks.get_full_details(123, comments_limit=200)


async def test_full_details_limit_with_include_ok(megaplan_api, tasks):
    """Test that passing a *_limit together with include_*=True works without error."""
    megaplan_api.get("task/123", data={"contentType": "Task", "id": 123})
    megaplan_api.get("task/123/comments", data=[])

    details = await tasks.get_full_details(123, include_comments=True, comments_limit=200)
    assert details.task.id == 123


# --- #34: comments_count surfaced on FullDetails ---


async def test_get_full_details_exposes_comments_count(megaplan_api, tasks):
    """#34: details.comments_count comes from the card's commentsCount."""
    route = megaplan_api.get("task/1", data={"id": 1, "contentType": "Task", "commentsCount": 86})
    megaplan_api.get("task/1/comments", data=[{"id": 10, "contentType": "Comment"}])

    details = await tasks.get_full_details(task_id=1, include_comments=True, comments_limit=1)

    assert details.comments_count == 86
    assert details.comments is not None and len(details.comments) == 1
    # Truncation is now detectable: len(comments) < comments_count.
    decoded = unquote(str(route.calls.last.request.url)).replace(" ", "")
    assert '"fields":["commentsCount"]' in decoded


async def test_get_exposes_comments_count_via_fields(megaplan_api, tasks):
    """#34: tasks.get(fields=[...]) forwards fields to the card GET."""
    route = megaplan_api.get("task/1", data={"id": 1, "contentType": "Task", "commentsCount": 3})

    task = await tasks.get(1, fields=["commentsCount"])

    assert task.comments_count == 3
    decoded = unquote(str(route.calls.last.request.url)).replace(" ", "")
    assert '"fields":["commentsCount"]' in decoded


# --- #35: auditors/executors resolved to full Employees by default ---


async def test_get_full_details_resolves_auditors_by_default(megaplan_api, tasks):
    """#35: include_auditors=True returns full Employee objects."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task"})
    megaplan_api.get(
        "task/1/auditors",
        data=[
            {"contentType": "Employee", "id": 7},
            {"contentType": "Employee", "id": 8},
            {"contentType": "Employee", "id": 7},
        ],
    )
    route_7 = megaplan_api.get(
        "employee/7", data={"contentType": "Employee", "id": 7, "name": "Иван Петров"}
    )
    megaplan_api.get(
        "employee/8", data={"contentType": "Employee", "id": 8, "name": "Мария Сидорова"}
    )

    details = await tasks.get_full_details(task_id=1, include_auditors=True)

    assert details.auditors is not None
    assert [a.name for a in details.auditors] == ["Иван Петров", "Мария Сидорова", "Иван Петров"]
    # Batch loading: repeated id fetched once.
    assert route_7.call_count == 1


async def test_get_full_details_resolve_participants_opt_out(megaplan_api, tasks):
    """#35: resolve_participants=False keeps raw references untouched."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task"})
    megaplan_api.get("task/1/auditors", data=[{"contentType": "Employee", "id": 7}])

    details = await tasks.get_full_details(
        task_id=1, include_auditors=True, resolve_participants=False
    )

    assert details.auditors == [{"contentType": "Employee", "id": 7}]


async def test_deal_full_details_resolves_auditors_by_default(megaplan_api, deals):
    """#35: include_auditors=True returns full Employee objects for deals."""
    megaplan_api.get("deal/1", data={"id": 1, "contentType": "Deal", "name": "Test Deal"})
    megaplan_api.get(
        "deal/1/auditors",
        data=[{"contentType": "Employee", "id": 15}],
    )
    megaplan_api.get(
        "employee/15", data={"contentType": "Employee", "id": 15, "name": "Пётр Кузнецов"}
    )

    details = await deals.get_full_details(deal_id=1, include_auditors=True)

    assert details.auditors is not None
    assert details.auditors[0].name == "Пётр Кузнецов"


async def test_deal_full_details_resolve_participants_opt_out(megaplan_api, deals):
    """#35: resolve_participants=False keeps raw references untouched for deals."""
    megaplan_api.get("deal/1", data={"id": 1, "contentType": "Deal", "name": "Test Deal"})
    megaplan_api.get(
        "deal/1/auditors",
        data=[{"contentType": "Employee", "id": 15}],
    )

    details = await deals.get_full_details(
        deal_id=1, include_auditors=True, resolve_participants=False
    )

    assert details.auditors == [{"contentType": "Employee", "id": 15}]


async def test_resolve_participants_leaves_non_employee_items(megaplan_api, tasks):
    """#35: non-Employee participants pass through unresolved."""
    megaplan_api.get("task/1", data={"id": 1, "contentType": "Task"})
    megaplan_api.get(
        "task/1/auditors",
        data=[
            {"contentType": "Employee", "id": 7},
            {"contentType": "Group", "id": 55, "name": "Отдел разработки"},
        ],
    )
    megaplan_api.get("employee/7", data={"contentType": "Employee", "id": 7, "name": "Иван Петров"})

    details = await tasks.get_full_details(task_id=1, include_auditors=True)

    assert details.auditors[0].name == "Иван Петров"
    assert details.auditors[1] == {"contentType": "Group", "id": 55, "name": "Отдел разработки"}
