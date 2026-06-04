"""
Final render: composites title card + season badge animation + brand-logo
sticker cards + subtitles onto cut_no_subs.mp4.

Title card: fade in/out at a human-specified timestamp.
Season badge: pre-rendered PNG sequence from build_ticker.py.
Logos: white "sticker cards" that hard-cut in/out at each brand mention
       (ffmpeg `enable` windows -- no fades, no -itsoffset, so the fade-math
       pitfall documented in CLAUDE.md does not apply).
Subtitles: burned last from subs.ass.

Usage:
    python build_final.py --title-at 1.5 --badge-at 6 --episode 4
"""
import argparse
import os
import subprocess
import json
import sys

from PIL import Image, ImageDraw, ImageFilter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
EP_DIR = os.path.dirname(SCRIPT_DIR)

BASE_VIDEO = os.path.join(SCRIPT_DIR, "cut_no_subs.mp4")
SUBS_FILE = os.path.join(SCRIPT_DIR, "subs.ass")
TITLE_CARD = os.path.join(PROJECT_ROOT, "Assets", "Webdune Diaries Title - White Text.png")
FONTS_DIR = os.path.join(PROJECT_ROOT, "Assets", "fonts")
TICKER_FRAMES = os.path.join(SCRIPT_DIR, "animations", "ticker", "positioned")
LOGOS_DIR = os.path.join(EP_DIR, "logos")
LOGO_CARDS_DIR = os.path.join(SCRIPT_DIR, "animations", "logos")

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

# --- Logo sticker cards -------------------------------------------------------
# White rounded card behind each logo for legibility against the busy background.
CARD_PAD = 26
CARD_RADIUS = 28
CARD_BG = (255, 255, 255, 235)
SHADOW_PAD = 18

# Each event: slug, t_in, t_out, centre x, centre y, logo height (px).
# Timings come from the real subtitle timings (subs.ass). Singles are centred
# above the head; the dev-tools group is a 2x2 grid that clears together.
LOGO_EVENTS = [
    # Dev tools (mentioned together) -> 2x2 grid, all cleared at once
    {"slug": "webflow",        "in": 12.7, "out": 15.2, "cx": 305, "cy": 125, "h": 70},
    {"slug": "wordpress",      "in": 12.7, "out": 15.2, "cx": 770, "cy": 120, "h": 78},
    {"slug": "wix",            "in": 12.7, "out": 15.2, "cx": 305, "cy": 300, "h": 66},
    {"slug": "squarespace",    "in": 12.7, "out": 15.2, "cx": 770, "cy": 300, "h": 56},
    # Design tool
    {"slug": "figma",          "in": 16.9, "out": 18.1, "cx": 540, "cy": 170, "h": 140},
    # Marketplace
    {"slug": "unicorn-factory","in": 26.2, "out": 29.9, "cx": 540, "cy": 160, "h": 110},
    {"slug": "fiverr",         "in": 32.1, "out": 35.2, "cx": 540, "cy": 150, "h": 92},
    {"slug": "unicorn-factory","in": 37.9, "out": 39.6, "cx": 540, "cy": 160, "h": 110},
    # Clients (sequential)
    {"slug": "hndrx",          "in": 43.8, "out": 47.5, "cx": 540, "cy": 150, "h": 84},
    {"slug": "onsite",         "in": 48.7, "out": 52.4, "cx": 540, "cy": 150, "h": 96},
    {"slug": "launch",         "in": 54.0, "out": 56.8, "cx": 540, "cy": 150, "h": 84},
    {"slug": "legend-story",   "in": 60.3, "out": 62.5, "cx": 540, "cy": 185, "h": 150},
    {"slug": "sellmycell",     "in": 64.1, "out": 68.2, "cx": 540, "cy": 150, "h": 96},
    {"slug": "spirit-douglas", "in": 68.9, "out": 72.2, "cx": 540, "cy": 185, "h": 150},
]


def make_card(slug, logo_h):
    """Render a logo on a white rounded card with a soft drop shadow."""
    logo = Image.open(os.path.join(LOGOS_DIR, f"{slug}.png")).convert("RGBA")
    w = max(1, int(round(logo.width * logo_h / logo.height)))
    logo = logo.resize((w, logo_h), Image.LANCZOS)
    cw, ch = w + 2 * CARD_PAD, logo_h + 2 * CARD_PAD
    p = SHADOW_PAD
    canvas = Image.new("RGBA", (cw + 2 * p, ch + 2 * p), (0, 0, 0, 0))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [p, p + 4, p + cw, p + ch + 4], CARD_RADIUS, fill=(0, 0, 0, 90))
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(8)))
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle([0, 0, cw - 1, ch - 1], CARD_RADIUS, fill=CARD_BG)
    card.alpha_composite(logo, (CARD_PAD, CARD_PAD))
    canvas.alpha_composite(card, (p, p))
    return canvas


def render_logo_cards():
    """Pre-render each logo event's card PNG; return list with pixel geometry."""
    os.makedirs(LOGO_CARDS_DIR, exist_ok=True)
    events = []
    for i, ev in enumerate(LOGO_EVENTS):
        card = make_card(ev["slug"], ev["h"])
        path = os.path.join(LOGO_CARDS_DIR, f"l{i:02d}_{ev['slug']}.png")
        card.save(path)
        x = int(round(ev["cx"] - card.width / 2))
        y = int(round(ev["cy"] - card.height / 2))
        events.append({**ev, "path": path, "x": x, "y": y})
    return events


