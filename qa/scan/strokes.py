"""Centerline tracing: a linework mask -> smooth cubic-Bézier strokes of constant width.

Filled outlines (what a normal tracer gives) have a slightly wobbly width that follows
the scan; apps want the drawing as *strokes*. Steps:
  skeletonize(mask) -> split the skeleton into chains at junctions/endpoints ->
  measure each chain's thickness (2 x distance transform) -> smooth + fit cubic Béziers
  (Schneider's algorithm) -> group chains into 1-2 stroke widths.
Coordinates are in the same pixel space as the mask (trace scale).
"""
import numpy as np, cv2
from skimage.morphology import skeletonize

# ---------- skeleton -> chains --------------------------------------------------------
_N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

def _chains(skel):
    H, W = skel.shape
    pts = set(zip(*np.nonzero(skel)))
    def nbrs(p):
        """8-neighbours, minus diagonals that are already reachable through an
        orthogonal neighbour (otherwise every staircase pixel looks like a junction)."""
        y, x = p
        orth = [(y + dy, x + dx) for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)) if (y + dy, x + dx) in pts]
        diag = [(y + dy, x + dx) for dy, dx in ((-1, -1), (-1, 1), (1, -1), (1, 1)) if (y + dy, x + dx) in pts]
        diag = [q for q in diag if not any(abs(q[0]-o[0]) + abs(q[1]-o[1]) == 1 for o in orth)]
        return orth + diag
    deg = {p: len(nbrs(p)) for p in pts}
    nodes = {p for p, d in deg.items() if d != 2}          # endpoints + junctions
    used = set(); chains = []
    def walk(start, nxt):
        chain = [start, nxt]; used.add((start, nxt)); used.add((nxt, start))
        prev, cur = start, nxt
        while cur not in nodes:
            cand = [q for q in nbrs(cur) if q != prev]
            # prefer a neighbour not diagonal-adjacent to prev (avoid 2-pixel stubs)
            if not cand: break
            q = cand[0]
            if len(cand) > 1:
                cand.sort(key=lambda q: (abs(q[0]-prev[0]) + abs(q[1]-prev[1])) < 2)
                q = cand[0]
            if (cur, q) in used: break
            used.add((cur, q)); used.add((q, cur)); chain.append(q); prev, cur = cur, q
        return chain
    for n in nodes:
        for q in nbrs(n):
            if (n, q) not in used:
                chains.append(walk(n, q))
    # closed loops (every pixel degree 2)
    for p in pts:
        if p in nodes: continue
        if all((p, q) in used for q in nbrs(p)): continue
        c = walk(p, nbrs(p)[0])
        if len(c) > 2: chains.append(c)
    return chains

# ---------- Schneider cubic fitting -------------------------------------------------
def _bezier(ctrl, t):
    p0, p1, p2, p3 = ctrl; mt = 1 - t
    return (mt**3)[:, None]*p0 + (3*mt*mt*t)[:, None]*p1 + (3*mt*t*t)[:, None]*p2 + (t**3)[:, None]*p3

def _dev(ctrl, pts):
    """Robust fit error: max distance from 24 samples on the curve to the pixel chain
    (independent of the parameterisation, so a collapsed `u` can't fool it)."""
    b = _bezier(ctrl, np.linspace(0, 1, 24))
    d = np.sqrt(((b[:, None, :] - pts[None, :, :]) ** 2).sum(-1)).min(1)
    return float(d.max())

