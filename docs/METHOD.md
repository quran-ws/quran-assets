# How the pipeline works

Two lineages produce assets that obey one contract.

* **scan** — traced from mushaf PDFs. `qa/scan/`, driven by `qa/jobs/<type>.json`. §1–§7 below.
* **font** — taken from the `U+06DD` glyph of Arabic fonts. `qa/font/`. §F1–§F5 below.

`python -m qa build` runs both; `--lineage scan|font` runs one. Either way `catalog.json` is
rewritten afterwards and `qa validate` holds both to `docs/CONVENTIONS.md`.

# The scan lineage

`python -m qa build --lineage scan` executes, per job in `qa/jobs/<type>.json`: **render →
detect → clean → symmetry → vectorize → svgout → (page frames only) slice**, then rewrites
`catalog.json`. Each stage is one module in `qa/scan/`; every stage's parameters can be
overridden per asset type (`defaults` in the job file) or per job.

## 1. render (`qa/scan/render.py`)
`pdfimages` pulls the page's embedded scan at native resolution (288 dpi for most of these
PDFs, 150 dpi JPEG for hafs-madinah-kabir). Vector pages would fall back to `pdftoppm`.
Cached in `work/pages/`.

## 2. detect (`qa/scan/detect.py`) — one function per asset type, returns boxes
* `surah_header` — after a 3 px closing, the frame's continuous outline makes the whole header
  one connected ink component; keep components that are wide (>30 % W), landscape (aspect >3),
  1.5–14 % of page height, and **colour-dense** (>12 % of the bbox is saturated; text lines are
  colour-poor). A top/bottom mirror pair is the page border → dropped. 2 % padding.
* `page_frame` — biggest closed coloured component (7 px closing) covering >55 % of the page.
* `frame_interior_rect` — text block = paper region reachable from the page centre without
  crossing ink; rows/cols where that region covers >30 % of the width/height. Fallback: colour
  profile from each edge, with mirror completion for a side that fails.
* `ayah_marker` — ink components inside the frame that **contain colour** (words are pure black),
  1–4 % of page height, aspect 0.55–1.5, convex hull ≥50 % of the bbox; ranked by mirror
  symmetry (most symmetric first). Every candidate is saved to `candidates/` (not committed);
  choose another with `"pick": n` in the job.
A job can bypass detection with `"box": [x0,y0,x1,y1]` (page pixels).

## 3. clean (`qa/scan/clean.py`) — makes the crop a reusable ornament
* `cartouche_text` (headers): flat light region at the centre = cartouche; its holes = title;
  the whole slot is flattened to the fill colour. Also strips page rules the padding caught.
* `frame_interior` (frames): blank the text block; then `strip_cartouches` removes running-head
  and page-number boxes that live in the band and **heals** the missing ornament by copying whole
  pattern periods from the neighbouring intact stretch (period from template matching).
* `marker` (markers): erase everything not connected to the central ornament, then blank the
  number like a cartouche.
Returns the cleaned crop, the slot box, the slot fill colour and the slot mask.

## 4. symmetry (`qa/scan/symmetry.py`)
Deskew (median slope of the top/bottom ink edges), find the vertical and horizontal mirror axes
(min L1 over ink pixels, blurred), align each mirrored copy with a small shift, and compare
residuals against a deliberately wrong offset: 4-fold if both mirrors match, 2-fold if only
left/right, **c2** (180° rotation) if the rotated copy matches much better than either mirror
(running vines), else none. The top-left quadrant (+6 px overlap) is what gets traced.
Averaging the copies was tried and rejected — scans carry slight rotation/scale so distant parts
never align to the pixel and the linework blurs.

## 5. vectorize (`qa/scan/vectorize.py`, `strokes.py`) — fills and lines are handled differently
Work at 3× (2× for frames, 6× for markers), cubic upscale + bilateral.
* **Linework** = `line_mask_auto`: k-means over all pixels; the darkest clusters whose pixels
  mostly vanish under a 2 px erosion are ink lines (black, navy, dark green all qualify; a navy
  *fill* survives erosion and stays a fill). Then `strokes.trace_strokes`: skeletonize → prune
  spurs → chains (8-neighbour adjacency with staircase-aware degrees) → thickness from the
  distance transform → Schneider cubic fitting with a sampled-distance acceptance test (no
  runaway handles; closed loops fitted as two halves) → grouped into 1–2 stroke widths.
