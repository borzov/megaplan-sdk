import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.knowledge_article import KnowledgeArticleResource
from megaplan_sdk.resources.knowledge_base import KnowledgeBaseResource


def _section_full(section_id: int, content: str) -> dict:
    return {
        "contentType": "KnowledgeBase",
        "id": str(section_id),
        "name": "Раздел",
        "content": content,
        "accessRole": "owner",
        "orderPos": 0,
        "expanded": True,
        "isDropped": False,
    }


def _article(article_id: int, base_id: int) -> dict:
    return {
        "contentType": "KnowledgeArticle",
        "id": str(article_id),
        "name": f"Статья {article_id}",
        "content": "<p>body</p>",
        "parent": None,
        "base": {"contentType": "KnowledgeBase", "id": str(base_id), "name": "Раздел"},
    }


@pytest.mark.asyncio
@respx.mock
async def test_list_returns_flat_sections():
    respx.get("https://example.com/api/v3/knowledgeBase").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": [
                    {"contentType": "KnowledgeBase", "id": "2", "name": "Рабочие вопросы"},
                    {"contentType": "KnowledgeBase", "id": "5", "name": "Орг. вопросы"},
                ],
            },
        )
    )
    async with HTTPClient("https://example.com", access_token="token") as http:
        resource = KnowledgeBaseResource(http)
        sections = await resource.list()

    assert [s.id for s in sections] == [2, 5]


@pytest.mark.asyncio
@respx.mock
async def test_get_parses_full_section():
    respx.get("https://example.com/api/v3/knowledgeBase/11").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": _section_full(11, "<p>x</p>")})
    )
    async with HTTPClient("https://example.com", access_token="token") as http:
        resource = KnowledgeBaseResource(http)
        section = await resource.get(11)

    assert section.id == 11
    assert section.content == "<p>x</p>"


@pytest.mark.asyncio
@respx.mock
async def test_get_with_articles_filters_by_base_and_skips_failures():
    # Section 2 links to articles 33 (base=2, kept), 99 (base=5, dropped), 77 (404, skipped)
    content = (
        '<a href="/knowledge/2/33">a</a>'
        '<a href="/knowledge/2/99">b</a>'
        '<a href="/knowledge/2/77">c</a>'
        '<a href="/knowledge/5">section link ignored</a>'
    )
    respx.get("https://example.com/api/v3/knowledgeBase/2").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": _section_full(2, content)})
    )
    respx.get("https://example.com/api/v3/knowledgeArticle/33").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": _article(33, 2)})
    )
    respx.get("https://example.com/api/v3/knowledgeArticle/99").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": _article(99, 5)})
    )
    respx.get("https://example.com/api/v3/knowledgeArticle/77").mock(
        return_value=Response(404, json={"meta": {"status": 404, "errors": [{"error": "not found"}]}})
    )
    async with HTTPClient("https://example.com", access_token="token") as http:
        articles_res = KnowledgeArticleResource(http)
        resource = KnowledgeBaseResource(http, article_resource=articles_res)
        result = await resource.get_with_articles(2)

    assert result.section.id == 2
    assert [a.id for a in result.articles] == [33]  # 99 wrong base, 77 failed


@pytest.mark.asyncio
@respx.mock
async def test_get_with_articles_toc_section_returns_empty():
    # Table-of-contents section: only single-segment section links
    content = '<a href="/knowledge/2">s</a><a href="/knowledge/6">s</a>'
    respx.get("https://example.com/api/v3/knowledgeBase/11").mock(
        return_value=Response(200, json={"meta": {"status": 200}, "data": _section_full(11, content)})
    )
    async with HTTPClient("https://example.com", access_token="token") as http:
        resource = KnowledgeBaseResource(http, article_resource=KnowledgeArticleResource(http))
        result = await resource.get_with_articles(11)

    assert result.articles == []


@pytest.mark.asyncio
async def test_client_wires_knowledge_resources():
    from megaplan_sdk.client import MegaplanClient
    from megaplan_sdk.resources.knowledge_article import KnowledgeArticleResource as KAR
    from megaplan_sdk.resources.knowledge_base import KnowledgeBaseResource as KBR

    async with MegaplanClient(base_url="https://example.com", access_token="token") as client:
        assert isinstance(client.knowledge_base, KBR)
        assert isinstance(client.knowledge_article, KAR)
        # get_with_articles must reuse the client's article resource instance
        assert client.knowledge_base._article_resource is client.knowledge_article
