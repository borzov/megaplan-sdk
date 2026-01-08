"""Files resource for Megaplan API."""

from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO

from megaplan_sdk.logging_config import logger
from megaplan_sdk.models.common import File
from megaplan_sdk.resources.base import BaseResource


class FileResource(BaseResource):
    """Resource for file uploads."""

    async def upload(self, file_path: str | Path, filename: str | None = None) -> File:
        """Upload a file from filesystem.

        Automatically uses streaming for large files (>10MB) for better performance.

        Args:
            file_path: Path to file.
            filename: Optional filename override.

        Returns:
            File object with id and contentType.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If path is not a file or filename contains path traversal.
        """
        # Security: Resolve to absolute path to prevent path traversal
        path_obj = Path(file_path).resolve()

        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Security: Ensure it's a file, not a directory
        if not path_obj.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Security: Sanitize filename to prevent path traversal
        # Path.name automatically extracts only the filename without any path components
        file_name = Path(filename or path_obj.name).name

        # Get file size for streaming decision
        file_size = path_obj.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        # Use streaming for files >10MB
        if file_size > 10 * 1024 * 1024:  # 10MB threshold
            logger.info(
                f"Streaming large file: {file_name} ({file_size_mb:.2f} MB)",
                extra={"filename": file_name, "size_bytes": file_size},
            )
            return await self._upload_streaming(path_obj, file_name)
        else:
            logger.debug(
                f"Uploading file: {file_name} ({file_size_mb:.2f} MB)",
                extra={"filename": file_name, "size_bytes": file_size},
            )
            # Small files - load to memory (more efficient for small files)
            with open(path_obj, "rb") as f:
                return await self.upload_bytes(f.read(), file_name)

    async def upload_bytes(self, file_bytes: bytes, filename: str) -> File:
        """Upload file from bytes.

        Args:
            file_bytes: File content as bytes.
            filename: File name.

        Returns:
            File object with id and contentType.
        """
        path = self._build_path("api", "file")

        files = {"file": (filename, file_bytes)}

        response = await self._http.post(path, files=files)
        return File(**response["data"])

    async def upload_file_obj(self, file_obj: BinaryIO, filename: str) -> File:
        """Upload file from file-like object.

        Args:
            file_obj: File-like object (must support read()).
            filename: File name.

        Returns:
            File object with id and contentType.
        """
        file_bytes = file_obj.read()
        return await self.upload_bytes(file_bytes, filename)

    async def _upload_streaming(self, path: Path, filename: str) -> File:
        """Upload file using streaming (for large files).

        Args:
            path: Path to file.
            filename: File name.

        Returns:
            File object with id and contentType.
        """
        api_path = self._build_path("api", "file")

        # Generator function for streaming file in chunks
        def file_generator() -> Iterator[bytes]:
            with open(path, "rb") as f:
                while chunk := f.read(8192):  # 8KB chunks
                    yield chunk

        # Create file tuple with generator
        files = {"file": (filename, file_generator())}

        response = await self._http.post(api_path, files=files)
        return File(**response["data"])
