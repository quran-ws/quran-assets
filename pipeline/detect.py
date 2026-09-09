"""Step 2: locate ornament assets on a page raster.

Detectors return a list of (x0, y0, x1, y1) boxes in page-pixel coordinates, sorted
top->bottom. Each asset *type* has its own detector; add one here and reference it from
assets.json ("detector": "<name>"). Extra keys in the job's "detect" config are passed
as keyword arguments.

surah_header: the frame's outline is one continuous line, so after a small closing the
whole header (both ornament halves + name cartouche + title) is a single connected
component of non-white pixels. We keep components that are wide, landscape, not the page
border, and dense in *colour* (text lines are ink-rich but colour-poor).
"""
import numpy as np, cv2

def colored_mask(bgr, s_min=25, v_min=40, v_max=245):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return (hsv[..., 1] >= s_min) & (hsv[..., 2] >= v_min) & (hsv[..., 2] <= v_max)

def ink_mask(bgr, white_thresh=200):
    return bgr.min(axis=2) < white_thresh

def surah_header(bgr, s_min=25, white_thresh=200, close=3, min_w=0.30, min_h=0.015, max_h=0.14,
                 min_aspect=3.0, min_color=0.12, pad=0.02, **_):
    """Returns header boxes top->bottom (page-pixel coords), padded by `pad`*height so the
    title and outline are never clipped."""
    H, W = bgr.shape[:2]
    ink = ink_mask(bgr, white_thresh).astype(np.uint8)
    col = colored_mask(bgr, s_min=s_min)
    if close > 1:
        ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
    cands = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if w < W * min_w or h < H * min_h or h > H * max_h or w < min_aspect * h:
            continue
        color_frac = col[y:y+h, x:x+w].mean()      # share of the bbox that is coloured
        if color_frac < min_color:
            continue
        cands.append([x, y, x + w, y + h, color_frac])
    cands.sort(key=lambda b: b[1])
    # safety: a top/bottom mirror-symmetric pair is the page border, not headers
    boxes = [c[:4] for c in cands]
    for i in range(len(boxes)):
        for j in range(len(boxes) - 1, i + 1, -1):
            t, b = boxes[i], boxes[j]
            ct, cb = (t[1] + t[3]) / 2, (b[1] + b[3]) / 2
            ht, hb = t[3] - t[1], b[3] - b[1]
            if abs((ct + cb) / 2 - H / 2) < H * 0.03 and abs(ht - hb) < 0.3 * max(ht, hb):
                boxes = boxes[i + 1:j]; break
        else: continue
        break
    out = []
    for x0, y0, x1, y1 in boxes:
        p = int(pad * (y1 - y0))
        out.append((max(0, x0 - p), max(0, y0 - p), min(W, x1 + p), min(H, y1 + p)))
    return out

def page_frame(bgr, s_min=25, close=7, min_frac=0.55, pad=0.006, **_):
    """The decorative page border: the biggest closed coloured component (after a closing
    that bridges its ornaments). Margin markers / running heads fall outside its bbox."""
    H, W = bgr.shape[:2]
    m = colored_mask(bgr, s_min=s_min).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    best = None
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if w > W * min_frac and h > H * min_frac and (best is None or a > best[4]):
            best = (x, y, w, h, a)
    if best is None: return []
    x, y, w, h, _ = best; p = int(pad * H)
    return [(max(0, x - p), max(0, y - p), min(W, x + w + p), min(H, y + h + p))]

def frame_interior_rect(bgr, white_thresh=200, grow=2):
    """Inner rectangle of the page border = bbox of the paper region reachable from the
    page centre without crossing ink (the border's inner outline is continuous, text is
    not). Returns (x0, y0, x1, y1) or None if the flood leaks to the page edge."""
    H, W = bgr.shape[:2]
    ink = (bgr.min(axis=2) < white_thresh).astype(np.uint8)
    ink = cv2.dilate(ink, np.ones((2 * grow + 1, 2 * grow + 1), np.uint8))
    paper = (1 - ink)
    mask = np.zeros((H + 2, W + 2), np.uint8)
    cy, cx = H // 2, W // 2
    # seed: nearest paper pixel to the centre
    ys, xs = np.nonzero(paper[cy - 40:cy + 40, cx - 40:cx + 40])
    if len(ys) == 0: return None
    k = int(np.argmin((ys - 40) ** 2 + (xs - 40) ** 2)); sy, sx = cy - 40 + ys[k], cx - 40 + xs[k]
    cv2.floodFill(paper.copy(), mask, (int(sx), int(sy)), 2, flags=8 | cv2.FLOODFILL_MASK_ONLY | (1 << 8))
    reg = mask[1:-1, 1:-1] > 0
    # the text block is where the flooded paper covers a large share of each row/column;
    # thin paper gaps in the band the flood leaked into never reach that coverage
    rows = np.where(reg.mean(axis=1) > 0.30)[0]; cols = np.where(reg.mean(axis=0) > 0.30)[0]
    if len(rows) == 0 or len(cols) == 0: return _interior_by_profile(bgr)
    y0, y1, x0, x1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    if x0 <= 1 or y0 <= 1 or x1 >= W - 1 or y1 >= H - 1 or (x1 - x0) < 0.4 * W or (y1 - y0) < 0.4 * H:
        return _interior_by_profile(bgr)          # leaked, or seed fell inside a letter -> profile fallback
    return (int(x0), int(y0), int(x1), int(y1))

