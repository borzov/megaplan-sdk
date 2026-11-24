"""Document cards, downloads and traversal over the two folder-scoped lists."""

import json
from urllib.parse import unquote

import httpx
import pytest

from megaplan_sdk import MegaplanClient

EMPLOYEE = {"contentType": "Employee", "id": 7, "name": "Автор", "bio": "я" * 65000}
CONTENT = {
    "contentType": "File",
    "id": 9,
    "name": "template.docx",
    "extension": "docx",
    "path": "/attach/template.docx",
}
VERSION = {
    "contentType": "DocVersion",
    "id": 5,
    "content": CONTENT,
    "userCreated": EMPLOYEE,
    "timeCreated": {"contentType": "DateTime", "value": "2026-11-24"},
}
DOC = {"contentType": "Doc", "id": 1, "actualVersion": VERSION, "userCreated": EMPLOYEE}
FOLDER = {"contentType": "DocFolder", "id": 4, "docs": [DOC]}


@pytest.fixture
async def client(megaplan_api):
    async with MegaplanClient(megaplan_api.base_url, access_token="dummy") as api:
        yield api


async def test_full_and_compact_docs_preserve_contents(client, megaplan_api):
    meta = {"status": 200, "pagination": {"count": 1}}
    megaplan_api.get("docFolder/4", json={"meta": meta, "data": FOLDER})
    megaplan_api.get("doc/1", data=DOC)
    folder = await client.docs.get_folder(4)
    assert folder.docs[0].actual_version.content.extension == "docx"
    assert folder.docs[0].actual_version.time_created.value == "2026-11-24"
    assert len(folder.model_dump_json(by_alias=True).encode()) > 100000
    compact = await client.docs.get_folder(4, compact=True)
    assert len(compact.model_dump_json(by_alias=True).encode()) < 100000
    raw = await client.raw("GET", "/api/v3/docFolder/4", compact=True)
    assert raw["meta"] == meta
    compact_doc = raw["data"]["docs"][0]
    assert compact_doc["actualVersion"]["content"] == CONTENT
    assert compact_doc["actualVersion"]["userCreated"] == {
        k: EMPLOYEE[k] for k in ["contentType", "name", "id"]
    }
    assert compact.docs[0].model_dump(by_alias=True, exclude_unset=True) == compact_doc
    assert (await client.docs.get(1, compact=True)).model_dump(
        by_alias=True, exclude_unset=True
    ) == compact_doc
    assert (await client.raw("GET", "/api/v3/docFolder/4"))["data"] == FOLDER


@pytest.mark.parametrize("many", [False, True])
async def test_raw_compact_preserves_top_level_employees(client, megaplan_api, many):
    row = {**EMPLOYEE, "manager": EMPLOYEE}
    megaplan_api.get("employee", data=[row] if many else row)
    data = (await client.raw("GET", "/api/v3/employee", compact=True))["data"]
    entity = data[0] if many else data
    assert entity["bio"] == EMPLOYEE["bio"]
    assert entity["manager"].keys() == {"contentType", "id", "name"}


async def test_download_document_or_content(client, megaplan_api):
    megaplan_api.get("doc/1", data=DOC)
    doc = await client.docs.get(1)
    route = megaplan_api.get(megaplan_api.base_url + CONTENT["path"]).mock(
        return_value=httpx.Response(200, content=b"sample")
    )
    for value in (doc, doc.actual_version.content, CONTENT, DOC):
        assert await client.docs.download(value) == b"sample"
    assert all(c.request.headers["Authorization"] == "Bearer dummy" for c in route.calls)
    megaplan_api.get("doc/2", data={"contentType": "Doc", "id": 2})
    with pytest.raises(ValueError, match="version"):
        await client.docs.download(await client.docs.get(2))
    with pytest.raises(ValueError, match="path"):
        await client.docs.download({"contentType": "File", "id": 22})


