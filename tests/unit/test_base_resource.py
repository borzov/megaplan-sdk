"""Unit tests for BaseResource."""

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.tasks import TasksResource


@pytest.mark.asyncio
@respx.mock
async def test_pagination_page_after():
    """Test pageAfter parameter in query params."""
    respx.get(
        url__regex=r"https://example\.com/api/v3/task\?.*pageAfter.*",
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 2, "contentType": "Task", "name": "Task 2"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = await resource.list(
            limit=10,
            page_after={"contentType": "Task", "id": 1},
        )

        assert len(tasks) == 1
        assert tasks[0].id == 2


@pytest.mark.asyncio
@respx.mock
async def test_pagination_page_before():
    """Test pageBefore parameter in query params."""
    respx.get(
        url__regex=r"https://example\.com/api/v3/task\?.*pageBefore.*",
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Task", "name": "Task 1"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = await resource.list(
            limit=10,
            page_before={"contentType": "Task", "id": 2},
        )

        assert len(tasks) == 1
        assert tasks[0].id == 1


@pytest.mark.asyncio
@respx.mock
async def test_pagination_page_with():
    """Test pageWith parameter in query params."""
    respx.get(
        url__regex=r"https://example\.com/api/v3/task\?.*pageWith.*",
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 5, "contentType": "Task", "name": "Task 5"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = await resource.list(
            limit=10,
            page_with={"contentType": "Task", "id": 5},
        )

        assert len(tasks) == 1
        assert tasks[0].id == 5


@pytest.mark.asyncio
@respx.mock
async def test_iterate_multiple_pages():
    """Test iterate() with multiple pages."""
    # First page - TasksResource adds statuses parameter
    respx.get(
        url__regex=r"https://example\.com/api/v3/task\?.*",
    ).mock(
        side_effect=[
            Response(
                200,
                json={
                    "meta": {"status": 200},
                    "data": [
                        {"id": 1, "contentType": "Task", "name": "Task 1"},
                        {"id": 2, "contentType": "Task", "name": "Task 2"},
                    ],
                },
            ),
            Response(
                200,
                json={
                    "meta": {"status": 200},
                    "data": [
                        {"id": 3, "contentType": "Task", "name": "Task 3"},
                    ],
                },
            ),
        ]
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = []
        async for task in resource.iterate(limit=2):
            tasks.append(task)

        assert len(tasks) == 3
        assert tasks[0].id == 1
        assert tasks[1].id == 2
        assert tasks[2].id == 3


@pytest.mark.asyncio
@respx.mock
async def test_iterate_empty_result():
    """Test iterate() with empty result."""
    respx.get("https://example.com/api/v3/task").mock(
        return_value=Response(
            200,
            json={"meta": {"status": 200}, "data": []},
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = []
        async for task in resource.iterate(limit=10):
            tasks.append(task)

        assert len(tasks) == 0


@pytest.mark.asyncio
@respx.mock
async def test_iterate_partial_page():
    """Test iterate() stops when last page < limit."""
    # First page with 2 items (limit is 10, but only 2 returned)
    respx.get("https://example.com/api/v3/task").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 1, "contentType": "Task", "name": "Task 1"},
                    {"id": 2, "contentType": "Task", "name": "Task 2"},
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = []
        async for task in resource.iterate(limit=10):
            tasks.append(task)

        assert len(tasks) == 2
        # Should not make second request since len(items) < limit


@pytest.mark.asyncio
@respx.mock
async def test_fields_parameter():
    """Test fields parameter in query."""
    respx.get(
        url__regex=r"https://example\.com/api/v3/task\?.*fields.*",
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Task", "name": "Task 1"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = await resource.list(fields=["name", "status"])

        assert len(tasks) == 1


@pytest.mark.asyncio
@respx.mock
async def test_sort_by_parameter():
    """Test sortBy parameter in query."""
    respx.get(
        url__regex=r"https://example\.com/api/v3/task\?.*sortBy.*",
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Task", "name": "Task 1"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = await resource.list(
            sort_by=[{"field": "name", "direction": "asc"}],
        )

        assert len(tasks) == 1


@pytest.mark.asyncio
@respx.mock
async def test_only_requested_fields():
    """Test onlyRequestedFields parameter in query."""
    respx.get(
        url__regex=r"https://example\.com/api/v3/task\?.*onlyRequestedFields.*",
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Task", "name": "Task 1"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = await resource.list(only_requested_fields=True)

        assert len(tasks) == 1


@pytest.mark.asyncio
@respx.mock
async def test_build_list_params_combinations():
    """Test combinations of all parameters together."""
    respx.get(
        url__regex=r"https://example\.com/api/v3/task\?.*",
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 1, "contentType": "Task", "name": "Task 1"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        tasks = await resource.list(
            limit=10,
            page_after={"contentType": "Task", "id": 1},
            fields=["name"],
            sort_by=[{"field": "name", "direction": "asc"}],
            only_requested_fields=True,
        )

        assert len(tasks) == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_entity_comments():
    """Test _get_entity_comments with different pagination parameters."""
    # Test with limit - Comment model uses "content" field, not "text"
    respx.get("https://example.com/api/v3/task/1/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"id": 1, "contentType": "Comment", "content": "Comment 1"},
                    {"id": 2, "contentType": "Comment", "content": "Comment 2"},
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        comments = await resource.get_comments(task_id=1, limit=10)

        assert len(comments) == 2
        assert comments[0].content == "Comment 1"
        assert comments[1].content == "Comment 2"


@pytest.mark.asyncio
@respx.mock
async def test_get_entity_comments_with_pagination():
    """Test _get_entity_comments with page_after."""
    respx.get(
        url__regex=r"https://example\.com/api/v3/task/1/comments\?.*pageAfter.*",
    ).mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [{"id": 2, "contentType": "Comment", "text": "Comment 2"}],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        comments = await resource.get_comments(
            task_id=1,
            page_after={"contentType": "Comment", "id": 1},
        )

        assert len(comments) == 1
        assert comments[0].id == 2


@pytest.mark.asyncio
@respx.mock
async def test_create_entity_comment():
    """Test _create_entity_comment with attaches and extra_fields."""
    respx.post("https://example.com/api/v3/task/1/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "id": 1,
                    "contentType": "Comment",
                    "content": "Test comment",
                    "work": 2.5,
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TasksResource(http_client)
        comment = await resource.create_comment(
            task_id=1,
            text="Test comment",
            work=2.5,
            attaches=[{"id": 10, "contentType": "File"}],
        )

        assert comment.id == 1
        assert comment.content == "Test comment"


@pytest.mark.asyncio
async def test_fetch_details_parallel_exceptions():
    """Test _fetch_details_parallel handles exceptions correctly."""
    from megaplan_sdk.resources.base import BaseResource

    class TestResource(BaseResource):
        pass

    async def failing_task():
        raise ValueError("Test error")

    async def success_task():
        return "success"

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TestResource(http_client)

        tasks = {
            "failing": failing_task(),
            "success": success_task(),
        }

        results = await resource._fetch_details_parallel(tasks)

        assert results["failing"] is None  # Exception should result in None
        assert results["success"] == "success"


@pytest.mark.asyncio
async def test_fetch_details_parallel_empty():
    """Test _fetch_details_parallel with empty tasks dict."""
    from megaplan_sdk.resources.base import BaseResource

    class TestResource(BaseResource):
        pass

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = TestResource(http_client)

        results = await resource._fetch_details_parallel({})

        assert results == {}
