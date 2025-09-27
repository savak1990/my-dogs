import os
import json
import exception_handlers as eh

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response
from aws_lambda_powertools.event_handler.openapi.exceptions import RequestValidationError
from aws_lambda_powertools.event_handler.openapi.params import Path
from aws_lambda_powertools.event_handler.exceptions import ServiceError
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_xray_sdk.core import patch_all

from botocore.exceptions import ClientError, BotoCoreError
from db import DynamoDBClient
from handlers import DogsService, HealthService
from models import CreateDogResponsePayload, CreateDogRequestPayload, DogInfo, CreateImageRequestPayload, ImageUploadInstructions
from typing import List
from typing_extensions import Annotated
from s3 import S3Client
from uuid import UUID

POWERTOOLS_SERVICE_NAME = os.environ.get("POWERTOOLS_SERVICE_NAME", "dogs_service")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
DOGS_TABLE_NAME = os.environ.get("DOGS_TABLE_NAME")
DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT") or None
DOGS_IMAGES_BUCKET = os.environ.get("DOGS_IMAGES_BUCKET")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT") or None
S3_PRESIGN_ENDPOINT = os.environ.get("S3_PRESIGN_ENDPOINT") or S3_ENDPOINT

patch_all()
tracer = Tracer()
logger = Logger(level=LOG_LEVEL)
app = APIGatewayRestResolver(enable_validation=True, debug=True)

if not DOGS_TABLE_NAME:
    raise ValueError("DOGS_TABLE_NAME environment variable is not set")

if not DOGS_IMAGES_BUCKET:
    raise ValueError("DOGS_IMAGES_BUCKET environment variable is not set")

logger.info("All environment variables: %s", json.dumps(dict(os.environ)))

dogs_service = None
health_service = None

def get_dogs_service() -> DogsService:
    global dogs_service
    if dogs_service is None:
        dogs_db = DynamoDBClient(
            table_name=DOGS_TABLE_NAME,
            endpoint_url=DYNAMODB_ENDPOINT)
        dogs_s3 = S3Client(
            bucket_name=DOGS_IMAGES_BUCKET,
            endpoint_url=S3_ENDPOINT,
            presign_endpoint=S3_PRESIGN_ENDPOINT)
        dogs_service = DogsService(db=dogs_db, s3=dogs_s3)
    return dogs_service

def get_health_service() -> HealthService:
    global health_service
    if health_service is None:
        dogs_service = get_dogs_service()
        health_service = HealthService(dogs_service=dogs_service, service_name=POWERTOOLS_SERVICE_NAME)
    return health_service

@app.get("/users/<user_id>/dogs")
@tracer.capture_method
def get_user_dogs(user_id: Annotated[UUID, Path(description="user id as UUID")]) -> List[DogInfo]:
    serv = get_dogs_service()
    return serv.handle_user_dogs_get(str(user_id))

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
