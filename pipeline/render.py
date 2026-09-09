"""Step 1: get the page raster out of a source PDF.

Scanned mushafs embed one image per page; `pdfimages` pulls it at native resolution
(no resampling). If the page has no single embedded image (vector PDF), fall back to
rendering with pdftoppm at `dpi`.
"""
import subprocess, shutil, glob, os
from pathlib import Path

def page_image(pdf: Path, page: int, out_dir: Path, dpi: int = 300, force: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{pdf.stem}_p{page:04d}.png"
    if out.exists() and not force:
        return out
    tmp_prefix = out_dir / f"_tmp_{pdf.stem}_p{page}"
    subprocess.run(["pdfimages", "-f", str(page), "-l", str(page), "-png", str(pdf), str(tmp_prefix)], check=True)
    imgs = sorted(glob.glob(f"{tmp_prefix}-*.png"))
    if len(imgs) == 1:
        shutil.move(imgs[0], out)
    else:
        for f in imgs: os.remove(f)
        subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(dpi), "-png", "-singlefile",
                        str(pdf), str(out.with_suffix(""))], check=True)
    return out
