"""Tests for NotificationsResource (#FR-F).

/api/v3/notification is the only reliable source of "the user was mentioned":
the server sets isMention itself. Payload shape and accepted query fields were
taken from the stand on 2026-08-07 — the server rejects unknown fields with 422
("not defined for content type GetAllNotificationsRequest"), and the only
filter it accepts besides pagination is isActive.
"""

import json
from urllib.parse import unquote

from megaplan_sdk.models.comment import Comment

NOTIFICATION = {
    "contentType": "Notification",
    "id": "2402317",
    "type": "BumsTaskN_TaskNewComment",
    "content": 'Иван написал: текст :: задача <a href="/task/1006256/card/#c189191">Договор</a>',
    "time": {"contentType": "DateTime", "value": "2026-07-28T13:35:19+00:00"},
    "isActive": True,
    "size": 1,
    "isMention": True,
    "isHistoryLog": False,
    "sender": {"contentType": "Employee", "id": "1000004", "name": "Чертилов Илья"},
    "subject": {"contentType": "Comment", "id": "189191", "content": "текст"},
}

DEAL_NOTIFICATION = {
    "contentType": "Notification",
    "id": "2401421",
    "type": "BumsTradeN_DealAddRole",
    "content": 'назначил вас :: сделка <a href="/deals/1955/card/">Процесс</a>',
    "time": {"contentType": "DateTime", "value": "2026-07-27T10:00:00+00:00"},
    "isActive": True,
    "isMention": False,
    "sender": {"contentType": "Employee", "id": "1000003"},
    "subject": {"contentType": "Deal", "id": "1955", "name": "Процесс"},
}


def sent_query(route) -> dict:
    """Decode Megaplan's query literal from a recorded request."""
    return json.loads(unquote(route.calls[0].request.url.query.decode()))


async def test_list_parses_notifications(megaplan_api, notifications):
    """Typed fields, including the isMention flag the whole feature exists for."""
    megaplan_api.get("notification", data=[NOTIFICATION])

    items = await notifications.list(limit=1)

    assert len(items) == 1
    item = items[0]
    assert item.id == 2402317
    assert item.type == "BumsTaskN_TaskNewComment"
    assert item.is_mention is True
    assert item.is_active is True
    assert item.time is not None and item.time.value.startswith("2026-07-28")
    assert item.sender is not None and item.sender.name == "Чертилов Илья"
    assert item.subject is not None and item.subject.content_type == "Comment"


async def test_list_sends_limit_as_megaplan_literal(megaplan_api, notifications):
    """Query goes out as ?{"limit": 60}, not as key=value pairs."""
    route = megaplan_api.get("notification", data=[])

    await notifications.list(limit=60)

    assert sent_query(route) == {"limit": 60}


async def test_only_active_is_a_server_side_filter(megaplan_api, notifications):
    """isActive is the one filter the server accepts (verified on the stand)."""
    route = megaplan_api.get("notification", data=[])

    await notifications.list(limit=5, only_active=True)

    assert sent_query(route) == {"limit": 5, "isActive": True}


async def test_only_mentions_filters_client_side(megaplan_api, notifications):
    """The server has no mention filter, so the SDK filters what it received."""
    route = megaplan_api.get("notification", data=[NOTIFICATION, DEAL_NOTIFICATION])

    items = await notifications.list(limit=10, only_mentions=True)

    assert [item.id for item in items] == [2402317]
    assert "isMention" not in sent_query(route), "server rejects isMention with 422"


async def test_entity_ref_points_at_the_mentioned_entity(megaplan_api, notifications):
    """Consumers need the entity behind the notification, not the HTML."""
    megaplan_api.get("notification", data=[NOTIFICATION, DEAL_NOTIFICATION])

    task_note, deal_note = await notifications.list(limit=2)

    assert task_note.entity_ref is not None
    assert (task_note.entity_ref.entity_type, task_note.entity_ref.entity_id) == ("task", 1006256)
    assert task_note.entity_ref.comment_anchor == 189191
    assert deal_note.entity_ref is not None
    assert (deal_note.entity_ref.entity_type, deal_note.entity_ref.entity_id) == ("deal", 1955)


async def test_subject_comment_is_typed_only_for_comment_subjects(megaplan_api, notifications):
    """subject is polymorphic (Comment/Deal/Task/Todo); only comments parse as Comment."""
    megaplan_api.get("notification", data=[NOTIFICATION, DEAL_NOTIFICATION])

    task_note, deal_note = await notifications.list(limit=2)

    assert isinstance(task_note.subject_comment, Comment)
    assert task_note.subject_comment.content == "текст"
    assert deal_note.subject_comment is None


async def test_iterate_paginates_with_page_after(megaplan_api, notifications):
    """Auto-pagination uses Notification references, like every other resource."""
    first = dict(NOTIFICATION)
    second = dict(DEAL_NOTIFICATION)
    responses = [[first, second], []]

    def handler(request):
        from httpx import Response

        return Response(200, json={"meta": {"status": 200}, "data": responses.pop(0)})

    megaplan_api.router.request(
        "GET", f"{megaplan_api.base_url}/api/v3/notification"
    ).mock(side_effect=handler)

    collected = [item.id async for item in notifications.iterate(limit=2)]

    assert collected == [2402317, 2401421]


async def test_iterate_only_mentions_does_not_truncate_pagination(megaplan_api, notifications):
    """Mention filtering must happen after paging, not inside the page loop.

    A filtered page shorter than ``limit`` would otherwise look like the last
    page and silently drop every older mention.
    """
    from httpx import Response

    pages = [
        [NOTIFICATION, DEAL_NOTIFICATION],
        [dict(NOTIFICATION, id="2400000")],
    ]

    def handler(request):
        page = pages.pop(0) if pages else []
        return Response(200, json={"meta": {"status": 200}, "data": page})

    megaplan_api.router.request(
        "GET", f"{megaplan_api.base_url}/api/v3/notification"
    ).mock(side_effect=handler)

    collected = [item.id async for item in notifications.iterate(limit=2, only_mentions=True)]

    assert collected == [2402317, 2400000]


async def test_counter_returns_mention_count(megaplan_api, notifications):
    """/notification/counter is the cheap "is there anything new" probe."""
    megaplan_api.get(
        "notification/counter",
        data={
            "contentType": "Counter",
            "id": "notifications",
            "attributes": ["mention"],
            "count": 2047,
        },
    )

    counter = await notifications.counter()

    assert counter.count == 2047
    assert counter.attributes == ["mention"]


async def test_activity_types_keeps_string_ids(megaplan_api, notifications):
    """Notification type ids are strings (BumsCommonN_CommentLiked), not numbers."""
    megaplan_api.get(
        "notification/activityTypes",
        data=[
            {
                "contentType": "NotificationType",
                "id": "BumsCommonN_CommentLiked",
                "name": "Ваш комментарий понравился пользователю",
            }
        ],
    )

    types = await notifications.activity_types()

    assert types[0].id == "BumsCommonN_CommentLiked"
    assert types[0].name == "Ваш комментарий понравился пользователю"


def test_notification_models_are_exported_from_the_package():
    """Consumers import models from megaplan_sdk, not from internal modules."""
    from megaplan_sdk import (  # noqa: F401
        Notification,
        NotificationCounter,
        NotificationEntityRef,
        NotificationType,
    )
