"""
Cloudflare Stream and R2 Storage Integration Service
Handles video uploads to Cloudflare Stream for streaming and R2 for backup storage
"""
import httpx
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any
import logging
from pathlib import Path
import uuid

from ..core.config import settings

logger = logging.getLogger(__name__)


class CloudflareService:
    """Service for Cloudflare Stream and R2 operations"""
    
    def __init__(self):
        self.account_id = settings.CLOUDFLARE_ACCOUNT_ID
        self.api_token = settings.CLOUDFLARE_API_TOKEN
        self.stream_api_base = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/stream"
        
        # Initialize R2 client (S3-compatible)
        self.r2_client = None
        if settings.CLOUDFLARE_R2_ACCESS_KEY_ID and settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY:
            try:
                self.r2_client = boto3.client(
                    's3',
                    endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT,
                    aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
                    region_name='auto'
                )
            except Exception as e:
                logger.error(f"Failed to initialize R2 client: {str(e)}")
    
    async def upload_video_to_stream(
        self,
        file_content: bytes,
        filename: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload video directly to Cloudflare Stream via Direct Creator Upload
        
        Args:
            file_content: Video file content as bytes
            filename: Original filename
            metadata: Optional metadata for the video
            
        Returns:
            Dict containing video UID, status, and other Stream details
        """
        if not self.account_id or not self.api_token:
            raise ValueError("Cloudflare credentials not configured")
        
        try:
            # Step 1: Create a Direct Creator Upload URL
            async with httpx.AsyncClient() as client:
                # Request upload URL
                create_response = await client.post(
                    f"{self.stream_api_base}/direct_upload",
                    headers={
                        "Authorization": f"Bearer {self.api_token}",
                    },
                    json={
                        "maxDurationSeconds": 21600,  # 6 hours max
                        "requireSignedURLs": False,  # Set to True for private videos
                        "meta": metadata or {"name": filename}
                    }
                )
                create_response.raise_for_status()
                upload_data = create_response.json()
                
                if not upload_data.get("success"):
                    raise Exception(f"Failed to create upload URL: {upload_data.get('errors')}")
                
                result = upload_data["result"]
                upload_url = result["uploadURL"]
                video_uid = result["uid"]
                
                # Step 2: Upload the actual video file
                upload_response = await client.post(
                    upload_url,
                    files={
                        "file": (filename, file_content, "video/mp4")
                    }
                )
                upload_response.raise_for_status()
                
                logger.info(f"Video uploaded to Stream successfully: {video_uid}")
                
                return {
                    "uid": video_uid,
                    "status": "pending",  # Will be "ready" once encoding completes
                    "thumbnail": f"https://customer-{self.account_id}.cloudflarestream.com/{video_uid}/thumbnails/thumbnail.jpg",
                    "preview": f"https://customer-{self.account_id}.cloudflarestream.com/{video_uid}/watch",
                    "embed_code": result.get("embedCode", ""),
                }
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error uploading to Stream: {str(e)}")
            raise Exception(f"Failed to upload video to Cloudflare Stream: {str(e)}")
        except Exception as e:
            logger.error(f"Error uploading to Stream: {str(e)}")
            raise Exception(f"Video upload failed: {str(e)}")
    
    async def get_video_details(self, video_uid: str) -> Dict[str, Any]:
        """
        Get video details from Cloudflare Stream
        
        Args:
            video_uid: The Cloudflare Stream video UID
            
        Returns:
            Dict with video status, duration, thumbnail, etc.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.stream_api_base}/{video_uid}",
                    headers={"Authorization": f"Bearer {self.api_token}"}
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("success"):
                    result = data["result"]
                    return {
                        "uid": result.get("uid"),
                        "status": result.get("status", {}).get("state", "unknown"),
                        "duration": result.get("duration"),
                        "thumbnail": result.get("thumbnail"),
                        "preview": result.get("preview"),
                        "playback": result.get("playback"),
                    }
                else:
                    raise Exception(f"Failed to get video details: {data.get('errors')}")
                    
        except Exception as e:
            logger.error(f"Error getting video details: {str(e)}")
            raise
    
    async def delete_video_from_stream(self, video_uid: str) -> bool:
        """
        Delete a video from Cloudflare Stream
        
        Args:
            video_uid: The Cloudflare Stream video UID
            
        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.stream_api_base}/{video_uid}",
                    headers={"Authorization": f"Bearer {self.api_token}"}
                )
                response.raise_for_status()
                return True
                
        except Exception as e:
            logger.error(f"Error deleting video from Stream: {str(e)}")
            return False
    
    def upload_to_r2(
        self,
        file_content: bytes,
        filename: str,
        content_type: str = "video/mp4"
    ) -> Optional[str]:
        """
        Upload file to Cloudflare R2 storage (backup/alternative storage)
        
        Args:
            file_content: File content as bytes
            filename: Destination filename in R2
            content_type: MIME type of the file
            
        Returns:
            Public URL of the uploaded file or None if failed
        """
        if not self.r2_client:
            logger.warning("R2 client not configured, skipping R2 upload")
            return None
        
        try:
            # Generate unique filename
            file_ext = Path(filename).suffix
            unique_filename = f"videos/{uuid.uuid4()}{file_ext}"
            
            # Upload to R2
            self.r2_client.put_object(
                Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME,
                Key=unique_filename,
                Body=file_content,
                ContentType=content_type
            )
            
            # Generate public URL (adjust based on your R2 public URL setup)
            public_url = f"{settings.CLOUDFLARE_R2_ENDPOINT}/{settings.CLOUDFLARE_R2_BUCKET_NAME}/{unique_filename}"
            
            logger.info(f"File uploaded to R2: {unique_filename}")
            return public_url
            
        except ClientError as e:
            logger.error(f"Error uploading to R2: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading to R2: {str(e)}")
            return None
    
    def delete_from_r2(self, file_key: str) -> bool:
        """
        Delete a file from R2 storage
        
        Args:
            file_key: The R2 object key
            
        Returns:
            True if successful
        """
        if not self.r2_client:
            return False
        
        try:
            self.r2_client.delete_object(
                Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME,
                Key=file_key
            )
            logger.info(f"File deleted from R2: {file_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting from R2: {str(e)}")
            return False


# Singleton instance
cloudflare_service = CloudflareService()
