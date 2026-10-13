"""Photo-of-the-day fetcher.

Reads the backlog RSS feed (/backlog/feed) and takes the newest item —
the most recently published photo. The backlog page itself recycles old
photos when nothing new is published, so the feed is the authoritative
"picture of the day". Each item's <description> contains an <img> tag
with the bordered image URL, plus the photo title and caption.
"""

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

import requests

_IMG_SRC_RE = re.compile(r'<img\s+src="([^"]+)"')


@dataclass
class PhotoOfDay:
    image_url: str
    title: str
    published: object  # datetime from RSS pubDate
    caption_html: str


def parse_feed(feed_xml: str, base_url: str) -> PhotoOfDay | None:
    """Return the newest backlog entry from RSS XML, or None if empty."""
    root = ET.fromstring(feed_xml)
    item = root.find("./channel/item")
    if item is None:
        return None

    description = item.findtext("description", "")
    match = _IMG_SRC_RE.search(html.unescape(description))
    if not match:
        return None

    pub = item.findtext("pubDate")
    return PhotoOfDay(
        image_url=urljoin(base_url, match.group(1)),
        title=item.findtext("title", ""),
        published=parsedate_to_datetime(pub) if pub else None,
        caption_html=html.unescape(description),
    )


def fetch_photo_of_day(feed_url: str) -> tuple[PhotoOfDay, bytes]:
    """Return (PhotoOfDay, image_bytes) for the most recent backlog photo."""
    feed = requests.get(feed_url, timeout=15)
    feed.raise_for_status()
    photo = parse_feed(feed.text, feed_url)
    if photo is None:
        raise ValueError("no photo found in backlog feed")
    img = requests.get(photo.image_url, timeout=30)
    img.raise_for_status()
    return photo, img.content
