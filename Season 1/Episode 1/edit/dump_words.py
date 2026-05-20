import json

with open(r"E:\Josue Munro\Documents\Projects\WebDune\Webdune Diaries\Season 1\Episode 1\edit\transcript_raw.json", "r", encoding="utf-8-sig") as f:
    data = json.load(f)

words = [w for w in data["words"] if w["type"] == "word"]
for i, w in enumerate(words):
    print(f"{i:3d} [{w['start']:6.2f}-{w['end']:6.2f}] {w['text']}")
