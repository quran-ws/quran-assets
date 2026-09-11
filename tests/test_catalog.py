"""The catalog and the SVG contract are the public interface: check the shipped files."""
import json

import pytest
from jsonschema import Draft202012Validator

from qa import ROOT, TYPE_DIR, load_jobs, split_style, style_id
from qa.common import validate

CATALOG = json.loads((ROOT / "catalog.json").read_text())
SCHEMA = json.loads((ROOT / "tests/catalog.schema.json").read_text())


def test_schema_itself_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


def test_catalog_matches_the_schema():
    errors = [f"{list(e.path)}: {e.message}" for e in Draft202012Validator(SCHEMA).iter_errors(CATALOG)]
    assert errors == []


def test_every_job_produced_an_entry():
    jobs = load_jobs()["jobs"]
    expected = {f"{TYPE_DIR[j['asset']]}/{style_id('scan', j['mushaf'])}" for j in jobs}
    assert expected <= {a["id"] for a in CATALOG["assets"]}


def test_every_style_follows_the_naming_standard():
    """`<lineage>-<name>`, and the prefix agrees with the catalog's own lineage field."""
    for asset in CATALOG["assets"]:
        lineage, name = split_style(asset["style"])
        assert lineage == asset["lineage"], asset["id"]
        assert name, asset["id"]


def test_shipped_svgs_follow_the_contract():
    problems = []
    for asset in CATALOG["assets"]:
        validate.check_svg(asset, problems)
    assert problems == []


def test_licenses_are_traceable():
    problems = []
    for asset in CATALOG["assets"]:
        validate.check_license(asset, problems)
    assert problems == []


@pytest.mark.parametrize("asset", CATALOG["assets"], ids=lambda a: a["id"])
def test_slot_lies_inside_the_viewbox(asset):
    _, _, width, height = (float(v) for v in asset["viewBox"].split())
    for slot in asset["slots"]:
        assert 0 <= slot["x"] and 0 <= slot["y"]
        assert slot["x"] + slot["w"] <= width + 0.01
        assert slot["y"] + slot["h"] <= height + 0.01


def test_confirmed_licenses_may_be_redistributed_only_with_evidence():
    asset = json.loads(json.dumps(CATALOG["assets"][0]))
    asset["license"] = {"id": "CC-BY-4.0", "status": "confirmed", "redistributable": True}
    asset["style"] = "a-style-with-no-evidence-file"
    problems = []
    validate.check_license(asset, problems)
    assert len(problems) == 1 and "sources/licenses" in problems[0]
