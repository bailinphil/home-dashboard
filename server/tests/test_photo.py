from pathlib import Path

from dashboard.fetchers import photo

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_feed_returns_newest_item():
    feed = (FIXTURES / "backlog_feed.xml").read_text()
    p = photo.parse_feed(feed, "https://bailinphil.com/backlog/feed")
    assert p.title == "pawing"
    assert p.image_url == "https://bailinphil.com/images/backlog/bordered/39/pawing.png"
    assert p.published is not None
    assert p.published.year == 2026


def test_parse_feed_empty():
    empty = '<?xml version="1.0"?><rss version="2.0"><channel><title>x</title></channel></rss>'
    assert photo.parse_feed(empty, "https://bailinphil.com/backlog/feed") is None


def test_parse_feed_no_image():
    noimg = ('<?xml version="1.0"?><rss version="2.0"><channel>'
             '<item><title>x</title><description>text only</description></item>'
             '</channel></rss>')
    assert photo.parse_feed(noimg, "https://bailinphil.com/backlog/feed") is None
