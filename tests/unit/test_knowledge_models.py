from megaplan_sdk.models.knowledge import (
    KnowledgeArticle,
    KnowledgeBase,
    KnowledgeSectionWithArticles,
)


def test_knowledge_base_parses_full_section():
    section = KnowledgeBase(
        **{
            "contentType": "KnowledgeBase",
            "id": "11",
            "name": "Содержание Базы знаний",
            "content": "<p>html</p>",
            "accessRole": "owner",
            "lastUpdated": {"contentType": "DateTime", "value": "2026-01-22T14:30:25+00:00"},
            "lastUpdateBy": {"contentType": "Employee", "id": "1000028", "name": "Мужейко Мария"},
            "orderPos": 0,
            "expanded": True,
            "isDropped": False,
        }
    )
    assert section.id == 11  # coerced from str
    assert section.content == "<p>html</p>"
    assert section.access_role == "owner"
    assert section.last_updated is not None and section.last_updated.value.startswith("2026-01-22")
    assert section.last_update_by is not None and section.last_update_by.id == 1000028
    assert section.order_pos == 0
    assert section.is_dropped is False


def test_knowledge_base_allows_empty_name():
    section = KnowledgeBase(**{"contentType": "KnowledgeBase", "id": "12", "name": ""})
    assert section.id == 12
    assert section.name == ""


def test_knowledge_article_uses_base_not_parent():
    article = KnowledgeArticle(
        **{
            "contentType": "KnowledgeArticle",
            "id": "33",
            "name": "Постановка задачи в Мегаплан",
            "content": "<p>body</p>",
            "parent": None,
            "base": {"contentType": "KnowledgeBase", "id": "2", "name": "Рабочие вопросы"},
            "accessRole": "owner",
            "orderPos": 11,
        }
    )
    assert article.parent is None
    assert article.base is not None
    assert article.base.id == 2
    assert article.base.name == "Рабочие вопросы"


def test_section_with_articles_composite():
    section = KnowledgeBase(**{"contentType": "KnowledgeBase", "id": "2", "name": "Рабочие вопросы"})
    article = KnowledgeArticle(**{"contentType": "KnowledgeArticle", "id": "33", "name": "A"})
    composite = KnowledgeSectionWithArticles(section=section, articles=[article])
    assert composite.section.id == 2
    assert len(composite.articles) == 1
    assert composite.articles[0].id == 33


def test_section_with_articles_delegates_to_section():
    section = KnowledgeBase(id=11, name="Раздел", content="<p>x</p>")
    composite = KnowledgeSectionWithArticles(section=section, articles=[])
    assert composite.id == 11
    assert composite.name == "Раздел"
    assert composite.content == "<p>x</p>"
    assert composite.last_updated == section.last_updated


def test_knowledge_models_exported_from_package():
    import megaplan_sdk

    assert megaplan_sdk.KnowledgeBase is not None
    assert megaplan_sdk.KnowledgeArticle is not None
    assert megaplan_sdk.KnowledgeSectionWithArticles is not None