def _interior_by_profile(bgr, s_min=12, hi=0.10, lo=0.04, run=8, core=(0.3, 0.7)):
    """Inner edge per side = first run of `run` rows/cols with almost no colour after the
    coloured border band, scanning inward from each edge."""
    H, W = bgr.shape[:2]
    col = colored_mask(bgr, s_min=s_min)
    rows = col[:, int(W*core[0]):int(W*core[1])].mean(axis=1)
    cols = col[int(H*core[0]):int(H*core[1]), :].mean(axis=0)
    def edge(prof, forward):
        idx = list(range(len(prof))) if forward else list(range(len(prof) - 1, -1, -1))
        seen, quiet = False, 0
        for i in idx:
            if prof[i] > hi: seen, quiet = True, 0
            elif seen and prof[i] < lo:
                quiet += 1
                if quiet >= run: return i - (run - 1) if forward else i + (run - 1)
            else: quiet = 0
        return None
    t, b, l, r = edge(rows, True), edge(rows, False), edge(cols, True), edge(cols, False)
    # the frame is mirror-symmetric: complete a side that failed (or ran into the crop edge) from its twin
    def ok(v, n): return v is not None and 0.03 * n < v < 0.97 * n
    if not ok(t, H) and ok(b, H): t = H - b
    if not ok(b, H) and ok(t, H): b = H - t
    if not ok(l, W) and ok(r, W): l = W - r
    if not ok(r, W) and ok(l, W): r = W - l
    if None in (t, b, l, r) or b - t < H * 0.3 or r - l < W * 0.3: return None
    return (int(l) + 2, int(t) + 2, int(r) - 2, int(b) - 2)

def _mirror_residual(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return float(np.abs(g - g[:, ::-1]).mean() + np.abs(g - g[::-1]).mean()) / 2

def ayah_marker(bgr, s_min=25, min_px=0.010, max_px=0.040, hull_min=0.50, color_min=0.04, pad=0.15, white_thresh=205, **_):
    """Ayah-end ornaments: inside the page frame, *ink* components (outline + fill + digit)
    that are near-square, ½–1½ line heights, round (convex hull fills the box like a
    disc) and contain colour (words are pure black). Ranked most mirror-symmetric first;
    every candidate is saved for `pick`."""
    H, W = bgr.shape[:2]
    inner = frame_interior_rect(bgr)
    ink = (bgr.min(axis=2) < white_thresh).astype(np.uint8)
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    col = colored_mask(bgr, s_min=s_min)
    if inner:
        ix0, iy0, ix1, iy1 = inner; roi = np.zeros_like(ink); roi[iy0 + 4:iy1 - 4, ix0 + 4:ix1 - 4] = 1; ink = ink * roi
    n, lab, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
    lo, hi = H * min_px, H * max_px
    out = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if not (lo < w < hi and lo < h < hi and 0.55 < w / h < 1.5): continue
        if col[y:y+h, x:x+w].mean() < color_min: continue
        comp = (lab[y:y+h, x:x+w] == i).astype(np.uint8)
        cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        hull_area = cv2.contourArea(cv2.convexHull(np.vstack(cnts)))
        if hull_area / (w * h) < hull_min: continue
        p = int(pad * max(w, h))
        crop = bgr[max(0, y - p):y + h + p, max(0, x - p):x + w + p]
        out.append((max(0, x - p), max(0, y - p), min(W, x + w + p), min(H, y + h + p), _mirror_residual(crop)))
    out.sort(key=lambda b: (b[4], b[1]))
    return [b[:4] for b in out]

DETECTORS = {"surah_header": surah_header, "ayah_marker": ayah_marker, "page_frame": page_frame}
