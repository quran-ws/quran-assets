"""The font lineage: that the hand-made inputs are what actually shipped.

Two things in qa/font/data/ were made by hand and cannot be regenerated -- the contour
-> colour-part assignment in annotations.json and the 47 number centres in
number_placement.json. Everything else in the lineage is derived. These tests are the
guard on that: they check the hand work survived normalisation to the repo's SVG
contract, rather than re-testing the derivation that produced it.

Replaces the upstream tests/test_number_placement_editor.py, which asserted against the
source text of a build script and an exact `transform=` string.
"""
import io
import json
import re

import numpy as np
import pytest
from PIL import Image

from qa import ROOT
from qa.font import NUMBER_PLACEMENT, selection
from qa.font.svgout import read_outline

CATALOG = json.loads((ROOT / "catalog.json").read_text())
FONT = [a for a in CATALOG["assets"] if a["lineage"] == "font"]
PLACEMENT = json.loads(NUMBER_PLACEMENT.read_text())
ids = lambda a: a["style"]


def test_every_selected_marker_became_an_asset():
    assert {"font-" + m["id"] for m in selection()} == {a["style"] for a in FONT}


def test_every_marker_has_a_hand_placed_centre():
    assert {m["id"] for m in selection()} == set(PLACEMENT)


@pytest.mark.parametrize("asset", FONT, ids=ids)
def test_the_shipped_centre_is_the_hand_placed_one(asset):
    """The normalisation is one uniform scale, so a hand-placed centre maps onto the
    delivered slot exactly. This is the test that would catch a rescale that quietly
    moved the numbers -- the thing docs/PLAN.md §3 was worried about."""
    marker = next(m for m in selection() if "font-" + m["id"] == asset["style"])
    (min_x, min_y, _, height), _ = read_outline(ROOT / asset["source_crop"])
    scale = 100.0 / height
    hand = PLACEMENT[marker["id"]]
    slot = asset["slots"][0]
    assert slot["cx"] == pytest.approx((hand["cx"] - min_x) * scale, abs=1e-3)
    assert slot["cy"] == pytest.approx((hand["cy"] - min_y) * scale, abs=1e-3)


@pytest.mark.parametrize("asset", FONT, ids=ids)
def test_the_number_box_lies_inside_the_viewbox(asset):
    _, _, width, height = (float(v) for v in asset["viewBox"].split())
    slot = asset["slots"][0]
    assert 0 <= slot["x"] and slot["x"] + slot["w"] <= width + 1e-6
    assert 0 <= slot["y"] and slot["y"] + slot["h"] <= height + 1e-6
    assert slot["r"] > 0


@pytest.mark.parametrize("asset", FONT, ids=ids)
def test_the_number_box_does_not_land_on_the_marker_s_ink(asset):
    """Upstream's check_number_boxes gate, at 0.5% coverage -- and it runs here, which it
    could not upstream: that script read a `number.source` key that no longer exists, so
    it raised KeyError on the first box it had anything to report about."""
    import cairosvg
    size = 800
    png = cairosvg.svg2png(bytestring=(ROOT / asset["variants"]["mono"]).read_bytes(),
                           output_height=size, background_color="white")
    ink = np.array(Image.open(io.BytesIO(png)).convert("L")) < 200
    s, k = asset["slots"][0], size / 100.0
    box = ink[int(s["y"] * k):int((s["y"] + s["h"]) * k), int(s["x"] * k):int((s["x"] + s["w"]) * k)]
    assert box.size and box.mean() <= 0.005


@pytest.mark.parametrize("asset", FONT, ids=ids)
def test_colours_are_presentation_attributes(asset):
    """docs/CONVENTIONS.md, and not a style rule: cairosvg raises outright on
    `style="fill:var(--x,#hex)"` -- it reads `var` as a hex colour."""
    for path in asset["variants"].values():
        text = (ROOT / path).read_text()
        assert "var(" not in text, path
        assert not re.search(r'<g[^>]*\sstyle=', text), path


@pytest.mark.parametrize("asset", FONT, ids=ids)
def test_the_palette_is_c1_upwards_with_no_gaps(asset):
    assert [p["name"] for p in asset["palette"]] == [f"c{i}" for i in range(1, len(asset["palette"]) + 1)]


@pytest.mark.parametrize("asset", FONT, ids=ids)
def test_font_metrics_survive_for_the_font_build(asset):
    """The OTF/TTF build needs UPEM units back after the artwork is normalised."""
    font = asset["font"]
    # UPEM is the source font's, not a repo constant: 37 markers come from 1000-unit fonts,
    # 9 from 2048 (Scheherazade New, the Nastaliq and Uthmanic families) and Jomhuria from 3000.
    assert font["upem"] in (1000, 2048, 3000) and font["glyph"] == "U+06DD"
    assert font["advance"] > 0
    _, _, _, height = (float(v) for v in asset["viewBox"].split())
    (_, _, _, source_height), _ = read_outline(ROOT / asset["source_crop"])
    assert font["upem_scale"] == pytest.approx(height / source_height, rel=1e-6)


def test_codepoints_are_unique_and_contiguous_from_the_pua():
    points = sorted(int(a["font"]["codepoint"][2:], 16) for a in FONT)
    assert points == list(range(0xE000, 0xE000 + len(FONT)))
