# quran-assets — plan for the unified repo (`quran-ws/quran-assets`)

> Abdullah's plan (Sep 2026). **Not implemented yet** — see `HANDOVER.md`: the vectorization
> review comes first, then this, in phases. Phase 0 decisions are his.

One repo, one catalog, one demo, one npm package for every decorative asset a Quran app needs: surah headers, ayah markers, page frames (and later whatever comes next — juz/hizb marks, sajdah marks, basmala). Two lineages feed it: **scan-derived** assets traced from mushaf PDFs (the surah-header pipeline, now in this repo) and **font-derived** assets extracted from OFL fonts (`quranpedia/ayah-markers`). The repo's job is to make those two lineages look identical to a consumer.

## 1. What we are merging

| | scan pipeline (this repo) | quranpedia/ayah-markers | page frames |
|---|---|---|---|
| Source | 8 mushaf PDFs (archive.org) | 26 fonts (Google Fonts + fonts.quran.ws) | same 8 mushaf PDFs |
| Method | render → detect → clean → symmetry → vectorize → svgout | glyph extraction → layered SVG → hand-placed number boxes → font build | same pipeline as headers (+ 9-slice split, todo) |
| Colour API | `<g class="c1" fill="#hex">`, `.line`, `.slot` | `<g data-part="fill-1" style="fill:var(--fill-1,#hex)">` | as headers |
| Units | viewBox height = 100 | font units (UPEM 1000) | as headers |
| Catalog | `catalog.json` (+ provenance: sha256, page, crop, commit) | `collection.json` (+ `number` box, `sources[].license`) | as headers |
| Extras | recolour demo, glyph slot placement | OTF/TTF font, `font-map.json`, demo, previews | — |
| License status | scans of printed mushafs — **undecided** | 14 OFL verified, **12 unverified** | inherits scan question |

The two conventions differ in three places (colour API, units, catalog schema). Everything else is compatible, so the merge is mostly a normalisation job plus one new pipeline stage.

## 2. Target repo layout

```
quran-assets/
├── README.md                     one-page: what's here, how to use, how to add
├── LICENSE.md                    repo license + per-asset license table (generated)
├── catalog.json                  ONE machine-readable index of every asset (generated)
├── assets/                       committed outputs, the product
│   ├── surah-headers/<style>/    color.svg mono.svg line.svg meta.json preview.png
│   ├── ayah-markers/<style>/     color.svg mono.svg meta.json preview.png
│   └── page-frames/<style>/      full.svg  mono.svg  slices/{corner,edge-h,edge-v,...}.svg meta.json
├── sources/                      inputs, NOT committed (manifest + fetchers only)
│   ├── mushafs.json  fetch_mushafs.sh
│   └── fonts.json    fetch_fonts.py            (from ayah-markers)
├── pipeline/                     python package `qa`
│   ├── scan/    render detect clean symmetry vectorize strokes slice
│   ├── font/    extract layer number_box build_font                    (from ayah-markers)
│   ├── common/  svgout catalog validate preview license
│   └── jobs/    surah-headers.json ayah-markers.json page-frames.json
├── dist/                         build output for consumers (generated, committed on release)
│   ├── fonts/AyahMarkers.{otf,ttf} + font-map.json
│   ├── sprites/<type>.svg        one <symbol> sheet per type
│   └── index.js / index.d.ts     typed catalog for npm
├── demo/                         single static site (GitHub Pages): browse, recolour, place a name / number, copy SVG
├── docs/  METHOD.md  USAGE.md  CONVENTIONS.md  CONTRIBUTING.md
├── tests/                        schema + geometry + license checks
└── .github/workflows/            build → validate → pages → release
```

Current state vs this layout: `assets/<type>/<style>/`, root `catalog.json`, `demo/`, `docs/`, `sources/mushafs.json` + `fetch_mushafs.sh` are in place. `pipeline/` is still one flat package (not `qa` with `scan/font/common`), jobs are one `jobs.json`, and `dist/`, `tests/`, workflows and the font lineage don't exist yet.

`<style>` is the thing an app picks: for scan assets it's the mushaf id (`qalon`, `warsh`, `hafs-madinah-mumtaza`…); for font assets it's the design number (`001`, `012-black`). A style directory is the unit of provenance and of licensing.

## 3. Conventions to unify (the real work)

**Colour API — adopt the ayah-markers form, keep the class names.** Every colour group becomes

```svg
<g class="c1" data-part="c1" style="fill:var(--c1,#e4e4e4)">
```

so both `.c1{fill:…}` and `--c1:…` keep working, and the fallback renders with no CSS at all. Reserved names: `slot` (transparent by default, for the surah name / ayah number), `c1…cN` (light→dark), `line` (constant-width strokes, `stroke:var(--line,#hex)`), and for mono variants `ink` (`currentColor`). Ayah-markers' `fill-base`/`fill-1` get renamed to `c1`/`c2` by a one-off script; the old names can stay as `data-part-legacy` for one release.

**Units — keep native, declare in meta.** Headers/frames stay at height-100 viewBoxes; markers from fonts stay in font units (they feed the font build and the number-box maths). `meta.json` carries `units: "normalized-100" | "font-upem"`; the catalog exposes both `viewBox` and `aspect`. Don't rescale font-marker paths — that would invalidate the hand-placed number centres.

