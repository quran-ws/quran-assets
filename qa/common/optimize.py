"""Optimize SVGs and refresh path counts to describe the delivered files."""
import os
from pathlib import Path
import shutil
import subprocess
import json
import xml.etree.ElementTree as ET

from qa import ROOT
NS = "{http://www.w3.org/2000/svg}"


def refresh_counts(directory):
    metadata_path = directory / "meta.json"
    metadata = json.loads(metadata_path.read_text())
    color = ET.parse(directory / "color.svg").getroot()
    metadata["viewBox"] = color.get("viewBox")
    groups = color.iter(NS + "g")
    counts = {g.get("class"): len(list(g.iter(NS + "path"))) for g in groups if g.get("class")}
    for color in metadata["palette"]:
        color["paths"] = counts.get(color["class"], 0)
    mono = ET.parse(directory / "mono.svg").getroot()
    metadata["mono_paths"] = sum(len(list(g.iter(NS + "path"))) for g in mono.iter(NS + "g") if g.get("class") == "ink")
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")


def main():
    executable = os.environ.get("SVGO") or shutil.which("svgo")
    local = ROOT / "node_modules/.bin/svgo"
    if executable is None and local.exists():
        executable = str(local)
    if executable is None:
        raise SystemExit("SVGO is missing: install dependencies or set SVGO to its executable path.")
    for metadata in sorted((ROOT / "assets").glob("*/*/meta.json")):
        for svg in sorted(metadata.parent.glob("*.svg")):
            subprocess.run([executable, "-q", "--config", str(Path(__file__).resolve().parent / "svgo.config.mjs"), str(svg), "-o", str(svg)], check=True)
        refresh_counts(metadata.parent)
    print("Optimized SVGs and refreshed metadata path counts.")


if __name__ == "__main__":
    main()