* **Fills**: k-means (k=8) in Lab on the non-paper, non-line pixels, fitted on the smoothed
  image but assigned by the sharp one; centres within ΔE 11 merge; clusters under 3 % are
  absorbed into their nearest colour (gradients → flat, deliberately). Per layer: median filter,
  3 px opening, speckle removal, blur-and-threshold smoothing, 1 px growth, then grown further
  *only under the strokes* so no gap can show. Paper inside the frame becomes a white layer;
  the slot is cut out of every fill. Each mask is traced with vtracer in binary mode.
* **mono** = every non-paper pixel inside the frame minus the slot.

## 6. svgout (`qa/scan/svgout.py`)
Writes the standardized SVG (see CONVENTIONS): quadrant in `<defs>`, `<use>` mirrors, folds
vtracer's per-path translate into coordinates, `data-*` + `<metadata>` provenance.
`python -m qa optimize` runs svgo with `qa/common/svgo.config.mjs` (keeps ids, classes, data-*, metadata,
viewBox; merges paths; 2-decimal precision). Typical sizes after svgo: header 25–40 KB colour,
10 KB line, 12 KB mono; frame 100–200 KB (600 KB when unsymmetrised); marker 5–9 KB.

## 7. slice (`qa/scan/slicer.py`, page frames only)
An app draws a page border at whatever page size it renders, so a fixed-aspect frame is the
wrong shape to ship. The border is a corner motif plus a repeating unit, so: take the top band
and (rotated) the left band; propose repeat lengths from the autocorrelation of the column
profile and **confirm** each by correlating neighbouring windows — that rejects the half-period
an alternating two-motif band produces; walk out from the middle while the ornament still
repeats to find where the periodic run starts; snap the corner out to a whole repeat and to at
least the width of the band it meets. The three pieces (`slices/corner.svg`, `edge-h.svg`,
`edge-v.svg`) are traced from **one** quantization of the whole frame, so they share a palette
and their class names — traced separately, each piece would fit its own k-means and the seams
would not match. All three carry the frame's units (100 = the whole frame's height).

Before the pieces are written they are checked: cut them from the cleaned scan, reassemble the
frame the way `frame()` does, and compare the ink with the original. Below IoU 0.70 the frame
ships whole and says so (`hafs-madinah-kabir`, whose 150-dpi scan defeats the repeat detection).
Seven of the eight tile, at 0.74–0.96.

## Knobs that matter (all in `qa/jobs/<type>.json`)
`vectorize`: `k`, `scale`, `merge_de`, `min_frac`, `smooth`, `median`, `open_px`, `min_px`,
`light_min_px`, `line_mode` (`auto`|`threshold`), `line_dark`, `line_s_max`, `strokes` (bool),
`paper_thresh`; `detect`/`clean` dicts pass straight to the functions; `symmetry`:
`auto|4|2|c2|none`; `pick`, `box`.


## Review corrections (10 Sep 2026)

Palette fitting now excludes the text slot, paper, and linework. Paper is retained
as an explicit white layer rather than depending on a k-means cluster. Merged
cluster populations are counted once; edge pixels borrow from labelled fill pixels,
not excluded line pixels. Thin neutral antialiasing bands are absorbed into adjacent
fills. Fill growth is restricted to ink and its immediate rim, and cannot expand or
paint over the slot. This preserves white ornament channels.

Madinah headers use larger palettes to retain their small flower colours; Kabir
uses gentler smoothing for the low-resolution scan. Markers use per-job line
classification and reduced spur pruning to retain their short curved outlines.
Frame cleaning retains the connected border and removes detached scan marks.
`pipeline.optimize` updates path counts after SVGO. See QUALITY.md for the
raster comparisons, diagnostic limits, and regression command.


# The font lineage

47 markers from 26 Arabic font families. The first three stages are rare, need the network or
the source fonts, and re-mint ids; their output is committed, so the daily build is §F4 alone.

## F1. collect (`qa/font/collect.py`, `select.py`) — network, rarely run
Every Arabic family in Google Fonts (`primaryScript == "Arab"`) plus the `fonts.quran.ws`
catalogue; extract `U+06DD` from each; deduplicate the outlines by a scale-normalised path hash.
47 distinct outlines across 20 design families survive. Ids are minted here and are a public
contract: `NNN` is the design family, densely renumbered 1–20, and the suffix is a CSS weight
name. A **double suffix is a weight range, not two weights** — `010-regular-bold` is one outline
that Noto Naskh Arabic draws identically at 400/500/600/700, so it carries four `sources[]`.

