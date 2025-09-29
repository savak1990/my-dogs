from typing import Optional
from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

class AppConfig(BaseSettings):

    # Service configuration
    powertools_service_name: str = "dogs_service"
    log_level: str = "INFO"

    # Database configuration
    dogs_table_name: str
    dynamodb_endpoint: Optional[str] = None

    # S3 configuration
    dogs_images_bucket: str
    s3_endpoint: Optional[str] = None
    s3_presign_endpoint: Optional[str] = None

    # Upload configuration
    image_upload_expiration_secs: int = Field(default=3600)
    image_upload_max_size: int = Field(default=5 * 1024 * 1024)
    supported_image_extensions: str = Field(default=['jpg', 'jpeg', 'png', 'webp'])

    model_config = {"case_sensitive": False}

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        return v.upper()
    
    @field_validator("dynamodb_endpoint")
    @classmethod
    def set_dynamodb_endpoint(cls, v, info):
        return None if v == "" else v
    
    @field_validator("s3_endpoint")
    @classmethod
    def set_s3_endpoint(cls, v, info):
        return None if v == "" else v

    @field_validator("s3_presign_endpoint")
    @classmethod
    def set_presign_endpoint(cls, v, info):
        if v is None and info.data:
            return info.data.get("s3_endpoint")
        return v

    @field_validator("dogs_table_name")
    @classmethod
    def validate_dogs_table_name(cls, v):
        if not v or not v.strip():
            raise ValueError("DOGS_TABLE_NAME environment variable must not be empty")
        return v.strip()

    @field_validator("dogs_images_bucket")
    @classmethod
    def validate_dogs_images_bucket(cls, v):
        if not v or not v.strip():
            raise ValueError("DOGS_IMAGES_BUCKET environment variable must not be empty")
        return v.strip()

    def __str__(self):
        dump = self.model_dump()
        dump['level'] = self.log_level
        dump['message'] = 'config'
        return str(dump)
    
    def maybe_print(self):
        if self.log_level.upper() in ["DEBUG", "INFO"]:
            print(self)

@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    config = AppConfig()
    config.maybe_print()
    return config