# Using the assets in an app

## Surah header
```html
<div class="header"><!-- inline the SVG or <img src> it -->
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
import { get, frame } from "@quran-ws/assets";

const asset = get("page-frames", "qalon");
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

## Ayah marker
`data-slot` is the number disc. Draw the ayah number centred at `cx, cy` from `catalog.json`
(`slots[0]`), font-size ≈ 0.6 × slot height. `.slot{fill:…}` fills the disc.

## catalog.json
```js
const cat = await (await fetch('catalog.json')).json();
const qalonHeader = cat.assets.find(a => a.id === 'surah-headers/qalon');
qalonHeader.variants.color  // "assets/surah-headers/qalon/color.svg"
qalonHeader.palette          // [{name:'slot',hex:'none'},{name:'c1',hex:'#ffffff'},…,{name:'line',hex:'#353941',stroke:true}]
qalonHeader.slots[0]         // {role:'surah-name', x,y,w,h,cx,cy}
qalonHeader.sources[0]       // {kind:'mushaf-scan', mushaf, riwaya, file, sha256, archive_url, pdf_page, crop_box_px, …}
qalonHeader.license          // {id:'CC-BY-NC-SA-4.0', status:'provisional', redistributable:false, …}
cat.assets.find(a => a.id === 'page-frames/qalon').slices
                             // {files:{corner,'edge-h','edge-v'}, corner:{w,h}, repeat:{h,v}, corner_mode, reconstruction_iou}
```

The same data ships as a typed module: `import { assets, byId, get, ofType, url, slot, frame }
from "@quran-ws/assets"` (`dist/index.d.ts` has the types). One `<symbol>` sheet per type is in
`dist/sprites/<type>.svg`; inline the sheet in the DOM and `<use href="#surah-headers-qalon">`
— an external `<use>` across files is not portable.

Check `license.status` before you ship anything: today every scan-derived asset is
`provisional`, and the npm package is marked private for exactly that reason.
