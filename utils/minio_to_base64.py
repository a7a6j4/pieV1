import base64
from io import BytesIO
from typing import Optional
import logging
from .minio import minio_client
from config import settings

logger = logging.getLogger(__name__)

class MinIOToBase64Converter:
    def __init__(self):
        """Initialize MinIO client for converting stored objects to base64"""
        self.minio_client = minio_client

    def minio_to_base64(self, bucket_name: str, object_name: str) -> str:
        """
        Convert a MinIO object to base64 encoded string
        
        Args:
            bucket_name: Name of the MinIO bucket
            object_name: Name/path of the object in MinIO
            
        Returns:
            Base64 encoded string of the object content
        """
        try:
            # Get object from MinIO
            response = self.minio_client.get_object(bucket_name, object_name)
            object_content = response.read()
            
            # Convert to base64
            base64_encoded = base64.b64encode(object_content).decode('utf-8')
            
            return base64_encoded
            
        except Exception as e:
            logger.error(f"Failed to convert MinIO object to base64: {e}")
            raise

    def minio_to_base64_with_prefix(self, bucket_name: str, object_name: str, 
                                  content_type: Optional[str] = None) -> str:
        """
        Convert a MinIO object to base64 with data URL prefix
        
        Args:
            bucket_name: Name of the MinIO bucket
            object_name: Name/path of the object in MinIO
            content_type: MIME type of the content (optional, will be detected if not provided)
            
        Returns:
            Base64 encoded string with data URL prefix (e.g., "data:image/jpeg;base64,...")
        """
        try:
            # Get object from MinIO
            response = self.minio_client.get_object(bucket_name, object_name)
            object_content = response.read()
            
            # Get content type from MinIO response if not provided
            if not content_type:
                try:
                    stat = self.minio_client.stat_object(bucket_name, object_name)
                    content_type = stat.content_type or 'application/octet-stream'
                except:
                    content_type = 'application/octet-stream'
            
            # Convert to base64
            base64_encoded = base64.b64encode(object_content).decode('utf-8')
            
            # Return with data URL prefix
            return f"data:{content_type};base64,{base64_encoded}"
            
        except Exception as e:
            logger.error(f"Failed to convert MinIO object to base64 with prefix: {e}")
            raise

    def minio_image_to_base64(self, bucket_name: str, object_name: str) -> str:
        """
        Convert a MinIO image to base64 encoded string with image data URL prefix
        
        Args:
            bucket_name: Name of the MinIO bucket
            object_name: Name/path of the image in MinIO
            
        Returns:
            Base64 encoded string with image data URL prefix (e.g., "data:image/jpeg;base64,...")
        """
        try:
            # Get object from MinIO
            response = self.minio_client.get_object(bucket_name, object_name)
            object_content = response.read()
            
            # Get content type from MinIO response
            try:
                stat = self.minio_client.stat_object(bucket_name, object_name)
                content_type = stat.content_type or 'image/jpeg'
            except:
                content_type = 'image/jpeg'
            
            # Ensure it's an image type
            if not content_type.startswith('image/'):
                content_type = 'image/jpeg'  # Default fallback
            
            # Convert to base64
            base64_encoded = base64.b64encode(object_content).decode('utf-8')
            
            # Return with image data URL prefix
            return f"data:{content_type};base64,{base64_encoded}"
            
        except Exception as e:
            logger.error(f"Failed to convert MinIO image to base64: {e}")
            raise

    def get_minio_object_info(self, bucket_name: str, object_name: str) -> dict:
        """
        Get information about a MinIO object
        
        Args:
            bucket_name: Name of the MinIO bucket
            object_name: Name/path of the object in MinIO
            
        Returns:
            Dictionary with object metadata
        """
        try:
            stat = self.minio_client.stat_object(bucket_name, object_name)
            return {
                'content_type': stat.content_type,
                'content_length': stat.size,
                'last_modified': stat.last_modified,
                'etag': stat.etag,
                'metadata': stat.metadata
            }
        except Exception as e:
            logger.error(f"Failed to get MinIO object info: {e}")
            raise

    def minio_url_to_base64(self, minio_url: str) -> str:
        """
        Convert a MinIO URL to base64 encoded string
        
        Args:
            minio_url: Full MinIO URL (e.g., "http://localhost:9000/bucket/path/to/file.jpg")
            
        Returns:
            Base64 encoded string with image data URL prefix
        """
        try:
            # Extract bucket and object name from URL
            # URL format: http://endpoint/bucket/object_name
            url_parts = minio_url.replace(settings.MINIO_ENDPOINT, '').strip('/')
            parts = url_parts.split('/', 1)
            
            if len(parts) != 2:
                raise ValueError(f"Invalid MinIO URL format: {minio_url}")
            
            bucket_name, object_name = parts
            return self.minio_image_to_base64(bucket_name, object_name)
            
        except Exception as e:
            logger.error(f"Failed to convert MinIO URL to base64: {e}")
            raise


# Convenience functions for quick usage
def convert_minio_to_base64(bucket_name: str, object_name: str) -> str:
    """
    Quick function to convert MinIO object to base64
    
    Args:
        bucket_name: Name of the MinIO bucket
        object_name: Name/path of the object in MinIO
        
    Returns:
        Base64 encoded string
    """
    converter = MinIOToBase64Converter()
    return converter.minio_to_base64(bucket_name, object_name)


def convert_minio_image_to_base64(bucket_name: str, object_name: str) -> str:
    """
    Quick function to convert MinIO image to base64 with data URL prefix
    
    Args:
        bucket_name: Name of the MinIO bucket
        object_name: Name/path of the image in MinIO
        
    Returns:
        Base64 encoded string with image data URL prefix
    """
    converter = MinIOToBase64Converter()
    return converter.minio_image_to_base64(bucket_name, object_name)


def convert_minio_url_to_base64(minio_url: str) -> str:
    """
    Quick function to convert MinIO URL to base64
    
    Args:
        minio_url: Full MinIO URL
        
    Returns:
        Base64 encoded string with image data URL prefix
    """
    converter = MinIOToBase64Converter()
    return converter.minio_url_to_base64(minio_url)


# Example usage:
if __name__ == "__main__":
    # Example 1: Using the class
    converter = MinIOToBase64Converter()
    
    # Convert any MinIO object to base64
    base64_string = converter.minio_to_base64('user', '123/kyc/FRONT_ID.jpg')
    print(f"Base64 string: {base64_string[:100]}...")
    
    # Convert MinIO image to base64 with data URL prefix
    image_base64 = converter.minio_image_to_base64('user', '123/kyc/FRONT_ID.jpg')
    print(f"Image data URL: {image_base64[:100]}...")
    
    # Convert MinIO URL to base64
    minio_url = f"{settings.MINIO_ENDPOINT}/user/123/kyc/FRONT_ID.jpg"
    url_base64 = converter.minio_url_to_base64(minio_url)
    print(f"URL to base64: {url_base64[:100]}...")
    
    # Example 2: Using convenience functions
    base64_string = convert_minio_to_base64('user', '123/kyc/FRONT_ID.jpg')
    image_base64 = convert_minio_image_to_base64('user', '123/kyc/FRONT_ID.jpg')
    url_base64 = convert_minio_url_to_base64(f"{settings.MINIO_ENDPOINT}/user/123/kyc/FRONT_ID.jpg")
