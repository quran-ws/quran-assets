"""`qa.font` — the font-derived lineage.

Markers are the U+06DD glyph of an Arabic font, extracted, deduplicated by outline,
layered into colour parts by hand, and given a hand-placed box for the ayah number.
The rare, network-and-HarfBuzz half of that (collect, layer, the number derivations)
is kept apart from the daily half: `qa build --lineage font` reads only what is
committed here and in assets/<...>/source.svg, and needs neither the source fonts
nor a network.

    data/selection.json          the 47 markers: id, codepoint, font metrics, sources, number box
    data/annotations.json        contour -> colour part, by hand
    data/number_placement.json   the hand-placed number centres

Stages, in order (see docs/METHOD.md):

    collect.py      scrape + extract + dedupe + mint ids    network, rare
    layer.py        apply annotations.json to the outlines  rare
    numbers_*.py    derive the number boxes                 needs the source fonts + uharfbuzz
    svgout.py       normalise to the repo's SVG contract    every build
    fontbuild.py    AyahMarkers.otf / .ttf                  called by `qa dist`
"""
import json

from qa import PKG

DATA = PKG / "font" / "data"
SELECTION = DATA / "selection.json"
ANNOTATIONS = DATA / "annotations.json"
NUMBER_PLACEMENT = DATA / "number_placement.json"


def selection():
    """The 47 marker records, in codepoint order."""
    return json.loads(SELECTION.read_text())["markers"]
