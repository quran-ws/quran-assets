"""Step 4: raster ornament -> SVG path data (mono + multi-colour).

Tracing is done by vtracer in binary mode, one layer at a time, so we control the
palette: k-means in Lab space picks `k` colours, the paper colour is dropped
(transparent), layers are stacked biggest-first and each mask is dilated by 1px so
adjacent layers never show hairline seams.
"""
import numpy as np, cv2, re, tempfile, os
import vtracer
from . import strokes as _strokes

VTRACER_KEYS = {"filter_speckle", "corner_threshold", "length_threshold", "max_iterations", "splice_threshold", "path_precision", "mode"}
COLOR_KEYS = {"stroke_prune_factor", "strokes", "line_mode", "line_min_px", "paper_thresh", "line_dark", "line_s_max", "min_px", "merge_de", "min_frac", "white_layer", "smooth", "median", "open_px", "light_thresh", "light_min_px"}

PATH_RE = re.compile(r'<path\b([^>]*)>', re.S)
ATTR_RE = re.compile(r'([\w:-]+)="([^"]*)"')
NUM_RE = re.compile(r'-?\d+(?:\.\d+)?')

def _bake_translate(d, dx, dy):
    """vtracer emits absolute M/C/L/Z data at the origin plus transform=translate(dx,dy);
    fold the offset into the coordinates so every path is self-contained."""
    toks = re.findall(r'[A-Za-z]|-?\d+(?:\.\d+)?', d)
    out, i = [], 0
    for tok in toks:
        if tok[0].isalpha():
            out.append(tok); i = 0
        else:
            v = float(tok) + (dx if i % 2 == 0 else dy); i += 1
            out.append(f"{v:.2f}".rstrip("0").rstrip("."))
    return " ".join(out)

def _paths(svg):
    res = []
    for m in PATH_RE.finditer(svg):
        a = dict(ATTR_RE.findall(m.group(1)))
        dx = dy = 0.0
        t = re.search(r'translate\(\s*(-?[\d.]+)[ ,]+(-?[\d.]+)', a.get("transform", ""))
        if t: dx, dy = float(t.group(1)), float(t.group(2))
        res.append(_bake_translate(a["d"], dx, dy))
    return res