def _fit_cubic(pts, t0, t1, u, err):
    n = len(pts)
    if n == 2:
        d = np.linalg.norm(pts[1] - pts[0]) / 3
        return [[pts[0], pts[0] + t0*d, pts[1] + t1*d, pts[1]]]
    A = np.stack([t0[None, :] * (3*(1-u)**2*u)[:, None], t1[None, :] * (3*(1-u)*u**2)[:, None]], 1)   # n x 2 x 2
    C = np.einsum('nia,nja->ij', A, A)
    tmp = pts - ((1-u)**3)[:, None]*pts[0] - (3*(1-u)**2*u)[:, None]*pts[0] - (3*(1-u)*u**2)[:, None]*pts[-1] - (u**3)[:, None]*pts[-1]
    X = np.array([np.sum(A[:, 0, :]*tmp), np.sum(A[:, 1, :]*tmp)])
    det = C[0, 0]*C[1, 1] - C[1, 0]*C[0, 1]
    if abs(det) < 1e-12: a1 = a2 = 0.0
    else:
        a1 = (X[0]*C[1, 1] - X[1]*C[0, 1]) / det; a2 = (C[0, 0]*X[1] - C[1, 0]*X[0]) / det
    seg = np.linalg.norm(pts[-1] - pts[0]); arc = float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))
    if a1 < 1e-6 or a2 < 1e-6 or a1 > arc or a2 > arc:   # runaway handles -> safe default
        a1 = a2 = max(seg, arc * 0.5) / 3
    ctrl = [pts[0], pts[0] + t0*a1, pts[-1] + t1*a2, pts[-1]]
    bez = _bezier(ctrl, u); d = np.linalg.norm(bez - pts, axis=1); k = int(d.argmax()); e = d[k]
    if e < err and _dev(ctrl, pts) < err * 1.5: return [ctrl]
    if e < err * err:                                        # reparameterize and retry
        for _ in range(4):
            u2 = _reparam(pts, ctrl, u)
            if np.any(np.diff(u2) < -1e-6) or u2[-1] - u2[0] < 0.5: break   # collapsed parameterisation
            u = u2; ctrl = _fit_ctrl(pts, t0, t1, u, ctrl)
            bez = _bezier(ctrl, u); d = np.linalg.norm(bez - pts, axis=1); k = int(d.argmax()); e = d[k]
            if e < err and _dev(ctrl, pts) < err * 1.5: return [ctrl]
    # split at worst point (never at an endpoint)
    if k < 1 or k > n - 2: k = n // 2
    tc = pts[k+1] - pts[k-1] if 0 < k < n-1 else pts[-1] - pts[0]
    tc = tc / (np.linalg.norm(tc) + 1e-9)
    left = _fit_cubic(pts[:k+1], t0, -tc, _chord(pts[:k+1]), err)
    right = _fit_cubic(pts[k:], tc, t1, _chord(pts[k:]), err)
    return left + right

def _fit_ctrl(pts, t0, t1, u, ctrl):
    A = np.stack([t0[None, :] * (3*(1-u)**2*u)[:, None], t1[None, :] * (3*(1-u)*u**2)[:, None]], 1)
    C = np.einsum('nia,nja->ij', A, A)
    tmp = pts - ((1-u)**3)[:, None]*pts[0] - (3*(1-u)**2*u)[:, None]*pts[0] - (3*(1-u)*u**2)[:, None]*pts[-1] - (u**3)[:, None]*pts[-1]
    X = np.array([np.sum(A[:, 0, :]*tmp), np.sum(A[:, 1, :]*tmp)])
    det = C[0, 0]*C[1, 1] - C[1, 0]*C[0, 1]
    if abs(det) < 1e-12: return ctrl
    a1 = (X[0]*C[1, 1] - X[1]*C[0, 1]) / det; a2 = (C[0, 0]*X[1] - C[1, 0]*X[0]) / det
    arc = float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))
    if a1 < 1e-6 or a2 < 1e-6 or a1 > arc or a2 > arc: return ctrl
    return [pts[0], pts[0] + t0*a1, pts[-1] + t1*a2, pts[-1]]

def _reparam(pts, ctrl, u):
    p0, p1, p2, p3 = ctrl
    b = _bezier(ctrl, u)
    d1 = 3*((1-u)**2)[:, None]*(p1-p0) + 6*((1-u)*u)[:, None]*(p2-p1) + 3*(u**2)[:, None]*(p3-p2)
    d2 = 6*(1-u)[:, None]*(p2-2*p1+p0) + 6*u[:, None]*(p3-2*p2+p1)
    num = np.sum((b-pts)*d1, 1); den = np.sum(d1*d1, 1) + np.sum((b-pts)*d2, 1)
    un = np.where(np.abs(den) > 1e-12, u - num/np.where(np.abs(den) > 1e-12, den, 1), u)
    return np.clip(un, 0, 1)

