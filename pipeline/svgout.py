"""Step 5: standardized SVG writer.

Conventions (same for every asset type / mushaf so apps can treat them uniformly):
  * viewBox is normalised to height 100; width = 100 * aspect. No width/height attrs.
  * root carries data-mushaf / data-asset / data-variant and, when known, data-slot
    (x y w h in viewBox units) = the empty cartouche where the app draws the surah name.
  * mono.svg  : <g class="slot" fill="none"> (the name slot, transparent) then
                <g class="ink" fill="currentColor">; tint with CSS `color`.
  * color.svg : <g class="slot" fill="none"> then one <g class="cN" fill="#hex"> per
                palette colour, bottom layer first; linework last as <g class="line"
                stroke="#hex"> of constant-width strokes (fills extend under them).
  * line.svg  : the strokes alone, stroke="currentColor" (line-art / outline variant).
                Recolour by CSS `.cN{fill:...}` / `.slot{fill:...}`.
Trace coordinates come from vtracer at `scale`x the crop; we fold that into one transform.
"""
def _fmt(v): return f"{v:.4f}".rstrip("0").rstrip(".")

import json as _json

def write_svg(path, paths_or_layers, w_px, h_px, scale, mushaf, asset, variant, slot=None, extra_attrs=None, slot_paths=None, provenance=None, sym=None):
    vb_h = 100.0
    s = vb_h / h_px
    vb_w = w_px * s
    attrs = {"xmlns": "http://www.w3.org/2000/svg", "viewBox": f"0 0 {_fmt(vb_w)} {_fmt(vb_h)}",
             "data-mushaf": mushaf, "data-asset": asset, "data-variant": variant}
    if slot:
        x0, y0, x1, y1 = slot
        attrs["data-slot"] = " ".join(_fmt(v * s) for v in (x0, y0, x1 - x0, y1 - y0))
    if provenance:   # where this ornament came from, readable without opening meta.json
        attrs["data-source-file"] = provenance["file"]; attrs["data-source-page"] = str(provenance["pdf_page"])
        attrs["data-source-url"] = provenance["url"]; attrs["data-source-box"] = " ".join(map(str, provenance["crop_box_px"]))
    if extra_attrs: attrs.update(extra_attrs)
    out = ["<svg " + " ".join(f'{k}="{v}"' for k, v in attrs.items()) + ">"]
    if provenance:
        out.append("<metadata>" + _json.dumps(provenance, ensure_ascii=False).replace("&", "&amp;").replace("<", "&lt;") + "</metadata>")
    t = f'transform="scale({_fmt(s / scale)})"'
    if sym:
        attrs_sym = f' data-symmetry="{sym["folds"]}"'
        out[0] = out[0][:-1] + attrs_sym + ">"
        out.append(f'<defs><g id="q" {t}>')
    else:
        out.append(f"<g {t}>")
    if variant == "line":
        if slot_paths:
            out.append('<g class="slot" fill="none">')
            out += [f'<path d="{d}"/>' for d in slot_paths]
            out.append("</g>")
        out.append('<g class="line" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">')
        for g in paths_or_layers:
            out.append(f'<g stroke-width="{g["width"]}">' + "".join(f'<path d="{d}"/>' for d in g["paths"]) + "</g>")
        out.append("</g>")
    elif variant == "mono":
        if slot_paths:
            out.append('<g class="slot" fill="none">')
            out += [f'<path d="{d}"/>' for d in slot_paths]
            out.append("</g>")
        out.append('<g class="ink" fill="currentColor">')
        out += [f'<path d="{d}"/>' for d in paths_or_layers]
        out.append("</g>")
    else:
        n = 0
        for l in paths_or_layers:
            if l.get("cls"): cls = l["cls"]
            else: n += 1; cls = f"c{n}"
            l["cls"] = cls
            if l.get("stroke"):
                cls = "line"; l["cls"] = cls
                out.append(f'<g class="{cls}" fill="none" stroke="{l["hex"]}" stroke-linecap="round" stroke-linejoin="round">')
                for g in l["groups"]:
                    out.append(f'<g stroke-width="{g["width"]}">' + "".join(f'<path d="{d}"/>' for d in g["paths"]) + "</g>")
                out.append("</g>")
                continue
            out.append(f'<g class="{cls}" fill="{l["hex"]}">')
            out += [f'<path d="{d}"/>' for d in l["paths"]]
            out.append("</g>")
    out.append("</g>")
    if sym:
        W2, H2 = _fmt(vb_w), _fmt(vb_h)
        out.append("</defs>")
        out.append('<use href="#q"/>')
        f = sym["folds"]
        if f in (2, 4): out.append(f'<use href="#q" transform="matrix(-1 0 0 1 {W2} 0)"/>')
        if f == 4:
            out.append(f'<use href="#q" transform="matrix(1 0 0 -1 0 {H2})"/>')
            out.append(f'<use href="#q" transform="matrix(-1 0 0 -1 {W2} {H2})"/>')
        if f == "c2": out.append(f'<use href="#q" transform="matrix(-1 0 0 -1 {W2} {H2})"/>')
    out.append("</svg>")
    open(path, "w").write("\n".join(out))
    return {"viewBox": attrs["viewBox"], "slot": attrs.get("data-slot")}
