import re

from functools import lru_cache

from pydantic import BaseModel
from dogs_common.models import ImageStatus, UpdateImageRequestPayload
from dogs_common.observability import logger, tracer
from dogs_common.config import AppConfig
from dogs_common.db import get_dogs_db_client
from dogs_common.s3 import get_s3_client
from aws_lambda_powertools.utilities.data_classes.s3_event import S3EventRecord

class Ids(BaseModel):
    user_id: str
    dog_id: int
    image_id: int
    extension: str

class DogsImageProcessor:
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config
        self.s3 = get_s3_client(app_config=app_config)
        self.db = get_dogs_db_client(app_config=app_config)
    
    @tracer.capture_method
    def process_record(self, record: S3EventRecord) -> dict:
        bucket_name = record.s3.bucket.name
        object_key = record.s3.get_object.key
        size = record.s3.get_object.size
        logger.info(f"Processing S3 object from bucket", bucket=bucket_name, key=object_key, size=size)
        
        if size > self.app_config.image_upload_max_size:
            return self._image_rejected(bucket_name, object_key, reason=f"File size exceeds limit: {size}/{self.app_config.image_upload_max_size}")
        
        return self._image_uploaded(bucket_name, object_key)
    
    def _image_rejected(self, bucket_name: str, object_key: str, reason: str) -> dict:
        logger.info(f"Image rejected", bucket=bucket_name, key=object_key)
        ids = self._parse_s3_key(object_key)
        if not ids:
            self.s3.delete_object(s3_key=object_key)
            return {"bucket": bucket_name, "key": object_key, "status": ImageStatus.DELETED, "reason": "Failed to parse S3 key"}
        self.s3.delete_object(s3_key=object_key)
        update_payload = UpdateImageRequestPayload(
            s3_key=object_key,
            status=ImageStatus.DELETED, 
            status_reason=reason)
        self.db.update_image(ids.user_id, ids.dog_id, ids.image_id, update_payload)
        return {"bucket": bucket_name, "key": object_key, "status": ImageStatus.DELETED, "reason": reason}

    def _image_uploaded(self, bucket_name: str, object_key: str):
        logger.info(f"Image uploaded", bucket=bucket_name, key=object_key)
        ids = self._parse_s3_key(object_key)
        if not ids:
            self.s3.delete_object(s3_key=object_key)
            return {"bucket": bucket_name, "key": object_key, "status": ImageStatus.DELETED, "reason": "Failed to parse S3 key"}
        update_payload = UpdateImageRequestPayload(
            s3_key=object_key,
            status=ImageStatus.UPLOADED,
            clear_ttl=True)
        self.db.update_image(ids.user_id, ids.dog_id, ids.image_id, update_payload)
        return {"bucket": bucket_name, "key": object_key, "status": ImageStatus.UPLOADED}

    def _parse_s3_key(self, s3_key: str) -> Ids:
        # Expected format: users/{user_id}/dogs/{dog_id}/images/{image_id}.{extension}
        # TODO This is bad: Need to pass them in presigned url metadata headers instead
        # e.g., x-amz-meta-user-id, x-amz-meta-dog-id, x-amz-meta-image-id, but for this
        # we need to migrate to POST /images/upload endpoint that generates presigned URL
        # because enforcing clients to pass metadata is allowed only with POST presigned URLs
        # with conditions
        if not s3_key:
            return None
        
        pattern = re.compile(r"^users/(?P<user_id>[^/]+)/dogs/(?P<dog_id>\d+)/images/(?P<image_id>\d+)\.(?P<extension>[^.]+)$")
        match = pattern.match(s3_key)
        if not match:
            return None
        try:
            user_id = match.group("user_id")
            dog_id = int(match.group("dog_id"))
            image_id = int(match.group("image_id"))
            extension = match.group("extension")
        except Exception:
            logger.exception(f"Error parsing S3 key: {s3_key}")
            return None
        return Ids(user_id=user_id, dog_id=dog_id, image_id=image_id, extension=extension)

@lru_cache(maxsize=1)
def get_processor(app_config: AppConfig) -> DogsImageProcessor:
    return DogsImageProcessor(app_config=app_config)