"""Compute how long the device may sleep before the next refresh.

The next meaningful change is whichever comes first: the next routine
transition, the next calendar event boundary, or midnight (date/header
rollover). Clamped to [min_s, max_s].
"""

from datetime import datetime, timedelta

from .data import DashboardData

MIN_REFRESH_S = 300      # never ask the device to wake more often than 5 min
MAX_REFRESH_S = 3600     # never sleep more than an hour, even if nothing changes


def next_refresh_s(data: DashboardData, now: datetime,
                   min_s: int = MIN_REFRESH_S,
                   max_s: int = MAX_REFRESH_S) -> int:
    candidates = [max_s]

    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
    candidates.append(int((midnight - now).total_seconds()))

    if data.routine and data.routine.minutes_until_next is not None:
        candidates.append(max(0, int(data.routine.minutes_until_next * 60)))

    for ev in data.events:
        if isinstance(ev.start, datetime) and ev.start > now:
            candidates.append(int((ev.start - now).total_seconds()))

    return max(min_s, min(candidates))
