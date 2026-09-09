# quran-assets

Decorative assets for Quran apps — **surah-header frames, page frames and ayah markers** —
vectorized from scanned mushaf PDFs into clean, recolourable, standardized SVGs.

Private repo of the quran.ws non-profit. Status: **alpha — pipeline works end to end on 8
mushafs (24 assets); vectorization quality is due for a review pass before anything ships.**
Start with [`docs/HANDOVER.md`](docs/HANDOVER.md).

```
assets/<type>/<style>/        the product: color.svg  mono.svg  line.svg  meta.json  source.*  clean.*
   type  = surah-headers | page-frames | ayah-markers
   style = mushaf id: qalon hafs-adi hafs-madinah-kabir sousi warsh hafs-madinah-mumtaza douri shubah
catalog.json                  one machine-readable index of every asset (+ provenance, palette, slots)
demo/index.html               standalone recolouring demo (Colour / Mono / Line / Original per asset)
demo/review.html              quick review sheet (needs a local http server for the object tags)
pipeline/                     python package: render → detect → clean → symmetry → vectorize → svgout
jobs.json                     what to extract from which page of which mushaf, + per-job overrides
sources/mushafs.json          the 8 source PDFs (archive.org) — the PDFs themselves are not committed
docs/                         HANDOVER · METHOD · CONVENTIONS · USAGE · SESSION-LOG · PLAN
```

## Run it

```bash
bash sources/fetch_mushafs.sh              # ~2 GB of PDFs into sources/ (re-run until ALL_DONE)
python3 -m pip install vtracer opencv-python-headless numpy scikit-image
# needs poppler (pdfimages/pdftoppm) on PATH; optional: node + `npm i svgo` for the optimize pass

python3 -m pipeline.run                    # every job in jobs.json  (headers ~3 s, frames ~20 s each)
python3 -m pipeline.run --mushaf qalon --asset page-frame --to clean   # one job, stop after a step
bash pipeline/optimize.sh                  # svgo pass (keeps ids/classes/data-*/metadata)
python3 -m pipeline.run --catalog-only     # rebuild catalog.json from meta.json files
python3 pipeline/build_demo.py             # demo/index.html
python3 -m pipeline.preview                # demo/review.html
```

PDFs can live elsewhere: `QA_SOURCES_DIR=/path/to/pdfs python3 -m pipeline.run …`.

## Using the SVGs

Every file follows the same contract (details in [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md)):
viewBox height 100; one `<g class="cN">` per printed colour, `<g class="line">` constant-width
strokes on top, `<g class="slot">` transparent by default where the surah name / text /
ayah number goes; `data-slot="x y w h"` on the root; provenance in `data-source-*` and
`<metadata>`; symmetric designs are one quadrant plus `<use>` mirrors.

## Licensing

Undecided — see [`docs/PLAN.md`](docs/PLAN.md) §6. Every asset carries its source (mushaf, archive.org
item, PDF sha256, page, crop) so a per-asset decision is possible. Do not redistribute until decided.
