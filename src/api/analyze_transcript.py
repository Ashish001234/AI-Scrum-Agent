from typing import Dict, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
import json
import httpx
from enum import Enum

from utils import transcript_analyser

from fastapi import Depends
from auth import api_key_auth


class ActionType(str, Enum):
    UPDATE_FIELDS = "UPDATE_FIELDS"
    POST_COMMENT = "POST_COMMENT"
    CHANGE_STAGE = "CHANGE_STAGE"
    NONE = "NONE"


class FieldsToUpdate(BaseModel):
    field_name: str
    new_value: str


class ActionDetails(BaseModel):
    fields_to_update: List[FieldsToUpdate] = []
    comment_text: str = ""
    tag_users: List[str] = []
    new_stage: str = ""
    reason: str = ""


class TicketAction(BaseModel):
    ticket_number: str
    ticket_id: str
    action_type: ActionType
    action_details: ActionDetails
    confidence_score: float
    transcript_context: str
    reasoning: str


class ResponseSchema(BaseModel):
    success: bool
    code: str  # e.g., "SUCCESS", "WRONG_INPUT", "INTERNAL_SERVER_ERROR"
    message: str
    status_code: int  # HTTP status code
    body: Optional[List[TicketAction]] = None


class TranscriptAnalyzeRequest(BaseModel):
    transcript_url: str
    pod_members: List[Dict]
    sprint_details: List[Dict]


router = APIRouter()

from dotenv import load_dotenv

load_dotenv()


async def download_file(s3_url: str) -> bytes:
    """
    Downloads a file from S3 using the provided URL using httpx.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(s3_url, timeout=30)  # 30 seconds timeout
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.content
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
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


@router.post(
    "/analyze-transcription", response_model=ResponseSchema, dependencies=[Depends(api_key_auth)]
)
async def analyze_transcript_endpoint(request: TranscriptAnalyzeRequest):
    """
    Endpoint to analyze a transcription file stored in S3.
    """
    try:
        # Fetch the transcription text from S3
        transcript_url = request.transcript_url

        # Download the file using the utility function
        file_content = await download_file(transcript_url)
        transcription_text = file_content.decode("utf-8")

        # Analyze the transcription
        result = transcript_analyser.analyze_transcription(
            transcription_text=transcription_text,
            pod_members=request.pod_members,
            sprint_details=request.sprint_details,
        )

        # Create the map of ticket numbers to id
        ticket_number_to_id_map = {}
        for ticket in request.sprint_details:
            ticket_number = ticket.get("display_id", "")
            if ticket_number:
                ticket_number_to_id_map[ticket_number] = ticket.get("id")

        # Add ticket_id to each action
        for action in result:
            ticket_number = action["ticket_number"]
            if ticket_number in ticket_number_to_id_map:
                action["ticket_id"] = ticket_number_to_id_map[ticket_number]
            else:
                action["ticket_id"] = ""

        return ResponseSchema(
            success=True,
            code="SUCCESS",
            message="Transcription analysis completed successfully.",
            status_code=status.HTTP_200_OK,
            body=result,
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
