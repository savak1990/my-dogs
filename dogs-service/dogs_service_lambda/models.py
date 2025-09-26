from pydantic import BaseModel, Field
from uuid import UUID

class DogIn(BaseModel):
    name: str
    age: int

class DogOut(BaseModel):
    user_id: UUID
    dog_id: int
    name: str
    age: int

class DogDb(BaseModel):
    PK: str = Field(..., description="Partition Key, format: USER#<user_id>")
    SK: str = Field(..., description="Sort Key, format: DOG#<dog_id>")
    name: str
    age: int
    created_at: str
    updated_at: str
    
    def to_dog_out(self) -> DogOut:
        user_id = UUID(self.PK.split("#")[1])
        dog_id = int(self.SK.split("#")[1])
        return DogOut(
            user_id=user_id,
            dog_id=dog_id,
            name=self.name,
            age=self.age
        )