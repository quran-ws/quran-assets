# License — two lineages, two positions

The toolchain (`qa/`, `sources/*.sh|py`, `tests/`) is © quran.ws; a code license will be chosen
alongside the asset license.

**The assets do not share one licence, and they never will** — they were made from different
things. Every asset carries its own, in `catalog.json → license`, keyed to a position in
`qa/licenses.json` and traceable to the source in its `sources[]`.

## Font-derived assets — `assets/ayah-markers/font-*`

47 ayah markers taken from the `U+06DD` glyph of Arabic fonts.

40 of them come from families under the **SIL Open Font License 1.1**, verified from
`license: "OFL"` in the family's `METADATA.pb` in [google/fonts](https://github.com/google/fonts),
and carry `status: "confirmed"`. The OFL travels with them: the licence
text and each family's copyright notice are reproduced in full in the generated
`dist/LICENSES.md`, from the evidence files in `sources/licenses/`. Three things it requires,
which the build holds to:

* derivatives stay OFL — these markers cannot be relicensed;
* the notice must travel with the material, so linking is not enough;
* no **Reserved Font Name** (`Alkalami`, `SIL`, `Scheherazade`, `Plex`, `Source`) may name a
  modified version. Marker ids are numeric for this reason, and the built font is
  "Ayah Markers" with glyphs `marker001…` — no source family name appears anywhere in it.

The other 7 (designs `014`–`020`, from `fonts.quran.ws`, including DigitalKhatt, which is
explicitly not OFL) have terms that are **not recorded upstream and have not been confirmed**.
No licence is asserted for them. They ship in the repository and in `dist/` as
`status: "pending"`; `qa dist --exclude-unconfirmed` leaves them out.

## Scan-derived assets — `assets/*/mushaf-*`

**Not cleared for redistribution.** These are vector tracings of ornaments printed in scanned mushafs whose
designs belong to their publishers (King Fahd Glorious Qur'an Printing Complex and others).
The repo's working position, recorded in `qa/licenses.json` and stamped into every catalog
entry, is **CC BY-NC-SA 4.0, status `provisional`** — a
non-commercial release position held while written permission is sought (`docs/PLAN.md` §6,
option (b) alongside (a)). This is a position, not legal advice, and not a clearance.

What that means in practice:

* The npm package `qa dist` builds is marked `"private": true` while any bundled asset's
  license status is not `confirmed`, and the release workflow refuses to publish it. The scan
  assets alone are enough to keep it private, so as things stand nothing ships by default.
* `python -m qa validate` refuses to let an asset claim `confirmed` without an evidence file in
  `sources/licenses/` — `<style>.txt` for a scan asset, since permission is per mushaf, and one
  file per source family for a font one, since one OFL text covers every weight taken from that
  family. Every source family must be covered, so one unverified family in a multi-source
  outline cannot hide behind a verified sibling.
* Each asset records its source (mushaf, archive.org item, PDF sha256, page, crop box) in
  `meta.json`, in the SVG `<metadata>` and in `catalog.json`, so the decision can be made per
  source rather than for the whole set.
* Attribution, when a release does happen, is the mushaf and its archive.org item, listed per
  asset in the generated `dist/LICENSES.md`.

`demo/page/604.svg` comes from the separate quran-svg-pipeline repository and is not covered by
the above; see `demo/page/README.md`.
