# License — pending

The pipeline code (`pipeline/`, `sources/*.sh|py`, `demo/` build script) is © quran.ws; a
code license will be chosen with the asset license.

The assets in `assets/` are vector tracings of ornaments printed in scanned mushafs whose
designs belong to their publishers (King Fahd Glorious Qur'an Printing Complex and others).
They are **not yet cleared for redistribution**. Each asset records its source (mushaf, archive.org
item, PDF sha256, page, crop box) in `meta.json`, in the SVG `<metadata>`, and in `catalog.json`
(`license.status: "pending"`), so a per-source decision is possible. See `docs/PLAN.md` §6 for
the options under consideration.
