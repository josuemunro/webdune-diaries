import json

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "transcript_raw.json"), "r", encoding="utf-8-sig") as f:
    data = json.load(f)

words = [w for w in data["words"] if w["type"] == "word"]
for i, w in enumerate(words):
    print(f"{i:3d} [{w['start']:6.2f}-{w['end']:6.2f}] {w['text']}")
