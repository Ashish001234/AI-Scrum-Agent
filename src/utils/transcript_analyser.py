from google import genai
from google.genai import types

from typing import List
from pydantic import BaseModel
from jinja2 import Template
import os

from enum import Enum
import datetime


class ActionType(str, Enum):
    UPDATE_FIELDS = "UPDATE_FIELDS"
    POST_COMMENT = "POST_COMMENT"
    CHANGE_STAGE = "CHANGE_STAGE"
    NONE = "NONE"


class FieldsToUpdate(BaseModel):
    field_name: str
    new_value: str


class ActionDetails(BaseModel):
    fields_to_update: List[FieldsToUpdate]
    comment_text: str
    tag_users: List[str]
    new_stage: str
    reason: str


class TicketAction(BaseModel):
    ticket_number: str
    action_type: ActionType
    action_details: ActionDetails
    confidence_score: float
    transcript_context: str
    reasoning: str


from dotenv import load_dotenv

load_dotenv()


def get_sprint_details(sprint_details: List[dict]) -> List[dict]:
    result = []
    for work_item in sprint_details:
        sprint_item = {
            "ticket_number": work_item["display_id"],
            "title": work_item["title"],
            "product_manager": work_item.get("custom_fields", {}).get("tnt__product_manager", ""),
            "developers": work_item.get("custom_fields", {}).get("tnt__developers", []),
            "qa": work_item.get("custom_fields", {}).get("tnt__qa", ""),
            "start_date": work_item.get("sprint", {}).get("start_date", ""),
            "end_date": work_item.get("target_close_date", ""),
            "dev_end_date": work_item.get("custom_fields", {}).get("tnt__dev_closure_date", ""),
            "dev_start_date": work_item.get("custom_fields", {}).get("tnt__dev_start_date", ""),
            "stage": work_item.get("stage", {}).get("name", ""),
            "owned_by": [member.get("id", "") for member in work_item.get("owned_by", {})][0],
        }
        result.append(sprint_item)
    return result


def get_sprint_meeting_prompt(sprint_members, sprint_details):
    """ 
    Create prompt to include sprint members, and all current sprint issues and tickets.
    """
    template = Template("".join(open("prompts/sprint_meeting_info_template.txt")))
    prompt = template.render(members=sprint_members, sprint_details=sprint_details)
    return prompt


def analyze_transcription(transcription_text: str, pod_members: dict, sprint_details: dict):
    """
    Analyze the transcription text and generate content using the Gemini API.
    """
    # Initialize the client
    client = genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))

    # Define the prompt
    system_prompt = "".join(open("prompts/full_system_prompt.md"))

    # Gather sprint details
    sprint_details = get_sprint_details(sprint_details)
    sprint_meeting_prompt = get_sprint_meeting_prompt(pod_members, sprint_details)
    today_date = f"Today's date is {datetime.datetime.now().strftime('%Y-%m-%d')}"
    transcription_text = "\n".join([today_date, sprint_meeting_prompt, transcription_text])

    # Generate content
    response = client.models.generate_content(
        model="gemini-2.5-pro-exp-03-25",  # thinking model compulsory
        contents=transcription_text,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=list[TicketAction],
        ),
    )

    return response.to_json_dict()["parsed"]
