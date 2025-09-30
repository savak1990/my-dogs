from dogs_common.observability import logger, tracer
from aws_lambda_powertools.utilities.data_classes import event_source, S3Event
from aws_lambda_powertools.utilities.typing import LambdaContext

@tracer.capture_lambda_handler
@logger.inject_lambda_context(clear_state=True)
@event_source(data_class=S3Event)
def lambda_handler(event: S3Event, context: LambdaContext):
    logger.info("Processing dog image...")
    
    logger.info(f"Event: {event}")
    
    return {
        'statusCode': 200,
        'body': 'Image processed successfully'
    }