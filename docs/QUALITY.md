# Vector quality review

The review is reproducible and uses the SVGs actually delivered to consumers. Install
`requirements.txt`; Cairo and Poppler must also be available. On Apple Silicon Homebrew,
set `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` when running CairoSVG.

```sh
python -m pipeline.quality --out work/quality
python -m pipeline.quality --baseline tests/quality-baseline.json --out work/quality
python -m pytest -q
```

The report covers 360px and 1000px full renders, plus a 1000px top-left crop from a
4000px render. Each comparison sheet puts `clean.png` above the SVG. `fills.png`
hides linework so the underlying fills can be inspected independently.

Metrics:

- Ink IoU: dark/saturated pixel overlap, excluding the transparent slot. The cleaned
  scan is resized to the SVG canvas. This does not undo intentional symmetry or
  deskewing; compare changes against the same asset, not scores between designs.
- Palette distance: mean marginal Wasserstein distance between fixed 8-bit Lab
  histograms, normalized to 0–1. Fixed bins permit comparison when the palette changes.
  Per-group area deltas are also recorded as diagnostics against that run's palette.
- Uncovered line fraction: transparent fill beneath internal strokes at 1000px.
  Slot boundaries and exterior edges are excluded by one stroke width because they
  intentionally border transparency. The eligible pixel count is recorded too.
- Open and isolated endpoints: measured in the shared path coordinates, before
  mirroring. Closed subpaths are excluded. An isolated endpoint can be a legitimate
  floral tip or meet another path's interior, so this is a diagnostic, not a zero-end
  requirement or a connectivity proof. Inspect the rendered linework too.

The default gate fails for a missing asset/size or a deterioration greater than
0.02 in ink IoU, palette distance, or internal fill coverage. The numbers do not
replace visual inspection. A source-limited design must remain identified as such;
an improved average cannot excuse a broken individual asset.

The initial committed assets are backed up locally in `work/baseline/assets`; their
measurements are in `work/baseline-quality-v2`. The original handover's visual ratings
were provisional: enlarged review exposed broken marker outlines and detached scan
marks that were not evident at app size.

Page-frame slices have their own check, at build time and in the tests: the pieces are cut,
reassembled the way `frame()` assembles them, and compared with the frame they came from
(`qa.scan.build.MIN_RECONSTRUCTION_IOU`, 0.70). Six frames pass at 0.74–0.96; `sousi` at 0.78;
`hafs-madinah-kabir` fails at 0.49 and ships whole. `tests/test_slices.py` also renders the
assembled SVG against `color.svg` and checks that an arbitrary page box is filled to its edges.
