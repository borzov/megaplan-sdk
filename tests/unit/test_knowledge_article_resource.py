import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.knowledge_article import KnowledgeArticleResource


@pytest.mark.asyncio
@respx.mock
async def test_get_parses_article_with_base():
    respx.get("https://example.com/api/v3/knowledgeArticle/33").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {
                    "contentType": "KnowledgeArticle",
                    "id": "33",
                    "name": "Постановка задачи в Мегаплан",
                    "content": "<p>body</p>",
                    "parent": None,
                    "base": {"contentType": "KnowledgeBase", "id": "2", "name": "Рабочие вопросы"},
                },
            },
        )
    )
    async with HTTPClient("https://example.com", access_token="token") as http:
        resource = KnowledgeArticleResource(http)
        article = await resource.get(33)

    assert article.id == 33
    assert article.parent is None
    assert article.base is not None and article.base.id == 2


@pytest.mark.asyncio
async def test_article_resource_has_no_listing_methods():
    async with HTTPClient("https://example.com", access_token="token") as http:
        resource = KnowledgeArticleResource(http)
        assert not hasattr(resource, "list")
        assert not hasattr(resource, "iterate")
