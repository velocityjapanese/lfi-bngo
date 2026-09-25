"""
Lofi Bingoo YouTube Thumbnail Generator
- Generates high-CTR lofi music thumbnails (1280x720)
- Automatically detects and removes Gemini / Google Flow AI watermarks via OpenCV inpainting
- Clean, aesthetic typography (Cinzel / Playfair)
- Rich cozy lofi atmosphere, warm golden tones, and 1-Hour badge
"""
import os
import sys
import random
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

LOFI_HOOKS = [
    {"main": "COZY LOFI BEATS", "sub": "RELAXING STUDY & CHILL MUSIC", "badge": "1 HOUR · 1080p HD"},
    {"main": "PEACEFUL STUDY VIBES", "sub": "CALM LOFI MUSIC FOR DEEP FOCUS", "badge": "LOFI BINGOO · 1 HOUR"},
    {"main": "AUTUMN RAIN & CHILL", "sub": "SOOTHING BEATS TO WORK & RELAX", "badge": "DEEP FOCUS · 1 HOUR"},
    {"main": "COZY BEDROOM DREAMS", "sub": "CALMING LOFI HIP HOP FOR SLEEP", "badge": "1080p HD · 1 HOUR"},
    {"main": "MIDNIGHT STUDY SESSION", "sub": "STRESS RELIEF & PEACEFUL CHILLOUT", "badge": "STUDY & CHILL · 1 HOUR"},
    {"main": "GENTLE MORNING COFFEE", "sub": "MELLOW LOFI CHILLOUT SOUNDS", "badge": "RELAX & BREATHE · 1 HOUR"},
    {"main": "SUNLIT WINDOW SILL", "sub": "GENTLE COZY LOFI MELODIES", "badge": "1 HOUR · 1080p HD"},
    {"main": "PAWS & RAIN DROPS", "sub": "TRANQUIL AMBIENT LOFI SOUNDSCAPE", "badge": "DEEP CHILL · 1 HOUR"}
]


def remove_watermark(cv_img):
    """
    Removes Google Flow / Gemini AI 4-pointed star watermarks in the bottom-right corner
    using precise astroid geometry and Telea inpainting.
    """
    h, w = cv_img.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    p = 0.65

    # Target candidate centers for Google Flow image and video watermarks:
    # 1. Native image location (ratios 0.9317, 0.875)
    # 2. Converted video location (ratios 0.9023, 0.8264)
    centers = [
        (int(w * 0.9317), int(h * 0.875), int(h * 0.052)),
        (int(w * 0.9023), int(h * 0.8264), int(h * 0.050))
    ]

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

    return cv2.inpaint(cv_img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)


def apply_3d_lut(cv_img, lut_path=None):
    """Applies the Cinematic 3D LUT (lofi_cinematic.cube) to a CV2 image."""
    if lut_path is None:
        lut_path = os.path.join(SCRIPT_DIR, "assets", "luts", "lofi_cinematic.cube")
    if not os.path.exists(lut_path):
        return cv_img

    temp_in = os.path.join(SCRIPT_DIR, "temp_lut_thumb_in.png")
    temp_out = os.path.join(SCRIPT_DIR, "temp_lut_thumb_out.png")
    try:
        cv2.imwrite(temp_in, cv_img)
        safe_lut = lut_path.replace("\\", "/").replace(":", "\\:")
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-i", temp_in,
            "-vf", f"lut3d=file='{safe_lut}':interp=tetrahedral",
            temp_out
        ]
        subprocess.run(cmd, check=True)
        graded = cv2.imread(temp_out)
        return graded if graded is not None else cv_img
    except Exception as e:
        print(f"[THUMBNAIL] 3D LUT notice: {e}")
        return cv_img
    finally:
        for t in [temp_in, temp_out]:
            if os.path.exists(t):
                try:
                    os.remove(t)
                except Exception:
                    pass


def get_font(font_name="Cinzel.ttf", size=56):
    """Load font with fallback hierarchy."""
    font_path = os.path.join(SCRIPT_DIR, "assets", "fonts", font_name)
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass

    pf = os.path.join(SCRIPT_DIR, "assets", "fonts", "PlayfairDisplay.ttf")
    if os.path.exists(pf):
        try:
            return ImageFont.truetype(pf, size)
        except Exception:
            pass

    # System fonts fallback
    for f in [r"C:\Windows\Fonts\georgiab.ttf", r"C:\Windows\Fonts\georgia.ttf", r"C:\Windows\Fonts\arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass

    return ImageFont.load_default()


def apply_cozy_vignette(img, intensity=0.25):
    """Applies a rich cinematic vignette to frame cozy visuals."""
    W, H = img.size
    mask = Image.new("L", (W, H), 0)
    draw_m = ImageDraw.Draw(mask)
    draw_m.ellipse([-W * 0.15, -H * 0.15, W * 1.15, H * 1.15], fill=int(255 * (1.0 - intensity)))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=int(W * 0.07)))
    dark = Image.new("RGBA", (W, H), (15, 12, 20, 255))
    return Image.composite(img, dark, mask)


