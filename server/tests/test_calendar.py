from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from dashboard.fetchers import calendar_feed

FIXTURES = Path(__file__).parent / "fixtures"
TZ = ZoneInfo("America/New_York")


@pytest.fixture
def feeds():
    return {
        "family": (FIXTURES / "family.ics").read_text(),
        "work": (FIXTURES / "work.ics").read_text(),
    }


def test_events_for_day_merges_and_sorts(feeds):
    events = calendar_feed.events_for_day(feeds, date(2026, 10, 14), TZ)
    titles = [e.title for e in events]

    # All-day event first, then timed events in order (ET).
    assert titles == [
        "School picture day",
        "Dentist appointment",    # 10:30 ET
        "Pickup reminder call",   # 13:00 ET
        "Soccer practice",        # 16:30 ET (recurring weekly)
    ]
    assert events[0].all_day is True
    assert events[0].calendar == "work"
    assert "Tomorrow's event" not in titles


def test_recurring_event_expands(feeds):
    # Soccer practice starts Oct 7 and recurs weekly: also hits Oct 21.
    events = calendar_feed.events_for_day(feeds, date(2026, 10, 21), TZ)
    assert "Soccer practice" in [e.title for e in events]


def test_empty_range(feeds):
    events = calendar_feed.events_for_day(feeds, date(2026, 11, 20), TZ)
    assert events == []
