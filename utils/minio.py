from minio import Minio
from minio.error import S3Error
from config import settings
import io
from fastapi import HTTPException, UploadFile, status
import os
  
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False
)

async def upload_file(
  bucket_name: str, 
  file_object,
  file_name: str,
  content_type: str):


  file_object.seek(0,2)
  file_size = file_object.tell()
  file_object.seek(0)

  minio_client.put_object(
    bucket_name=bucket_name,
    object_name=file_name,
    data=file_object,
    length=file_size,
    content_type=content_type
  )
  return f"{settings.MINIO_ENDPOINT}/{bucket_name}/{file_name}"

async def get_file(bucket_name: str, file_name: str):
  return minio_client.presigned_get_object(bucket_name=bucket_name, object_name=file_name)

def download_s3_object(bucket_name: str, object_name: str):
    """
    Download an S3 object and return as bytes
    
    Returns:
        bytes: The file content as bytes
    """
    try:
        response = minio_client.get_object(bucket_name, object_name)
        file_data = response.read()
        response.close()
        response.release_conn()
        return file_data
    except S3Error as e:
        raise Exception(f"Error downloading S3 object: {e}")

async def download_s3_object_for_requests(bucket_name: str, object_name: str, content_type: str = "application/octet-stream"):
    """
    Download an S3 object and return it formatted for requests files parameter
    
    Returns:
        tuple: (filename, file_object, content_type) ready for requests files parameter
    """
    try:
        response = minio_client.get_object(bucket_name, object_name)
        file_data = response.read()
        response.close()
        response.release_conn()
        
        # Create a file-like object from bytes
        file_obj = io.BytesIO(file_data)
        file_obj.name = object_name  # Set the filename
        
        # Return tuple in format expected by requests files parameter
        return (object_name, file_obj, content_type)
        
    except S3Error as e:
        raise Exception(f"Error downloading S3 object: {e}")

# File validation constants
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_image_file(file: UploadFile) -> None:
    """
    Validate uploaded image file for type, size, and content
    """
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size too large. Maximum allowed size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Check file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed"
        )
    
    # Check MIME type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only {', '.join(ALLOWED_IMAGE_TYPES)} images are allowed"
        )
    
    # Validate file content using magic numbers
    try:
        file.file.seek(0)
        file_content = file.file.read(1024)  # Read first 1KB for magic number detection
        file.file.seek(0)  # Reset to beginning
        
        # Check for image magic numbers based on file type
        is_valid_image = False
        
        if file.content_type in ["image/jpeg", "image/jpg"]:
            # JPEG magic numbers: FF D8 FF or FF D8
            is_valid_image = (file_content.startswith(b'\xff\xd8\xff') or 
                            file_content.startswith(b'\xff\xd8'))
        elif file.content_type == "image/png":
            # PNG magic number: 89 50 4E 47 0D 0A 1A 0A
            is_valid_image = file_content.startswith(b'\x89PNG\r\n\x1a\n')
        elif file.content_type == "image/webp":
            # WebP magic number: 52 49 46 46 (RIFF) followed by 57 45 42 50 (WEBP)
            is_valid_image = (file_content.startswith(b'RIFF') and 
                            len(file_content) >= 12 and 
                            file_content[8:12] == b'WEBP')
        
        if not is_valid_image:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file content. File does not appear to be a valid {file.content_type} image"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error validating file content"
        )        