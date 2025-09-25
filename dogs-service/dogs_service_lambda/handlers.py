from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.models import APIGatewayProxyEvent

from models import Context, DogIn, DogOut
from utils import build_successful_response, build_bad_request_error

def handle_user_dogs_get(context: Context, request: APIGatewayProxyEvent):
    
    user_id = (request.pathParameters or {}).get("user_id")
    if not user_id:
        return build_bad_request_error(context, "user_id is required")
    
    dogs = [
        DogOut(user_id=user_id, name="Buddy", age=5),
        DogOut(user_id=user_id, name="Max", age=3),
    ]
    
    return build_successful_response(context, [d.model_dump() for d in dogs])

def handle_user_dogs_post(context: Context, request: APIGatewayProxyEvent):
    
    user_id = request.path_params.get("user_id")
    if not user_id:
        return build_bad_request_error(context, "user_id is required")

    dog_in = parse(request.body, model=DogIn)

    if not dog_in:
        return build_bad_request_error(context, "Invalid dog data")

    dog_out = DogOut(user_id=user_id, name=dog_in.name, age=dog_in.age)

    return build_successful_response(context, dog_out)