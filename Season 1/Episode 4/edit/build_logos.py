"""Normalize raw client/brand logos into a clean overlay-ready set.

For each source logo: EXIF-correct, convert to RGBA, strip a uniform opaque
background (e.g. Squarespace's white box) to transparency, autocrop transparent
padding, and save as logos/<slug>.png.

Run from anywhere: paths are resolved relative to the episode root.
"""
import os
import numpy as np
from PIL import Image, ImageOps

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EP_DIR = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(EP_DIR, "logos")

# source filename -> clean slug
LOGOS = {
    "webflow-logo.png": "webflow",
    "Wordpress-Logo.svg.png": "wordpress",
    "wix-logo.webp": "wix",
    "squarespace-logo.png": "squarespace",
    "Figma-logo.svg.png": "figma",
    "5f91cec86c0b970575f31bd1_unicornfactory-logo-full-color-rgb.webp": "unicorn-factory",
    "Fiverr-Logo.png": "fiverr",
    "HNDRX Logo.png": "hndrx",
    "Onsite logo.png": "onsite",
    "Launch Logo 1.png": "launch",
    "Flesh_and_Blood_TCG_Logo.png": "legend-story",
    "Sell_my_Cell_Logo_Black_Yellow_RGB 1.png": "sellmycell",
    "spirit-douglas-logo.png": "spirit-douglas",
}


def strip_uniform_bg(im, tol=18):
    """If the image is (near) fully opaque with a uniform corner colour,
    make pixels within `tol` of that colour transparent."""
    a = np.array(im).astype(np.int16)
    alpha = a[:, :, 3]
    if (alpha < 250).mean() > 0.05:
        return im  # already has meaningful transparency, leave it

    corners = np.array([a[0, 0, :3], a[0, -1, :3], a[-1, 0, :3], a[-1, -1, :3]])
    if corners.std(axis=0).max() > 8:
        return im  # corners disagree -> no uniform bg

    bg = corners.mean(axis=0)
    dist = np.sqrt(((a[:, :, :3] - bg) ** 2).sum(axis=2))
    a[:, :, 3] = np.where(dist <= tol, 0, a[:, :, 3])
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for fname, slug in LOGOS.items():
        path = os.path.join(EP_DIR, fname)
        if not os.path.exists(path):
            print(f"  MISSING: {fname}")
            continue
        im = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        im = strip_uniform_bg(im)
        bbox = im.getchannel("A").getbbox()
        if bbox:
            im = im.crop(bbox)
        out = os.path.join(OUT_DIR, f"{slug}.png")
        im.save(out)
        print(f"  {slug:16s} {im.size[0]:4d}x{im.size[1]:<4d}  <- {fname}")


if __name__ == "__main__":
    main()
