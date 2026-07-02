"""Knowledge Base section resource for Megaplan API."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from megaplan_sdk._knowledge_links import extract_article_ids
from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.logging_config import logger
from megaplan_sdk.models.knowledge import (
    KnowledgeArticle,
    KnowledgeBase,
    KnowledgeSectionWithArticles,
)
from megaplan_sdk.pagination import Page
from megaplan_sdk.resources.base import BaseResource
from megaplan_sdk.resources.knowledge_article import KnowledgeArticleResource

if TYPE_CHECKING:
    from megaplan_sdk.cache import EntityCache


class KnowledgeBaseResource(BaseResource):
    """Resource for Knowledge Base sections.

    Provides ``get`` / ``list`` / ``iterate`` over the working endpoints, plus
    the experimental ``get_with_articles`` helper.

    NOTE: the server-side ``parent`` filter on ``GET /api/v3/knowledgeBase`` is
    ignored and sections are flat (no hierarchy), so ``list`` exposes no
    ``parent`` parameter. The real hierarchy is section -> articles via
    ``KnowledgeArticle.base``.
    """

    def __init__(
        self,
        http_client: HTTPClient,
        cache: EntityCache | None = None,
        article_resource: KnowledgeArticleResource | None = None,
    ) -> None:
        super().__init__(http_client, cache=cache)
        # Reused for get_with_articles; falls back to a self-built one (shared cache).
        self._article_resource = article_resource or KnowledgeArticleResource(
            http_client, cache=cache
        )

    async def get(self, section_id: int, use_cache: bool = True) -> KnowledgeBase:
        """Get a Knowledge Base section by ID (full object, including HTML content).

        Args:
            section_id: Section identifier.
            use_cache: Whether to use the entity cache (default: True).

        Returns:
            Full KnowledgeBase section including HTML content.
        """
        return await self._get_entity_cached(
            "knowledgeBase", section_id, KnowledgeBase, use_cache=use_cache
        )

    async def list(
        self,
        limit: int | None = None,
        page_after: dict[str, Any] | None = None,
        page_before: dict[str, Any] | None = None,
        page_with: dict[str, Any] | None = None,
        page: Page | None = None,
    ) -> list[KnowledgeBase]:
        """Get the flat list of Knowledge Base sections.

        The API has no working ``parent`` filter and sections have no
        hierarchy, so all sections are returned as a flat list.

        Args:
            limit: Number of items per page.
            page_after: Load page starting from this entity.
            page_before: Load page strictly before this entity.
            page_with: Load page containing this entity.
            page: Page position (replaces page_after/page_before/page_with).

        Returns:
            List of KnowledgeBase sections.
        """
        path = self._build_path("api", "v3", "knowledgeBase")
        params = self._build_list_params(
            limit=limit,
            page_after=page_after,
            page_before=page_before,
            page_with=page_with,
            page=page,
        )
        return await self._get_list(path, KnowledgeBase, params)

    async def iterate(self, limit: int = 100, **kwargs: Any) -> AsyncIterator[KnowledgeBase]:
        """Iterate over all Knowledge Base sections with automatic pagination.

        Args:
            limit: Number of items per page.
            **kwargs: Additional parameters to pass to list().

        Yields:
            KnowledgeBase section objects.
        """
        section: KnowledgeBase
        async for section in self._iterate_generic(  # type: ignore[valid-type]
            "KnowledgeBase",
            self.list,
            limit,
            **kwargs,
        ):
            yield section

    async def get_with_articles(
        self, section_id: int, use_cache: bool = True
    ) -> KnowledgeSectionWithArticles:
        """Get a section together with its articles (EXPERIMENTAL).

        The Megaplan API has no endpoint to list a section's articles, so this
        discovers them by parsing ``/knowledge/<section>/<article>`` links in
        the section's HTML ``content`` and fetching each article. Only articles
        whose ``base.id`` equals ``section_id`` are kept (so a table-of-contents
        section cannot pull in unrelated articles). Individual article failures
        are skipped with a warning.

        FRAGILE: depends on Megaplan's HTML link format. If the format changes,
        ``articles`` may come back empty even when the section has articles.

        Args:
            section_id: Section identifier.
            use_cache: Whether to use the entity cache (default: True).

        Returns:
            KnowledgeSectionWithArticles with section and its filtered articles.
        """
        section = await self.get(section_id, use_cache=use_cache)
        article_ids = extract_article_ids(section.content)

        fetched = await asyncio.gather(
            *(self._article_resource.get(aid, use_cache=use_cache) for aid in article_ids),
            return_exceptions=True,
        )

        articles: list[KnowledgeArticle] = []
        for aid, result in zip(article_ids, fetched, strict=True):
            if isinstance(result, BaseException):
                logger.warning("Failed to load knowledge article %s: %s", aid, result)
                continue
            if result.base is not None and result.base.id == section_id:
                articles.append(result)

        return KnowledgeSectionWithArticles(section=section, articles=articles)
