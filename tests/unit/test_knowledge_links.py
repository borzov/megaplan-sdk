from megaplan_sdk._knowledge_links import extract_article_ids


def test_extracts_two_segment_article_ids():
    html = (
        '<a href="https://ruvents.megaplan.ru/knowledge/2/33">A</a>'
        '<a href="https://ruvents.megaplan.ru/knowledge/2/22">B</a>'
    )
    assert extract_article_ids(html) == [33, 22]


def test_ignores_single_segment_section_links():
    html = '<a href="https://ruvents.megaplan.ru/knowledge/2">section</a>'
    assert extract_article_ids(html) == []


def test_dedupes_preserving_order():
    html = "/knowledge/2/33 /knowledge/5/33 /knowledge/2/22"
    assert extract_article_ids(html) == [33, 22]


def test_handles_relative_urls():
    assert extract_article_ids('<a href="/knowledge/2/33">x</a>') == [33]


def test_handles_empty_and_none():
    assert extract_article_ids("") == []
    assert extract_article_ids(None) == []
