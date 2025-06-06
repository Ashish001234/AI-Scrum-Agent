import os

from google import genai
from fastapi import HTTPException
from google.api_core.exceptions import TooManyRequests
from dotenv import load_dotenv

load_dotenv()


def transcribe_audio_gemini(file_path: str) -> str:
    """
    Transcribes an audio file using the Gemini API.

    Args:
        file_path: The path to the audio file.

    Returns:
        The transcribed text.

    Raises:
        HTTPException: If there are issues with the Gemini API (e.g., invalid API key, rate limiting).
    """
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))
        audio_data = client.files.upload(file=file_path)
        prompt = "The given audio is in hinglish with a mix of hindi and english. Your task it to write everything in Hinglish format with latin script."
        response = client.models.generate_content(
            model="gemini-2.0-flash", contents=[prompt, audio_data]
        )
        return response.text
    except TooManyRequests as e:
        raise HTTPException(status_code=429, detail=f"Gemini API rate limit exceeded: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize Gemini API: {e}")
