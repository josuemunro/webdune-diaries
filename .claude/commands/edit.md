# Episode Production Pipeline

Run the full Webdune Diaries production pipeline for Episode **$ARGUMENTS**.

Read `CLAUDE.md` first for brand guidelines, subtitle style, and quality checks.

## Setup

```
EPISODE = $ARGUMENTS
SEASON_DIR = "Season 1/Episode {EPISODE}/"
EP_DIR = "Season 1/Episode {EPISODE}/edit/"
```

1. Verify source footage exists in SEASON_DIR (an .mp4 file)
2. If EP_DIR doesn't exist, create it and copy pipeline files from Episode 1:
   - `build_edit.py`, `build_final.py`, `build_ticker.py`
   - `ticker-anim/` folder (entire directory including `assets/Figtree-SemiBold.ttf`)
3. Update `build_edit.py` in the new EP_DIR: change the `SOURCE` path to point at the new footage

## Pipeline

Execute these steps in order. Steps marked **HUMAN CHECK** require explicit approval before continuing.

### Step 1: Transcribe

1. Check if `transcript_raw.json` already exists in EP_DIR — if so, skip transcription
2. Otherwise, transcribe the source footage using ElevenLabs Scribe (via video-use `transcribe.py` helper or direct API call)
3. Apply TEXT_CORRECTIONS from CLAUDE.md (Web June → Webdune, Jossie → Josue, favorite → favourite)
4. **HUMAN CHECK**: Show the corrected transcript. Wait for approval or edits.

### Step 2: Propose cuts

1. Run `python dump_words.py` (if it exists) to get a word-level view, or read `transcript_raw.json` directly
2. Identify filler words, stutters, false starts, and long pauses to cut
3. Generate a `CUT_INDICES` set — the word indices to remove
4. **HUMAN CHECK**: Present the cut list with context — show what's being cut and the surrounding words. Format as a table:
   ```
   Index | Word     | Reason
   12    | "um"     | filler
   13-15 | "I I I"  | stutter
   ```
   Wait for approval or adjustments.

### Step 3: Build base edit

1. Update `CUT_INDICES` in `build_edit.py` with the approved cut list
2. Run `python build_edit.py` — this produces:
   - `cut_no_subs.mp4` (base edit without subtitles)
   - `subs.ass` (subtitle file)
   - `segments.txt`, `edl.json` (edit metadata)
3. Verify output with ffprobe: confirm 1080x1920, H.264, under 90 seconds
4. Tell the human: "Base edit is ready at `cut_no_subs.mp4` — please watch it and tell me:
   - **Title card timestamp**: when should 'Webdune Diaries' appear? (e.g., 'title at 12s')
   - **Season badge timestamp**: when should the season badge appear? (e.g., 'badge at 61s')"

### Step 4: Overlay timings — HUMAN CHECK

Wait for the human to provide:
- `--title-at T` (seconds for title card appearance)
- `--badge-at B` (seconds for season badge appearance)

Do NOT proceed until both timings are provided.

### Step 5: Final render

Run the single-command final render:
```bash
python build_final.py --title-at T --badge-at B --episode {EPISODE}
```

This automatically:
1. Builds the ticker animation if frames don't exist (calls `build_ticker.py {EPISODE}`)
2. Composites title card + badge animation onto the base edit
3. Burns subtitles from subs.ass
4. Outputs `final.mp4`

### Step 6: Quality check + final review

1. Run ffprobe on `final.mp4` and verify:
   - Duration < 90 seconds
   - Resolution: 1080x1920
   - Codec: H.264 video, AAC audio
   - Container: MP4
2. Extract verification frames at key timestamps:
   - Title card moment (title_at + 1.5s)
   - Badge moment (badge_at + 1.5s)
   - A subtitle moment
3. Show the frames to the human
4. **HUMAN CHECK**: "Final render is ready. Watch `final.mp4` and let me know if it looks good, or if you want timing/overlay adjustments."

### Step 7: Done

When approved, tell the human:
"Episode {EPISODE} is locked! Run `/post {EPISODE}` when you're ready to publish to Instagram and YouTube."

## Important rules

- Never proceed past a HUMAN CHECK without explicit approval
- Never publish without explicit approval
- If any step fails, show the error and suggest fixes — don't silently retry
- Subtitle style: sentence case, Figtree SemiBold, white with black outline, lower third (MarginV=350)
- ALL CAPS subtitles are banned — sentence case only
