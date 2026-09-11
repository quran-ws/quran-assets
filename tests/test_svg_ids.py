"""Every `id` in the asset tree is unique across files.

Consumers inline several assets into one document — a header, a frame and a marker at the
least — and an id shared between files makes every `<use href>` on the page resolve to
whichever copy came first. That is what the demo's thumbnails looked like the day this was
found: eight different frames, all drawn as the first one.
"""
import re

from qa import ROOT

FILES = sorted((ROOT / "assets").rglob("*.svg"))


def test_no_id_is_shared_between_files():
    owners = {}
    for f in FILES:
        for i in re.findall(r'\sid="([^"]+)"', f.read_text()):
            assert i not in owners, f"id {i!r} in both {owners[i]} and {f.relative_to(ROOT)}"
            owners[i] = f.relative_to(ROOT)
    assert owners, "no ids found at all — the symmetry output changed shape"


def test_every_use_points_inside_its_own_file():
    for f in FILES:
        text = f.read_text()
        ids = set(re.findall(r'\sid="([^"]+)"', text))
        for ref in re.findall(r'href="#([^"]+)"', text):
            assert ref in ids, f"{f.relative_to(ROOT)} uses #{ref}, which it does not define"
