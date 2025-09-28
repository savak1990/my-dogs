from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, model_serializer
from uuid import UUID
from typing import List, Optional
from enum import Enum
from utils import DATETIME_NOW_UTC_FN

class ImageStatus(str, Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    READY = "ready"
    REJECTED = "rejected"
    FAILED = "failed"
    DELETED = "deleted"

class ImageDb(BaseModel):
    PK: str = Field(..., description="Partition Key, format: USER#<user_id>")
    SK: str = Field(..., description="Sort Key, format: IMAGE#<dog_id>#<image_id>")
    key: Optional[str] = None
    status: ImageStatus = ImageStatus.PENDING
    status_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: DATETIME_NOW_UTC_FN().isoformat())
    updated_at: str = created_at

class CreateImageRequestPayload(BaseModel):
    image_extension: str = Field(..., description="File extension of the image, e.g., jpg, png")

class ImageUploadInstructions(BaseModel):
    image_id: int
    method: str
    presigned_url: str
    expires_in: int
    headers: dict|None = None
    max_size: int|None = None

class ImageInfo(BaseModel):    
    image_id: str
    image_url: Optional[str] = None
    status: ImageStatus
    status_reason: Optional[str] = None

    @model_serializer
    def serialize_model(self):
        data = {
            'image_id': self.image_id,
            'status': self.status.value
        }
        
        # Only include non-None values
        if self.image_url is not None:
            data['image_url'] = self.image_url
        if self.status_reason is not None:
            data['status_reason'] = self.status_reason
            
        return data

    @classmethod
    def create(cls, image_db: ImageDb) -> ImageInfo:
        parts = image_db.SK.split("#")
        image_id = parts[2] if len(parts) > 2 else "0"
        
        return ImageInfo(
            image_id=image_id,
            image_url=None,  # Will be set by service layer after image is uploaded
            status=image_db.status,
            status_reason=image_db.status_reason
        )

class DogDb(BaseModel):
    PK: str = Field(..., description="Partition Key, format: USER#<user_id>")
    SK: str = Field(..., description="Sort Key, format: DOG#<dog_id>")
    name: str
    age: int
    images: List[ImageDb] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: DATETIME_NOW_UTC_FN().isoformat())
    updated_at: str = created_at

class CreateDogRequestPayload(BaseModel):
    name: str
    age: int

class CreateDogResponsePayload(BaseModel):
    user_id: UUID
    dog_id: int
    name: str
    age: int
    
    @classmethod
    def create(cls, dog_db: DogDb) -> CreateDogResponsePayload:
        user_id = UUID(dog_db.PK.split("#")[1])
        dog_id = int(dog_db.SK.split("#")[1])
        return CreateDogResponsePayload(
            user_id=user_id,
            dog_id=dog_id,
            name=dog_db.name,
            age=dog_db.age
        )

class DogInfo(BaseModel):
    dog_id: int
    name: str
    age: int
    images: List[ImageInfo] = Field(default_factory=list)

    @model_serializer
    def serialize_model(self):
        return {
            'dog_id': self.dog_id,
            'name': self.name,
            'age': self.age,
            'images': [image.serialize_model() for image in self.images]
        }
    
    @classmethod
    def create(cls, dog_db: DogDb) -> DogInfo:
        user_id = UUID(dog_db.PK.split("#")[1])
        dog_id = int(dog_db.SK.split("#")[1])
        return DogInfo(
            dog_id=dog_id,
            name=dog_db.name,
            age=dog_db.age,
            images=[ImageInfo.create(image_db) for image_db in dog_db.images]
        )
