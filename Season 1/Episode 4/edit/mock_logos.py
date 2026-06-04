"""Quick visual mock: composite logo 'sticker cards' onto real frames so we can
approve size/position/treatment before the full render."""
import os
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
EP = os.path.dirname(HERE)
LOGOS = os.path.join(EP, "logos")
VER = os.path.join(HERE, "verify")

CARD_PAD = 26          # padding between logo and card edge
CARD_RADIUS = 28
LOGO_H = 84            # target logo height inside card
CARD_BG = (255, 255, 255, 235)


def make_card(slug, logo_h=LOGO_H):
    logo = Image.open(os.path.join(LOGOS, f"{slug}.png")).convert("RGBA")
    w = int(logo.width * logo_h / logo.height)
    logo = logo.resize((w, logo_h), Image.LANCZOS)
    cw, ch = w + 2 * CARD_PAD, logo_h + 2 * CARD_PAD
    # shadow
    pad = 18
    canvas = Image.new("RGBA", (cw + 2 * pad, ch + 2 * pad), (0, 0, 0, 0))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([pad, pad + 4, pad + cw, pad + ch + 4], CARD_RADIUS, fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    canvas = Image.alpha_composite(canvas, shadow)
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 0, cw - 1, ch - 1], CARD_RADIUS, fill=CARD_BG)
    card.alpha_composite(logo, (CARD_PAD, CARD_PAD))
    canvas.alpha_composite(card, (pad, pad))
    return canvas


def place(frame, card, cx, cy):
    """Paste card centered at (cx, cy)."""
    frame.alpha_composite(card, (int(cx - card.width / 2), int(cy - card.height / 2)))


# Mock 1: single client logo (HNDRX) centered above head
f = Image.open(os.path.join(VER, "frame_44s.png")).convert("RGBA")
place(f, make_card("hndrx"), 540, 150)
f.convert("RGB").save(os.path.join(VER, "mock_single_hndrx.png"))

# Mock 2: four dev tools in a 2x2 grid (Webflow / WordPress / Wix / Squarespace)
f = Image.open(os.path.join(VER, "frame_13s.png")).convert("RGBA")
place(f, make_card("webflow", 70), 305, 125)
place(f, make_card("wordpress", 78), 770, 120)
place(f, make_card("wix", 66), 305, 300)
place(f, make_card("squarespace", 56), 770, 300)
f.convert("RGB").save(os.path.join(VER, "mock_tools_row.png"))

# Mock 3: single colourful logo (Legend Story) - bigger
f = Image.open(os.path.join(VER, "frame_69s.png")).convert("RGBA")
place(f, make_card("legend-story", 150), 540, 190)
f.convert("RGB").save(os.path.join(VER, "mock_single_legend.png"))

print("wrote mock_single_hndrx.png, mock_tools_row.png, mock_single_legend.png")
