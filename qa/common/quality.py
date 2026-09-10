"""Raster review and regression gate: python -m qa quality --help.

IoU compares dark/saturated ink with clean.png, excluding the declared slot.
Symmetrization intentionally changes the scan, so scores measure regressions,
not an absolute ship-quality threshold. Endpoint counts are diagnostics only:
open floral strokes and endpoints meeting another path's interior are legitimate.
"""
import argparse
import copy
import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import cairosvg
import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree
from svgpathtools import parse_path

from qa import ROOT
NS = "{http://www.w3.org/2000/svg}"
ET.register_namespace("", NS[1:-1])


def raster(root, width, mode="color"):
    root = copy.deepcopy(root)
    for group in root.iter(NS + "g"):
        cls = group.get("class", "")
        if mode == "fills" and cls == "line":
            group.set("display", "none")
        if mode == "lines" and cls and cls != "line":
            group.set("display", "none")
        if mode == "slot":
            if cls == "slot":
                group.set("fill", "black")
            elif cls:
                group.set("display", "none")
    data = cairosvg.svg2png(bytestring=ET.tostring(root), output_width=width)
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGBA"))


def on_white(rgba):
    alpha = rgba[..., 3:4].astype(float) / 255
    return (rgba[..., :3] * alpha + 255 * (1 - alpha)).astype(np.uint8)


def ink(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    return (gray < 170) | ((hsv[..., 1] >= 60) & (hsv[..., 2] <= 225))


def compare_images(actual, reference, valid, palette):
    a, b = ink(actual) & valid, ink(reference) & valid
    union = (a | b).sum()
    result = {"ink_iou": float((a & b).sum() / max(1, union))}
    colors = [p for p in palette if p["hex"].startswith("#")]
    centers = np.array([[int(p["hex"][i:i+2], 16) for i in (1, 3, 5)] for p in colors], np.uint8)
    centers = cv2.cvtColor(centers[None], cv2.COLOR_RGB2LAB)[0].astype(float)
    histograms, channel_histograms = [], []
    for rgb in (actual, reference):
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)[valid].astype(float)
        channel_histograms.append(np.array([
            np.bincount(lab[:, channel].astype(int), minlength=256) / max(1, len(lab))
            for channel in range(3)]))
        labels = np.zeros(len(lab), np.int32)
        # Bound memory when inspecting a large frame at 4000px.
        for start in range(0, len(lab), 100000):
            chunk = lab[start:start+100000]
            labels[start:start+len(chunk)] = ((chunk[:, None] - centers) ** 2).sum(2).argmin(1)
        histograms.append(np.bincount(labels, minlength=len(colors)) / max(1, len(labels)))
    delta = np.abs(histograms[0] - histograms[1])
    # Fixed Lab bins keep comparisons meaningful even when a palette gains a
    # restored flower shade. Mean marginal Wasserstein distance, normalized 0–1.
    result["palette_distance"] = float(np.abs(np.cumsum(
        channel_histograms[0] - channel_histograms[1], axis=1)).sum() / (3 * 255))
    result["palette_area_delta"] = {p["class"]: float(d) for p, d in zip(colors, delta)}
    return result


def endpoint_diagnostics(root):
    points, widths = [], []
    for group in root.iter(NS + "g"):
        if group.get("stroke-width") is None:
            continue
        width = float(group.get("stroke-width"))
        for element in group.iter(NS + "path"):
            for path in parse_path(element.get("d")).continuous_subpaths():
                if not path or path.isclosed():
                    continue
                points.extend([(path.start.real, path.start.imag), (path.end.real, path.end.imag)])
                widths.extend([width, width])
    if len(points) < 2:
        return {"open_ends": len(points), "isolated_ends": len(points)}
    distances = cKDTree(points).query(points, k=2)[0][:, 1]
    return {"open_ends": len(points), "isolated_ends": int((distances > widths).sum())}


