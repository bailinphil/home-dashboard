"""Google Calendar fetcher via private ICS/iCal feeds.

Each family calendar is fetched as an ICS feed (Google Calendar's
"Secret address in iCal format"), expanded (including recurring events),
merged, and filtered to the requested window.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import icalendar
import recurring_ical_events
import requests


@dataclass
class Event:
    title: str
    start: datetime | date
    end: datetime | date | None
    all_day: bool
    calendar: str


def _to_dt(value, tz: ZoneInfo) -> datetime | date:
    dt = value.dt
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(tz)
    return dt  # plain date = all-day


def events_in_range(
    ics_by_name: dict[str, str],
    start: datetime,
    end: datetime,
    tz: ZoneInfo,
) -> list[Event]:
    """Expand all calendars' events that intersect [start, end)."""
    events: list[Event] = []
    for name, ics_text in ics_by_name.items():
        cal = icalendar.Calendar.from_ical(ics_text)
        for component in recurring_ical_events.of(cal).between(start, end):
            ev = Event(
                title=str(component.get("SUMMARY", "(untitled)")),
                start=_to_dt(component["DTSTART"], tz),
                end=_to_dt(component["DTEND"], tz) if component.get("DTEND") else None,
                all_day=not isinstance(component["DTSTART"].dt, datetime),
                calendar=name,
            )
            events.append(ev)

    def sort_key(e: Event):
        start = e.start
        if isinstance(start, date) and not isinstance(start, datetime):
            start = datetime.combine(start, time.min, tzinfo=tz)
        return (start, not e.all_day, e.title)

    return sorted(events, key=sort_key)


def events_for_day(
    ics_by_name: dict[str, str],
    day: date,
    tz: ZoneInfo,
) -> list[Event]:
    start = datetime.combine(day, time.min, tzinfo=tz)
    return events_in_range(ics_by_name, start, start + timedelta(days=1), tz)


def fetch_calendars(urls_by_name: dict[str, str]) -> dict[str, str]:
    """Download each named calendar's ICS text."""
    feeds = {}
    for name, url in urls_by_name.items():
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        feeds[name] = resp.text
    return feeds
