import json
import subprocess
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EP_DIR = os.path.dirname(SCRIPT_DIR)
SOURCE = os.path.join(EP_DIR, "ep4_take2.mp4")
TRANSCRIPT_FILE = os.path.join(SCRIPT_DIR, "transcript_raw.json")
EDL_FILE = os.path.join(SCRIPT_DIR, "edl.json")
SEGMENTS_LIST = os.path.join(SCRIPT_DIR, "segments.txt")
SUBS_FILE = os.path.join(SCRIPT_DIR, "subs.ass")

PAD_BEFORE = 0.05
PAD_AFTER = 0.08
MIN_GAP_TO_MERGE = 0.30
FONTS_DIR = os.path.join(os.path.dirname(EP_DIR), os.pardir, "Assets", "fonts")

# Text corrections for transcription errors
TEXT_CORRECTIONS = {
    "Web June": "Webdune",
    "Webjune": "Webdune",
    "Jossie": "Josue",
    "favorite": "favourite",
    "Fiver": "Fiverr",
    "Hendricks": "HNDRX",
    "Sell Myself": "SellMyCell",
}

def load_words(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return [w for w in data["words"] if w["type"] == "word"]

# EP4 is a heavy content cut (3m41s take -> ~81s), so we define what to KEEP
# (inclusive word-index ranges) and derive the cut set as the complement.
# See plan_cuts.py for the readable per-segment breakdown.
KEEP_RANGES = [
    (2, 17),      # welcome finally to episode four of the Webdune Diaries in season one, the Fox Stevenson season.
    (81, 87),     # Webdune is a web agency, so we
    (89, 92),     # develop, which is coding,
    (94, 95),     # building websites,
    (97, 101),    # on tools like Webflow, WordPress,
    (103, 106),   # Wix, Squarespace, usually Webflow.
    (108, 118),   # and we also design them. So there's a tool called Figma
    (147, 151),   # how do we make money?
    (152, 165),   # Usually, I'm subcontracting for a marketing agency or a digital agency or web agency.
    (211, 216),   # how do I get these jobs?
    (217, 225),   # Usually through Unicorn Factory. It's a freelancer marketplace based
    (227, 229),   # in New Zealand,
    (240, 242),   # good high-quality leads,
    (255, 273),   # rather than the Fiverr situation of, you know, race to the bottom, I want a website for $5 situation.
    (275, 289),   # and then from Unicorn Factory, I've got ongoing relationships that I'll keep working with agencies
    (291, 292),   # or clients,
    (328, 331),   # I'm working for HNDRX.
    (333, 338),   # they're a web agency from Raglan.
    (339, 343),   # I'm doing some work with
    (345, 353),   # Onsite Media, they're a marketing digital agency from Tauranga.
    (355, 368),   # doing a little bit of work for Launch Agency, they're a big marketing agency
    (370, 371),   # from Hamilton.
    (372, 385),   # And then in terms of direct clients, I'm doing some work for Legend Story.
    (393, 396),   # a landing page design.
    (402, 423),   # And then a little bit of work with SellMyCell. We just wrapped up a massive phase two new website for them.
    (433, 438),   # Constantly working with Spirit of Douglas,
    (440, 444),   # a cool plane, so not-for-profit,
    (516, 518),   # so next episode,
    (520, 533),   # it would be awesome to show you guys what I do day to day.
    (576, 586),   # a bit of a portfolio, a bit of a showcase, maybe some fancy swirling animations.
]

KEEP_IDX = {i for a, b in KEEP_RANGES for i in range(a, b + 1)}

def build_keep_segments(words):
    segments = []
    current_start = None

    for i, w in enumerate(words):
        if i in KEEP_IDX:
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

def format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_ass_subtitles(segments, output_path):
    header = r"""[Script Info]
Title: Webdune Diaries S01E04
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
    output_time = 0.0

    for seg in segments:
        seg_duration = seg["end"] - seg["start"]
        raw_words = seg["text"].split()

        if not raw_words:
            output_time += seg_duration
            continue

        time_per_word = seg_duration / len(raw_words)

        # Chunk into 2-3 word groups
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

            events.append(f"Dialogue: 0,{format_ass_time(start_t)},{format_ass_time(end_t)},Default,,0,0,0,,{chunk_text}")
            word_offset += len(chunk)

        output_time += seg_duration

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(events))
        f.write("\n")

    return output_time

def main():
    print("Loading transcript...")
    words = load_words(TRANSCRIPT_FILE)
    cut_count = len(words) - len(KEEP_IDX)
    print(f"  {len(words)} words found")
    print(f"  Keeping {len(KEEP_IDX)} words, cutting {cut_count}")

    print("\nBuilding keep segments...")
    segments = build_keep_segments(words)
    total_kept = sum(s["end"] - s["start"] for s in segments)
    print(f"  {len(segments)} segments, estimated duration: {total_kept:.1f}s")

    for i, seg in enumerate(segments):
        dur = seg["end"] - seg["start"]
        print(f"  [{i:2d}] {seg['start']:6.2f}-{seg['end']:6.2f} ({dur:4.1f}s) {seg['text'][:80]}")

    edl = {
        "version": 1,
        "source": SOURCE,
        "segments": segments,
        "grade": "none",
        "estimated_duration": round(total_kept, 1)
    }
    with open(EDL_FILE, "w") as f:
        json.dump(edl, f, indent=2)
    print(f"\n  EDL saved to {EDL_FILE}")

    print("\nGenerating subtitles...")
    final_duration = generate_ass_subtitles(segments, SUBS_FILE)
    print(f"  Subtitles saved to {SUBS_FILE} ({final_duration:.1f}s)")

    # Generate ffmpeg segment extraction commands
    clips_dir = os.path.join(SCRIPT_DIR, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    concat_entries = []
    for i, seg in enumerate(segments):
        out_path = os.path.join(clips_dir, f"seg_{i:03d}.mp4")
        duration = round(seg["end"] - seg["start"], 3)
        fade_out_start = max(0, duration - 0.03)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(seg["start"]),
            "-i", SOURCE,
            "-t", str(duration),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-af", f"afade=t=in:st=0:d=0.03,afade=t=out:st={fade_out_start:.3f}:d=0.03",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            out_path
        ]

        print(f"  Extracting segment {i}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"    ERROR: {result.stderr[-200:]}")
            return

        concat_entries.append(f"file '{out_path}'")

    with open(SEGMENTS_LIST, "w") as f:
        f.write("\n".join(concat_entries))

    # Concat all segments
    concat_out = os.path.join(SCRIPT_DIR, "cut_no_subs.mp4")
    print(f"\nConcatenating {len(segments)} segments...")
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", SEGMENTS_LIST,
        "-c", "copy",
        concat_out
    ]
    result = subprocess.run(concat_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[-300:]}")
        return

    # Burn subtitles
    final_out = os.path.join(SCRIPT_DIR, "final.mp4")
    print("Burning subtitles...")
    subs_escaped = SUBS_FILE.replace("\\", "/").replace(":", "\\:")
    fonts_dir = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "Assets", "fonts"))
    fonts_escaped = fonts_dir.replace("\\", "/").replace(":", "\\:")
    sub_cmd = [
        "ffmpeg", "-y",
        "-i", concat_out,
        "-vf", f"subtitles='{subs_escaped}':fontsdir='{fonts_escaped}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        final_out
    ]
    result = subprocess.run(sub_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Subtitle burn error: {result.stderr[-300:]}")
        print("  Saving without subtitles as final.mp4 for now...")
        os.replace(concat_out, final_out)
    else:
        print(f"  Final output: {final_out}")

    # Verify with ffprobe
    probe_cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", final_out]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True)
    info = json.loads(probe.stdout)
    duration = float(info["format"]["duration"])
    size_mb = int(info["format"]["size"]) / (1024 * 1024)
    print(f"\n=== FINAL ===")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Size: {size_mb:.1f} MB")
    print(f"  Under 90s: {'YES' if duration < 90 else 'NO'}")

if __name__ == "__main__":
    main()
