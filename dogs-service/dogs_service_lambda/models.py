from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
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
    model_config = ConfigDict(exclude_none=True)
    
    image_id: str
    image_url: Optional[str] = None
    status: ImageStatus
    status_reason: Optional[str] = None

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
    model_config = ConfigDict(exclude_none=True)
    
    dog_id: int
    name: str
    age: int
    images: List[ImageInfo] = Field(default_factory=list)
    
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
