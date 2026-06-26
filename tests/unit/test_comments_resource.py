"""Unit tests for CommentsResource."""

import json
import warnings

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.comments import CommentsResource


@pytest.mark.asyncio
@respx.mock
async def test_list_defaults_to_task_path():
    """Test that list() defaults to 'task' entity type path."""
    route = respx.get("https://example.com/api/v3/task/123/comments").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": []})
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = CommentsResource(http_client)
        await resource.list(entity_id=123)

    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_list_respects_entity_type():
    """Test that list() uses the provided entity_type in the URL path."""
    route = respx.get("https://example.com/api/v3/project/55/comments").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": []})
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = CommentsResource(http_client)
        await resource.list(entity_id=55, entity_type="project")

    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_list_deal_entity_type():
    """Test that list() works with 'deal' entity type."""
    route = respx.get("https://example.com/api/v3/deal/99/comments").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": []})
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = CommentsResource(http_client)
        await resource.list(entity_id=99, entity_type="deal")

    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_create_defaults_to_task_path():
    """Test that create() defaults to 'task' entity type path."""
    route = respx.post("https://example.com/api/v3/task/123/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 1, "contentType": "Comment", "text": "Hello"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = CommentsResource(http_client)
        with pytest.warns(DeprecationWarning):
            await resource.create(entity_id=123, comment_data={"text": "Hello"})

    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_create_respects_entity_type():
    """Test that create() uses the provided entity_type in the URL path."""
    route = respx.post("https://example.com/api/v3/project/77/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 2, "contentType": "Comment", "text": "Project comment"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = CommentsResource(http_client)
        with pytest.warns(DeprecationWarning):
            await resource.create(
                entity_id=77, comment_data={"text": "Project comment"}, entity_type="project"
            )

    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_list_expand_owner_resolves_names():
    """Test that list(expand=['owner']) batch-loads Employee owners."""
    respx.get("https://example.com/api/v3/task/123/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {
                        "contentType": "Comment",
                        "id": 1,
                        "content": "hi",
                        "owner": {"contentType": "Employee", "id": 1000037},
                    }
                ],
            },
        )
    )
    respx.get("https://example.com/api/v3/employee/1000037").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "contentType": "Employee",
                    "id": 1000037,
                    "name": "Иван Петров",
                },
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = CommentsResource(http_client)
        comments = await resource.list(entity_id=123, expand=["owner"])

    assert comments[0].owner is not None
    assert comments[0].owner.name == "Иван Петров"  # type: ignore[union-attr]


@pytest.mark.asyncio
@respx.mock
async def test_list_without_expand_returns_stub_owner():
    """Test that list() without expand leaves owner as a stub BaseEntity."""
    respx.get("https://example.com/api/v3/task/123/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {
                        "contentType": "Comment",
                        "id": 1,
                        "content": "hi",
                        "owner": {"contentType": "Employee", "id": 1000037},
                    }
                ],
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = CommentsResource(http_client)
        comments = await resource.list(entity_id=123)

    assert comments[0].owner is not None
    assert comments[0].owner.id == 1000037
    # name is not populated because no expand was requested
    assert not hasattr(comments[0].owner, "name") or comments[0].owner.name is None


@pytest.mark.asyncio
@respx.mock
async def test_iterate_respects_entity_type():
    """Test that iterate() threads entity_type to the correct API path."""
    route = respx.get("https://example.com/api/v3/project/55/comments").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": []})
    )
    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = CommentsResource(http_client)
        results = [c async for c in resource.iterate(entity_id=55, entity_type="project")]
    assert route.called
    assert results == []


@pytest.mark.asyncio
@respx.mock
async def test_create_with_content_kwarg():
    """Test that create() with content kwarg sends correct JSON body."""
    route = respx.post("https://example.com/api/v3/task/123/comments").mock(
        return_value=Response(200, json={"meta": {"status": 200},
                                         "data": {"contentType": "Comment", "id": 1,
                                                  "content": "hi"}})
    )
    async with HTTPClient("https://example.com", access_token="token") as http:
        await CommentsResource(http).create(entity_id=123, content="hi")
    body = json.loads(route.calls.last.request.content)
    assert body == {"content": "hi"}


@pytest.mark.asyncio
@respx.mock
async def test_create_legacy_text_remapped_with_warning():
    """Test that create() remaps comment_data['text'] to 'content' and emits DeprecationWarning."""
    route = respx.post("https://example.com/api/v3/task/123/comments").mock(
        return_value=Response(200, json={"meta": {"status": 200},
                                         "data": {"contentType": "Comment", "id": 1,
                                                  "content": "hi"}})
    )
    async with HTTPClient("https://example.com", access_token="token") as http:
        with pytest.warns(DeprecationWarning):
            await CommentsResource(http).create(
                entity_id=123, comment_data={"text": "hi"}
            )
    assert json.loads(route.calls.last.request.content) == {"content": "hi"}


@pytest.mark.asyncio
async def test_create_both_content_and_data_raises():
    """Test that passing both content and comment_data raises ValueError."""
    async with HTTPClient("https://example.com", access_token="token") as http:
        with pytest.raises(ValueError):
            await CommentsResource(http).create(
                entity_id=1, content="x", comment_data={"content": "x"}
            )


@pytest.mark.asyncio
async def test_create_neither_content_nor_data_raises():
    """Test that passing neither content nor comment_data raises ValueError."""
    async with HTTPClient("https://example.com", access_token="token") as http:
        with pytest.raises(ValueError):
            await CommentsResource(http).create(entity_id=1)


@pytest.mark.asyncio
@respx.mock
async def test_create_work_serialized_as_value_in_seconds():
    """Test that work= is sent as DateInterval value in seconds (not seconds field).

    Empirically verified 2026-06-26: the server silently ignores the ``seconds``
    field and records 0 hours. The correct field is ``value``.
    For work=2.5 hours: int(2.5 * 3600) = 9000 seconds.
    """
    route = respx.post("https://example.com/api/v3/task/123/comments").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"contentType": "Comment", "id": 7, "content": "x"},
            },
        )
    )
    async with HTTPClient("https://example.com", access_token="token") as http:
        await CommentsResource(http).create(entity_id=123, content="x", work=2.5)

    body = json.loads(route.calls.last.request.content)
    assert body["workTime"] == {"contentType": "DateInterval", "value": 9000}
