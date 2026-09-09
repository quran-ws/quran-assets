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
glyph (`pipeline/surah_name_glyph.txt`).

Recolour: `.c2{fill:var(--brand)} .line{stroke:#222}`. Mono: set `color` on the container. Line-art:
`line.svg` with `color`, and `stroke-width` can be overridden per width class if you want bolder.

## Page frame
`data-slot` is the text area of the page in viewBox units. Fixed aspect (the mushaf page's).
Interior is transparent, so the app's page background shows through; `.slot{fill:…}` tints it.
Not yet 9-sliced (see PLAN §4) — at other aspect ratios it stretches.

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
```
