import io
from pathlib import Path

import pytest
import yaml
from PIL import Image

from dashboard import api
from dashboard.data import DashboardData
from dashboard.fetchers import routine as routine_fetch
from dashboard.render.palette import is_palette_pure
from preview import offline_data

FIXTURES = Path(__file__).parent / "fixtures"
CFG = {"location": {"timezone": "America/New_York"}}


@pytest.fixture
def fixed_data():
    """One instance so every render is byte-identical."""
    return offline_data()


@pytest.fixture
def client(tmp_path, fixed_data):
    app = api.create_app(
        data_provider=lambda ctx: fixed_data,
        state_dir=tmp_path, config=CFG)
    return app.test_client()


def test_active_manifest_shape(client):
    r = client.get("/v1/active?device=test&battery=3.9")
    assert r.status_code == 200
    m = r.get_json()
    assert m["screen"] == "home"
    assert m["full_refresh"] is True          # no baseline yet
    assert m["regions"] is None
    assert 300 <= m["next_refresh_s"] <= 3600
    assert m["image_url"].endswith(f"{m['image_etag']}.png")


def test_image_endpoint_serves_palette_pure_png(client):
    m = client.get("/v1/active?device=test").get_json()
    r = client.get(m["image_url"])
    assert r.status_code == 200
    img = Image.open(io.BytesIO(r.data))
    assert img.size == (1200, 1600)
    assert is_palette_pure(img)


def test_same_image_gives_empty_regions(client):
    first = client.get("/v1/active?device=test").get_json()
    second = client.get(f"/v1/active?device=test&since={first['image_etag']}").get_json()
    assert second["regions"] == []
    assert second["full_refresh"] is False


def test_changed_data_gives_regions(tmp_path):
    state = {"routine": "play time"}

    def provider(ctx):
        d = offline_data()
        d.routine = routine_fetch.RoutineState(
            current_activity=state["routine"], next_activity="dinner",
            next_time=None, minutes_until_next=42)
        return d

    app = api.create_app(data_provider=provider, state_dir=tmp_path, config=CFG)
    c = app.test_client()
    c.get("/v1/active?device=test")
    state["routine"] = "dinner"                      # change the panel
    m = c.get("/v1/active?device=test").get_json()
    assert m["full_refresh"] is False
    assert m["regions"] and all(len(r) == 4 for r in m["regions"])


def test_push_screen_and_release(client):
    r = client.post("/v1/screens/recipe",
                    json={"title": "chili", "body": "beans tomatoes cumin"})
    assert r.get_json()["active"] == "recipe"
    m = client.get("/v1/active?device=test").get_json()
    assert m["screen"] == "recipe"
    client.post("/v1/active_screen", json={"screen": "home"})
    assert client.get("/v1/active?device=test").get_json()["screen"] == "home"


def test_telemetry_and_status(client):
    client.get("/v1/active?device=test&battery=3.9")
    client.post("/v1/devices/test/telemetry",
                json={"rssi": -55, "fetch_ms": 1200, "errors": 0})
    s = client.get("/v1/status").get_json()
    assert s["devices"]["test"]["requests"] == 1
    assert s["devices"]["test"]["last_battery_v"] == 3.9
    assert s["devices"]["test"]["telemetry"]["rssi"] == -55
