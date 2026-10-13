import json
from pathlib import Path

import pytest

from dashboard.fetchers import weather

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def onecall():
    return json.loads((FIXTURES / "onecall.json").read_text())


def test_parse_onecall(onecall):
    w = weather.parse_onecall(onecall)
    assert w.temp_now_f == 58.2
    assert w.high_f == 66.0
    assert w.low_f == 48.0
    assert w.pop_pct == 15.0
    assert w.condition == "Clouds"
    assert w.icon == "02d"
    assert w.sunrise.timestamp() == 1760517000
    assert w.sunset.timestamp() == 1760558000


def test_parse_onecall_no_pop(onecall):
    del onecall["daily"][0]["pop"]
    assert weather.parse_onecall(onecall).pop_pct == 0.0


@pytest.mark.parametrize(
    "high,low,pop,expected",
    [
        (85, 70, 10, "shorts and t-shirt"),
        (70, 55, 10, "light layers"),
        (55, 40, 10, "jacket"),
        (45, 28, 10, "warm coat, hat, gloves"),
        (45, 40, 10, "warm coat"),
        (70, 55, 60, "rain gear"),
    ],
)
def test_clothing_suggestion(onecall, high, low, pop, expected):
    w = weather.parse_onecall(onecall)
    w.high_f, w.low_f, w.pop_pct = high, low, pop
    assert weather.clothing_suggestion(w) == expected
