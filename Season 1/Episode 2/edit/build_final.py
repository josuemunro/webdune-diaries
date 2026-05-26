"""EP02 final render — title card + season badge + image overlays + subtitles.

Usage:
    python build_final.py --title-at 2 --badge-at 12.5 --episode 2
"""
import argparse
import os
import subprocess
import json
import sys
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
EP_DIR = os.path.dirname(SCRIPT_DIR)

BASE_VIDEO = os.path.join(SCRIPT_DIR, "cut_no_subs.mp4")
SUBS_FILE = os.path.join(SCRIPT_DIR, "subs.ass")
TITLE_CARD = os.path.join(PROJECT_ROOT, "Assets", "Webdune Diaries Title - White Text.png")
FONTS_DIR = os.path.join(PROJECT_ROOT, "Assets", "fonts")
FONT_FILE = os.path.join(FONTS_DIR, "Figtree-SemiBold.ttf")
TICKER_FRAMES = os.path.join(SCRIPT_DIR, "animations", "ticker", "positioned")

OUTPUT_OVERLAYS = os.path.join(SCRIPT_DIR, "with_overlays.mp4")
OUTPUT_FINAL = os.path.join(SCRIPT_DIR, "final.mp4")

TITLE_SCALE_W = 900
TITLE_Y = 130
TITLE_FADE_IN = 1.5
TITLE_HOLD = 2.0
TITLE_FADE_OUT = 1.0
BADGE_FPS = 30
IMAGE_FADE = 0.3

SCALE_FILTER = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"

IMAGE_OVERLAYS = [
    {
        "name": "me and max",
        "path": os.path.join(EP_DIR, "me and max.jpg"),
        "start": 20.5, "end": 23.5,
        "caption": None,
    },
    {
        "name": "josi courier",
        "path": os.path.join(EP_DIR, "josi courier.jpg"),
        "start": 51.5, "end": 53.5,
        "caption": None,
    },
    {
        "name": "site screenshot",
        "path": os.path.join(EP_DIR, "one of the two sites I got paid peanutes on.png"),
        "start": 62.5, "end": 65.5,
        "caption": "what a banger of a site to get paid $2/hr for",
    },
]


def escape_path(path):
    return path.replace("\\", "/").replace(":", "\\:")


def count_badge_frames():
    if not os.path.isdir(TICKER_FRAMES):
        return 0
    return len([f for f in os.listdir(TICKER_FRAMES) if f.endswith(".png")])


def prerender_captioned_image(image_path, caption, output_path):
    img = Image.open(image_path).convert("RGB")
    canvas = Image.new("RGB", (1080, 1920), (0, 0, 0))

    max_w, max_h = 1000, 1400
    ratio = min(max_w / img.width, max_h / img.height)
    new_w, new_h = int(img.width * ratio), int(img.height * ratio)
    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    x = (1080 - new_w) // 2
    y = (1920 - new_h) // 2 - 80
    canvas.paste(img_resized, (x, y))

    if caption:
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype(FONT_FILE, 38)
        bbox = draw.textbbox((0, 0), caption, font=font)
        text_w = bbox[2] - bbox[0]
        text_x = (1080 - text_w) // 2
        text_y = y + new_h + 40
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx * dx + dy * dy <= 9:
                    draw.text((text_x + dx, text_y + dy), caption, font=font, fill=(0, 0, 0))
        draw.text((text_x, text_y), caption, font=font, fill=(255, 255, 255))

    canvas.save(output_path)


def build_overlay_cmd(title_at, badge_at, badge_frame_count, prepared_images):
    inputs = ["-i", BASE_VIDEO]
    filters = []
    input_idx = 1
    total_overlays = 1 + (1 if badge_frame_count > 0 else 0) + len(prepared_images)
    overlay_num = 0

    def out_label():
        nonlocal overlay_num
        overlay_num += 1
        return "vout" if overlay_num == total_overlays else f"c{overlay_num}"

    # Title card
    inputs += ["-loop", "1", "-i", TITLE_CARD]
    fade_out_start = title_at + TITLE_FADE_IN + TITLE_HOLD
    filters.append(
        f"[{input_idx}:v]scale={TITLE_SCALE_W}:-1,format=rgba,"
        f"fade=in:st={title_at}:d={TITLE_FADE_IN}:alpha=1,"
        f"fade=out:st={fade_out_start}:d={TITLE_FADE_OUT}:alpha=1[title]"
    )
    ol = out_label()
    filters.append(f"[0:v][title]overlay=(W-w)/2:{TITLE_Y}:shortest=1:eof_action=pass[{ol}]")
    prev = ol
    input_idx += 1

    # Badge
    if badge_frame_count > 0:
        inputs += [
            "-itsoffset", str(badge_at),
            "-framerate", str(BADGE_FPS),
            "-i", os.path.join(TICKER_FRAMES, "frame_%04d.png"),
        ]
        filters.append(f"[{input_idx}:v]format=rgba[badge]")
        ol = out_label()
        filters.append(f"[{prev}][badge]overlay=0:0:eof_action=pass[{ol}]")
        prev = ol
        input_idx += 1

    # Image overlays
    for i, img in enumerate(prepared_images):
        inputs += ["-loop", "1", "-i", img["prepared_path"]]
        fade_out = img["end"] - IMAGE_FADE
        img_label = f"img{i}"
        scale = "" if img.get("prerendered") else f"{SCALE_FILTER},"
        filters.append(
            f"[{input_idx}:v]{scale}format=rgba,"
            f"fade=in:st={img['start']}:d={IMAGE_FADE}:alpha=1,"
            f"fade=out:st={fade_out}:d={IMAGE_FADE}:alpha=1[{img_label}]"
        )
        ol = out_label()
        filters.append(f"[{prev}][{img_label}]overlay=0:0:eof_action=pass[{ol}]")
        prev = ol
        input_idx += 1

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", ";".join(filters),
        "-map", "[vout]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "26",
        "-c:a", "copy", "-pix_fmt", "yuv420p",
        OUTPUT_OVERLAYS
    ]
    return cmd


