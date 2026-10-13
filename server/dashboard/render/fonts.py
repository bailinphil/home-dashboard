"""Font loading with cross-platform fallbacks (macOS dev, Linux deploy)."""

from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

_REGULAR_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_BOLD_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
_KID_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Chalkboard.ttc",
    "/System/Library/Fonts/Supplemental/Comic Sans MS.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _first_existing(candidates) -> str:
    for path in candidates:
        if Path(path).exists():
            return path
    raise FileNotFoundError(f"no font found among {candidates}")


@lru_cache(maxsize=32)
def _load(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def regular(size: int) -> ImageFont.FreeTypeFont:
    return _load(_first_existing(_REGULAR_CANDIDATES), size)


def bold(size: int) -> ImageFont.FreeTypeFont:
    return _load(_first_existing(_BOLD_CANDIDATES), size)


def kid(size: int) -> ImageFont.FreeTypeFont:
    return _load(_first_existing(_KID_CANDIDATES), size)
