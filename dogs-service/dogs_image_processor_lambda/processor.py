from dogs_common.config import AppConfig, get_config
from dogs_common.observability import logger, tracer
from aws_lambda_powertools.utilities.data_classes import event_source, S3Event
from aws_lambda_powertools.utilities.typing import LambdaContext

from handlers import get_processor

_app_config = get_config()
_processor = get_processor(_app_config)

@tracer.capture_lambda_handler
@logger.inject_lambda_context(clear_state=True)
@event_source(data_class=S3Event)
def lambda_handler(event: S3Event, _: LambdaContext):
    
    total_result = []
    for record in event.records:
        try:
            item_result = _processor.process_record(record)
            total_result.append(item_result)
        except Exception as e:
            logger.exception(f"Error processing record", exception=e)
            raise e

    # event.records may be a generator (no len()); use the collected results instead
    logger.info(f"Processed {len(total_result)} records", results=total_result)
    return total_result