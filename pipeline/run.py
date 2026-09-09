#!/usr/bin/env python3
"""Run the ornament pipeline.

  python3 -m pipeline.run                      # every job in assets.json
  python3 -m pipeline.run --mushaf qalon       # one mushaf
  python3 -m pipeline.run --asset ayah-marker  # one asset type
  python3 -m pipeline.run --to detect          # stop after a step (render|detect|clean|vectorize)
  python3 -m pipeline.run --force              # ignore cached page renders

Outputs land in assets/<type>/<style>/  (type = surah-headers | page-frames | ayah-markers, style = mushaf id):
  source.png   raw crop (title included)          clean.png   title removed (what gets traced)
  mono.svg     single-colour (currentColor)       color.svg   multi-colour layers
  meta.json    page, boxes, palette, slot, viewBox candidates/  every detected occurrence (raw)
"""
import argparse, json, sys, time, hashlib, subprocess, re, os
from pathlib import Path
import cv2, numpy as np
from . import render, detect, clean, vectorize, svgout, symmetry

ROOT = Path(__file__).resolve().parent.parent
SOURCES = Path(os.environ.get("QA_SOURCES_DIR", ROOT / "sources"))   # where the mushaf PDFs live (not committed)

TYPE_DIR = {"surah-header": "surah-headers", "page-frame": "page-frames", "ayah-marker": "ayah-markers"}

def load():
    cfg = json.load(open(ROOT / "jobs.json"))
    src = {s["id"]: s for s in json.load(open(ROOT / "sources" / "mushafs.json"))["sources"]}
    return cfg, src

def file_sha256(path: Path) -> str:
    """sha256 of a source PDF, cached next to the page renders (PDFs are ~250 MB)."""
    cache = ROOT / "work" / "pages" / (path.name + ".sha256")
    if cache.exists() and cache.stat().st_mtime >= path.stat().st_mtime:
        return cache.read_text().strip()
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""): h.update(chunk)
    cache.parent.mkdir(parents=True, exist_ok=True); cache.write_text(h.hexdigest())
    return h.hexdigest()

def git_rev() -> str:
    try: return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception: return "uncommitted"

