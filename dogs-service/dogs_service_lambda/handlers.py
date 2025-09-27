from aws_lambda_powertools.event_handler.exceptions import ServiceError
from aws_lambda_powertools import Logger
from datetime import datetime, timezone
from db import DynamoDBClient
from models import DogDb, CreateDogRequestPayload, CreateDogResponsePayload
from models import DogInfo, ImageUploadInstructions, CreateImageRequestPayload
from typing import List, Dict, Any
from s3 import S3Client
from utils import supported_image_extensions, get_content_type_from_extension

class DogsService:

    def __init__(self, db: DynamoDBClient, s3: S3Client):
        self.db = db
        self.s3 = s3

    def handle_user_dogs_get(self, user_id: str) -> List[DogInfo]:
        dogs_db: List[DogDb] = self.db.query_dogs_by_user_id(user_id)
        return [DogInfo.create(dog_db) for dog_db in dogs_db]

    def handle_user_dogs_post(self, user_id: str, dog: CreateDogRequestPayload) -> CreateDogResponsePayload:
        dog_db: DogDb = self.db.create_dog(user_id, dog)
        return CreateDogResponsePayload.create(dog_db)

    def handle_create_dog_image_upload(self, user_id: str, dog_id: int, image_request: CreateImageRequestPayload) -> ImageUploadInstructions:
        image_id = self.db.create_image_id(user_id)
        extension = image_request.image_extension.strip().lstrip(".").lower()
        if extension not in supported_image_extensions():
            raise ValueError("Unsupported image extension")
        s3_key = f"users/{user_id}/dogs/{dog_id}/images/{image_id}.{extension}"
        
        image_db = self.db.create_image(user_id, dog_id, image_id, s3_key)
        
        expires_in = 3600 # Potentially configured with SSM Parameter Store
        content_type = get_content_type_from_extension(extension)
        presigned_url = self.s3.generate_presigned_put_url(
            s3_key, expires_in, content_type)
        
        return ImageUploadInstructions(
            image_id=image_id,
            s3_key=s3_key,
            method="PUT",
            presigned_url=presigned_url,
            expires_in=expires_in,
            headers={"Content-Type": content_type},
            max_size=5 * 1024 * 1024
        )


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
        
        # DB health status
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
            
        # S3 health status
        try:
            self.dogs_service.s3.health_check()
            health_status["checks"]["s3"] = {"status": "healthy"}
        except Exception as e:
            overall_healthy = False
            health_status["checks"]["s3"] = {
                "status": "unhealthy", 
                "error": str(e)
            }
            self.logger.exception(f"S3 health check failed: {e}")
        
        if not overall_healthy:
            health_status["status"] = "unhealthy"
        
        return health_status