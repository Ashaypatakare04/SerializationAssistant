import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from backend.app.services.storage import LocalStorageService, S3StorageService, get_storage_service


def test_local_storage_lifecycle(tmp_path):
    svc = LocalStorageService(base_dir=str(tmp_path))
    test_data = b"Hello, Webtoon Studio Storage!"
    
    # Save bytes
    key, checksum, size = svc.save_bytes("documents", "test_file.txt", test_data)
    assert key == "documents/test_file.txt"
    assert size == len(test_data)
    assert len(checksum) == 64
    
    # Read bytes & text
    read_data = svc.read_bytes(key)
    assert read_data == test_data
    assert svc.read_text(key) == "Hello, Webtoon Studio Storage!"
    
    # Absolute path
    path = svc.get_absolute_path(key)
    assert path.exists()
    assert path.is_file()
    
    # Collision avoidance
    key2, _, _ = svc.save_bytes("documents", "test_file.txt", b"New content")
    assert key2 == "documents/test_file_1.txt"
    assert svc.read_bytes(key2) == b"New content"
    
    # Delete
    assert svc.delete(key) is True
    assert not path.exists()
    assert svc.delete("documents/non_existent.txt") is False


def test_s3_storage_with_mocked_client(tmp_path):
    with patch("boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        
        # Configure mock get_object response
        mock_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"S3 Payload Data")
        }
        mock_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/assets/panel.png?signed=true"

        s3_svc = S3StorageService(
            bucket_name="my-test-bucket",
            region_name="us-west-2",
            cache_dir=str(tmp_path),
        )
        
        # Save bytes
        key, checksum, size = s3_svc.save_bytes("assets", "panel_1.png", b"S3 Payload Data")
        assert key == "assets/panel_1.png"
        assert size == 15
        mock_client.put_object.assert_called_once()
        
        # Presigned URL
        url = s3_svc.generate_presigned_url(key)
        assert url is not None
        assert "signed=true" in url
        
        # Read bytes (from cache)
        cached_data = s3_svc.read_bytes(key)
        assert cached_data == b"S3 Payload Data"
        
        # Delete
        assert s3_svc.delete(key) is True
        mock_client.delete_object.assert_called_once_with(Bucket="my-test-bucket", Key=key)


def test_get_storage_service_factory(monkeypatch):
    from backend.app.core.config import settings
    
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    svc_local = get_storage_service()
    assert isinstance(svc_local, LocalStorageService)
