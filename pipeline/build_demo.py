#!/usr/bin/env python3
"""Generate the recolouring demo page (demo/index.html) from assets/*/*/{color,mono,line}.svg
+ meta.json. Usage: python3 pipeline/build_demo.py  [assets_dir out_body.html out_full.html]
out_body = page without <html>/<head> wrapper (for hosted artifacts); out_full = standalone file.
"""
import json, re, sys, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
A = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets"
out_body = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "work" / "demo_body.html"
out_full = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "demo" / "index.html"
out_body.parent.mkdir(parents=True, exist_ok=True)
GLYPH = (Path(__file__).resolve().parent / "surah_name_glyph.txt").read_text().strip()
ORDER = ["hafs-madinah-mumtaza", "hafs-madinah-kabir", "hafs-adi", "shubah", "warsh", "qalon", "douri", "sousi"]
NAMES = {"hafs-madinah-mumtaza": "Hafs · Madinah (Mumtaza)", "hafs-madinah-kabir": "Hafs · Madinah (Kabir)", "hafs-adi": "Hafs · ʿĀdī",
         "shubah": "Shuʿbah", "warsh": "Warsh", "qalon": "Qālūn", "douri": "al-Dūrī", "sousi": "al-Sūsī"}

def load_svg(p, uid):
    s = p.read_text()
    s = re.sub(r'<\?xml[^>]*\?>', '', s)
    # scope: add an id so JS can find it; strip nothing else (groups + classes are the API)
    s = s.replace("<svg ", f'<svg id="{uid}" ', 1)
    s = s.replace('id="q"', f'id="q-{uid}"').replace('href="#q"', f'href="#q-{uid}"')
    return s.strip()

TYPES = [("surah-header", "Surah headers", "The title frame above every surah. The name slot is transparent; your calligraphic glyph is placed from <code>data-slot</code>."),
         ("page-frame", "Page frames", "The decorative border of every page, interior blanked; <code>data-slot</code> is the text area. Running heads and page-number boxes are removed and the ornament healed."),
         ("ayah-marker", "Ayah markers", "The verse-end ornament with the number removed; <code>data-slot</code> is where the number goes.")]
import base64, io
try:
    from PIL import Image
except Exception: Image = None
def orig_data_uri(path, max_h=900):
    raw = path.read_bytes()
    if Image is not None and len(raw) > 250_000:
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        if im.height > max_h: im = im.resize((int(im.width * max_h / im.height), max_h), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=82); return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return "data:image/png;base64," + base64.b64encode(raw).decode()

