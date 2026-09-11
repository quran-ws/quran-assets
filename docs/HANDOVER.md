# Handover

> **Updated 11 Sep 2026.** The font lineage is merged: `quranpedia/ayah-markers` is in, its 47
> markers normalised to the same SVG contract as the 24 scan assets, under one naming standard
> (`<lineage>-<name>`) and one catalog. 71 assets, 0 problems, 389 tests. `qa dist` now also
> builds `dist/fonts/AyahMarkers.{otf,ttf}`. See PLAN §3 (naming, units — §3's old units
> position is reversed and says so), §6 (licensing) and §8 phase 4.
>
> **The next job is the licensing decision for the scan assets (PLAN §6), which is Abdullah's.**
> It is now the only thing standing between this repo and a publishable package: 40 of the
> font markers are OFL-verified and `qa dist --exclude-unconfirmed` already produces a
> non-private 40-asset package. Everything else stays `private` and the release workflow
> refuses to publish it.
>
> Two things in `qa/font/data/` were made by hand and cannot be regenerated —
> `annotations.json` (contour → colour layer) and `number_placement.json` (47 number centres).
> `tests/test_font_markers.py` is the guard that they are what actually shipped.

> **Updated 10 Sep 2026.** Both jobs below were carried out: the vectorization review is done
> (§3 lists what was fixed and what remains), and PLAN phases 1–3 are largely implemented —
> `qa` CLI, catalog schema + validation, page-frame slicing, dist/npm build, CI, and a demo
> that dresses a real typeset page.

**Originally, to the next agent.** Two jobs, in this order:

1. **Review and improve the vectorization** (this document, §2–§4). Do not start on the plan
   until the assets are something you'd ship.
2. Then continue with [`PLAN.md`](PLAN.md) (unified repo, ayah-markers font lineage merge,
   9-sliced frames, dist/npm, demo on Pages, licensing). Phase 0 decisions there are Abdullah's.

Owner: Abdullah (quran.ws). Priorities he stated, in his words as much as possible: *"clean,
beautiful results, no noise"*; *"parts that were coloured together should be recolourable
together"*; *"priority clear + smooth vs 100 % matching the source"*; *"fixed-width drawing
lines, no fill gaps, smooth curves"*; *"middle section transparent by default (can be
recoloured)"*; *"all frames only"* (no running heads / page numbers); *"keep track of where each
came from"*.

## 1. State of the repo

* 8 mushafs × 3 types = 24 scan assets, plus 47 font-derived ayah markers = 79, all generated
  by `python -m qa build` with no manual boxes,
  plus 3 slice pieces for each of the 7 page frames whose border tiles. `demo/index.html` shows
  every one beside its scan and on a real page; open it and look before reading on.
* Everything is reproducible: `sources/fetch_mushafs.sh`, then `python -m qa build`,
  `qa optimize`, `qa catalog`, `qa demo`, `qa dist`. Set `QA_SOURCES_DIR` if the PDFs live
  elsewhere. Page renders are cached in `work/pages/` (ignored).
* Guard rails that did not exist before: `python -m qa validate` (catalog schema, SVG contract,
  license traceability), `python -m qa quality --baseline tests/quality-baseline.json` (raster
  regression gate at 360/1000/4000 px), and 54 tests. CI runs all three.
* `docs/METHOD.md` explains every stage; `docs/CONVENTIONS.md` the SVG contract;
  `docs/SESSION-LOG.md` how we got here and what was tried and rejected.
* Git history before this repo lives in Abdullah's local `quran-surah-header` folder (one
  commit + a large uncommitted round blocked by a stale `.git/HEAD.lock`); this repo starts fresh.

## 2. Quality assessment, honestly (the table below is the *original* review, kept for the reasoning)

Current numbers instead of ratings: every asset passes the raster regression gate, and the
review pass improved 21 of 24 on ink IoU (Warsh marker +0.13, Mumtaza frame +0.16, Qālūn header
+0.07) while the rest stayed within tolerance. `docs/QUALITY.md` explains what the numbers mean
and what they cannot tell you.

Scale: ✅ ship-quality after a glance · ◐ usable, visible flaws · ✗ needs work.

| style | header colour | header line | header mono | frame | marker | notes |
|---|---|---|---|---|---|---|
| qalon | ✅ | ✅ | ✅ | ✅ | ✅ | flower petals flattened to one pink (gradient absorbed) |
| warsh | ✅ | ✅ | ✅ | ◐ | ✅ | frame unsymmetrised (600 KB); same publisher layout as qalon |
| hafs-adi | ✅ | ✅ | ✅ | ✅ | ✅ | dark-green outlines; white-line ornament |
| shubah | ✅ | ✅ | ✅ | ✅ | ✅ | |
| douri | ✅ | ✅ | ✅ | ✅ | ✅ | |
| sousi | ✅ | ✅ | ✅ | ✅ | ✅ | navy is a fill, must stay one (erosion rule) |
| hafs-madinah-mumtaza | ◐ | ◐ | ✅ | ◐ | ✅ | fine detail; one stray stroke in the frame; unsymmetrised frame (670 KB); petal gradient |
| hafs-madinah-kabir | ◐ | ◐ | ◐ | ◐ | ◐ | 150-dpi JPEG source; softest of all; healed cartouches look right |

