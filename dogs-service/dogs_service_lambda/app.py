import os
import handlers

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.openapi.params import Path
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from datetime import datetime, timezone
from models import DogIn, DogOut
from typing import List
from typing_extensions import Annotated
from uuid import UUID

DATETIME_NOW_UTC_FN = lambda: datetime.now(timezone.utc)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

tracer = Tracer(service="dogs-service")
logger = Logger(service="dogs-service", level=LOG_LEVEL)
app = APIGatewayRestResolver(enable_validation=True, debug=True)

@app.get("/users/<user_id>/dogs")
@tracer.capture_method
def get_user_dogs(user_id: Annotated[UUID, Path(description="user id as UUID")]) -> List[DogOut]:
    return handlers.handle_user_dogs_get(user_id)

@app.post("/users/<user_id>/dogs")
@tracer.capture_method
def create_user_dog(user_id: Annotated[UUID, Path(description="user id as UUID")], body: DogIn) -> DogOut:
    return handlers.handle_user_dogs_post(user_id, body)

@app.get("/health")
@tracer.capture_method
def health_check():
    return {"status": "healthy"}

@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.debug(f"Start Lambda Handler with event: {event}")
    return app.resolve(event, context)
