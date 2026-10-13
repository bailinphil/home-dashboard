"""OpenWeatherMap One Call 3.0 fetcher.

Reuses the same API the kitchen-lights Weather-Updater script calls, but
keeps the fields the dashboard needs: today's high/low for clothing
decisions, current temp, precipitation probability, and a condition code
for icon selection.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import requests

ONECALL_URL = "https://api.openweathermap.org/data/3.0/onecall"


@dataclass
class Weather:
    temp_now_f: float
    high_f: float
    low_f: float
    pop_pct: float          # today's precipitation probability, 0-100
    condition: str          # e.g. "Rain", "Clear", "Clouds"
    icon: str               # OWM icon code, e.g. "10d"
    sunrise: datetime
    sunset: datetime
    fetched_at: datetime


def parse_onecall(data: dict) -> Weather:
    current = data["current"]
    today = data["daily"][0]
    return Weather(
        temp_now_f=float(current["temp"]),
        high_f=float(today["temp"]["max"]),
        low_f=float(today["temp"]["min"]),
        pop_pct=float(today.get("pop", 0)) * 100,
        condition=current["weather"][0]["main"],
        icon=current["weather"][0]["icon"],
        sunrise=datetime.fromtimestamp(current["sunrise"], tz=timezone.utc),
        sunset=datetime.fromtimestamp(current["sunset"], tz=timezone.utc),
        fetched_at=datetime.now(tz=timezone.utc),
    )


def clothing_suggestion(w: Weather) -> str:
    """Simple rule-based clothing category for the kids' panel."""
    if w.pop_pct >= 50:
        return "rain gear"
    if w.high_f >= 80:
        return "shorts and t-shirt"
    if w.high_f >= 65:
        return "light layers"
    if w.high_f >= 50:
        return "jacket"
    if w.low_f <= 32:
        return "warm coat, hat, gloves"
    return "warm coat"


def fetch_weather(api_key: str, lat: float, lon: float) -> Weather:
    resp = requests.get(
        ONECALL_URL,
        params={
            "lat": lat,
            "lon": lon,
            "units": "imperial",
            "appid": api_key,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return parse_onecall(resp.json())
