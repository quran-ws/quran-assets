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
