import os
import handlers
import utils

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler.api_gateway import APIGatewayHttpResolver
from aws_lambda_powertools.utilities.parser import event_parser, parse
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser.models import APIGatewayProxyEventModel
from pydantic import ValidationError

from dataclasses import dataclass
from models import Context
from typing import Callable

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logger = Logger(service="dogs-service", level=LOG_LEVEL)

@dataclass
class Operation:
    id: str
    handler: Callable

OPERATION_MAP = {
    "GET /users/{user_id}/dogs": Operation("userDogsGet", handlers.handle_user_dogs_get),
    "POST /users/{user_id}/dogs": Operation("userDogsPost", handlers.handle_user_dogs_post),
}

def handle_event(event, context: LambdaContext):
    operation_id = "unknown"
    response_holder: any
    try:
        request = parse(event, model=APIGatewayProxyEventModel)
        request_sig = f"{request.http_method} {request.resource}"
        operation = OPERATION_MAP.get(request_sig)
        if operation is None:
            response_holder = utils.build_bad_request_error(
                context, f"Unknown operation: {request_sig}")
        else:
            operation_id = operation.id
            response_holder = operation.handler(context, request)
    except ValidationError as ve:
        logger.warning(
            "Validation error", 
            extra={"event": request, "operation_id": operation_id},
            exc_info=ve, 
            stack_info=True)
        response_holder = utils.build_bad_request_error(context, "Invalid request format")
    except Exception as e:
        logger.exception("Error handling event", extra={"event": request, "operation_id": operation_id}, stack_info=True)
        response_holder = utils.build_unexpected_error(
            context, 
            "An unexpected error occurred",
            exc_info=ve,
            stack_info=True)
    return operation_id, response_holder

def lambda_handler(event, context):
    logger.debug("handler invoked", extra={"event_present": bool(event)})

    start_time = utils.DATETIME_NOW_UTC_FN()
    context = Context(context, start_time)
    operation_id, response_holder = handle_event(event, context)
    response = utils.build_response(response_holder)
    dur_ms = int((utils.DATETIME_NOW_UTC_FN() - start_time).total_seconds() * 1000)

    logger.debug("handler completed", extra={"event_present": bool(event)})

    return response
