"""EP03 build_edit.py — Second half of the origin story: existential crisis → comeback.

Source: ../Episode 2/main-clip.mp4 (131.7s onwards, with cuts)
Opens with a 1s fade-in from black.

Output: cut_no_subs.mp4, subs.ass
"""
import json
import subprocess
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EP_DIR = os.path.dirname(SCRIPT_DIR)

# Source — shared with EP02
MAIN_CLIP = os.path.abspath(os.path.join(EP_DIR, "..", "Episode 2", "main-clip.mp4"))
MAIN_TRANSCRIPT = os.path.abspath(os.path.join(EP_DIR, "..", "Episode 2", "edit", "transcripts", "main-clip.json"))

# Output
SEGMENTS_LIST = os.path.join(SCRIPT_DIR, "segments.txt")
SUBS_FILE = os.path.join(SCRIPT_DIR, "subs.ass")
OUTPUT = os.path.join(SCRIPT_DIR, "cut_no_subs.mp4")

# Config
SCALE_FILTER = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
PAD_BEFORE = 0.05
PAD_AFTER = 0.08
MIN_GAP_TO_MERGE = 0.30
FONTS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "Assets", "fonts"))
FONT_FILE = os.path.join(FONTS_DIR, "Figtree-SemiBold.ttf")

TEXT_CORRECTIONS = {
    "Web June": "Webdune",
    "Jossie": "Josue",
    "favorite": "favourite",
}

# EP03 uses words 457-847 from the main-clip transcript (rebased to 0)
EP03_FIRST_WORD = 457  # "I" at 131.7s
EP03_LAST_WORD = 847   # "this." at 241.5s

# ── CUT INDICES (rebased: 0 = original word 457) ────────────────────────
CUT_INDICES = {
    24,    # 481: um, (before "where I felt like")
    36,    # 493: uh, (before "why am I making websites")
    # "and, and, and ch- save" → "and save"
    48,    # 505: and, (first repeated)
    49,    # 506: and, (second repeated)
    51,    # 508: ch- (false start)
    55,    # 512: Um, (before "but then I went overseas")
    65,    # 522: um, (before "a bit after that")
    94,    # 551: and, (first of "and, and they're")
    111,   # 568: um, (before "and enjoy for a while")
    117,   # 574: and, (first of "and, and maybe")
    135,   # 592: Um, (before "so that's, yeah")
    156,   # 613: and, (first of "and, and projects")
    179,   # 636: um, (before "through that period")
    185,   # 642: Um, (before "but now in these past")
    216,   # 673: um, (before "a lot")
    231,   # 688: turbulent, (first of "turbulent, turbulent")
    233,   # 690: um, (before "time coming to")
    253,   # 710: Um, (before "yeah, things are always")
    283,   # 740: to, (first of "to, to, to share")
    284,   # 741: to, (second of "to, to, to share")
    298,   # 755: um, (before "and talk about the day-to-day")
    # Big cut: meta wrap-up / subway surfers / Minecraft (218.1s-233.7s)
    *range(304, 369),
    # Ending cleanup: "But, um, yeah, thanks for all, already, all the support..."
    # → "thanks for all the support that has come through"
    369,   # 826: But,
    370,   # 827: um,
    371,   # 828: yeah,
    374,   # 831: all, (first of "all, already, all")
    375,   # 832: already,
    383,   # 840: and,
}


# ── HELPERS ──────────────────────────────────────────────────────────────

def run(cmd, label=""):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR ({label}): {result.stderr[-400:]}")
        sys.exit(1)
    return result

def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())

def load_words(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return [w for w in data["words"] if w["type"] == "word"]


# ── SEGMENTS ─────────────────────────────────────────────────────────────

def build_keep_segments(all_words):
    words = all_words[EP03_FIRST_WORD:EP03_LAST_WORD + 1]

    segments = []
    current_start = None

    for i, w in enumerate(words):
        if i not in CUT_INDICES:
            if current_start is None:
                current_start = i
        else:
            if current_start is not None:
                segments.append((current_start, i - 1))
                current_start = None

    if current_start is not None:
        segments.append((current_start, len(words) - 1))

    time_segments = []
    for start_idx, end_idx in segments:
        t_start = max(0, words[start_idx]["start"] - PAD_BEFORE)
        t_end = words[end_idx]["end"] + PAD_AFTER
        text = " ".join(words[j]["text"].strip() for j in range(start_idx, end_idx + 1))
        for wrong, right in TEXT_CORRECTIONS.items():
            text = text.replace(wrong, right)
        time_segments.append({
            "start": round(t_start, 3),
            "end": round(t_end, 3),
            "text": text
        })

    merged = [time_segments[0]]
    for seg in time_segments[1:]:
        if seg["start"] - merged[-1]["end"] < MIN_GAP_TO_MERGE:
            merged[-1]["end"] = seg["end"]
            merged[-1]["text"] += " " + seg["text"]
        else:
            merged.append(seg)

    return merged


def create_intro_card():
    """Create 'continuing from episode 2...' text card that fades into first segment."""
    clips_dir = os.path.join(SCRIPT_DIR, "clips")
    os.makedirs(clips_dir, exist_ok=True)
    card_path = os.path.join(clips_dir, "intro_card.mp4")
    card_dur = 2.0

    font_escaped = FONT_FILE.replace("\\", "/").replace(":", "\\:")
    drawtext = (
        f"drawtext=text='continuing from episode 2...':"
        f"fontfile='{font_escaped}':"
        f"fontsize=42:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2,"
        f"fade=in:d=0.5,fade=out:st={card_dur - 0.5}:d=0.5"
    )

    print("  Creating intro card...")
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=black:s=1080x1920:d={card_dur}:r=30",
        "-f", "lavfi", "-i", f"anullsrc=cl=stereo:r=44100",
        "-t", str(card_dur),
        "-vf", drawtext,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-pix_fmt", "yuv420p",
        "-shortest",
        card_path
    ], "intro card")

    return card_path, card_dur


