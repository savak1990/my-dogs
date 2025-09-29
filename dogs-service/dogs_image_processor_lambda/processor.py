from dogs_common import logger, tracer, get_config

config = get_config()

@tracer.capture_lambda_handler
@logger.inject_lambda_context(clear_state=True)
def lambda_handler(event, context):
    logger.info("Processing dog image...")
    
    logger.info(f"Event: {event}")
    
    return {
        'statusCode': 200,
        'body': 'Image processed successfully'
    }