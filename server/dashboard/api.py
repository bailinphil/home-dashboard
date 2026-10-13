"""REST API for the dashboard service.

  GET  /v1/active?device=<id>&battery=<v>&since=<etag>
  GET  /v1/images/<etag>.png
  POST /v1/screens/<name>?hold_s=<n>      {title, body, image_b64?}
  POST /v1/active_screen                 {screen: "home"|<name>}
  POST /v1/devices/<id>/telemetry        {battery_v, rssi, ...}
  GET  /v1/status
"""

import hashlib
import io
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, request, send_file
from PIL import Image

from . import diff, refresh, screens, state
from .config import load_config
from .data import DashboardData, collect

_SERVER_DIR = Path(__file__).resolve().parent.parent
DEFAULT_STATE_DIR = _SERVER_DIR / "state"


def create_app(data_provider=None, state_dir=None, config=None):
    """data_provider(ctx) -> DashboardData; ctx = {device, battery_v}.

    Defaults to collect(load_config()). Tests inject a provider that
    returns synthetic data.
    """
    app = Flask(__name__)
    cfg = config or load_config()
    tz = ZoneInfo(cfg["location"]["timezone"])
    store = state.State(state_dir or DEFAULT_STATE_DIR)
    mgr = screens.ScreenManager()
    started = time.time()

    def default_provider(ctx):
        data = collect(cfg)
        data.battery_v = ctx["battery_v"]
        return data

    provide = data_provider or default_provider

    @app.get("/v1/active")
    def active():
        device = request.args.get("device", "default")
        battery = request.args.get("battery", type=float)
        since = request.args.get("since")
        store.record_request(device, battery)

        now = datetime.now(tz)
        data = DashboardData(now=now)
        try:
            if mgr.active_name() == "home":
                data = provide({"device": device, "battery_v": battery})
            img = mgr.render_active(data)
        except Exception as e:
            store.record_failure(device, str(e))
            raise

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        png = buf.getvalue()
        etag = hashlib.sha256(png).hexdigest()[:16]
        store.save_image(etag, png)

        baseline_tag = since or store.device(device)["last_etag"]
        if baseline_tag == etag:
            regions = []                       # nothing changed
        else:
            base_png = store.read_image(baseline_tag) if baseline_tag else None
            baseline = Image.open(io.BytesIO(base_png)) if base_png else None
            regions = diff.diff_regions(baseline, img)
        store.set_last_etag(device, etag)

        try:
            next_s = refresh.next_refresh_s(data, now)
        except Exception:
            next_s = refresh.MAX_REFRESH_S

        return jsonify({
            "screen": mgr.active_name(),
            "image_url": f"/v1/images/{etag}.png",
            "image_etag": etag,
            "regions": regions,
            "full_refresh": regions is None,
            "next_refresh_s": next_s,
            "server_time": now.isoformat(),
        })

    @app.get("/v1/images/<etag>.png")
    def image(etag):
        path = store.image_path(etag)
        if not path.exists():
            return "unknown image", 404
        return send_file(path, mimetype="image/png")

    @app.post("/v1/screens/<name>")
    def push_screen(name):
        try:
            hold = request.args.get("hold_s", type=int)
            mgr.push(name, screens.spec_from_request(
                request.get_json(force=True) or {}, hold))
        except ValueError as e:
            return str(e), 400
        return jsonify({"ok": True, "active": mgr.active_name()})

    @app.post("/v1/active_screen")
    def set_active():
        name = (request.get_json(force=True) or {}).get("screen", "home")
        try:
            mgr.set_active(name)
        except KeyError:
            return f"unknown screen {name}", 404
        return jsonify({"ok": True, "active": mgr.active_name()})

    @app.post("/v1/devices/<device>/telemetry")
    def telemetry(device):
        store.record_telemetry(device, request.get_json(force=True) or {})
        return jsonify({"ok": True})

    @app.get("/v1/status")
    def status():
        return jsonify({
            "uptime_s": int(time.time() - started),
            "devices": store.devices,
            "active_screen": mgr.active_name(),
            "pushed_screens": list(mgr.pushed),
        })

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=8080, debug=True)