def extract_segments(segments):
    clips_dir = os.path.join(SCRIPT_DIR, "clips")
    os.makedirs(clips_dir, exist_ok=True)
    paths = []

    for i, seg in enumerate(segments):
        out_path = os.path.join(clips_dir, f"seg_{i:03d}.mp4")
        duration = round(seg["end"] - seg["start"], 3)

        # First segment: fade-in from black (follows the intro card)
        if i == 0:
            vf = f"{SCALE_FILTER},fade=in:d=1"
            af = f"afade=t=in:d=1,afade=t=out:st={max(0, duration - 0.03):.3f}:d=0.03"
        else:
            fade_out_start = max(0, duration - 0.03)
            vf = SCALE_FILTER
            af = f"afade=t=in:st=0:d=0.03,afade=t=out:st={fade_out_start:.3f}:d=0.03"

        print(f"  Extracting segment {i} [{seg['start']:.1f}s-{seg['end']:.1f}s]...")
        run([
            "ffmpeg", "-y",
            "-ss", str(seg["start"]), "-i", MAIN_CLIP, "-t", str(duration),
            "-vf", vf,
            "-af", af,
            "-r", "30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-pix_fmt", "yuv420p",
            out_path
        ], f"seg {i}")
        paths.append(out_path)

    return paths


# ── SUBTITLES ────────────────────────────────────────────────────────────

def format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_subtitles(intro_card_dur, segments):
    header = r"""[Script Info]
Title: Webdune Diaries S01E03
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Figtree SemiBold,60,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,4,1,2,40,40,350

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    output_time = intro_card_dur  # offset subs past the intro card

    for seg in segments:
        seg_duration = seg["end"] - seg["start"]
        raw_words = seg["text"].split()

        if not raw_words:
            output_time += seg_duration
            continue

        time_per_word = seg_duration / len(raw_words)
        chunks = []
        i = 0
        while i < len(raw_words):
            remaining = len(raw_words) - i
            if remaining <= 3:
                chunks.append(raw_words[i:])
                break
            elif remaining == 4:
                chunks.append(raw_words[i:i+2])
                i += 2
            else:
                chunk_size = 2 if remaining % 3 != 0 and remaining % 2 == 0 else 3
                if remaining - chunk_size == 1:
                    chunk_size = 2
                chunks.append(raw_words[i:i+chunk_size])
                i += chunk_size

        word_offset = 0
        for chunk in chunks:
            chunk_text = " ".join(chunk)
            start_t = output_time + word_offset * time_per_word
            end_t = output_time + (word_offset + len(chunk)) * time_per_word
            events.append(
                f"Dialogue: 0,{format_ass_time(start_t)},{format_ass_time(end_t)},Default,,0,0,0,,{chunk_text}"
            )
            word_offset += len(chunk)

        output_time += seg_duration

    with open(SUBS_FILE, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(events))
        f.write("\n")

    return output_time


# ── MAIN ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("EP03 Build Edit — Existential crisis + comeback")
    print("=" * 60)

    print("\nLoading transcript...")
    all_words = load_words(MAIN_TRANSCRIPT)
    ep03_words = all_words[EP03_FIRST_WORD:EP03_LAST_WORD + 1]
    print(f"  {len(ep03_words)} words for EP03 (indices {EP03_FIRST_WORD}-{EP03_LAST_WORD})")
    print(f"  Cutting {len(CUT_INDICES)} words")

    print("\nBuilding keep segments...")
    segments = build_keep_segments(all_words)
    total_kept = sum(s["end"] - s["start"] for s in segments)
    print(f"  {len(segments)} segments, ~{total_kept:.1f}s of content")

    for i, seg in enumerate(segments):
        dur = seg["end"] - seg["start"]
        preview = seg["text"][:70]
        print(f"  [{i:2d}] {seg['start']:6.1f}s-{seg['end']:6.1f}s ({dur:4.1f}s) {preview}...")

    print("\nCreating intro card...")
    intro_path, intro_dur = create_intro_card()

    print("\nExtracting segments...")
    seg_paths = extract_segments(segments)

    print(f"\nConcatenating intro card + {len(seg_paths)} segments...")
    all_clips = [intro_path] + seg_paths
    entries = [f"file '{p}'" for p in all_clips]
    with open(SEGMENTS_LIST, "w") as f:
        f.write("\n".join(entries))
    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", SEGMENTS_LIST,
        "-c", "copy",
        OUTPUT
    ], "concat")

    print("\nGenerating subtitles...")
    sub_dur = generate_subtitles(intro_dur, segments)
    print(f"  Subtitles: {SUBS_FILE} ({sub_dur:.1f}s)")

    # Verify
    final_dur = get_duration(OUTPUT)
    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print(f"  Output: {OUTPUT}")
    print(f"  Duration: {final_dur:.1f}s")
    print(f"  Size: {size_mb:.1f} MB")
    print(f"  Under 90s: {'YES' if final_dur < 90 else 'NO — needs more cuts'}")
    print(f"  Breakdown: intro card {intro_dur:.1f}s + content {total_kept:.1f}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
