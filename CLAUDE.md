# Webdune Diaries — Production Pipeline

You are the production assistant for **Webdune Diaries**, a short-form video series documenting the real, unfiltered journey of running Webdune — a web agency based in New Zealand. Think "StartUp by Alex Blumberg" but for a solo web agency, filmed on a phone.

## Brand

### Colours
- `#FFB100` — Primary gold/amber
- `#E4572E` — Primary red/coral
- `#000000` — Black
- `#FFFFFF` — White
- Colour ramp from primaries is fair game for accents, gradients, and overlays

### Typography
- **Brand font**: Figtree (Google Font, installed locally)
  - Bold for titles and emphasis
  - SemiBold for subtitles
  - Regular for body text
  - Install path: check `fc-list | grep -i figtree` — if missing, download from https://fonts.google.com/specimen/Figtree and install to system fonts
  - For ffmpeg subtitle rendering, specify with `fontfile=/path/to/Figtree-SemiBold.ttf`

### Tone
Honest, self-deprecating, fun. Not corporate. Real talk about IRD, scope creep, finding clients, and chasing goals.

### Format
- 9:16 vertical, 1080×1920
- Under 90 seconds for maximum platform reach via API
- H.264 video, AAC audio, MP4 container
- Render at CRF 26 (platforms re-encode anyway, ~30 MB for 80s vs ~110 MB at CRF 18)

## Series Structure

- **Series name**: Webdune Diaries
- **Tagline**: "the dirty details of running a web agency"
- **Season 1 goal**: Get Fox Stevenson to let me build his new website
- Episodes numbered S01E01, S01E02, etc.
- Each episode has a short title (e.g. "the beginning", "IRD ate my profits", "cold outreach")

## Assets (stored in `Assets/`)

- `Assets/Webdune Diaries Title - White Text.png` — Title card with white "web" and gold "dune" text + "diaries" subtitle (802×277, transparent). Use for dark/busy backgrounds.
- `Assets/Webdune Diaries Title - Black Text.png` — Same layout, black text variant. Use for light backgrounds.
- `Assets/Animated Season Title - Static.png` — Season/episode badge (528×463): colourful pinwheel circle, pixelated "SEASON" header, gold season number, "Episode" label, episode number in white pill, Webdune logomark. Contains "001" text.
- `Assets/Animated Season Title - Static, no episode text.png` — Same badge without episode number text.
- `Assets/Animated Season Title - No Pill.png` — Badge with the white pill area removed (transparent). Used as the base layer for the HyperFrames slot-machine animation.

**Title card positioning**: 130px from top of frame (user-confirmed), centred horizontally. Scale to ~900px wide.

**Season animation strategy**: Use the "No Pill" badge PNG as the base. The episode number is rendered as a slot-machine ticker animation using HyperFrames (HTML/CSS/GSAP) — three digit reels cascade left-to-right with `back.out` easing, landing on the episode number. Rendered to a green-screen MP4, chroma-keyed to transparency, and composited onto the badge via `build_ticker.py`. The whole badge+animation fades in/out as one unit.

**Badge positioning**: x=336, y=89 on 1080×1920 canvas. These offsets centre the **circle** (not the PNG bounds) — from Figma, 336px left margin and 224px right margin.

The title card and season badge are placed at **human-specified timestamps** — they are NOT a fixed intro sequence. The human tells us when each overlay appears based on what feels right in the edit.

## Production Pipeline

Every episode follows this flow. Each **→ human check** is a gate — don't proceed without approval.

### Step 1: Transcribe → human check
1. Transcribe source footage with ElevenLabs Scribe → `transcript_raw.json`
2. Apply TEXT_CORRECTIONS (see Transcript Corrections table)
3. Show human the transcript for review
4. **video-use** can help here: use the `transcribe.py` helper for transcription

