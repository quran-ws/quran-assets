"""Step 5: standardized SVG writer.

Conventions (same for every asset type / mushaf so apps can treat them uniformly):
  * viewBox is normalised to height 100; width = 100 * aspect. No width/height attrs.
  * root carries data-style / data-lineage / data-asset / data-variant and, when known,
    data-slot (x y w h in viewBox units) = the empty cartouche where the app draws the
    surah name. data-style is the `<lineage>-<name>` id; data-mushaf is the bare mushaf id
    and is present on scan assets only, since a font-derived asset has no mushaf.
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

def part(cls, prop="fill", default=None, extra=""):
    """One recolourable group, addressable as `.cls` or `[data-part=cls]`.

    The colour is a presentation attribute, not an inline `style`/`var()`: a CSS rule of any
    kind overrides it, and rasterizers without CSS-variable support (cairosvg, resvg, most
    mobile SVG libraries) still render the traced colours. See docs/CONVENTIONS.md.
    """
    return f'<g class="{cls}" data-part="{cls}" {prop}="{default}"{extra}'

import json as _json

from qa import style_id

def write_svg(path, paths_or_layers, w_px, h_px, scale, mushaf, asset, variant, slot=None, extra_attrs=None, slot_paths=None, provenance=None, sym=None, norm_h=None):
    # `norm_h` is the height that maps to 100 units: the piece's own height normally, the
    # whole frame's for a 9-slice piece, so the pieces share the frame's coordinate system.
    s = 100.0 / (norm_h or h_px)
    vb_h = h_px * s
    vb_w = w_px * s
    attrs = {"xmlns": "http://www.w3.org/2000/svg", "viewBox": f"0 0 {_fmt(vb_w)} {_fmt(vb_h)}",
             "data-style": style_id("scan", mushaf), "data-lineage": "scan",
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
    # The quadrant's id is unique per file, not `q`: consumers inline several assets into one
    # document, and every `<use href="#{qid}">` on the page would otherwise resolve to the first one.
    qid = f'q-{attrs["data-style"]}-{asset}-{variant}'
    if sym:
        attrs_sym = f' data-symmetry="{sym["folds"]}"'
        out[0] = out[0][:-1] + attrs_sym + ">"
        out.append(f'<defs><g id="{qid}" {t}>')
    else:
        out.append(f"<g {t}>")
    if variant == "line":
        if slot_paths:
            out.append(part("slot", default="none") + ">")
            out += [f'<path d="{d}"/>' for d in slot_paths]
            out.append("</g>")
        out.append(part("line", "stroke", "currentColor", ' fill="none"') + ' stroke-linecap="round" stroke-linejoin="round">')
        for g in paths_or_layers:
            out.append(f'<g stroke-width="{g["width"]}">' + "".join(f'<path d="{d}"/>' for d in g["paths"]) + "</g>")
        out.append("</g>")
    elif variant == "mono":
        if slot_paths:
            out.append(part("slot", default="none") + ">")
            out += [f'<path d="{d}"/>' for d in slot_paths]
            out.append("</g>")
        out.append(part("ink", default="currentColor") + ">")
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
                out.append(part(cls, "stroke", l["hex"], ' fill="none"') + ' stroke-linecap="round" stroke-linejoin="round">')
                for g in l["groups"]:
                    out.append(f'<g stroke-width="{g["width"]}">' + "".join(f'<path d="{d}"/>' for d in g["paths"]) + "</g>")
                out.append("</g>")
                continue
            out.append(part(cls, default=l["hex"]) + ">")
            out += [f'<path d="{d}"/>' for d in l["paths"]]
            out.append("</g>")
    out.append("</g>")
    if sym:
        W2, H2 = _fmt(vb_w), _fmt(vb_h)
        out.append("</defs>")
        out.append('<use href="#{qid}"/>')
        f = sym["folds"]
        if f in (2, 4): out.append(f'<use href="#{qid}" transform="matrix(-1 0 0 1 {W2} 0)"/>')
        if f == 4:
            out.append(f'<use href="#{qid}" transform="matrix(1 0 0 -1 0 {H2})"/>')
            out.append(f'<use href="#{qid}" transform="matrix(-1 0 0 -1 {W2} {H2})"/>')
        if f == "c2": out.append(f'<use href="#{qid}" transform="matrix(-1 0 0 -1 {W2} {H2})"/>')
    out.append("</svg>")
    open(path, "w").write("\n".join(out))
    return {"viewBox": attrs["viewBox"], "slot": attrs.get("data-slot")}
