
from models import DogIn, DogOut
from typing import List

def handle_user_dogs_get(user_id: str) -> List[DogOut]:
    
    dogs = [
        DogOut(user_id=user_id, name="Buddy", age=5),
        DogOut(user_id=user_id, name="Max", age=3),
    ]

    return [d.model_dump() for d in dogs]

def handle_user_dogs_post(user_id: str, dog: DogIn) -> DogOut:
    dog_out = DogOut(user_id=user_id, name=dog.name, age=dog.age)
    return dog_out