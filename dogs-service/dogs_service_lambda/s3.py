import boto3

from aws_lambda_powertools import Logger
from typing import Optional
from utils import is_running_local

class S3Client:
    def __init__(self, bucket_name: str, endpoint_url: str = None, presign_endpoint: str = None):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.presign_url = presign_endpoint
        self.client = boto3.client("s3", endpoint_url=endpoint_url)
        self.logger = Logger(service="dogs-service", child=True)
    
    def generate_presigned_put_url(
        self, 
        s3_key: str, 
        expires_in: int = 3600, 
        content_type: Optional[str] = None
    ) -> str:
        self.logger.info(f"Generating presigned PUT URL for key: {s3_key}")
        
        params = {
            "Bucket": self.bucket_name,
            "Key": s3_key,
        }
        
        if content_type:
            params["ContentType"] = content_type

        presigned_url = self.client.generate_presigned_url("put_object", Params=params, ExpiresIn=expires_in)
        
        if is_running_local():
            presigned_url = presigned_url.replace(self.endpoint_url, self.presign_url)
        
        self.logger.info(f"Generated presigned PUT URL: {presigned_url}")
        return presigned_url
    
    def health_check(self):
        self.client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)