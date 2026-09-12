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


def test_slices_are_colour_only_and_the_docs_say_so():
    """A frame offers mono and line whole; its slices are colour and only colour.

    The README carried this until it was slimmed to a card, and then nothing did.
    It is the kind of fact that surfaces only as a failure: ``asset.slices`` is
    truthy for a mono request exactly as it is for a colour one, and hands back
    colour geometry, so a themed reader gets a colour border and no explanation.

    Two assertions, because either half alone can rot. The first pins the
    behaviour; the second pins the sentence that tells a consumer about it, so
    the documentation cannot be tidied away again while the behaviour stands.
    """
    allowed = {"corner.svg", "edge-h.svg", "edge-v.svg"}
    for asset in SLICED:
        directory = ROOT / "assets" / asset["id"] / "slices"
        present = {path.name for path in directory.iterdir() if path.is_file()}
        assert present == allowed, (
            f"{asset['id']}/slices holds {sorted(present)}. If a mono or line slice now "
            "ships, this repository can tile a themed border — update docs/USAGE.md, "
            "which currently tells consumers it cannot, and then this test."
        )

    usage = (ROOT / "docs" / "USAGE.md").read_text(encoding="utf-8")
    assert "Slices are colour-only" in usage, (
        "docs/USAGE.md no longer states that slices are colour-only. The behaviour "
        "asserted above has not changed, so the sentence has to stay."
    )
