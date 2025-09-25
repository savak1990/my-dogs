from pydantic import BaseModel, Field
from uuid import UUID

class DogIn(BaseModel):
    name: str
    age: int

class DogOut(BaseModel):
    id: UUID = Field(default_factory=UUID)
    user_id: UUID
    name: str
    age: int
