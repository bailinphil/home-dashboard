"""Photo-of-the-day fetcher.

Scrapes the backlog page for the day's image
(/static/images/backlog/bordered/<id>/<name>.png). The RSS feed at
/backlog/feed was returning a 500 at time of writing, so HTML scraping
is the reliable path.
"""

import re
from urllib.parse import urljoin

import requests

_BACKLOG_IMG_RE = re.compile(r'src="([^"]*/static/images/backlog/bordered/[^"]+)"')


def parse_backlog_html(html: str, base_url: str) -> str | None:
    """Return the absolute URL of the photo-of-the-day, or None."""
    match = _BACKLOG_IMG_RE.search(html)
    if not match:
        return None
    return urljoin(base_url, match.group(1))


def fetch_photo_of_day(backlog_url: str) -> tuple[str, bytes]:
    """Return (image_url, image_bytes) for the current backlog photo."""
    page = requests.get(backlog_url, timeout=15)
    page.raise_for_status()
    image_url = parse_backlog_html(page.text, backlog_url)
    if image_url is None:
        raise ValueError("no backlog image found on page")
    img = requests.get(image_url, timeout=30)
    img.raise_for_status()
    return image_url, img.content
