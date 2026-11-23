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

These are vector tracings of ornaments in eight mushafs printed by the King Fahd Glorious
Qur'an Printing Complex. The designs belong to the Complex. **The Complex permits reuse and
republication for any purpose other than printing.** The owner of quran-ws recorded this
position on 2026-11-23. Each of the eight mushafs has an evidence file in `sources/licenses/`,
and the catalogue gives the licence as `LicenseRef-KFGQPC`, status `confirmed`.

What that means in practice:

* The npm package `qa dist` builds is marked `"private": true` while any bundled asset's
  license status is not `confirmed`, and the release workflow refuses to publish it. The 7
  unverified font markers keep it private; `qa dist --exclude-unconfirmed` leaves them out.
* `python -m qa validate` refuses to let an asset claim `confirmed` without an evidence file in
  `sources/licenses/` — `<style>.txt` for a scan asset, since permission is per mushaf, and one
  file per source family for a font one, since one OFL text covers every weight taken from that
  family. Every source family must be covered, so one unverified family in a multi-source
  outline cannot hide behind a verified sibling.
* Each asset records its source (mushaf, archive.org item, PDF sha256, page, crop box) in
  `meta.json`, in the SVG `<metadata>` and in `catalog.json`, so the decision can be made per
  source rather than for the whole set.
* Attribution is the Complex and the mushaf, listed per asset in the generated
  `dist/LICENSES.md`.
* This record does not permit printing. Ask the Complex.

`demo/page/604.svg` comes from the separate quran-svg-pipeline repository and is not covered by
the above; see `demo/page/README.md`.
