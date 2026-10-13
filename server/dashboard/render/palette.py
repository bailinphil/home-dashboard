"""The Inkplate 13SPECTRA 6-color palette.

Everything rendered to the device must be one of these colors. We render
the UI in RGB, quantize to the palette (no dithering for UI elements —
nearest-color snap keeps text edges clean), and Floyd-Steinberg dither
only the photo region.
"""

from PIL import Image

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (228, 60, 48)
BLUE = (45, 90, 170)
GREEN = (55, 140, 70)
YELLOW = (248, 200, 30)

COLORS = [BLACK, WHITE, RED, BLUE, GREEN, YELLOW]


def palette_image() -> Image.Image:
    """A 1x6 P-mode image whose palette is the six Spectra colors."""
    img = Image.new("P", (6, 1))
    flat = [c for rgb in COLORS for c in rgb] + [0] * (768 - 18)
    img.putpalette(flat)
    for x in range(6):
        img.putpixel((x, 0), x)
    return img


def quantize(img: Image.Image, dither: Image.Dither = Image.Dither.NONE) -> Image.Image:
    """Snap an RGB image to the Spectra palette."""
    return img.quantize(palette=palette_image(), dither=dither)


def dither_photo(img: Image.Image) -> Image.Image:
    """Floyd-Steinberg dither a photo to the palette; returns RGB."""
    return quantize(img.convert("RGB"), dither=Image.Dither.FLOYDSTEINBERG).convert("RGB")


def is_palette_pure(img: Image.Image) -> bool:
    """True if every pixel is exactly one of the six palette colors."""
    colors = img.convert("RGB").getcolors(maxcolors=1 << 24)
    if colors is None:  # more than 2^24 distinct colors: certainly impure
        return False
    return {c for _, c in colors} <= set(COLORS)
