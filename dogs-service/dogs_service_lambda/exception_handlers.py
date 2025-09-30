from aws_lambda_powertools.event_handler import Response
from aws_lambda_powertools.event_handler.openapi.exceptions import RequestValidationError
from botocore.exceptions import ClientError, BotoCoreError
from aws_lambda_powertools.event_handler.exceptions import ServiceError
from dogs_common.observability import logger

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
    # Log detailed validation errors for debugging
    errors = getattr(e, 'errors', None)
    body = getattr(e, 'body', None)
    
    # Handle different types of errors attribute
    error_list = None
    error_count = 0
    
    try:
        if errors:
            if callable(errors):
                error_list = errors()
            else:
                error_list = errors
            
            if error_list and hasattr(error_list, '__len__'):
                error_count = len(error_list)
            elif error_list:
                error_count = 1
    except Exception as ex:
        logger.warning(f"Could not process validation errors: {ex}")
    
    logger.error(
        "RequestValidationError - Response validation failed",
        extra={
            "errors": error_list,
            "response_body": body,
            "error_count": error_count
        }
    )
    
    # Return meaningful error message to client
    error_message = "Request validation failed"
    if error_list and error_count > 0:
        # Extract first error for user-friendly message
        first_error = error_list[0] if isinstance(error_list, (list, tuple)) and len(error_list) > 0 else error_list
        if isinstance(first_error, dict):
            field = first_error.get('loc', ['unknown'])[-1] if first_error.get('loc') else 'unknown'
            msg = first_error.get('msg', 'validation error')
            error_message = f"Validation error in field '{field}': {msg}"
    
    return Response(
        status_code=400, 
        content_type="application/json", 
        body={
            "message": error_message,
            "type": "validation_error"
        }
    )

def handle_value_error(e: ValueError) -> Response:
    logger.exception("ValueError: %s", e)
    return Response(status_code=400, content_type="application/json", body={"message": str(e)})

def handle_generic_error(e: Exception) -> Response:
    logger.exception("Unhandled exception: %s", e)
    return Response(status_code=500, content_type="application/json", body={
        "error": "Internal Server Error",
        "message": "An unexpected error occurred"
    })