sections = []
for asset, title, blurb in TYPES:
  panels = []
  for m in ORDER:
    d = A / {"surah-header": "surah-headers", "page-frame": "page-frames", "ayah-marker": "ayah-markers"}[asset] / m
    if not (d / "meta.json").exists(): continue
    meta = json.loads((d / "meta.json").read_text())
    uid = f"{asset}-{m}"
    color = load_svg(d / "color.svg", f"c-{uid}")
    mono = load_svg(d / "mono.svg", f"m-{uid}")
    line = load_svg(d / "line.svg", f"l-{uid}") if (d / "line.svg").exists() else ""
    orig = orig_data_uri(d / ("source.jpg" if (d / "source.jpg").exists() else "source.png"))
    pal = [p for p in meta["palette"]]
    chips = "".join(
        f'<label class="chip" data-cls="{p["class"]}"><input type="color" value="{"#ffffff" if p["hex"]=="none" else p["hex"]}" data-cls="{p["class"]}" data-default="{p["hex"]}">'
        f'<span class="sw" style="background:{"transparent" if p["hex"]=="none" else p["hex"]}"></span><span class="cn">{ "slot" if p["class"]=="slot" else p["class"]}</span><code>{p["hex"]}</code></label>'
        for p in pal)
    sx, sy, sw, sh = [float(v) for v in meta["slot"].split()]
    pv = meta.get("provenance", {})
    srcline = (f'<a href="{html.escape(pv.get("archive_url",""))}" target="_blank" rel="noopener">archive.org/{html.escape(pv.get("archive_item",""))}</a> · {html.escape(pv.get("file",""))} p.{pv.get("pdf_page")} · crop {" ".join(map(str, pv.get("crop_box_px",[])))} px · sha256 {pv.get("sha256","")[:12]}…'
               if pv else f"source {meta['source']} p.{meta['page']}")
    vbw = float(meta['viewBox'].split()[2])
    if asset == "surah-header":
        slot_html = '<svg viewBox="95.6 28.3 49.7 16.1" preserveAspectRatio="xMidYMid meet"><use href="#surah-name-glyph"/></svg>'
    elif asset == "ayah-marker":
        slot_html = '<span class="num">٢٨</span>'
    else:
        slot_html = ''
    folds = meta.get('symmetry',{}).get('folds','–')
    folds_txt = {4: '4-fold mirror', 2: 'left/right mirror', 'c2': '180° rotation', 1: 'no symmetry'}.get(folds, folds)
    panels.append(f"""
<section class="panel p-{asset}" data-m="{m}" data-asset="{asset}" data-slot="{meta['slot']}">
  <header class="ph">
    <div><h2>{NAMES.get(m, m)}</h2><p class="meta">{html.escape(meta.get('riwaya',''))} · viewBox {meta['viewBox']} · {len(pal)} groups · {folds_txt}</p><p class="meta src">{srcline}</p></div>
    <div class="seg" role="group" aria-label="Variant"><button class="on" data-v="color">Colour</button><button data-v="mono">Mono</button><button data-v="line">Line</button><button data-v="orig">Original</button></div>
  </header>
  <div class="stage">
    <div class="v v-color">{color}</div>
    <div class="v v-mono" hidden>{mono}</div>
    <div class="v v-line" hidden>{line}</div>
    <div class="v v-orig" hidden><img src="{orig}" alt="original scan crop"></div>
    <div class="name" style="left:{sx/vbw*100:.3f}%;top:{sy:.2f}%;width:{sw/vbw*100:.3f}%;height:{sh:.2f}%">{slot_html}</div>
  </div>
  <div class="ctl">
    <div class="chips chips-color">{chips}<button class="reset" type="button">Reset colours</button></div>
    <div class="chips chips-mono" hidden><label class="chip"><input type="color" value="#1d3f6e" data-mono><span class="sw" style="background:#1d3f6e"></span><span class="cn">ink</span><code>currentColor</code></label>
      <label class="chip"><input type="color" value="#ffffff" data-mslot data-default="none"><span class="sw" style="background:transparent"></span><span class="cn">slot</span><code>none</code></label></div>
    <div class="chips chips-orig" hidden><span class="hint">source scan crop, title included — what the pipeline started from</span></div>
    <div class="chips chips-line" hidden><label class="chip"><input type="color" value="#1e2126" data-line><span class="sw" style="background:#1e2126"></span><span class="cn">stroke</span><code>currentColor</code></label>
      <label class="chip"><input type="color" value="#ffffff" data-lslot data-default="none"><span class="sw" style="background:transparent"></span><span class="cn">slot</span><code>none</code></label>
      <span class="hint">stroke widths {" / ".join(str(v) for v in meta.get("stroke_widths_px", []))} px of source</span></div>
    <div class="act"><button class="copy" type="button">Copy SVG</button><span class="hint">copies the frame with the colours above (name text not included)</span></div>
  </div>
</section>""")
  sections.append(f'<h2 class="sec"><span>{title}</span> <small>{len(panels)} mushafs</small></h2><p class="lead">{blurb}</p>' + "".join(panels))

