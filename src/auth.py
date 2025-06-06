import os
from fastapi import status, Depends
from fastapi.security import APIKeyHeader
from fastapi import HTTPException

from pydantic import BaseModel

from dotenv import load_dotenv

load_dotenv()


class ResponseSchema(BaseModel):
    success: bool
    code: str  # e.g., "SUCCESS", "WRONG_INPUT", "INTERNAL_SERVER_ERROR"
    message: str
    status_code: int  # HTTP status code
    body: dict = None


def verify_api_key(api_key: str) -> bool:
    """
    Verify if the provided API key is valid.
    This is a placeholder function. In a real-world scenario, you would implement actual verification logic.
    """
    # For demonstration purposes, let's assume any non-empty string is a valid API key
    return api_key in os.getenv("VALID_API_KEYS", "").split(",")


api_key_header = APIKeyHeader(name="x-api-key")


def api_key_auth(api_key_header: str = Depends(api_key_header)):
    if not verify_api_key(api_key_header):
        raise HTTPException(
            status_code=401,
            detail=ResponseSchema(
                success=False,
                code="UNAUTHORIZED",
                message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ),
        )
    return True