def provenance(job, s, box, pick, boxes):
    m = re.search(r"/items/([^/]+)/", s["url"])
    return {
        "mushaf": s["id"], "riwaya": s.get("riwaya"),
        "file": s["file"], "sha256": file_sha256(SOURCES / s["file"]),
        "url": s["url"], "archive_item": m.group(1) if m else None,
        "archive_url": f"https://archive.org/details/{m.group(1)}" if m else None,
        "pdf_page": job["page"], "crop_box_px": list(map(int, box)), "occurrence": pick, "occurrences_on_page": len(boxes),
        "pipeline": "quran-assets " + git_rev(), "extracted": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

def write_catalog():
    """assets/catalog.json: every generated asset with its provenance, for apps and audits."""
    items = []
    for meta in sorted((ROOT / "assets").glob("*/*/meta.json")):
        m = json.load(open(meta)); d = "assets/" + str(meta.parent.relative_to(ROOT / "assets"))
        typ, style = meta.parent.parent.name, meta.parent.name
        crop = "source.jpg" if (meta.parent / "source.jpg").exists() else "source.png"
        sx = [float(v) for v in m["slot"].split()] if m.get("slot") else None
        items.append({"id": f"{typ}/{style}", "type": typ, "style": style, "lineage": "scan", "units": "normalized-100",
                      "riwaya": m.get("riwaya"), "viewBox": m.get("viewBox"),
                      "variants": {k: f"{d}/{k}.svg" for k in ("color", "mono", "line") if (meta.parent / f"{k}.svg").exists()},
                      "source_crop": f"{d}/{crop}",
                      "palette": [{"name": p["class"], "hex": p["hex"], **({"stroke": True} if p.get("stroke") else {})} for p in m.get("palette", [])],
                      "stroke_widths_px": m.get("stroke_widths_px"),
                      "slots": [{"role": {"surah-headers": "surah-name", "page-frames": "text-area", "ayah-markers": "ayah-number"}[typ],
                                 "x": sx[0], "y": sx[1], "w": sx[2], "h": sx[3], "cx": sx[0] + sx[2] / 2, "cy": sx[1] + sx[3] / 2}] if sx else [],
                      "symmetry": m.get("symmetry", {}).get("folds"),
                      "sources": [{"kind": "mushaf-scan", **{k: v for k, v in (m.get("provenance") or {}).items() if k != "pipeline"}}],
                      "license": {"id": "TBD", "status": "pending"},
                      "pipeline_commit": (m.get("provenance") or {}).get("pipeline")})
    json.dump({"generated": time.strftime("%Y-%m-%d"), "schema": "quran-assets/catalog@1", "count": len(items), "assets": items},
              open(ROOT / "catalog.json", "w"), indent=2, ensure_ascii=False)
    return len(items)

def run_job(job, cfg, src, to="vectorize", force=False, log=print):
    mushaf, asset = job["mushaf"], job["asset"]
    at = cfg["asset_types"][asset]
    out = ROOT / "assets" / TYPE_DIR.get(asset, asset) / mushaf
    out.mkdir(parents=True, exist_ok=True)
    meta = {"mushaf": mushaf, "asset": asset, "page": job["page"], "source": src[mushaf]["file"],
            "riwaya": src[mushaf].get("riwaya"), "generated": time.strftime("%Y-%m-%d %H:%M")}
    # 1 render
    page_png = render.page_image(SOURCES / src[mushaf]["file"], job["page"], ROOT / "work" / "pages", force=force)
    bgr = cv2.imread(str(page_png)); meta["page_px"] = [bgr.shape[1], bgr.shape[0]]
    if to == "render": return meta
    # 2 detect
    if "box" in job:
        boxes = [tuple(job["box"])]
    else:
        kw = {**at.get("detect", {}), **job.get("detect", {})}
        boxes = detect.DETECTORS[at["detector"]](bgr, **kw)
    if not boxes:
        log(f"  !! no {asset} found on page {job['page']} of {mushaf}; add a manual 'box' to assets.json"); return meta
    meta["boxes"] = [list(map(int, b)) for b in boxes]
    cand = out / "candidates"; cand.mkdir(exist_ok=True)
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        cv2.imwrite(str(cand / f"{i}.png"), bgr[y0:y1, x0:x1])
    pick = job.get("pick", 0)
    x0, y0, x1, y1 = boxes[pick]; meta["pick"] = pick
    meta["provenance"] = provenance(job, src[mushaf], boxes[pick], pick, boxes)
    crop = bgr[y0:y1, x0:x1]
    cv2.imwrite(str(out / "source.png"), crop)
    log(f"  detected {len(boxes)} x {asset}; using #{pick} {crop.shape[1]}x{crop.shape[0]}px")
    if to == "detect": json.dump(meta, open(out / "meta.json", "w"), indent=2, ensure_ascii=False); return meta
    # 3 clean
    kw = {**at.get("clean", {}), **job.get("clean", {})}
    cleaned, slot, bg, slot_mask = clean.CLEANERS[at["cleaner"]](crop, **kw)
    cv2.imwrite(str(out / "clean.png"), cleaned)
    meta["slot_px"] = slot; meta["slot_fill"] = "#%02x%02x%02x" % bg if bg else None
    if to == "clean": json.dump(meta, open(out / "meta.json", "w"), indent=2, ensure_ascii=False); return meta
    # 4 vectorize + 5 standardize
    vk = {**at.get("vectorize", {}), **job.get("vectorize", {})}
    scale = vk.pop("scale", 2); k = vk.pop("k", 6)
    h, w = cleaned.shape[:2]
    sym_mode = job.get("symmetry", at.get("symmetry", "auto"))       # auto | 4 | 2 | none
    sym = None
    if sym_mode != "none":
        up = vectorize._upscale(cleaned, scale, smooth=False)
        sm_up = cv2.resize(slot_mask.astype(np.uint8), (up.shape[1], up.shape[0]), interpolation=cv2.INTER_NEAREST) > 0 if slot_mask is not None else None
        sym = symmetry.symmetrize(up, sm_up, force=(None if sym_mode == "auto" else (sym_mode if sym_mode == "c2" else int(sym_mode))))
        cleaned, slot_mask = sym["quadrant"], sym["slot"]
        w, h = sym["full"][0] / scale, sym["full"][1] / scale          # full frame size in 1x px
        meta["symmetry"] = {"folds": sym["folds"], "deskew_deg": sym["deskew_deg"], "axes_px": [sym["axes"][0] / scale, sym["axes"][1] / scale],
                            "residual": sym["residual"], "baseline": sym["baseline"]}
        log(f"  symmetry: {sym['folds']}-fold, deskew {sym['deskew_deg']}°, residual {sym['residual']} (baseline {sym['baseline']})")
    pre = sym is not None
    mono_keys = {"smooth", "min_px", "paper_thresh", "line_dark", "line_s_max", "line_mode"}
    mono, slot_paths = vectorize.trace_mono(cleaned, scale=scale, slot_mask=slot_mask, prescaled=pre, **{a: b for a, b in vk.items() if a in mono_keys or a in vectorize.VTRACER_KEYS})
    vk = {a: b for a, b in vk.items() if a in vectorize.COLOR_KEYS or a in vectorize.VTRACER_KEYS}
    m1 = svgout.write_svg(out / "mono.svg", mono, w, h, scale, mushaf, asset, "mono", slot, slot_paths=slot_paths, provenance=meta["provenance"], sym=sym)
    layers = vectorize.trace_color(cleaned, k=k, scale=scale, slot_mask=slot_mask, prescaled=pre, **vk)
    m2 = svgout.write_svg(out / "color.svg", layers, w, h, scale, mushaf, asset, "color", slot, provenance=meta["provenance"], sym=sym)
    if layers and layers[-1].get("stroke"):
        svgout.write_svg(out / "line.svg", layers[-1]["groups"], w, h, scale, mushaf, asset, "line", slot, slot_paths=slot_paths, provenance=meta["provenance"], sym=sym)
        meta["stroke_widths_px"] = [round(g["width"] / scale, 2) for g in layers[-1]["groups"]]
    meta["viewBox"] = m1["viewBox"]; meta["slot"] = m1["slot"]
    meta["palette"] = [{"class": l["cls"], "hex": l["hex"], "paths": len(l["paths"]), **({"stroke": True} if l.get("stroke") else {})} for l in layers]
    meta["mono_paths"] = len(mono)
    json.dump(meta, open(out / "meta.json", "w"), indent=2, ensure_ascii=False)
    log(f"  mono {len(mono)} paths, color {len(layers)} layers -> {out.relative_to(ROOT)}")
    return meta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mushaf"); ap.add_argument("--asset")
    ap.add_argument("--to", default="vectorize", choices=["render", "detect", "clean", "vectorize"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--catalog-only", action="store_true", help="just rebuild catalog.json from existing meta.json files")
    a = ap.parse_args()
    if a.catalog_only:
        print(f"catalog: {write_catalog()} assets -> catalog.json"); return
    cfg, src = load()
    jobs = [j for j in cfg["jobs"] if (not a.mushaf or j["mushaf"] == a.mushaf) and (not a.asset or j["asset"] == a.asset)]
    for j in jobs:
        print(f"[{j['mushaf']} / {j['asset']} p{j['page']}]")
        t = time.time(); run_job(j, cfg, src, to=a.to, force=a.force); print(f"  {time.time()-t:.1f}s")
    print(f"catalog: {write_catalog()} assets -> catalog.json")

if __name__ == "__main__":
    main()
