"""Kitchen air quality fetcher.

The kitchen-lights controller reports readings to
http://ino.bailinphil.com/air_in?<params>, where they land in a database.
The read-back endpoint is still TBD; this fetcher expects a JSON document
using the same parameter names as the air_in query string so it works
with whatever thin read endpoint we add server-side.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import requests


@dataclass
class AirQuality:
    co2_ppm: float
    pm1p0: float
    pm2p5: float
    pm4p0: float
    pm10: float
    voc: float
    nox: float
    temp_f: float | None
    humidity_pct: float | None
    timestamp: datetime | None
    fetched_at: datetime


def parse_reading(data: dict) -> AirQuality:
    ts = data.get("timestamp")
    temp_c = data.get("t41")
    return AirQuality(
        co2_ppm=float(data["co2"]),
        pm1p0=float(data["p1p0"]),
        pm2p5=float(data["p2p5"]),
        pm4p0=float(data["p4p0"]),
        pm10=float(data["p10"]),
        voc=float(data["voc"]),
        nox=float(data["nox"]),
        temp_f=(temp_c * 9 / 5 + 32) if temp_c is not None else None,
        humidity_pct=float(data["h41"]) if data.get("h41") is not None else None,
        timestamp=datetime.fromisoformat(ts) if ts else None,
        fetched_at=datetime.now(tz=timezone.utc),
    )


def co2_rating(aq: AirQuality) -> str:
    if aq.co2_ppm < 800:
        return "good"
    if aq.co2_ppm < 1200:
        return "ok"
    return "poor"


def pm25_rating(aq: AirQuality) -> str:
    if aq.pm2p5 <= 12:
        return "good"
    if aq.pm2p5 <= 35:
        return "moderate"
    return "poor"


def fetch_air_quality(read_url: str) -> AirQuality:
    resp = requests.get(read_url, timeout=15)
    resp.raise_for_status()
    return parse_reading(resp.json())
