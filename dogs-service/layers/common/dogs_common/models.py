from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, model_serializer
from typing import List, Optional
from enum import Enum
from .utils import DATETIME_NOW_UTC_FN

class ImageStatus(str, Enum):
    PENDING = "pending"
    UPLOADED = "uploaded" # Uploaded to S3 successfully, link is available
    DELETED = "deleted" # Explicit deletion, deleted from S3

# Image DB Models
class ImageDb(BaseModel):
    PK: str = Field(..., description="Partition Key, format: USER#<user_id>")
    SK: str = Field(..., description="Sort Key, format: IMAGE#<dog_id>#<image_id>")
    s3_key: Optional[str] = None
    status: ImageStatus = ImageStatus.PENDING
    status_reason: Optional[str] = None
    version: int = Field(default=1)
    created_at: str = Field(default_factory=lambda: DATETIME_NOW_UTC_FN().isoformat())
    updated_at: str = Field(default_factory=lambda: DATETIME_NOW_UTC_FN().isoformat())
    expires_at: Optional[int] = None

# Image API Models
class CreateImageRequestPayload(BaseModel):
    model_config = ConfigDict(frozen=True)
    image_extension: str = Field(..., description="File extension of the image, e.g., jpg, png")

class UpdateImageRequestPayload(BaseModel):
    model_config = ConfigDict(frozen=True)
    s3_key: str
    status: ImageStatus
    status_reason: Optional[str] = None
    clear_ttl: Optional[bool] = Field(default=False, description="If true, clears the expires_at field")

class ImageUploadInstructions(BaseModel):
    model_config = ConfigDict(frozen=True)
    method: str
    presigned_url: str
    expires_in: int
    headers: Optional[dict[str, str]] = None
    max_size: Optional[int] = None

    @model_serializer
    def serialize_model(self) -> dict:
        data = {
            "method": self.method,
            "presigned_url": self.presigned_url,
            "expires_in": self.expires_in,
        }
        if self.headers is not None:
            data["headers"] = self.headers
        if self.max_size is not None:
            data["max_size"] = self.max_size
        return data
    
    @classmethod
    def create(cls, method: str, presigned_url: str, expires_in: int, headers: Optional[dict[str, str]] = None, max_size: Optional[int] = None) -> "ImageUploadInstructions":
        return cls(
            method=method,
            presigned_url=presigned_url,
            expires_in=expires_in,
            headers=headers,
            max_size=max_size
        )

class ImageInfo(BaseModel):    
    image_id: str
    image_url: Optional[str] = None
    status: ImageStatus
    status_reason: Optional[str] = None
    version: int = Field(default=1)
    created_at: str = Field(default_factory=lambda: DATETIME_NOW_UTC_FN().isoformat())
    updated_at: str = Field(default_factory=lambda: DATETIME_NOW_UTC_FN().isoformat())

    @model_serializer
    def serialize_model(self) -> dict:
        data = {
            "image_id": self.image_id,
            "status": self.status.value,
            "image_url": self.image_url,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.image_url is not None:
            data["image_url"] = self.image_url
        if self.status_reason is not None:
            data["status_reason"] = self.status_reason
        return data

    @classmethod
    def create(cls, image_db: ImageDb) -> "ImageInfo":
        parts = image_db.SK.split("#")
        image_id = parts[2] if len(parts) > 2 else "0"
        return cls(
            image_id=image_id,
            image_url=f"s3://{image_db.s3_key}" if image_db.s3_key else None,
            status=image_db.status,
            status_reason=image_db.status_reason,
            version=image_db.version,
            created_at=image_db.created_at,
            updated_at=image_db.updated_at,
        )

class CreateImageResponsePayload(BaseModel):
    image: ImageInfo
    upload_instructions: ImageUploadInstructions
    
    @model_serializer
    def serialize_model(self) -> dict:
        return {
            "image": self.image.serialize_model(),
            "upload_instructions": self.upload_instructions.serialize_model()
        }
    
    @classmethod
    def create(cls, image_db: ImageDb, upload_instructions: ImageUploadInstructions) -> "CreateImageResponsePayload":
        return cls(
            image=ImageInfo.create(image_db),
            upload_instructions=upload_instructions
        )

# Dogs DB Models
class DogDb(BaseModel):
    PK: str = Field(..., description="Partition Key, format: USER#<user_id>")
    SK: str = Field(..., description="Sort Key, format: DOG#<dog_id>")
    name: str
    age: int
    images: List[ImageDb] = Field(default_factory=list)
    version: int = Field(default=1)
    created_at: str = Field(default_factory=lambda: DATETIME_NOW_UTC_FN().isoformat())
    updated_at: str = Field(default_factory=lambda: DATETIME_NOW_UTC_FN().isoformat())

# Dogs API Models
class BaseDogFields(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    age: int

class BaseDogRequestPayload(BaseDogFields):
    model_config = ConfigDict(extra="forbid")
    pass

class CreateDogRequestPayload(BaseDogRequestPayload):
    pass

class UpdateDogRequestPayload(BaseDogRequestPayload):
    pass

class BaseDogResponsePayload(BaseDogFields):
    dog_id: int
    images: tuple[ImageInfo, ...] = Field(default_factory=tuple)
    version: int
    created_at: str
    updated_at: str
    
    @model_serializer
    def serialize_model(self) -> dict:
        return {
            'dog_id': self.dog_id,
            'name': self.name,
            'age': self.age,
            'images': [image.serialize_model() for image in self.images],
            'version': self.version,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def create(cls, dog_db: DogDb) -> "BaseDogResponsePayload":
        dog_id = int(dog_db.SK.split("#")[1])
        return cls(
            dog_id=dog_id,
            name=dog_db.name,
            age=dog_db.age,
            images=tuple(ImageInfo.create(image_db) for image_db in dog_db.images),
            version=dog_db.version,
            created_at=dog_db.created_at,
            updated_at=dog_db.updated_at
        )

class CreateDogResponsePayload(BaseDogResponsePayload):
    pass

class UpdateDogResponsePayload(BaseDogResponsePayload):
    pass

class GetDogResponsePayload(BaseDogResponsePayload):
    pass
