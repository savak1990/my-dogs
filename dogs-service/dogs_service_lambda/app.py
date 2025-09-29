import exception_handlers as eh

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response
from aws_lambda_powertools.event_handler.openapi.exceptions import RequestValidationError
from aws_lambda_powertools.event_handler.openapi.params import Path
from aws_lambda_powertools.event_handler.exceptions import ServiceError
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from botocore.exceptions import ClientError, BotoCoreError
from dogs_common import get_config, logger, tracer
from handlers import DogsService, HealthService
from models import CreateDogResponsePayload, CreateDogRequestPayload, DogInfo, CreateImageRequestPayload, ImageUploadInstructions
from typing import List
from typing_extensions import Annotated
from uuid import UUID

app_config = get_config()

app = APIGatewayRestResolver(enable_validation=True)

dogs_service = None
health_service = None

def get_dogs_service() -> DogsService:
    global dogs_service
    if dogs_service is None:
        dogs_service = DogsService(app_config=app_config)
    return dogs_service

def get_health_service() -> HealthService:
    global health_service
    if health_service is None:
        dogs_service = get_dogs_service()
        health_service = HealthService(
            dogs_service=dogs_service, 
            app_config=app_config)
    return health_service

@app.get("/users/<user_id>/dogs")
@tracer.capture_method
def get_user_dogs(user_id: Annotated[UUID, Path(description="user id as UUID")]) -> List[DogInfo]:
    serv = get_dogs_service()
    dogs = serv.handle_user_dogs_get(str(user_id))
    return dogs

@app.post("/users/<user_id>/dogs", responses={201: {"model": CreateDogResponsePayload}})
@tracer.capture_method
def create_user_dog(user_id: Annotated[UUID, Path(description="user id as UUID")], body: CreateDogRequestPayload) -> CreateDogResponsePayload:
    serv = get_dogs_service()
    created_dog = serv.handle_user_dogs_post(str(user_id), body)
    return created_dog

@app.post("/users/<user_id>/dogs/<dog_id>/images", responses={201: {"model": ImageUploadInstructions}})
@tracer.capture_method
def create_dog_image_placeholder(
    user_id: Annotated[UUID, Path(description="user id as UUID")],
    dog_id: Annotated[int, Path(description="dog id as integer")],
    body: CreateImageRequestPayload
) -> ImageUploadInstructions:
    serv = get_dogs_service()
    image_upload_instructions = serv.handle_create_dog_image_upload(str(user_id), dog_id, body)
    return image_upload_instructions

@app.get("/health")
@tracer.capture_method
def health_check():
    health_service = get_health_service()
    health_status = health_service.get_health_status()
    
    if health_status["status"] == "unhealthy":
        return Response(
            status_code=503,
            content_type="application/json",
            body=health_status
        )
    return health_status

app.exception_handler(ClientError)(eh.handle_boto_client_error)
app.exception_handler(BotoCoreError)(eh.handle_boto_core_error)
app.exception_handler(ServiceError)(eh.handle_service_error)
app.exception_handler(ValueError)(eh.handle_value_error)
app.exception_handler(RequestValidationError)(eh.handle_request_validation_error)
app.exception_handler(Exception)(eh.handle_generic_error)

@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
