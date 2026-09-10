"""Assemble a 9-sliced page frame at any page size.

The reference implementation of the arithmetic; `dist/index.js` does the same in the
browser and `tests/test_slices.py` checks this one against the whole frame. Pieces are in
frame units (100 = the source frame's height), so they compose without any rescaling
beyond the deliberate stretch that absorbs the rounding remainder of the repeat count.
"""
import json
from pathlib import Path

from qa import ROOT


def _inner(svg_text):
    """The drawable content of a piece: everything inside its root <svg>, minus metadata."""
    body = svg_text.split(">", 1)[1].rsplit("</svg>", 1)[0]
    if "<metadata>" in body:
        body = body.split("</metadata>", 1)[1]
    return body.strip()


def _tiles(total, unit):
    """Whole repeats across `total`, each stretched by the same small factor to fit exactly."""
    count = max(1, round(total / unit))
    step = total / count
    return count, step


def assemble(asset_dir, width, height, geometry=None):
    """An <svg> string for one frame drawn at `width` x `height` (frame units, height 100 = the source).

    Pieces are defined once and placed with <use>, so a page border costs three traced
    shapes however large the page is.
    """
    asset_dir = Path(asset_dir)
    if geometry is None:
        geometry = json.loads((asset_dir / "meta.json").read_text())["slices"]
    if not geometry:
        raise ValueError(f"{asset_dir.name} has no slices; use color.svg")
    frame_h = geometry["frame_px"][1]
    unit = 100.0 / frame_h
    corner_w = geometry["corner_px"][2] * unit
    corner_h = geometry["corner_px"][3] * unit
    repeat_h = geometry["repeat_px"]["h"] * unit
    repeat_v = geometry["repeat_px"]["v"] * unit
    rotate = geometry.get("corner_mode") == "rotate"

    defs = []
    for name in ("corner", "edge-h", "edge-v"):
        defs.append(f'<g id="{name}">{_inner((asset_dir / "slices" / f"{name}.svg").read_text())}</g>')

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.4f} {height:.4f}" '
           f'data-asset="page-frame" data-assembled-from="slices">', "<defs>", *defs, "</defs>"]
    place = lambda name, transform: out.append(f'<use href="#{name}" transform="{transform}"/>')

    place("corner", "translate(0 0)")
    place("corner", f"translate({width:.4f} 0) scale(-1 1)" if not rotate else f"matrix(-1 0 0 -1 {width:.4f} {corner_h:.4f})")
    place("corner", f"translate(0 {height:.4f}) scale(1 -1)" if not rotate else f"matrix(-1 0 0 -1 {corner_w:.4f} {height:.4f})")
    place("corner", f"matrix(-1 0 0 -1 {width:.4f} {height:.4f})" if not rotate else f"translate({width - corner_w:.4f} {height - corner_h:.4f})")

    count, step = _tiles(width - 2 * corner_w, repeat_h)
    for i in range(count):
        x = corner_w + i * step
        scale = step / repeat_h
        place("edge-h", f"translate({x:.4f} 0) scale({scale:.6f} 1)")
        place("edge-h", f"translate({x:.4f} {height:.4f}) scale({scale:.6f} -1)")
    count, step = _tiles(height - 2 * corner_h, repeat_v)
    for i in range(count):
        y = corner_h + i * step
        scale = step / repeat_v
        place("edge-v", f"translate(0 {y:.4f}) scale(1 {scale:.6f})")
        place("edge-v", f"translate({width:.4f} {y:.4f}) scale(-1 {scale:.6f})")
    out.append("</svg>")
    return "\n".join(out)


def native_size(asset_dir):
    """The source frame's own size in frame units, for a like-for-like comparison."""
    meta = json.loads((Path(asset_dir) / "meta.json").read_text())
    _, _, width, height = (float(v) for v in meta["viewBox"].split())
    return width, height


if __name__ == "__main__":
    import sys
    directory = ROOT / "assets/page-frames" / sys.argv[1]
    width, height = (float(v) for v in sys.argv[2:4]) if len(sys.argv) > 3 else native_size(directory)
    print(assemble(directory, width, height))
