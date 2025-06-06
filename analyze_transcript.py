from google import genai
from google.genai import types

from pydantic import BaseModel
from typing import List
import os

from enum import Enum


class ActionType(str, Enum):
    MARK_TICKET_LIVE = "MARK_TICKET_LIVE"
    COMMENT = "COMMENT"
    NOTHING = "NOTHING"


class TicketAction(BaseModel):
    ticket_number: str
    ticket_comment: str
    action_type: ActionType


from dotenv import load_dotenv

load_dotenv()

# Initialize the client
client = genai.Client(api_key=os.getenv("GEMINI_DEVELOPER_API_KEY"))

# Define the prompt
prompt = "".join(open("sample_transcription_prompt.txt"))

# Generate content
response = client.models.generate_content(
    model="gemini-2.5-pro-exp-03-25",  # thinking model compulsory
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json", response_schema=list[TicketAction]
    ),
)

# Print the generated content
with open("gemini_transcript_for_lit.json", "w") as f:
    print(response.model_dump_json(), file=f)