**Slots — one shape.** `data-slot="x y w h"` and the font repo's `number:{cx,cy,width,height,r}` are the same idea. Catalog form: `slots: [{ role: "surah-name" | "ayah-number" | "text-area", x, y, w, h, cx, cy, r? }]` (already emitted), also as `data-slot-*` attributes on the SVG root.

**Catalog schema (`catalog.json`)** — one entry per style × type: `id, type, style, lineage, units, viewBox, variants{color,mono,line}, palette[], slots[], symmetry, sources[{kind:"mushaf-scan"|"font", …}], license{id,status}, pipeline_commit`. Font-derived entries use `sources[].kind = "font"` with the existing family/variant/OFL block. A JSON Schema in `tests/` validates every entry in CI. `collection.json` and `font-map.json` are regenerated *from* the catalog, not maintained separately.

**Tooling — one CLI.** `python -m qa build [--type page-frames] [--style qalon] [--to detect]`, `qa validate`, `qa catalog`, `qa preview`, `qa font`, `qa dist`. Same stage names for both lineages so a contributor learns one flow.

## 4. Page frames — the new asset type

Two sub-types, because they're used differently:

*Opening spread frames* (`page-frames/<mushaf>-opening`): the ornate Fatiha/Baqara pair, pages 1–2 of every mushaf. Detect as the largest colour-dense component on those pages; it's a left/right mirror pair, so trace the right page and emit the left as a mirrored `<use>`. The text block is the `slot`. Shipped as a whole SVG with a fixed aspect — apps place them like a header.

*Regular page borders* (`page-frames/<mushaf>`, **what exists today as full frames**): apps need these at *any* page size, so ship them 9-sliced: `corner.svg` (one, mirrored), `edge-h.svg` / `edge-v.svg` (repeatable unit, with `data-repeat="length"`), plus `full.svg` at the source aspect. Add a `slice` stage after `vectorize`: find the corner extent by symmetry, find the edge repeat period by autocorrelation (`clean._period_by_template` already does this), cut the paths. A small JS helper in `dist/` (`frame(el, {w,h})`) assembles the nine pieces.

## 5. Distribution

- **npm** `@quran-ws/assets`: `dist/` + `assets/` + `catalog.json` + types.
- **CDN**: jsDelivr picks up npm and GitHub tags automatically.
- **Fonts**: AyahMarkers OTF/TTF stay in `dist/fonts/`; a surah-header font is plausible later.
- **Demo** on GitHub Pages at `assets.quran.ws`: merge the two existing demos into one.
- **Versioning**: semver, `CHANGELOG.md`, git tags → GitHub release with the dist zip. Asset ids are stable; renaming a style is a major bump.

## 6. Licensing — needs a decision before the first public release

Font-derived assets: 14 OFL-verified are fine to redistribute with attribution. The 12 from fonts.quran.ws are *pending* — get written confirmation or exclude them from `dist/` until confirmed.

Scan-derived assets (headers, frames, markers): the ornament designs are the publishers' (KFGQPC and others); the traced SVGs are derivative works. Options, roughly in order of safety: (a) ask the publishers; (b) release under a clearly non-commercial license (CC BY-NC-SA) with attribution to each mushaf and the archive.org item, said so per asset in the catalog; (c) keep scan assets in the repo but out of npm until (a) resolves. Suggested: (b)+(a) in parallel. Not legal advice — check with the non-profit's counsel, since this ships under the quran.ws name.

## 7. Migration mechanics

1. ~~Finish the pending commit in `quran-surah-header`~~ — superseded: this repo starts fresh with the current state; the old folder keeps its own history locally.
2. `git subtree add --prefix=legacy/ayah-markers https://github.com/quranpedia/ayah-markers main` when merging the font lineage — full history, no rewriting.
3. Move files into the layout above in one "restructure" commit. Delete `legacy/`.
4. Archive the old repos with a README pointer to the new one.
5. Don't commit `sources/*.pdf` (1.9 GB) or source fonts; keep `work/` ignored. Committed footprint ~15 MB today; no LFS needed. `candidates/` PNGs are not committed — regenerate on demand.

## 8. Phases

**Phase 0 — decisions (Abdullah):** package name, license position (§6), colour-API rename (§3), whether the 12 pending fonts ship.

**Phase 1 — vectorization review** (see HANDOVER.md §2–4), then scaffold: `qa` CLI, unified catalog schema + JSON Schema + CI validate.

**Phase 2 — page frames:** opening-spread jobs, slicer, `frame()` helper; symmetrise Warsh/Mumtaza via tiles.

**Phase 3 — demo + dist + release:** merged demo on Pages, `dist/` build, npm publish `0.1.0`, `LICENSES.md` generated from the catalog.

**Phase 4 — later:** juz/hizb/sajdah marks (the margin marker is visible on page 300 of every mushaf), basmala, a surah-header font.

## 9. Open questions

- Package name: `@quran-ws/assets` or `@quran-ws/quran-assets`?
- Keep `quranpedia/ayah-markers` alive as a mirror, or archive outright?
- Is `<use>` mirroring acceptable for opening-spread frames too, or trace left/right pages separately where the scans differ?
- Demo domain: `assets.quran.ws`?