def burn_subtitles():
    subs_escaped = escape_path(SUBS_FILE)
    fonts_escaped = escape_path(FONTS_DIR)
    return [
        "ffmpeg", "-y",
        "-i", OUTPUT_OVERLAYS,
        "-vf", f"subtitles='{subs_escaped}':fontsdir='{fonts_escaped}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "26",
        "-c:a", "copy", "-pix_fmt", "yuv420p",
        OUTPUT_FINAL
    ]


def verify(path):
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True
    )
    info = json.loads(probe.stdout)
    dur = float(info["format"]["duration"])
    size_mb = int(info["format"]["size"]) / (1024 * 1024)
    return dur, size_mb


def main():
    parser = argparse.ArgumentParser(description="EP02 final render")
    parser.add_argument("--title-at", type=float, required=True)
    parser.add_argument("--badge-at", type=float, required=True)
    parser.add_argument("--episode", type=int, default=2)
    parser.add_argument("--skip-ticker", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(BASE_VIDEO):
        print(f"ERROR: {BASE_VIDEO} not found. Run build_edit.py first.")
        sys.exit(1)

    badge_frames = count_badge_frames()
    if badge_frames == 0 and not args.skip_ticker:
        print("No ticker frames found, building...")
        subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "build_ticker.py"),
                        str(args.episode)], check=True)
        badge_frames = count_badge_frames()

    print("=" * 60)
    print("EP02 Final Render")
    print(f"  Title at: {args.title_at}s")
    print(f"  Badge at: {args.badge_at}s ({badge_frames} frames, {badge_frames/BADGE_FPS:.1f}s)")
    print(f"  Image overlays: {len(IMAGE_OVERLAYS)}")
    print("=" * 60)

    # Pre-process captioned images
    print("\nStep 1: Preparing image overlays...")
    clips_dir = os.path.join(SCRIPT_DIR, "clips")
    os.makedirs(clips_dir, exist_ok=True)
    prepared = []
    for img in IMAGE_OVERLAYS:
        if not os.path.exists(img["path"]):
            print(f"  WARNING: {img['name']} not found at {img['path']}, skipping")
            continue
        if img["caption"]:
            prep_path = os.path.join(clips_dir, f"captioned_{img['name'].replace(' ', '_')}.png")
            print(f"  Pre-rendering '{img['name']}' with caption...")
            prerender_captioned_image(img["path"], img["caption"], prep_path)
            prepared.append({**img, "prepared_path": prep_path, "prerendered": True})
        else:
            print(f"  '{img['name']}' at {img['start']}-{img['end']}s")
            prepared.append({**img, "prepared_path": img["path"], "prerendered": False})

    # Composite overlays
    print("\nStep 2: Compositing overlays...")
    cmd = build_overlay_cmd(args.title_at, args.badge_at, badge_frames, prepared)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR compositing overlays:")
        print(result.stderr[-600:])
        sys.exit(1)
    dur, size = verify(OUTPUT_OVERLAYS)
    print(f"  with_overlays.mp4: {dur:.1f}s, {size:.1f} MB")

    # Burn subtitles
    print("\nStep 3: Burning subtitles...")
    cmd = burn_subtitles()
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR burning subtitles:")
        print(result.stderr[-500:])
        print("  Falling back to overlays-only...")
        import shutil
        shutil.copy2(OUTPUT_OVERLAYS, OUTPUT_FINAL)

    dur, size = verify(OUTPUT_FINAL)
    print(f"\n{'=' * 60}")
    print(f"  Output: {OUTPUT_FINAL}")
    print(f"  Duration: {dur:.1f}s, Size: {size:.1f} MB")
    print(f"  Under 90s: {'YES' if dur < 90 else 'NO'}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
