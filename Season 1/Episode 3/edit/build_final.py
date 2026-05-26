"""EP03 final render — title card + season badge + TA image slideshow + subtitles.

The TA images (ta1-ta5) appear fullscreen after the badge animation finishes,
1.5s each with quick fade transitions, like flicking through photos.

Usage:
    python build_final.py --title-at 0.5 --badge-at 5 --episode 3
"""
import argparse
import os
import subprocess
import json
import sys
from PIL import Image, ImageOps
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

BASE_VIDEO = os.path.join(SCRIPT_DIR, "cut_no_subs.mp4")
SUBS_FILE = os.path.join(SCRIPT_DIR, "subs.ass")
TITLE_CARD = os.path.join(PROJECT_ROOT, "Assets", "Webdune Diaries Title - White Text.png")
FONTS_DIR = os.path.join(PROJECT_ROOT, "Assets", "fonts")
TICKER_FRAMES = os.path.join(SCRIPT_DIR, "animations", "ticker", "positioned")

OUTPUT_OVERLAYS = os.path.join(SCRIPT_DIR, "with_overlays.mp4")
OUTPUT_FINAL = os.path.join(SCRIPT_DIR, "final.mp4")

TITLE_SCALE_W = 900
TITLE_Y = 130
TITLE_FADE_IN = 0.5
TITLE_HOLD = 2.0
TITLE_FADE_OUT = 0.5
BADGE_FPS = 30

SCALE_FILTER = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"

TA_IMAGES = [
    os.path.join(SCRIPT_DIR, "ta1.jpeg"),
    os.path.join(SCRIPT_DIR, "ta2.jpeg"),
    os.path.join(SCRIPT_DIR, "ta3.jpg"),
    os.path.join(SCRIPT_DIR, "ta4.jpg"),
    os.path.join(SCRIPT_DIR, "ta5.jpeg"),
]
TA_DURATION = 1.5
TA_FADE = 0.2
TA_GAP_AFTER_BADGE = 1.0


def escape_path(path):
    return path.replace("\\", "/").replace(":", "\\:")


def count_badge_frames():
    if not os.path.isdir(TICKER_FRAMES):
        return 0
    return len([f for f in os.listdir(TICKER_FRAMES) if f.endswith(".png")])


TA_SLIDESHOW_VIDEO = os.path.join(SCRIPT_DIR, "ta_slideshow.mp4")
FPS = 30


def prerender_ta_slideshow(ta_images):
    """Render the TA slideshow as a standalone video: images on black with fades."""
    total_dur = len(ta_images) * TA_DURATION
    total_frames = int(total_dur * FPS)

    imgs = []
    for p in ta_images:
        img = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        w, h = img.size
        scale = min(1080 / w, 1920 / h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new("RGB", (1080, 1920), (0, 0, 0))
        canvas.paste(img, ((1080 - new_w) // 2, (1920 - new_h) // 2))
        imgs.append(np.array(canvas))

    black = np.zeros((1920, 1080, 3), dtype=np.uint8)
    frames_dir = os.path.join(SCRIPT_DIR, "ta_frames")
    os.makedirs(frames_dir, exist_ok=True)

    for fi in range(total_frames):
        t = fi / FPS
        img_idx = min(int(t / TA_DURATION), len(imgs) - 1)
        img_t = t - img_idx * TA_DURATION

        if img_t < TA_FADE:
            alpha = img_t / TA_FADE
        elif img_t > TA_DURATION - TA_FADE:
            alpha = (TA_DURATION - img_t) / TA_FADE
        else:
            alpha = 1.0
        alpha = max(0.0, min(1.0, alpha))

        frame = (black * (1 - alpha) + imgs[img_idx] * alpha).astype(np.uint8)
        Image.fromarray(frame).save(os.path.join(frames_dir, f"ta_{fi:04d}.png"))

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "ta_%04d.png"),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p",
        TA_SLIDESHOW_VIDEO,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR rendering TA slideshow: {result.stderr[-400:]}")
        sys.exit(1)

    print(f"  TA slideshow video: {total_dur:.1f}s ({len(ta_images)} images)")
    return total_dur


def build_overlay_cmd(title_at, badge_at, badge_frame_count, ta_start):
    ta_images = [p for p in TA_IMAGES if os.path.exists(p)]
    has_slideshow = len(ta_images) > 0 and os.path.exists(TA_SLIDESHOW_VIDEO)

    inputs = ["-i", BASE_VIDEO]
    filters = []
    input_idx = 1
    total_overlays = 1 + (1 if badge_frame_count > 0 else 0) + (1 if has_slideshow else 0)
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

    # TA slideshow (pre-rendered opaque video)
    if has_slideshow:
        inputs += ["-itsoffset", str(ta_start), "-i", TA_SLIDESHOW_VIDEO]
        filters.append(f"[{input_idx}:v]scale=1080:1920[taslide]")
        ol = out_label()
        filters.append(f"[{prev}][taslide]overlay=0:0:eof_action=pass[{ol}]")
        prev = ol
        input_idx += 1

    ta_end = ta_start + len(ta_images) * TA_DURATION
    print(f"  TA slideshow: {ta_start:.1f}s - {ta_end:.1f}s ({len(ta_images)} images)")

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
    parser = argparse.ArgumentParser(description="EP03 final render")
    parser.add_argument("--title-at", type=float, required=True)
    parser.add_argument("--badge-at", type=float, required=True)
    parser.add_argument("--episode", type=int, default=3)
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

    badge_dur = badge_frames / BADGE_FPS if badge_frames > 0 else 0
    print("=" * 60)
    print("EP03 Final Render")
    print(f"  Title at: {args.title_at}s")
    print(f"  Badge at: {args.badge_at}s ({badge_frames} frames, {badge_dur:.1f}s)")
    ta_start = args.badge_at + badge_dur + TA_GAP_AFTER_BADGE
    print(f"  TA slideshow starts at: {ta_start:.1f}s ({len(TA_IMAGES)} images x {TA_DURATION}s)")
    print("=" * 60)

    # Pre-render TA slideshow
    ta_images = [p for p in TA_IMAGES if os.path.exists(p)]
    if ta_images:
        print("\nStep 1: Pre-rendering TA slideshow...")
        prerender_ta_slideshow(ta_images)
    else:
        print("\n  WARNING: No TA images found, skipping slideshow")

    # Composite overlays
    print("\nStep 2: Compositing overlays...")
    cmd = build_overlay_cmd(args.title_at, args.badge_at, badge_frames, ta_start)
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
