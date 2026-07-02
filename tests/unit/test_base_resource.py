"""Unit tests for BaseResource."""

from httpx import Response

from megaplan_sdk.resources.base import BaseResource


async def test_pagination_page_after(megaplan_api, tasks):
    """Test pageAfter parameter in query params."""
    megaplan_api.get("task", data=[{"id": 2, "contentType": "Task", "name": "Task 2"}])

    result = await tasks.list(
        limit=10,
        page_after={"contentType": "Task", "id": 1},
    )

    assert len(result) == 1
    assert result[0].id == 2


async def test_pagination_page_before(megaplan_api, tasks):
    """Test pageBefore parameter in query params."""
    megaplan_api.get("task", data=[{"id": 1, "contentType": "Task", "name": "Task 1"}])

    result = await tasks.list(
        limit=10,
        page_before={"contentType": "Task", "id": 2},
    )

    assert len(result) == 1
    assert result[0].id == 1


async def test_pagination_page_with(megaplan_api, tasks):
    """Test pageWith parameter in query params."""
    megaplan_api.get("task", data=[{"id": 5, "contentType": "Task", "name": "Task 5"}])

    result = await tasks.list(
        limit=10,
        page_with={"contentType": "Task", "id": 5},
    )

    assert len(result) == 1
    assert result[0].id == 5


async def test_iterate_multiple_pages(megaplan_api, tasks):
    """Test iterate() with multiple pages."""
    # First page - TasksResource adds statuses parameter
    route = megaplan_api.router.get(f"{megaplan_api.base_url}/api/v3/task")
    route.mock(
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

    collected = []
    async for task in tasks.iterate(limit=2):
        collected.append(task)

    assert len(collected) == 3
    assert collected[0].id == 1
    assert collected[1].id == 2
    assert collected[2].id == 3


async def test_iterate_empty_result(megaplan_api, tasks):
    """Test iterate() with empty result."""
    megaplan_api.get("task", data=[])

    collected = []
    async for task in tasks.iterate(limit=10):
        collected.append(task)

    assert len(collected) == 0


async def test_iterate_partial_page(megaplan_api, tasks):
    """Test iterate() stops when last page < limit."""
    # First page with 2 items (limit is 10, but only 2 returned)
    megaplan_api.get(
        "task",
        data=[
            {"id": 1, "contentType": "Task", "name": "Task 1"},
            {"id": 2, "contentType": "Task", "name": "Task 2"},
        ],
    )

    collected = []
    async for task in tasks.iterate(limit=10):
        collected.append(task)

    assert len(collected) == 2
    # Should not make second request since len(items) < limit


async def test_fields_parameter(megaplan_api, tasks):
    """Test fields parameter in query."""
    megaplan_api.get("task", data=[{"id": 1, "contentType": "Task", "name": "Task 1"}])

    result = await tasks.list(fields=["name", "status"])

    assert len(result) == 1


async def test_sort_by_parameter(megaplan_api, tasks):
    """Test sortBy parameter in query."""
    megaplan_api.get("task", data=[{"id": 1, "contentType": "Task", "name": "Task 1"}])

    result = await tasks.list(
        sort_by=[{"field": "name", "direction": "asc"}],
    )

    assert len(result) == 1


async def test_only_requested_fields(megaplan_api, tasks):
    """Test onlyRequestedFields parameter in query."""
    megaplan_api.get("task", data=[{"id": 1, "contentType": "Task", "name": "Task 1"}])

    result = await tasks.list(only_requested_fields=True)

    assert len(result) == 1


async def test_build_list_params_combinations(megaplan_api, tasks):
    """Test combinations of all parameters together."""
    megaplan_api.get("task", data=[{"id": 1, "contentType": "Task", "name": "Task 1"}])

    result = await tasks.list(
        limit=10,
        page_after={"contentType": "Task", "id": 1},
        fields=["name"],
        sort_by=[{"field": "name", "direction": "asc"}],
        only_requested_fields=True,
    )

    assert len(result) == 1


async def test_get_entity_comments(megaplan_api, tasks):
    """Test _get_entity_comments with different pagination parameters."""
    # Test with limit - Comment model uses "content" field, not "text"
    megaplan_api.get(
        "task/1/comments",
        data=[
            {"id": 1, "contentType": "Comment", "content": "Comment 1"},
            {"id": 2, "contentType": "Comment", "content": "Comment 2"},
        ],
    )

    comments = await tasks.get_comments(task_id=1, limit=10)

    assert len(comments) == 2
    assert comments[0].content == "Comment 1"
    assert comments[1].content == "Comment 2"


async def test_get_entity_comments_with_pagination(megaplan_api, tasks):
    """Test _get_entity_comments with page_after."""
    megaplan_api.get(
        "task/1/comments",
        data=[{"id": 2, "contentType": "Comment", "text": "Comment 2"}],
    )

    comments = await tasks.get_comments(
        task_id=1,
        page_after={"contentType": "Comment", "id": 1},
    )

    assert len(comments) == 1
    assert comments[0].id == 2


async def test_create_entity_comment(megaplan_api, tasks):
    """Test _create_entity_comment with attaches and extra_fields."""
    megaplan_api.post(
        "task/1/comments",
        data={
            "id": 1,
            "contentType": "Comment",
            "content": "Test comment",
            "work": 2.5,
        },
    )

    comment = await tasks.create_comment(
        task_id=1,
        text="Test comment",
        work=2.5,
        attaches=[{"id": 10, "contentType": "File"}],
    )

    assert comment.id == 1
    assert comment.content == "Test comment"


async def test_fetch_details_parallel_exceptions(http_client):
    """Test _fetch_details_parallel handles exceptions correctly."""

    class TestResource(BaseResource):
        pass

    async def failing_task():
        raise ValueError("Test error")

    async def success_task():
        return "success"

    resource = TestResource(http_client)

    tasks = {
        "failing": failing_task(),
        "success": success_task(),
    }

    results = await resource._fetch_details_parallel(tasks)

    assert results["failing"] is None  # Exception should result in None
    assert results["success"] == "success"


async def test_fetch_details_parallel_empty(http_client):
    """Test _fetch_details_parallel with empty tasks dict."""

    class TestResource(BaseResource):
        pass

    resource = TestResource(http_client)

    results = await resource._fetch_details_parallel({})

    assert results == {}


def test_knowledge_content_types_defined():
    """Test that KnowledgeBase and KnowledgeArticle ContentType constants are defined."""
    from megaplan_sdk.constants import ContentType

    assert ContentType.KNOWLEDGE_BASE == "KnowledgeBase"
    assert ContentType.KNOWLEDGE_ARTICLE == "KnowledgeArticle"


def test_entity_type_maps_knowledge_segments():
    """Test that knowledgeBase and knowledgeArticle map to correct ContentTypes."""
    assert BaseResource._entity_type_to_content_type("knowledgeBase") == "KnowledgeBase"
    assert BaseResource._entity_type_to_content_type("knowledgeArticle") == "KnowledgeArticle"
