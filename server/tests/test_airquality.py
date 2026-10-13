import json
from pathlib import Path

import pytest

from dashboard.fetchers import airquality

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def aq():
    return airquality.parse_reading(
        json.loads((FIXTURES / "air_latest.json").read_text()))


def test_parse_reading(aq):
    assert aq.co2_ppm == 743.0
    assert aq.pm2p5 == 3.8
    assert aq.voc == 12.0
    assert aq.nox == 1.0
    assert aq.temp_f == pytest.approx(70.5, abs=0.1)   # 21.4C -> F
    assert aq.humidity_pct == 44.2
    assert aq.timestamp is not None


def test_ratings(aq):
    assert airquality.co2_rating(aq) == "good"
    assert airquality.pm25_rating(aq) == "good"

    aq.co2_ppm = 1400
    aq.pm2p5 = 50
    assert airquality.co2_rating(aq) == "poor"
    assert airquality.pm25_rating(aq) == "poor"
