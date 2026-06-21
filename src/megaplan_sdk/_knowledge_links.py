"""HTML link parsing for Knowledge Base article discovery.

EXPERIMENTAL / FRAGILE: this module is the single place coupled to Megaplan's
HTML format. The Megaplan API has no endpoint to list articles in a section,
so article IDs are discovered by parsing ``/knowledge/<section>/<article>``
links inside a section's HTML ``content``.
"""

import re

# Matches /knowledge/<section_id> and /knowledge/<section_id>/<article_id>
# inside href values; scheme/host-agnostic (absolute or relative URLs).
_KNOWLEDGE_LINK_RE = re.compile(r"/knowledge/(\d+)(?:/(\d+))?")


def extract_article_ids(html: str | None) -> list[int]:
    """Extract article IDs from two-segment ``/knowledge/<section>/<article>`` links.

    Single-segment ``/knowledge/<section>`` links (section references, e.g. a
    table of contents) are ignored. Returns unique IDs in first-seen order.
    """
    seen: dict[int, None] = {}
    for _section, article in _KNOWLEDGE_LINK_RE.findall(html or ""):
        if article:
            seen.setdefault(int(article), None)
    return list(seen)
