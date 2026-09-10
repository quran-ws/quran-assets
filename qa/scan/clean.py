"""Step 3: cleaners turn a raw crop into a reusable ornament.

cartouche_text: remove the surah title from the name cartouche. The cartouche is the
flat light region around the crop centre; the title is the set of *holes* in that
region. We inpaint the holes with the surrounding fill so the slot is empty and the
app can draw its own surah name there. Returns (clean_bgr, slot_box, slot_fill_bgr, slot_mask).
"""
import numpy as np, cv2

def _fill_holes(mask):
    h, w = mask.shape
    ff = np.pad(mask, 1).astype(np.uint8).copy()
    cv2.floodFill(ff, None, (0, 0), 2)          # 2 = reachable background
    outside = ff[1:-1, 1:-1] == 2
    return ~outside                              # component + its holes

def strip_edge_rules(bgr, max_thick=0.02, min_len=0.5, white=(255, 255, 255)):
    """Erase page rules that the crop padding caught: ink components touching the crop
    edge that are thin (< max_thick * H) and long (> min_len of that side)."""
    H, W = bgr.shape[:2]
    ink = (bgr.min(axis=2) < 200).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
    out = bgr.copy(); t = max(2, int(H * max_thick))
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        touches = x == 0 or y == 0 or x + w == W or y + h == H
        vertical_rule = w <= t and h >= min_len * H
        horizontal_rule = h <= t and w >= min_len * W
        if touches and (vertical_rule or horizontal_rule):
            m = cv2.dilate((lab == i).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
            out[m] = white
    return out

def cartouche_text(bgr, tol=38, seed_band=0.35, dilate=2, inpaint=True, **_):
    bgr = strip_edge_rules(bgr)
    H, W = bgr.shape[:2]
    cx, cy = W // 2, H // 2
    # cartouche fill colour = median of non-ink pixels in the central band
    band = bgr[int(H*0.3):int(H*0.7), int(W*(0.5-seed_band/2)):int(W*(0.5+seed_band/2))]
    light = band.min(axis=2) > 150
    bg = np.median(band[light].reshape(-1, 3), axis=0) if light.any() else np.array([255, 255, 255])
    near = (np.abs(bgr.astype(int) - bg.astype(int)).max(axis=2) < tol).astype(np.uint8)
    near = cv2.morphologyEx(near, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(near, 4)
    # pick the near-bg component that covers most of the central band
    ys, xs = slice(int(H*0.35), int(H*0.65)), slice(int(W*0.4), int(W*0.6))
    counts = np.bincount(lab[ys, xs].ravel(), minlength=n); counts[0] = 0
    ci = int(counts.argmax())
    comp = lab == ci
    x, y, w, h = stats[ci][:4]
    holes = _fill_holes(comp) & ~comp
    # only holes strictly inside the cartouche box, away from its outline
    m = np.zeros_like(holes); m[y+2:y+h-2, x+2:x+w-2] = True
    text = (holes & m).astype(np.uint8)
    if dilate: text = cv2.dilate(text, np.ones((2*dilate+1, 2*dilate+1), np.uint8))
    out = bgr.copy()
    # flatten the whole slot (component + title holes) to its fill colour: removes the
    # title AND scan noise in one go, which is what a clean reusable frame needs
    slot = comp | (text > 0)
    slot = cv2.morphologyEx(slot.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    slot_in = cv2.erode(slot.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)  # keep the outline's AA edge
    out[slot_in] = bg
    return out, (int(x), int(y), int(x + w), int(y + h)), tuple(int(v) for v in bg[::-1]), slot

def frame_interior(bgr, **_):
    """Page frame: blank the text block inside the border with paper white. The block is
    the paper region reachable from the page centre (see detect.frame_interior_rect); it
    becomes the slot = the page's content area for the app."""
    from .detect import frame_interior_rect
    H, W = bgr.shape[:2]
    r = frame_interior_rect(bgr)
    if r is None: return bgr.copy(), None, None, None
    left, top, right, bot = r
    out = bgr.copy(); out[top:bot, left:right] = 255
    slot = np.zeros((H, W), bool); slot[top:bot, left:right] = True
    out = strip_cartouches(out, exclude=slot)
    # The border is one connected ornament. Disconnected scan flecks outside it
    # must not turn into floating coloured strokes in the exported frame.
    ink = (out.min(axis=2) < 235).astype(np.uint8)
    joined = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(joined, 8)
    if count > 1:
        largest = 1 + int(stats[1:, cv2.CC_STAT_AREA].argmax())
        keep = cv2.dilate((labels == largest).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        out[~keep] = 255
    return out, (int(left), int(top), int(right), int(bot)), (255, 255, 255), slot

def _cartouche_boxes(bgr, exclude, min_area_frac=0.0008, light=200):
    """Compact light boxes in the band that hold (unsaturated) text: running heads, page number."""
    H, W = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lightm = (bgr.min(axis=2) > light).astype(np.uint8)
    if exclude is not None: lightm[exclude] = 0
    lightm = cv2.morphologyEx(lightm, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(lightm, 4)
    text = (hsv[..., 1] < 90) & (bgr.min(axis=2) < 150)
    colm = (hsv[..., 1] >= 110) & (hsv[..., 2] >= 60)
    boxes = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a < min_area_frac * H * W or a / (w * h) < 0.5 or h > 0.08 * H or w > 0.6 * W: continue
        comp = lab[y:y+h, x:x+w] == i; holes = _fill_holes(comp) & ~comp
        if (holes & text[y:y+h, x:x+w]).sum() < 20 or colm[y:y+h, x:x+w][holes].sum() > 30: continue
        boxes.append((int(x), int(y), int(w), int(h)))
    return boxes

def _period(profile, min_p=15):
    """Dominant repeat length of a 1-D pattern profile (first autocorrelation peak)."""
    x = profile - profile.mean()
    if len(x) < 4 * min_p or np.abs(x).sum() == 0: return None
    ac = np.correlate(x, x, mode="full")[len(x) - 1:]; ac /= ac[0] + 1e-9
    seg = ac[min_p:len(x) // 2]
    if len(seg) < 3: return None
    i = int(np.argmax(seg)); return min_p + i if seg[i] > 0.3 else None

def _period_by_template(band, x_from, x_to, T=36, min_p=15):
    """Repeat length of the band ornament in columns [x_from, x_to): match a T-wide
    template against the rest of the span and take the first strong off-centre peak."""
    seg = band[:, x_from:x_to]
    if seg.shape[1] < 3 * T: return None
    g = cv2.cvtColor(seg, cv2.COLOR_BGR2GRAY)
    tpl = g[:, :T]
    res = cv2.matchTemplate(g, tpl, cv2.TM_CCOEFF_NORMED)[0]
    for i in range(min_p, len(res)):
        if res[i] > 0.6 and res[i] >= res[max(0, i - 3):i + 4].max():
            return i
    return None

def _heal_band_gap(out, rows, x0, x1, margin=8, avoid=()):
    """Fill band columns [x0, x1) from neighbouring intact ornament, shifted by a whole
    number of pattern periods so the phase matches. `avoid` = other gaps (x0, x1) that must
    not be used as a source."""
    r0, r1 = rows; W = out.shape[1]
    band = out[r0:r1].copy()
    gap = x1 - x0
    def free(a, b):   # source span [a, b) inside the image and clear of every gap
        return a >= 0 and b <= W and all(b <= g0 - margin or a >= g1 + margin for g0, g1 in avoid)
    # free stretches next to the gap: up to the next gap (or the edge) on each side
    r_end = min([W] + [g0 - margin for g0, g1 in avoid if g0 >= x1])
    l_start = max([0] + [g1 + margin for g0, g1 in avoid if g1 <= x0])
    P = _period_by_template(band, x1 + margin, r_end)
    if P is None: P = _period_by_template(band, l_start, x0 - margin)
    L = int(np.ceil(gap / P) * P) if P else gap
    for k in range(3):                                   # shrink by whole periods if a source overlaps a gap
        Lk = L - k * (P or 0)
        if Lk < gap: break
        if free(x1, x1 + Lk):
            out[r0:r1, x1 - Lk:x1] = band[:, x1:x1 + Lk]; return True
        if free(x0 - Lk, x0):
            out[r0:r1, x0:x0 + Lk] = band[:, x0 - Lk:x0]; return True
    # last resort: tile the nearest free stretch of one period (or the gap width)
    T = P or gap
    if free(x1 + margin, x1 + margin + T):
        src = band[:, x1 + margin:x1 + margin + T]
    elif free(x0 - margin - T, x0 - margin):
        src = band[:, x0 - margin - T:x0 - margin]
    else: return False
    tile = np.tile(src, (1, int(np.ceil(gap / T)) + 1, 1))[:, :gap]
    out[r0:r1, x0:x1] = tile
    return True

def strip_cartouches(bgr, exclude=None, band_frac=0.25, margin=18, ref_w=120, **_):
    """Remove running-head / page-number cartouches from the band: the cartouche span is
    erased outside the band's outer edge (measured on the intact ornament next to it),
    then the missing ornament under it is healed from the neighbouring pattern, shifted
    by whole pattern periods. The band itself is never cut."""
    H, W = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    col = (hsv[..., 1] >= 25) & (hsv[..., 2] >= 40) & (hsv[..., 2] <= 245)
    out = bgr.copy()
    boxes = _cartouche_boxes(bgr, exclude)
    spans = [(max(0, bx - margin), min(W, bx + bw + margin)) for bx, by, bw, bh in boxes]
    sides = [(by + bh / 2) < H * 0.5 for bx, by, bw, bh in boxes]
    for (x, y, w, h), (x0, x1), side in zip(boxes, spans, sides):
        others = [sp for sp, sd in zip(spans, sides) if sp != (x0, x1) and sd == side]
        top_side = (y + h / 2) < H * 0.5
        # reference span: intact band right next to the cartouche
        if x1 + margin + ref_w <= W: rx0, rx1 = x1 + margin, x1 + margin + ref_w
        else: rx0, rx1 = max(0, x0 - margin - ref_w), max(0, x0 - margin)
        prof = col[:, rx0:rx1].mean(axis=1)
        ys = np.where(exclude[:, (rx0 + rx1) // 2])[0] if exclude is not None else None
        if top_side:
            rows = np.where(prof > band_frac)[0]
            if len(rows) == 0: continue
            band_top = int(rows[0]); out[:max(0, band_top - 3), x0:x1] = 255
            if ys is not None and len(ys): _heal_band_gap(out, (max(0, band_top - 3), int(ys.min())), x0, x1, margin, avoid=others)
        else:
            rows = np.where(prof > band_frac)[0]
            if len(rows) == 0: continue
            band_bot = int(rows[-1]); out[min(H, band_bot + 4):, x0:x1] = 255
            if ys is not None and len(ys): _heal_band_gap(out, (int(ys.max()) + 1, min(H, band_bot + 4)), x0, x1, margin, avoid=others)
    return out

def marker(bgr, white_thresh=205, grow=2, **_):
    """Ayah marker: erase everything not connected to the ornament in the crop centre
    (neighbouring letters), then blank the number inside like a title cartouche."""
    H, W = bgr.shape[:2]
    ink = (bgr.min(axis=2) < white_thresh).astype(np.uint8)
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
    if n > 1:
        cy, cx = H // 2, W // 2
        best = max(range(1, n), key=lambda i: (stats[i][0] <= cx <= stats[i][0] + stats[i][2] and stats[i][1] <= cy <= stats[i][1] + stats[i][3], stats[i][4]))
        keep = cv2.dilate((lab == best).astype(np.uint8), np.ones((2 * grow + 1, 2 * grow + 1), np.uint8)).astype(bool)
        ff = np.pad((lab == best).astype(np.uint8), 1).copy(); cv2.floodFill(ff, None, (0, 0), 2)
        keep |= (ff[1:-1, 1:-1] != 2)
        out = bgr.copy(); out[~keep] = 255
    else:
        out = bgr.copy()
    return cartouche_text(out, seed_band=0.3)

def none(bgr, **_):
    return bgr.copy(), None, None, None

CLEANERS = {"cartouche_text": cartouche_text, "frame_interior": frame_interior, "marker": marker, "none": none}
