import hashlib
import os
import shutil
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile
from PIL import Image
from backend.app.core.config import settings
from backend.app.core.security import get_safe_storage_path, validate_safe_filename

class LocalStorageService:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.STORAGE_LOCAL_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Subdirectories
        (self.base_dir / "documents").mkdir(exist_ok=True)
        (self.base_dir / "references").mkdir(exist_ok=True)
        (self.base_dir / "assets").mkdir(exist_ok=True)
        (self.base_dir / "exports").mkdir(exist_ok=True)

    def save_bytes(self, category: str, filename: str, data: bytes) -> Tuple[str, str, int]:
        safe_name = validate_safe_filename(filename)
        rel_key = f"{category}/{safe_name}"
        abs_path = get_safe_storage_path(str(self.base_dir), rel_key)
        
        # Avoid collisions by appending counter if needed
        counter = 1
        stem = abs_path.stem
        suffix = abs_path.suffix
        while abs_path.exists():
            safe_name = f"{stem}_{counter}{suffix}"
            rel_key = f"{category}/{safe_name}"
            abs_path = get_safe_storage_path(str(self.base_dir), rel_key)
            counter += 1

        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(data)
        
        checksum = hashlib.sha256(data).hexdigest()
        file_size = len(data)
        return rel_key, checksum, file_size

    async def save_upload(self, category: str, upload: UploadFile) -> Tuple[str, str, int]:
        content = await upload.read()
        return self.save_bytes(category, upload.filename or "upload.bin", content)

    def get_absolute_path(self, rel_key: str) -> Path:
        return get_safe_storage_path(str(self.base_dir), rel_key)

    def read_bytes(self, rel_key: str) -> bytes:
        path = self.get_absolute_path(rel_key)
        if not path.exists():
            raise FileNotFoundError(f"Storage key {rel_key} not found")
        return path.read_bytes()

    def read_text(self, rel_key: str) -> str:
        return self.read_bytes(rel_key).decode("utf-8", errors="replace")

    def inspect_image(self, rel_key: str) -> Tuple[int, int, str]:
        path = self.get_absolute_path(rel_key)
        with Image.open(path) as img:
            return img.width, img.height, (img.format or "PNG").lower()

storage_service = LocalStorageService()
