import abc
import hashlib
import io
import mimetypes
import os
import shutil
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from fastapi import UploadFile
from PIL import Image

from backend.app.core.config import settings
from backend.app.core.security import get_safe_storage_path, validate_safe_filename
import logging

logger = logging.getLogger(__name__)


class BaseStorageService(abc.ABC):
    """Abstract base class for storage adapters."""

    @abc.abstractmethod
    def save_bytes(self, category: str, filename: str, data: bytes) -> Tuple[str, str, int]:
        """Saves raw bytes under category/filename. Returns (rel_key, sha256_checksum, size_bytes)."""
        pass

    async def save_upload(self, category: str, upload: UploadFile) -> Tuple[str, str, int]:
        """Saves an uploaded file. Returns (rel_key, sha256_checksum, size_bytes)."""
        content = await upload.read()
        return self.save_bytes(category, upload.filename or "upload.bin", content)

    @abc.abstractmethod
    def read_bytes(self, rel_key: str) -> bytes:
        """Reads raw bytes for the given storage key."""
        pass

    def read_text(self, rel_key: str) -> str:
        """Reads text content for the given storage key."""
        return self.read_bytes(rel_key).decode("utf-8", errors="replace")

    @abc.abstractmethod
    def get_absolute_path(self, rel_key: str) -> Path:
        """Returns a local file Path for local serving / file operations."""
        pass

    def inspect_image(self, rel_key: str) -> Tuple[int, int, str]:
        """Inspects image dimensions and format."""
        data = self.read_bytes(rel_key)
        with Image.open(io.BytesIO(data)) as img:
            return img.width, img.height, (img.format or "PNG").lower()

    def generate_presigned_url(self, rel_key: str, expires_in: int = 3600) -> Optional[str]:
        """Generates a presigned URL for direct client access if supported."""
        return None

    @abc.abstractmethod
    def delete(self, rel_key: str) -> bool:
        """Deletes an object by key."""
        pass


class LocalStorageService(BaseStorageService):
    """Local filesystem storage implementation with directory separation and collision avoidance."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.STORAGE_LOCAL_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Ensure subdirectories exist
        for subdir in ["documents", "references", "assets", "exports"]:
            (self.base_dir / subdir).mkdir(exist_ok=True)

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

    def get_absolute_path(self, rel_key: str) -> Path:
        return get_safe_storage_path(str(self.base_dir), rel_key)

    def read_bytes(self, rel_key: str) -> bytes:
        path = self.get_absolute_path(rel_key)
        if not path.exists():
            raise FileNotFoundError(f"Storage key {rel_key} not found")
        return path.read_bytes()

    def delete(self, rel_key: str) -> bool:
        path = self.get_absolute_path(rel_key)
        if path.exists():
            path.unlink()
            return True
        return False


class S3StorageService(BaseStorageService):
    """S3-compatible object storage provider with local disk cache and presigned URL support."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region_name: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        cache_dir: Optional[str] = None,
    ):
        import boto3
        from botocore.config import Config

        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME or "studio-assets"
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL or None
        self.region_name = region_name or settings.S3_REGION_NAME or "us-east-1"
        self.access_key_id = access_key_id or settings.S3_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or settings.S3_SECRET_ACCESS_KEY
        
        # Local cache directory for fast reads, PIL inspections, and local streaming
        base = Path(cache_dir or settings.STORAGE_LOCAL_DIR).resolve()
        self.cache_dir = base / "s3_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        boto_kwargs: Dict[str, Any] = {
            "region_name": self.region_name,
            "config": Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
        }
        if self.endpoint_url:
            boto_kwargs["endpoint_url"] = self.endpoint_url
        if self.access_key_id and self.secret_access_key:
            boto_kwargs["aws_access_key_id"] = self.access_key_id
            boto_kwargs["aws_secret_access_key"] = self.secret_access_key

        self.s3_client = boto3.client("s3", **boto_kwargs)
        logger.info(f"Initialized S3StorageService for bucket '{self.bucket_name}' (endpoint: {self.endpoint_url or 'AWS default'})")

    def _get_cache_path(self, rel_key: str) -> Path:
        return get_safe_storage_path(str(self.cache_dir), rel_key)

    def save_bytes(self, category: str, filename: str, data: bytes) -> Tuple[str, str, int]:
        safe_name = validate_safe_filename(filename)
        rel_key = f"{category}/{safe_name}"
        
        # Cache locally
        cache_path = self._get_cache_path(rel_key)
        counter = 1
        stem = cache_path.stem
        suffix = cache_path.suffix
        while cache_path.exists():
            safe_name = f"{stem}_{counter}{suffix}"
            rel_key = f"{category}/{safe_name}"
            cache_path = self._get_cache_path(rel_key)
            counter += 1

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(data)

        # Content type detection
        content_type, _ = mimetypes.guess_type(safe_name)
        content_type = content_type or "application/octet-stream"

        # Upload to S3
        checksum = hashlib.sha256(data).hexdigest()
        file_size = len(data)
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=rel_key,
                Body=data,
                ContentType=content_type,
                Metadata={"sha256": checksum},
            )
        except Exception as e:
            logger.error(f"Failed to upload {rel_key} to S3 bucket {self.bucket_name}: {e}")
            raise

        return rel_key, checksum, file_size

    def read_bytes(self, rel_key: str) -> bytes:
        cache_path = self._get_cache_path(rel_key)
        if cache_path.exists():
            return cache_path.read_bytes()

        # Fetch from S3
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=rel_key)
            data = response["Body"].read()
            # Cache for future reads
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
            return data
        except Exception as e:
            raise FileNotFoundError(f"Key {rel_key} not found in S3 bucket {self.bucket_name}: {e}")

    def get_absolute_path(self, rel_key: str) -> Path:
        cache_path = self._get_cache_path(rel_key)
        if not cache_path.exists():
            # Trigger download to cache
            self.read_bytes(rel_key)
        return cache_path

    def generate_presigned_url(self, rel_key: str, expires_in: int = 3600) -> Optional[str]:
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": rel_key},
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.warning(f"Could not generate presigned URL for {rel_key}: {e}")
            return None

    def delete(self, rel_key: str) -> bool:
        cache_path = self._get_cache_path(rel_key)
        if cache_path.exists():
            cache_path.unlink()

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=rel_key)
            return True
        except Exception as e:
            logger.warning(f"Failed to delete {rel_key} from S3 bucket {self.bucket_name}: {e}")
            return False


def get_storage_service() -> BaseStorageService:
    """Factory to retrieve configured storage service."""
    backend_choice = getattr(settings, "STORAGE_BACKEND", "local").lower()
    if backend_choice == "s3":
        try:
            return S3StorageService()
        except Exception as e:
            logger.warning(f"S3StorageService initialization failed: {e}. Falling back to LocalStorageService.")
            return LocalStorageService()
    return LocalStorageService()


storage_service: BaseStorageService = get_storage_service()
