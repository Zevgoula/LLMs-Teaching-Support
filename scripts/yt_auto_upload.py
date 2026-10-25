import os
import google.auth.exceptions
import google.oauth2.credentials
import google.auth.transport.requests
import google_auth_oauthlib.flow
import googleapiclient.discovery
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.json"
CLIENT_SECRETS_FILE = "client.json"

sys.path.append(str(Path(__file__).resolve().parent.parent)) # to import config

from config import USER_FILES_DIR

def authenticate_youtube():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = google.oauth2.credentials.Credentials.from_authorized_user_file(
            TOKEN_FILE, SCOPES
        )

    # Refresh silently if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(google.auth.transport.requests.Request())
        except google.auth.exceptions.RefreshError:
            creds = None  # token revoked or expired, fall back to login

    # Only open the browser if there is no usable token
    if not creds or not creds.valid:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES
        )
        creds = flow.run_local_server(port=0)
        print("Authentication successful. Saving credentials to token.json")

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

def upload_video(youtube):
    request_body = {
        "snippet": {
            "categoryId": "22",
            "title": "Uploaded from Python",
            "description": "This is the most awsome description ever",
            "tags": ["test","python", "api" ]
        },
        "status":{
            "privacyStatus": "unlisted",
        }
    }

    # put the path of the video that you want to upload
    media_file = USER_FILES_DIR / "video" / "recording.mp4"

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=googleapiclient.http.MediaFileUpload(media_file, chunksize=-1, resumable=True)
    )

    response = None 

    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload {int(status.progress()*100)}%")

        print(f"Upload Complete! Video ID: {response.get('id')}")
        with open("yt_video_id.txt", "w") as f:
            f.write(response.get("id"))

if __name__ == "__main__":
    youtube = authenticate_youtube()
    upload_video(youtube)