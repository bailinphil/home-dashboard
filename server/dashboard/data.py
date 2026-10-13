"""Assemble everything the renderer needs, degrading gracefully.

Each source is fetched independently; failures are collected into
`errors` so one dead API can't blank the whole dashboard.
"""

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

from .fetchers import airquality, calendar_feed
from .fetchers import photo as photo_fetch
from .fetchers import routine as routine_fetch
from .fetchers import weather as weather_fetch


@dataclass
class DashboardData:
    now: datetime
    weather: weather_fetch.Weather | None = None
    clothing: str | None = None
    events: list[calendar_feed.Event] = field(default_factory=list)
    photo: photo_fetch.PhotoOfDay | None = None
    photo_image: Image.Image | None = None
    air: airquality.AirQuality | None = None
    routine: routine_fetch.RoutineState | None = None
    battery_v: float | None = None   # reported by the device at request time
    errors: list[str] = field(default_factory=list)


def collect(config: dict) -> DashboardData:
    tz = ZoneInfo(config["location"]["timezone"])
    data = DashboardData(now=datetime.now(tz))
    server_dir = Path(__file__).resolve().parent.parent

    try:
        data.weather = weather_fetch.fetch_weather(
            config["openweathermap"]["api_key"],
            config["location"]["lat"], config["location"]["lon"])
        data.clothing = weather_fetch.clothing_suggestion(data.weather)
    except Exception as e:
        data.errors.append(f"weather: {e}")

    try:
        urls = {k: v for k, v in (config.get("calendars") or {}).items() if v}
        if urls:
            feeds = calendar_feed.fetch_calendars(urls)
            data.events = calendar_feed.events_for_day(feeds, data.now.date(), tz)
    except Exception as e:
        data.errors.append(f"calendar: {e}")

    try:
        data.photo, img_bytes = photo_fetch.fetch_photo_of_day(config["backlog"]["feed_url"])
        data.photo_image = Image.open(BytesIO(img_bytes))
    except Exception as e:
        data.errors.append(f"photo: {e}")

    try:
        read_url = (config.get("air_quality") or {}).get("read_url")
        if read_url:
            data.air = airquality.fetch_air_quality(read_url)
    except Exception as e:
        data.errors.append(f"air quality: {e}")

    try:
        routine_path = server_dir / (config.get("routine") or {}).get("path", "routine.yaml")
        if routine_path.exists():
            data.routine = routine_fetch.routine_state(
                routine_fetch.load_routine(routine_path), data.now.replace(tzinfo=None))
    except Exception as e:
        data.errors.append(f"routine: {e}")

    return data
