"""Unit tests for CommentsResource."""

import json

import pytest


async def test_list_defaults_to_task_path(megaplan_api, comments):
    """Test that list() defaults to 'task' entity type path."""
    route = megaplan_api.get("task/123/comments", data=[])

    await comments.list(entity_id=123)

    assert route.called


async def test_list_respects_entity_type(megaplan_api, comments):
    """Test that list() uses the provided entity_type in the URL path."""
    route = megaplan_api.get("project/55/comments", data=[])

    await comments.list(entity_id=55, entity_type="project")

    assert route.called


async def test_list_deal_entity_type(megaplan_api, comments):
    """Test that list() works with 'deal' entity type."""
    route = megaplan_api.get("deal/99/comments", data=[])

    await comments.list(entity_id=99, entity_type="deal")

    assert route.called


async def test_create_defaults_to_task_path(megaplan_api, comments):
    """Test that create() defaults to 'task' entity type path."""
    route = megaplan_api.post(
        "task/123/comments", data={"id": 1, "contentType": "Comment", "text": "Hello"}
    )

    with pytest.warns(DeprecationWarning):
        await comments.create(entity_id=123, comment_data={"text": "Hello"})

    assert route.called


async def test_create_respects_entity_type(megaplan_api, comments):
    """Test that create() uses the provided entity_type in the URL path."""
    route = megaplan_api.post(
        "project/77/comments",
        data={"id": 2, "contentType": "Comment", "text": "Project comment"},
    )

    with pytest.warns(DeprecationWarning):
        await comments.create(
            entity_id=77, comment_data={"text": "Project comment"}, entity_type="project"
        )

    assert route.called


async def test_list_expand_owner_resolves_names(megaplan_api, comments):
    """Test that list(expand=['owner']) batch-loads Employee owners."""
    megaplan_api.get(
        "task/123/comments",
        data=[
            {
                "contentType": "Comment",
                "id": 1,
                "content": "hi",
                "owner": {"contentType": "Employee", "id": 1000037},
            }
        ],
    )
    megaplan_api.get(
        "employee/1000037",
        data={
            "contentType": "Employee",
            "id": 1000037,
            "name": "Иван Петров",
        },
    )

    result = await comments.list(entity_id=123, expand=["owner"])

    assert result[0].owner is not None
    assert result[0].owner.name == "Иван Петров"  # type: ignore[union-attr]


async def test_list_without_expand_returns_stub_owner(megaplan_api, comments):
    """Test that list() without expand leaves owner as a stub BaseEntity."""
    megaplan_api.get(
        "task/123/comments",
        data=[
            {
                "contentType": "Comment",
                "id": 1,
                "content": "hi",
                "owner": {"contentType": "Employee", "id": 1000037},
            }
        ],
    )

    result = await comments.list(entity_id=123)

    assert result[0].owner is not None
    assert result[0].owner.id == 1000037
    # name is not populated because no expand was requested
    assert not hasattr(result[0].owner, "name") or result[0].owner.name is None


async def test_iterate_respects_entity_type(megaplan_api, comments):
    """Test that iterate() threads entity_type to the correct API path."""
    route = megaplan_api.get("project/55/comments", data=[])
    results = [c async for c in comments.iterate(entity_id=55, entity_type="project")]
    assert route.called
    assert results == []


async def test_create_with_content_kwarg(megaplan_api, comments):
    """Test that create() with content kwarg sends correct JSON body."""
    route = megaplan_api.post(
        "task/123/comments", data={"contentType": "Comment", "id": 1, "content": "hi"}
    )
    await comments.create(entity_id=123, content="hi")
    body = json.loads(route.calls.last.request.content)
    assert body == {"content": "hi"}


async def test_create_legacy_text_remapped_with_warning(megaplan_api, comments):
    """Test that create() remaps comment_data['text'] to 'content' and emits DeprecationWarning."""
    route = megaplan_api.post(
        "task/123/comments", data={"contentType": "Comment", "id": 1, "content": "hi"}
    )
    with pytest.warns(DeprecationWarning):
        await comments.create(entity_id=123, comment_data={"text": "hi"})
    assert json.loads(route.calls.last.request.content) == {"content": "hi"}


async def test_create_both_content_and_data_raises(comments):
    """Test that passing both content and comment_data raises ValueError."""
    with pytest.raises(ValueError):
        await comments.create(entity_id=1, content="x", comment_data={"content": "x"})


async def test_create_neither_content_nor_data_raises(comments):
    """Test that passing neither content nor comment_data raises ValueError."""
    with pytest.raises(ValueError):
        await comments.create(entity_id=1)


async def test_create_work_serialized_as_value_in_seconds(megaplan_api, comments):
    """Test that work= is sent as DateInterval value in seconds (not seconds field).

    Empirically verified 2026-06-26: the server silently ignores the ``seconds``
    field and records 0 hours. The correct field is ``value``.
    For work=2.5 hours: int(2.5 * 3600) = 9000 seconds.
    """
    route = megaplan_api.post(
        "task/123/comments", data={"contentType": "Comment", "id": 7, "content": "x"}
    )
    await comments.create(entity_id=123, content="x", work=2.5)

    body = json.loads(route.calls.last.request.content)
    assert body["workTime"] == {"contentType": "DateInterval", "value": 9000}


async def test_get_accepts_entity_type_kwarg(megaplan_api, comments):
    """#17: get() accepts (and ignores) entity_type for API symmetry."""
    megaplan_api.get("comment/187507", data={"id": 187507, "contentType": "Comment"})
    comment = await comments.get(comment_id=187507, entity_type="task")
    assert comment.id == 187507


async def test_delete_accepts_entity_type_kwarg(megaplan_api, comments):
    """#17: delete() accepts (and ignores) entity_type for API symmetry."""
    megaplan_api.delete("comment/187507")
    await comments.delete(comment_id=187507, entity_type="task")
