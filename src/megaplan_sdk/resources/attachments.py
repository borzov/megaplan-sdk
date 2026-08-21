"""Attachments resource: authorized download and upload of files (#FR-C, #FR-D).

``Comment.attaches`` / ``Task.attaches`` items carry a relative ``path``
(e.g. ``/attach/SdfFileM_File/File/237/81/x.png``) that requires a Bearer
header to fetch. This resource owns that logic so callers never touch
``client._http`` internals. It also uploads local files via ``POST
/api/file`` (outside the usual ``/api/v3`` prefix), returning a reference
that can be passed straight into an entity's ``attaches``.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any

import httpx

from megaplan_sdk.exceptions import MegaplanError
from megaplan_sdk.resources.base import BaseResource


class AttachmentsResource(BaseResource):
    """Resource for downloading and uploading file attachments."""

    def _attach_path(self, attach: Any) -> str:
        """Extract the download path from a model, dict, or raw string.

        Accepts ``File``/``Attache`` pydantic models (including ``path``
        stored in ``model_extra`` on ``BaseEntity`` references), plain dicts,
        or the path/URL string itself.
        """
        if isinstance(attach, str):
            path = attach
        elif isinstance(attach, dict):
            path = attach.get("path") or attach.get("url")
        else:
            path = getattr(attach, "path", None) or getattr(attach, "url", None)
        if not path or not isinstance(path, str):
            raise ValueError(
                "Attachment has no downloadable 'path'/'url'; pass an attach "
                "model, a dict with 'path', or the path string itself"
            )
        return path

    async def download(self, attach: Any) -> bytes:
        """Download an attachment fully into memory.

        Args:
            attach: Attach model, dict with ``path``/``url``, or path string.

        Returns:
            Raw file bytes.

        Examples:
            >>> data = await client.attachments.download(comment.attaches[0])
            >>> Path("report.pdf").write_bytes(data)
        """
        return await self._http.get_binary(self._attach_path(attach))

    async def upload(self, path: str | Path) -> dict[str, Any]:
        """Upload a file and get a reference to attach to an entity.

        Note:
            The file is read synchronously (``Path.open()``/``handle.read()``
            under the hood of the multipart encoder) — it is not streamed
            off the event loop. For large files this blocks the loop for the
            duration of the read; see ``asyncio.to_thread`` if that matters
            for your workload (not done here — planned for 0.6.2).

        Args:
            path: Local file to upload.

        Returns:
            Reference like ``{"contentType": "File", "id": 9100}`` for ``attaches``.

        Raises:
            MegaplanError: The server returned HTTP 200 with no file data,
                so there is no reference to hand back.
        """
        file_path = Path(path)
        with file_path.open("rb") as handle:
            response = await self._http.post(
                "/api/file", files={"files[]": (file_path.name, handle)}
            )
        data = self._parse_list_response(response)
        if not data:
            raise MegaplanError(
                "Upload of "
                f"{file_path.name!r} returned no file data (empty 'data' in "
                "response); the file was not accepted by the server"
            )
        item = data[0]
        return {"contentType": item["contentType"], "id": int(item["id"])}

    def stream(self, attach: Any) -> AbstractAsyncContextManager[httpx.Response]:
        """Stream an attachment (for large files).

        Examples:
            >>> async with client.attachments.stream(attach) as response:
            ...     async for chunk in response.aiter_bytes():
            ...         f.write(chunk)
        """
        return self._http.stream_binary(self._attach_path(attach))
