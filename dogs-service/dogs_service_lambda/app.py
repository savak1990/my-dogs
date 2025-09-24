import json
import os
import requests

from aws_lambda_powertools import Logger

print("Set loglevel to " + os.environ.get("LOG_LEVEL"))

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logger = Logger(service="dogs-service", level=LOG_LEVEL)

# import requests

def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    logger.info("handler invoked", extra={"event_present": bool(event)})

    try:
        ip = requests.get("http://checkip.amazonaws.com/")
        ip.raise_for_status()
    except requests.RequestException as e:
        logger.error("Unable to get IP address: %s", e)
        raise e

    logger.info("handler completed", extra={"event_present": bool(event)})

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "hello world",
            "location": ip.text.replace("\n", "")
        }),
    }