def _chord(pts):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    return d / (d[-1] if d[-1] > 0 else 1)

def fit_polyline(pts, err=0.9, closed=False):
    pts = np.asarray(pts, float)
    if len(pts) < 2: return []
    # a closed (or nearly closed) chain has a tiny chord and a huge arc: the fit degenerates,
    # so fit it as two open halves
    if len(pts) >= 8 and np.linalg.norm(pts[-1] - pts[0]) < 0.15 * float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1))):
        h = len(pts) // 2
        return fit_polyline(pts[:h+1], err) + fit_polyline(pts[h:], err)
    t0 = pts[1] - pts[0]; t0 /= np.linalg.norm(t0) + 1e-9
    t1 = pts[-2] - pts[-1]; t1 /= np.linalg.norm(t1) + 1e-9
    return _fit_cubic(pts, t0, t1, _chord(pts), err)

# ---------- pipeline entry ----------------------------------------------------------
def _smooth(poly, win):
    if win < 2 or len(poly) < win + 2: return np.asarray(poly, float)   # convolve 'valid' would return garbage
    k = np.ones(win) / win
    p = np.asarray(poly, float)
    inner = np.stack([np.convolve(p[:, i], k, mode="valid") for i in range(2)], 1)
    return np.vstack([p[:1], inner, p[-1:]]) if len(inner) else p

def _prune(skel, max_len, rounds=3):
    """Delete endpoint branches shorter than max_len (skeleton spurs)."""
    skel = skel.copy()
    for _ in range(rounds):
        removed = 0
        pts = set(zip(*np.nonzero(skel)))
        deg = {}
        for p in pts:
            y, x = p
            orth = [(y+dy, x+dx) for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)) if (y+dy, x+dx) in pts]
            diag = [(y+dy, x+dx) for dy, dx in ((-1,-1),(-1,1),(1,-1),(1,1)) if (y+dy, x+dx) in pts]
            deg[p] = len(orth) + sum(not any(abs(q[0]-o[0]) + abs(q[1]-o[1]) == 1 for o in orth) for q in diag)
        for c in _chains(skel):
            ends = (deg.get(c[0], 0) == 1) + (deg.get(c[-1], 0) == 1)
            if ends >= 1 and len(c) < max_len and not (ends == 2 and len(c) >= 3):
                for (y, x) in c:
                    if deg.get((y, x), 0) < 3: skel[y, x] = False; removed += 1
        if not removed: break
    return skel

def trace_strokes(mask, err=1.1, min_len=2, smooth_win=7, width_split=1.6, prune_factor=2.5):
    """mask: bool HxW linework. Returns list of stroke groups:
       [{"width": w, "paths": ["M.. C..", ...]}] with 1-2 groups (thin / thick)."""
    m = mask.astype(np.uint8)
    if not m.any():
        return []
    skel = skeletonize(m > 0)
    dist = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    w_global = 2 * float(np.median(dist[skel]))
    skel = _prune(skel, max_len=int(round(w_global * prune_factor)) + 2)
    chains = [c for c in _chains(skel) if len(c) >= min_len]
    items = []
    for c in chains:
        w = 2 * float(np.median([dist[y, x] for y, x in c])) if len(c) >= 2 * w_global else w_global
        poly = _smooth([(x + 0.5, y + 0.5) for y, x in c], smooth_win)
        beziers = fit_polyline(poly, err)
        if not beziers: continue
        d = f"M{beziers[0][0][0]:.2f} {beziers[0][0][1]:.2f}" + "".join(
            f"C{b[1][0]:.2f} {b[1][1]:.2f} {b[2][0]:.2f} {b[2][1]:.2f} {b[3][0]:.2f} {b[3][1]:.2f}" for b in beziers)
        items.append((w, d))
    if not items: return []
    ws = np.array([w for w, _ in items]); med = w_global
    thick = ws > med * width_split
    groups = []
    if (~thick).any(): groups.append({"width": round(float(np.median(ws[~thick])), 2), "paths": [d for (w, d), t in zip(items, thick) if not t]})
    if thick.any(): groups.append({"width": round(float(np.median(ws[thick])), 2), "paths": [d for (w, d), t in zip(items, thick) if t]})
    return groups
