from typing import Optional
import boto3

from aws_lambda_powertools import Logger

class S3Client:
    def __init__(self, bucket_name: str, endpoint_url: str = None):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
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
        self.logger.info(f"Generated presigned PUT URL: {presigned_url}")
        return presigned_url
    
    def health_check(self):
        self.client.list_buckets()