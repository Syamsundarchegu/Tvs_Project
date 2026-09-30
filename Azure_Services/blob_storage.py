"""Azure Blob Storage helpers for opening private source documents with short-lived SAS URLs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlparse

from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas

import config


def _connection_string_parts(connection_string: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for item in connection_string.split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        parts[key] = value
    return parts


def _storage_credentials() -> tuple[str, str, BlobServiceClient]:
    connection_string = getattr(config, "AZURE_STORAGE_CONNECTION_STRING", "")
    account_name = getattr(config, "AZURE_STORAGE_ACCOUNT_NAME", "")
    account_key = getattr(config, "AZURE_STORAGE_ACCOUNT_KEY", "")

    if connection_string:
        parts = _connection_string_parts(connection_string)
        account_name = account_name or parts.get("AccountName", "")
        account_key = account_key or parts.get("AccountKey", "")
        if not account_name or not account_key:
            raise RuntimeError("Storage connection string must contain AccountName and AccountKey")
        return account_name, account_key, BlobServiceClient.from_connection_string(connection_string)

    if not account_name or not account_key:
        raise RuntimeError(
            "Set AZURE_STORAGE_CONNECTION_STRING or both AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY"
        )

    return account_name, account_key, BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=account_key,
    )


def normalize_blob_path(blob_path: str) -> str:
    """Normalize an AI Search current_path into a blob name."""
    path = unquote((blob_path or "").strip()).replace("\\", "/")
    if not path:
        raise ValueError("Blob path is empty")

    # Support metadata that stores a complete blob URL.
    if path.startswith("http://") or path.startswith("https://"):
        parsed = urlparse(path)
        path = parsed.path.lstrip("/")

    path = path.lstrip("/")
    container = getattr(config, "AZURE_STORAGE_CONTAINER_NAME", "").strip("/")
    if container and path.startswith(container + "/"):
        path = path[len(container) + 1 :]

    if any(part == ".." for part in path.split("/")):
        raise ValueError("Invalid blob path")

    return path


def create_blob_read_url(blob_path: str, expiry_minutes: int = 10) -> str:
    container = getattr(config, "AZURE_STORAGE_CONTAINER_NAME", "").strip("/")
    if not container:
        raise RuntimeError("AZURE_STORAGE_CONTAINER_NAME is not configured")

    blob_name = normalize_blob_path(blob_path)
    account_name, account_key, service = _storage_credentials()
    blob_client = service.get_blob_client(container=container, blob=blob_name)

    if not blob_client.exists():
        raise FileNotFoundError(f"Blob not found: {blob_name}")

    expiry = datetime.now(timezone.utc) + timedelta(minutes=max(1, min(expiry_minutes, 30)))
    sas = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry,
    )
    return f"{blob_client.url}?{sas}"
