#!/usr/bin/env python3
"""Build demo/review.html: a review sheet of every generated asset (source crop, clean
crop, colour SVG, mono SVG tinted via CSS `color`), with a live recolour demo per layer.
Run:  python3 -m pipeline.preview
"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
rows = []
for meta in sorted((ROOT / "assets").glob("*/*/meta.json")):
    m = json.load(open(meta)); d = Path("..") / "assets" / meta.parent.relative_to(ROOT / "assets")
    src = "source.jpg" if (meta.parent / "source.jpg").exists() else "source.png"
    pal = "".join(f'<label><input type="color" value="{p["hex"]}" data-cls="{p["class"]}"> {p["class"]}</label>' for p in m.get("palette", []))
    rows.append(f"""
<section data-dir="{d}"><h2>{m['mushaf']} <small>{m.get('riwaya','')} · {m['asset']} · p{m['page']} · viewBox {m.get('viewBox')}</small></h2>
<div class="grid">
 <figure><img src="{d}/{src}"><figcaption>source crop</figcaption></figure>
 <figure><img src="{d}/clean.png"><figcaption>clean (title removed)</figcaption></figure>
 <figure class="svgwrap"><object data="{d}/color.svg" type="image/svg+xml"></object><figcaption>color.svg — {len(m.get('palette',[]))} layers <span class="pal">{pal}</span></figcaption></figure>
 <figure><img class="mono" src="{d}/mono.svg" style="color:#1b3a5c"><figcaption>mono.svg (currentColor)  <input type="color" value="#1b3a5c" data-mono></figcaption></figure>
</div></section>""")
html = f"""<!doctype html><meta charset="utf-8"><title>Mushaf ornament assets</title>
<style>body{{font:14px system-ui;margin:24px;background:#f6f3ee;color:#222}} h2 small{{font-weight:normal;color:#666;font-size:12px}}
.grid{{display:grid;gap:10px}} figure{{margin:0;background:#fff;padding:8px;border:1px solid #ddd}} img,object{{width:100%;display:block}}
figcaption{{color:#666;font-size:12px;margin-top:4px}} .pal label{{margin-left:10px}} .mono{{background:transparent}}</style>
<h1>Mushaf ornament assets</h1><p>{len(rows)} assets. Pick colours to test recolouring: the colour SVG is recoloured per layer class (c1…cN); mono uses CSS <code>color</code>.</p>
{''.join(rows)}
<script>
document.querySelectorAll('input[data-cls]').forEach(i=>i.addEventListener('input',e=>{{
  const obj=e.target.closest('section').querySelector('object'); const doc=obj.contentDocument; if(!doc) return;
  doc.querySelectorAll('.'+e.target.dataset.cls).forEach(g=>g.setAttribute('fill',e.target.value));}}));
document.querySelectorAll('input[data-mono]').forEach(i=>i.addEventListener('input',e=>{{
  e.target.closest('figure').querySelector('img').style.color=e.target.value;}}));
</script>"""
(ROOT / "demo").mkdir(exist_ok=True); (ROOT / "demo" / "review.html").write_text(html)
print("wrote demo/review.html")
