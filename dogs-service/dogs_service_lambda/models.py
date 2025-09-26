from __future__ import annotations

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional

class DogDb(BaseModel):
    PK: str = Field(..., description="Partition Key, format: USER#<user_id>")
    SK: str = Field(..., description="Sort Key, format: DOG#<dog_id>")
    name: str
    age: int
    created_at: str
    updated_at: str

class UploadInfo(BaseModel):
    upload_id: int
    method: str
    presigned_url: str
    expires_in: Optional[int] = None
    headers: Optional[dict] = None
    max_size: Optional[int] = None

class CreateDogRequestPayload(BaseModel):
    name: str
    age: int

class CreateDogResponsePayload(BaseModel):
    user_id: UUID
    dog_id: int
    name: str
    age: int
    upload_info: UploadInfo
    
    @classmethod
    def create(dog_db: DogDb, upload_info: UploadInfo) -> CreateDogResponsePayload:
        user_id = UUID(dog_db.PK.split("#")[1])
        dog_id = int(dog_db.SK.split("#")[1])
        return CreateDogResponsePayload(
            user_id=user_id,
            dog_id=dog_id,
            name=dog_db.name,
            age=dog_db.age,
            upload_info=upload_info
        )

class DogInfo(BaseModel):
    user_id: UUID
    dog_id: int
    name: str
    age: int
    
    @classmethod
    def create(dog_db: DogDb) -> DogInfo:
        user_id = UUID(dog_db.PK.split("#")[1])
        dog_id = int(dog_db.SK.split("#")[1])
        return DogInfo(
            user_id=user_id,
            dog_id=dog_id,
            name=dog_db.name,
            age=dog_db.age
        )
