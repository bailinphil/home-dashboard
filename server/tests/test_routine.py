from datetime import datetime
from pathlib import Path

import pytest

from dashboard.fetchers import routine

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def schedule():
    return routine.load_routine(FIXTURES / "routine.yaml")


def test_load_routine_groups(schedule):
    # mon-fri get "weekdays", sun gets "weekends", sat has its own override.
    assert schedule["mon"][0]["activity"] == "wake up"
    assert schedule["sun"][0]["activity"] == "wake up"
    assert schedule["sat"][0]["activity"] == "pancakes"


def test_mid_day(schedule):
    # Wednesday 07:30 -> current "wake up", next "breakfast" in 30 min.
    state = routine.routine_state(schedule, datetime(2026, 10, 14, 7, 30))
    assert state.current_activity == "wake up"
    assert state.next_activity == "breakfast"
    assert state.minutes_until_next == 30


def test_before_first_entry_uses_yesterday(schedule):
    # Saturday 08:00, before pancakes at 09:00 -> still on Friday's "bedtime".
    state = routine.routine_state(schedule, datetime(2026, 10, 17, 8, 0))
    assert state.current_activity == "bedtime"
    assert state.next_activity == "pancakes"
    assert state.minutes_until_next == 60


def test_after_last_entry_rolls_to_tomorrow(schedule):
    # Wednesday 21:30, past bedtime -> next is Thursday's "wake up" (570 min).
    state = routine.routine_state(schedule, datetime(2026, 10, 14, 21, 30))
    assert state.current_activity == "bedtime"
    assert state.next_activity == "wake up"
    assert state.minutes_until_next == 570
