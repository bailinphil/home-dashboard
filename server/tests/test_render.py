from preview import offline_data

from dashboard.render import dashboard
from dashboard.render.palette import COLORS, is_palette_pure


def test_render_size_and_mode():
    img = dashboard.render(offline_data())
    assert img.size == (1200, 1600)
    assert img.mode == "RGB"


def test_render_palette_purity():
    """Every pixel must be exactly one of the six Spectra colors."""
    img = dashboard.render(offline_data())
    assert is_palette_pure(img)
    # sanity: a colorful render should actually use most of the palette
    used = {c for _, c in img.getcolors(maxcolors=1 << 24)}
    assert len(used & set(COLORS)) >= 4


def test_render_degrades_with_missing_data():
    from dashboard.data import DashboardData
    from datetime import datetime
    img = dashboard.render(DashboardData(now=datetime.now()))
    assert img.size == (1200, 1600)
    assert is_palette_pure(img)
