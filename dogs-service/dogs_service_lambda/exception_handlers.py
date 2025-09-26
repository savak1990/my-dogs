import logging

from aws_lambda_powertools.event_handler import Response
from aws_lambda_powertools.event_handler.openapi.exceptions import RequestValidationError
from botocore.exceptions import ClientError, BotoCoreError
from aws_lambda_powertools.event_handler.exceptions import ServiceError

logger = logging.getLogger("dogs_service")

def handle_boto_client_error(e: ClientError) -> Response:
    logger.exception("ClientError: %s", e)
    return Response(status_code=503, content_type="application/json", body={"message": str(e)})

def handle_boto_core_error(e: BotoCoreError) -> Response:
    logger.exception("BotoCoreError: %s", e)
    return Response(status_code=503, content_type="application/json", body={"message": str(e)})

def handle_service_error(e: ServiceError) -> Response:
    logger.exception("ServiceError: %s", e)
    return Response(status_code=503, content_type="application/json", body={
        "error": "Service Unavailable",
        "message": str(e),
        "details": "Database connection or operation failed"
    })

def handle_request_validation_error(e: RequestValidationError) -> Response:
    logger.exception("RequestValidationError: %s", e)
    return Response(status_code=400, content_type="application/json", body={"message": str(e)})

def handle_value_error(e: ValueError) -> Response:
    logger.exception("ValueError: %s", e)
    return Response(status_code=400, content_type="application/json", body={"message": str(e)})

def handle_generic_error(e: Exception) -> Response:
    logger.exception("Unhandled exception: %s", e)
    return Response(status_code=500, content_type="application/json", body={
        "error": "Internal Server Error",
        "message": "An unexpected error occurred"
    })
