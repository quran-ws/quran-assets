"""`qa build --lineage font` — the 47 font-derived markers, from what is committed.

Reads qa/font/data/selection.json and each asset's own source.svg (the extracted glyph,
committed as the provenance crop, the way a scan asset commits source.png), and writes
color.svg, mono.svg and meta.json beside it. No network, no source fonts, no HarfBuzz:
everything expensive happened once, in the stages named in qa/font/__init__.py, and its
result is committed.
"""
import json
import time

from qa import ROOT, git_rev, style_id
from qa.font import selection
from qa.font import svgout

OUT = ROOT / "assets" / "ayah-markers"


def provenance(marker):
    """Where this outline came from, per source font, readable without opening meta.json."""
    sources = [{"kind": "font", "source": s["source"], "family": s["family"], "variant": s["variant"],
                "source_url": s.get("source_url"), "upem": s["upem"], "advance": s["width"],
                "license": s["license"]} for s in marker["sources"]]
    families = sorted({s["family"] for s in marker["sources"]})
    return {"family": ", ".join(families), "glyph": "U+06DD", "codepoint": marker["codepoint"],
            "sources": sources, "extracted": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "pipeline": "quran-assets " + git_rev()}


def license_key(marker):
    """OFL only if every source family is OFL: one unverified source taints the outline."""
    ids = {s["license"]["id"] for s in marker["sources"]}
    return "font-ofl" if ids == {"OFL-1.1"} else "font-unverified"


def build_one(marker):
    directory = OUT / style_id("font", marker["id"])
    source = directory / "source.svg"
    if not source.exists():
        raise SystemExit(f"{marker['id']}: missing {source.relative_to(ROOT)}")
    view_box, parts = svgout.read_outline(source)
    if not parts:
        raise SystemExit(f"{marker['id']}: source.svg has no data-part groups; run qa.font.layer first")
    norm = svgout.normalise(view_box, parts, marker["number"])
    meta = svgout.write(directory, marker, view_box, parts, norm, provenance(marker))
    meta["license_key"] = license_key(marker)
    (directory / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n")
    return meta


def build(style=None):
    markers = [m for m in selection() if not style or style_id("font", m["id"]) == style]
    if not markers:
        raise SystemExit(f"no font marker matches --style {style}")
    for marker in markers:
        meta = build_one(marker)
        print(f"[font-{marker['id']}] {meta['viewBox']} · {len(meta['palette'])} groups · slot {meta['slot']}")
    return len(markers)


if __name__ == "__main__":
    print(f"{build()} font markers")
