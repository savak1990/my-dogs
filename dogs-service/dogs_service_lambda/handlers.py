
from db import DynamoDBClient
from models import DogDb, CreateDogRequestPayload, CreateDogResponsePayload, DogInfo, UploadInfo
from typing import List, Dict, Any
from datetime import datetime, timezone
from aws_lambda_powertools.event_handler.exceptions import ServiceError
from aws_lambda_powertools import Logger

class DogsService:

    def __init__(self, db: DynamoDBClient):
        self.db = db

    def handle_user_dogs_get(self, user_id: str) -> List[DogInfo]:
        dogs_db: List[DogDb] = self.db.query_dogs_by_user_id(user_id)
        return [DogInfo.create(dog_db) for dog_db in dogs_db]

    def handle_user_dogs_post(self, user_id: str, dog: CreateDogRequestPayload) -> CreateDogResponsePayload:
        dog_db: DogDb = self.db.create_dog(user_id, dog)
        upload_id = self.db.create_upload_id()
        
        upload_info = UploadInfo(
            upload_id=upload_id,
            method="PUT",
            presigned_url=f"https://placeholder-bucket.s3.amazonaws.com/uploads/user-{user_id}/dog-{dog_db.SK.split('#')[1]}.jpg?signature=placeholder",
            expires_in=300,
            max_size=5242880
        )
        
        return CreateDogResponsePayload.create(dog_db, upload_info)


class HealthService:
    def __init__(self, dogs_service: DogsService, service_name: str = "dogs-service"):
        self.dogs_service = dogs_service
        self.service_name = service_name
        self.logger = Logger()
    
    def get_health_status(self) -> Dict[str, Any]:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "checks": {}
        }
        
        overall_healthy = True
        
        health_status["checks"]["service"] = {"status": "healthy"}
        
        try:
            self.dogs_service.db.health_check()
            health_status["checks"]["database"] = {"status": "healthy"}
        except ServiceError as e:
            overall_healthy = False
            health_status["checks"]["database"] = {
                "status": "unhealthy", 
                "error": str(e)
            }
            self.logger.exception(f"Database health check failed: {e}")
        except Exception as e:
            overall_healthy = False
            health_status["checks"]["database"] = {
                "status": "unhealthy", 
                "error": "Database connection test failed"
            }
            self.logger.exception(f"Unexpected error in database health check: {e}")
        
        if not overall_healthy:
            health_status["status"] = "unhealthy"
        
        return health_status