"""Mirror symmetry: these frames are one quadrant mirrored left/right (and usually
top/bottom). We find the mirror axes, align each mirrored copy to the reference with a
small shift (scans are never perfectly square), check the mirrored copies really match, and hand back one quadrant plus an overlap margin so the mirrored
copies never show a seam. svgout emits the quadrant once and <use> mirrors for the rest.
Works at trace scale (the upscaled image) for sub-pixel accuracy."""
import numpy as np, cv2

def _score(gray, axis, c):
    if axis == "x":
        w = min(c, gray.shape[1] - c); a = gray[:, c - w:c]; b = gray[:, c:c + w][:, ::-1]
    else:
        w = min(c, gray.shape[0] - c); a = gray[c - w:c, :]; b = gray[c:c + w, :][::-1]
    if w <= 8: return 1e9
    a = a.astype(np.float32); b = b.astype(np.float32); m = (a < 225) | (b < 225)
    return float(np.abs(a[m] - b[m]).mean()) if m.any() else 1e9

def find_axes(bgr, search=0.04):
    gray = cv2.GaussianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (0, 0), 1.0)
    H, W = gray.shape
    xs = range(int(W * (0.5 - search)), int(W * (0.5 + search)) + 1)
    ys = range(int(H * (0.5 - 2 * search)), int(H * (0.5 + 2 * search)) + 1)
    sx = {c: _score(gray, "x", c) for c in xs}; sy = {c: _score(gray, "y", c) for c in ys}
    return min(sx, key=sx.get), min(sy, key=sy.get)

def deskew(bgr, ink_thresh=200, span=(0.15, 0.85)):
    """Rotate so the frame's long top/bottom edges are horizontal. Angle = median slope of
    the first/last ink row per column over the middle of the width. Returns (img, degrees)."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY); H, W = gray.shape
    ink = gray < ink_thresh
    xs = np.arange(int(W * span[0]), int(W * span[1]))
    top = np.array([np.argmax(ink[:, x]) if ink[:, x].any() else -1 for x in xs], float)
    bot = np.array([H - 1 - np.argmax(ink[::-1, x]) if ink[:, x].any() else -1 for x in xs], float)
    angles = []
    for e in (top, bot):
        ok = e >= 0
        if ok.sum() < 50: continue
        # robust slope: median of pairwise slopes between points far apart
        x, y = xs[ok], e[ok]; n = len(x); k = n // 3
        sl = (y[k:] - y[:-k]) / (x[k:] - x[:-k])
        angles.append(np.degrees(np.arctan(np.median(sl))))
    if not angles: return bgr, 0.0
    ang = float(np.mean(angles))
    if abs(ang) < 0.02: return bgr, ang
    M = cv2.getRotationMatrix2D((W / 2, H / 2), ang, 1.0)
    return cv2.warpAffine(bgr, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255)), ang

def _canvas(img, xc, yc, fill):
    H, W = img.shape[:2]; W2, H2 = 2 * xc, 2 * yc
    out = np.full((H2, W2) + img.shape[2:], fill, img.dtype)
    h, w = min(H, H2), min(W, W2); out[:h, :w] = img[:h, :w]
    return out

def _align(ref, img, r):
    """Best integer shift (dx, dy) in [-r, r] of img onto ref: L1 over *ink* pixels of
    either image, so a mostly-white page frame is judged on its ornament, not its paper."""
    g0 = cv2.GaussianBlur(cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY), (0, 0), 2.0).astype(np.float32)
    g1 = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (0, 0), 2.0).astype(np.float32)
    best = (1e18, 0, 0)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            s = np.roll(np.roll(g1, dy, 0), dx, 1)
            a, b = g0[r:-r, r:-r], s[r:-r, r:-r]
            m = (a < 225) | (b < 225)
            d = float(np.abs(a[m] - b[m]).mean()) if m.any() else 0.0
            if d < best[0]: best = (d, dx, dy)
    return best

def symmetrize(bgr, slot_mask=None, margin=6, shift=4, y_ratio_max=0.6, force=None):
    """bgr at trace scale. Returns dict: quadrant (bgr), slot (mask|None), full (W2,H2),
    folds (4 or 2), axes (xc,yc), residuals."""
    bgr, angle = deskew(bgr)
    if slot_mask is not None and abs(angle) >= 0.02:
        H, W = slot_mask.shape; M = cv2.getRotationMatrix2D((W / 2, H / 2), angle, 1.0)
        slot_mask = cv2.warpAffine(slot_mask.astype(np.uint8), M, (W, H), flags=cv2.INTER_NEAREST) > 0
    xc, yc = find_axes(bgr)
    c = _canvas(bgr, xc, yc, 255)
    copies = {"lr": c[:, ::-1], "ud": c[::-1], "both": c[::-1, ::-1]}
    aligned, res = {}, {}
    for k, im in copies.items():
        d, dx, dy = _align(c, im, shift)
        aligned[k] = np.roll(np.roll(im, dy, 0), dx, 1); res[k] = d
    # is top/bottom really a mirror? compare against a deliberately wrong offset
    gray = cv2.GaussianBlur(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY), (0, 0), 2.0)
    baseline = _score(gray, "y", int(yc * 1.25))
    if force: folds = force
    elif res["both"] < 0.6 * min(res["lr"], res["ud"]) and res["both"] < y_ratio_max * baseline:
        folds = "c2"                                   # 180° rotation only (running vines)
    elif res["ud"] < y_ratio_max * baseline and res["lr"] < y_ratio_max * baseline: folds = 4
    elif res["lr"] < y_ratio_max * baseline: folds = 2
    else: folds = 1
    # Use the top-left quadrant as-is (averaging the copies blurs linework: scans carry
    # slight rotation/scale so distant parts never align to the pixel). The mirrored
    # copies were only needed to decide 2- vs 4-fold and to measure the residual.
    if folds == 4:   qh, qw = yc + margin, xc + margin
    elif folds == 2: qh, qw = 2 * yc, xc + margin
    elif folds == "c2": qh, qw = yc + margin, 2 * xc
    else:            qh, qw = 2 * yc, 2 * xc
    quad = c[:qh, :qw]
    qs = None
    if slot_mask is not None:
        s = _canvas(slot_mask.astype(np.uint8), xc, yc, 0)
        if folds == 4: s = s | s[:, ::-1] | s[::-1] | s[::-1, ::-1]
        elif folds == 2: s = s | s[:, ::-1]
        elif folds == "c2": s = s | s[::-1, ::-1]
        qs = s[:qh, :qw] > 0
    return {"quadrant": quad, "slot": qs, "full": (2 * xc, 2 * yc), "folds": folds, "axes": (xc, yc), "deskew_deg": round(angle, 3),
            "residual": {k: round(v, 2) for k, v in res.items()}, "baseline": round(baseline, 2)}
