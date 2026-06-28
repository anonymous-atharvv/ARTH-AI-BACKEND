import os
import boto3
from botocore.exceptions import NoCredentialsError
import structlog
from config import settings

logger = structlog.get_logger()

class StorageService:
    def __init__(self):
        self.s3_enabled = all([
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY,
            settings.AWS_BUCKET_NAME
        ])
        if self.s3_enabled:
            self.s3_client = boto3.client(
                "s3",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            self.bucket_name = settings.AWS_BUCKET_NAME
        else:
            logger.warning("AWS S3 credentials not fully configured. Using local fallback storage.")

    async def upload_file(self, file_bytes: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        """Upload file to S3 if configured, else save locally and return relative path"""
        if self.s3_enabled:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=file_bytes,
                    ContentType=content_type
                )
                url = self.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": key},
                    ExpiresIn=30 * 24 * 3600  # 30 days
                )
                return url
            except Exception as e:
                logger.error("Failed to upload to S3", error=str(e))
                # Fallback to local
        
        # Local fallback
        local_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        with open(local_path, "wb") as f:
            f.write(file_bytes)
            
        return f"/static/{key}"
