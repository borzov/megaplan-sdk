"""Entity links inside notification HTML content (#FR-F).

FRAGILE: this module is the single place coupled to the HTML Megaplan puts in
``Notification.content``. The API returns no structured reference to the entity
a notification is about — only an anchor in the rendered text. Link shapes seen
on the stand (100 records, 2026-08-07): ``/task/N/card/#cN``, ``/task/N/card/``,
``/deals/N/card/``, ``/deals/N/card/#cN``, ``/event/N/card/``.
"""

import re

from pydantic import BaseModel

# href="/<section>/<id>/card/[#c<comment_id>]" — the only shape the UI emits
# for entity cards. Links without a numeric id (navigation, settings) never match.
_ENTITY_LINK_RE = re.compile(
    r'href="/(?P<section>[a-zA-Z]+)/(?P<id>\d+)/card/(?:#c(?P<anchor>\d+))?'
)

# UI sections whose path differs from the entity type.
_SECTION_TO_ENTITY_TYPE = {"deals": "deal"}


class NotificationEntityRef(BaseModel):
    """Entity a notification points at.

    Attributes:
        entity_type: Entity type in SDK terms ("task", "deal", "event").
        entity_id: Numeric entity identifier.
        comment_anchor: Comment id from the ``#c<id>`` anchor, when the
            notification is about a specific comment.
    """

    entity_type: str
    entity_id: int
    comment_anchor: int | None = None


def parse_entity_ref(content: str | None) -> NotificationEntityRef | None:
    """Extract the entity reference from a notification's HTML content.

    Args:
        content: ``Notification.content`` HTML, or None.

    Returns:
        The first entity reference found, or None when the content carries no
        entity link (e.g. "Ваш комментарий понравился пользователю").
    """
    match = _ENTITY_LINK_RE.search(content or "")
    if match is None:
        return None

    section = match.group("section")
    anchor = match.group("anchor")
    return NotificationEntityRef(
        entity_type=_SECTION_TO_ENTITY_TYPE.get(section, section),
        entity_id=int(match.group("id")),
        comment_anchor=int(anchor) if anchor else None,
    )
