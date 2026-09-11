"""`python -m qa validate` — the checks CI runs before anything ships.

Three groups, all of them cheap and offline:
  * catalog.json against tests/catalog.schema.json, and every path in it exists;
  * the SVG contract from docs/CONVENTIONS.md, checked on the delivered files;
  * licensing: no asset may claim `confirmed` without evidence in sources/licenses/.
Geometry and rendering quality are not checked here — that is `qa quality`.
"""
import json
import re
import xml.etree.ElementTree as ET

from jsonschema import Draft202012Validator

from qa import ROOT

NS = "{http://www.w3.org/2000/svg}"
SCHEMA = ROOT / "tests/catalog.schema.json"
COLOUR_GROUPS = {"slot", "line", "ink"}


def _same_box(a, b, tolerance=0.01):
    """SVGO rounds coordinates, so compare the numbers, not the strings."""
    if not a or not b:
        return False
    first, second = [float(v) for v in a.split()], [float(v) for v in b.split()]
    return len(first) == len(second) == 4 and all(abs(x - y) <= tolerance for x, y in zip(first, second))


def _classes(svg_root):
    return [g.get("class") for g in svg_root.iter(NS + "g") if g.get("class")]


def check_catalog(catalog, problems):
    validator = Draft202012Validator(json.loads(SCHEMA.read_text()))
    for error in sorted(validator.iter_errors(catalog), key=lambda e: list(e.path)):
        problems.append(f"catalog{list(error.path)}: {error.message}")
    if catalog.get("count") != len(catalog.get("assets", [])):
        problems.append("catalog: count does not match the number of entries")
    ids = [a["id"] for a in catalog.get("assets", [])]
    if len(set(ids)) != len(ids):
        problems.append("catalog: duplicate asset ids")


def check_svg(asset, problems):
    """The SVG contract: one recolourable group per palette entry, declared slot, no fixed size."""
    for variant, relative in asset["variants"].items():
        path = ROOT / relative
        if not path.exists():
            problems.append(f"{asset['id']}: missing {relative}")
            continue
        root = ET.parse(path).getroot()
        if not _same_box(root.get("viewBox"), asset["viewBox"]):
            problems.append(f"{asset['id']}/{variant}: viewBox differs from the catalog")
        if root.get("width") or root.get("height"):
            problems.append(f"{asset['id']}/{variant}: width/height must be left to CSS")
        if asset["units"] == "normalized-100" and not root.get("viewBox", "").endswith(" 100"):
            problems.append(f"{asset['id']}/{variant}: normalized-100 assets must have viewBox height 100")
        for attribute in ("data-style", "data-lineage", "data-asset", "data-variant"):
            if not root.get(attribute):
                problems.append(f"{asset['id']}/{variant}: root is missing {attribute}")
        if root.get("data-style") != asset["style"]:
            problems.append(f"{asset['id']}/{variant}: data-style is {root.get('data-style')!r}, not the style id")
        # A font-derived asset has no mushaf, so data-mushaf is scan-only rather than universal.
        if asset["lineage"] == "scan" and not root.get("data-mushaf"):
            problems.append(f"{asset['id']}/{variant}: a scan asset must carry data-mushaf")
        if asset["lineage"] != "scan" and root.get("data-mushaf"):
            problems.append(f"{asset['id']}/{variant}: data-mushaf on a {asset['lineage']}-derived asset")
        if asset["slots"] and not root.get("data-slot"):
            problems.append(f"{asset['id']}/{variant}: root is missing data-slot")
        classes = _classes(root)
        for group in root.iter(NS + "g"):
            cls = group.get("class")
            if cls and group.get("data-part") != cls:
                problems.append(f"{asset['id']}/{variant}: <g class=\"{cls}\"> is missing a matching data-part")
        # A slot *group* is a scan thing. A traced cartouche leaves its middle empty, so a
        # transparent group there is real geometry the app can fill. A font marker's interior
        # is painted solid by its base fill, so a rect behind the artwork is invisible and one
        # in front would cover it -- measured, not assumed: 0 of 5 probed designs showed any of
        # it. Those ship the number box as data-slot and catalog slots[] only.
        if asset["lineage"] == "scan" and "slot" not in classes and asset["slots"]:
            problems.append(f"{asset['id']}/{variant}: no slot group")
        if variant == "color":
            expected = {p["name"] for p in asset["palette"]}
            found = {c for c in classes if c in expected or c.startswith("c")}
            if found != expected:
                problems.append(f"{asset['id']}/color: groups {sorted(found)} do not match palette {sorted(expected)}")
        if variant == "mono" and "ink" not in classes:
            problems.append(f"{asset['id']}/mono: no ink group")
        if variant == "line" and "line" not in classes:
            problems.append(f"{asset['id']}/line: no line group")


def evidence_for(asset):
    """Where a 'confirmed' claim has to be backed up, and whether it is.

    Per style for a scan asset -- written permission is per mushaf. Per source family for a
    font one: one OFL text covers every weight and every design taken from that family, and
    40 copies of the same licence would be 40 chances to let them drift apart. Every source
    must be covered, so one unverified family in a multi-source outline cannot hide behind
    a verified sibling.
    """
    directory = ROOT / "sources/licenses"
    if asset["lineage"] == "scan":
        return [f"{asset['style']}.txt"], (directory / f"{asset['style']}.txt").exists()
    wanted = [f"{re.sub(r'[^a-z0-9]+', '', s['family'].lower())}.txt" for s in asset["sources"] if s.get("family")]
    wanted = sorted(set(wanted))
    return wanted, bool(wanted) and all((directory / name).exists() for name in wanted)


def check_license(asset, problems):
    licence = asset["license"]
    wanted, satisfied = evidence_for(asset)
    if licence["status"] == "confirmed" and not satisfied:
        missing = ", ".join(n for n in wanted if not (ROOT / "sources/licenses" / n).exists()) or "no source family named"
        problems.append(f"{asset['id']}: license claims 'confirmed' but sources/licenses/{{{missing}}} is missing")
    if licence["status"] != "confirmed" and licence.get("redistributable"):
        problems.append(f"{asset['id']}: redistributable is only allowed once the license is confirmed")
    if not asset["sources"]:
        problems.append(f"{asset['id']}: no source recorded, so the license cannot be traced")


def main():
    catalog = json.loads((ROOT / "catalog.json").read_text())
    problems = []
    check_catalog(catalog, problems)
    for asset in catalog.get("assets", []):
        if (ROOT / asset.get("source_crop", "")).exists() is False:
            problems.append(f"{asset['id']}: missing {asset.get('source_crop')}")
        check_svg(asset, problems)
        check_license(asset, problems)
    for problem in problems:
        print("FAIL:", problem)
    print(f"{len(catalog.get('assets', []))} assets checked, {len(problems)} problems")
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
