"""Stage 6 (page frames only): cut a frame into 9-slice pieces.

Apps need a page border at whatever page size they render, so a fixed-aspect frame is the
wrong shape to ship. The border is a corner motif plus a repeating edge unit, so we find
the repeat length and where the periodic run starts, and emit:

    slices/corner.svg   the corner motif (mirrored or rotated into the other three)
    slices/edge-h.svg   one horizontal repeat unit, data-repeat = its length
    slices/edge-v.svg   one vertical repeat unit

All pieces are traced from one quantization of the whole frame, so they share a palette and
their class names (`qa.scan.vectorize.trace_color(crops=...)`), and all of them use the
full frame's units: 100 = the full frame height, so an assembler can place them directly.
"""
import numpy as np
import cv2


def _profile(strip):
    """Column profile of a band, mean over its rows."""
    return cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY).astype(np.float32).mean(0)


def _shift_similarity(strip, period, step=4):
    """s[x] = correlation between the window at x and the window one period later.

    High where the ornament really repeats; it drops through the corner motif, which is
    what tells us where the repeating run begins.
    """
    grey = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY).astype(np.float32)
    width = grey.shape[1]
    if width < 2 * period + 1:
        return np.empty(0, int), np.empty(0)
    xs = np.arange(0, width - 2 * period + 1, step)
    out = np.zeros(len(xs))
    for i, x in enumerate(xs):
        a = grey[:, x:x + period].ravel(); b = grey[:, x + period:x + 2 * period].ravel()
        a = a - a.mean(); b = b - b.mean()
        norm = np.sqrt((a * a).sum() * (b * b).sum())
        out[i] = (a * b).sum() / norm if norm else 0.0
    return xs, out


