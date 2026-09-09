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
<g class="slot" fill="none">…</g>                       transparent slot shape; .slot{fill:…} to fill it
<g class="c1" fill="#ffffff">…</g>                      fills, light → dark: c1 … cN
<g class="cN" fill="#…">…</g>
<g class="line" fill="none" stroke="#353941"            constant-width linework, on top
   stroke-linecap="round" stroke-linejoin="round">
  <g stroke-width="4">…</g> <g stroke-width="8">…</g>   1–2 width classes (units = quadrant px; the
</g>                                                      scale() group brings them to viewBox units)
```

`mono.svg`: `<g class="slot" fill="none">` + `<g class="ink" fill="currentColor">`.
`line.svg`: `<g class="slot" fill="none">` + `<g class="line" stroke="currentColor">`.

Recolour with CSS (`.c2{fill:#…} .line{stroke:#…} .slot{fill:#…}`) or by setting the group's
attribute; because the mirrors are `<use>` clones, one change recolours all four quadrants.

## meta.json (per asset)

`mushaf, asset, page, riwaya, page_px, boxes` (all detections on the page), `pick`, `slot_px`,
`slot_fill`, `viewBox`, `slot`, `palette[{class, hex, paths, stroke?}]`, `mono_paths`,
`stroke_widths_px` (in *source* pixels), `symmetry{folds, deskew_deg, axes_px, residual, baseline}`,
`provenance{…}`. `catalog.json` is generated from these.
