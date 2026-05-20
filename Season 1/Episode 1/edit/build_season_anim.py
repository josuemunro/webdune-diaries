"""
Generate season animation: static badge with episode number counting up from 000 to 001.
Uses the no-episode-text badge as base, overlays the counter text.
Output: PNG sequence -> ffmpeg concat -> transparent overlay video.
"""
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
BADGE_PATH = os.path.join(PROJECT_ROOT, "Assets", "Animated Season Title - Static, no episode text.png")
FONT_PATH = os.path.join(PROJECT_ROOT, "Assets", "fonts", "Figtree-SemiBold.ttf")
FRAMES_DIR = os.path.join(SCRIPT_DIR, "animations", "season_badge")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "animations", "season_overlay.mp4")

FPS = 30
HOLD_BEFORE = 0.5      # seconds to show badge with no number
COUNT_DURATION = 0.8    # seconds for 000 -> 001 tick
HOLD_AFTER = 1.5        # seconds to hold final 001
FADE_OUT = 0.5          # seconds to fade out

TOTAL_DURATION = HOLD_BEFORE + COUNT_DURATION + HOLD_AFTER + FADE_OUT
TOTAL_FRAMES = int(TOTAL_DURATION * FPS)

# Episode number text positioning (determined from the static reference)
# The pill/rounded rect is roughly centred in the badge
# Badge is 528x463, the text area is roughly centred at y~290, x~264
TEXT_X = 264
TEXT_Y = 262
FONT_SIZE = 76


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def main():
    os.makedirs(FRAMES_DIR, exist_ok=True)

    badge = Image.open(BADGE_PATH).convert("RGBA")

    # Check if we have Figtree Bold - fall back to SemiBold
    bold_path = FONT_PATH.replace("SemiBold", "Bold")
    if os.path.exists(bold_path):
        font = ImageFont.truetype(bold_path, FONT_SIZE)
    else:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    frame_hold_before = int(HOLD_BEFORE * FPS)
    frame_count_end = int((HOLD_BEFORE + COUNT_DURATION) * FPS)
    frame_hold_end = int((HOLD_BEFORE + COUNT_DURATION + HOLD_AFTER) * FPS)

    for frame_idx in range(TOTAL_FRAMES):
        t = frame_idx / FPS
        img = badge.copy()
        draw = ImageDraw.Draw(img)

        # Determine what number to show
        if frame_idx < frame_hold_before:
            # No number yet, just the badge
            number_text = None
        elif frame_idx < frame_count_end:
            # Counting phase: tick through numbers with easing
            progress = (frame_idx - frame_hold_before) / (frame_count_end - frame_hold_before)
            eased = ease_out_cubic(progress)
            # Map eased progress to 0-1 (the episode number)
            current_num = int(eased * 1)
            number_text = f"{current_num:03d}"
        else:
            number_text = "001"

        if number_text is not None:
            # Measure text for centering
            bbox = draw.textbbox((0, 0), number_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            x = TEXT_X - text_w // 2
            y = TEXT_Y - text_h // 2

            # Draw text with dark color to match the badge style
            draw.text((x, y), number_text, fill=(51, 51, 51, 255), font=font)

        # Apply fade out in last phase
        if frame_idx >= frame_hold_end:
            fade_progress = (frame_idx - frame_hold_end) / (TOTAL_FRAMES - frame_hold_end)
            alpha = int(255 * (1 - fade_progress))
            # Apply alpha to entire image
            r, g, b, a = img.split()
            a = a.point(lambda p: int(p * alpha / 255))
            img = Image.merge("RGBA", (r, g, b, a))

        img.save(os.path.join(FRAMES_DIR, f"frame_{frame_idx:04d}.png"))

    print(f"Generated {TOTAL_FRAMES} frames ({TOTAL_DURATION:.1f}s at {FPS}fps)")

    # Render to video with alpha channel (using qtrle for transparency)
    # Actually, render as regular MP4 with green screen, then use chromakey
    # Better approach: render as MOV with alpha, or just render positioned on transparent
    # Simplest: render as regular video and overlay in final composite

    # For overlay purposes, render the badge centered on a 1080x1920 transparent canvas
    print("Rendering to full-frame positioned PNGs...")
    positioned_dir = os.path.join(FRAMES_DIR, "positioned")
    os.makedirs(positioned_dir, exist_ok=True)

    for frame_idx in range(TOTAL_FRAMES):
        frame_path = os.path.join(FRAMES_DIR, f"frame_{frame_idx:04d}.png")
        badge_frame = Image.open(frame_path).convert("RGBA")

        # Scale badge to fit nicely — roughly 60% of frame width
        target_w = 640
        scale = target_w / badge_frame.width
        target_h = int(badge_frame.height * scale)
        badge_scaled = badge_frame.resize((target_w, target_h), Image.LANCZOS)

        # Create full-frame canvas
        canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))

        # Position: centered horizontally, in the upper area (below title card area)
        x = (1080 - target_w) // 2
        y = 180  # below the title card position
        canvas.paste(badge_scaled, (x, y), badge_scaled)
        canvas.save(os.path.join(positioned_dir, f"frame_{frame_idx:04d}.png"))

    # Encode as video
    print("Encoding overlay video...")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(positioned_dir, "frame_%04d.png"),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        OUTPUT_PATH
    ]
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr[-300:]}")
        return

    # Verify
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", OUTPUT_PATH],
        capture_output=True, text=True
    )
    import json
    info = json.loads(probe.stdout)
    dur = float(info["format"]["duration"])
    print(f"Season overlay: {dur:.1f}s, saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
