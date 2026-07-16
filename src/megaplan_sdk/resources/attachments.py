"""Attachments resource: authorized download of file attachments (#FR-C).

``Comment.attaches`` / ``Task.attaches`` items carry a relative ``path``
(e.g. ``/attach/SdfFileM_File/File/237/81/x.png``) that requires a Bearer
header to fetch. This resource owns that logic so callers never touch
``client._http`` internals.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Any

import httpx

from megaplan_sdk.resources.base import BaseResource


class AttachmentsResource(BaseResource):
    """Resource for downloading file attachments."""

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

    def stream(self, attach: Any) -> AbstractAsyncContextManager[httpx.Response]:
        """Stream an attachment (for large files).

        Examples:
            >>> async with client.attachments.stream(attach) as response:
            ...     async for chunk in response.aiter_bytes():
            ...         f.write(chunk)
        """
        return self._http.stream_binary(self._attach_path(attach))
