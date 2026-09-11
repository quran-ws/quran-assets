# quran-assets — plan for the unified repo (`quran-ws/quran-assets`)

> Abdullah's plan (Sep 2026). **Phases 1–3 are largely implemented** (10 Sep 2026); §8 records
> what is done and what is left. Abdullah delegated the Phase 0 decisions ("it's not launched
> yet, you can change anything, you decide") — the calls taken are marked **decided** below.
> The font lineage (§1, `quranpedia/ayah-markers`) is the main piece still outstanding.

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

Current state vs this layout: in place — `assets/<type>/<style>/` (page frames also carry
`slices/`), root `catalog.json`, `demo/`, `docs/`, `sources/mushafs.json` + `fetch_mushafs.sh`,
`qa/` (`scan/`, `common/`, `jobs/<type>.json`), `tests/`, `.github/workflows/`, and a generated
`dist/` (not committed; built by `qa dist` and by CI). Missing: `qa/font/` and everything the
font lineage brings (`sources/fonts.json`, `dist/fonts/`), and per-asset `preview.png`
(`qa preview` writes one review sheet instead).

`<style>` is the thing an app picks: for scan assets it's the mushaf id (`qalon`, `warsh`, `hafs-madinah-mumtaza`…); for font assets it's the design number (`001`, `012-black`). A style directory is the unit of provenance and of licensing.

## 3. Conventions to unify (the real work)

**Naming — decided 11 Sep 2026: `style = <lineage>-<name>`, every type, no exceptions.**
`mushaf-qalon`, `font-003-regular`. The merge put 8 riwāyah-named markers and 47
design-numbered ones in one directory; without the prefix that is two naming vocabularies side
by side and a consumer has to know which kind of name a style has before reading one. Applied to
all three types rather than only to markers, so a mushaf's header, frame and marker still share
a style id. `qa.style_id` / `qa.split_style`; `catalog.json → lineage` is derived from the
prefix. Done while nothing was published; after a release it is a major bump (§5).

**Colour API — decided: `class` + `data-part`, colour as a presentation attribute.** Every group is

```svg
<g class="c1" data-part="c1" fill="#e4e4e4">
```

The `style="fill:var(--c1,#e4e4e4)"` form in the original plan was implemented, tested, and
**rejected**: an inline `style` is exactly what a consumer's `.c1{fill:…}` rule cannot override,
and a rasterizer without CSS-variable support renders the file wrong — cairosvg throws on it,
resvg and most mobile SVG libraries ignore it. A presentation attribute loses to *every* CSS
rule, so class rules, attribute rules and custom properties of the app's own all work, and the
file is still right with no CSS at all. `data-part` is kept as the lineage-neutral selector. Reserved names: `slot` (transparent by default, for the surah name / ayah number), `c1…cN` (light→dark), `line` (constant-width strokes, `stroke="#hex"`), and for mono variants `ink` (`fill="currentColor"`). *Done:* `qa/font/svgout.py` renames `fill-base`/`fill-1`/`ink-*` to `c1…cN` on every build. No `data-part-legacy` was kept — nothing consumed the old names, and cairosvg raises outright on the `var()` form they came with, so there was nothing to stay compatible with.

**Units — one system, `normalized-100`, everywhere.** *Superseded 11 Sep 2026 (Abdullah).* This
section used to say markers from fonts should stay in font units, because rescaling "would
invalidate the hand-placed number centres". It does not: the centres are in the glyph's own
space and scale by the same factor as the artwork, and `tests/test_font_markers.py` asserts the
delivered slot is the hand-placed centre for all 47. The files had to be rewritten regardless —
the schema's `viewBox` pattern is `^0 0 …` and a glyph box has its origin wherever the font left
it — so normalising cost nothing and spared every consumer a branch on `units`. The font metrics
the OTF/TTF build needs (`upem`, `advance`, `upem_scale`, `codepoint`) are kept in `meta.json`
and in the catalog's `font` block; `upem` is the source font's and is 1000, 2048 or 3000.

**Slots — one shape.** `data-slot="x y w h"` and the font repo's `number:{cx,cy,width,height,r}` are the same idea. Catalog form: `slots: [{ role: "surah-name" | "ayah-number" | "text-area", x, y, w, h, cx, cy, r? }]` (already emitted), also as `data-slot-*` attributes on the SVG root.

**Catalog schema (`catalog.json`)** — *done*: one entry per style × type with `id, type, style,
lineage, units, viewBox, aspect, variants{color,mono,line}, palette[], slots[], symmetry,
slices{…} (page frames), sources[{kind:"mushaf-scan"|"font", …}], license{id,status,…},
pipeline_commit`. `tests/catalog.schema.json` validates every entry (`python -m qa validate`, in
CI and in `tests/test_catalog.py`), together with the SVG contract and license traceability.
*Done:* font-derived entries use `sources[].kind = "font"`, one per source font, each with its
own licence — which is what lets `license` be decided per asset rather than per lineage.
`collection.json` is gone rather than regenerated: everything it held is in the catalog, and its
per-marker source records live on as the pipeline's input at `qa/font/data/selection.json`.
`font-map.json` is generated by `qa dist` and keys each glyph by catalog `style`.

**Tooling — one CLI.** *done*: `python -m qa build [--type page-frames] [--style qalon] [--to detect] [--force]`, `qa catalog`, `qa optimize`, `qa validate`, `qa quality`, `qa preview`, `qa demo`, `qa dist`. `qa font` arrives with the font lineage. Jobs are split per type in `qa/jobs/<type>.json`.

## 4. Page frames — the new asset type

Two sub-types, because they're used differently:

*Opening spread frames* (`page-frames/<mushaf>-opening`): the ornate Fatiha/Baqara pair, pages 1–2 of every mushaf. Detect as the largest colour-dense component on those pages; it's a left/right mirror pair, so trace the right page and emit the left as a mirrored `<use>`. The text block is the `slot`. Shipped as a whole SVG with a fixed aspect — apps place them like a header.

*Regular page borders* — **done**. `qa/scan/slicer.py` runs after `vectorize` and writes
`slices/{corner,edge-h,edge-v}.svg` beside the whole `color.svg`; `frame(asset, {width, height})`
in `dist/index.js` (and `qa.common.frame.assemble` in Python) puts them together at any page
size. Two things the plan did not anticipate: the repeat length has to be *confirmed* by
correlating neighbouring windows, because an alternating two-motif band autocorrelates at half
its true period (Mumtaza); and the three pieces must be traced from one quantization of the
whole frame, or each fits its own k-means and the seams do not match. Every cut is gated on
rebuilding the frame it came from (IoU ≥ 0.70): 7 of 8 tile, `hafs-madinah-kabir` does not and
ships whole. Warsh and Mumtaza no longer need the tile-symmetrisation of §3.5 — slicing solves
the same problem better.

## 5. Distribution

- **npm** `@quran-ws/assets` (*decided*; `python -m qa dist` builds it): `dist/index.js` +
  `index.d.ts` (typed catalog, `get`/`ofType`/`url`/`slot`/`frame`), `catalog.json`, `assets/`
  (incl. `slices/`), `sprites/<type>.svg`, `LICENSES.md`. The package is `"private": true`
  while any bundled asset's license is not `confirmed`, and the release workflow refuses to
  publish it — so the legal call stays human. `dist/` is generated, not committed.
- **CDN**: jsDelivr picks up npm and GitHub tags automatically.
- **Fonts**: AyahMarkers OTF/TTF stay in `dist/fonts/`; a surah-header font is plausible later.
- **Demo** on GitHub Pages at `assets.quran.ws`: merge the two existing demos into one.
- **Versioning**: semver, `CHANGELOG.md`, git tags → GitHub release with the dist zip. Asset ids are stable; renaming a style is a major bump.

## 6. Licensing — needs a decision before the first public release

Font-derived assets: the 14 OFL-verified families are fine to redistribute with attribution, and
40 markers now carry `status: "confirmed", redistributable: true` — evidence is the OFL text per
family in `sources/licenses/`, which `qa validate` requires and `qa dist` reproduces in full.
*Decided 11 Sep 2026 (Abdullah):* the 7 markers from the unverified `fonts.quran.ws` families
(designs 014–020) ship everywhere — repository, `dist/`, and one 47-glyph font — flagged
`status: "pending", redistributable: false`. That needed no gate loosened: the package is
`private` while anything is unconfirmed, and the scan assets keep it that way regardless. The
two positions only diverge once the scan licences resolve and the package goes public;
`qa dist --exclude-unconfirmed` is the flag for making that call at release time, and it
produces a publishable 40-asset package today.

Scan-derived assets (headers, frames, markers): the ornament designs are the publishers' (KFGQPC and others); the traced SVGs are derivative works. Options, roughly in order of safety: (a) ask the publishers; (b) release under a clearly non-commercial license (CC BY-NC-SA) with attribution to each mushaf and the archive.org item, said so per asset in the catalog; (c) keep scan assets in the repo but out of npm until (a) resolves. Suggested: (b)+(a) in parallel. Not legal advice — check with the non-profit's counsel, since this ships under the quran.ws name.

## 7. Migration mechanics

1. ~~Finish the pending commit in `quran-surah-header`~~ — superseded: this repo starts fresh with the current state; the old folder keeps its own history locally.
2. `git subtree add --prefix=legacy/ayah-markers https://github.com/quranpedia/ayah-markers main` when merging the font lineage — full history, no rewriting.
3. Move files into the layout above in one "restructure" commit. Delete `legacy/`.
4. Archive the old repos with a README pointer to the new one.
5. Don't commit `sources/*.pdf` (1.9 GB) or source fonts; keep `work/` ignored. Committed footprint ~15 MB today; no LFS needed. `candidates/` PNGs are not committed — regenerate on demand.

## 8. Phases

**Phase 0 — decisions.** *Taken* (delegated by Abdullah, 10 Sep 2026): package name
`@quran-ws/assets`; colour API = `class` + `data-part` + presentation attribute (§3, the
`var()` form was tried and rejected); license position = scan assets `CC-BY-NC-SA-4.0`,
status `provisional`, redistribution blocked in the build until confirmed (§6, recorded in
`qa/licenses.json`); the 12 unverified fonts stay `pending` and cannot be marked
redistributable — `qa validate` enforces that a `confirmed` claim has an evidence file in
`sources/licenses/`. Any of these is Abdullah's to overturn; each is one data change.

**Phase 1 — done.** Vectorization review (see QUALITY.md; 24/24 pass the raster regression
gate, 54 tests), `qa` CLI, per-type job files, unified catalog + JSON Schema + `qa validate`
in CI.

**Phase 2 — page frames: slicer done** (see §4). Still open: opening-spread frames
(`<mushaf>-opening`, pages 1–2), which need their own detector and job.

**Phase 3 — demo + dist mostly done.** `qa dist` builds the package and sprite sheets; CI
publishes `demo/` to Pages and a tagged build produces a release zip. The demo now also
dresses a real typeset page (KFGQPC Hafs p. 604) in any mushaf's ornaments — marks, headers
placed from `data-slot`, and the sliced border tiled to that page's aspect. Not done: npm
publish (blocked on §6), `assets.quran.ws` DNS, merging the ayah-markers demo.

**Phase 4 — font lineage done (11 Sep 2026).** `quranpedia/ayah-markers` merged as a plain copy
of `e083434` (not a subtree: every file was about to be rewritten by the normalisation pass, so
blame through the move would have pointed at something that no longer looked like that). 47
markers at `assets/ayah-markers/font-*`, `qa/font/` with the 9 upstream scripts renamed and
repackaged, `qa build --lineage font`, and `dist/fonts/AyahMarkers.{otf,ttf}` from `qa dist`.
No new CLI verb: `qa font` was dropped in favour of `--lineage`, so the eight documented
commands still cover everything. `collection.json` is gone — the catalog is the catalog.
Still not started: juz/hizb/sajdah marks, basmala, a surah-header font.

## 9. Open questions

- ~~Package name~~ — decided: `@quran-ws/assets`.
- ~~Keep `quranpedia/ayah-markers` alive as a mirror, or archive outright?~~ — neither for now:
  it is untouched and read-only. Abdullah, 11 Sep 2026.
- Is `<use>` mirroring acceptable for opening-spread frames too, or trace left/right pages separately where the scans differ?
- Demo domain: `assets.quran.ws`?
