"""
CLI Video Generator Utility for Lofi Bingoo
- Easily test and render custom durations (e.g. 1-hour full render or custom preview)
- Auto-upscales 720p to 1080p Full HD (Lanczos + Unsharp)
- Seamless ping-pong loop units with lofi study music audio synchronization
"""
import os
import sys
import argparse
from video_generator import build_lofi_longform_video

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description="Lofi Bingoo Video Renderer")
    parser.add_argument("--duration", type=int, default=3600, help="Target duration in seconds (3600 for 1h, 300 for 5m)")
    parser.add_argument("--video", type=str, default=None, help="Path to input video MP4")
    parser.add_argument("--audio", type=str, default=None, help="Path to input audio MP3")
    parser.add_argument("--output", type=str, default=None, help="Path to output video MP4")
    args = parser.parse_args()

    # Look for local video or download from drive
    vid_dir = os.path.join(SCRIPT_DIR, "input_videos")
    aud_dir = os.path.join(SCRIPT_DIR, "input_audio")

    vids = [os.path.join(vid_dir, f) for f in os.listdir(vid_dir) if f.endswith(".mp4")] if os.path.exists(vid_dir) else []
    auds = [os.path.join(aud_dir, f) for f in os.listdir(aud_dir) if f.endswith(".mp3")] if os.path.exists(aud_dir) else []

    vid_path = args.video or (vids[0] if vids else None)
    aud_path = args.audio or (auds[0] if auds else None)

    if not vid_path or not aud_path:
        from google_drive_fetch import fetch_assets_triplet
        print("[INIT] Fetching assets from Google Drive...")
        v, a, i, _ = fetch_assets_triplet(allow_repost=True)
        vid_path = args.video or v
        aud_path = args.audio or a

    dur_label = f"{args.duration // 60}min" if args.duration >= 60 else f"{args.duration}s"
    safe_name = os.path.splitext(os.path.basename(aud_path))[0].replace(" ", "_")

    out_dir = os.path.join(SCRIPT_DIR, "output_videos")
    os.makedirs(out_dir, exist_ok=True)
    out_path = args.output or os.path.join(out_dir, f"LofiBingoo_{safe_name}_{dur_label}.mp4")

    build_lofi_longform_video(
        input_video=vid_path,
        input_audio=aud_path,
        output_path=out_path,
        duration_seconds=args.duration,
        remove_watermark=True,
        upscale_to_1080p=True
    )


if __name__ == "__main__":
    main()
