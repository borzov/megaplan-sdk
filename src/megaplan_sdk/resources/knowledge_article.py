"""Knowledge Base article resource for Megaplan API."""

from megaplan_sdk.models.knowledge import KnowledgeArticle
from megaplan_sdk.resources.base import BaseResource


class KnowledgeArticleResource(BaseResource):
    """Resource for Knowledge Base articles.

    Only ``get(id)`` is supported: the Megaplan API has NO endpoint to list
    articles (``GET /api/v3/knowledgeArticle`` returns 404). To discover the
    articles of a section, use ``client.knowledge_base.get_with_articles()``.
    """

    async def get(self, article_id: int, use_cache: bool = True) -> KnowledgeArticle:
        """Get a Knowledge Base article by ID.

        Args:
            article_id: Article identifier.
            use_cache: Whether to use the entity cache (default: True).

        Returns:
            The article, including its ``base`` (parent section) reference.
            Note: ``article.parent`` is always None in the API — use ``base``.
        """
        return await self._get_entity_cached(
            "knowledgeArticle", article_id, KnowledgeArticle, use_cache=use_cache
        )