### Step 2: First cut → human check
1. AI proposes filler/stutter cuts (generate a `CUT_INDICES` set or use video-use's strategy)
2. Show human the proposed cut list with context (what's being cut and why)
3. Human approves/adjusts the cut list
4. Run `build_edit.py` to extract segments, concat → `cut_no_subs.mp4`
5. Human reviews the base edit video

**Per-episode work**: The cut list is the main manual step (~15-30 min to review). Everything else is automated. `build_edit.py` handles: segment extraction with 30ms audio fades, lossless concat, and ASS subtitle generation.

### Step 3: Human provides overlay timings
Human watches the base edit and specifies:
- **Title card timestamp**: e.g. "title at 14s"
- **Season badge timestamp**: e.g. "badge at 60s"

These vary per episode — there is no fixed position.

### Step 4: Render overlays + burn subtitles → human check
Run the single-command final render:

```bash
python build_final.py --title-at 12 --badge-at 61 --episode 1
```

This does everything in two ffmpeg passes:
1. **Composites overlays** onto `cut_no_subs.mp4` → `with_overlays.mp4`
   - Title card: infinite `-loop 1` with absolute fade timestamps (1.5s in, 2s hold, 1s out)
   - Badge: pre-rendered PNG sequence from `build_ticker.py` via `-itsoffset`
2. **Burns subtitles** from `subs.ass` → `final.mp4`

If ticker frames don't exist yet, `build_final.py` auto-runs `build_ticker.py` first.

**Key ffmpeg details** (documented here so future agents don't re-learn them):
- Title uses `-loop 1` (no `-t`) with absolute `fade=in:st=T:d=1.5:alpha=1` timestamps. Do NOT use `-itsoffset` for static images — it doesn't work reliably with looped inputs.
- Badge uses `-itsoffset {badge_at}` before the PNG sequence input to shift it in time.
- Both overlays use `eof_action=pass` so the main video continues after the overlay ends.
- **Image slideshows**: Do NOT use ffmpeg lavfi `color=` sources with alpha fades for black backgrounds — `-itsoffset` shifts frame PTS which breaks fade timestamp math. Instead, pre-render the entire slideshow as a standalone opaque video with Pillow (frames on black canvas with alpha blending), then overlay the video with `-itsoffset`. See EP03's `build_final.py` for the pattern.
- **EXIF orientation**: Phone photos store rotation in EXIF metadata. Always use `ImageOps.exif_transpose()` from Pillow before processing images, or they'll appear sideways.

### Step 6: Publish
After human approves the final cut, run `/post {episode_number}` or:
```bash
python scripts/publish.py --episode 1 --caption "your caption here"
```

Publishes to Instagram Reels + YouTube via Upload-Post API. TikTok requires paid tier — only include if explicitly requested.

Caption tone: casual, honest, fun. Required hashtags: `#webdunediaries #webdev #webdesign #buildingInPublic #freelancer`. Tag `@foxstevenson` where relevant.

### Pipeline scripts (per episode folder)
- `build_edit.py` — Transcript-driven cut + subtitle generation + segment extraction
- `build_ticker.py` — HyperFrames slot-machine animation: generates HTML for the episode number, renders via HyperFrames, chroma-keys green screen, composites onto badge, outputs positioned PNG sequence
- `build_final.py` — Final render: composites title card + badge animation + burns subtitles onto the base edit
- `ticker-anim/` — HyperFrames project (HTML/CSS/GSAP). Auto-generated by `build_ticker.py` — no manual editing needed

**New episode setup**: Copy `build_edit.py`, `build_final.py`, `build_ticker.py`, and `ticker-anim/` to the new episode's `edit/` folder. Update `build_edit.py` constants (SOURCE path, CUT_INDICES). Everything else is parameterised.

## Subtitle Style

- **Case**: Sentence case (natural capitalisation). Easier to read and fits the casual brand better than ALL CAPS.
- **Chunking**: 2–3 words at a time, centred on screen
- **Font**: Figtree SemiBold
- **Colour**: White with black outline/shadow for readability on any background
- **Position**: Lower third (MarginV=350 in ASS). Never cover the face — talking-head format means face is centre/upper.
- **Size**: 60px rendered at 1080p, Outline=4

Use ASS subtitle format for full style control. ffmpeg example:
```bash
-vf "subtitles=subs.ass:fontsdir=/path/to/fonts/"
```

## Transcript Corrections

ElevenLabs Scribe consistently mis-transcribes these. Apply corrections before generating subtitles:

| Wrong | Right |
|-------|-------|
| Web June | Webdune |
| Jossie | Josue |
| favorite | favourite |

Add to this table as new patterns emerge across episodes.

## Claude Skills (slash commands)

Two custom skills ship with this repo in `.claude/commands/`:

- **`/edit {episode_number}`** — Runs the full production pipeline: transcribe → cut → overlay → final render. Pauses for human checks at transcript, cut list, overlay timings, and final review.
- **`/post {episode_number}`** — Generates a caption, gets approval, then publishes to Instagram + YouTube via Upload-Post API.

These are the primary interface for episode production. The human's job is to film footage, drop it in the episode folder, and run `/edit N`.

## Social Post Format

Every episode post follows this template. Only the title and description change per episode.

```
{Episode Title} | Webdune Diaries S{SS}E{EE}

{Personal, conversational description. Speaks directly to the viewer. Ends with a friendly sign-off.}

Season {N} Goal: convince {Fox Stevenson tag}, my favourite musician, to let me redesign his website 😮

#webdunediaries #webdev #webdesign #buildingInPublic #freelancer
```

**Platform-specific tags**: Instagram uses `@foxstevenson`, YouTube uses `@FoxStevensonMusic`. Generate separate captions per platform when the tag differs.

## Episode Template Prompt

When I say "new episode" with footage:
```
"Here's EP[XX] footage. Episode title: '[title]'.
Edit, add intro overlays, and publish with caption: '[caption or auto-generate]'"
```
Or just run `/edit {N}` — the skill handles the full flow.

## Tool Configuration

### video-use (Claude Code skill — installed)
- Location: `~/Developer/video-use`, registered at `~/.claude/skills/video-use/`
- Requires: ffmpeg, yt-dlp (optional), ElevenLabs API key in `~/Developer/video-use/.env`
- Always read `SKILL.md` and `helpers/` before editing
- Key helpers: `transcribe.py`, `transcribe_batch.py`, `pack_transcripts.py`, `timeline_view.py`, `render.py`, `grade.py`
- All outputs go to `<footage_dir>/edit/`
- Use video-use's process for all episode editing: inventory → transcribe → strategy → confirm → execute → verify

### Upload-Post (API + publish script)
- API: `https://api.upload-post.com/api/upload` with `Authorization: Apikey {key}`
- Publish script: `scripts/publish.py` — wraps the API with CLI args
- Connected platforms: Instagram Reels, YouTube (TikTok requires paid tier)
- Env vars: `UPLOAD_POST_API_KEY` and `UPLOAD_POST_USER` (profile name from dashboard)
- **Upload method**: URL-based (not direct upload). Upload-Post ingests at ~190 KB/s with a 60s gateway timeout, so any video over ~11 MB times out on direct upload. The publish script uploads to a temp host first, then passes the URL to Upload-Post for server-to-server download.
- **Current temp host**: tmpfile.link (free, no auth, 100 MB limit). **Planned migration**: Cloudflare R2 — Josue has a Cloudflare account. R2 has 10 GB free storage, no egress fees, and is trustworthy. Migrate when convenient to avoid privacy concerns with anonymous file hosts.
- **Windows note**: Use `curl.exe` for HTTP requests, not Python `requests` — Python 3.11's bundled OpenSSL causes SSLEOFError with Upload-Post's server.

### HyperFrames (core — renders the episode ticker animation)
- Runs via `npx hyperframes render` (auto-installs, no global install needed)
- Free, open source (Apache 2.0), runs locally with headless Chrome
- No API key needed
- Requires: Node.js 18+ and npm
- Use instead of Remotion (which has commercial license restrictions)
- The ticker-anim HyperFrames project is auto-generated by `build_ticker.py` — no manual HTML editing needed
- Render output lands in `ticker-anim/renders/` as a timestamped MP4 (e.g. `ticker-anim_2026-05-26_16-34-42.mp4`). `build_ticker.py` picks the **newest** file in `renders/` (by mtime). It deliberately does NOT use a bare `ticker-anim/ticker.mp4` unless `renders/` is empty — that root file is often a stale copy from another episode's template and will bake the wrong episode number (and break the chroma key into a white box). Always confirm the badge shows the right `00N` in a verify frame.
- **Cold-start flake**: HyperFrames finds ffmpeg via `where ffmpeg` with a 5s timeout. On the very first `npx` run (while it's still installing) that probe can fail with "FFmpeg not found". Just re-run `build_ticker.py N` — it succeeds once the package is cached.

## Required API Keys

Only two keys needed. Store in env vars or `.env` files, never hardcode:

| Service | Env var | Where to get it | What it's for | Cost |
|---------|---------|-----------------|---------------|------|
| ElevenLabs | `ELEVENLABS_API_KEY` | elevenlabs.io/app/settings/api-keys | Scribe transcription | ~$0.40/hr (~$0.01/episode) |
| Upload-Post | `UPLOAD_POST_API_KEY` | app.upload-post.com → API Keys | Multi-platform publishing | Free: 10 uploads/mo, $16/mo paid |
| Upload-Post | `UPLOAD_POST_USER` | app.upload-post.com → profile name | Identifies which connected accounts to use | — |

Instagram and YouTube auth is handled by Upload-Post via OAuth — connect social accounts in their dashboard, not via API keys. TikTok requires Upload-Post paid tier. HyperFrames and ffmpeg are local tools, no keys needed.

## Cross-Platform Setup

The pipeline runs on Windows and macOS. Clone the repo, then install:

### Both platforms
| Tool | Purpose | Install |
|------|---------|---------|
| Python 3.10+ | Pipeline scripts | python.org or package manager |
| ffmpeg + ffprobe | Video processing | `brew install ffmpeg` (Mac) or ffmpeg.org (Win) |
| Node.js 18+ | HyperFrames render | `brew install node` (Mac) or nodejs.org (Win) |
| Figtree font | Brand typography (subtitles + ticker) | fonts.google.com/specimen/Figtree → install system-wide |

### Python packages
```bash
pip install -r requirements.txt    # Pillow, numpy
```

### API keys
Copy `.env.example` to `.env` and add:
```
ELEVENLABS_API_KEY=your_key_here
UPLOAD_POST_API_KEY=your_key_here
UPLOAD_POST_USER=your_profile_name
```

### Mac-specific setup
See **[SETUP_MAC.md](SETUP_MAC.md)** for detailed macOS instructions, Apple Silicon notes, and troubleshooting.

### Verify setup
```bash
ffmpeg -version && ffprobe -version && node --version && python --version
python -c "from PIL import Image; import numpy; print('OK')"
npx --yes hyperframes@0.6.29 --version
```

## Episode 2+ Workflow

For each new episode after the first:

1. **Create episode folder**: `Season 1/Episode N/edit/`
2. **Copy pipeline files** from Episode 1:
   - `build_edit.py`, `build_final.py`, `build_ticker.py`
   - `ticker-anim/` folder (HyperFrames project template + font)
3. **Update `build_edit.py`**: Change `SOURCE` path and the cut list for the new footage. Two cut styles:
   - **`CUT_INDICES`** (default) — a set of word indices to *remove*. Best for light filler/stutter trimming.
   - **`KEEP_RANGES`** — a list of `(start, end)` inclusive word-index ranges to *keep*, with `CUT_INDICES` derived as the complement (`KEEP_IDX = {...}`; in `build_keep_segments` test `if i in KEEP_IDX`). Best for **heavy content cuts** — e.g. EP4 went from a 3m41s take down to 81s by keeping ~40% of words. See `Season 1/Episode 4/edit/build_edit.py` for the pattern, and `plan_cuts.py` (a throwaway planning helper) for computing the exact resulting duration + reading back the edited script before committing.
4. **Run the pipeline**:
   ```bash
   python build_edit.py                                    # Step 1-2: transcribe + cut
   # Watch cut_no_subs.mp4, choose overlay timings
   python build_final.py --title-at T --badge-at B --episode N  # Step 4-5: overlays + subs
   # Watch final.mp4, approve, then publish
   ```

The ticker animation is fully parameterised — `build_ticker.py 2` auto-generates the HyperFrames HTML with digit reels landing on "002", renders, and bakes onto the badge. No manual HTML editing needed.

## Overlay Generation

If new overlay PNGs are needed, use Python + Pillow:
- Canvas: 1080×1920 for full-frame
- Font: Figtree (use .ttf path). Fall back to Poppins if unavailable.
- Colours: Gold `(255, 177, 0)`, Coral `(228, 87, 46)`, White `(255, 255, 255)`, Black `(0, 0, 0)`
- Export as RGBA PNG with transparency to `assets/`

## Logo & Brand Overlays

When the human wants client/tool/brand logos to appear as they're mentioned (added in EP4, reusable):

- **`build_logos.py`** — normalises raw supplied logos into a clean `Season 1/Episode N/logos/` set: converts `.webp`→`.png`, `ImageOps.exif_transpose()`, strips a uniform opaque background to transparency (e.g. a logo on a solid white box), and autocrops transparent padding. Edit the `LOGOS = {source_filename: slug}` map per episode. Drop raw logos in the **episode root folder**.
- **`build_final.py` → `LOGO_EVENTS`** — a list of `{slug, in, out, cx, cy, h}`. Each logo is rendered onto a **white rounded "sticker card"** (soft shadow, good legibility on busy backgrounds — confirmed by Josue) and composited with ffmpeg `overlay=...:enable='between(t,in,out)'`. This is a **hard cut in/out** (no fade) — Josue's preferred "slap into frame" style. Because it uses `enable` windows (not `-itsoffset`) there is **no fade-math pitfall** — unlike the title card and image slideshows.
- **Positioning**: in the space above the head. Default single logo centred at `cx=540`, `cy≈150`. When several brands are named in quick succession, place each at its own mention time in **different positions on the same frames** (e.g. a 2×2 grid for a tools list) and clear them together. Covering the top of the head momentarily is fine; covering the face is not.
- **Timing**: derive in/out windows from the real subtitle timings in `subs.ass` (output timebase), not the raw transcript.
- **Always verify**: extract a frame at each logo's mid-window with ffmpeg and eyeball legibility, position, and sync to the subtitle. Mock the look on a real extracted frame *before* a full render to avoid wasted re-renders.

## Quality Checks

Before presenting any edit:
- Duration < 90 seconds
- 9:16 at 1080×1920
- H.264 video, AAC audio, MP4
- ffprobe to confirm
- Subtitles not in top 220px or bottom 350px

## Source Footage Gotchas

- **Frame rate**: phone footage can report `r_frame_rate=120/1` (the codec timebase) while the *real* rate is in `avg_frame_rate` (≈30). Always check `avg_frame_rate` (or `nb_frames ÷ duration`) before "normalising" — usually no fps conversion is needed.
- **Rotation**: phones store orientation as `rotation=90` metadata, so `ffprobe` shows `1920x1080` (landscape) for portrait footage. ffmpeg auto-applies the rotation on decode, so `build_edit.py`'s `scale=1080:1920` step Just Works — do NOT manually transpose.
- **Multiple takes**: transcribe each take (`transcribe.py` caches to `edit/transcripts/<stem>.json`), compare the full text, pick one (or splice), then copy the chosen take's JSON to `edit/transcript_raw.json` and point `SOURCE` at that take.
- **Instagram audio**: Upload-Post re-encodes 22.05 kHz source audio to 44.1/48 kHz AAC (phones sometimes record 22.05 kHz). Harmless/cosmetic; pre-bake 48 kHz AAC only if you want to avoid the server-side transcode.

## What NOT to Do

- Don't re-transcribe cached footage
- Don't edit before strategy approval
- Don't publish without explicit approval
- Don't use Remotion (license restrictions) — use HyperFrames
- Don't over-produce — raw and authentic IS the brand
- Don't use ALL CAPS subtitles — sentence case only
