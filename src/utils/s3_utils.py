import os
import boto3
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
AWS_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Initialize S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)


async def get_file_from_s3(bucket_name: str, key: str) -> bytes:
    """
    Retrieves a file from S3.

    Args:
        bucket_name: The name of the S3 bucket.
        key: The key of the file in the bucket.

    Returns:
        The file content as bytes.

    Raises:
        HTTPException: If there are issues retrieving the file from S3.
    """
    try:
        response = s3.get_object(Bucket=bucket_name, Key=key)
        return response["Body"].read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving file from S3: {e}")


async def store_file_in_s3(prefix: str, file_name: str, file_content: bytes) -> str:
    """
    Stores a file in S3 and returns a presigned URL.

    Args:
        bucket_name: The name of the S3 bucket.
        key: The key to use for the file in the bucket.
        file_content: The content of the file as bytes.

    Returns:
        The S3 URL of the stored file.

    Raises:
        HTTPException: If there are issues storing the file in S3.
    """
    try:
        key = os.path.join(prefix, file_name)
        # Store the file in S3
        s3.put_object(Bucket=AWS_BUCKET_NAME, Key=key, Body=bytes(file_content))
        return s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": AWS_BUCKET_NAME, "Key": key},
            ExpiresIn=3600 * 24 * 100,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing file in S3: {e}")
