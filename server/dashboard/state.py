"""Server-side state: per-device bookkeeping, image cache, telemetry log.

Persisted under a state dir so restarts don't lose the diff baseline or
metrics. Device state is small JSON; images live as files; telemetry is
an append-only JSONL log.
"""

import json
import time
from pathlib import Path


class State:
    def __init__(self, state_dir: str | Path):
        self.dir = Path(state_dir)
        self.images_dir = self.dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.devices_path = self.dir / "devices.json"
        self.telemetry_path = self.dir / "telemetry.jsonl"
        self.devices = self._load(self.devices_path)

    # ---- devices -----------------------------------------------------

    def device(self, device_id: str) -> dict:
        return self.devices.setdefault(device_id, {
            "requests": 0, "failures": 0, "last_etag": None,
            "last_seen": None, "last_battery_v": None, "last_error": None,
        })

    def record_request(self, device_id: str, battery_v: float | None):
        d = self.device(device_id)
        d["requests"] += 1
        d["last_seen"] = time.time()
        d["last_battery_v"] = battery_v
        self._save()

    def record_failure(self, device_id: str, error: str):
        d = self.device(device_id)
        d["failures"] += 1
        d["last_error"] = error
        self._save()

    def set_last_etag(self, device_id: str, etag: str):
        self.device(device_id)["last_etag"] = etag
        self._save()

    def record_telemetry(self, device_id: str, payload: dict):
        d = self.device(device_id)
        d["telemetry"] = {**payload, "received_at": time.time()}
        self._save()
        with open(self.telemetry_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"device": device_id, **payload,
                                "received_at": time.time()}) + "\n")

    # ---- image cache ---------------------------------------------------

    def image_path(self, etag: str) -> Path:
        return self.images_dir / f"{etag}.png"

    def has_image(self, etag: str) -> bool:
        return self.image_path(etag).exists()

    def save_image(self, etag: str, png: bytes):
        self.image_path(etag).write_bytes(png)

    def read_image(self, etag: str) -> bytes | None:
        p = self.image_path(etag)
        return p.read_bytes() if p.exists() else None

    # ---- io --------------------------------------------------------------

    def _load(self, path: Path) -> dict:
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def _save(self):
        self.devices_path.write_text(json.dumps(self.devices, indent=2))
