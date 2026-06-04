"""
Render the slot-machine episode ticker animation via HyperFrames.

1. Generate HyperFrames composition for the target episode number
2. Render to green-screen MP4 via HyperFrames
3. Extract frames, chroma-key green to transparency
4. Composite keyed frames onto the pill-less badge PNG
5. Apply fade in/out, place on 1080x1920 canvas
6. Output positioned PNG sequence + demo video

Usage:
    python build_ticker.py 1        # Episode 1 (001)
    python build_ticker.py 15       # Episode 15 (015)
"""
import os
import sys
import subprocess
import json
import platform
import numpy as np
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
BADGE_PATH = os.path.join(PROJECT_ROOT, "Assets", "Animated Season Title - No Pill.png")
TICKER_DIR = os.path.join(SCRIPT_DIR, "ticker-anim")
FRAMES_DIR = os.path.join(SCRIPT_DIR, "animations", "ticker")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "animations", "ticker_demo.mp4")

FPS = 30

CANVAS_W, CANVAS_H = 1080, 1920
BADGE_X = 336  # from Figma — centers the circle, not the PNG
BADGE_Y = 89

FADE_IN = 0.5
FADE_OUT = 0.5

KEY_TOLERANCE = 80


def build_reels(episode_num):
    """Generate digit reel values for each of the three slot reels."""
    d = [episode_num // 100, (episode_num // 10) % 10, episode_num % 10]
    reels = []
    for pos, target in enumerate(d):
        if target == 0 and pos == 0:
            values = [0, 9, 8, 7, 0]
        elif target == 0 and pos == 1:
            values = [0, 9, 8, 7, 6, 5, 0]
        elif target == 0 and pos == 2:
            values = [0, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
        else:
            values = [0] + list(range(9, target - 1, -1))
        reels.append(values)
    return reels


def generate_ticker_html(episode_num):
    """Generate the HyperFrames index.html for the given episode number."""
    reels = build_reels(episode_num)
    labels = ["hundreds", "tens", "units"]
    digits = [episode_num // 100, (episode_num // 10) % 10, episode_num % 10]

    reel_sections = []
    gsap_lines = []

    for i, (values, label, target) in enumerate(zip(reels, labels, digits)):
        digit_divs = "\n".join(
            f'              <div class="digit">{v}</div>' for v in values
        )
        reel_sections.append(
            f'          <!-- Reel {i+1} ({label}): 0 → spin → {target} -->\n'
            f'          <div class="reel-window">\n'
            f'            <div class="reel-strip" id="reel{i+1}">\n'
            f'{digit_divs}\n'
            f'            </div>\n'
            f'          </div>'
        )

        scroll = len(values) - 1
        duration = round(0.35 + scroll * 0.055, 2)
        ease_strength = round(1.4 + i * 0.15, 1)
        start_delay = round(0.05 + i * 0.05, 2)
        gsap_lines.append(
            f'      tl.to("#reel{i+1}", {{\n'
            f'        y: -({scroll} * SLOT_H),\n'
            f'        duration: {duration},\n'
            f'        ease: "back.out({ease_strength})",\n'
            f'      }}, {start_delay});'
        )

    reels_html = "\n\n".join(reel_sections)
    gsap_js = "\n\n".join(gsap_lines)

    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=528, height=464" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      @font-face {{
        font-family: 'Figtree';
        src: url('assets/Figtree-SemiBold.ttf') format('truetype');
        font-weight: 600;
        font-style: normal;
      }}

      * {{ margin: 0; padding: 0; box-sizing: border-box; }}

      html, body {{
        margin: 0;
        width: 528px;
        height: 464px;
        overflow: hidden;
        background: #00FF00;
      }}

      .pill {{
        position: absolute;
        left: 70px;
        top: 228px;
        width: 283px;
        height: 75px;
        border-radius: 38px;
        overflow: hidden;
        background: white;
        box-shadow: inset 0 4px 8px rgba(0, 0, 0, 0.35);
        display: flex;
        align-items: center;
        justify-content: center;
      }}

      .digits {{
        display: flex;
        align-items: center;
        gap: 0px;
        height: 75px;
      }}

      .reel-window {{
        width: 44px;
        height: 75px;
        overflow: hidden;
        position: relative;
      }}

      .reel-strip {{
        display: flex;
        flex-direction: column;
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
      }}

      .digit {{
        width: 44px;
        height: 75px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Figtree', sans-serif;
        font-weight: 700;
        font-size: 52px;
        color: rgb(51, 51, 51);
        flex-shrink: 0;
      }}
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="ticker"
      data-start="0"
      data-duration="3"
      data-width="528"
      data-height="464"
    >
      <div id="pill" class="clip pill" data-start="0" data-duration="3" data-track-index="1">
        <div class="digits">
{reels_html}
        </div>
      </div>
    </div>

    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});

      const SLOT_H = 75;

{gsap_js}

      window.__timelines["ticker"] = tl;
    </script>
  </body>
