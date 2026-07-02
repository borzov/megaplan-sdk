from megaplan_sdk.resources.knowledge_article import KnowledgeArticleResource


async def test_get_parses_article_with_base(megaplan_api, http_client):
    megaplan_api.get(
        "knowledgeArticle/33",
        data={
            "contentType": "KnowledgeArticle",
            "id": "33",
            "name": "Постановка задачи в Мегаплан",
            "content": "<p>body</p>",
            "parent": None,
            "base": {"contentType": "KnowledgeBase", "id": "2", "name": "Рабочие вопросы"},
        },
    )

    resource = KnowledgeArticleResource(http_client)
    article = await resource.get(33)

    assert article.id == 33
    assert article.parent is None
    assert article.base is not None and article.base.id == 2


async def test_article_resource_has_no_listing_methods(http_client):
    resource = KnowledgeArticleResource(http_client)
    assert not hasattr(resource, "list")
    assert not hasattr(resource, "iterate")
