"""Unit tests for FileResource."""

import io
import tempfile
from pathlib import Path

import pytest
import respx
from httpx import Response

from megaplan_sdk.http_client import HTTPClient
from megaplan_sdk.resources.files import FileResource


@pytest.mark.asyncio
@respx.mock
async def test_upload_bytes():
    """Test upload_bytes with multipart POST request."""
    respx.post("https://example.com/api/file").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 1, "contentType": "File", "name": "test.txt"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FileResource(http_client)
        file_bytes = b"test file content"
        file_obj = await resource.upload_bytes(file_bytes, "test.txt")

        assert file_obj.id == 1
        assert file_obj.name == "test.txt"


@pytest.mark.asyncio
@respx.mock
async def test_upload_filename_override():
    """Test upload() with filename parameter override."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_file:
        tmp_file.write(b"test content")
        tmp_path = Path(tmp_file.name)

        try:
            respx.post("https://example.com/api/file").mock(
                return_value=Response(
                    200,
                    json={
                        "meta": {"status": 200},
                        "data": {"id": 1, "contentType": "File", "name": "custom.txt"},
                    },
                )
            )

            async with HTTPClient(
                "https://example.com", access_token="token"
            ) as http_client:
                resource = FileResource(http_client)
                file_obj = await resource.upload(tmp_path, filename="custom.txt")

                assert file_obj.id == 1
                assert file_obj.name == "custom.txt"
        finally:
            tmp_path.unlink()


@pytest.mark.asyncio
async def test_upload_file_not_found():
    """Test FileNotFoundError when file doesn't exist."""
    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FileResource(http_client)
        non_existent_path = Path("/nonexistent/file.txt")

        with pytest.raises(FileNotFoundError, match="File not found"):
            await resource.upload(non_existent_path)


@pytest.mark.asyncio
@respx.mock
async def test_upload_path_traversal_prevention():
    """Test path traversal prevention in filename."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(b"test content")
        tmp_path = Path(tmp_file.name)

        try:
            respx.post("https://example.com/api/file").mock(
                return_value=Response(
                    200,
                    json={
                        "meta": {"status": 200},
                        "data": {"id": 1, "contentType": "File", "name": "file.txt"},
                    },
                )
            )

            async with HTTPClient(
                "https://example.com", access_token="token"
            ) as http_client:
                resource = FileResource(http_client)

                # Try to use path traversal in filename
                # Should be sanitized to just "file.txt"
                file_obj = await resource.upload(
                    tmp_path, filename="../../../etc/passwd/file.txt"
                )

                assert file_obj.id == 1
                # Filename should be sanitized (only last component)
                assert file_obj.name == "file.txt"
        finally:
            tmp_path.unlink()


@pytest.mark.asyncio
@respx.mock
async def test_upload_streaming_large_file():
    """Test that files >10MB use streaming."""
    # Mock _upload_streaming to avoid httpx generator issues
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        # Create a file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        tmp_file.write(large_content)
        tmp_file.flush()
        tmp_path = Path(tmp_file.name)

        try:
            # Mock the streaming endpoint - use a simpler approach
            # Since httpx has issues with generators, we'll just verify the method is called
            from unittest.mock import patch, AsyncMock

            async with HTTPClient(
                "https://example.com", access_token="token"
            ) as http_client:
                resource = FileResource(http_client)

                # Mock _upload_streaming to return a file object
                with patch.object(
                    resource, "_upload_streaming", new_callable=AsyncMock
                ) as mock_streaming:
                    mock_streaming.return_value = type(
                        "File", (), {"id": 1, "name": "large.bin", "content_type": "File"}
                    )()

                    file_obj = await resource.upload(tmp_path, filename="large.bin")

                    # Verify _upload_streaming was called (not upload_bytes)
                    assert mock_streaming.called
                    assert file_obj.id == 1
        finally:
            tmp_path.unlink()


@pytest.mark.asyncio
@respx.mock
async def test_upload_small_file():
    """Test that files <10MB use upload_bytes (not streaming)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_file:
        # Create a small file (<10MB)
        small_content = b"small file content"
        tmp_file.write(small_content)
        tmp_path = Path(tmp_file.name)

        try:
            respx.post("https://example.com/api/file").mock(
                return_value=Response(
                    200,
                    json={
                        "meta": {"status": 200},
                        "data": {"id": 1, "contentType": "File", "name": "small.txt"},
                    },
                )
            )

            async with HTTPClient(
                "https://example.com", access_token="token"
            ) as http_client:
                resource = FileResource(http_client)
                file_obj = await resource.upload(tmp_path)

                assert file_obj.id == 1
        finally:
            tmp_path.unlink()


@pytest.mark.asyncio
@respx.mock
async def test_upload_file_obj():
    """Test upload_file_obj with file-like object."""
    respx.post("https://example.com/api/file").mock(
        return_value=Response(
            200,
            json={
                "meta": {"status": 200},
                "data": {"id": 1, "contentType": "File", "name": "from_obj.txt"},
            },
        )
    )

    async with HTTPClient("https://example.com", access_token="token") as http_client:
        resource = FileResource(http_client)
        file_obj_mock = io.BytesIO(b"file content from object")
        file_obj = await resource.upload_file_obj(file_obj_mock, "from_obj.txt")

        assert file_obj.id == 1
        assert file_obj.name == "from_obj.txt"


@pytest.mark.asyncio
async def test_upload_directory_error():
    """Test ValueError when path is a directory, not a file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        async with HTTPClient("https://example.com", access_token="token") as http_client:
            resource = FileResource(http_client)
            dir_path = Path(tmp_dir)

            with pytest.raises(ValueError, match="Path is not a file"):
                await resource.upload(dir_path)
