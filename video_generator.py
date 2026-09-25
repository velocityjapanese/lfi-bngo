"""
Lofi Bingoo YouTube Long-Form Video Generator
- Detects video resolution and auto-upscales 720p to 1080p Full HD (Lanczos + Unsharp)
- Automatically removes Google Flow / Gemini AI watermarks in the bottom-right corner
- Builds seamless ping-pong loop blocks (Forward + Reverse = 100% smooth continuous flow)
- Synchronizes and loops high-fidelity lofi audio tracks with smooth fade-out
- Automatically utilizes NVIDIA NVENC GPU hardware acceleration with libx264 CPU fallback
- Supports configurable duration (e.g., 20-minute test or 1-hour full video)
"""
import os
import sys
import json
import subprocess
import cv2
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_media_info(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=width,height,codec_name:format=duration",
        "-of", "json", str(file_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    duration = float(data.get("format", {}).get("duration", 0))
    v_stream = next((s for s in data.get("streams", []) if s.get("width")), None)
    width = int(v_stream["width"]) if v_stream else 1920
    height = int(v_stream["height"]) if v_stream else 1080
    return width, height, duration


def is_nvenc_available():
    try:
        res = subprocess.run(
            ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=24", "-c:v", "h264_nvenc", "-f", "null", "-"],
            capture_output=True, text=True
        )
        return res.returncode == 0
    except Exception:
        return False


def inpaint_video_watermark(input_video, output_video):
    """
    Removes Google Flow / Gemini AI 4-pointed star watermarks across all frames
    using high-precision astroid geometry and Telea inpainting.
    Ultra fast: runs at 100+ fps (~2 seconds for a 10s loop).
    """
    cap = cv2.VideoCapture(str(input_video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    p = 0.65
    centers = [
        (int(w * 0.9023), int(h * 0.8264), int(h * 0.050)),
        (int(w * 0.9317), int(h * 0.8750), int(h * 0.052))
    ]

    mask = np.zeros((h, w), dtype=np.uint8)
    kernel = np.ones((5, 5), np.uint8)
    for cx, cy, r in centers:
        y_min, y_max = max(0, cy - r - 15), min(h, cy + r + 15)
        x_min, x_max = max(0, cx - r - 15), min(w, cx + r + 15)
        vy, vx = np.ogrid[y_min:y_max, x_min:x_max]
        vdist = (np.abs(vx - cx) / r) ** p + (np.abs(vy - cy) / r) ** p
        mask_roi = np.zeros((y_max - y_min, x_max - x_min), dtype=np.uint8)
        mask_roi[vdist <= 1.0] = 255
        mask_roi = cv2.dilate(mask_roi, kernel, iterations=1)
        mask[y_min:y_max, x_min:x_max] = np.maximum(mask[y_min:y_max, x_min:x_max], mask_roi)

    nz = cv2.findNonZero(mask)
    if nz is not None:
        bx, by, bw, bh = cv2.boundingRect(nz)
    else:
        bx, by, bw, bh = 0, 0, w, h

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_video), fourcc, fps, (w, h))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        roi_frame = frame[by:by+bh, bx:bx+bw]
        roi_mask = mask[by:by+bh, bx:bx+bw]
        frame[by:by+bh, bx:bx+bw] = cv2.inpaint(roi_frame, roi_mask, 3, cv2.INPAINT_TELEA)
        out.write(frame)

    cap.release()
    out.release()
    return output_video


def get_video_filter_chain(width, height, upscale_to_1080p=True, apply_color_grade=True):
    filters = []

    # 1. 3D LUT Cinematic Lofi Color Grading
    lut_path = os.path.join(SCRIPT_DIR, "assets", "luts", "lofi_cinematic.cube")
    if apply_color_grade and os.path.exists(lut_path):
        print("[VIDEO] Applying Cinematic 3D LUT color grading (warm cozy aesthetic)...")
        safe_lut = lut_path.replace("\\", "/").replace(":", "\\:")
        filters.append(f"lut3d=file='{safe_lut}':interp=tetrahedral")

    # 2. High Quality 1080p Upscaling (if input is 720p or lower)
    if upscale_to_1080p and (width < 1920 or height < 1080):
        print(f"[VIDEO] Auto-upscaling from {width}x{height} to 1920x1080 Full HD (Lanczos + Unsharp)...")
        filters.append("scale=1920:1080:flags=lanczos+accurate_rnd")
        filters.append("unsharp=5:5:0.8:5:5:0.0")

    return ",".join(filters) if filters else "null"


def build_lofi_longform_video(input_video, input_audio, output_path, duration_seconds=3600, remove_watermark=True, upscale_to_1080p=True, apply_color_grade=True):
    """
    Main entry point to render 1080p HD Lofi Music video with watermark removal,
    cinematic 3D LUT color grading, and seamless ping-pong loop.
    """
    print("\n" + "=" * 60)
    print("RENDERING LOFI BINGOO VIDEO (WATERMARK REMOVAL & 3D LUT ACTIVE)")
    print("=" * 60)
    print(f"  Input Video: {os.path.basename(input_video)}")
    print(f"  Input Audio: {os.path.basename(input_audio)}")
    print(f"  Target Duration: {duration_seconds}s ({duration_seconds / 60:.1f} mins)")
    print(f"  Output Path: {output_path}")

    temp_inpaint = os.path.join(SCRIPT_DIR, "temp_inpaint.mp4")
    temp_clean = os.path.join(SCRIPT_DIR, "temp_clean.mp4")
    temp_block = os.path.join(SCRIPT_DIR, "temp_block.mp4")

    # Step 1: Remove watermark via Astroid inpaint & Upscale + Color Grade
    source_to_upscale = input_video
    if remove_watermark:
        print("[VIDEO] Applying high-precision astroid inpainting to remove Google Flow watermark...")
        inpaint_video_watermark(input_video, temp_inpaint)
        source_to_upscale = temp_inpaint

    w, h, orig_dur = get_media_info(source_to_upscale)
    vf_arg = get_video_filter_chain(w, h, upscale_to_1080p=upscale_to_1080p, apply_color_grade=apply_color_grade)

    cmd_clean = [
        "ffmpeg", "-y",
        "-i", str(source_to_upscale),
        "-vf", vf_arg,
        "-c:v", "libx264", "-crf", "15", "-preset", "fast", "-an",
        temp_clean
    ]
    subprocess.run(cmd_clean, check=True)

    # Step 2: Create ping-pong loop block (Forward + Reverse = seamless continuous flow)
    cmd_block = [
        "ffmpeg", "-y",
        "-i", temp_clean,
        "-filter_complex", "[0:v]reverse[v_rev];[0:v][v_rev]concat=n=2:v=1:a=0[v_out]",
        "-map", "[v_out]",
        "-c:v", "libx264", "-crf", "15", "-preset", "fast",
        temp_block
    ]
    subprocess.run(cmd_block, check=True)

    _, _, block_dur = get_media_info(temp_block)
    loop_count = int(duration_seconds / max(block_dur, 1)) + 2
    fade_start = max(0, duration_seconds - 4)

    # Check encoder
    if is_nvenc_available():
        print("[VIDEO] Using NVIDIA NVENC Hardware Acceleration...")
        video_codec_args = ["-c:v", "h264_nvenc", "-cq", "19", "-b:v", "14M"]
    else:
        print("[VIDEO] Using CPU libx264 encoder (veryfast preset)...")
        video_codec_args = ["-c:v", "libx264", "-crf", "18", "-preset", "veryfast"]

    # Step 3: Full assemble with audio loop and fade out
    print("[VIDEO] Assembling full 1080p video with audio synchronization...")
    cmd_full = [
        "ffmpeg", "-y",
        "-stream_loop", str(loop_count), "-i", temp_block,
        "-stream_loop", "-1", "-i", str(input_audio),
        "-filter_complex", (
            f"[0:v]trim=0:{duration_seconds},setpts=PTS-STARTPTS,fade=t=out:st={fade_start}:d=4[v_out];"
            f"[1:a]atrim=0:{duration_seconds},asetpts=PTS-STARTPTS,afade=t=out:st={fade_start}:d=4[a_out]"
        ),
        "-map", "[v_out]",
        "-map", "[a_out]",
        *video_codec_args,
        "-c:a", "aac", "-b:a", "320k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path)
    ]

    try:
        subprocess.run(cmd_full, check=True)
    except subprocess.CalledProcessError:
        print("[!] NVENC failed or unavailable, falling back to libx264 CPU encoder...")
        cmd_full_cpu = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_count), "-i", temp_block,
            "-stream_loop", "-1", "-i", str(input_audio),
            "-filter_complex", (
                f"[0:v]trim=0:{duration_seconds},setpts=PTS-STARTPTS,fade=t=out:st={fade_start}:d=4[v_out];"
                f"[1:a]atrim=0:{duration_seconds},asetpts=PTS-STARTPTS,afade=t=out:st={fade_start}:d=4[a_out]"
            ),
            "-map", "[v_out]",
            "-map", "[a_out]",
            "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "320k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path)
        ]
        subprocess.run(cmd_full_cpu, check=True)

    # Cleanup temp
    for t in [temp_inpaint, temp_clean, temp_block]:
        if os.path.exists(t):
            try:
                os.remove(t)
            except Exception:
                pass

    print(f"[SUCCESS] 1080p Video rendered successfully (Watermark Removed): {output_path}")
    return True


# Alias for cross-module compatibility
build_tropical_longform_video = build_lofi_longform_video
