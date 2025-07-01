import os
import uuid
import logging
from fastapi import UploadFile, HTTPException
from PIL import Image
import aiofiles
from typing import List
import shutil
from app.external_services.s3_service import S3Service
from botocore.exceptions import ClientError


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageService:
    def __init__(self):
        self.allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.max_dimension = 1920  # Max width/height in pixels
        self.s3_service = S3Service()

    async def save_image(self, file: UploadFile, entity_type: str) -> str:
        """Save an uploaded image and return its path."""
        logger.info(f"Starting image save process for file: {file.filename}")
        
        if not file or not file.filename:
            logger.warning("No file provided or file has no name.")
            raise HTTPException(
                status_code=400,
                detail="No file provided or file has no name"
            )

        # Validate file extension
        ext = os.path.splitext(file.filename)[1].lower()
        logger.info(f"File extension: {ext}")
        
        if ext not in self.allowed_extensions:
            logger.warning(f"Invalid file type: {file.filename}. Allowed types: {', '.join(self.allowed_extensions)}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {ext}. Allowed types: {', '.join(self.allowed_extensions)}"
            )

        # Generate unique filename
        filename = f"{uuid.uuid4()}{ext}"
        temp_path = f"temp_{filename}"
        s3_path = f"{entity_type}/{filename}"
        logger.info(f"Generated temp path: {temp_path} and S3 path: {s3_path}")

        try:
            # Save file temporarily
            async with aiofiles.open(temp_path, 'wb') as out_file:
                content = await file.read()
                content_size = len(content)
                logger.info(f"Read file content, size: {content_size} bytes")
                
                if content_size == 0:
                    logger.warning(f"Uploaded file is empty: {file.filename}")
                    raise HTTPException(status_code=400, detail="Uploaded file is empty")
                    
                if content_size > self.max_file_size:
                    logger.warning(f"File too large: {content_size} bytes (max: {self.max_file_size} bytes)")
                    raise HTTPException(status_code=400, detail=f"File too large: {content_size} bytes. Max size: 5MB")
                    
                await out_file.write(content)
                logger.info("Successfully wrote content to temp file")

            # Process image
            logger.info("Starting image processing with PIL")
            try:
                with Image.open(temp_path) as img:
                    logger.info(f"Image opened successfully. Mode: {img.mode}, Size: {img.size}")
                    
                    # Resize if needed
                    if max(img.size) > self.max_dimension:
                        logger.info(f"Resizing image from {img.size}")
                        ratio = self.max_dimension / max(img.size)
                        new_size = tuple(int(dim * ratio) for dim in img.size)
                        img = img.resize(new_size, Image.Resampling.LANCZOS)
                        logger.info(f"Resized image to {new_size}")
                    
                    # Save image with correct format and mode
                    if ext in ['.jpg', '.jpeg', '.webp']:
                        if img.mode in ('RGBA', 'P'):
                            logger.info(f"Converting image from {img.mode} to RGB for JPEG/WEBP")
                            img = img.convert('RGB')
                        save_format = 'JPEG' if ext in ['.jpg', '.jpeg'] else 'WEBP'
                        img.save(temp_path, format=save_format, quality=85, optimize=True)
                    elif ext == '.png':
                        if img.mode not in ('RGBA', 'LA'):
                            logger.info(f"Converting image from {img.mode} to RGBA for PNG")
                            img = img.convert('RGBA')
                        img.save(temp_path, format='PNG', optimize=True)
                    else:
                        # Default fallback
                        img.save(temp_path, quality=85, optimize=True)
                    logger.info("Image saved successfully")
            except Exception as e:
                logger.error(f"Error processing image with PIL: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Error processing image: {str(e)}"
                )

            # Upload to S3
            logger.info("Starting S3 upload")
            try:
                s3_path = await self.s3_service.upload_file(temp_path, s3_path)
                logger.info(f"Successfully uploaded {file.filename} to S3 path: {s3_path}")
                return s3_path
            except Exception as e:
                logger.error(f"Error uploading to S3: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error uploading file to storage: {str(e)}"
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing file {file.filename}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}") from e
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                logger.info(f"Cleaning up temp file: {temp_path}")
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.error(f"Error cleaning up temp file: {str(e)}")

    async def delete_image(self, image_path: str) -> None:
        """Delete an image file."""
        await self.s3_service.delete_file(image_path)

    async def delete_images(self, image_paths: List[str]) -> None:
        """Delete multiple image files."""
        await self.s3_service.delete_files(image_paths)

    def get_image_url(self, image_path: str) -> str:
        """Get the full URL for an image."""
        if not image_path:
            return None
        return self.s3_service.get_file_url(image_path) 