def period(strip, min_period=20, min_score=0.65):
    """Repeat length of a border band, in pixels.

    Autocorrelation of the column profile proposes candidates; each is confirmed by
    actually comparing neighbouring windows, which rejects half-periods (an alternating
    two-motif band autocorrelates at half its true repeat).
    """
    profile = _profile(strip)
    n = len(profile)
    middle = profile[n // 4:3 * n // 4] - profile[n // 4:3 * n // 4].mean()
    if len(middle) < 4 * min_period:
        return None
    auto = np.correlate(middle, middle, "full")[len(middle) - 1:]
    auto = auto / auto[0]
    candidates = [i for i in range(min_period, len(auto) - 1)
                  if auto[i] > 0.3 and auto[i] >= auto[max(0, i - 5):i + 6].max()]
    candidates = [c for c in candidates if 3 * c < strip.shape[1]]
    for candidate in candidates + [2 * c for c in candidates if 6 * c < strip.shape[1]]:
        _, scores = _shift_similarity(strip[:, n // 4:3 * n // 4], candidate)
        if len(scores) and float(np.median(scores)) >= min_score:
            return int(candidate)
    return None


def periodic_run(strip, repeat, min_score=0.7, step=4):
    """[start, end) of the repeating run inside the band, snapped to whole repeats.

    The phase reference is the middle of the band, which is always inside the run.
    """
    xs, scores = _shift_similarity(strip, repeat, step=step)
    if not len(xs):
        return None
    good = scores >= min_score
    if not good.any():
        return None
    middle = len(xs) // 2
    if not good[middle]:                      # centre landed on a defect; take the widest run
        middle = int(np.argmax(np.convolve(good.astype(float), np.ones(5) / 5, "same")))
    left = middle
    while left > 0 and good[left - 1]:
        left -= 1
    right = middle
    while right + 1 < len(good) and good[right + 1]:
        right += 1
    reference = int(xs[middle])
    start = reference - ((reference - int(xs[left])) // repeat) * repeat
    end = reference + ((int(xs[right]) + repeat - reference) // repeat) * repeat
    return max(0, start), min(strip.shape[1], end)


def analyse(clean, slot_px, symmetry="4"):
    """Geometry of the 9-slice cut, in source pixels.

    Returns None when the border is not periodic enough to slice (then the frame ships
    whole and an app scales it) — that is a real answer, not a failure.
    """
    height, width = clean.shape[:2]
    x0, y0, x1, y1 = slot_px
    bands = {"top": y0, "left": x0}
    if min(bands.values()) < 8:
        return None
    top = clean[:y0]
    left = np.rot90(clean[:, :x0], -1)        # trace the vertical band as a horizontal one
    result = {}
    for name, strip, extent, across in (("h", top, width, bands["left"]), ("v", left, height, bands["top"])):
        repeat = period(strip)
        if not repeat:
            return None
        run = periodic_run(strip, repeat)
        if not run:
            return None
        start, end = run
        corner = min(start, extent - end)     # the two ends of one band are the same motif
        # The corner piece has to cover the band that meets it, and it has to end on a
        # repeat boundary or the first tile would start mid-motif.
        corner = start + max(0, -(-(across - start) // repeat)) * repeat if across > corner else corner
        corner = start + max(0, -(-(corner - start) // repeat)) * repeat
        if corner <= 0 or corner >= extent / 2:
            return None
        count = (extent - 2 * corner) // repeat
        if count < 2:
            return None
        result[name] = {"repeat": int(repeat), "corner": int(corner), "count": int(count), "start": int(start)}
    corner_w, corner_h = result["h"]["corner"], result["v"]["corner"]
    return {
        "corner_px": [0, 0, corner_w, corner_h],
        "edge_h_px": [corner_w, 0, corner_w + result["h"]["repeat"], bands["top"]],
        "edge_v_px": [0, corner_h, bands["left"], corner_h + result["v"]["repeat"]],
        "repeat_px": {"h": result["h"]["repeat"], "v": result["v"]["repeat"]},
        "repeats": {"h": result["h"]["count"], "v": result["v"]["count"]},
        "band_px": {"top": int(bands["top"]), "left": int(bands["left"])},
        "frame_px": [int(width), int(height)],
        "corner_mode": "rotate" if str(symmetry) == "c2" else "mirror",
    }


def assemble(pieces, size, geometry):
    """Rebuild the whole frame from the pieces (arrays), for the reconstruction check.

    The same arithmetic the `frame()` helper in dist/ does: corners at the four corners,
    edge units repeated between them and stretched by the rounding remainder.
    """
    width, height = size
    canvas = np.full((height, width, 3), 255, np.uint8)
    corner, edge_h, edge_v = pieces["corner"], pieces["edge-h"], pieces["edge-v"]
    ch, cw = corner.shape[:2]
    rotate = geometry["corner_mode"] == "rotate"

    def place(img, x, y):
        h, w = img.shape[:2]
        canvas[y:y + h, x:x + w] = np.minimum(canvas[y:y + h, x:x + w], img)

    def span(unit, total, vertical=False):
        count = max(1, round(total / (unit.shape[0] if vertical else unit.shape[1])))
        exact = total / count
        out = []
        for i in range(count):
            start = int(round(i * exact))
            stop = int(round((i + 1) * exact))
            size_ = (unit.shape[1], stop - start) if vertical else (stop - start, unit.shape[0])
            out.append((start, cv2.resize(unit, size_, interpolation=cv2.INTER_AREA)))
        return out

    place(corner, 0, 0)
    place(corner[::-1, ::-1] if rotate else corner[:, ::-1], width - cw, 0)
    place(corner[::-1, ::-1] if rotate else corner[::-1], 0, height - ch)
    place(corner if rotate else corner[::-1, ::-1], width - cw, height - ch)
    for x, tile in span(edge_h, width - 2 * cw):
        place(tile, cw + x, 0)
        place(tile[::-1, ::-1] if rotate else tile[::-1], cw + x, height - tile.shape[0])
    for y, tile in span(edge_v, height - 2 * ch, vertical=True):
        place(tile, 0, ch + y)
        place(tile[::-1, ::-1] if rotate else tile[:, ::-1], width - tile.shape[1], ch + y)
    return canvas
