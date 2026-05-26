"""EP02 build_edit.py — Multi-source edit with rave intro + main clip + ending card.

Order:
  1. main-clip intro "Hello everybody..." (~4s)
  2. rave-explainer.mp4 (full, ~5s) — "Apologies, I was at a rave..."
  3. rave-screen-recording.mp4 (1.5s-4.5s, muted + Venjent audio) — smash cut to rave
  4. main-clip.mp4 (rest of origin story, with cuts)
  5. Generated ending card (2.5s) — fade to black + "continues in Episode 3"

Output: cut_no_subs.mp4, subs.ass
"""
import json
import subprocess
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EP_DIR = os.path.dirname(SCRIPT_DIR)

# Sources
MAIN_CLIP = os.path.join(EP_DIR, "main-clip.mp4")
RAVE_EXPLAINER = os.path.join(EP_DIR, "rave-explainer.mp4")
RAVE_RECORDING = os.path.join(EP_DIR, "rave-screen-recording.mp4")
VENJENT_SONG = os.path.join(EP_DIR, "Venjent - Driven By My Heart.mp3")
MAIN_TRANSCRIPT = os.path.join(SCRIPT_DIR, "transcripts", "main-clip.json")
RAVE_TRANSCRIPT = os.path.join(SCRIPT_DIR, "transcripts", "rave-explainer.json")

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

# Rave recording trim (cut in 0.5s earlier, 1s shorter total)
RAVE_REC_START = 1.5
RAVE_REC_END = 4.5
VENJENT_START = 83.0  # 1:23 of song
RAVE_EXP_TRIM = 0.5   # trim from end for snappier cut to rave recording

# Main clip: use words 0-455 (up to "cool." at ~130.4s)
EP02_LAST_WORD = 455

TEXT_CORRECTIONS = {
    "Web June": "Webdune",
    "Jossie": "Josue",
    "favorite": "favourite",
}

