# Webdune Diaries — Mac Setup

Setup guide for running the production pipeline on macOS (tested on M2 MacBook).

## Prerequisites

### 1. Homebrew packages

```bash
brew install python ffmpeg node
```

Verify:
```bash
ffmpeg -version && ffprobe -version && node --version && python3 --version
```

### 2. Python packages

```bash
pip3 install -r requirements.txt
```

This installs `Pillow` (image processing) and `numpy` (chroma keying).

For publishing, also install:
```bash
pip3 install requests python-dotenv
```

### 3. Figtree font

Download from [Google Fonts](https://fonts.google.com/specimen/Figtree) and install system-wide:
1. Download the font family ZIP
2. Open Font Book
3. Drag all `.ttf` files into Font Book
4. The pipeline uses Figtree SemiBold for subtitles and Figtree Bold for the ticker animation

Verify:
```bash
fc-list | grep -i figtree
```

### 4. API keys

Copy `.env.example` to `.env` (or create `.env` in the project root):

```
ELEVENLABS_API_KEY=your_key_here
UPLOAD_POST_API_KEY=your_key_here
UPLOAD_POST_USER=your_profile_name
```

- **ElevenLabs**: Get from [elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys)
- **Upload-Post**: Get from [app.upload-post.com](https://app.upload-post.com) → API Keys. Connect Instagram + YouTube via OAuth in their dashboard.

## Running an episode

```bash
# Full pipeline via Claude Code skill:
/edit 2

# Or manually:
cd "Season 1/Episode 2/edit"
python3 build_edit.py                                         # cut + subtitles
python3 build_final.py --title-at 12 --badge-at 61 --episode 2  # overlays + subs
python3 ../../../scripts/publish.py --episode 2 --caption "..."  # publish

# Just the ticker animation:
python3 build_ticker.py 2
```

## Mac-specific notes

### ffmpeg subtitle path escaping

On Mac, ffmpeg filter paths use forward slashes and colons need escaping:
```
subtitles='path/to/subs.ass':fontsdir='path/to/fonts/'
```

The `build_final.py` script handles this automatically via the `escape_path()` function — it works on both Windows and Mac.

### HyperFrames rendering

HyperFrames uses headless Chromium via Puppeteer. On first run, `npx hyperframes render` will download Chromium (~170 MB). Subsequent runs use the cached version.

On Apple Silicon Macs, if you see Chromium-related errors:
```bash
# Ensure Rosetta 2 is installed (usually already present)
softwareupdate --install-rosetta --agree-to-license
```

### Font paths

Mac font directories:
- User fonts: `~/Library/Fonts/`
- System fonts: `/Library/Fonts/`

The pipeline scripts reference the font via the `Assets/fonts/` directory in the repo, so as long as the font file is there, it works cross-platform.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ffmpeg: command not found` | `brew install ffmpeg` |
| `ModuleNotFoundError: PIL` | `pip3 install Pillow` |
| `npx: command not found` | `brew install node` |
| Font not rendering in subtitles | Install Figtree system-wide via Font Book |
| HyperFrames Chromium error on M2 | Install Rosetta 2 (see above) |
| `ELEVENLABS_API_KEY not set` | Add to `.env` in project root |
