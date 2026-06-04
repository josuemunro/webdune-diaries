# Publish Episode

Publish Webdune Diaries Episode **$ARGUMENTS** to Instagram Reels and YouTube.

Read `CLAUDE.md` first for brand tone and hashtag guidelines.

## Setup

```
EPISODE = $ARGUMENTS
EP_DIR = "Season 1/Episode {EPISODE}/edit/"
VIDEO = EP_DIR + "final.mp4"
```

1. Verify `final.mp4` exists in EP_DIR
2. Run ffprobe to confirm it meets platform requirements:
   - H.264 video, AAC audio, MP4 container
   - 1080x1920 (9:16)
   - Duration: under 90s for Instagram Reels, under 180s for YouTube Shorts
3. Load API key: read `UPLOAD_POST_API_KEY` from the `.env` file in the project root
4. Load profile name: read `UPLOAD_POST_USER` from `.env` — if missing, ask the human for their Upload-Post profile name

## Generate caption

Write a caption that matches the Webdune Diaries brand tone: honest, self-deprecating, fun. Not corporate.

Structure:
- **Line 1**: Hook or episode title (casual, conversational)
- **Line 2-3**: 1-2 sentences about what happens in this episode
- **Line 4**: Call to action or teaser for next episode
- **Line 5**: Hashtags

Required hashtags: `#webdunediaries #webdev #webdesign #buildingInPublic #freelancer`
Optional extras based on episode content: `#solopreneur #webdeveloper #nztech #agencylife`

If the episode mentions Fox Stevenson, tag `@foxstevenson` in the caption.

**HUMAN CHECK**: Show the generated caption. Wait for approval or edits. Also confirm:
- "Publishing to: Instagram Reels + YouTube"
- "Profile: {UPLOAD_POST_USER}"
- "Video: final.mp4 ({duration}s, {size_mb:.1f} MB)"

Do NOT proceed until the human explicitly approves.

## Publish

Generate platform-specific captions (Instagram uses `@foxstevenson`, YouTube uses `@FoxStevensonMusic`). Then run the publish script:

```bash
python scripts/publish.py --episode {EPISODE} --caption "INSTAGRAM_CAPTION" --yt-title "YOUTUBE_TITLE" --yt-desc "YOUTUBE_DESCRIPTION"
```

The script handles the two-step upload automatically: uploads to file.io first (fast), then passes the URL to Upload-Post (avoids gateway timeouts on direct upload). It polls for async results and prints platform URLs when done.

## After publishing

1. Check the response for success/failure per platform
2. Extract and show the URLs:
   - Instagram: `result["results"]["instagram"]["url"]`
   - YouTube: `result["results"]["youtube"]["url"]`
3. Report to the human:
   ```
   Published Episode {EPISODE}!
   Instagram: {url}
   YouTube: {url}
   ```
4. If any platform failed, show the error and suggest fixes

## Important rules

- NEVER publish without explicit human approval of the caption and platform list
- NEVER hardcode the API key — always read from .env
- If the API key is missing, tell the human to add `UPLOAD_POST_API_KEY` to their `.env` file
- If the profile name is missing, ask the human — they set it up at app.upload-post.com
- TikTok requires a paid Upload-Post tier — only include if the human explicitly asks