# ── CUT INDICES ──────────────────────────────────────────────────────────
# Word indices into main-clip transcript (words-only, 0-based).
CUT_INDICES = {
    # Big cut A: Fox Stevenson preamble (5.0s-19.0s)
    *range(12, 70),
    # Big cut B: "this episode, we were gonna talk about the day-to-day operations, but I wanted"
    *range(70, 85),
    # Filler: "um," before "why I made it"
    95,
    # False start group: "and w-" → keep "and where we're up to"
    100, 101,
    # Big cut C: "Um, so let's get into that."
    *range(107, 113),
    # Filler
    119,   # uh, (before Max)
    142,   # uh, (before "a normal software company")
    # Stutter: "as a, as a junior" → "as a junior"
    147, 148,
    163,   # Um, (before "I've got some design skills")
    175,   # Let's, (first of "Let's, let's")
    200,   # Um, (before "and five years later")
    205,   # um, (before "it's kind of true")
    # Big cut D: "not as easy as we thought...getting better and better" (64.4s-73.3s)
    *range(222, 255),
    255,   # "They," stutter before "the first year"
    265,   # Um,
    269,   # um, (between "worked," and "from")
    309,   # um, (before "during that period")
    319,   # Um, (before "ended up getting paid")
    352,   # Um, (before "and then after")
    365,   # to, (first of "to, to survive")
    370,   # um, (before "I got a job")
    375,   # uh, (before "a contract")
    383,   # a, (first of "a, a massive")
    390,   # the, (first of "the, the tool")
    398,   # Um, (before "I worked")
    401,   # f- (false start before "for them")
    # Big cut E: N4 culture + departure details (117.2s-127.9s)
    *range(407, 444),
    447,   # and, (first of "and, and making")
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


# ── STEP 1: RAVE CLIPS ──────────────────────────────────────────────────

def prepare_rave_clips():
    clips_dir = os.path.join(SCRIPT_DIR, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    # 1a: Rave explainer — trimmed, scaled to 1080x1920
    rave_exp_out = os.path.join(clips_dir, "rave_explainer.mp4")
    rave_exp_full_dur = get_duration(RAVE_EXPLAINER)
    rave_exp_trim_dur = rave_exp_full_dur - RAVE_EXP_TRIM
    print(f"  Preparing rave explainer ({rave_exp_full_dur:.1f}s -> {rave_exp_trim_dur:.1f}s)...")
    run([
        "ffmpeg", "-y", "-i", RAVE_EXPLAINER,
        "-t", str(rave_exp_trim_dur),
        "-vf", SCALE_FILTER,
        "-r", "30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-pix_fmt", "yuv420p",
        rave_exp_out
    ], "rave explainer")
    rave_exp_dur = get_duration(rave_exp_out)

    # 1b: Rave screen recording — trim, mute, add Venjent audio + text overlay
    rave_rec_out = os.path.join(clips_dir, "rave_recording.mp4")
    rave_dur = RAVE_REC_END - RAVE_REC_START
    font_esc = FONT_FILE.replace("\\", "/").replace(":", "\\:")
    rave_text = (
        f"drawtext=text='the rave in question':"
        f"fontfile='{font_esc}':"
        f"fontsize=48:fontcolor=white:borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:y=(h*3/4)"
    )
    print("  Preparing rave recording + Venjent audio + text overlay...")
    run([
        "ffmpeg", "-y",
        "-ss", str(RAVE_REC_START), "-t", str(rave_dur), "-i", RAVE_RECORDING,
        "-ss", str(VENJENT_START), "-t", str(rave_dur), "-i", VENJENT_SONG,
        "-filter_complex", f"[0:v]crop=1080:min(1920\\,ih):0:(ih-min(1920\\,ih))/2,{SCALE_FILTER},{rave_text}[v]",
        "-map", "[v]", "-map", "1:a",
        "-r", "30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-pix_fmt", "yuv420p",
        "-shortest",
        rave_rec_out
    ], "rave recording")
    rave_rec_dur = get_duration(rave_rec_out)

    print(f"  Rave explainer: {rave_exp_dur:.1f}s")
    print(f"  Rave recording: {rave_rec_dur:.1f}s")
    return rave_exp_out, rave_rec_out, rave_exp_dur, rave_rec_dur


# ── STEP 2: MAIN CLIP SEGMENTS ──────────────────────────────────────────

def build_keep_segments(words):
    segments = []
    current_start = None

    for i, w in enumerate(words):
        if i <= EP02_LAST_WORD:
            if i not in CUT_INDICES:
                if current_start is None:
                    current_start = i
            else:
                if current_start is not None:
                    segments.append((current_start, i - 1))
                    current_start = None

    if current_start is not None:
        segments.append((current_start, min(EP02_LAST_WORD, len(words) - 1)))

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


def extract_main_segments(segments, is_last_with_fade=True):
    clips_dir = os.path.join(SCRIPT_DIR, "clips")
    paths = []

    for i, seg in enumerate(segments):
        out_path = os.path.join(clips_dir, f"main_{i:03d}.mp4")
        duration = round(seg["end"] - seg["start"], 3)

        # Last segment gets a long fade-out for transition to black card
        if is_last_with_fade and i == len(segments) - 1:
            fade_out_start = max(0, duration - 1.5)
            vf = f"{SCALE_FILTER},fade=out:st={fade_out_start:.3f}:d=1.5"
            af = f"afade=t=in:st=0:d=0.03,afade=t=out:st={fade_out_start:.3f}:d=1.5"
        else:
            fade_out_start = max(0, duration - 0.03)
            vf = SCALE_FILTER
            af = f"afade=t=in:st=0:d=0.03,afade=t=out:st={fade_out_start:.3f}:d=0.03"

        print(f"  Extracting main segment {i} [{seg['start']:.1f}s-{seg['end']:.1f}s]...")
        run([
            "ffmpeg", "-y",
            "-ss", str(seg["start"]), "-i", MAIN_CLIP, "-t", str(duration),
            "-vf", vf,
            "-af", af,
            "-r", "30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-pix_fmt", "yuv420p",
            out_path
        ], f"main seg {i}")
        paths.append(out_path)

    return paths


# ── STEP 3: ENDING CARD ─────────────────────────────────────────────────

def create_ending_card():
    clips_dir = os.path.join(SCRIPT_DIR, "clips")
    card_path = os.path.join(clips_dir, "ending_card.mp4")
    card_dur = 2.5

    font_escaped = FONT_FILE.replace("\\", "/").replace(":", "\\:")
    drawtext = (
        f"drawtext=text='continues in Episode 3':"
        f"fontfile='{font_escaped}':"
        f"fontsize=42:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2,"
        f"fade=in:d=0.8"
    )

    print("  Creating ending card...")
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=black:s=1080x1920:d={card_dur}:r=30",
        "-f", "lavfi", "-i", f"anullsrc=cl=stereo:r=44100",
        "-t", str(card_dur),
        "-vf", drawtext,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
        "-shortest",
        card_path
    ], "ending card")

    return card_path, card_dur


# ── STEP 4: CONCAT ──────────────────────────────────────────────────────

def concat_all(clip_paths):
    entries = [f"file '{p}'" for p in clip_paths]
    with open(SEGMENTS_LIST, "w") as f:
        f.write("\n".join(entries))

    print(f"\nConcatenating {len(clip_paths)} clips...")
    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", SEGMENTS_LIST,
        "-c", "copy",
        OUTPUT
    ], "concat")


