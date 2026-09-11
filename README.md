# Quran Assets

Surah headers, page frames and ayah markers from eight printed muṣḥafs, traced into
recolourable SVGs — with the scan each one came from recorded inside the file. Beside them,
47 more ayah markers taken from the `U+06DD` glyph of Arabic fonts, under the same contract.

| Package | Version | Assets | Sources |
|---|---|---|---|
| `@quran-ws/assets` — **not published yet** | `0.1.0` | 71 — 24 traced (3 types × 8 printings) + 47 font-derived markers | 8 printings of 6 riwāyāt; 26 font families |

![A printed surah header and the SVG traced from it](docs/img/scan-to-svg.png)

The name is gone, the gradient bands are gone, the paper is gone. What is left is one
group per printed ink, a transparent slot where the calligrapher left room for the surah
name, and this on the root element:

```
data-source-file="qalon.pdf"  data-source-page="607"  data-source-box="341 300 1348 416"
```

A **muṣḥaf** is a printed copy of the Qurʾān; a **riwayah** is one transmitted reading of
its text, and each riwayah tends to be printed with its own ornament. There are glossary
entries for [muṣḥaf](https://quran.ws/docs/concepts/glossary/#mushaf),
[riwayah](https://quran.ws/docs/concepts/glossary/#riwayah),
[surah header](https://quran.ws/docs/concepts/glossary/#surah-header),
[ayah marker](https://quran.ws/docs/concepts/glossary/#ayah-marker) and
[page frame](https://quran.ws/docs/concepts/glossary/#page-frame) if any of those are new.

---

**زخارف المصاحف، جاهزة للتطبيقات.** عناوين السور، وإطارات الصفحات، وعلامات الآيات،
مستخرَجة من ثمانية مصاحف مطبوعة ومحوَّلة إلى ملفات SVG نظيفة قابلة لإعادة التلوين، لكل
رواية زخرفتها. كل ملف يحمل مصدره: اسم المصحف، ورقم الصفحة، وبصمة sha256 للملف الأصلي.
الأصول **لم تُرخَّص للنشر بعد** — انظر [LICENSE.md](LICENSE.md).

---

## What it provides

- **Three ornament types for each of eight printed muṣḥafs** — a set per riwayah, not one
  generic set. A Warsh page dressed in Ḥafṣ ornament is wrong, and this repository exists
  so you do not have to do that.
- **Three drawings of every asset**: `color.svg` (as printed), `mono.svg` (one ink,
  `currentColor`), `line.svg` (linework only, `currentColor`). They are separate tracings,
  not filters over one another.
- **One group per printed ink**, each carrying both a `class` and a `data-part`, so
  recolouring is a CSS rule rather than a redraw.
- **A transparent `slot` group** and a `data-slot="x y w h"` rectangle marking the space
  the printer left for the surah name, the ayah number or the page's text area.
- **Tileable borders.** Where a frame's border repeats, it also ships as three pieces —
  `corner.svg`, `edge-h.svg`, `edge-v.svg` — so it can be assembled to a page aspect the
  printed page never had.
- **Provenance in every file**: source PDF, page number, crop box and the scan's `sha256`,
  on the root element and in a JSON `<metadata>` block. An asset pulled out of context can
  still be traced back to the printed page.
- **A second lineage of ayah markers, from fonts.** 47 markers extracted from the `U+06DD`
  glyph of 26 Arabic families — 20 designs across their weights — each layered into
  recolourable groups by hand, with a hand-placed box for the ayah number. They also ship
  as one PUA font (`dist/fonts/AyahMarkers.otf`). 40 of the 47 are OFL-1.1 and are the only
  things here currently clear to redistribute.
- **One naming rule for both lineages**: `style` is `<lineage>-<name>` — `mushaf-qalon`,
  `font-003-regular` — and `data-style` / `data-lineage` on every root element say which is
  which.

## Use it when you need

- Ornament in an application, a website, an export or a design tool — headers above a
  surah, markers after a verse, a border around a page.
- To dress typeset text in a particular muṣḥaf's decoration, rather than in generic
  Islamic clip art.
- A border at your page's aspect ratio, tiled from repeat units instead of stretched.
- To recolour ornament to a theme without losing what the press actually laid down — the
  printed palette stays in `catalog.json` and in the file's own attributes.

## Not for

| You want | Use instead |
|---|---|
| The Qurʾānic text itself — verses, words, search | [Quran Text](https://github.com/quran-ws/quran-text) |
| A complete printed muṣḥaf page as artwork | [Quran SVG](https://github.com/quran-ws/quran-svg) — the archive of vectorised muṣḥafs, every ayah mapped |
| Addressing individual words or marks inside page artwork | [Quran SVG Elements](https://github.com/quran-ws/quran-svg-elements), for the muṣḥafs that have been split |
| Rendering pages on mobile or native, where SVG stops performing | [Quran Engine](https://github.com/quran-ws/quran-engine) |

This repository holds ornament only. There is no Qurʾānic text in it.

## See it work

<https://quran.ws/blocks/quran-assets/> dresses a real page with the files from this
repository, at the commit recorded in the site's `public/demo/SOURCES.json`. Pick a header,
a frame and an ayah marker — all 55 markers, from muṣḥafs and from fonts, in one drawer —
and see them on page 604 of the Madinah muṣḥaf (its own ornaments swapped out, its own ayah
numbers kept) or on live text set in the riwāyah's font. Recolour any ink group, resize the
marker, then copy the recoloured SVG, the CSS that produces it, or download the file. The
`slot` group is never touched.

`demo/index.html` in this repository does the same locally.

## Supported muṣḥafs

Eight printings of six riwāyāt. Ḥafṣ appears three times because a printing, not a
riwayah, is the right unit for an ornament.

| `style` key | Riwayah | Border tiles? |
|---|---|---|
| `mushaf-qalon` | Qālūn ʿan Nāfiʿ | yes |
| `mushaf-warsh` | Warsh ʿan Nāfiʿ | yes |
| `mushaf-douri` | al-Dūrī ʿan Abī ʿAmr | yes |
| `mushaf-sousi` | al-Sūsī ʿan Abī ʿAmr | yes |
| `mushaf-shubah` | Shuʿbah ʿan ʿĀṣim | yes |
| `mushaf-hafs-adi` | Ḥafṣ ʿan ʿĀṣim — ʿĀdī printing | yes |
| `mushaf-hafs-madinah-mumtaza` | Ḥafṣ ʿan ʿĀṣim — Madinah, *mumtāza* | yes |
| `mushaf-hafs-madinah-kabir` | Ḥafṣ ʿan ʿĀṣim — Madinah, large | **no** — ships whole |

Read from `catalog.json`; the "tiles" column is `if (asset.slices)`.

The font-derived markers are `font-<design>-<weight>`: `font-001-regular` through
`font-020-…`, 47 in all, `lineage: "font"` in the catalog. Their ids are numeric on purpose
(see [Licence](#licence)); the family each came from is in `sources[]`.

> **Key naming, unresolved.** The muṣḥaf keys are printings, and their romanisation differs
> from `quran-text`, which uses `duri`, `susi`, `qalun` and a single `hafs`. There is no
> `mushaf-hafs` key here at all. Neither spelling is authoritative yet, so do not assume you
> can join the two packages lexically — write the mapping explicitly, and expect it to
> change when the org settles on one romanisation.
>
> For the same reason, `riwaya` in `catalog.json` is a display string
> (`"Qalun 'an Nafi'"`) — ASCII, no Arabic, and the parenthetical names the printing as
> well as the riwayah. Do not parse it.

## Provenance

Every scan asset is traced from a scanned muṣḥaf PDF fetched from archive.org, and records
where it came from in three places: the SVG root element, the SVG `<metadata>` block and
`catalog.json`. A font asset records the family, variant, source URL and glyph the same
three ways, and keeps the extracted outline beside it as `source.svg`.

```json
{ "kind": "mushaf-scan", "mushaf": "qalon", "riwaya": "Qalun 'an Nafi'",
  "file": "qalon.pdf", "sha256": "cbbb52b2…aef8de", "pdf_page": 607,
  "crop_box_px": [341, 300, 1348, 416],
  "archive_url": "https://archive.org/details/quran-qalon" }
```

Quality is measured, not asserted. `qa quality` renders every asset at 360, 1000 and
4000 px and diffs the ink against the cleaned scan, failing on any deterioration against
`tests/quality-baseline.json`. A font marker is vector in and vector out, so it is compared
with the outline it was extracted from instead; all 47 score ≥ 0.99. Frame slices are cut,
reassembled and compared with the frame they came from: the threshold is 0.70 IoU, the
seven that ship score 0.74–0.96, and `mushaf-hafs-madinah-kabir` fails at 0.49 and is
therefore not sliced. [`docs/QUALITY.md`](docs/QUALITY.md) says what the numbers cannot
tell you.

**Licence: the scan assets are provisional and not cleared for redistribution.** All 24
carry `"status": "provisional"`, `"redistributable": false`; so do the 7 font markers whose
terms are unconfirmed. The other 40 are OFL-1.1, `confirmed`. See [Licence](#licence) below
before you use anything.

## Quick start

**There is no install line, and that is not an oversight.** This repository is private,
there are no releases, and `@quran-ws/assets` is not on npm — `qa dist` marks the package
`"private": true` while any asset's licence is unconfirmed, and the release workflow
refuses to publish it. If you have access to the repository, read the files directly:

```sh
gh repo clone quran-ws/quran-assets
# or one file at a time — quote the URL, zsh globs '?'
gh api "repos/quran-ws/quran-assets/contents/assets/surah-headers/mushaf-qalon/color.svg?ref=main" \
  --jq '.content' | base64 -d > qalon-header.svg
```

The layout is `assets/<type>/<style>/`, with `<type>` one of `surah-headers`,
`page-frames`, `ayah-markers`:

```
assets/surah-headers/mushaf-hafs-madinah-mumtaza/color.svg
assets/page-frames/mushaf-warsh/slices/          # corner + edge-h + edge-v
assets/ayah-markers/mushaf-qalon/mono.svg
assets/ayah-markers/font-003-regular/color.svg   # from a font; OFL-1.1
```

Every file has the same shape. `viewBox` height is always 100, so the width *is* the
aspect ratio:

```svg
<svg viewBox="0 0 863.429 100" data-style="mushaf-qalon" data-lineage="scan" data-mushaf="qalon"
     data-asset="surah-header" data-variant="color" data-symmetry="4"
     data-slot="180.8571 8.5714 501.4286 83.1429">
  <g class="slot" data-part="slot" fill="none">…</g>          <!-- where the name goes -->
  <g class="c1"   data-part="c1"   fill="#ffffff">…</g>       <!-- fills, light → dark -->
  <g class="c2"   data-part="c2"   fill="#cfd0d2">…</g>
  …
  <g class="line" data-part="line" stroke="#343f49" fill="none">…</g>
</svg>
```

Inline it and recolour with CSS. Colours are presentation attributes, never inline
`style` and never `var()` in the file, so any CSS rule of yours wins — and a rasteriser
with no CSS support at all still renders the file as printed:

```css
.c2 { fill: var(--brand); }
.line { stroke: #222; }
.slot { fill: #fffdf7; }     /* the slot is transparent until you fill it */
```

Because mirrored artwork is built from `<use>` clones, one declaration recolours all four
quadrants. `data-symmetry` says how: `4` on headers and tiling frames, `2` on scan markers,
`c2` for a 180° rotation, `1` for artwork traced whole and for every font marker. The
quadrant's id is unique per file (`q-<style>-<asset>-<variant>`), so any number of assets
can be inlined into one document.

Font markers ship `color.svg` and `mono.svg` but no `line.svg` — there is no constant-width
linework in a glyph — and no `slot` group: the number's box is `data-slot` and the catalog's
`slots[]`, with `r` for the inscribed circle. Size the numeral by the box's *height*, never
its width; the width is the three-digit case.

Place your own type inside `data-slot` — it is `x y w h` in viewBox units, so convert to
percentages of the rendered box and position absolutely. `catalog.json` adds `cx, cy` for
centring, and names the slot's role: `surah-name`, `ayah-number` or `text-area`.

To tile a border, read the three slice files. Each carries its size in its own `viewBox`,
the repeat length in `data-repeat`, and the frame it belongs to in `data-frame-viewbox` —
all in the frame's units, so they compose without rescaling.

> **You also need `catalog.json` to assemble a frame.** Whether the other three corners are
> mirrors or 180° rotations is `slices.corner_mode`, and it lives only in the catalog — it
> is not on `corner.svg`. Every frame is currently `"mirror"`, so guessing is right today
> and would fail silently on the day one is `"rotate"`: the corner would be flipped rather
> than turned, which renders cleanly and is wrong. Read `corner_mode` from the catalog.

> **Slices are colour-only.** There are no `mono` or `line` slice files, so a tiled border
> is full colour or it is not tiled. A mono or line border is available only whole, at the
> printed page's own aspect.

## Works with

| | Why |
|---|---|
| [Quran SVG](https://github.com/quran-ws/quran-svg) | Frame a real vectorised page, and use the marker that printing actually used. |
| [Quran Engine](https://github.com/quran-ws/quran-engine) | Draw ornament alongside page artwork on mobile and native. |
| [Quran Text](https://github.com/quran-ws/quran-text) | The surah name and ayah number you draw into the slots. |

## Documentation

| | |
|---|---|
| Using the assets in an app | [`docs/USAGE.md`](docs/USAGE.md) |
| The SVG contract in full | [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) |
| How each pipeline stage works | [`docs/METHOD.md`](docs/METHOD.md) |
| What the quality numbers mean | [`docs/QUALITY.md`](docs/QUALITY.md) |
| What is decided and what is open | [`docs/PLAN.md`](docs/PLAN.md), [`docs/HANDOVER.md`](docs/HANDOVER.md) |
| Long-form reference on the site | <https://quran.ws/docs/reference/quran-assets/> |

### Rebuilding from source

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

## Licence

**The scan assets are not cleared for redistribution. Read this before using anything.**

They are vector tracings of ornaments printed in muṣḥafs whose designs belong to their
publishers (the King Fahd Glorious Qurʾān Printing Complex among others). The working
position is CC BY-NC-SA 4.0 with status `provisional` — a position held while written
permission is sought, not a clearance, and not legal advice.

**40 of the 47 font markers are OFL-1.1 and may be redistributed**, with the licence and
each family's copyright notice travelling with them — `qa dist` writes both into
`dist/LICENSES.md` in full, because the OFL requires it. Marker ids are numeric on purpose:
the OFL forbids a Reserved Font Name (Alkalami, SIL, Scheherazade, Plex, Source) naming a
modified version, and nothing here carries a family name. The other 7 (designs 014–020,
from `fonts.quran.ws`) have terms nobody has confirmed; they ship flagged `pending`, and it
is they and the scan assets that keep the npm package private. `qa dist
--exclude-unconfirmed` builds the 40 alone as a package that could be published.

That position is enforced rather than stated. `python -m qa validate` refuses to let an
asset claim `confirmed` without written evidence in `sources/licenses/`; `qa dist` marks
the npm package private while anything is unconfirmed; the release workflow refuses to
publish. Because every asset carries its own source, the decision can be made per muṣḥaf
rather than for the whole set.

A code licence for the toolchain (`qa/`, `sources/`, `tests/`) will be chosen alongside the
asset licence. See [LICENSE.md](LICENSE.md) and [`docs/PLAN.md`](docs/PLAN.md) §6.

`demo/page/604.svg` comes from a separate repository and is not covered by the above; see
`demo/page/README.md`.

---

A [quran.ws](https://quran.ws) project. The assets and the pipeline are real; nothing is
published.
