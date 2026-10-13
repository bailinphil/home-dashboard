from pathlib import Path

from dashboard.fetchers import photo

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_backlog_html():
    html = (FIXTURES / "backlog.html").read_text()
    url = photo.parse_backlog_html(html, "https://bailinphil.com/backlog")
    assert url == "https://bailinphil.com/static/images/backlog/bordered/69/friendly.png"


def test_parse_backlog_html_missing():
    assert photo.parse_backlog_html("<html><body>no images</body></html>",
                                    "https://bailinphil.com/backlog") is None
