import uuid

from aws_lambda_powertools.utilities.typing import LambdaContext
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

@dataclass
class Context:
    lambda_context: LambdaContext = None
    request_start_time: datetime = None

@dataclass
class ResponseHolder:
    status_code: int
    headers: dict[str, str]
    response: any = None

@dataclass
class SuccessfulResponseHolder(ResponseHolder):
    status_code: int = 200
    headers: dict[str, str] = None
    response: any = None

@dataclass
class ErrorHolder(ResponseHolder):
    def get_code(self) -> int:
        return self.response.code
    
    def get_message(self) -> str:
        return self.response.message

class ErrorCode(str, Enum):
    BAD_REQUEST = "badRequest"
    UNEXPECTED_ERROR = "unexpectedError"

@dataclass
class Error:
    code: ErrorCode
    message: str

class DogIn(BaseModel):
    name: str
    age: int

class DogOut(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    age: int