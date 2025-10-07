from minio import Minio
from minio.error import S3Error
from config import settings
  
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