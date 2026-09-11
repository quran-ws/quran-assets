#!/usr/bin/env python3
"""Build the Ayah Markers PUA font: dist/fonts/AyahMarkers.{ttf,otf} + font-map.json.

Called by `python -m qa dist`. Glyphs are taken from each asset's source.svg -- the
extracted outline in the source font's own units -- not from the normalised color.svg,
because a font wants UPEM units and one flat contour set, not a height-100 viewBox and
one group per colour.

Codepoints come from selection.json rather than from position in this list, so building
a subset (`qa dist --exclude-unconfirmed`) leaves the remaining markers on the
codepoints the catalog already advertises, with gaps, instead of silently shifting them.

Reserved Font Names (Alkalami, SIL, Scheherazade, Plex, Source) must not name a modified
version, so nothing here carries a source family name: the font is "Ayah Markers" and its
glyphs are marker001..markerNNN.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from fontTools.fontBuilder import FontBuilder
from fontTools.svgLib.path import parse_path
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.t2CharStringPen import T2CharStringPen

ROOT = Path(__file__).resolve().parents[2]  # repo root
UPEM = 1000

def glyph_path(path: Path) -> str:
    """The glyph's contours, each once, in their original order.

    The markers are layered for CSS, so a contour that punches a hole in a
    part it does not belong to is drawn in both parts. Feeding those duplicates
    to a pen would double their winding and fill the counters in, so the
    `data-contours` indices the layering records are used to take each contour
    exactly once, back in the order the source font drew them.
    """
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    contours: dict[int, str] = {}
    order = 0
    for element in root.iter("{http://www.w3.org/2000/svg}path"):
        subpaths = re.findall(r"[Mm][^Mm]*", element.attrib.get("d", ""))
        indices = element.attrib.get("data-contours")
        if indices:
            keys = [int(value) for value in indices.split()]
        else:
            keys = list(range(order, order + len(subpaths))); order += len(subpaths)
        for key, subpath in zip(keys, subpaths):
            contours.setdefault(key, subpath)
    return " ".join(contours[key] for key in sorted(contours))


def outline(path: Path, source_upem: int):
    pen = TTGlyphPen(None); scale = UPEM / source_upem
    target = TransformPen(Cu2QuPen(pen, max_err=1.0), (scale, 0, 0, scale, 0, 0))
    parse_path(glyph_path(path), target)
    return pen.glyph()

def cff_outline(path: Path, source_upem: int, width: int):
    """Keep SVG cubic curves when producing the CFF-flavoured OTF."""
    pen = T2CharStringPen(width, None)
    scale = UPEM / source_upem
    target = TransformPen(pen, (scale, 0, 0, scale, 0, 0))
    parse_path(glyph_path(path), target)
    return pen.getCharString()

def main(out_dir: Path | None = None, markers=None) -> dict:
    if markers is None:
        markers = json.loads((ROOT / "qa" / "font" / "data" / "selection.json").read_text(encoding="utf-8"))["markers"]
    out_dir = Path(out_dir) if out_dir else ROOT / "dist" / "fonts"
    points = [int(marker["codepoint"][2:], 16) for marker in markers]
    names = [".notdef"] + [f"marker{index + 1:03d}" for index in range(len(markers))]
    glyphs = {".notdef": TTGlyphPen(None).glyph()}; metrics = {".notdef": (UPEM, 0)}; cmap = {}
    for index, marker in enumerate(markers):
        name = names[index + 1]; glyphs[name] = outline(ROOT / marker["file"], marker["upem"])
        metrics[name] = (round(marker["width"] * UPEM / marker["upem"]), 0); cmap[points[index]] = name
    font = FontBuilder(UPEM, isTTF=True); font.setupGlyphOrder(names); font.setupCharacterMap(cmap); font.setupGlyf(glyphs); font.setupHorizontalMetrics(metrics); font.setupHorizontalHeader(ascent=800, descent=-200)
    font.setupNameTable({"familyName":"Ayah Markers", "styleName":"Regular", "fullName":"Ayah Markers Regular", "uniqueFontIdentifier":"Ayah Markers Regular", "psName":"AyahMarkers-Regular", "version":"Version 1.0"})
    font.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=1000, usWinDescent=200); font.setupPost(); font.setupMaxp()
    destination = out_dir / "AyahMarkers.ttf"; destination.parent.mkdir(parents=True, exist_ok=True); font.save(destination)
    font_map = {
        "fonts": ["AyahMarkers.ttf", "AyahMarkers.otf"],
        "unicode_range": f"U+{min(points):04X}–U+{max(points):04X}",
        "glyphs": [
            # `style` is the catalog id, so font-map.json joins onto catalog.json without a lookup table.
            {"style": "font-" + marker["id"], "marker": marker["id"],
             "codepoint": marker["codepoint"], "character": chr(points[index])}
            for index, marker in enumerate(markers)
        ],
    }
    (out_dir / "font-map.json").write_text(json.dumps(font_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    cff_glyphs = {".notdef": T2CharStringPen(UPEM, None).getCharString()}
    for index, marker in enumerate(markers):
        width = round(marker["width"] * UPEM / marker["upem"])
        cff_glyphs[names[index + 1]] = cff_outline(ROOT / marker["file"], marker["upem"], width)
    otf = FontBuilder(UPEM, isTTF=False); otf.setupGlyphOrder(names); otf.setupCharacterMap(cmap)
    otf.setupHorizontalMetrics(metrics); otf.setupHorizontalHeader(ascent=800, descent=-200)
    otf.setupNameTable({"familyName":"Ayah Markers", "styleName":"Regular", "fullName":"Ayah Markers Regular", "uniqueFontIdentifier":"Ayah Markers Regular", "psName":"AyahMarkers-Regular", "version":"Version 1.0"})
    otf.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=1000, usWinDescent=200); otf.setupPost(); otf.setupMaxp()
    otf.setupCFF("AyahMarkers-Regular", {"FullName":"Ayah Markers Regular", "FamilyName":"Ayah Markers", "Weight":"Regular", "version":"1.0"}, cff_glyphs, {})
    otf_destination = out_dir / "AyahMarkers.otf"; otf.save(otf_destination)
    print(f"fonts: {len(markers)} glyphs, U+{min(points):04X}–U+{max(points):04X} -> {out_dir.relative_to(ROOT)}/")
    return font_map

if __name__ == "__main__": main()
