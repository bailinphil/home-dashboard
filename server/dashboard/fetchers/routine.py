"""Kids' daily routine module.

Loads a YAML timetable (per-weekday schedule of named activities) and
answers: what should the kids be doing now, and how long until the next
step? Pure functions take `now` explicitly so tests don't need clocks.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

import yaml

_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass
class RoutineState:
    current_activity: str
    next_activity: str
    next_time: time
    minutes_until_next: float


def load_routine(path: str | Path) -> dict[str, list[dict]]:
    """Load routine YAML into {day_key: [{time, activity}]} resolved per day."""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    def entries(group):
        return [
            {"time": _parse_time(e["time"]), "activity": e["activity"]}
            for e in raw.get(group, [])
        ]

    schedule = {}
    for i, day in enumerate(_DAYS):
        group = day
        if group not in raw:
            group = "weekdays" if i < 5 else "weekends"
        schedule[day] = entries(group)
    return schedule


def routine_state(schedule: dict[str, list[dict]], now: datetime) -> RoutineState | None:
    """Return the current activity, next activity, and minutes until it."""
    day_key = _DAYS[now.weekday()]
    today = schedule.get(day_key, [])
    if not today:
        return None

    todays = [(datetime.combine(now.date(), e["time"]), e["activity"]) for e in today]
    # Before the first entry of the day, "current" is yesterday's last entry.
    yesterday = schedule.get(_DAYS[(now.weekday() - 1) % 7], [])
    current_activity = yesterday[-1]["activity"] if yesterday else "free time"
    next_time, next_activity = None, None

    for start, activity in todays:
        if start <= now:
            current_activity = activity
        else:
            next_time, next_activity = start, activity
            break

    if next_time is None:
        # After the last entry of the day: next is tomorrow's first entry.
        tomorrow_key = _DAYS[(now.weekday() + 1) % 7]
        first = schedule.get(tomorrow_key, today[:1])
        if first:
            next_time = datetime.combine(now.date() + timedelta(days=1), first[0]["time"])
            next_activity = first[0]["activity"]

    if next_time is None:
        return None

    return RoutineState(
        current_activity=current_activity,
        next_activity=next_activity,
        next_time=next_time.time(),
        minutes_until_next=(next_time - now).total_seconds() / 60,
    )


def _parse_time(value) -> time:
    if isinstance(value, time):
        return value
    h, m = str(value).split(":")
    return time(int(h), int(m))
