# Session log — 9 Sep 2026 (Abdullah + Claude)

What was built, in order, with the decisions taken. Newest state is what's in the repo.

1. **Sources.** 8 mushaf PDFs from archive.org (Qalun, Hafs ʿĀdī, Hafs Madinah kabīr, Sūsī,
   Warsh, Hafs Madinah mumtāza, Dūrī, Shuʿbah), ~1.9 GB, verified byte-exact against the
   metadata API. The `dnXXX.archive.org` mirrors 500 on some items; the fetcher resolves the
   real storage server via `archive.org/metadata/<item>`.
2. **Surah headers** from PDF page 607/605 (three headers per page, sample pages chosen by
   Abdullah). Detection went through three designs before the connected-outline approach
   worked on all 8 without manual boxes. Cleaning = flatten the whole name slot.
3. **Vectorization** iterated with Abdullah watching: fills only → fills + traced outline →
   strokes. Decisions: *clean + smooth beats exact*; every printed ink one recolourable group;
   slot transparent by default; fixed-width strokes with fills extended under them; gradients
   flattened. Two real bugs found along the way: `np.convolve('valid')` on chains shorter than
   the window returned garbage (the long straight slashes), and black-only line detection
   missed dark-green/navy outlines (Hafs ʿĀdī, Kabir) — replaced by the erosion-based
   hue-agnostic rule.
4. **Symmetry.** Abdullah pointed out the 4-fold symmetry; quadrant + `<use>` mirrors cut
   files ~4× and made them exactly symmetric. Averaging quadrants blurred lines → rejected.
   A tilted stray page rule inside the padding produced a "bow" when mirrored → rules stripped,
   corner threshold lowered.
5. **Provenance** everywhere (`data-source-*`, `<metadata>`, catalog) at Abdullah's request.
6. **Demo** (`demo/index.html`, also a Claude artifact): Colour / Mono / Line / Original tabs,
   per-group colour pickers, background, Abdullah's calligraphic surah-name glyph placed from
   `data-slot`, copy-SVG. The glyph is y-down already — an early version flipped it by mistake.
7. **Page frames** (page 300): interior blanked from a centre flood; running-head and
   page-number cartouches removed and the ornament healed from neighbouring periods
   ("frames only", per Abdullah). Symmetry gained the c2 mode (Kabir's vine is rotational).
   Warsh and Mumtaza trace unsymmetrised (repeats not centre-aligned).
8. **Ayah markers** (page 300): detection needed ink-components-that-contain-colour; markers
   are teardrops/rosettes so aspect was relaxed and symmetry forced to 2-fold.
9. Repo restructured into the `quran-assets` layout from `docs/PLAN.md` (assets/<type>/<style>,
   root catalog, demo/, jobs.json). The plan itself is **not** implemented — see HANDOVER.

# Session log — 10 Sep 2026 (Abdullah + Claude)

Continues the log above. The handover's two jobs, in order.

10. **Vectorization review.** Built the missing measurement first (`qa quality`): renders every
    asset at 360 / 1000 / 4000 px, diffs ink against the cleaned scan, measures a palette
    distance and the fraction of stroke length with no fill under it, writes comparison sheets
    and fails on regressions against a committed baseline. Then fixed what it and the enlarged
    sheets exposed: palette fitting was including the blank text slot, paper and linework;
    merged clusters double-counted their pixels; ring reassignment could borrow from excluded
    pixels; fill growth expanded over intentional white channels and the slot. Qālūn's two
    petal shades survive now. The 4000 px review caught broken marker outlines and short
    pruned frame outlines that app-size screenshots had hidden. Removing detached scan marks
    also let Mumtaza's frame resolve to 4-fold symmetry (670 KB → 207 KB). 21 of 24 assets
    improved on ink IoU, none regressed beyond tolerance.
11. **Colour API.** Implemented the plan's `style="fill:var(--c1,#hex)"` form, then rejected it:
    an inline style is the one thing a consumer's `.c1{fill:…}` cannot override, and cairosvg
    throws on `var()` while resvg and mobile SVG libraries ignore it. Shipped `class` +
    `data-part` with the colour as a presentation attribute instead — every CSS rule wins over
    it, and the file is still right with no CSS at all. (PLAN §3 records the reversal.)
12. **Repo and tooling.** `pipeline/` became the `qa` package (`qa/scan`, `qa/common`,
    `qa/jobs/<type>.json`) behind one CLI: `build catalog optimize validate quality preview
    demo dist`. Added `tests/catalog.schema.json` + `qa validate` (schema, SVG contract,
    license traceability) and 54 tests; CI runs validate + tests + dist, publishes the demo to
    Pages, and a tag builds a release zip.
13. **Page frames are 9-sliced** (PLAN §4). Repeat length from the column-profile
    autocorrelation, *confirmed* by correlating neighbouring windows — without that, Mumtaza's
    alternating two-motif band reads as half its true period. The corner is snapped out to a
    whole repeat and to at least the width of the band it meets. All three pieces are traced
    from one quantization of the whole frame; traced separately, each fits its own k-means and
    the seams do not match. Every cut is gated on rebuilding the frame it came from (IoU ≥
    0.70): 7 of 8 tile (0.74–0.96), `hafs-madinah-kabir` does not and ships whole and says so.
    `frame()` in the npm package and `qa.common.frame` in Python assemble them at any page size.
14. **Licensing position, recorded rather than assumed** (`qa/licenses.json`): scan assets
    `CC-BY-NC-SA-4.0`, status `provisional`, `redistributable: false` until written permission.
    `qa validate` refuses a `confirmed` claim without an evidence file, `qa dist` marks the npm
    package private while anything is unconfirmed, and the release workflow refuses to publish
    it. The decision itself stays Abdullah's.
15. **Demo, at Abdullah's request:** a real typeset page (`quran-svg-pipeline`, KFGQPC Hafs
    p. 604) dressed in any mushaf's ornaments — ayah marks swapped for ours (the page keeps its
    own numbers), the surah-header frame placed behind each name by aligning `data-slot` with
    the name's bounding box, and the border assembled from the slices and tiled to that page's
    aspect. The page grows by exactly the margin the border needs, so the ornament never covers
    a word; a mushaf without slices falls back to the stretched whole frame and labels itself.
