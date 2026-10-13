"""Render the dashboard to server/output/dashboard.png.

  python preview.py            # live: fetch real data via config.local.yaml
  python preview.py --offline  # synthetic data, no network
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))

from dashboard import load_config
from dashboard.data import DashboardData, collect
from dashboard.fetchers import airquality, calendar_feed, photo, routine, weather
from dashboard.render import dashboard

OUT_DIR = Path(__file__).parent / "output"
TZ = ZoneInfo("America/New_York")


def _sample_photo(w=900, h=600) -> Image.Image:
    """A stand-in photo: sky gradient over a hill with a sun."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for yy in range(h):
        frac = yy / h
        r = int(135 + 60 * frac)
        g = int(200 - 140 * frac)
        b = int(235 - 195 * frac)
        d.line([(0, yy), (w, yy)], fill=(r, g, b))
    d.ellipse([w - 220, 40, w - 80, 180], fill=(255, 240, 80))
    d.ellipse([-200, int(h * 0.55), w // 2 + 100, h + 300], fill=(60, 150, 60))
    d.ellipse([w // 2 - 100, int(h * 0.65), w + 200, h + 300], fill=(80, 170, 80))
    return img


def offline_data() -> DashboardData:
    now = datetime.now(TZ)
    d = DashboardData(now=now)
    d.weather = weather.Weather(
        temp_now_f=64.5, high_f=71.0, low_f=48.0, pop_pct=15.0,
        condition="Clouds", icon="02d",
        sunrise=now.replace(hour=6, minute=58), sunset=now.replace(hour=18, minute=20),
        fetched_at=now)
    d.clothing = weather.clothing_suggestion(d.weather)
    d.events = [
        calendar_feed.Event("School picture day", date.today(), None, True, "family"),
        calendar_feed.Event("Dentist – Molly",
                            now.replace(hour=10, minute=30, second=0, microsecond=0),
                            now.replace(hour=11, minute=30, second=0, microsecond=0),
                            False, "work"),
        calendar_feed.Event("Soccer practice",
                            now.replace(hour=16, minute=30, second=0, microsecond=0),
                            now.replace(hour=17, minute=30, second=0, microsecond=0),
                            False, "family"),
    ]
    d.photo = photo.PhotoOfDay(
        image_url="https://bailinphil.com/images/backlog/bordered/39/pawing.png",
        title="pawing", published=now, caption_html="")
    d.photo_image = _sample_photo()
    d.air = airquality.AirQuality(
        co2_ppm=743, pm1p0=1.2, pm2p5=3.8, pm4p0=4.1, pm10=4.2,
        voc=12, nox=1, temp_f=70.5, humidity_pct=44.2, timestamp=now, fetched_at=now)
    d.routine = routine.RoutineState(
        current_activity="play time", next_activity="dinner",
        next_time=now.replace(hour=18, minute=0).time(), minutes_until_next=42)
    d.battery_v = 3.87
    return d


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--out", default=str(OUT_DIR / "dashboard.png"))
    args = parser.parse_args()

    data = offline_data() if args.offline else collect(load_config())
    for err in data.errors:
        print(f"warning: {err}", file=sys.stderr)

    img = dashboard.render(data)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print(f"wrote {args.out} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
