"""Compose the 1200x1600 portrait dashboard image.

Layout (top to bottom):
  - header:    date + current time
  - photo:     backlog picture of the day (dithered) with title
  - schedule:  today's merged calendar events
  - split row: kids' routine (left) | weather + clothing (right)
  - footer:    air quality | battery + last-updated
"""

from datetime import date, datetime, time

from PIL import Image, ImageDraw

from ..data import DashboardData
from ..fetchers import airquality, weather as weather_mod
from . import fonts, palette as pal

W, H = 1200, 1600
MARGIN = 32
GAP = 24

_HEADER_H = 110
_PHOTO_H = 600
_SCHEDULE_H = 330
_SPLIT_H = 330
_FOOTER_H = 110


def render(data: DashboardData) -> Image.Image:
    img = Image.new("RGB", (W, H), pal.WHITE)
    draw = ImageDraw.Draw(img)

    _header(draw, data)
    _photo(img, draw, data, _HEADER_H + GAP, _PHOTO_H)
    sched_y = _HEADER_H + GAP + _PHOTO_H + GAP
    _schedule(draw, data, sched_y, _SCHEDULE_H)
    split_y = sched_y + _SCHEDULE_H + GAP
    _routine_panel(draw, data, MARGIN, split_y, (W - 2 * MARGIN - GAP) // 2, _SPLIT_H)
    _weather_panel(draw, data, MARGIN + (W - 2 * MARGIN + GAP) // 2,
                   split_y, (W - 2 * MARGIN - GAP) // 2, _SPLIT_H)
    _footer(draw, data, split_y + _SPLIT_H + GAP, _FOOTER_H)

    return pal.quantize(img).convert("RGB")


# ---------------------------------------------------------------- helpers

def _panel(draw: ImageDraw.ImageDraw, x, y, w, h, title, accent):
    draw.rectangle([x, y, x + w, y + h], outline=pal.BLACK, width=3)
    bar_h = 56
    draw.rectangle([x, y, x + w, y + bar_h], fill=accent)
    draw.text((x + 16, y + 14), title.upper(), font=fonts.bold(28), fill=pal.BLACK)
    return y + bar_h + 12


def _fit(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = min(w / img.width, h / img.height)
    return img.resize((int(img.width * scale), int(img.height * scale)),
                      Image.Resampling.LANCZOS)


def _fmt_time(value, tz) -> str:
    if isinstance(value, datetime):
        return value.astimezone(tz).strftime("%-I:%M%p").lower()
    return ""


# ---------------------------------------------------------------- sections

def _header(draw, data):
    now = data.now
    draw.text((MARGIN, 20), now.strftime("%A, %B %-d"),
              font=fonts.bold(64), fill=pal.BLACK)
    time_str = now.strftime("%-I:%M")
    draw.text((W - MARGIN - draw.textlength(time_str, font=fonts.bold(64)), 20),
              time_str, font=fonts.bold(64), fill=pal.BLACK)


def _photo(img, draw, data, y, h):
    x, w = MARGIN, W - 2 * MARGIN
    draw.rectangle([x, y, x + w, y + h], outline=pal.BLACK, width=3)
    if data.photo_image is None:
        draw.text((x + 24, y + 24), "photo unavailable",
                  font=fonts.regular(32), fill=pal.RED)
        return
    caption_h = 64
    inner_h = h - caption_h - 8
    pic = pal.dither_photo(_fit(data.photo_image, w - 8, inner_h))
    px = x + (w - pic.width) // 2
    py = y + 4 + (inner_h - pic.height) // 2
    img.paste(pic, (px, py))
    title = data.photo.title if data.photo else ""
    draw.text((x + 16, y + h - caption_h + 12), title,
              font=fonts.regular(30), fill=pal.BLACK)


def _schedule(draw, data, y, h):
    x, w = MARGIN, W - 2 * MARGIN
    body_y = _panel(draw, x, y, w, h, "Today", pal.RED)
    if not data.events:
        draw.text((x + 24, body_y + 16), "nothing scheduled",
                  font=fonts.regular(32), fill=pal.BLACK)
        return
    row_h, shown = 44, 0
    for ev in data.events:
        if shown >= 6:
            remaining = len(data.events) - shown
            draw.text((x + 24, body_y), f"+ {remaining} more…",
                      font=fonts.regular(28), fill=pal.BLACK)
            break
        if ev.all_day:
            label = "all day"
            color = pal.BLUE
        else:
            label = _fmt_time(ev.start, data.now.tzinfo)
            color = pal.BLACK
        draw.text((x + 24, body_y), label, font=fonts.bold(28), fill=color)
        draw.text((x + 170, body_y), _truncate(draw, ev.title, w - 220, fonts.regular(30)),
                  font=fonts.regular(30), fill=pal.BLACK)
        body_y += row_h
        shown += 1


def _routine_panel(draw, data, x, y, w, h):
    body_y = _panel(draw, x, y, w, h, "Right now", pal.BLUE)
    r = data.routine
    if r is None:
        draw.text((x + 24, body_y + 16), "no routine set",
                  font=fonts.regular(30), fill=pal.BLACK)
        return
    draw.text((x + 24, body_y + 8),
              _truncate(draw, r.current_activity, w - 48, fonts.kid(52)),
              font=fonts.kid(52), fill=pal.BLACK)
    mins = int(r.minutes_until_next)
    nxt = f"in {mins} min: {r.next_activity}"
    draw.text((x + 24, body_y + 110),
              _truncate(draw, nxt, w - 48, fonts.kid(38)),
              font=fonts.kid(38), fill=pal.BLUE)


def _weather_panel(draw, data, x, y, w, h):
    body_y = _panel(draw, x, y, w, h, "Outside", pal.GREEN)
    wthr = data.weather
    if wthr is None:
        draw.text((x + 24, body_y + 16), "weather unavailable",
                  font=fonts.regular(30), fill=pal.RED)
        return
    draw.text((x + 24, body_y), f"{wthr.temp_now_f:.0f}°F",
              font=fonts.bold(64), fill=pal.BLACK)
    draw.text((x + 24, body_y + 80),
              f"high {wthr.high_f:.0f}° / low {wthr.low_f:.0f}°  ·  {wthr.condition}",
              font=fonts.regular(28), fill=pal.BLACK)
    if data.clothing:
        draw.text((x + 24, body_y + 140),
                  _truncate(draw, f"wear: {data.clothing}", w - 48, fonts.kid(40)),
                  font=fonts.kid(40), fill=pal.GREEN)


def _footer(draw, data, y, h):
    x, w = MARGIN, W - 2 * MARGIN
    left_w = w * 2 // 3
    right_x = x + left_w + GAP
    right_w = w - left_w - GAP

    body_y = _panel(draw, x, y, left_w, h, "Kitchen air", pal.YELLOW)
    if data.air is None:
        draw.text((x + 24, body_y), "no readings", font=fonts.regular(28), fill=pal.BLACK)
    else:
        co2_color = {"good": pal.GREEN, "ok": pal.YELLOW, "poor": pal.RED}[
            airquality.co2_rating(data.air)]
        pm_color = {"good": pal.GREEN, "moderate": pal.YELLOW, "poor": pal.RED}[
            airquality.pm25_rating(data.air)]
        draw.text((x + 24, body_y), f"CO2 {data.air.co2_ppm:.0f} ppm",
                  font=fonts.bold(30), fill=co2_color)
        draw.text((x + 24 + draw.textlength(f"CO2 {data.air.co2_ppm:.0f} ppm   ",
                  font=fonts.bold(30)), body_y),
                  f"PM2.5 {data.air.pm2p5:.1f}", font=fonts.bold(30), fill=pm_color)

    body_y = _panel(draw, right_x, y, right_w, h, "Device", pal.YELLOW)
    batt = f"{data.battery_v:.2f}V" if data.battery_v else "--"
    draw.text((right_x + 24, body_y), f"battery {batt}  ·  upd {data.now.strftime('%-I:%M')}",
              font=fonts.regular(26), fill=pal.BLACK)


def _truncate(draw, text: str, max_w: int, font) -> str:
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text + "…" if text else ""
