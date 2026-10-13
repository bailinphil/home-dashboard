"""Region diffing between consecutive dashboard renders.

The Spectra panel's full refresh is slow and flashes; if the driver
supports regional updates we can redraw only what changed. We diff on a
coarse cell grid (e-ink regions must be block-aligned anyway) and merge
adjacent dirty cells into rectangles.
"""

from PIL import Image, ImageChops

CELL = 80


def diff_regions(old: Image.Image | None, new: Image.Image,
                 cell: int = CELL) -> list[list[int]] | None:
    """Return dirty rects as [[x, y, w, h], ...].

    None  -> caller should do a full refresh (no baseline / size change)
    []    -> identical images, no redraw needed
    [...] -> the listed regions changed
    """
    if old is None or old.size != new.size:
        return None

    diff = ImageChops.difference(old.convert("RGB"), new.convert("RGB"))
    w, h = new.size
    dirty = set()
    for cy in range(0, h, cell):
        for cx in range(0, w, cell):
            if diff.crop((cx, cy, min(cx + cell, w), min(cy + cell, h))).getbbox():
                dirty.add((cx, cy))

    if not dirty:
        return []
    if len(dirty) * cell * cell > w * h * 0.5:
        return None  # more than half the screen changed: full refresh wins
    return [list(r) for r in _merge_cells(dirty, cell)]


def _merge_cells(dirty: set[tuple[int, int]], cell: int) -> list[tuple[int, int, int, int]]:
    """Greedy merge: horizontal runs per row, then merge equal spans on adjacent rows."""
    rows: dict[int, list[tuple[int, int]]] = {}
    for y in sorted({y for _, y in dirty}):
        row_xs = sorted(x for x, yy in dirty if yy == y)
        spans = []
        start = prev = row_xs[0]
        for x in row_xs[1:]:
            if x != prev + cell:
                spans.append((start, prev + cell))
                start = x
            prev = x
        spans.append((start, prev + cell))
        rows[y] = spans

    rects = []
    open_spans: dict[tuple[int, int], list] = {}
    for y in sorted(rows):
        current = set(rows[y])
        for key in [k for k in open_spans if k not in current]:
            rects.append(tuple(open_spans.pop(key)))
        for x0, x1 in rows[y]:
            key = (x0, x1)
            if key in open_spans:
                open_spans[key][3] = y + cell
            else:
                open_spans[key] = [x0, y, x1, y + cell]
    rects.extend(tuple(v) for v in open_spans.values())
    return [(x0, y0, x1 - x0, y1 - y0) for x0, y0, x1, y1 in rects]
