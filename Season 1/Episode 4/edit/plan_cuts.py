"""Planning helper: define KEEP ranges, compute resulting duration + subtitle text.
Mirrors build_edit.py's pad/merge logic so the number is accurate before we commit.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "transcript_raw.json"), "r", encoding="utf-8-sig") as f:
    data = json.load(f)
words = [w for w in data["words"] if w["type"] == "word"]

PAD_BEFORE = 0.05
PAD_AFTER = 0.08
MIN_GAP_TO_MERGE = 0.30

TEXT_CORRECTIONS = {"Webjune": "Webdune", "Web June": "Webdune",
                    "Jossie": "Josue", "favorite": "favourite", "Fiver": "Fiverr"}

# Inclusive keep ranges (word indices). Everything else is cut.
KEEP = [
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
    (328, 331),   # I'm working for Hendricks.
    (333, 338),   # they're a web agency from Raglan.
    (339, 343),   # I'm doing some work with
    (345, 353),   # Onsite Media, they're a marketing digital agency from Tauranga.
    (355, 368),   # doing a little bit of work for Launch Agency, they're a big marketing agency
    (370, 371),   # from Hamilton.
    (372, 385),   # And then in terms of direct clients, I'm doing some work for Legend Story.
    (393, 396),   # a landing page design.
    (402, 423),   # And then a little bit of work with Sell Myself. We just wrapped up a massive phase two new website for them.
    (433, 438),   # Constantly working with Spirit of Douglas,
    (440, 444),   # a cool plane, so not-for-profit,
    (516, 518),   # so next episode,
    (520, 533),   # it would be awesome to show you guys what I do day to day.
    (576, 586),   # a bit of a portfolio, a bit of a showcase, maybe some fancy swirling animations.
]

# Build keep index set
keep_idx = set()
for a, b in KEEP:
    for i in range(a, b + 1):
        keep_idx.add(i)

# Build contiguous segments from kept indices
segs = []
cur = None
for i in range(len(words)):
    if i in keep_idx:
        if cur is None:
            cur = i
    else:
        if cur is not None:
            segs.append((cur, i - 1)); cur = None
if cur is not None:
    segs.append((cur, len(words) - 1))

time_segs = []
for a, b in segs:
    t0 = max(0, words[a]["start"] - PAD_BEFORE)
    t1 = words[b]["end"] + PAD_AFTER
    text = " ".join(words[j]["text"].strip() for j in range(a, b + 1))
    for wr, ri in TEXT_CORRECTIONS.items():
        text = text.replace(wr, ri)
    time_segs.append({"start": t0, "end": t1, "text": text})

# Merge segments with small gaps
merged = [time_segs[0]]
for s in time_segs[1:]:
    if s["start"] - merged[-1]["end"] < MIN_GAP_TO_MERGE:
        merged[-1]["end"] = s["end"]; merged[-1]["text"] += " " + s["text"]
    else:
        merged.append(s)

total = sum(s["end"] - s["start"] for s in merged)
print(f"{len(merged)} segments, total kept ~{total:.1f}s\n")
running = 0.0
for s in merged:
    d = s["end"] - s["start"]
    print(f"[{running:5.1f}->{running+d:5.1f}] ({d:4.1f}s) {s['text']}")
    running += d
print(f"\nTOTAL: {total:.1f}s")
