"""9-sliced page frames must rebuild the frame they came from, at any page size."""
import io
import json

import numpy as np
import pytest
from PIL import Image

from qa import ROOT
from qa.common import frame

CATALOG = json.loads((ROOT / "catalog.json").read_text())
SLICED = [a for a in CATALOG["assets"] if a.get("slices")]


def _ink(png_bytes):
    image = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    rgb = np.asarray(image.convert("RGB")).astype(int)
    alpha = np.asarray(image)[..., 3]
    return (alpha > 64) & (rgb.max(axis=2) < 235)


def _render(svg, width):
    import cairosvg
    return cairosvg.svg2png(bytestring=svg.encode(), output_width=width)


def test_some_frames_are_sliced():
    assert SLICED, "no page frame produced slices; the slicer or the reconstruction gate regressed"


@pytest.mark.parametrize("asset", SLICED, ids=lambda a: a["id"])
def test_slices_rebuild_the_frame(asset):
    directory = ROOT / "assets" / asset["type"] / asset["style"]
    width, height = frame.native_size(directory)
    assembled = _render(frame.assemble(directory, width, height), 900)
    whole = _render((directory / "color.svg").read_text(), 900)
    a, b = _ink(assembled), _ink(whole)
    iou = (a & b).sum() / max(1, (a | b).sum())
    assert iou > 0.6, f"{asset['id']}: assembled frame matches the whole frame only at IoU {iou:.3f}"


@pytest.mark.parametrize("asset", SLICED, ids=lambda a: a["id"])
def test_slice_geometry_is_consistent(asset):
    slices = asset["slices"]
    _, _, width, height = (float(v) for v in asset["viewBox"].split())
    assert 0 < slices["corner"]["w"] < width / 2
    assert 0 < slices["corner"]["h"] < height / 2
    assert 0 < slices["repeat"]["h"] <= width - 2 * slices["corner"]["w"]
    assert 0 < slices["repeat"]["v"] <= height - 2 * slices["corner"]["h"]
    for relative in slices["files"].values():
        assert (ROOT / relative).exists()


@pytest.mark.parametrize("size", [(60, 100), (100, 60), (100, 100)])
def test_assembly_fills_the_requested_box(size):
    asset = SLICED[0]
    directory = ROOT / "assets" / asset["type"] / asset["style"]
    svg = frame.assemble(directory, *size)
    assert svg.startswith("<svg") and f'viewBox="0 0 {size[0]:.4f} {size[1]:.4f}"' in svg
    ink = _ink(_render(svg, 600))
    rows, columns = np.where(ink)
    # the border must reach all four edges of the box
    assert rows.min() < ink.shape[0] * 0.05 and rows.max() > ink.shape[0] * 0.95
    assert columns.min() < ink.shape[1] * 0.05 and columns.max() > ink.shape[1] * 0.95