## 3. Known defects and where they come from (start here)

**Fixed in the review pass (10 Sep 2026)** — see `docs/METHOD.md` "Review corrections" and
`docs/QUALITY.md`: palette fitting no longer includes the slot, paper or linework, so Qālūn's
two petal shades survive (defect 1 is much reduced, not gone); light-cluster crumbs near slots
(defect 2) are absorbed; fill growth no longer paints over intentional white channels; markers
had broken outlines at 4000 px that the app-size review missed, fixed with per-job line
classification and gentler spur pruning; detached scan marks are removed from frame crops,
which also let Mumtaza resolve to 4-fold symmetry (670 KB → 207 KB); Kabir's frame keeps its
rotational symmetry. Defects 5 (Warsh/Mumtaza unsymmetrised) is obsolete: slicing replaced it.
Defect 6 (Mumtaza stray stroke) went with the detached-mark cleaning. Still open: 3 (stroke
junctions), 4 (only 1–2 stroke width classes), 7 (Kabir is source-limited — it is also the one
frame whose border will not slice), 8, 9, 10.

**The original list:**

1. **Gradient flattening loses design intent in flowers** (qalon/warsh petals pink→blue-gray;
   mumtaza). `min_frac` absorbs the shade into the nearest colour by ΔE, which is sometimes the
   wrong neighbour. Options: absorb into the *spatially adjacent* cluster (shared boundary
   length) instead of the nearest colour; or keep two shades when the minor one is a coherent
   blob rather than an edge ring. `vectorize.quantize`.
2. **Light-cluster crumbs near slots** — small fragments of the cartouche-fill colour (`c2`)
   survive around the slot outline (`light_min_px`, `_reassign_ring`). Visible as pale slivers
   in qalon/warsh headers at high zoom.
3. **Stroke quality at junctions** — round caps hide most gaps, but T-junctions and crossings
   are two chain ends meeting, not one path. Consider merging chains through degree-3 nodes when
   the tangents agree, and a final Ramer–Douglas–Peucker pass on the Bézier control polygon.
   `strokes._chains`, `_prune`.
4. **Stroke width classes** — currently 1–2 widths by a 1.6× split of the median. Mumtaza and
   others have three distinct line weights. Consider k-means on chain widths with a penalty.
5. **Warsh / Mumtaza frames not symmetrised** — the repeat is not phase-aligned to the centre.
   The right representation is a corner + repeating edge tile (PLAN §4, 9-slice); the
   `_period_by_template` code in `clean.py` already finds the period.
6. **Mumtaza frame has one stray stroke** (right side, mid-height) — a chain from the healed
   region boundary or the deskew edge; inspect `line.svg`.
7. **Kabir** — everything is limited by the source. Either find a 288-dpi scan of the same
   mushaf or accept it as "usable". Per-job overrides live in `qa/jobs/<type>.json`.
8. **Detection robustness is untested beyond these 8.** New mushafs will break assumptions
   (headers butting the border, frames without a closed inner outline, markers without colour).
   `candidates/` + `pick`, and `box`, are the escape hatches.
9. **Mono for pale-palette designs** relies on `paper_thresh`; a mushaf printed on tinted
   paper will need a per-job value.
10. **svgo** merges paths per group; fine for apps. (`qa optimize` now refreshes
    `meta.json.palette[].paths` and `viewBox` afterwards, so the metadata describes the
    delivered file.)

## 4. How to review (do this, don't eyeball the demo only)

* This is now `python -m qa quality` (see `docs/QUALITY.md`): renders at 360 / 1000 / 4000 px,
  diffs the ink against `clean.png`, measures a palette distance and the uncovered-line
  fraction, writes comparison sheets, and fails against `tests/quality-baseline.json`. Look at
  the sheets as well as the numbers — the enlarged review is what caught the broken marker
  outlines that app-size screenshots hid.
* Check continuity of `line.svg`: count path segments whose endpoints are >1 stroke width from
  any other path end (dangling ends) — should be near zero for these designs.
* Check the fills-under-strokes guarantee by rendering `color.svg` with `.line{stroke:none}` —
  no paper should show along former line positions.
* Keep the demo honest: it is the artefact Abdullah judges by. Rebuild it after every change.

## 5. What NOT to change without asking

* The SVG contract (CONVENTIONS.md) — the demo and any early consumers depend on it.
* Slot semantics (transparent, recolourable, `data-slot` in viewBox units).
* The "clean over exact" priority. Don't reintroduce gradient banding or speckle in the name
  of fidelity.
* Provenance fields.

## 6. Environment that worked

Originally: macOS host, pipeline in a Linux VM with Python 3.10, opencv-python-headless 5.0,
numpy, scikit-image 0.25, vtracer 0.6.12, poppler `pdfimages`, node + svgo 3.

Now (10 Sep 2026) it runs on the macOS host itself: Python 3.13 in `.venv` (uv-managed),
`requirements.txt` pinned, Homebrew cairo + poppler — CairoSVG needs
`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` on Apple Silicon — and `npm install --no-save
svgo@3` for the optimize pass. Headers ~2 s, markers ~1 s, frames ~35 s each (slicing traces
the whole frame a second time). No GPU, no network after the PDFs are fetched.