def _trace_mask(mask, scale, prescaled=False, **opts):
    """mask: bool HxW (or already at `scale`x when prescaled). Returns path 'd' strings in
    `scale`x pixel units (svgout folds the scale back into one transform)."""
    if prescaled:
        up = mask.astype(np.uint8)
    else:
        up = cv2.resize(mask.astype(np.uint8) * 255, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        up = (up > 127).astype(np.uint8)
    img = 255 - up * 255                       # vtracer binary: dark = shape
    with tempfile.TemporaryDirectory() as td:
        pi, po = os.path.join(td, "m.png"), os.path.join(td, "m.svg")
        cv2.imwrite(pi, img)
        o = dict(colormode="binary", hierarchical="stacked", mode="spline", filter_speckle=4,
                 corner_threshold=60, length_threshold=3.5, max_iterations=10,
                 splice_threshold=45, path_precision=2)
        o.update(opts)
        vtracer.convert_image_to_svg_py(pi, po, **o)
        svg = open(po).read()
    return _paths(svg)

def mono_mask(bgr, dark=170, s_min=60, v_max=225):
    """Everything that reads as 'drawn' in a one-colour rendering: dark linework plus
    saturated fills. Pale fills (cartouche, paper) stay transparent."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return (gray < dark) | ((hsv[..., 1] >= s_min) & (hsv[..., 2] <= v_max))

def line_mask(bgr, dark=125, s_max=70, black=55):
    """Dark *achromatic* linework (the black outlines). Dark saturated fills (navy,
    maroon) are NOT lines; only near-black passes regardless of saturation."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return ((gray < dark) & (hsv[..., 1] < s_max)) | ((gray < black) & (hsv[..., 1] < 150))

def line_mask_auto(sharp, k=8, erode_px=2, survive_max=0.30, dark_max=140, seed=1):
    """Hue-agnostic linework: k-means over all pixels, then take the dark clusters whose
    pixels mostly vanish under a small erosion (thin strokes) — black, navy, dark green
    outlines all qualify; a navy *fill* survives erosion and stays a fill."""
    lab = cv2.cvtColor(sharp, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.3)
    cv2.setRNGSeed(seed)
    _, lbl, centers = cv2.kmeans(lab, k, None, crit, 4, cv2.KMEANS_PP_CENTERS)
    lbl = lbl.reshape(sharp.shape[:2])
    gray = cv2.cvtColor(sharp, cv2.COLOR_BGR2GRAY)
    ker = np.ones((2 * erode_px + 1, 2 * erode_px + 1), np.uint8)
    out = np.zeros(sharp.shape[:2], bool)
    order = np.argsort(centers[:, 0])                     # darkest first (L channel)
    for i in order:
        m = (lbl == i)
        if not m.any(): continue
        if gray[m].mean() > dark_max: break               # only dark clusters can be ink lines
        survive = cv2.erode(m.astype(np.uint8), ker).sum() / m.sum()
        if survive < survive_max: out |= m
    return out

def trace_mono(bgr, scale=3, smooth=1.5, min_px=60, slot_mask=None, paper_thresh=225, line_dark=125, line_s_max=70, prescaled=False, line_mode="auto", **opts):
    """One-colour silhouette: every printed (non-paper) pixel inside the frame, minus the
    name slot. Paper-coloured parts of the design (white lines) become transparent cut-outs."""
    up = cv2.bilateralFilter(bgr, 7, 45, 7) if prescaled else _upscale(bgr, scale)
    paper = up.min(axis=2) >= paper_thresh
    lines = _drop_small(line_mask_auto(bgr if prescaled else _upscale(bgr, scale, smooth=False)) if line_mode == "auto" else line_mask(up, line_dark, line_s_max), min_px)
    m = ~paper & ~_outside(paper, lines)
    if slot_mask is not None:
        sm = _slot_at_scale(slot_mask, up.shape)
        m &= ~sm
    m = _drop_small(_smooth_mask(_drop_small(m, min_px), smooth), min_px)
    paths = _trace_mask(m, scale, prescaled=True, **{**SMOOTH_TRACE, **opts})
    slot_paths = _trace_mask(sm > 0, scale, prescaled=True, **{**SMOOTH_TRACE, **opts}) if slot_mask is not None else []
    return paths, slot_paths

def _upscale(bgr, scale, smooth=True):
    up = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return cv2.bilateralFilter(up, 7, 45, 7) if smooth else up

def _drop_small(mask, min_px):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    keep = np.zeros(n, bool); keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_px
    return keep[lab]

def quantize(bgr, k=8, exclude=None, merge_de=11.0, min_frac=0.03, seed=1, assign=None):
    """k-means in Lab over pixels not in `exclude`, then merge centres closer than
    `merge_de` (CIE76 distance, 8-bit Lab units) so one printed ink = one cluster.
    Returns (labels HxW with -1 for excluded, centers as BGR uint8)."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    sel = np.ones(len(lab), bool) if exclude is None else ~exclude.ravel()
    paper = (bgr.min(axis=2) >= 232).ravel()                # cluster the ink only: paper is its own
    if (sel & ~paper).sum() > 5000: sel &= ~paper           # layer, and must not dominate min_frac
    k = min(k, int(sel.sum()))
    if k == 0:
        return np.full(bgr.shape[:2], -1, np.int32), np.empty((0, 3), np.uint8)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.2)
    cv2.setRNGSeed(seed)
    _, lbl, centers = cv2.kmeans(lab[sel], k, None, crit, 6, cv2.KMEANS_PP_CENTERS)
    lbl = lbl.ravel()
    # merge near-identical centres (union-find), weighted by member count
    counts = np.bincount(lbl, minlength=k).astype(np.float32)
    parent = list(range(k))
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    changed = True
    while changed:
        changed = False
        roots = sorted(set(find(i) for i in range(k)))
        for a in roots:
            for b in roots:
                if b <= a or find(a) != a or find(b) != b: continue
                if np.linalg.norm(centers[a] - centers[b]) < merge_de:
                    w = counts[a] + counts[b]
                    centers[a] = (centers[a] * counts[a] + centers[b] * counts[b]) / w
                    counts[a] = w; counts[b] = 0; parent[b] = a; changed = True
    # absorb minor clusters (gradient shading, scan tints) into their nearest main colour
    total = counts.sum()
    changed = True
    while changed:
        changed = False
        roots = sorted(set(find(i) for i in range(k)))
        for a in roots:
            if find(a) != a or counts[a] >= min_frac * total or len(roots) <= 2: continue
            others = [b for b in roots if b != a and find(b) == b]
            b = min(others, key=lambda b: np.linalg.norm(centers[a] - centers[b]))
            centers[b] = (centers[a] * counts[a] + centers[b] * counts[b]) / (counts[a] + counts[b])
            counts[b] += counts[a]; counts[a] = 0; parent[a] = b; changed = True; break
    roots = sorted(set(find(i) for i in range(k)))
    remap = {r: n for n, r in enumerate(roots)}
    lbl = np.array([remap[find(i)] for i in range(k)], np.int32)[lbl]
    centers = centers[roots]
    if assign is not None:   # fit on the smoothed image, assign by the sharp one
        lab2 = cv2.cvtColor(assign, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)[sel]
        d = ((lab2[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
        lbl = d.argmin(1).astype(np.int32)
    labels = np.full(len(lab), -1, np.int32); labels[sel] = lbl
    centers_bgr = cv2.cvtColor(centers.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_LAB2BGR)[0]
    return labels.reshape(bgr.shape[:2]), centers_bgr

def _reassign_ring(labels, ring):
    """Assign edge pixels from a labelled fill, never from excluded line pixels."""
    donors = (~ring) & (labels >= 0)
    if not donors.any() or not ring.any():
        return labels.copy()
    _, nearest = cv2.distanceTransformWithLabels(
        (~donors).astype(np.uint8), cv2.DIST_L2, 3,
        labelType=cv2.DIST_LABEL_PIXEL)
    lookup = np.full(nearest.max() + 1, -1, np.int32)
    lookup[nearest[donors]] = labels[donors]
    out = labels.copy()
    out[ring] = lookup[nearest[ring]]
    return out

def _outside(paper, lines):
    """Paper pixels connected to the crop border (outside the frame's closed outline)."""
    wall = cv2.morphologyEx(lines.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    free = (paper & ~wall).astype(np.uint8)
    h, w = free.shape
    ff = np.pad(free, 1); ff[0, :] = ff[-1, :] = ff[:, 0] = ff[:, -1] = 1
    n, lab = cv2.connectedComponents(ff, connectivity=4)
    return (lab[1:-1, 1:-1] == lab[0, 0]) & paper

def _slot_at_scale(slot_mask, shape):
    """Slot mask -> smooth bool mask at trace scale, pulled 1px inside the cartouche outline."""
    sm = slot_mask.astype(np.float32) if slot_mask.shape == shape[:2] else cv2.resize(slot_mask.astype(np.float32), (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)
    sm = cv2.GaussianBlur(sm, (0, 0), 2.0) > 0.5
    return cv2.erode(sm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)

def _smooth_mask(m, sigma):
    """Blur + re-threshold: rounds off scan jaggies without moving edges."""
    if not sigma: return m
    b = cv2.GaussianBlur(m.astype(np.float32), (0, 0), sigma)
    return b > 0.5

SMOOTH_TRACE = dict(corner_threshold=60, length_threshold=6.0, splice_threshold=55, filter_speckle=14, max_iterations=12)

def trace_color(bgr, k=8, scale=3, paper_thresh=232, line_dark=125, line_s_max=70, min_px=60, merge_de=11.0,
                min_frac=0.03, white_layer=True, smooth=1.7, median=5, open_px=3,
                light_thresh=200, light_min_px=600, slot_mask=None, strokes=True, prescaled=False,
                line_mode="auto", line_min_px=20, stroke_prune_factor=2.5, crops=None, **opts):
    """Layers bottom->top: fills sorted light->dark (each grown 1px so it tucks under its
    neighbours), then the dark linework on top. Paper *outside* the frame is transparent;
    paper inside it becomes a 'white' fill layer when white_layer is on.
    Returns [{hex, area, paths}].

    `crops={name: (x0, y0, x1, y1)}` (source pixels) traces those windows instead of the
    whole image and returns {name: layers}. One quantization feeds every window, so the
    9-slice pieces of a frame share one palette and one set of class names — otherwise
    each piece would fit its own k-means and the tiles would not match at the seams."""
    if prescaled: sharp = bgr; up = cv2.bilateralFilter(bgr, 7, 45, 7)
    else: up = _upscale(bgr, scale); sharp = _upscale(bgr, scale, smooth=False)
    raw = line_mask_auto(sharp) if line_mode == "auto" else line_mask(up, line_dark, line_s_max)
    raw = cv2.morphologyEx(raw.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
    lines = _drop_small(_smooth_mask(_drop_small(raw, line_min_px), smooth * 0.8), line_min_px)
    ring = cv2.dilate(lines.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~lines
    sm = _slot_at_scale(slot_mask, up.shape) if slot_mask is not None else np.zeros(up.shape[:2], bool)
    paper_pixels = up.min(axis=2) >= paper_thresh
    labels, centers = quantize(up, k, exclude=lines | ring | sm | paper_pixels,
                               merge_de=merge_de, min_frac=min_frac, assign=sharp)
    # Paper remains an explicit layer even when it was excluded from k-means.
    paper_id = len(centers)
    centers = np.vstack([centers, np.array([[255, 255, 255]], np.uint8)])
    labels[paper_pixels & ~lines & ~sm] = paper_id
    labels = _reassign_ring(labels, ring)
    # Neutral edge shades belong to antialiasing, not separate printed inks.
    # Keep broad neutral fills; absorb only clusters that have no solid core.
    for index, center in enumerate(centers):
        if int(center.max()) - int(center.min()) > 20 or center.min() >= 232:
            continue
        mask = labels == index
        if not mask.any():
            continue
        core = cv2.erode(mask.astype(np.uint8), np.ones((5, 5), np.uint8))
        if core.sum() / mask.sum() < 0.15:
            labels = _reassign_ring(labels, mask)
    if median:   # majority filter kills 1-2px slivers of a wrong colour along edges
        lm = np.where(labels < 0, 255, labels).astype(np.uint8)
        lm = cv2.medianBlur(lm, median)
        labels = np.where((labels < 0) | (lm == 255), labels, lm.astype(np.int32))
    paper_ids = [i for i, c in enumerate(centers) if c.min() >= paper_thresh]
    # thin scanned white lines never read as pure white; small fragments of any very light
    # cluster are really paper -> hand them to the paper cluster
    if paper_ids:
        for i, c in enumerate(centers):
            if i in paper_ids or c.min() < light_thresh: continue
            small = (labels == i) & ~_drop_small(labels == i, light_min_px)
            labels[small] = paper_ids[0]
    paper = np.isin(labels, paper_ids)
    outside = _outside(paper, lines) if paper_ids else np.zeros_like(paper)
    fills = []
    def add(m, c):
        if open_px:  # slivers narrower than open_px (anti-aliased edges of other colours) go away
            k_ = np.ones((open_px, open_px), np.uint8)
            m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, k_).astype(bool)
        m = _drop_small(_smooth_mask(_drop_small(m, min_px), smooth), min_px)
        m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        if not m.any(): return
        lum = 0.114 * c[0] + 0.587 * c[1] + 0.299 * c[2]
        fills.append({"hex": "#%02x%02x%02x" % (int(c[2]), int(c[1]), int(c[0])), "area": int(m.sum()), "lum": float(lum), "mask": m})
    for i, c in enumerate(centers):
        if i in paper_ids: continue
        add(labels == i, c)
    if white_layer and paper_ids:
        add(paper & ~outside, np.array([255, 255, 255]))
    fills.sort(key=lambda l: -l["lum"])
    # the name slot is its own layer, transparent by default, and is cut out of every fill
    if slot_mask is not None:
        sm = _slot_at_scale(slot_mask, up.shape)
        for l in fills: l["mask"] &= ~sm
        fills = [l for l in fills if l["mask"].any()]
        fills.insert(0, {"hex": "none", "cls": "slot", "area": int(sm.sum()), "lum": 999.0, "mask": sm})
    lc = np.median(up[lines].reshape(-1, 3), axis=0) if lines.any() else np.zeros(3)
    line_hex = "#%02x%02x%02x" % (int(lc[2]), int(lc[1]), int(lc[0]))
    groups = _strokes.trace_strokes(lines, prune_factor=stroke_prune_factor) if strokes else []
    if groups:
        # grow every fill under the strokes (only into the line zone) so fills never
        # leave a gap at the stroke's edge whatever the renderer's anti-aliasing does
        r = int(np.ceil(max(g["width"] for g in groups) / 2)) + 1
        k_ = np.ones((2 * r + 1, 2 * r + 1), np.uint8)
        # Expand into ink and its antialiased rim only. Expanding the zone by a
        # stroke radius paints over intentional white channels and pale petals.
        zone = lines | ring
        for l in fills:
            if l.get("cls") == "slot":
                continue
            grown = cv2.dilate(l["mask"].astype(np.uint8), k_).astype(bool)
            l["mask"] = l["mask"] | (grown & zone)
            if slot_mask is not None:
                l["mask"] &= ~sm
    # Name the groups here, not in the writer: every crop must use the palette's own
    # names, so that c3 is the same ink in the corner piece and in the edge tile.
    index = 0
    for l in fills:
        if not l.get("cls"):
            index += 1
            l["cls"] = f"c{index}"

    def emit(window=None):
        def cut(mask):
            return mask if window is None else mask[window[1]:window[3], window[0]:window[2]]
        out = []
        for l in fills:
            m = cut(l["mask"])
            if not m.any():
                continue
            out.append({**{k: v for k, v in l.items() if k != "mask"},
                        "area": int(m.sum()), "paths": _trace_mask(m, scale, prescaled=True, **{**SMOOTH_TRACE, **opts})})
        cut_lines = cut(lines)
        if strokes:
            cut_groups = _strokes.trace_strokes(cut_lines, prune_factor=stroke_prune_factor) if window is not None else groups
            out.append({"hex": line_hex, "area": int(cut_lines.sum()), "lum": 0.0, "stroke": True, "cls": "line",
                        "groups": cut_groups, "paths": [d for g in cut_groups for d in g["paths"]]})
        else:
            out.append({"hex": line_hex, "area": int(cut_lines.sum()), "lum": 0.0, "cls": "line",
                        "paths": _trace_mask(cut_lines, scale, prescaled=True, **{**SMOOTH_TRACE, **opts})})
        return out

    if crops is None:
        return emit()
    factor = 1 if prescaled else scale
    return {name: emit(tuple(int(round(v * factor)) for v in box)) for name, box in crops.items()}
