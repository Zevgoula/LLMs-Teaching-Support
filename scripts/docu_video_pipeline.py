"""WAV -> MP4 -> YouTube upload."""

import argparse
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import USER_FILES_DIR

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]



def convert_wav_to_mp4(audio_path, image_path, output_dir):
    """Static image + audio -> small MP4."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (Path(audio_path).stem + ".mp4") 
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y",
        "-loop", "1", "-framerate", "1", "-i", str(image_path),
        "-i", str(audio_path),
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
        "-crf", "40", "-pix_fmt", "yuv420p",
        "-vf", "scale=320:180:force_original_aspect_ratio=decrease,"
               "pad=320:180:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    return output_path


def get_youtube():
    """Log in (browser on first run, token.json afterwards)."""
    creds = None
    if Path("token.json").exists():
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            creds = None
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("client.json", SCOPES)
        creds = flow.run_local_server(port=0)
        Path("token.json").write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, video_path, title, description, privacy="unlisted"):
    body = {
        "snippet": {"title": title, "description": description, "categoryId": "22"},
        "status": {"privacyStatus": privacy},
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload {int(status.progress() * 100)}%")
    return response["id"]


def main():
    p = argparse.ArgumentParser(description="Turn a WAV recording into a YouTube video.")
    p.add_argument("audio", type=Path, nargs="?",
                   default=USER_FILES_DIR / "audio" / "tester.wav",
                   help="Path to a .wav file (default: %(default)s)")
    p.add_argument("--image", type=Path,
                   default=Path(__file__).resolve().parent.parent / "cover.png")
    p.add_argument("--title", default="Test upload")
    p.add_argument("--description", default="Test description")
    p.add_argument("--privacy", choices=["public", "unlisted", "private"], default="unlisted")
    args = p.parse_args()

    if not args.audio.exists():
        p.error(f"Audio file not found: {args.audio}")
    if not args.image.exists():
        p.error(f"Cover image not found: {args.image}")

    video = convert_wav_to_mp4(args.audio, args.image, USER_FILES_DIR / "video")
    video_id = upload_video(get_youtube(), video, args.title, args.description, args.privacy)
    with open("yt_video_id.txt", "w") as f:
        f.write(video_id)
    print(f"https://www.youtube.com/watch?v={video_id}")

if __name__ == "__main__":
    main()