## F2. layer (`qa/font/layer.py`)
A glyph is one flat set of contours; the product is one group per colour. `qa/font/data/
annotations.json` says which part each contour belongs to — made by hand, and not
reproducible. Where a contour of an earlier part lies inside one of a later part's, it is
redrawn in that part with `fill-rule="evenodd"` so the hole is punched again; containment is
tested by real point-in-path testing, not bounding boxes. Each path keeps `data-contours`, so
the original outline is recoverable and the stage is idempotent over its own output. A design
whose interior has no contour of its own gets a synthetic shape (`generatedFills`; only the 012
family, an `<ellipse>`).

## F3. number boxes (`qa/font/numbers*.py`) — needs the source fonts and uharfbuzz
Where the ayah number goes, which is rarely the middle of the bounding box: a design with a
flourish below the disc puts the number well above centre. Two derivations, then a hand pass.
`numbers_font.py` shapes `U+06DD` with the Arabic-Indic digits in the marker's *own* source font
with HarfBuzz and reads where that font puts them (24 markers); `numbers_geometry.py` rasterises
at 600², finds the enclosed counter overlapping the base fill, and takes its centre, inscribed
circle and largest fitting rectangle (23). `numbers.py` merges them and applies
`qa/font/data/number_placement.json` **last** — the 47 hand-placed centres, which move a centre
and never resize a box, so the derived width/height/`r` survive. Delete an entry and that marker
falls back to its derived centre.

## F4. svgout (`qa/font/svgout.py`) — every build
Normalisation to `docs/CONVENTIONS.md`, and the only stage `qa build --lineage font` runs:

* `<g data-part="fill-1" style="fill:var(--fill-1,#f4e9bc)">` → `<g class="c2" data-part="c2"
  fill="#f4e9bc">`. The `var()` form is rejected for the reason CONVENTIONS gives, which is not
  theoretical: cairosvg raises `invalid literal for int() with base 16: 'ar'` on these files.
  Parts keep their order, so `c1…cN` still runs light → dark, and which of them came from an
  `ink-*` part is kept in `meta.json` — that is what `mono.svg` is generated from.
* the glyph's own box, origin wherever the font left it, becomes `0 0 <w> 100`. One uniform
  scale for artwork and number box together, so the hand-placed centres stay correct. The
  source font's UPEM — 1000, 2048 or 3000 — is kept in `meta.json` for §F5.
* the number box becomes `data-slot` and `catalog.json → slots[]`, with no slot group. A font
  marker's interior is painted solid by its base fill rather than left as a counter, so a rect
  behind it is invisible and one in front would cover the artwork; measured before assuming.

## F5. font build (`qa/font/fontbuild.py`, called by `qa dist`)
`dist/fonts/AyahMarkers.{ttf,otf}` at UPEM 1000, PUA from `U+E000`. Glyphs come from each asset's
`source.svg`, not the normalised `color.svg`: a font wants UPEM units and one flat contour set,
not a height-100 viewBox and one group per colour. `data-contours` is used to take each contour
exactly once, or the duplicated hole contours would double their winding and fill the counters
in. Codepoints come from `selection.json`, so a subset build leaves gaps rather than shifting
every glyph off the codepoints the catalog advertises. No Reserved Font Name appears in the
font's names or glyph names — the OFL forbids one naming a modified version.

## Rebuilding from source

The PDFs are not committed. Fetch them and the 24 scan assets regenerate:

```bash
bash sources/fetch_mushafs.sh     # ~2 GB from archive.org
pip install -r requirements.txt   # + poppler and cairo on PATH

python -m qa build                # render → detect → clean → symmetry → vectorize → slice
python -m qa optimize             # svgo, then rewrite meta.json to match the delivered file
python -m qa validate             # catalog schema, SVG contract, licence traceability
python -m qa quality --baseline tests/quality-baseline.json --out work/quality
```

No manual crop boxes: headers, frames and markers are found on the page by their own
geometry, with per-job overrides in `qa/jobs/<type>.json`.

The font markers need none of that — `python -m qa build --lineage font` rebuilds all 47
offline from what is committed, in a second. The expensive half (scraping the families,
deduplicating outlines, deriving number boxes with HarfBuzz) ran once; its output and the
two things done by hand — the contour-to-layer assignment and the 47 number centres — live
in `qa/font/data/`. `python -m qa dist` builds the PUA font from the same files.
