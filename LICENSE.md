# License — provisional, not cleared for redistribution

The toolchain (`qa/`, `sources/*.sh|py`, `tests/`) is © quran.ws; a code license will be chosen
alongside the asset license.

The assets in `assets/` are vector tracings of ornaments printed in scanned mushafs whose
designs belong to their publishers (King Fahd Glorious Qur'an Printing Complex and others).
The repo's working position, recorded in `qa/licenses.json` and stamped into every catalog
entry, is **CC BY-NC-SA 4.0, status `provisional`, `redistributable: false`** — a
non-commercial release position held while written permission is sought (`docs/PLAN.md` §6,
option (b) alongside (a)). This is a position, not legal advice, and not a clearance.

What that means in practice:

* Nothing here may be redistributed yet — the npm package `qa dist` builds is marked
  `"private": true` while any asset's license status is not `confirmed`, and the release
  workflow refuses to publish it.
* `python -m qa validate` refuses to let an asset claim `confirmed` without a written evidence
  file in `sources/licenses/<style>.txt`.
* Each asset records its source (mushaf, archive.org item, PDF sha256, page, crop box) in
  `meta.json`, in the SVG `<metadata>` and in `catalog.json`, so the decision can be made per
  source rather than for the whole set.
* Attribution, when a release does happen, is the mushaf and its archive.org item, listed per
  asset in the generated `dist/LICENSES.md`.

`demo/page/604.svg` comes from the separate quran-svg-pipeline repository and is not covered by
the above; see `demo/page/README.md`.