def escape_path(path):
    """Escape path for ffmpeg filter strings on Windows."""
    return path.replace("\\", "/").replace(":", "\\:")


def count_badge_frames():
    if not os.path.isdir(TICKER_FRAMES):
        return 0
    return len([f for f in os.listdir(TICKER_FRAMES) if f.endswith(".png")])


def build_overlay_cmd(title_at, badge_at, badge_frame_count, logo_events):
    """Build the ffmpeg command for compositing title + badge + logos."""
    inputs = [
        "-i", BASE_VIDEO,
        "-loop", "1",
        "-i", TITLE_CARD,
    ]
    next_idx = 2

    badge_idx = None
    if badge_frame_count > 0:
        badge_idx = next_idx
        inputs += [
            "-itsoffset", str(badge_at),
            "-framerate", str(BADGE_FPS),
            "-i", os.path.join(TICKER_FRAMES, "frame_%04d.png"),
        ]
        next_idx += 1

    logo_idx0 = next_idx
    for ev in logo_events:
        inputs += ["-loop", "1", "-i", ev["path"]]
        next_idx += 1

    # Title card: scale, fade in/out using absolute timestamps.
    fade_out_start = title_at + TITLE_FADE_IN + TITLE_HOLD
    parts = [
        f"[1:v]scale={TITLE_SCALE_W}:-1,format=rgba,"
        f"fade=in:st={title_at}:d={TITLE_FADE_IN}:alpha=1,"
        f"fade=out:st={fade_out_start}:d={TITLE_FADE_OUT}:alpha=1[title]",
        f"[0:v][title]overlay=(W-w)/2:{TITLE_Y}:shortest=1:eof_action=pass[v1]",
    ]
    cur = "[v1]"

    if badge_idx is not None:
        parts.append(f"[{badge_idx}:v]format=rgba[badge]")
        parts.append(f"{cur}[badge]overlay=0:0:eof_action=pass[vb]")
        cur = "[vb]"

    # Logos: hard cut in/out via enable windows (no fade, no itsoffset).
    for n, ev in enumerate(logo_events):
        idx = logo_idx0 + n
        lbl = f"[lg{n}]"
        parts.append(f"[{idx}:v]format=rgba{lbl}")
        out_lbl = f"[vl{n}]"
        parts.append(
            f"{cur}{lbl}overlay={ev['x']}:{ev['y']}"
            f":enable='between(t,{ev['in']},{ev['out']})':eof_action=pass{out_lbl}"
        )
        cur = out_lbl

    filter_complex = ";".join(parts)
    # rename final label to [vout]
    filter_complex = filter_complex[: filter_complex.rfind(cur)] + "[vout]"
    map_video = "[vout]"

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", map_video, "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "26",
        "-c:a", "copy", "-pix_fmt", "yuv420p",
        OUTPUT_OVERLAYS,
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
        OUTPUT_FINAL,
    ]


def verify(path):
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True,
    )
    info = json.loads(probe.stdout)
    return float(info["format"]["duration"]), int(info["format"]["size"]) / (1024 * 1024)


def main():
    parser = argparse.ArgumentParser(description="Final render with overlays + subtitles")
    parser.add_argument("--title-at", type=float, required=True)
    parser.add_argument("--badge-at", type=float, required=True)
    parser.add_argument("--episode", type=int, default=4)
    parser.add_argument("--skip-ticker", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(BASE_VIDEO):
        print(f"ERROR: Base video not found: {BASE_VIDEO}")
        print("Run build_edit.py first to generate cut_no_subs.mp4")
        sys.exit(1)

    badge_frames = count_badge_frames()
    if badge_frames == 0 and not args.skip_ticker:
        print("No ticker frames found, building...")
        subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "build_ticker.py"),
                        str(args.episode)], check=True)
        badge_frames = count_badge_frames()

    print("Rendering logo cards...")
    logo_events = render_logo_cards()
    print(f"  {len(logo_events)} logo events")

    print("=== Final Render ===")
    print(f"  Base: {BASE_VIDEO}")
    print(f"  Title card at: {args.title_at}s")
    print(f"  Badge at: {args.badge_at}s ({badge_frames} frames, {badge_frames/BADGE_FPS:.1f}s)")

    print("\nStep 1: Compositing overlays (title + badge + logos)...")
    cmd = build_overlay_cmd(args.title_at, args.badge_at, badge_frames, logo_events)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("  ERROR compositing overlays:")
        print(result.stderr[-1500:])
        sys.exit(1)
    dur, size = verify(OUTPUT_OVERLAYS)
    print(f"  with_overlays.mp4: {dur:.1f}s, {size:.1f} MB")

    print("\nStep 2: Burning subtitles...")
    result = subprocess.run(burn_subtitles(), capture_output=True, text=True)
    if result.returncode != 0:
        print("  ERROR burning subtitles:")
        print(result.stderr[-1000:])
        print("\n  Falling back to overlays-only as final...")
        import shutil
        shutil.copy2(OUTPUT_OVERLAYS, OUTPUT_FINAL)

    dur, size = verify(OUTPUT_FINAL)
    print("\n=== DONE ===")
    print(f"  {OUTPUT_FINAL}")
    print(f"  Duration: {dur:.1f}s  Size: {size:.1f} MB  Under 90s: {'YES' if dur < 90 else 'NO'}")


if __name__ == "__main__":
    main()
