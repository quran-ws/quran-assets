"""catalog.json — one machine-readable entry per asset, generated from the meta.json files.

Consumers (apps, the demo, `qa dist`) read this; nothing here is maintained by hand.
Schema: tests/catalog.schema.json, validated by `python -m qa validate`.
"""
import json
import time
from pathlib import Path

from qa import ROOT, PKG, split_style

SLOT_ROLE = {"surah-headers": "surah-name", "page-frames": "text-area", "ayah-markers": "ayah-number"}
LICENSES = {k: v for k, v in json.loads((PKG / "licenses.json").read_text()).items() if not k.startswith("_")}


def aspect(view_box):
    """width / height of the viewBox, so an app can reserve the box before loading the SVG."""
    _, _, w, h = (float(v) for v in view_box.split())
    return round(w / h, 6)


def slices(geometry, directory):
    """9-slice pieces of a page frame, in the frame's own units (100 = frame height)."""
    unit = 100.0 / geometry["frame_px"][1]
    return {
        "files": {name: f"{directory}/{relative}" for name, relative in geometry["files"].items()},
        "corner": {"w": round(geometry["corner_px"][2] * unit, 4), "h": round(geometry["corner_px"][3] * unit, 4)},
        "repeat": {"h": round(geometry["repeat_px"]["h"] * unit, 4), "v": round(geometry["repeat_px"]["v"] * unit, 4)},
        "corner_mode": geometry["corner_mode"],
        "reconstruction_iou": geometry["reconstruction_iou"],
    }


def sources(m, lineage):
    """One entry per thing the asset was made from: a mushaf scan, or each source font.

    A font marker can have several -- one deduplicated outline shared by several weights of
    a family, or by several families -- and each carries its own licence, which is what lets
    `license_key` decide per asset rather than per lineage.
    """
    provenance = m.get("provenance") or {}
    if lineage == "font":
        return [{k: v for k, v in s.items() if v is not None} for s in provenance.get("sources", [])]
    return [{"kind": "mushaf-scan", **{k: v for k, v in provenance.items() if k != "pipeline"}}]


def write_catalog():
    """assets/catalog.json: every generated asset with its provenance, for apps and audits."""
    items = []
    for meta in sorted((ROOT / "assets").glob("*/*/meta.json")):
        m = json.load(open(meta)); d = "assets/" + str(meta.parent.relative_to(ROOT / "assets"))
        typ, style = meta.parent.parent.name, meta.parent.name
        lineage, _ = split_style(style)
        crop_name = "source.svg" if lineage == "font" else None
        crop = crop_name or ("source.jpg" if (meta.parent / "source.jpg").exists() else "source.png")
        sx = [float(v) for v in m["slot"].split()] if m.get("slot") else None
        items.append({"id": f"{typ}/{style}", "type": typ, "style": style, "lineage": lineage, "units": "normalized-100",
                      "riwaya": m.get("riwaya"), "viewBox": m.get("viewBox"), "aspect": aspect(m.get("viewBox")),
                      "variants": {k: f"{d}/{k}.svg" for k in ("color", "mono", "line") if (meta.parent / f"{k}.svg").exists()},
                      "source_crop": f"{d}/{crop}",
                      "palette": [{"name": p["class"], "hex": p["hex"], **({"stroke": True} if p.get("stroke") else {})} for p in m.get("palette", [])],
                      "stroke_widths_px": m.get("stroke_widths_px"),
                      "slots": [{"role": SLOT_ROLE[typ],
                                 "x": sx[0], "y": sx[1], "w": sx[2], "h": sx[3], "cx": sx[0] + sx[2] / 2, "cy": sx[1] + sx[3] / 2,
                                 # `r`: the largest circle that fits the marker's interior, for an app
                                 # that would rather place a round badge than a box. Font markers only.
                                 **({"r": float(m["slot_circle"]["r"])} if m.get("slot_circle") else {})}] if sx else [],
                      "symmetry": m.get("symmetry", {}).get("folds"),
                      **({"font": m["font"]} if m.get("font") else {}),
                      **({"slices": slices(m["slices"], d)} if m.get("slices") else {}),
                      "sources": sources(m, lineage),
                      "license": dict(LICENSES[m.get("license_key", lineage)]),
                      "pipeline_commit": (m.get("provenance") or {}).get("pipeline")})
    json.dump({"generated": time.strftime("%Y-%m-%d"), "schema": "quran-assets/catalog@1", "count": len(items), "assets": items},
              open(ROOT / "catalog.json", "w"), indent=2, ensure_ascii=False)
    return len(items)



if __name__ == "__main__":
    print(f"catalog: {write_catalog()} assets -> catalog.json")
