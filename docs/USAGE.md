# Using the assets in an app

## Surah header
```html
<div class="header"><!-- inline the SVG or <img src> it; ids are unique per file, so inline as many as you like -->
  <svg …data-slot="181.9 8.6 504.3 83.6"…>…</svg>
</div>
```
Place the surah name inside the slot: read `data-slot` (viewBox units, height = 100), convert to
percentages of the rendered box (`x/vbWidth*100 %`, `y %`, `w/vbWidth*100 %`, `h %`), and absolutely
position a text or glyph element there. `demo/index.html` does exactly this with a calligraphic
glyph (`qa/common/surah_name_glyph.txt`), and the demo's live page places the header behind
the surah name of a real typeset page by aligning `data-slot` with the name's bounding box.

Recolour: `.c2{fill:var(--brand)} .line{stroke:#222}`. Mono: set `color` on the container. Line-art:
`line.svg` with `color`, and `stroke-width` can be overridden per width class if you want bolder.

## Page frame
`data-slot` is the text area of the page in viewBox units. `color.svg` has the source page's
aspect; the interior is transparent, so the app's page background shows through and
`.slot{fill:…}` tints it.

For a page of *your* aspect, use the slices — the corner keeps its shape and only the edge runs
repeat, which is what stretching the whole frame gets wrong:

```js
import { get, frame } from "@quran.ws/assets";

const asset = get("page-frames", "mushaf-qalon");
if (asset.slices) {
  const svg = await frame(asset, { width: 210, height: 297 });   // any box, e.g. A4
  page.append(svg);                                              // size it with CSS
} else {
  // this border does not tile (hafs-madinah-kabir): use color.svg and scale it
}
```

The border needs its own margin: it is drawn *around* the text, not over it. Give the page a
margin of at least the band thickness — `slices.corner.h` is a safe value in frame units, or
read `slots[0].y` (the text area's inset) from the catalog. Colours work exactly as elsewhere
(`.c2{fill:…}`); each piece carries the same class names because all three are traced from one
quantization of the frame.

**Slices are colour-only.** A frame's `variants` lists `color`, `mono` and `line`, and it is
natural to assume the slices follow. They do not — a `slices/` directory only ever holds
`corner.svg`, `edge-h.svg` and `edge-v.svg`, traced from the colour quantization:

```sh
$ find assets -path '*slices*' -type f | sed 's#.*/slices/##' | sort | uniq -c
   7 corner.svg
   7 edge-h.svg
   7 edge-v.svg
```

So a tiled border is full colour or it is not tiled. A mono or line border is available only
whole, at the source page's own aspect — `variants.mono` / `variants.line` with `color.svg`'s
scaling caveat above. There is nothing to read from the catalog that says this; `asset.slices`
is truthy for a mono request exactly as it is for a colour one, and returns colour geometry.

Seven of the eight frames have slices at all. `mushaf-hafs-madinah-kabir` has none — its border
does not tile — which is what the `else` branch in the example above is for.

## Ayah marker
55 of them: 8 traced from mushaf scans (`mushaf-qalon`…, one per riwāyah) and 47 taken from the
`U+06DD` glyph of OFL fonts (`font-003-regular`…, a design number and a weight). Same contract,
same units; `ofType("ayah-markers", "scan" | "font")` separates them.

`data-slot` is where the number goes. Draw it centred at `cx, cy` from `catalog.json`
(`slots[0]`) and **size it by `h`, never by `w`** — `w` is the widest box the marker holds,
which is the three-digit case, and stretching one digit to it draws it about 2.7× too wide.
One centre per marker: the number sits in the same place whether it is one digit or three.

Two differences on the font-derived ones, both deliberate:

* `slots[0].r` is the largest circle that fits the marker's interior, if you would rather place
  a round badge than a box.
* there is no `slot` *group* and no `line.svg`. A traced cartouche leaves its middle empty, so a
  transparent group there is real geometry `.slot{fill:…}` can tint; a font marker's interior is
  painted solid by its base fill, so the number box ships as `data-slot` and `slots[]` only.
  Check `variants` rather than assuming three files.

The 47 centres were placed by hand and none of the boxes touches the marker's own ink.

## Ayah markers as a font
The font-derived markers also ship as a PUA font, for text runs where an inline SVG per ayah is
too much. It is outline only — one colour, no layers, and it contains no number.

```css
@font-face { font-family: "Ayah Markers"; src: url("./fonts/AyahMarkers.otf") format("opentype"); }
.ayah-mark { font-family: "Ayah Markers"; }
```
```html
<span class="ayah-mark">&#xE000;</span>
```

`dist/fonts/font-map.json` maps each glyph to its catalog `style`, so the SVG and the glyph for a
design are the same lookup:

```js
const map = await (await fetch('fonts/font-map.json')).json();
map.glyphs.find(g => g.style === 'font-003-regular')   // {style, marker, codepoint:'U+E00A', character}
```

Codepoints are fixed per marker, so a build that excludes some markers leaves gaps rather than
shifting the rest.

## catalog.json
```js
const cat = await (await fetch('catalog.json')).json();
// A style id is always `<lineage>-<name>`: `mushaf-qalon`, `font-003-regular`.
const qalonHeader = cat.assets.find(a => a.id === 'surah-headers/mushaf-qalon');
qalonHeader.variants.color   // "assets/surah-headers/mushaf-qalon/color.svg"
qalonHeader.palette          // [{name:'slot',hex:'none'},{name:'c1',hex:'#ffffff'},…,{name:'line',hex:'#353941',stroke:true}]
qalonHeader.slots[0]         // {role:'surah-name', x,y,w,h,cx,cy}
qalonHeader.lineage          // 'scan'  — always equals the style id's prefix
qalonHeader.sources[0]       // {kind:'mushaf-scan', mushaf, riwaya, file, sha256, archive_url, pdf_page, crop_box_px, …}
qalonHeader.license          // {id:'CC-BY-NC-SA-4.0', status:'provisional', …}
cat.assets.find(a => a.id === 'page-frames/mushaf-qalon').slices
                             // {files:{corner,'edge-h','edge-v'}, corner:{w,h}, repeat:{h,v}, corner_mode, reconstruction_iou}

const marker = cat.assets.find(a => a.id === 'ayah-markers/font-003-regular');
marker.variants              // {color, mono} — no `line`: a font marker has no linework
marker.slots[0]              // {role:'ayah-number', x,y,w,h,cx,cy,r}
marker.font                  // {upem:1000, advance, upem_scale, codepoint:'U+E00A', glyph:'U+06DD'}
marker.sources[0]            // {kind:'font', source, family, variant, source_url, upem, advance, license}
marker.license               // {id:'OFL-1.1', status:'confirmed', …}
```

The same data ships as a typed module: `import { assets, byId, get, ofType, url, slot, frame }
from "@quran.ws/assets"` (`dist/index.d.ts` has the types). One `<symbol>` sheet per type is in
`dist/sprites/<type>.svg`; inline the sheet in the DOM and `<use href="#surah-headers-qalon">`
— an external `<use>` across files is not portable.

Check `license.status` before you ship anything: today every scan-derived asset is
`provisional`, and the npm package is marked private for exactly that reason.