</html>
'''


def render_hyperframes():
    """Render the ticker animation via HyperFrames CLI."""
    cmd = ["npx", "--yes", "hyperframes@0.6.29", "render"]
    result = subprocess.run(
        cmd, cwd=TICKER_DIR,
        capture_output=True, text=True,
        shell=(platform.system() == "Windows")
    )
    if result.returncode != 0:
        print(f"  ERROR rendering HyperFrames:")
        print(result.stderr[-500:])
        sys.exit(1)


def find_render_output():
    """Find the freshly rendered MP4.

    HyperFrames writes to renders/<name>.mp4, so prefer the newest file there.
    Stale ticker.mp4/ticker_green.mp4 can be copied in from another episode's
    template, so the named-file fallbacks are only used if renders/ is empty.
    """
    renders_dir = os.path.join(TICKER_DIR, "renders")
    if os.path.isdir(renders_dir):
        mp4s = [os.path.join(renders_dir, f) for f in os.listdir(renders_dir)
                if f.endswith(".mp4")]
        if mp4s:
            return max(mp4s, key=os.path.getmtime)
    for name in ["ticker.mp4", "ticker_green.mp4", "output.mp4"]:
        path = os.path.join(TICKER_DIR, name)
        if os.path.exists(path):
            return path
    return None


def extract_frames(video_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"fps={FPS}",
        os.path.join(output_dir, "raw_%04d.png")
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    frames = sorted(f for f in os.listdir(output_dir) if f.startswith("raw_") and f.endswith(".png"))
    return len(frames)


def chroma_key_simple(img_array):
    """Remove green screen background."""
    r = img_array[:, :, 0].astype(int)
    g = img_array[:, :, 1].astype(int)
    b = img_array[:, :, 2].astype(int)
    green_diff = np.minimum(g - r, g - b)
    alpha = np.clip(255 - green_diff * 4, 0, 255).astype(np.uint8)
    alpha[green_diff > KEY_TOLERANCE] = 0
    alpha[green_diff < 5] = 255
    return np.dstack([img_array[:, :, :3], alpha])


def main():
    if len(sys.argv) < 2:
        print("Usage: python build_ticker.py <episode_number>")
        print("  e.g. python build_ticker.py 1")
        sys.exit(1)

    episode = int(sys.argv[1])
    print(f"=== Building ticker for Episode {episode:03d} ===")

    # Step 1: Generate HyperFrames composition
    print("  Generating HyperFrames composition...")
    html = generate_ticker_html(episode)
    html_path = os.path.join(TICKER_DIR, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Step 2: Render via HyperFrames
    print("  Rendering green-screen video...")
    render_hyperframes()

    ticker_video = find_render_output()
    if not ticker_video:
        print(f"  ERROR: No render output found in {TICKER_DIR}")
        for f in os.listdir(TICKER_DIR):
            print(f"    {f}")
        sys.exit(1)
    print(f"  Rendered: {os.path.basename(ticker_video)}")

    # Step 3: Load badge
    badge = Image.open(BADGE_PATH).convert("RGBA")
    print(f"  Badge: {badge.size} (pill-less)")

    # Step 4: Extract frames from green-screen render
    raw_dir = os.path.join(FRAMES_DIR, "raw")
    print("  Extracting frames...")
    frame_count = extract_frames(ticker_video, raw_dir)
    print(f"  {frame_count} frames extracted")

    # Step 5: Calculate fade timing
    anim_duration = frame_count / FPS
    total_frames = int((FADE_IN + anim_duration + FADE_OUT) * FPS)
    fade_in_frames = int(FADE_IN * FPS)
    fade_out_start = total_frames - int(FADE_OUT * FPS)
    print(f"  {anim_duration:.1f}s + fades = {total_frames/FPS:.1f}s total ({total_frames} frames)")

    # Step 6: Generate positioned frames (chroma key → badge composite → canvas)
    positioned_dir = os.path.join(FRAMES_DIR, "positioned")
    os.makedirs(positioned_dir, exist_ok=True)

    for i in range(total_frames):
        if i < fade_in_frames:
            anim_frame_idx = 0
        elif i >= fade_in_frames + frame_count:
            anim_frame_idx = frame_count - 1
        else:
            anim_frame_idx = i - fade_in_frames

        raw_path = os.path.join(raw_dir, f"raw_{anim_frame_idx + 1:04d}.png")
        raw_img = Image.open(raw_path).convert("RGB")
        keyed = chroma_key_simple(np.array(raw_img))
        pill_frame = Image.fromarray(keyed, "RGBA")

        if pill_frame.height > badge.height:
            pill_frame = pill_frame.crop((0, 0, pill_frame.width, badge.height))

        frame = badge.copy()
        frame.paste(pill_frame, (0, 0), pill_frame)

        if i < fade_in_frames:
            alpha_mult = i / fade_in_frames
        elif i >= fade_out_start:
            alpha_mult = 1 - (i - fade_out_start) / (total_frames - fade_out_start)
        else:
            alpha_mult = 1.0

        if alpha_mult < 1.0:
            r, g, b, a = frame.split()
            a = a.point(lambda p: int(p * alpha_mult))
            frame = Image.merge("RGBA", (r, g, b, a))

        canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        canvas.paste(frame, (BADGE_X, BADGE_Y), frame)
        canvas.save(os.path.join(positioned_dir, f"frame_{i:04d}.png"))

    print(f"  Generated {total_frames} positioned frames")

    # Step 7: Encode demo video
    print("  Encoding demo video...")
    demo_dir = os.path.join(FRAMES_DIR, "demo")
    os.makedirs(demo_dir, exist_ok=True)

    for i in range(total_frames):
        pos = Image.open(os.path.join(positioned_dir, f"frame_{i:04d}.png")).convert("RGBA")
        bg = Image.new("RGBA", (CANVAS_W, CANVAS_H), (30, 30, 30, 255))
        bg.paste(pos, (0, 0), pos)
        bg.convert("RGB").save(os.path.join(demo_dir, f"frame_{i:04d}.png"))

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(demo_dir, "frame_%04d.png"),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        OUTPUT_PATH
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[-300:]}")
        return

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", OUTPUT_PATH],
        capture_output=True, text=True
    )
    info = json.loads(probe.stdout)
    dur = float(info["format"]["duration"])
    print(f"\n  Demo: {dur:.1f}s -> {OUTPUT_PATH}")
    print(f"  Positioned frames -> {positioned_dir}")
    print("  Ready for build_final.py!")


if __name__ == "__main__":
    main()
