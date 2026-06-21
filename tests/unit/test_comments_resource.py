"""Unit tests for CommentsResource."""

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
        await resource.create(
            entity_id=77, comment_data={"text": "Project comment"}, entity_type="project"
        )

    assert route.called
