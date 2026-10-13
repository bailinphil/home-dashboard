"""Screen registry.

"home" is the full dashboard render. Other screens (recipe, trip, ...)
can be pushed by other devices via POST /v1/screens/<name>; they render
as a simple title + body (or provided image) and become the active screen
until released or their hold expires.
"""

import base64
import time
from dataclasses import dataclass, field
from io import BytesIO

from PIL import Image, ImageDraw

from .data import DashboardData
from .render import dashboard, fonts, palette as pal

W, H = dashboard.W, dashboard.H


@dataclass
class PushedScreen:
    title: str
    body: str = ""
    image: Image.Image | None = None
    expires_at: float | None = None


class ScreenManager:
    def __init__(self):
        self.active = "home"
        self.pushed: dict[str, PushedScreen] = {}

    def push(self, name: str, spec: PushedScreen):
        if name == "home":
            raise ValueError("'home' is reserved")
        self.pushed[name] = spec
        self.active = name

    def set_active(self, name: str):
        if name != "home" and name not in self.pushed:
            raise KeyError(name)
        self.active = name

    def _gc(self):
        now = time.time()
        for name in [n for n, s in self.pushed.items()
                     if s.expires_at and s.expires_at < now]:
            del self.pushed[name]
            if self.active == name:
                self.active = "home"

    def active_name(self) -> str:
        self._gc()
        return self.active

    def render_active(self, data: DashboardData) -> Image.Image:
        self._gc()
        if self.active == "home":
            return dashboard.render(data)
        return render_pushed(self.pushed[self.active])


def render_pushed(spec: PushedScreen) -> Image.Image:
    img = Image.new("RGB", (W, H), pal.WHITE)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 110], fill=pal.BLUE)
    draw.text((40, 24), spec.title.upper(), font=fonts.bold(56), fill=pal.BLACK)
    if spec.image is not None:
        pic = pal.dither_photo(spec.image)
        scale = min((W - 80) / pic.width, (H - 240) / pic.height)
        pic = pic.resize((int(pic.width * scale), int(pic.height * scale)),
                         Image.Resampling.LANCZOS)
        img.paste(pic, ((W - pic.width) // 2, 140 + (H - 240 - pic.height) // 2))
    elif spec.body:
        _wrapped(draw, spec.body, 60, 170, W - 120, fonts.regular(44))
    return pal.quantize(img).convert("RGB")


def _wrapped(draw, text, x, y, max_w, font, line_h=60):
    words, line = text.split(), ""
    for word in words:
        cand = f"{line} {word}".strip()
        if draw.textlength(cand, font=font) <= max_w:
            line = cand
        else:
            draw.text((x, y), line, font=font, fill=pal.BLACK)
            y += line_h
            line = word
    if line:
        draw.text((x, y), line, font=font, fill=pal.BLACK)


def spec_from_request(payload: dict, hold_s: int | None) -> PushedScreen:
    image = None
    if payload.get("image_b64"):
        image = Image.open(BytesIO(base64.b64decode(payload["image_b64"])))
    return PushedScreen(
        title=str(payload.get("title", "screen")),
        body=str(payload.get("body", "")),
        image=image,
        expires_at=(time.time() + hold_s) if hold_s else None,
    )