body = f"""<title>Mushaf Ornaments</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#f6f2e9;--bg2:#fffdf8;--ink:#1e2126;--mute:#6f6a62;--line:#ddd5c5;--acc:#1d5c8f;--acc2:#c98a2b;--chip:#efe9dc;--stage:#fbf9f3;--focus:#c98a2b}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#15171b;--bg2:#1d2025;--ink:#ece7db;--mute:#9a958b;--line:#2e3239;--acc:#6aa7d8;--acc2:#e0a94a;--chip:#23272d;--stage:#1a1d22}}}}
:root[data-theme="dark"]{{--bg:#15171b;--bg2:#1d2025;--ink:#ece7db;--mute:#9a958b;--line:#2e3239;--acc:#6aa7d8;--acc2:#e0a94a;--chip:#23272d;--stage:#1a1d22}}
*{{box-sizing:border-box}} [hidden]{{display:none!important}} .meta a{{color:var(--acc);text-decoration:none}} .meta a:hover{{text-decoration:underline}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:28px 24px 80px}}
h1{{font:700 34px/1.15 Amiri,Georgia,serif;margin:0;text-wrap:balance}} h1 span{{color:var(--acc)}}
.lead{{max-width:68ch;color:var(--mute);margin:8px 0 0}}
.top{{display:flex;flex-wrap:wrap;gap:20px;align-items:flex-end;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:20px;margin-bottom:26px}}
.global{{display:flex;flex-wrap:wrap;gap:14px;align-items:center}}
.global label{{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--mute)}}
.global input[type=text]{{font:18px Amiri,serif;padding:4px 10px;border:1px solid var(--line);border-radius:4px;background:var(--bg2);color:var(--ink);width:200px;direction:rtl}}
input[type=color]{{width:26px;height:26px;border:1px solid var(--line);border-radius:4px;padding:0;background:none;cursor:pointer}}
.panel{{background:var(--bg2);border:1px solid var(--line);border-radius:6px;margin:0 0 22px;overflow:hidden}}
.ph{{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;padding:16px 20px 10px}}
h2{{font:700 24px/1.2 Amiri,Georgia,serif;margin:0}} .meta{{margin:2px 0 0;color:var(--mute);font-size:12.5px;font-family:"IBM Plex Mono",monospace}}
.seg{{display:flex;border:1px solid var(--line);border-radius:4px;overflow:hidden;flex:none}} .seg button{{font:500 13px "IBM Plex Sans";padding:6px 12px;border:0;background:transparent;color:var(--mute);cursor:pointer}} .seg button.on{{background:var(--acc);color:#fff}}
.stage{{position:relative;margin:0 20px;background:var(--stage-bg,var(--stage));border:1px solid var(--line);border-radius:4px;padding:18px 3%}}
.stage svg,.stage img{{width:100%;height:auto;display:block}} .p-page-frame .stage{{padding:0;width:min(100%,480px);margin:0 auto;border:0;background:transparent}} .p-page-frame .stage svg,.p-page-frame .stage img{{width:100%}} .p-ayah-marker .stage{{padding:0;width:200px;margin:0 auto;border:0;background:transparent}} .p-ayah-marker .stage svg,.p-ayah-marker .stage img{{width:100%}} .num{{font:700 var(--nsz,28px) Amiri,serif;color:var(--name-color,#1e2126);line-height:1}} h2.sec{{font:700 28px/1.2 Amiri,Georgia,serif;margin:34px 0 4px;border-bottom:1px solid var(--line);padding-bottom:8px}} h2.sec small{{font:13px 'IBM Plex Sans';color:var(--mute)}} .v-mono{{color:#1d3f6e}} .v-line{{color:#1e2126}}
.name{{position:absolute;display:flex;align-items:center;justify-content:center;pointer-events:none;box-sizing:border-box}}
.stage .name{{left:calc(3% + var(--nx,0%) * 0.94)}}
.name svg{{width:56%;height:58%;display:block;fill:var(--name-color,#1e2126)}}
.ctl{{padding:12px 20px 16px;display:flex;flex-direction:column;gap:10px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}}
.chip{{display:inline-flex;align-items:center;gap:7px;background:var(--chip);border-radius:4px;padding:4px 8px 4px 4px;font-size:12.5px;cursor:pointer}}
.chip .sw{{width:16px;height:16px;border-radius:3px;border:1px solid var(--line);background-image:linear-gradient(45deg,#bbb 25%,transparent 25%,transparent 75%,#bbb 75%),linear-gradient(45deg,#bbb 25%,transparent 25%,transparent 75%,#bbb 75%);background-size:8px 8px;background-position:0 0,4px 4px}}
.chip .sw[style*="background:#"]{{background-image:none}} .chip .cn{{font-weight:500}} .chip code{{font:12px "IBM Plex Mono",monospace;color:var(--mute)}}
button.reset,button.copy{{font:500 13px "IBM Plex Sans";padding:6px 12px;border:1px solid var(--line);border-radius:4px;background:var(--bg2);color:var(--ink);cursor:pointer}} button.copy{{border-color:var(--acc);color:var(--acc)}}
button.copy.done{{background:var(--acc);color:#fff}} .act{{display:flex;gap:10px;align-items:center}} .hint{{font-size:12px;color:var(--mute)}}
button:focus-visible,input:focus-visible{{outline:2px solid var(--focus);outline-offset:2px}}
.how{{margin-top:36px;border-top:1px solid var(--line);padding-top:20px;color:var(--mute);max-width:75ch}} .how code{{font-family:"IBM Plex Mono",monospace;font-size:13px;color:var(--ink)}}
.how h3{{font:700 20px Amiri,serif;color:var(--ink);margin:0 0 6px}}
@media (max-width:640px){{.ph{{flex-direction:column}} .stage{{margin:0 10px;padding:10px 2%}} .name span{{font-size:14px}}}}
</style>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs><g id="surah-name-glyph"><path fill-rule="evenodd" d="M125.43 32.43c.37-.23.88-.59 1.56-1.4-.11-.05-.34-.15-.52-.28-.49-.5.39-2.03.98-1.28.33.54.22 1.08.18 1.22.19.16.36.38.22.77-.02.06-.06.08-.08.08-.1.01-.24-.23-.42-.35-.09.18-.37.69-.82 1.03-1.06.77-1.9.88-1.91.88-.49-.13.46-.43.81-.67zM113.26 31.05c.23.12.19-.11.26-.16.44.34.72.86.9 1.44.05.19.26.19.3-.04.15-.59-.04-1.69.43-2.08.27-.07.47.41.67.4.15-.13.21-.56.14-.8-.02-.04-.29-.42-.6-.45-.76.15-.75 1.29-.85 1.99-.13-.51-1.68-2.49-1.73-1.2-.02.58-.02.5.48.9zM124.09 39.69c.08.71.15 1.33.15 1.69-.02.22.14.24.2.09.33-.96.26-1.99.04-3.76-.03-.15-.72-5.12-.85-6.05 1.12 1.13.52-.11.01-1.33-.23-.46-.4-1.26-.56-.91-.04.12-.3.76-.3.79 0 .05.07.36.1.44.29 2.27.96 6.92 1.21 9.04zM135.75 30.85c.08.09.33.25.43.34.08.07.21.03.22-.07 0-.05.04-.12.08-.06.41.37.69.84.86 1.42.05.19.26.18.3-.04.15-.59-.04-1.69.43-2.08.26-.07.48.42.67.4.14-.11.21-.54.14-.8-.02-.04-.3-.42-.61-.45-.76.15-.75 1.3-.85 1.99-.11-.48-1.6-2.4-1.73-1.29-.04.39.09.59-.04.55zM101.8 31.35c.01-.08.05-.11.1-.05.46.44.69.97.81 1.34.02.07.08.12.14.12.05 0 .12-.02.12-.16.15-.57-.04-1.57.41-1.97.26-.08.4.38.58.4.04 0 .08-.01.12-.09.18-.46.14-.92-.51-1.11-.75.14-.75 1.19-.82 1.86-.31-.87-1.94-2.56-1.59-.58.13.1.6.53.64.24zM141.37 29.99h-.04c.23-.44.72-.66.98-.28.33.54.22 1.08.18 1.22.19.16.36.38.23.77-.07.17-.19.06-.26-.06-.06-.04-.21-.3-.26-.17-.13.28-.16.37-.77.89-.58.51-1.7 1.27-3.15 1.72-.19-.02-.14-.15 0-.26 1.08-.69 2.57-1.36 3.6-2.55-.11-.05-.34-.15-.52-.28-.22-.18-.13-.73.01-1zM110.28 30.79c-.17-.56.01-1.12.14-1.21.09-.18.21-.14.27.1.83 3.4.65 5.5 1.28 8.93.75 3.58 4.71 1.48 5.89.93-.24-.62-.26-1.24-.26-1.42.28-2.37 2.18-1.76 2.22.1-.02 1.1-.5 1.43-.82 1.69.45.61 1.45.48 1.46.48 1.33-.24 1.2-.56 1.16-1.12-.03-.5-1.23-8.66-1.3-9.15 0-.01.23-.6.27-.7.01-.02.03-.09.09-.09.19.12.19.4.44.91.34.92 1.03 2.06.46 1.81-.07-.04-.29-.26-.43-.39.09.59.43 2.78.7 4.53.27 2.17.53 2.75.25 4.03-.37.98-1.18 1.17-1.52 1.21-1.58.19-2.03-.56-2.27-.97-.09-.13-1.34.66-1.81.76-2.93 1.14-5.15.46-5.23-3.23-.16-1.57-.58-5.53-.99-7.2zM133.68 30.24c.23-.08.5-.52.39-.68-.23-.08-4.22 2.4-4.5 2.5-.23.12-.25.27-.31.44-.04.09-.05.22.07.22.55-.2 4.26-2.47 4.35-2.48zM107.8 31.68c.14 0 .34-.07.48-.53.03-.14.08-.26-.02-.33-.06-.02-.1.05-.12.09-.4.71-.68-.24-.38-.86.08-.23.22-.4.09-.51-.02-.01-.09-.02-.17.11-.14.23-.77 1.81.12 2.03zM142.23 30.78c.05-.15-.15-1.19-.6-.44-.16.2.39.31.6.44zM127.34 30.51c0-.07.03-.44-.2-.67-.1-.07-.2-.07-.4.23-.07.1 0 .17.13.23.16.08.44.22.47.21zM100.29 32.69c0-.19-.17-.14-.2-.01-.46.95-.95-.21-.58-1.11.08-.29.25-.53.1-.66-.03-.01-.11-.02-.19.15-.15.33-.47 1.08-.34 1.98.2.97 1.17.8 1.21-.35zM112.56 35.88c.45-.17 6.8-3.67 7.07-3.86.24-.1.61-.94.04-.62-.17.1-6.63 3.62-6.84 3.72-.33.1-.33.47-.35.67 0 .07.03.09.08.09zM107.5 33.54h.11l.35-.52.69.51c.01.02.11.01.12.01l.45-.63c.02 0 .01-.11.01-.12l-.81-.6h-.11l-.35.52-.7-.51c-.01-.02-.11-.01-.12-.01l-.45.63c-.02 0-.01.11-.01.12zM101.83 34.42c-.01.12-.1.26-.01.35.36 0 .89-.41 1.96-.87.92-.44 1.88-.89 1.95-.93.23-.11.33-.3.39-.5.07-.17-.01-.24-.24-.13-.16.07-2.35 1.13-3.02 1.45-.32.2-.97.3-1.03.63zM134.64 35.02c.11 0 .36-.06.48-.57.03-.15.09-.32-.03-.38-.07-.01-.09.08-.1.11-.1.29-.35.36-.48.1-.03-.06-.16-.38.07-1.07.04-.25.21-.44.08-.56-.07-.06-.2.13-.23.26-.18.34-.65 1.95.21 2.11zM142.22 33.03c-.26.32-.44.91-.45 1.67.02.56.67.89.87.02.04-.15.09-.3-.04-.35-.06 0-.08.08-.09.11-.1.26-.33.34-.44.1-.17-.22.15-1.28.2-1.33.05-.1.06-.22-.05-.22zM127.89 33.14h.11l.81.6c0 .01.01.12-.01.12l-.45.63c-.01 0-.12.01-.12-.01l-.7-.51-.35.52h-.11l-.8-.6c0-.01-.01-.12.01-.12l.45-.62c.01 0 .12-.01.12.01l.7.51zM97.45 37.91c.34 0 .58-.36.72-1.08.12-.5-.07-.83-.2-.39-.49 1.36-1.29-.05-.81-1.79.07-.42.27-.87.08-1-.16-.02-.18.27-.24.42-.17.54-.98 3.48.45 3.84zM143.49 37.11l-.01-.02.01-.02c.1-.24.08-.68.28-.83.25.08.47.52.54 1.17 0 .5-.02.65-.07.75-.07.21-.3.86-1.28.66-.27-.03-.75-.16-.97-.65-.27.39-.88 1.21-1.98 1.05-.27-.04-1.03-.36-1.11-1.29-.23.19-.9.72-1.27.93.03.41-.02.81-.17 1.23-.17.49-2.24 2.78-3.89 3.15-1.32.39-2.85-.2-2.81-1.89 0-.36.02-.7.05-1.03-1.24.94-2.4 1.5-3.23 1.94-.74.37-3.51.81-3.54.81-.33.06-.42-.1-.2-.23 3.64-1.38 6.68-3.11 8.27-4.82.04-.06.03-.17-.04-.31-.28-.46-1.1-2.11-1.27-2.62-.11-.22-.01-.35.03-.63.04-.23.07-.57.29-.31.12.12.96 1 1.04 1.07.29.32-.23.25-.42.26.14.24.55.96.7 1.27.6 1.28-.25 2.45-1.24 3.24-.22.82.12 2.39 1.5 2.34.38 0 1.2.05 2.98-1.36.4-.33.89-.75 1.3-1.33.13-.2.27-.54.01-.52-.66.15-2.23.61-2.5-.48-.14-2.06 1.36-3.1 2.82-.78.35-.16.93-.51 1.55-1.01.17-.12.31-.21.4-.16.23.22-.16.85.39 1.38.78.49 1.97.15 2.55-1.4.09-.21.21-.27.29-.24.26.17-.35.84-.1.99.18.19.65.48 1.2.42.16-.03.25-.09.19-.23-.09-.17-.29-.5-.29-.5zM97.34 40.2c-.03-.27.03-1 .1-1.19.02-.14-.02-.26-.11-.28-.26-.14-.91 3 .77 3.98.45.22.96.19 1.24-.36.31-.75.75-2.14 1.56-2.66.69-.38.93-.31 1.12.21 1.26 3.18 4.2.4 6.92-.54.49-.09 1.42-.17 1.46-.17l.01-.02c.03-.05.13-.21.23-.38.12-.24.32-.41.27-.57-.73-.1-1.81.06-2.75-.03-.85-.06-1.99-.2-2.36-.25.28-.22 1.07-.89 1.4-1.52.11-.23.47-.72.65-.78.78-.34.23 1.18.71 1.32.3-.17.32-.97.22-1.65-.04-.16-.13-.57-.42-.71-.44-.14-.82.31-1.22.86-.35.58-.67 1.19-1.59 1.69-1.06.6-1.66.74-1.83 1.54-.05.14.01.29.18.23.18-.14 2.02.08 3.23.26-.36.25-1.46.93-2.63 1.16-.56.13-1.37.19-1.86-.81-.21-.42-.42-1.27-1.3-.96-.84.34-1.5 1.02-1.81 1.88-.26.73-.57 1.51-.92 1.51-.35-.03-1.18-.53-1.27-1.76zM117.48 35.11c-.02 0-.01.11-.01.12l.81.6h.11c.01-.02.45-.62.46-.64v-.11l-.81-.6h-.11zM127.51 36.58c.32-.36 1.21-1.75 1.41-1.77.14.2-.2.99-.29 1.19-.06.09-.54.75-.67.93.19.11.83.49 1.01.76.36.49.17.91.07 1.28-.23.73-1.24 1.19-1.58 1.28-1.66.49-.89-2.41-.45-2.95-.44-.32-1.09-.88-1.37-1.11-.17-.11-.04-.57-.06-.95.01-.12.12-.15.21-.08.12.08 1.39.46 1.37.68-.05.18-.21.11-.43.19zM99.64 35.56c-.01.02-.45.62-.46.64v.11l.81.6h.11l.36-.52.7.51c.01.02.11.01.12.01l.45-.63c.02 0 .01-.11.01-.12l-.81-.6h-.11l-.35.52c-.02-.01-.69-.5-.71-.52zM115.09 36.33c-.14.33-.47 1.03-.34 1.94.11.66.88 1.07 1.17-.06.03-.18.09-.33-.03-.41-.18 0-.17.44-.44.45-.67-.11-.36-1.24-.13-1.82.08-.23-.07-.4-.23-.1zM136.46 38.16c-.6-.8-1.31-.37-1.41-.27-.31.57 1.46.33 1.41.27zM118.05 38.26c.07.2.4 1.07.4 1.07.13-.07 1.07-.6.87-1.01-.2-.4-.5-.84-.91-.67-.39.17-.42.41-.36.61zM127.5 37.53c-.22.45-1.33 1.76-.13 1.73.2 0 .94-.37 1.27-.67.37-.29-.87-.92-1.14-1.06zM142.05 40.28c-.3.6-.28 1.08-1.29.65-.14-.06-.38-.16-.68.17-.63.58-1.12.74-1.74.95-.48.1-1.19.55-.42.47.41-.03 1.36-.09 1.92-.71.18-.19.26-.43.72-.26.39.17.8.49 1.38-.31.37.2.95.12 1-.35.13-.3.11-.69.14-.92.02-.2-.16-.37-.23-.12-.12.35-.11.44-.07.73-.08.06-.34.2-.59.04.03-.07.05-.18.06-.24.04-.15-.09-.3-.2-.1zM111.1 40.18c-1.29.53-3.87 1.52-3.94 1.59-.28.11-.28.25-.36.46-.03.04-.05.18.05.17.57-.23 3.87-1.54 4.03-1.62.25-.01.63-.77.22-.6zM117.58 41.16c-.11.24-.69 1.77.14 1.92.12 0 .33-.07.45-.51.04-.18.09-.27-.04-.33-.14 0-.18.34-.36.33-.35-.01-.22-.87 0-1.41.06-.33-.15-.2-.19 0zM102.91 41.7c-.08.03-.63.22-1.15.41-.73.31-1.24.29-1.43.66-.11.25-.13.44.17.3.13-.06 1.98-.69 2.22-.77.13-.07.22-.11.29-.26.11-.19.2-.45-.1-.34z"/></g></defs></svg>
<div class="wrap">
<div class="top">
  <div><h1>Mushaf <span>Ornaments</span></h1><p class="lead">Surah headers, page frames and ayah markers vectorized from eight printed mushafs — colour, mono and line-art variants. Every printed ink is one recolourable group; each asset's slot (name, text area, number) is transparent by default and can be filled too. Pick colours, then copy the SVG.</p></div>
  <div class="global">
    <label>Background <input type="color" id="bg" value="#fbf9f3"></label>
    <label>Name colour <input type="color" id="nc" value="#1e2126"></label>
    <label><input type="checkbox" id="shownm" checked> show name in slot</label>
  </div>
</div>
{''.join(sections)}
<div class="how"><h3>Using the files</h3>
<p>Every file records where it came from: <code>data-source-file</code> / <code>-page</code> / <code>-box</code> / <code>-url</code> on the root and a full JSON record in <code>&lt;metadata&gt;</code> (archive.org item, PDF sha256, crop box, pipeline commit). <code>assets/catalog.json</code> lists all of it in one place.</p>
<p>Each frame is traced once as a quadrant and mirrored with <code>&lt;use&gt;</code> (<code>data-symmetry="4"</code>), so it is exactly symmetric and small. Linework is drawn as constant-width strokes (<code>&lt;g class="line" stroke=…&gt;</code>, widths in <code>meta.json</code>) with the fills extended underneath — no gaps at any zoom. <code>line.svg</code> is the strokes alone.</p>
<p><code>color.svg</code>: one <code>&lt;g class="cN"&gt;</code> per printed colour (bottom to top, black linework last) plus <code>&lt;g class="slot" fill="none"&gt;</code>. Recolour with CSS <code>.c2{{fill:#…}}</code> or by setting the group's <code>fill</code>. <code>mono.svg</code>: one <code>&lt;g class="ink" fill="currentColor"&gt;</code> — set CSS <code>color</code>. Both carry <code>data-slot="x y w h"</code> in viewBox units (height = 100) so an app can place the surah name exactly where the calligrapher left room for it.</p></div>
</div>
<script>
(function(){{
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
function setFill(svg,cls,val){{ $$('g.'+cls,svg).forEach(g=>g.setAttribute(cls==='line'?'stroke':'fill',val)); }}
function applyGlobal(){{
  const bg=$('#bg').value, nc=$('#nc').value, show=$('#shownm').checked;
  document.documentElement.style.setProperty('--stage-bg',bg);
  document.documentElement.style.setProperty('--name-color',nc);
  $$('.panel .name').forEach(n=>n.style.display=show?'':'none');
}}
function fitNames(){{ $$('.panel .name .num').forEach(n=>{{ const h=n.parentElement.getBoundingClientRect().height; n.style.fontSize=(h*0.62)+'px'; }}); }}
$$('#bg,#nc,#shownm').forEach(i=>i.addEventListener('input',applyGlobal));
addEventListener('resize',fitNames);
$$('.panel').forEach(p=>{{
  const svgC=$('.v-color svg',p), svgM=$('.v-mono svg',p);
  $$('.seg button',p).forEach(b=>b.addEventListener('click',()=>{{
    $$('.seg button',p).forEach(x=>x.classList.toggle('on',x===b));
    const v=b.dataset.v;
    for(const k of ['color','mono','line','orig']){{ $('.v-'+k,p).hidden=(k!==v); $('.chips-'+k,p).hidden=(k!==v); }}
    $('.name',p).style.visibility = v==='orig' ? 'hidden' : '';
  }}));
  $$('.chips-color input[type=color]',p).forEach(i=>i.addEventListener('input',e=>{{
    setFill(svgC,i.dataset.cls,i.value); const sw=i.parentElement.querySelector('.sw'); sw.style.background=i.value; sw.style.backgroundImage='none'; i.parentElement.querySelector('code').textContent=i.value;
  }}));
  $('.reset',p).addEventListener('click',()=>$$('.chips-color input[type=color]',p).forEach(i=>{{
    const d=i.dataset.default; setFill(svgC,i.dataset.cls,d); i.value=d==='none'?'#ffffff':d; const sw=i.parentElement.querySelector('.sw');
    sw.style.background=d==='none'?'transparent':d; sw.style.backgroundImage=d==='none'?'':'none'; i.parentElement.querySelector('code').textContent=d; }}));
  $('[data-mono]',p).addEventListener('input',e=>{{ $('.v-mono',p).style.color=e.target.value; e.target.parentElement.querySelector('.sw').style.background=e.target.value; }});
  const svgL=$('.v-line svg',p);
  if(svgL){{ $('[data-line]',p).addEventListener('input',e=>{{ $('.v-line',p).style.color=e.target.value; e.target.parentElement.querySelector('.sw').style.background=e.target.value; }});
    $('[data-lslot]',p).addEventListener('input',e=>{{ setFill(svgL,'slot',e.target.value); const sw=e.target.parentElement.querySelector('.sw'); sw.style.background=e.target.value; sw.style.backgroundImage='none'; e.target.parentElement.querySelector('code').textContent=e.target.value; }}); }}
  $('[data-mslot]',p).addEventListener('input',e=>{{ setFill(svgM,'slot',e.target.value); const sw=e.target.parentElement.querySelector('.sw'); sw.style.background=e.target.value; sw.style.backgroundImage='none'; e.target.parentElement.querySelector('code').textContent=e.target.value; }});
  $('.copy',p).addEventListener('click',async()=>{{
    if($('.v-orig',p).hidden===false){{ return; }}
    const mono=$('.v-mono',p).hidden===false, lineV=$('.v-line',p).hidden===false; const src=lineV?svgL:(mono?svgM:svgC); const c=src.cloneNode(true); c.removeAttribute('id');
    if(mono){{ const ink=$('.v-mono',p).style.color; if(ink) $$('g.ink',c).forEach(g=>g.setAttribute('fill',ink)); }}
    if(lineV){{ const ink=$('.v-line',p).style.color; if(ink) $$('g.line',c).forEach(g=>g.setAttribute('stroke',ink)); }}
    c.innerHTML=c.innerHTML.replace(/q-[a-z]-[a-z0-9-]+/g,'q');
    const txt='<?xml version="1.0" encoding="UTF-8"?>\\n'+c.outerHTML; const b=$('.copy',p);
    try{{ await navigator.clipboard.writeText(txt); b.textContent='Copied'; }}catch(err){{ b.textContent='Copy blocked — select the SVG in the page source'; }}
    b.classList.add('done'); setTimeout(()=>{{b.textContent='Copy SVG';b.classList.remove('done')}},1600);
  }});
}});
applyGlobal(); if(document.fonts) document.fonts.ready.then(fitNames);
}})();
</script>
"""
out_body.write_text(body)
full = "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n" + body.split("<style>")[0] + "<style>" + body.split("<style>",1)[1].split("</style>")[0] + "</style>\n</head>\n<body>\n" + body.split("</style>",1)[1] + "\n</body>\n</html>\n"
out_full.write_text(full)
print("panels", len(panels), "body bytes", len(body))
