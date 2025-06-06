from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from api import analyze_transcript, process_audio
from auth import api_key_auth

from fastapi.responses import JSONResponse
from fastapi import HTTPException


async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(exc.detail.model_dump(mode="json"), status_code=exc.status_code)


app = FastAPI()
app.add_exception_handler(HTTPException, http_exception_handler)

# Configure CORS (Cross-Origin Resource Sharing)
# This allows your frontend to make requests to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # Allows all origins (for development - VERY IMPORTANT TO CHANGE FOR PRODUCTION)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include the API routers
app.include_router(process_audio.router, prefix="/api/v1")
app.include_router(analyze_transcript.router, prefix="/api/v1")


@app.get("/", dependencies=[Depends(api_key_auth)])
async def read_root():
    return {"message": "Welcome to Eye of Horus!"}
