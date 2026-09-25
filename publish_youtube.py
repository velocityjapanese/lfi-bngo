"""
YouTube Upload & Thumbnail Publishing Module for Lofi Bingoo
Uses OAuth 2.0 refresh token to upload 1-hour 1080p HD Lofi Music videos and set custom thumbnails.
"""
import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()


def get_authenticated_service():
    """Authenticate using refresh token from environment variables or local token file."""
    client_id = (os.getenv("YOUTUBE_CLIENT_ID") or os.getenv("YT_CLIENT_ID", "")).strip()
    client_secret = (os.getenv("YOUTUBE_CLIENT_SECRET") or os.getenv("YT_CLIENT_SECRET", "")).strip()
    refresh_token = (os.getenv("YOUTUBE_REFRESH_TOKEN") or os.getenv("YT_REFRESH_TOKEN", "")).strip()
    token_uri = os.getenv("YOUTUBE_TOKEN_URI", "https://oauth2.googleapis.com/token").strip()

    if not all([client_id, client_secret, refresh_token]) or "your_" in client_id:
        possible_token_paths = [
            Path(__file__).parent / "token_lofi bingoo.json",
            Path(__file__).parent / "token_lofibingoo.json",
            Path(r"C:\Users\kreg9\Downloads\kreggscode\open code\bots\youtube refresh tokens bot\token_lofi bingoo.json"),
        ]
        for p in possible_token_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        client_id = data.get("client_id", "")
                        client_secret = data.get("client_secret", "")
                        refresh_token = data.get("refresh_token", "")
                        token_uri = data.get("token_uri", token_uri)
                        print(f"[youtube] Loaded credentials from: {p.name}")
                        break
                except Exception as e:
                    print(f"[youtube] Error reading {p}: {e}")

    def mask(s):
        return f"{s[:4]}...{s[-4:]}" if s and len(s) > 8 else "MISSING"

    print(f"[youtube] Client ID: {mask(client_id)}")
    print(f"[youtube] Client Secret: {mask(client_secret)}")
    print(f"[youtube] Refresh Token: {mask(refresh_token)}")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            "Missing YouTube credentials! Set YT_CLIENT_ID, YT_CLIENT_SECRET, and YT_REFRESH_TOKEN."
        )

    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube"]
    )

    try:
        creds.refresh(Request())
    except Exception as e:
        if "invalid_grant" in str(e).lower():
            print("\n❌ [youtube] AUTH ERROR: Refresh token has EXPIRED or been REVOKED.")
        raise

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(video_path, title, description, tags=None, category_id="10", privacy_status="public"):
    """
    Uploads a long-form video to YouTube.
    Category 10 = Music
    """
    if tags is None:
        tags = [
            "lofi", "lofi beats", "study music", "lofi study", "lofi bingoo",
            "relaxing music", "chill beats", "peaceful music", "calm beats",
            "lofi hip hop", "music to study to", "deep focus", "1 hour lofi",
            "sleep beats", "instrumental lofi", "chillhop"
        ]

    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": category_id
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        str(video_path),
        chunksize=10 * 1024 * 1024,
        resumable=True,
        mimetype="video/mp4"
    )

    print(f"[youtube] Uploading Video: {title}")
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  --> Upload progress: {pct}%")

    video_id = response.get("id")
    print(f"[youtube] Upload Complete! Video ID: {video_id}")
    print(f"[youtube] URL: https://youtu.be/{video_id}")
    return video_id


def set_video_thumbnail(video_id, thumbnail_path):
    """Sets custom thumbnail on uploaded YouTube video."""
    if not os.path.exists(thumbnail_path):
        print(f"[youtube] Thumbnail path not found: {thumbnail_path}")
        return False

    youtube = get_authenticated_service()
    print(f"[youtube] Setting custom thumbnail for Video ID: {video_id}...")
    try:
        media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
        youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
        print("[youtube] Thumbnail successfully set!")
        return True
    except Exception as e:
        print(f"[youtube] Failed to set thumbnail: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 3:
        upload_to_youtube(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python publish_youtube.py <video_path> <title> <description>")
