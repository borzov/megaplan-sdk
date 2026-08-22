"""Tests for AttachmentsResource (#FR-C)."""

import pytest
from httpx import Response

from megaplan_sdk.exceptions import MegaplanError, NotFoundError
from megaplan_sdk.models.base import BaseEntity


async def test_download_accepts_model_with_extra_path(megaplan_api, attachments, base_url):
    """FR-C: an Attache reference (BaseEntity with extra 'path') downloads."""
    route = megaplan_api.get(f"{base_url}/attach/File/1/2/report.pdf")
    route.mock(return_value=Response(200, content=b"%PDF-1.7 data"))

    attach = BaseEntity(**{"contentType": "File", "id": 42, "path": "/attach/File/1/2/report.pdf"})
    data = await attachments.download(attach)

    assert data == b"%PDF-1.7 data"


async def test_download_accepts_dict_and_str(megaplan_api, attachments, base_url):
    """FR-C: dict payloads and raw path strings work too."""
    route = megaplan_api.get(f"{base_url}/attach/File/9/x.png")
    route.mock(return_value=Response(200, content=b"PNG"))

    assert await attachments.download({"path": "/attach/File/9/x.png"}) == b"PNG"
    assert await attachments.download("/attach/File/9/x.png") == b"PNG"
    assert route.call_count == 2


async def test_download_accepts_dict_with_url_fallback(megaplan_api, attachments, base_url):
    """FR-C: dict payloads with 'url' (no 'path') fall back correctly."""
    route = megaplan_api.get(f"{base_url}/attach/File/9/y.png")
    route.mock(return_value=Response(200, content=b"PNG-url"))

    data = await attachments.download({"url": "/attach/File/9/y.png"})

    assert data == b"PNG-url"
    assert route.call_count == 1


async def test_stream_yields_response(megaplan_api, attachments, base_url):
    """FR-C: stream() is an async context manager over the raw response."""
    route = megaplan_api.get(f"{base_url}/attach/big.bin")
    route.mock(return_value=Response(200, content=b"B" * 2048))

    collected = b""
    async with attachments.stream("/attach/big.bin") as response:
        async for chunk in response.aiter_bytes():
            collected += chunk

    assert collected == b"B" * 2048


async def test_download_rejects_attach_without_path(attachments):
    """FR-C: a reference without path/url fails loudly, not with a 404."""
    with pytest.raises(ValueError, match="path"):
        await attachments.download(BaseEntity(**{"contentType": "File", "id": 42}))


async def test_download_maps_http_errors(megaplan_api, attachments, base_url):
    """FR-C: SDK exceptions propagate from the transport layer."""
    route = megaplan_api.get(f"{base_url}/attach/gone.png")
    route.mock(return_value=Response(404, content=b""))

    with pytest.raises(NotFoundError):
        await attachments.download("/attach/gone.png")


async def test_upload_sends_multipart(megaplan_api, attachments, base_url, tmp_path):
    """#FR-D: upload goes to /api/file (no /v3) as multipart files[]."""
    report = tmp_path / "report.pdf"
    report.write_bytes(b"%PDF-1.4 test")
    # MegaplanAPIMock prefixes /api/v3 for relative paths; this route is outside it,
    # so the absolute URL form is used (conftest.py:79-83).
    route = megaplan_api.post(f"{base_url}/api/file", data=[{"contentType": "File", "id": "9100"}])

    ref = await attachments.upload(report)

    assert ref == {"contentType": "File", "id": 9100}
    assert b"report.pdf" in route.calls[0].request.content


async def test_upload_raises_on_empty_data(megaplan_api, attachments, base_url, tmp_path):
    """#BUG: HTTP 200 with an empty 'data' list must raise, not IndexError."""
    report = tmp_path / "report.pdf"
    report.write_bytes(b"%PDF-1.4 test")
    megaplan_api.post(f"{base_url}/api/file", data=[])

    with pytest.raises(MegaplanError, match="no file data"):
        await attachments.upload(report)
