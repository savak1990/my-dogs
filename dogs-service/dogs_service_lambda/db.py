import boto3
import json

from botocore.config import Config
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone
from decimal import Decimal

from models import DogDb, DogIn
from typing import List

class DynamoDBClient:
    
    def __init__(self, table_name: str, endpoint_url: str = None):
        self.table_name = table_name
        self.endpoint_url = endpoint_url
        config = Config(connect_timeout=2, read_timeout=5, retries={"max_attempts": 2})
        self._ddb = boto3.resource("dynamodb", config=config, endpoint_url=self.endpoint_url)
        self._table = self._ddb.Table(self.table_name)
    
    def query_dogs_by_user_id(self, user_id: str) -> List[DogDb]:
        pk = f"USER#{user_id}"
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with("DOG#")
        )
        items = resp.get("Items", [])
        normalized_items = [self._normalize_item(item) for item in items]
        return [DogDb.model_validate(item) for item in normalized_items]
    
    def create_dog(self, user_id: str, item: DogIn) -> DogDb:
        seq = self._next_sequence_id(user_id)
        now = datetime.now(timezone.utc).isoformat()
        pk = f"USER#{user_id}"
        sk = f"DOG#{seq}"
        
        item = DogDb(
            PK=pk,
            SK=sk,
            name=item.name,
            age=item.age,
            created_at=now,
            updated_at=now
        )

        self._table.put_item(Item=item.model_dump())
        return item
    
    def health_check(self):
        self._table.meta.client.describe_table(TableName=self.table_name)

    def _next_sequence_id(self, user_id: str) -> int:
        pk = f"USER#{user_id}"
        
        resp = self._table.update_item(
            Key={"PK": pk, "SK": "META#SEQUENCE"},
            UpdateExpression="ADD #c :inc",
            ExpressionAttributeNames={"#c": "dog_counter"},
            ExpressionAttributeValues={":inc": Decimal(1)},
            ReturnValues="UPDATED_NEW")

        new_val = resp.get("Attributes", {}).get("dog_counter", 0)
        return int(new_val)
    
    
    def _normalize_item(self, item: dict) -> dict:
        return json.loads(json.dumps(item, default=self._decimal_default))


    def _decimal_default(self, obj):
        if isinstance(obj, Decimal):
            if obj == obj.to_integral_value():
                return int(obj)
            return float(obj)
        raise TypeError
