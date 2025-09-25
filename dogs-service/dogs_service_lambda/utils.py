import json

from models import Context, Error, ErrorCode, ErrorHolder, RequestHolder, ResponseHolder, SuccessfulResponseHolder
from datetime import datetime, timezone

DEFAULT_RESPONSE_HEADERS = {"Content-Type": "application/json"}

DATETIME_NOW_UTC_FN = lambda: datetime.now(timezone.utc)

def to_json(obj) -> str:
    """ Convert an object to a JSON string """
    return json.dumps(obj, default=lambda o: o.__dict__)

def build_request_holder(event) -> RequestHolder:
    """ Build a request holder object from raw event """
    

def build_response(response_holder: ResponseHolder) -> dict:
    """ Build a response dictionary from a ResponseHolder """
    
    response = {
        "statusCode": response_holder.status_code,
        "headers": {k.lower(): [{"key": k, "value": v}] for k, v in response_holder.headers.items()},
    }
    
    if response_holder.response is not None:
        response["body"] = to_json(response_holder.response)
    
    return response

def build_successful_response(context: Context, status_code: int = 200, response: any = None) -> SuccessfulResponseHolder:
    """ Build a SuccessfulResponseHolder """
    return SuccessfulResponseHolder(status_code=status_code, headers=DEFAULT_RESPONSE_HEADERS, response=response)

def build_error_holder(context: Context, status_code: int, code: ErrorCode, message: str) -> ErrorHolder:
    """ Build an ErrorHolder """
    error = Error(code=code, message=message)
    return ErrorHolder(status_code=status_code, headers=DEFAULT_RESPONSE_HEADERS, response=error)

def build_bad_request_error(context: Context, message: str) -> ErrorHolder:
    return build_error_holder(context, 400, ErrorCode.BAD_REQUEST, message)

def build_unexpected_error(context: Context, message: str) -> ErrorHolder:
    return build_error_holder(context, 500, ErrorCode.UNEXPECTED_ERROR, message)

def get_query_param_single(event, key, default=None):
    mv = (event.get("multiValueQueryStringParameters") or {}).get(key)
    if mv:
        return mv[0]
    qs = (event.get("queryStringParameters") or {}).get(key)
    return qs if qs is not None else default

def get_query_param_list(event, key):
    mv = (event.get("multiValueQueryStringParameters") or {}).get(key)
    if mv:
        return mv
    qs = (event.get("queryStringParameters") or {}).get(key)
    if qs is None:
        return []
    # if single string with commas, split; adjust to your API convention
    return [s for s in qs.split(",") if s]

