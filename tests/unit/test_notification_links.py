"""Tests for the notification content link parser (#FR-F).

Notification.content is HTML; the entity it points at is only recoverable from
the anchor href. Shapes observed on the stand (100 records, 2026-08-07):
/task/N/card/#cN, /task/N/card/, /deals/N/card/, /deals/N/card/#cN, /event/N/card/.
"""

from megaplan_sdk._notification_links import parse_entity_ref


def test_parses_task_link_with_comment_anchor():
    """The most common shape: a comment inside a task."""
    ref = parse_entity_ref('Иван написал: текст :: задача <a href="/task/1006256/card/#c189191">Имя</a>')

    assert ref is not None
    assert ref.entity_type == "task"
    assert ref.entity_id == 1006256
    assert ref.comment_anchor == 189191


def test_parses_deal_link_and_normalizes_plural_segment():
    """Deals live at /deals/ in the UI, but the entity type is singular."""
    ref = parse_entity_ref('привязал сделку <a href="/deals/219/card/">Процесс</a>')

    assert ref is not None
    assert ref.entity_type == "deal"
    assert ref.entity_id == 219
    assert ref.comment_anchor is None


def test_parses_event_link():
    """Todo notifications point at /event/N/card/."""
    ref = parse_entity_ref('<a href="/event/4242/card/">Событие</a>')

    assert ref is not None
    assert ref.entity_type == "event"
    assert ref.entity_id == 4242


def test_returns_none_without_link():
    """Plain-text content yields no reference instead of a broken one."""
    assert parse_entity_ref("Ваш комментарий понравился пользователю") is None
    assert parse_entity_ref(None) is None


def test_ignores_links_without_an_entity_id():
    """Navigation links (no numeric id) are not entity references."""
    assert parse_entity_ref('<a href="/settings/application">настройки</a>') is None


def test_takes_the_first_entity_link():
    """Content may mention several entities; the subject is the first one."""
    ref = parse_entity_ref(
        '<a href="/task/1/card/">одна</a> и <a href="/deals/2/card/">другая</a>'
    )

    assert ref is not None
    assert (ref.entity_type, ref.entity_id) == ("task", 1)
