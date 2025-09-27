import os

from datetime import datetime, timezone

DATETIME_NOW_UTC_FN = lambda: datetime.now(timezone.utc)

def supported_image_extensions() -> set:
    """Return a set of supported image file extensions."""
    return {'jpg', 'jpeg', 'png', 'gif', 'webp'}

def get_content_type_from_extension(extension: str) -> str:
    """Map file extension to MIME type."""
    content_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg', 
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    return content_types.get(extension.lower(), 'application/octet-stream')

def is_running_local() -> bool:
    return os.getenv("AWS_SAM_LOCAL") == "true" or os.getenv("LOCALSTACK_HOSTNAME") is not None