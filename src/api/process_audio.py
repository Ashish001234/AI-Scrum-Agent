import os
import json
import httpx  # Import httpx for making HTTP requests

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from utils.audio_transcriber import (
    transcribe_audio_gemini,
)  # Import the transcribe_audio function
from utils.s3_utils import store_file_in_s3
from utils.download_google_meet_recordings import authenticate_drive, get_audio_path
from pydantic import BaseModel
from typing import Optional

from fastapi import Depends
from auth import api_key_auth

from dotenv import load_dotenv

load_dotenv()

router = APIRouter()


class AudioProcessRequest(BaseModel):
    file_uri: str
    log_id: str


class ResponseSchema(BaseModel):
    success: bool
    code: str  # e.g., "SUCCESS", "WRONG_INPUT", "INTERNAL_SERVER_ERROR"
    message: str
    status_code: int  # HTTP status code
    s3_url: Optional[str] = None


async def download_file(file_uri: str) -> bytes:
    """Downloads a file from a given URI."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(file_uri, timeout=60)  # Set a timeout
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.content
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=ResponseSchema(
                    success=False,
                    code="HTTP_ERROR",
                    message=f"HTTP error: {e.response.status_code} - {e.response.text}",
                    status_code=e.response.status_code,
                ).json(),
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ResponseSchema(
                    success=False,
                    code="REQUEST_ERROR",
                    message=f"Request error: {e}",
                    status_code=status.HTTP_400_BAD_REQUEST,
                ).json(),
            )


@router.post("/process-audio/", response_model=ResponseSchema, dependencies=[Depends(api_key_auth)])
async def process_audio(request: AudioProcessRequest):
    """
    Endpoint to process audio files, transcribe them, and return the storage URI.
    """
    try:
        # Authenticate with Google Drive
        service = authenticate_drive()

        # Download the audio file from the provided URI
        audio_file_path = get_audio_path(service, request.file_uri)
        transcript_file_name = f"{request.log_id}.txt"

        # Transcribe the audio using the utility function
        transcript = transcribe_audio_gemini(audio_file_path)

        storage_uri = await store_file_in_s3(
            prefix="transcripts/",
            file_name=transcript_file_name,
            file_content=transcript.encode("utf-8"),
        )

        # Clean up the temporary file
        os.remove(audio_file_path)

        return ResponseSchema(
            success=True,
            code="SUCCESS",
            message="Audio processed successfully",
            status_code=status.HTTP_200_OK,
            s3_url=storage_uri,
        )
    except HTTPException as http_exception:
        return JSONResponse(
            status_code=http_exception.status_code, content=json.loads(http_exception.detail)
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseSchema(
                success=False,
                code="INTERNAL_SERVER_ERROR",
                message=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ).json(),
        )
