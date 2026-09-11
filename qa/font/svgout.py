"""Font lineage, final stage: normalise one extracted glyph to the repo's SVG contract.

The outlines arrive from the font world and disagree with docs/CONVENTIONS.md in three
places. This module is where that stops:

  * colour   `<g data-part="fill-1" style="fill:var(--fill-1,#f4e9bc)">` becomes
             `<g class="c2" data-part="c2" fill="#f4e9bc">`. An inline `style` is the one
             thing a consumer's `.c2{}` rule cannot override, and cairosvg raises on
             `var()` outright (it reads `var` as a hex colour). Parts keep their order,
             so c1..cN still runs light -> dark, and the fill/ink split survives in
             meta.json `mono_paths`, which is what mono.svg is generated from.
  * units    the glyph's own box (`-22.54 -304.54 1168.08 1242.08`, origin wherever the
             font put it) becomes `0 0 <w> 100` like every other asset. One uniform
             scale, so the hand-placed number box scales with the artwork and stays
             correct; the font metrics it came from are kept in meta.json for the
             OTF/TTF build, which needs UPEM units back.
  * slot     a font marker has no slot *group*: unlike a cartouche, its interior is
             painted solid by fill-base rather than left as a counter, so a rect behind
             the artwork is invisible and a rect in front would cover it. The number box
             ships as `data-slot` and `catalog.json -> slots[]` only. docs/CONVENTIONS.md
             says so, and qa.common.validate enforces the group for scan assets alone.
"""
import json
import re

VAR_FILL = re.compile(r'style="fill:var\(--[\w-]+,\s*(#[0-9a-fA-F]{6})\)"')
GROUP = re.compile(r'<g\s+data-part="([\w-]+)"([^>]*)>(.*?)</g>', re.S)
# Usually <path>, but the 012 family's base fill is a synthetic <ellipse>: annotations.json
# marks it `generatedFills`, for a design whose interior has no contour of its own to reuse.
SHAPE = re.compile(r'<(?:path|ellipse|circle|rect|polygon|polyline)\b[^>]*/>')


def _fmt(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def read_outline(path):
    """The source glyph: its viewBox and its parts, in stacking order."""
    text = path.read_text()
    view_box = [float(v) for v in re.search(r'viewBox="([^"]+)"', text).group(1).split()]
    parts = []
    for match in GROUP.finditer(text):
        name, attrs, body = match.groups()
        hex_match = VAR_FILL.search(attrs)
        parts.append({"part": name, "hex": (hex_match.group(1) if hex_match else "#000000").lower(),
                      "paths": SHAPE.findall(body)})
    return view_box, parts


def normalise(view_box, parts, number):
    """Everything in glyph units -> viewBox units, and `fill-*`/`ink-*` -> `c1..cN`.

    One scale for the artwork and the number box together, which is why the hand-placed
    centres survive: they are in the glyph's own space and move with it.
    """
    min_x, min_y, width, height = view_box
    scale = 100.0 / height
    palette, mono = [], []
    for index, part in enumerate(parts, start=1):
        cls = f"c{index}"
        palette.append({"class": cls, "hex": part["hex"], "paths": len(part["paths"]), "part": part["part"]})
        if part["part"].startswith("ink"):
            mono.append(cls)
    slot = [(number["cx"] - number["width"] / 2 - min_x) * scale,
            (number["cy"] - number["height"] / 2 - min_y) * scale,
            number["width"] * scale, number["height"] * scale]
    return {
        "scale": scale,
        "viewBox": f"0 0 {_fmt(width * scale)} 100",
        "slot": " ".join(_fmt(v) for v in slot),
        "slot_circle": {"cx": _fmt((number["cx"] - min_x) * scale), "cy": _fmt((number["cy"] - min_y) * scale),
                        "r": _fmt(number["r"] * scale)},
        "palette": palette,
        "mono": mono,
    }


def _svg(attrs, provenance, scale, min_x, min_y, groups):
    out = ["<svg " + " ".join(f'{k}="{v}"' for k, v in attrs.items()) + ">"]
    out.append("<metadata>" + json.dumps(provenance, ensure_ascii=False).replace("&", "&amp;").replace("<", "&lt;") + "</metadata>")
    out.append(f'<g transform="scale({_fmt(scale)}) translate({_fmt(-min_x)} {_fmt(-min_y)})">')
    out += groups
    out.append("</g></svg>")
    return "".join(out)


def write(directory, marker, view_box, parts, norm, provenance):
    """color.svg + mono.svg for one marker; returns the meta.json body."""
    min_x, min_y, _, _ = view_box
    style = "font-" + marker["id"]
    base = {"xmlns": "http://www.w3.org/2000/svg", "viewBox": norm["viewBox"],
            "data-style": style, "data-lineage": "font", "data-asset": "ayah-marker",
            "data-slot": norm["slot"], "data-symmetry": "1",
            "data-source-font": provenance["family"], "data-source-glyph": provenance["glyph"]}

    colour_groups = []
    for entry, part in zip(norm["palette"], parts):
        colour_groups.append(f'<g class="{entry["class"]}" data-part="{entry["class"]}" '
                             f'fill="{entry["hex"]}" fill-rule="evenodd">' + "".join(part["paths"]) + "</g>")
    attrs = dict(base, **{"data-variant": "color"})
    (directory / "color.svg").write_text(_svg(_ordered(attrs), provenance, norm["scale"], min_x, min_y, colour_groups))

    # mono: the ink parts alone, tinted by CSS `color` like every other mono variant.
    ink = [p for entry, p in zip(norm["palette"], parts) if entry["class"] in norm["mono"]]
    ink_paths = [path for part in ink for path in part["paths"]]
    mono_group = ['<g class="ink" data-part="ink" fill="currentColor" fill-rule="evenodd">' + "".join(ink_paths) + "</g>"]
    attrs = dict(base, **{"data-variant": "mono"})
    (directory / "mono.svg").write_text(_svg(_ordered(attrs), provenance, norm["scale"], min_x, min_y, mono_group))

    return {"asset": "ayah-marker", "style": style, "lineage": "font", "riwaya": None,
            "viewBox": norm["viewBox"], "slot": norm["slot"], "slot_circle": norm["slot_circle"],
            "palette": [{k: v for k, v in p.items() if k != "part"} for p in norm["palette"]],
            "source_parts": {p["class"]: p["part"] for p in norm["palette"]},
            "mono_paths": len(ink_paths), "mono_classes": norm["mono"],
            "stroke_widths_px": None, "symmetry": {"folds": 1},
            "font": {"upem": marker["upem"], "advance": marker["width"],
                     "upem_scale": round(norm["scale"], 8), "codepoint": marker["codepoint"],
                     "glyph": provenance["glyph"]},
            "provenance": provenance}


def _ordered(attrs):
    """svgo writes xmlns first and the rest alphabetically; match it so `qa optimize` is a no-op."""
    return {k: attrs[k] for k in ["xmlns"] + sorted(k for k in attrs if k != "xmlns")}