# ── STEP 5: SUBTITLES ───────────────────────────────────────────────────

def format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def chunk_words_to_subs(raw_words, output_time, seg_duration):
    """Split words into 2-3 word subtitle chunks. Returns (events, new_output_time)."""
    events = []
    if not raw_words:
        return events, output_time + seg_duration

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

    return events, output_time + seg_duration


def generate_subtitles(intro_seg, rave_exp_dur, rave_rec_dur, story_segments):
    """Generate subs in clip order: intro → rave explainer → (no subs) → story segments."""
    header = r"""[Script Info]
Title: Webdune Diaries S01E02
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
    all_events = []
    output_time = 0.0

    # 1. Intro segment subs ("Hello everybody...")
    intro_dur = intro_seg["end"] - intro_seg["start"]
    intro_words = intro_seg["text"].split()
    events, output_time = chunk_words_to_subs(intro_words, output_time, intro_dur)
    all_events.extend(events)

    # 2. Rave explainer subtitles
    rave_words = load_words(RAVE_TRANSCRIPT)
    rave_text = []
    for w in rave_words:
        t = w["text"].strip()
        for wrong, right in TEXT_CORRECTIONS.items():
            t = t.replace(wrong, right)
        rave_text.append(t)
    events, output_time = chunk_words_to_subs(rave_text, output_time, rave_exp_dur)
    all_events.extend(events)

    # 3. No subs during rave recording
    output_time += rave_rec_dur

    # 4. Story segments (main clip after intro)
    for seg in story_segments:
        seg_dur = seg["end"] - seg["start"]
        words = seg["text"].split()
        events, output_time = chunk_words_to_subs(words, output_time, seg_dur)
        all_events.extend(events)

    with open(SUBS_FILE, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(all_events))
        f.write("\n")

    return output_time


# ── MAIN ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("EP02 Build Edit — Intro > Rave hook > Origin story")
    print("=" * 60)

    # Step 1: Rave clips
    print("\nStep 1: Preparing rave clips...")
    rave_exp_path, rave_rec_path, rave_exp_dur, rave_rec_dur = prepare_rave_clips()

    # Step 2: Main clip segments
    print("\nStep 2: Building main clip segments...")
    words = load_words(MAIN_TRANSCRIPT)
    print(f"  {len(words)} words in transcript")
    print(f"  Using words 0-{EP02_LAST_WORD}, cutting {len(CUT_INDICES)} words")

    segments = build_keep_segments(words)
    total_main = sum(s["end"] - s["start"] for s in segments)
    print(f"  {len(segments)} segments, ~{total_main:.1f}s of main clip content")

    for i, seg in enumerate(segments):
        dur = seg["end"] - seg["start"]
        preview = seg["text"][:70]
        print(f"  [{i:2d}] {seg['start']:6.1f}s-{seg['end']:6.1f}s ({dur:4.1f}s) {preview}...")

    main_paths = extract_main_segments(segments)

    # Split: first segment is intro, rest is story
    intro_seg = segments[0]
    story_segments = segments[1:]
    intro_path = main_paths[0]
    story_paths = main_paths[1:]

    # Step 3: Ending card
    print("\nStep 3: Creating ending card...")
    card_path, card_dur = create_ending_card()

    # Step 4: Concat in new order — intro → rave → story → ending
    print("\nStep 4: Concatenating (intro > rave > story > ending)...")
    all_clips = [intro_path, rave_exp_path, rave_rec_path] + story_paths + [card_path]
    concat_all(all_clips)

    # Step 5: Subtitles (matching new clip order)
    print("\nStep 5: Generating subtitles...")
    sub_dur = generate_subtitles(intro_seg, rave_exp_dur, rave_rec_dur, story_segments)
    print(f"  Subtitles: {SUBS_FILE} ({sub_dur:.1f}s)")

    # Verify
    final_dur = get_duration(OUTPUT)
    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    rave_total = rave_exp_dur + rave_rec_dur
    print(f"\n{'=' * 60}")
    print(f"  Output: {OUTPUT}")
    print(f"  Duration: {final_dur:.1f}s")
    print(f"  Size: {size_mb:.1f} MB")
    print(f"  Under 90s: {'YES' if final_dur < 90 else 'NO — needs more cuts'}")
    print(f"  Breakdown: intro {intro_seg['end']-intro_seg['start']:.1f}s + rave {rave_total:.1f}s + story {total_main - (intro_seg['end']-intro_seg['start']):.1f}s + card {card_dur:.1f}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
