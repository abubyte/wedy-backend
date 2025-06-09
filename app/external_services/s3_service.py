import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException
from app.core.config import settings
import logging
from typing import Optional, List
import os

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL,
            config=boto3.session.Config(
                signature_version='s3v4',
                s3={'addressing_style': 'virtual'},
                retries={'max_attempts': 3}
            )
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    async def upload_file(self, file_path: str, object_name: Optional[str] = None) -> str:
        """Upload a file to S3 bucket."""
        if object_name is None:
            object_name = os.path.basename(file_path)

        try:
            self.s3_client.upload_file(file_path, self.bucket_name, object_name)
            return f"/{object_name}"
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            raise HTTPException(status_code=500, detail="Error uploading file to storage")

    async def delete_file(self, object_name: str) -> None:
        """Delete a file from S3 bucket."""
        if not object_name:
            return

        # Remove leading slash if present
        if object_name.startswith('/'):
            object_name = object_name[1:]

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {str(e)}")
            raise HTTPException(status_code=500, detail="Error deleting file from storage")

    async def delete_files(self, object_names: List[str]) -> None:
        """Delete multiple files from S3 bucket."""
        if not object_names:
            return

        # Remove leading slashes and filter out empty strings
        keys = [name[1:] if name.startswith('/') else name for name in object_names if name]

        try:
            # Delete objects in batches of 1000 (S3 limit)
            for i in range(0, len(keys), 1000):
                batch = keys[i:i + 1000]
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': [{'Key': key} for key in batch]}
                )
        except ClientError as e:
            logger.error(f"Error deleting files from S3: {str(e)}")
            raise HTTPException(status_code=500, detail="Error deleting files from storage")

    def get_file_url(self, object_name: str) -> str:
        """Get the permanent URL for a file in S3 bucket."""
        if not object_name:
            return None

        # Remove leading slash if present
        if object_name.startswith('/'):
            object_name = object_name[1:]

        try:
            # Generate permanent URL using the bucket's endpoint
            url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{object_name}"
            return url
        except Exception as e:
            logger.error(f"Error generating URL for S3 file: {str(e)}")
            raise HTTPException(status_code=500, detail="Error generating file URL") 