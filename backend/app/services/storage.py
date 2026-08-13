import os
import hashlib
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger("app.services.storage")

class StorageService:
    def __init__(self, base_dir: str = "storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, content: bytes, relative_path: str) -> Tuple[str, str, int]:
        """
        Saves binary content to the relative storage path.
        Returns tuple of (full_file_path, sha256_checksum, file_size_in_bytes).
        """
        file_path = self.base_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(content)

        checksum = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        logger.info(f"Saved file to storage: {file_path} | Size: {file_size} bytes | SHA256: {checksum[:8]}...")
        return str(file_path), checksum, file_size

    def read_file(self, file_path_str: str) -> bytes:
        """
        Reads binary file from storage.
        """
        path = Path(file_path_str)
        if not path.exists():
            raise FileNotFoundError(f"Storage file not found at path: {file_path_str}")

        with open(path, "rb") as f:
            return f.read()

    def exists(self, file_path_str: str) -> bool:
        """
        Checks if file exists at specified path.
        """
        return Path(file_path_str).exists()

    def delete_file(self, file_path_str: str) -> bool:
        """
        Deletes file if exists.
        """
        path = Path(file_path_str)
        if path.exists():
            path.unlink()
            return True
        return False


storage_service = StorageService()
