# SVG conventions

All three asset types share one contract so an app can treat them uniformly.

## File set per asset (`assets/<type>/<style>/`)

| file | what |
|---|---|
| `color.svg` | full-colour, recolourable by group |
| `mono.svg` | one-colour silhouette, `currentColor` |
| `line.svg` | linework only, constant-width strokes, `currentColor` |
| `meta.json` | palette, slot, viewBox, stroke widths, symmetry, provenance, detection boxes |
| `source.png` / `source.jpg` | the raw crop from the scan (title / text / number included) |
| `clean.png` / `clean.jpg` | the cleaned crop that was traced |
| `slices/` | page frames only, when the border tiles: `corner.svg`, `edge-h.svg`, `edge-v.svg` |

## Root element

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 <w> 100"
     data-mushaf="qalon" data-asset="surah-header" data-variant="color"
     data-symmetry="4" data-slot="181.9 8.6 504.3 83.6"
     data-source-file="qalon.pdf" data-source-page="607" data-source-box="341 300 1348 416"
     data-source-url="…">
  <metadata>{ …JSON provenance: mushaf, riwaya, file, sha256, url, archive_item, archive_url,
              pdf_page, crop_box_px, occurrence, occurrences_on_page, pipeline, extracted… }</metadata>
```

* **viewBox** is normalised to height 100; width = 100 × aspect. No `width`/`height` attributes —
  size it with CSS.
* **data-slot** = `x y w h` in viewBox units: the empty area the app fills (surah name / page text /
  ayah number). `catalog.json` also gives `cx, cy`.
* **data-symmetry**: `4` (quadrant mirrored both ways), `2` (left/right), `c2` (180° rotation),
  `1` (traced whole). Mirrored files have `<defs><g id="q">…</g></defs>` + `<use>` elements.
* Paths use absolute `M/C/L/Z` (after svgo: relative + `h/v` too) — no transforms except the one
  `scale()` on the quadrant group and the `<use>` matrices.

## Groups (in stacking order)

```svg
<g class="slot" data-part="slot" fill="none">…</g>            transparent slot; .slot{fill:…} fills it
<g class="c1" data-part="c1" fill="#ffffff">…</g>             fills, light → dark: c1 … cN
<g class="cN" data-part="cN" fill="#…">…</g>
<g class="line" data-part="line" stroke="#353941" fill="none" constant-width linework, on top
   stroke-linecap="round" stroke-linejoin="round">
  <g stroke-width="4">…</g> <g stroke-width="8">…</g>         1–2 width classes (units = quadrant px; the
</g>                                                            scale() group brings them to viewBox units)
```

`mono.svg`: `<g class="slot">` + `<g class="ink" data-part="ink" fill="currentColor">`.
`line.svg`: `<g class="slot">` + `<g class="line" data-part="line" stroke="currentColor">`.

Every group carries **both** `class` and `data-part` with the same name — pick whichever your
tooling prefers (`.c2 {…}`, `[data-part="c2"] {…}`).

Recolour with CSS (`.c2{fill:#…} .line{stroke:#…} .slot{fill:#…}`) or by setting the group's
attribute; because the mirrors are `<use>` clones, one change recolours all four quadrants.

**The colour is a presentation attribute, never an inline `style`, and never `var()`.** A CSS
rule of any kind overrides a presentation attribute, so both a class rule and a custom property
of your own (`.c2{fill:var(--brand)}`) work; and a file whose colours were written as
`style="fill:var(--c2,#…)"` would render *wrong* in every rasterizer without CSS-variable
support — cairosvg and resvg among them, and most mobile SVG libraries. Theming is CSS's job;
the file must be right on its own.

## meta.json (per asset)

`mushaf, asset, page, riwaya, page_px, boxes` (all detections on the page), `pick`, `slot_px`,
`slot_fill`, `viewBox`, `slot`, `palette[{class, hex, paths, stroke?}]`, `mono_paths`,
`stroke_widths_px` (in *source* pixels), `symmetry{folds, deskew_deg, axes_px, residual, baseline}`,
`provenance{…}`, and for a sliced page frame `slices{files, corner_px, edge_h_px, edge_v_px,
repeat_px, repeats, band_px, frame_px, corner_mode, reconstruction_iou}`.
`catalog.json` is generated from these and validated against `tests/catalog.schema.json`
(`python -m qa validate`).

## Page-frame slices

A frame whose border tiles also ships three pieces in `slices/`, all in the **frame's** units
(100 = the whole frame's height, so they compose without rescaling):

* `corner.svg` — the corner motif; the other three corners are its mirrors (`corner_mode:
  "mirror"`) or its 180° rotations (`"rotate"`).
* `edge-h.svg`, `edge-v.svg` — one repeat unit each, carrying `data-repeat` (its length in
  frame units) and `data-frame-viewbox`.

`catalog.json → slices` gives `corner{w,h}`, `repeat{h,v}`, `corner_mode` and the
`reconstruction_iou` the pieces scored against the whole frame. Assemble with `frame()` from
`@quran-ws/assets` (or `qa.common.frame.assemble` in Python): corners at the four corners, the
edge units repeated between them, each stretched by the same rounding remainder so the run fits
exactly. Frames without a `slices` entry (`hafs-madinah-kabir`, whose border does not tile
cleanly) ship whole only.