@pytest.mark.parametrize("recursive", [False, True])
async def test_folder_traversal_pages_and_cycles(client, megaplan_api, recursive):
    parents = {4: [5, 6], 5: [4, 6], 6: []}
    doc_ids = {4: [11, 12, 13], 5: [], 6: [14]}
    calls = []

    def respond(request):
        route = request.url.path.rsplit("/", 1)[-1]
        params = json.loads(unquote(request.url.query.decode()))
        folder = params["parentFolder"]
        assert folder["contentType"] == "DocFolder"
        folder_id = int(folder["id"])
        ids = parents[folder_id] if route == "docFolder" else doc_ids[folder_id]
        content_type = "DocFolder" if route == "docFolder" else "Doc"
        after = params.get("pageAfter")
        if after:
            assert after["contentType"] == content_type
            ids = ids[ids.index(int(after["id"])) + 1 :]
        calls.append((route, folder_id, bool(after)))
        return httpx.Response(
            200,
            json={"data": [{"contentType": content_type, "id": i} for i in ids[: params["limit"]]]},
        )

    for route in ("doc", "docFolder"):
        megaplan_api.get(route).mock(side_effect=respond)
    rows = [d.id async for d in client.docs.iterate(4, recursive=recursive, limit=2)]
    assert rows == ([11, 12, 13, 14] if recursive else [11, 12, 13])
    assert calls.count(("doc", 4, False)) == 1
    if recursive:
        assert ("docFolder", 4, True) in calls
    else:
        assert all(c[0] == "doc" for c in calls)


async def test_inline_version_does_not_hide_folder_siblings(client, megaplan_api):
    inline_doc = {**DOC, "id": 2, "actualVersion": {**VERSION, "content": "Текст документа"}}
    megaplan_api.get("docFolder/4", data={**FOLDER, "docs": [inline_doc, DOC]})
    folder = await client.docs.get_folder(4, compact=True)
    assert folder.docs[1].actual_version.content.path == CONTENT["path"]
    assert folder.docs[0].actual_version.content == "Текст документа"
    for value in (folder.docs[0], inline_doc, folder.docs[0].actual_version.content):
        with pytest.raises(ValueError, match="path"):
            await client.docs.download(value)


async def test_string_version_downloads_only_from_same_origin(client, megaplan_api):
    absolute = megaplan_api.base_url + CONTENT["path"]
    route = megaplan_api.get(absolute).mock(return_value=httpx.Response(200, content=b"document"))
    for path in [CONTENT["path"], absolute]:
        card = {**DOC, "actualVersion": {**VERSION, "content": path}}
        assert await client.docs.download(card) == b"document"
        assert await client.docs.download(path) == b"document"
    assert route.call_count == 4
    for value in [
        absolute.replace("https:", "http:"),
        absolute.replace("/attach", ":9443/attach"),
        "//foreign.example/file",
        "https://foreign.example/file",
        "file:relative",
        "text",
    ]:
        with pytest.raises(ValueError, match="path|origin"):
            await client.docs.download(value)


async def test_paginating_stops_on_nonconsecutive_repeated_cursor(client, megaplan_api):
    from megaplan_sdk import MegaplanError

    def respond(request):
        params = json.loads(unquote(request.url.query.decode()))
        previous = params.get("pageAfter", {}).get("id")
        return httpx.Response(
            200, json={"data": [{"contentType": "Doc", "id": 2 if previous == 1 else 1}]}
        )

    route = megaplan_api.get("doc").mock(side_effect=respond)
    pages = client.docs.iterate(4, limit=1)
    assert (await anext(pages)).id == 1
    assert (await anext(pages)).id == 2
    with pytest.raises(MegaplanError, match="cursor"):
        await anext(pages)
    assert route.call_count == 3


def test_binary_transport_checks_origin_for_file_objects(client):
    """File-shaped content and raw strings use the same origin check."""
    with pytest.raises(ValueError, match="origin"):
        client._http._binary_url("https://example.megaplan.ru:9443/file/document")
