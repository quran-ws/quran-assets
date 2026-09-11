#!/usr/bin/env python3
"""Scan lineage: render -> detect -> clean -> symmetry -> vectorize -> svgout.

Driven by `python -m qa build` (see `python -m qa build --help`); one job per
(mushaf, asset type) in qa/jobs/<type>.json.

Outputs land in assets/<type>/<style>/  (type = surah-headers | page-frames | ayah-markers,
style = `mushaf-<mushaf id>` -- the `<lineage>-<name>` rule, see qa.style_id):
  source.png   raw crop (title included)          clean.png   title removed (what gets traced)
  mono.svg     single-colour (currentColor)       color.svg   multi-colour layers
  meta.json    page, boxes, palette, slot, viewBox candidates/  every detected occurrence (raw)
"""
import json, time, hashlib, re
from pathlib import Path
import cv2, numpy as np
from qa import ROOT, SOURCES, TYPE_DIR, JOBS_DIR, git_rev, load_jobs, style_id
from . import render, detect, clean, slicer, vectorize, svgout, symmetry

def load():
    src = {s["id"]: s for s in json.load(open(ROOT / "sources" / "mushafs.json"))["sources"]}
    return load_jobs(), src

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

def pipeline_digest() -> str:
    """Identify the actual local pipeline, including changes not yet committed."""
    digest = hashlib.sha256()
    for path in sorted((ROOT / "qa").rglob("*.py")) + sorted(JOBS_DIR.glob("*.json")):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0" + path.read_bytes())
    return digest.hexdigest()

def provenance(job, s, box, pick, boxes):
    m = re.search(r"/items/([^/]+)/", s["url"])
    return {
        "mushaf": s["id"], "riwaya": s.get("riwaya"),
        "file": s["file"], "sha256": file_sha256(SOURCES / s["file"]),
        "url": s["url"], "archive_item": m.group(1) if m else None,
        "archive_url": f"https://archive.org/details/{m.group(1)}" if m else None,
        "pdf_page": job["page"], "crop_box_px": list(map(int, box)), "occurrence": pick, "occurrences_on_page": len(boxes),
        "pipeline": "quran-assets " + git_rev(), "pipeline_sha256": pipeline_digest(),
        "extracted": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

def run_job(job, cfg, src, to="vectorize", force=False, log=print):
    mushaf, asset = job["mushaf"], job["asset"]
    at = cfg["asset_types"][asset]
    out = ROOT / "assets" / TYPE_DIR.get(asset, asset) / style_id("scan", mushaf)
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
    source_crop = out / ("source.jpg" if (out / "source.jpg").exists() else "source.png")
    cv2.imwrite(str(source_crop), crop)
    log(f"  detected {len(boxes)} x {asset}; using #{pick} {crop.shape[1]}x{crop.shape[0]}px")
    if to == "detect": json.dump(meta, open(out / "meta.json", "w"), indent=2, ensure_ascii=False); return meta
    # 3 clean
    kw = {**at.get("clean", {}), **job.get("clean", {})}
    cleaned, slot, bg, slot_mask = clean.CLEANERS[at["cleaner"]](crop, **kw)
    cv2.imwrite(str(out / "clean.png"), cleaned)
    meta["slot_px"] = slot; meta["slot_fill"] = "#%02x%02x%02x" % bg if bg else None
    if to == "clean": json.dump(meta, open(out / "meta.json", "w"), indent=2, ensure_ascii=False); return meta
    # 4 vectorize + 5 standardize
    full_clean, full_slot_mask = cleaned.copy(), None if slot_mask is None else slot_mask.copy()
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
    if asset == "page-frame":
        meta["slices"] = write_slices(out, full_clean, full_slot_mask, meta, k, scale, vk, log)
    json.dump(meta, open(out / "meta.json", "w"), indent=2, ensure_ascii=False)
    log(f"  mono {len(mono)} paths, color {len(layers)} layers -> {out.relative_to(ROOT)}")
    return meta

MIN_RECONSTRUCTION_IOU = 0.70   # below this the pieces do not rebuild the frame; ship it whole


def write_slices(out, cleaned, slot_mask, meta, k, scale, vk, log):
    """9-slice pieces for a page frame, or None when the border does not tile.

    The pieces are checked before they are written: cut them out of the cleaned scan,
    reassemble the frame the way the `frame()` helper does, and compare the ink with the
    original. A border whose corner or repeat we read wrongly fails here and ships whole.
    """
    geometry = slicer.analyse(cleaned, meta["slot_px"], meta.get("symmetry", {}).get("folds"))
    if geometry is None:
        log("  slices: border is not periodic enough to slice; shipping the frame whole")
        return None
    boxes = {"corner": geometry["corner_px"], "edge-h": geometry["edge_h_px"], "edge-v": geometry["edge_v_px"]}
    pieces = {name: cleaned[b[1]:b[3], b[0]:b[2]] for name, b in boxes.items()}
    rebuilt = slicer.assemble(pieces, tuple(geometry["frame_px"]), geometry)
    ink = lambda image: cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) < 210
    a, b = ink(cleaned), ink(rebuilt)
    iou = float((a & b).sum() / max(1, (a | b).sum()))
    geometry["reconstruction_iou"] = round(iou, 4)
    if iou < MIN_RECONSTRUCTION_IOU:
        log(f"  slices: reconstruction IoU {iou:.3f} < {MIN_RECONSTRUCTION_IOU}; shipping the frame whole")
        return None
    traced = vectorize.trace_color(cleaned, k=k, scale=scale, slot_mask=slot_mask, crops=boxes,
                                  **{a_: b_ for a_, b_ in vk.items() if a_ in vectorize.COLOR_KEYS or a_ in vectorize.VTRACER_KEYS})
    directory = out / "slices"; directory.mkdir(exist_ok=True)
    height_px = geometry["frame_px"][1]
    written = {}
    for name, box in boxes.items():
        x0, y0, x1, y1 = box
        extra = {"data-slice": name, "data-frame-viewbox": meta["viewBox"]}
        if name != "corner":
            extra["data-repeat"] = _fmt_units((x1 - x0) if name == "edge-h" else (y1 - y0), height_px)
        svgout.write_svg(directory / f"{name}.svg", traced[name], x1 - x0, y1 - y0, scale,
                         meta["mushaf"], meta["asset"], "color", None, extra_attrs=extra,
                         provenance=meta["provenance"], norm_h=height_px)
        written[name] = f"slices/{name}.svg"
    log(f"  slices: corner {boxes['corner'][2]}x{boxes['corner'][3]}px, repeat {geometry['repeat_px']}, reconstruction IoU {iou:.3f}")
    return {"files": written, **geometry}


def _fmt_units(value, height_px):
    return round(value * 100.0 / height_px, 4)


def build(mushaf=None, asset=None, to="vectorize", force=False):
    cfg, src = load()
    jobs = [j for j in cfg["jobs"] if (not mushaf or j["mushaf"] == mushaf) and (not asset or j["asset"] == asset)]
    if not jobs:
        raise SystemExit("no jobs match that --mushaf/--asset selection")
    for j in jobs:
        print(f"[{j['mushaf']} / {j['asset']} p{j['page']}]")
        t = time.time(); run_job(j, cfg, src, to=to, force=force); print(f"  {time.time()-t:.1f}s")
    return jobs
