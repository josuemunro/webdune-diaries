"""
Publish a Webdune Diaries episode to social platforms via Upload-Post API.

Uses file.io as an intermediary to avoid Upload-Post's slow ingestion
causing gateway timeouts on direct file uploads.

Usage:
    python scripts/publish.py --episode 1 --caption "caption here"
    python scripts/publish.py --episode 1 --caption "caption" --platforms instagram youtube
    python scripts/publish.py --episode 1 --caption "caption" --yt-title "YT Title" --yt-desc "YT desc"
    python scripts/publish.py --episode 1 --caption "caption" --dry-run
"""
import argparse
import io
import os
import sys
import json
import subprocess
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

API_URL = "https://api.upload-post.com/api/upload"
STATUS_URL = "https://api.upload-post.com/api/uploadposts/status"

VALID_PLATFORMS = ["instagram", "youtube", "tiktok"]
DEFAULT_PLATFORMS = ["instagram", "youtube"]


def load_env():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if load_dotenv:
        load_dotenv(env_path)
    elif os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def upload_to_tmphost(video_path, size_mb):
    """Upload video to tmpfile.link and return the temporary public URL."""
    print(f"\n  Step 1: Uploading {size_mb:.1f} MB to temporary file host (tmpfile.link)...")
    cmd = [
        "curl.exe", "-s", "-S",
        "--connect-timeout", "30",
        "--max-time", "300",
        "-H", "Accept: application/json",
        "-F", f"file=@{video_path}",
        "https://tmpfile.link/api/upload",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"  ERROR: tmpfile.link upload failed: {result.stderr}")
        sys.exit(1)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  ERROR: unexpected response: {result.stdout[:500]}")
        sys.exit(1)

    url = data.get("downloadLink")
    if not url:
        print(f"  ERROR: no download link in response: {json.dumps(data)}")
        sys.exit(1)

    print(f"  Hosted at: {url}")
    return url


def publish_via_url(api_key, video_url, user, caption, platforms, yt_title=None, yt_desc=None):
    """Send the file.io URL to Upload-Post API."""
    print("\n  Step 2: Publishing via Upload-Post...")
    cmd = [
        "curl.exe", "-s", "-S",
        "--connect-timeout", "30",
        "--max-time", "120",
        "-X", "POST", API_URL,
        "-H", f"Authorization: Apikey {api_key}",
        "-F", f"video={video_url}",
        "-F", f"user={user}",
        "-F", f"title={caption}",
        "-F", "async_upload=true",
    ]

    for p in platforms:
        cmd += ["-F", f"platform[]={p}"]

    if "instagram" in platforms:
        cmd += ["-F", "media_type=REELS"]
    if "youtube" in platforms:
        cmd += ["-F", "privacyStatus=public"]
        if yt_title:
            cmd += ["-F", f"youtube_title={yt_title}"]
        if yt_desc:
            cmd += ["-F", f"youtube_description={yt_desc}"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"  ERROR: Upload-Post request failed: {result.stderr}")
        sys.exit(1)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  Raw response:\n{result.stdout[:1000]}")
        sys.exit(1)

    return data


def poll_status(api_key, request_id, platforms, max_wait=180):
    """Poll Upload-Post for async upload results."""
    print(f"  Polling for results (up to {max_wait}s)...")
    attempts = max_wait // 10

    for attempt in range(attempts):
        time.sleep(10)
        cmd = [
            "curl.exe", "-s", "--max-time", "15",
            "-H", f"Authorization: Apikey {api_key}",
            f"{STATUS_URL}?request_id={request_id}",
        ]
        sr = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if sr.returncode == 0 and sr.stdout.strip():
            try:
                sd = json.loads(sr.stdout)
                results = sd.get("results", [])
                if isinstance(results, dict):
                    items = list(results.values())
                elif isinstance(results, list):
                    items = results
                else:
                    items = []
                done = all(
                    r.get("success") is not None for r in items
                ) if items else False

                if done or sd.get("completed"):
                    print(json.dumps(sd, indent=2, ensure_ascii=False))
                    print("\n=== Published! ===")
                    for r in items:
                        p = r.get("platform", "unknown")
                        if r.get("success") and r.get("url"):
                            print(f"  {p}: {r['url']}")
                        elif r.get("success") is False:
                            print(f"  {p}: FAILED - {r.get('error', 'unknown')}")
                    return True
            except json.JSONDecodeError:
                pass

        print(f"  ...still processing ({(attempt + 1) * 10}s)")

    print(f"\n  Still processing after {max_wait}s. Check status manually:")
    print(f'  curl -H "Authorization: Apikey YOUR_KEY" "{STATUS_URL}?request_id={request_id}"')
    return False


def main():
    parser = argparse.ArgumentParser(description="Publish episode to social platforms")
    parser.add_argument("--episode", type=int, required=True, help="Episode number")
    parser.add_argument("--caption", type=str, required=True, help="Post caption (used for Instagram)")
    parser.add_argument("--yt-title", type=str, default=None, help="YouTube title override")
    parser.add_argument("--yt-desc", type=str, default=None, help="YouTube description override")
    parser.add_argument("--platforms", nargs="+", default=DEFAULT_PLATFORMS,
                        choices=VALID_PLATFORMS, help="Target platforms")
    parser.add_argument("--user", type=str, default=None,
                        help="Upload-Post profile name (or set UPLOAD_POST_USER in .env)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be published without actually posting")
    parser.add_argument("--season", type=int, default=1, help="Season number")
    args = parser.parse_args()

    load_env()

    api_key = os.environ.get("UPLOAD_POST_API_KEY")
    if not api_key:
        print("ERROR: UPLOAD_POST_API_KEY not found in environment or .env file")
        print("Get your key from app.upload-post.com -> API Keys")
        sys.exit(1)

    user = args.user or os.environ.get("UPLOAD_POST_USER")
    if not user:
        print("ERROR: Upload-Post profile name required.")
        print("Set UPLOAD_POST_USER in .env or pass --user <name>")
        sys.exit(1)

    video_path = os.path.join(
        PROJECT_ROOT, f"Season {args.season}", f"Episode {args.episode}", "edit", "final.mp4"
    )
    if not os.path.exists(video_path):
        print(f"ERROR: Video not found: {video_path}")
        print(f"Run the edit pipeline first: /edit {args.episode}")
        sys.exit(1)

    size_mb = os.path.getsize(video_path) / (1024 * 1024)

    print(f"=== Publishing S{args.season:02d}E{args.episode:02d} ===")
    print(f"  Video: {video_path} ({size_mb:.1f} MB)")
    print(f"  Platforms: {', '.join(args.platforms)}")
    print(f"  Profile: {user}")
    print(f"  Caption: {args.caption[:80]}{'...' if len(args.caption) > 80 else ''}")

    if args.dry_run:
        print("\n  [DRY RUN] Would publish to the above platforms. Exiting.")
        return

    video_url = upload_to_tmphost(video_path, size_mb)

    data = publish_via_url(api_key, video_url, user, args.caption, args.platforms,
                           yt_title=args.yt_title, yt_desc=args.yt_desc)

    print(json.dumps(data, indent=2, ensure_ascii=False))

    if data.get("success"):
        req_id = data.get("request_id", "")
        print(f"\n=== Upload accepted! ===")
        print(f"  Request ID: {req_id}")
        if req_id:
            poll_status(api_key, req_id, args.platforms)
    else:
        print(f"\nAPI error: {data.get('message', json.dumps(data))}")
        sys.exit(1)


if __name__ == "__main__":
    main()
