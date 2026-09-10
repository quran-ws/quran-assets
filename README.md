# quran-assets

Decorative assets for Quran apps — **surah-header frames, page frames and ayah markers** —
vectorized from scanned mushaf PDFs into clean, recolourable, standardized SVGs.

Private repo of the quran.ws non-profit. Status: **alpha — 24 assets from 8 mushafs, a
regression-gated pipeline, a 9-slice page-frame build and an npm package that is deliberately
`private` until the licensing question in [`docs/PLAN.md`](docs/PLAN.md) §6 is settled.**

```
assets/<type>/<style>/        the product: color.svg  mono.svg  line.svg  meta.json  source.*  clean.*
   type  = surah-headers | page-frames | ayah-markers
   style = mushaf id: qalon hafs-adi hafs-madinah-kabir sousi warsh hafs-madinah-mumtaza douri shubah
   page frames also carry slices/{corner,edge-h,edge-v}.svg when their border tiles
catalog.json                  one machine-readable index of every asset (+ provenance, palette, slots, slices)
demo/index.html               standalone demo: a real mushaf page dressed in any mushaf's ornaments, plus
                              per-asset Colour / Mono / Line / Original and recolouring
demo/review.html              quick review sheet (needs a local http server for the object tags)
qa/                           the toolchain: qa/scan (render → … → slice), qa/common, qa/jobs
tests/                        catalog schema, SVG contract, slice geometry, tracer unit tests
docs/                         HANDOVER · METHOD · CONVENTIONS · USAGE · QUALITY · SESSION-LOG · PLAN
```

## Run it

```bash
bash sources/fetch_mushafs.sh              # ~2 GB of PDFs into sources/ (re-run until ALL_DONE)
pip install -r requirements.txt            # also needs poppler + cairo on PATH; npm i svgo for the optimize pass

python -m qa build                         # every job (headers ~3 s, frames ~35 s each)
python -m qa build --type page-frames --style qalon --to clean   # one job, stop after a stage
python -m qa optimize                      # svgo pass, then refresh meta.json to describe the delivered files
python -m qa catalog                       # rebuild catalog.json from the meta.json files
python -m qa validate                      # catalog schema + SVG contract + license traceability
python -m qa quality --baseline tests/quality-baseline.json --out work/quality    # raster regression gate
python -m qa demo                          # demo/index.html
python -m qa dist                          # dist/ for npm and the CDN
python -m pytest -q                        # 54 tests
```

PDFs can live elsewhere: `QA_SOURCES_DIR=/path/to/pdfs python -m qa build …`.
On Apple Silicon, cairo needs `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`.

## Using the SVGs

Every file follows the same contract (details in [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md)):
viewBox height 100; one `<g class="cN" data-part="cN">` per printed colour, `<g class="line">`
constant-width strokes on top, `<g class="slot">` transparent by default where the surah name /
text / ayah number goes; `data-slot="x y w h"` on the root; provenance in `data-source-*` and
`<metadata>`; symmetric designs are one quadrant plus `<use>` mirrors. Colours are presentation
attributes, so any CSS rule of yours wins and every rasterizer still renders the file correctly.

A page frame is not one fixed shape: where the border tiles, `slices/` holds the corner and the
two repeat units, and `frame()` in `@quran-ws/assets` assembles them at your page's aspect —
the corner keeps its shape, only the edge runs repeat. See [`docs/USAGE.md`](docs/USAGE.md).

## Licensing

**Not settled — do not redistribute yet.** The repo's position is recorded in
`qa/licenses.json` and stamped into every catalog entry: scan-derived assets are marked
`CC-BY-NC-SA-4.0`, status `provisional`, while written permission is sought from the mushaf
publishers ([`docs/PLAN.md`](docs/PLAN.md) §6). `python -m qa dist` marks the npm package
`"private": true` while any bundled asset is not `confirmed`, and the release workflow refuses
to publish it — the legal decision stays a human one. Every asset carries its source (mushaf,
archive.org item, PDF sha256, page, crop) so it can be made per-asset.
