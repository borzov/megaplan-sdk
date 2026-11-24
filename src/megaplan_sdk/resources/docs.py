"""Read documents and walk folder-scoped document lists."""

from collections import deque
from collections.abc import AsyncIterator
from typing import Any

from megaplan_sdk.exceptions import MegaplanError
from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.models.common import File
from megaplan_sdk.models.doc import Doc, DocFolder
from megaplan_sdk.resources.attachments import AttachmentsResource
from megaplan_sdk.resources.base import BaseResource


def compact_employee_refs(data: Any, *, nested: bool = False) -> Any:
    """Copy API data, retaining only identity and name on nested employee links."""
    if isinstance(data, list):
        return [compact_employee_refs(row, nested=nested) for row in data]
    if isinstance(data, dict):
        if nested and data.get("contentType") == "Employee" and "id" in data:
            return {key: data[key] for key in ("contentType", "id", "name") if key in data}
        return {key: compact_employee_refs(value, nested=True) for key, value in data.items()}
    return data


class DocsResource(BaseResource):
    """Read documents and download their current content."""

    def __init__(self, http_client: HTTPClient, attachments: AttachmentsResource) -> None:
        """Use the client's authorized JSON and binary transports."""
        super().__init__(http_client)
        self._attachments = attachments

    async def get(self, doc_id: int, *, compact: bool = False) -> Doc:
        """Get a document card, optionally shortening nested employee references."""
        path = self._build_path("api", "v3", "doc", str(doc_id))
        data = self._parse_single_response(await self._http.get(path))
        return Doc.model_validate(compact_employee_refs(data) if compact else data)

    async def get_folder(self, folder_id: int, *, compact: bool = False) -> DocFolder:
        """Get a folder, including the documents embedded in its card."""
        path = self._build_path("api", "v3", "docFolder", str(folder_id))
        data = self._parse_single_response(await self._http.get(path))
        return DocFolder.model_validate(compact_employee_refs(data) if compact else data)

    async def download(self, doc_or_content: Doc | File | str | dict[str, Any]) -> bytes:
        """Download a document's current version or a content object by its path.

        Raises:
            ValueError: The document has no available version or the content lacks a path.
        """
        content: Any = doc_or_content
        if isinstance(doc_or_content, dict) and (
            doc_or_content.get("contentType") == "Doc" or "actualVersion" in doc_or_content
        ):
            doc_or_content = Doc.model_validate(doc_or_content)
        if isinstance(doc_or_content, Doc):
            version = doc_or_content.actual_version
            if version is None or version.content is None:
                raise ValueError("Document has no current version with downloadable content")
            content = version.content
        if isinstance(content, str) and not content.startswith(("/", "https://", "http://")):
            raise ValueError("Document content has no downloadable file path")
        return await self._attachments.download(content)

    async def _entries(
        self, route: str, folder_id: int, limit: int
    ) -> AsyncIterator[dict[str, Any]]:
        path = self._build_path("api", "v3", route)
        params: dict[str, Any] = {
            "parentFolder": {"contentType": "DocFolder", "id": folder_id},
            "limit": limit,
        }
        if route == "doc":
            params["fields"] = ["actualVersion"]
        else:
            params["onlyRequestedFields"] = True
            params["fields"] = ["id"]
        seen_cursors: set[tuple[str, str]] = set()
        while True:
            page = self._parse_list_response(await self._http.get(path, params=params))
            if not page:
                return
            last = page[-1]
            cursor = {"contentType": last["contentType"], "id": last["id"]}
            key = (last["contentType"], str(last["id"]))
            if key in seen_cursors:
                raise MegaplanError(f"{route} pagination repeated its cursor")
            seen_cursors.add(key)
            for row in page:
                yield row
            params["pageAfter"] = cursor

    async def iterate(
        self, folder_id: int, recursive: bool = False, *, compact: bool = False, limit: int = 100
    ) -> AsyncIterator[Doc]:
        """Yield documents in this folder and optionally visit each descendant folder once."""
        if limit < 1:
            raise ValueError("limit must be positive")
        pending = deque([folder_id])
        visited = {folder_id}
        while pending:
            current = pending.popleft()
            async for row in self._entries("doc", current, limit):
                yield Doc.model_validate(compact_employee_refs(row) if compact else row)
            if recursive:
                async for folder in self._entries("docFolder", current, limit):
                    child = int(folder["id"])
                    if child not in visited:
                        pending.append(child)
                        visited.add(child)