def create_lofi_thumbnail(bg_path, output_path, main_text=None, sub_text=None, badge_text=None):
    """
    Creates a clean, high-converting Lofi Study Music YouTube thumbnail (1280x720)
    with watermark removal, Cinematic 3D LUT color grading, and centered typography.
    """
    if not main_text:
        preset = random.choice(LOFI_HOOKS)
        main_text = preset["main"]
        sub_text = preset["sub"]
        badge_text = preset.get("badge", "1 HOUR · 1080p HD")
    elif not badge_text:
        badge_text = "1 HOUR · 1080p HD"

    # 1. Load image, inpaint watermark, and apply Cinematic 3D LUT
    cv_img = cv2.imread(bg_path)
    if cv_img is not None:
        clean_cv = remove_watermark(cv_img)
        graded_cv = apply_3d_lut(clean_cv)
        rgb_img = cv2.cvtColor(graded_cv, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_img).convert("RGBA")
    else:
        img = Image.open(bg_path).convert("RGBA")

    target_w, target_h = 1280, 720
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h

    if img_ratio > target_ratio:
        new_w = int(img.height * target_ratio)
        offset = (img.width - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, img.height))
    else:
        new_h = int(img.width / target_ratio)
        offset = (img.height - new_h) // 2
        img = img.crop((0, offset, img.width, offset + new_h))

    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # 2. Add vignette
    img = apply_cozy_vignette(img, intensity=0.25)

    # 3. Create text overlay
    overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_main = get_font("Cinzel.ttf", size=62)
    font_sub = get_font("PlayfairDisplay.ttf", size=28)
    font_badge = get_font("Cinzel.ttf", size=24)

    # Bottom-left typography layout
    x_pos = 70
    y_base = target_h - 165

    # Subtitle
    if sub_text:
        for dx, dy in [(-2, 2), (2, 2), (0, 2), (2, 0), (-1, -1)]:
            draw.text((x_pos + dx, y_base - 40 + dy), sub_text.upper(), font=font_badge, fill=(0, 0, 0, 230))
        draw.text((x_pos, y_base - 40), sub_text.upper(), font=font_badge, fill=(255, 230, 160, 255))

    # Main Headline
    for dx, dy in [(-3, 3), (3, 3), (0, 4), (4, 4), (-2, -2), (2, -2)]:
        draw.text((x_pos + dx, y_base + dy), main_text.upper(), font=font_main, fill=(0, 0, 0, 240))
    draw.text((x_pos, y_base), main_text.upper(), font=font_main, fill=(255, 255, 255, 255))

    # Top-Right Badge (Centered perfectly with anchor='mm')
    bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    padding_x = 22
    padding_y = 12
    box_w = text_w + padding_x * 2
    box_h = text_h + padding_y * 2

    box_x2 = target_w - 60
    box_x1 = box_x2 - box_w
    box_y1 = 45
    box_y2 = box_y1 + box_h

    draw.rounded_rectangle(
        [box_x1, box_y1, box_x2, box_y2],
        radius=12,
        fill=(18, 14, 25, 210),
        outline=(255, 205, 110, 220),
        width=2
    )

    badge_cx = (box_x1 + box_x2) / 2
    badge_cy = (box_y1 + box_y2) / 2
    draw.text((badge_cx, badge_cy), badge_text, font=font_badge, fill=(255, 245, 215, 255), anchor="mm")

    final = Image.alpha_composite(img, overlay).convert("RGB")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    final.save(output_path, quality=96)
    print(f"[+] Generated Lofi Thumbnail (Watermark Removed): {output_path}")
    return output_path


# Alias for compatibility
create_tropical_thumbnail = create_lofi_thumbnail
TROPICAL_HOOKS = LOFI_HOOKS


if __name__ == "__main__":
    if len(sys.argv) > 2:
        create_lofi_thumbnail(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python thumbnail_generator.py <input_image> <output_thumbnail>")
