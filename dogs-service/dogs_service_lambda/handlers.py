from aws_lambda_powertools.event_handler.exceptions import ServiceError
from aws_lambda_powertools import Logger
from datetime import datetime, timezone
from db import DynamoDBClient
from dogs_common.config import AppConfig
from models import DogDb, CreateDogRequestPayload, CreateDogResponsePayload
from models import DogInfo, ImageUploadInstructions, CreateImageRequestPayload
from typing import List, Dict, Any
from s3 import S3Client
from utils import get_content_type_from_extension

class DogsService:

    def __init__(self, app_config: AppConfig):
        self.app_config = app_config
        self.db = DynamoDBClient(app_config=app_config)
        self.s3 = S3Client(app_config=app_config)

    def handle_user_dogs_get(self, user_id: str) -> List[DogInfo]:
        dogs_db: List[DogDb] = self.db.batch_query_dogs_with_images(user_id)
        return [DogInfo.create(dog_db) for dog_db in dogs_db]

    def handle_user_dogs_post(self, user_id: str, dog: CreateDogRequestPayload) -> CreateDogResponsePayload:
        dog_db: DogDb = self.db.create_dog(user_id, dog)
        return CreateDogResponsePayload.create(dog_db)

    def handle_create_dog_image_upload(self, user_id: str, dog_id: int, image_request: CreateImageRequestPayload) -> ImageUploadInstructions:
        image_id = self.db.create_image_id(user_id)
        extension = image_request.image_extension.strip().lstrip(".").lower()
        if extension not in self.app_config.supported_image_extensions:
            raise ValueError(f"Unsupported image extension: {extension}. Supported extensions: {self.app_config.supported_image_extensions}")
        s3_key = f"users/{user_id}/dogs/{dog_id}/images/{image_id}.{extension}"
        
        self.db.create_image(user_id, dog_id, image_id, s3_key)
        
        expires_in = self.app_config.image_upload_expiration_secs
        content_type = get_content_type_from_extension(extension)
        presigned_url = self.s3.generate_presigned_put_url(s3_key, expires_in, content_type)
        
        return ImageUploadInstructions(
            image_id=image_id,
            method="PUT",
            presigned_url=presigned_url,
            expires_in=expires_in,
            headers={"Content-Type": content_type},
            max_size=self.app_config.image_upload_max_size
        )


class HealthService:
    def __init__(self, dogs_service: DogsService, app_config: AppConfig):
        self.dogs_service = dogs_service
        self.service_name = app_config.powertools_service_name
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