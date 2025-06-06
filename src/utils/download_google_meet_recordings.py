import os
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from pydub import AudioSegment

# Define the OAuth 2.0 scope for read-only access to Google Drive
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def authenticate_drive():
    """Authenticate with Google Drive API and return the service object."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    service = build("drive", "v3", credentials=creds)
    return service


def find_meet_recordings_folder(service):
    """Find the 'Meet Recordings' folder in Google Drive."""
    query = "name='Travel' and mimeType='application/vnd.google-apps.folder'"
    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    folders = results.get("files", [])
    if not folders:
        print("No 'Meet Recordings' folder found.")
        return None
    return folders[0]["id"]


def list_recordings(service, folder_id):
    """List all video files in the specified folder."""
    query = f"'{folder_id}' in parents and (mimeType='video/webm' or mimeType='video/mp4')"
    results = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id, name, mimeType)",  # Include mimeType to determine extension
        )
        .execute()
    )
    files = results.get("files", [])
    return files


def download_recording_file(service, file_id, mime_type=".mp4", download_path="downloads"):
    """Download a file from Google Drive to the specified path with appropriate extension."""
    # Create the download directory if it doesn't exist
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    # Determine the file extension based on MIME type
    extension = ".webm" if mime_type == "video/webm" else ".mp4"

    # Append extension if not already present
    file_name = file_id + extension

    # Define the output file path
    output_file = os.path.join(download_path, file_name)

    # Check if file already exists
    if os.path.exists(output_file):
        print(f"File '{file_name}' already exists, skipping download.")
        return output_file

    # Download the file
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(output_file, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Downloading '{file_name}' ({int(status.progress() * 100)}%)")
    print(f"Downloaded '{file_name}' to '{output_file}'")

    # return file path
    return output_file


def convert_video_to_audio(video_path, audio_path="downloads", bitrate="320k"):
    """Convert a video file to high-quality MP3 audio."""
    if not os.path.exists(audio_path):
        os.makedirs(audio_path)

    # Generate output audio file name (replace video extension with .mp3)
    audio_file_name = os.path.splitext(os.path.basename(video_path))[0] + ".mp3"
    output_audio_file = os.path.join(audio_path, audio_file_name)

    # Check if audio file already exists
    if os.path.exists(output_audio_file):
        print(f"Audio file '{audio_file_name}' already exists, skipping conversion.")
        return output_audio_file

    try:
        # Load the video file and extract audio
        print(f"Converting '{video_path}' to audio...")
        audio = AudioSegment.from_file(video_path)

        # Export as MP3 with high-quality bitrate
        audio.export(output_audio_file, format="mp3", bitrate=bitrate)
        print(f"Converted to '{output_audio_file}' (bitrate: {bitrate})")
        return output_audio_file
    except Exception as e:
        print(f"Error converting '{video_path}': {str(e)}")
        return None


def get_audio_path(service, file_id, mime_type=".mp4"):
    """Run the download and conversion process for a specific file."""
    # Download the recording file
    video_path = download_recording_file(service, file_id, mime_type)

    if not video_path:
        print(f"Failed to download file with ID '{file_id}'.")
        return None

    # Convert to audio
    audio_path = convert_video_to_audio(video_path)

    # Remove the video file after conversion
    if os.path.exists(video_path):
        os.remove(video_path)
        print(f"Removed video file '{video_path}' after conversion.")

    return audio_path


def main():
    """Main function to download Google Meet recordings and convert to audio."""
    # Authenticate and get the Drive service
    service = authenticate_drive()

    # Find the 'Meet Recordings' folder
    folder_id = find_meet_recordings_folder(service)
    if not folder_id:
        return

    # List all recordings in the folder
    recordings = list_recordings(service, folder_id)
    if not recordings:
        print("No recordings found in 'Meet Recordings' folder.")
        return

    # Download and convert each recording
    print(f"Found {len(recordings)} recordings:")
    for file in recordings:
        print(f"- {file['name']} (ID: {file['id']}, Type: {file['mimeType']})")
        # Download the video
        get_audio_path(service, file["id"], file["mimeType"])


if __name__ == "__main__":
    main()
