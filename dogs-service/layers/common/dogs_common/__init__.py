# dogs_common package
"""
Common utilities and configuration for the Dogs Service Lambda functions.
"""

__version__ = "0.1.0"
__all__ = ["config", "observability", "get_config", "logger", "tracer"]

# Make key components available at package level
from .config import get_config, AppConfig
from .observability import logger, tracer
from .db import get_dogs_db_client, DynamoDBClient
from .s3 import get_s3_client, S3Client
from .models import (
    ImageStatus,
    ImageDb,
    CreateImageRequestPayload,
    ImageUploadInstructions,
    ImageInfo,
    DogDb,
    CreateDogRequestPayload,
    CreateDogResponsePayload,
    DogInfo
)
