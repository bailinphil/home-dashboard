from PIL import Image, ImageDraw

from dashboard import diff
from dashboard.render import palette as pal


def _img(w=400, h=300):
    return Image.new("RGB", (w, h), pal.WHITE)


def test_no_baseline_full_refresh():
    assert diff.diff_regions(None, _img()) is None


def test_identical_no_regions():
    a = _img()
    assert diff.diff_regions(a, a.copy()) == []


def test_small_change_one_region():
    a, b = _img(), _img()
    ImageDraw.Draw(b).rectangle([10, 10, 30, 30], fill=pal.RED)
    regions = diff.diff_regions(a, b, cell=80)
    assert regions is not None and len(regions) >= 1
    # the changed pixel must be inside one of the rects
    assert any(x <= 10 < x + w and y <= 10 < y + h for x, y, w, h in regions)


def test_regions_aligned_and_merged():
    a, b = _img(), _img()
    d = ImageDraw.Draw(b)
    d.rectangle([0, 0, 159, 79], fill=pal.RED)      # two adjacent cells in row 0
    d.rectangle([0, 240, 79, 299], fill=pal.BLUE)   # separate cell, row 3
    regions = diff.diff_regions(a, b, cell=80)
    assert [160, 0, 160, 80] in regions or [0, 0, 160, 80] in regions
    assert [0, 240, 80, 60] in regions or [0, 240, 80, 80] in regions


def test_huge_change_falls_back_to_full():
    a, b = _img(), _img()
    ImageDraw.Draw(b).rectangle([0, 0, 400, 300], fill=pal.RED)
    assert diff.diff_regions(a, b) is None
