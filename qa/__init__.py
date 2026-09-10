"""`qa` — the quran-assets toolchain.

One CLI for every lineage (see docs/PLAN.md): `python -m qa build|catalog|optimize|
preview|demo|quality|validate|dist`. Scan-derived stages live in `qa.scan`, everything
that works on the finished assets in `qa.common`.
"""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = Path(__file__).resolve().parent
JOBS_DIR = PKG / "jobs"
SOURCES = Path(os.environ.get("QA_SOURCES_DIR", ROOT / "sources"))  # mushaf PDFs, not committed

# `<type>` in assets/<type>/<style> for each job's asset name, and back.
TYPE_DIR = {"surah-header": "surah-headers", "page-frame": "page-frames", "ayah-marker": "ayah-markers"}
ASSET_OF_TYPE = {v: k for k, v in TYPE_DIR.items()}


def load_jobs():
    """Merge qa/jobs/<type>.json into one config: {asset_types: {...}, jobs: [...]}.

    One file per asset type keeps a contributor's diff to the type they are adding.
    """
    asset_types, jobs = {}, []
    for path in sorted(JOBS_DIR.glob("*.json")):
        cfg = json.loads(path.read_text())
        asset = cfg["asset"]
        asset_types[asset] = cfg["defaults"]
        for job in cfg["jobs"]:
            jobs.append({"asset": asset, **job})
    return {"asset_types": asset_types, "jobs": jobs}


def git_rev() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "uncommitted"
