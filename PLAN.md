# Implementation Plan — Home Dashboard (Inkplate 13SPECTRA)

## Architecture

**Server-rendered images over a REST API.** A Python service hosted under
`ino.bailinphil.com` (HTTP only, same as the kitchen-lights integration —
the Apache config for that vhost will need to grow beyond its current form)
composes a palette-locked PNG for the 1200×1600 portrait display. The
Inkplate is a thin client: wake → fetch active screen → display → sleep
until the server-specified time.

Rationale: ~90% of the system is testable on a Mac with zero hardware.
Per-refresh download is ~100–800 KB (PNG); ~0.5–1.5 GB/month at a 30-min
cadence. Each wake cycle costs ~2–4 mAh → roughly 1 month of battery at
30-min refresh, 2+ months hourly.

### REST API sketch (versioned, multi-screen)

- `GET /v1/active?device=<id>&battery=<v>&since=<etag>`
  → JSON manifest: `{image_url, image_etag, regions: [...], next_refresh_s, screen}`
- `GET /v1/images/<etag>.png` → the rendered PNG
- `POST /v1/screens/<name>` (e.g. `recipe`, `trip`) → another device pushes
  content / switches the active screen
- `POST /v1/devices/<id>/telemetry` → device reports battery, RSSI, wake
  reason, fetch/refresh timings, error counts
- `GET /v1/status` → health endpoint: per-device fetch counts,
  success/failure rates, last-seen timestamps

Region diffing: the server keeps each device's last-sent image (keyed by
etag via `since`). It renders the new image, diffs against the device's
previous one, and returns changed bounding boxes. If the etag is unknown
or dirty area exceeds a threshold, the manifest requests a full refresh.

### Key constraints & decisions

- **Palette:** exactly 6 Spectra colors (black, white, red, blue, green,
  yellow). Renderer enforces palette-only output; photos are
  quantized + dithered.
- **Orientation:** portrait, 1200×1600 (`setRotation` on device).
- **Regional update:** Spectra docs say no partial refresh, but regional
  update is believed supported at the driver level. Phase 5 spike verifies;
  if unsupported, device ignores the region list.
- **Power:** battery + scheduled refresh. Server computes `next_refresh_s`
  from the next meaningful event (routine transition, calendar event),
  clamped to min/max bounds. Device reports battery via query param /
  telemetry; server renders battery status into the image.
- **WiFi:** ordered list of SSID/password pairs in `/config.txt` on the SD
  card — editable without reflashing, keeps secrets out of the repo,
  makes the device portable.
- **Force refresh / input:** GPIO button on an RTC-capable wake pin (ext0/
  ext1). Qwiic Twist click is usable via its interrupt pin wired to a wake
  GPIO. Input handling sits behind an abstraction so an IR or BLE remote
  can be added later.
- **Observability:** every device error is (a) counted and POSTed via
  telemetry, (b) printed to Serial with an error code in debug builds.
  Server logs every request outcome; `/v1/status` exposes per-device
  counters (attempts, successes, failures, last error, last seen).

## Phases

### Phase 0 — Environment bring-up
- Arduino CLI/IDE, Inkplate board definitions + library, CH340 driver
  (macOS: WCH driver + enable in System Settings → Login Items & Extensions).
- **Checkpoint:** Hello World sketch displays on hardware.

### Phase 1 — Server renderer skeleton (no hardware needed)
- Python + Pillow. 1200×1600 portrait layout grid. Palette-locked drawing
  primitives. `make preview` → `dashboard.png` locally.
- Hosted design target: `ino.bailinphil.com` (HTTP).
- **Checkpoint:** static mock layout renders correctly at native resolution.

### Phase 2 — Data fetchers (each unit-tested with recorded fixtures)
1. **Weather** — reuse the existing OpenWeatherMap API key/query already
   on the server for kitchen-lights → kids' clothing icons.
2. **Calendar** — private ICS/iCal secret URLs per family calendar
   (no Google Cloud project, calendars stay private); merge N feeds.
3. **Photo of the day** — scrape `bailinphil.com/backlog`, resize,
   quantize/dither to the 6-color palette.
4. **Air quality** — kitchen-lights already publishes readings;
   first task is locating the endpoint/format.
5. **Kids' routine** — static YAML timetable (per-weekday schedule of
   named activities + icons); current activity + countdown to next.

### Phase 3 — Visual design iteration (still no hardware)
- Portrait layout; large type/icons legible at distance for kids.
- Golden-image tests: render from fixtures, inspect `dashboard.png`.
- Check dithering quality on photos in the 6-color palette.

### Phase 4 — REST API + TTL + region diffing + telemetry ingestion
- Manifest/image/screen-push/telemetry/status endpoints as above.
- Server-side image cache; per-device last-image store for region diffs.
- **Checkpoint:** curl round-trips verify manifest fields, region rects,
  and image bytes; pushed screens appear via `/v1/active`.

### Phase 5 — Firmware, staged bring-up (Arduino)
1. WiFi connect from SD-card credential list → HTTPS-optional GET → save
   image to SD → display (decouples download bugs from display bugs).
2. Stream-to-display without SD intermediate.
3. `setRotation(1)` portrait verification.
4. Battery voltage read → sent via `battery` param + telemetry POST.
5. **Spike:** regional/partial update on Spectra hardware — if the driver
   supports it, consume `regions[]` to skip flicker-prone full redraws.
6. `next_refresh_s` → RTC → deep sleep → scheduled wake.
7. GPIO wake button (force refresh / cycle screens); abstraction layer
   for future Twist-interrupt or remote-control input.
8. Failure path: failed fetch → keep existing screen, exponential backoff,
   error counter + Serial dump.
- **Checkpoint:** wake→fetch→display→sleep cycle runs 24 h with correct
  timing; button forces refresh; errors counted and reported.

### Phase 6 — Deploy & harden
- Flask (or similar) app behind Apache `mod_proxy` on the
  `ino.bailinphil.com` vhost; secrets via env vars, never committed.
- Measure actual wake-cycle power draw; tune refresh bounds.
- README documents config format, API, and deployment.

### Phase 7 — Observability validation
- `/v1/status` shows real per-device counters after a soak period.
- Induce failures (bad SSID, server down, malformed manifest) and confirm
  error counts, backoff, and Serial output behave as designed.
- Battery-life estimate validated against measured current draw.

## Known risks / open questions

- **PNG decode on ESP32-S3 at 1600×1200** may be slow/heavy. Fallback:
  serve raw or gzipped packed framebuffer (~720–960 KB), decode is trivial.
- **Regional update support on Spectra** is undocumented — Phase 5 spike.
- **Google ICS feeds** can lag behind real-time calendar edits (Google
  refreshes them on its own schedule).
- **Air-quality endpoint format** — discovery task in Phase 2.
- **HTTP only** on ino.bailinphil.com — fine for a dashboard; screen-push
  endpoints should take a shared token to prevent casual misuse.