def review_asset(directory, out, widths):
    meta = json.loads((directory / "meta.json").read_text())
    root = ET.parse(directory / "color.svg").getroot()
    clean_path = directory / "clean.png"
    if not clean_path.exists():
        clean_path = directory / "clean.jpg"
    clean = np.asarray(Image.open(clean_path).convert("RGB"))
    report = {"sizes": {}, "continuity": endpoint_diagnostics(ET.parse(directory / "line.svg").getroot())}
    out.mkdir(parents=True, exist_ok=True)
    for width in widths:
        rgba = raster(root, width)
        actual = on_white(rgba)
        reference = cv2.resize(clean, (actual.shape[1], actual.shape[0]), interpolation=cv2.INTER_CUBIC)
        slot = raster(root, width, "slot")[..., 3] > 0
        valid = ~slot
        # Full-resolution corner review avoids enormous page-sized comparison sheets.
        if width == 4000:
            actual, reference, valid = actual[:1000, :1000], reference[:1000, :1000], valid[:1000, :1000]
        result = compare_images(actual, reference, valid, meta["palette"])
        if width == 1000:
            fills = raster(root, width, "fills")[..., 3]
            lines = raster(root, width, "lines")[..., 3] > 200
            # Outer stroke edges and the text slot intentionally have no fill.
            # Only inspect strokes inside the enclosed ornament, beyond one
            # stroke width of those transparent boundaries.
            occupied = rgba[..., 3] > 100
            exterior = np.pad((~occupied).astype(np.uint8), 1, constant_values=1)
            cv2.floodFill(exterior, None, (0, 0), 2)
            enclosed = (exterior[1:-1, 1:-1] != 2) & ~slot
            source_width = clean.shape[1]
            margin = max(2, int(np.ceil(max(meta.get("stroke_widths_px") or [1]) * width / source_width)))
            interior = cv2.erode(enclosed.astype(np.uint8), np.ones((2 * margin + 1, 2 * margin + 1), np.uint8)) > 0
            zone = lines & interior
            result["interior_line_pixels"] = int(zone.sum())
            result["uncovered_line_fraction"] = float(((fills < 200) & zone).sum() / max(1, zone.sum()))
            Image.fromarray(on_white(raster(root, width, "fills"))).save(out / "fills.png")
        report["sizes"][str(width)] = result
        sheet = Image.new("RGB", (actual.shape[1], actual.shape[0] * 2 + 48), "white")
        sheet.paste(Image.fromarray(reference), (0, 24))
        sheet.paste(Image.fromarray(actual), (0, actual.shape[0] + 48))
        draw = ImageDraw.Draw(sheet)
        draw.text((4, 4), "Clean scan", fill="black")
        draw.text((4, actual.shape[0] + 28), f"SVG at {width}px" + (" (top-left corner)" if width == 4000 else ""), fill="black")
        sheet.save(out / f"review-{width}.png")
    return report


def regressions(current, baseline, tolerance, complete=True):
    """Deteriorations against the baseline. `complete=False` for a filtered run, where the
    assets the filter left out are absent on purpose and must not read as missing."""
    if current.get("version") != baseline.get("version"):
        raise ValueError("Quality report versions differ; regenerate the comparison baseline.")
    failures = []
    for asset, old in baseline["assets"].items():
        if asset not in current["assets"]:
            if complete:
                failures.append(f"{asset}: missing asset")
            continue
        for width, previous in old["sizes"].items():
            new = current["assets"][asset]["sizes"].get(width)
            if new is None:
                failures.append(f"{asset}: missing size {width}")
                continue
            for key, direction in (("ink_iou", -1), ("palette_distance", 1), ("uncovered_line_fraction", 1)):
                if key in previous and direction * (new[key] - previous[key]) > tolerance:
                    failures.append(f"{asset} {width}px {key}: {previous[key]:.4f} -> {new[key]:.4f}")
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(prog="qa quality", description=__doc__)
    parser.add_argument("--assets", type=Path, default=ROOT / "assets")
    parser.add_argument("--out", type=Path, default=ROOT / "work/quality")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--style")
    parser.add_argument("--type", choices=["surah-headers", "ayah-markers", "page-frames"])
    parser.add_argument("--widths", nargs="+", type=int, default=[360, 1000, 4000])
    parser.add_argument("--tolerance", type=float, default=0.02)
    args = parser.parse_args(argv)
    if args.tolerance < 0 or any(width <= 0 for width in args.widths):
        parser.error("widths must be positive and tolerance must be nonnegative")
    report = {"version": 2, "assets": {}}
    for meta in sorted(args.assets.glob("*/*/meta.json")):
        if args.style and meta.parent.name != args.style:
            continue
        if args.type and meta.parent.parent.name != args.type:
            continue
        asset = meta.parent.relative_to(args.assets).as_posix()
        report["assets"][asset] = review_asset(meta.parent, args.out / asset, args.widths)
        print(asset, flush=True)
    if not report["assets"]:
        parser.error("no assets selected")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    failures = (regressions(report, json.loads(args.baseline.read_text()), args.tolerance,
                            complete=not (args.style or args.type)) if args.baseline else [])
    for failure in failures:
        print("REGRESSION:", failure)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
