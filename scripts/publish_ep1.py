"""One-shot publish for S01E01. Run: python scripts/publish_ep1.py"""
import os, sys, json, io, subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

api_key = os.environ.get("UPLOAD_POST_API_KEY")
if not api_key:
    print("ERROR: Set UPLOAD_POST_API_KEY in .env")
    sys.exit(1)

video = os.path.join(os.path.dirname(__file__), "..", "Season 1", "Episode 1", "edit", "final_upload.mp4")
if not os.path.exists(video):
    print(f"ERROR: {video} not found")
    sys.exit(1)

ig_caption = (
    "The Beginning | Webdune Diaries S01E01\n\n"
    "Starting a series about the ups and downs of being a freelance web dev / designer. "
    "I'll try my best to show the real side of what it's like - surviving the hard months "
    "with little work to juggling 5 projects at once. Whether you find it helpful, intriguing, "
    "concerning or a bit of fun I hope you come along for the ride! See you soon :)\n\n"
    "Season 1 Goal: convince @foxstevenson, my favourite musician, "
    "to let me redesign his website \U0001f62e\n\n"
    "#webdunediaries #webdev #webdesign #buildingInPublic #freelancer"
)

yt_title = "The Beginning | Webdune Diaries S01E01"
yt_desc = (
    "Starting a series about the ups and downs of being a freelance web dev / designer. "
    "I'll try my best to show the real side of what it's like - surviving the hard months "
    "with little work to juggling 5 projects at once. Whether you find it helpful, intriguing, "
    "concerning or a bit of fun I hope you come along for the ride! See you soon :)\n\n"
    "Season 1 Goal: convince @FoxStevensonMusic, my favourite musician, "
    "to let me redesign his website \U0001f62e\n\n"
    "#webdunediaries #webdev #webdesign #buildingInPublic #freelancer"
)

size_mb = os.path.getsize(video) / 1024 / 1024
print(f"=== Publishing S01E01 ({size_mb:.1f} MB) ===")
print(f"\nInstagram caption:\n{ig_caption}\n")
print(f"YouTube title: {yt_title}")
print(f"YouTube desc:\n{yt_desc}\n")

confirm = input("Publish to Instagram + YouTube? (y/n): ")
if confirm.lower() != "y":
    print("Cancelled.")
    sys.exit(0)

# Step 1: Upload to temp file host (tmpfile.link) to get a public URL.
# Upload-Post's server ingests files very slowly, causing gateway timeouts.
# Passing a URL instead lets their server download it server-to-server.
print(f"\nStep 1: Uploading {size_mb:.1f} MB to temporary file host...")
upload_cmd = [
    "curl.exe", "-s", "-S",
    "--connect-timeout", "30",
    "--max-time", "300",
    "-H", "Accept: application/json",
    "-F", f"file=@{video}",
    "https://tmpfile.link/api/upload",
]
upload_result = subprocess.run(upload_cmd, capture_output=True, text=True, timeout=300)

if upload_result.returncode != 0:
    print(f"ERROR: tmpfile.link upload failed: {upload_result.stderr}")
    sys.exit(1)

try:
    tmp_data = json.loads(upload_result.stdout)
except json.JSONDecodeError:
    print(f"ERROR: unexpected response: {upload_result.stdout[:500]}")
    sys.exit(1)

video_url = tmp_data.get("downloadLink")
if not video_url:
    print(f"ERROR: no download link in response: {json.dumps(tmp_data)}")
    sys.exit(1)

print(f"  Hosted at: {video_url}")

# Step 2: Send URL to Upload-Post (tiny request, no timeout issues)
print("\nStep 2: Publishing via Upload-Post...")
publish_cmd = [
    "curl.exe", "-s", "-S",
    "--connect-timeout", "30",
    "--max-time", "120",
    "-X", "POST",
    "https://api.upload-post.com/api/upload",
    "-H", f"Authorization: Apikey {api_key}",
    "-F", f"video={video_url}",
    "-F", "user=Webdune",
    "-F", "platform[]=instagram",
    "-F", "platform[]=youtube",
    "-F", f"title={ig_caption}",
    "-F", "media_type=REELS",
    "-F", f"youtube_title={yt_title}",
    "-F", f"youtube_description={yt_desc}",
    "-F", "privacyStatus=public",
    "-F", "async_upload=true",
]

publish_result = subprocess.run(publish_cmd, capture_output=True, text=True, timeout=120)

if publish_result.returncode != 0:
    print(f"ERROR: Upload-Post request failed: {publish_result.stderr}")
    sys.exit(1)

try:
    data = json.loads(publish_result.stdout)
except json.JSONDecodeError:
    print(f"Raw response:\n{publish_result.stdout[:1000]}")
    sys.exit(1)

print(json.dumps(data, indent=2, ensure_ascii=False))

if data.get("success"):
    req_id = data.get("request_id", "")
    print(f"\n=== Upload accepted! ===")
    print(f"  Request ID: {req_id}")

    if req_id:
        import time
        print("  Polling for results (up to 3 minutes)...")
        for attempt in range(18):
            time.sleep(10)
            status_cmd = [
                "curl.exe", "-s", "--max-time", "15",
                "-H", f"Authorization: Apikey {api_key}",
                f"https://api.upload-post.com/api/uploadposts/status?request_id={req_id}",
            ]
            sr = subprocess.run(status_cmd, capture_output=True, text=True, timeout=30)
            if sr.returncode == 0 and sr.stdout.strip():
                try:
                    sd = json.loads(sr.stdout)
                    results = sd.get("results", [])
                    if isinstance(results, dict):
                        items = results.values()
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
                        for r in (items if isinstance(results, list) else []):
                            p = r.get("platform", "unknown")
                            if r.get("success") and r.get("url"):
                                print(f"  {p}: {r['url']}")
                            elif r.get("success") is False:
                                print(f"  {p}: FAILED - {r.get('error', 'unknown')}")
                        break
                except json.JSONDecodeError:
                    pass
            print(f"  ...still processing ({(attempt+1)*10}s)")
        else:
            print(f"\n  Still processing. Check status manually:")
            print(f'  curl -H "Authorization: Apikey YOUR_KEY" "https://api.upload-post.com/api/uploadposts/status?request_id={req_id}"')
else:
    print(f"\nAPI error: {data.get('message', json.dumps(data))}")
