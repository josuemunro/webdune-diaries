"""
Final render: composites title card + season badge animation + subtitles
onto cut_no_subs.mp4.

Title card: fade in/out at a human-specified timestamp.
Season badge: pre-rendered PNG sequence from build_ticker.py.
Subtitles: burned last from subs.ass.

Usage:
    python build_final.py --title-at 14 --badge-at 60
    python build_final.py --title-at 14 --badge-at 60 --episode 1
"""
import argparse
import os
import subprocess
import json
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

BASE_VIDEO = os.path.join(SCRIPT_DIR, "cut_no_subs.mp4")
SUBS_FILE = os.path.join(SCRIPT_DIR, "subs.ass")
TITLE_CARD = os.path.join(PROJECT_ROOT, "Assets", "Webdune Diaries Title - White Text.png")
FONTS_DIR = os.path.join(PROJECT_ROOT, "Assets", "fonts")
TICKER_FRAMES = os.path.join(SCRIPT_DIR, "animations", "ticker", "positioned")

OUTPUT_OVERLAYS = os.path.join(SCRIPT_DIR, "with_overlays.mp4")
OUTPUT_FINAL = os.path.join(SCRIPT_DIR, "final.mp4")

# Title card: 802x277, scaled to fit 1080 wide with padding, positioned at y=130
TITLE_SCALE_W = 900
TITLE_Y = 130

# Title card timing
TITLE_FADE_IN = 1.5
TITLE_HOLD = 2.0
TITLE_FADE_OUT = 1.0
TITLE_TOTAL = TITLE_FADE_IN + TITLE_HOLD + TITLE_FADE_OUT  # 4.5s

# Badge animation: 4.0s at 30fps = 120 frames (from build_ticker.py, includes fades)
BADGE_FPS = 30


def escape_path(path):
    """Escape path for ffmpeg filter strings on Windows."""
    return path.replace("\\", "/").replace(":", "\\:")


def count_badge_frames():
    if not os.path.isdir(TICKER_FRAMES):
        return 0
    return len([f for f in os.listdir(TICKER_FRAMES) if f.endswith(".png")])


def build_overlay_cmd(title_at, badge_at, badge_frame_count):
    """Build the ffmpeg command for compositing overlays."""
    badge_duration = badge_frame_count / BADGE_FPS

    # Title: infinite loop, no -t. Fade uses absolute timestamps so the
    # title is alpha=0 outside its window — no enable needed.
    # Badge: -itsoffset shifts the PNG sequence to start at badge_at.
    inputs = [
        "-i", BASE_VIDEO,
        "-loop", "1",
        "-i", TITLE_CARD,
    ]

    if badge_frame_count > 0:
        inputs += [
            "-itsoffset", str(badge_at),
            "-framerate", str(BADGE_FPS),
            "-i", os.path.join(TICKER_FRAMES, "frame_%04d.png"),
        ]

    # Title card: scale, then fade in/out using absolute timestamps.
    # Before title_at: fully transparent. After fade-out: fully transparent.
    fade_out_start = title_at + TITLE_FADE_IN + TITLE_HOLD
    title_filter = (
        f"[1:v]scale={TITLE_SCALE_W}:-1,format=rgba,"
        f"fade=in:st={title_at}:d={TITLE_FADE_IN}:alpha=1,"
        f"fade=out:st={fade_out_start}:d={TITLE_FADE_OUT}:alpha=1"
        f"[title]"
    )

    title_x = f"(W-w)/2"
    title_overlay = (
        f"[0:v][title]overlay={title_x}:{TITLE_Y}"
        f":shortest=1:eof_action=pass[v1]"
    )

    if badge_frame_count > 0:
        badge_filter = f"[2:v]format=rgba[badge]"
        badge_overlay = (
            f"[v1][badge]overlay=0:0"
            f":eof_action=pass[vout]"
        )
        filter_complex = f"{title_filter};{title_overlay};{badge_filter};{badge_overlay}"
        map_video = "[vout]"
    else:
        filter_complex = f"{title_filter};{title_overlay.replace('[v1]', '[vout]')}"
        map_video = "[vout]"

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", map_video, "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "26",
        "-c:a", "copy", "-pix_fmt", "yuv420p",
        OUTPUT_OVERLAYS
    ]
    return cmd


def burn_subtitles():
    """Burn ASS subtitles onto the overlay video."""
    subs_escaped = escape_path(SUBS_FILE)
    fonts_escaped = escape_path(FONTS_DIR)

    cmd = [
        "ffmpeg", "-y",
        "-i", OUTPUT_OVERLAYS,
        "-vf", f"subtitles='{subs_escaped}':fontsdir='{fonts_escaped}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "26",
        "-c:a", "copy", "-pix_fmt", "yuv420p",
        OUTPUT_FINAL
    ]
    return cmd


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
    parser = argparse.ArgumentParser(description="Final render with overlays + subtitles")
    parser.add_argument("--title-at", type=float, required=True,
                        help="Timestamp (seconds) for title card appearance")
    parser.add_argument("--badge-at", type=float, required=True,
                        help="Timestamp (seconds) for season badge appearance")
    parser.add_argument("--episode", type=int, default=1,
                        help="Episode number (for rebuilding ticker if needed)")
    parser.add_argument("--skip-ticker", action="store_true",
                        help="Skip ticker rebuild, use existing frames")
    args = parser.parse_args()

    if not os.path.exists(BASE_VIDEO):
        print(f"ERROR: Base video not found: {BASE_VIDEO}")
        print("Run build_edit.py first to generate cut_no_subs.mp4")
        sys.exit(1)

    # Rebuild ticker if needed
    badge_frames = count_badge_frames()
    if badge_frames == 0 and not args.skip_ticker:
        print("No ticker frames found, building...")
        subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "build_ticker.py"),
                        str(args.episode)], check=True)
        badge_frames = count_badge_frames()

    print(f"=== Final Render ===")
    print(f"  Base: {BASE_VIDEO}")
    print(f"  Title card at: {args.title_at}s (fade in {TITLE_FADE_IN}s, hold {TITLE_HOLD}s, fade out {TITLE_FADE_OUT}s)")
    print(f"  Badge at: {args.badge_at}s ({badge_frames} frames, {badge_frames/BADGE_FPS:.1f}s)")

    # Step 1: Composite overlays
    print("\nStep 1: Compositing overlays...")
    cmd = build_overlay_cmd(args.title_at, args.badge_at, badge_frames)
    print(f"  Running ffmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR compositing overlays:")
        print(result.stderr[-500:])
        sys.exit(1)

    dur, size = verify(OUTPUT_OVERLAYS)
    print(f"  with_overlays.mp4: {dur:.1f}s, {size:.1f} MB")

    # Step 2: Burn subtitles
    print("\nStep 2: Burning subtitles...")
    cmd = burn_subtitles()
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR burning subtitles:")
        print(result.stderr[-500:])
        print("\n  Falling back to overlays-only as final...")
        import shutil
        shutil.copy2(OUTPUT_OVERLAYS, OUTPUT_FINAL)

    dur, size = verify(OUTPUT_FINAL)
    print(f"\n=== DONE ===")
    print(f"  {OUTPUT_FINAL}")
    print(f"  Duration: {dur:.1f}s")
    print(f"  Size: {size:.1f} MB")
    print(f"  Under 90s: {'YES' if dur < 90 else 'NO'}")


if __name__ == "__main__":
    main()
