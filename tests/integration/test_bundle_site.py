"""The real course site bundles into one self-contained page."""

import json
import re
from pathlib import Path

import pytest

from practicum.bundle import write_bundle
from practicum.site import load_curriculum
from tests.conftest import REPO_ROOT

pytestmark = pytest.mark.integration

MAX_BYTES = 16 * 1024 * 1024


def test_bundle_holds_every_manifest_page(tmp_path: Path) -> None:
    site = REPO_ROOT / "docs"
    out = tmp_path / "index.html"
    count, size = write_bundle(site, out)
    assert size < MAX_BYTES
    html = out.read_text(encoding="utf-8")
    match = re.search(r'<script type="application/json" id="pp-data">(.*?)</script>', html, re.S)
    assert match
    data = json.loads(match.group(1))
    manifest = load_curriculum(site)
    expected = {"home"} | {str(r["id"]) for r in manifest["reference"]}  # type: ignore[attr-defined]
    for part in manifest["parts"]:  # type: ignore[attr-defined]
        expected |= {str(m["id"]) for m in part["modules"] + part["projects"]}
    assert {p["id"] for p in data["pages"].values()} == expected
    assert count == len(expected)
    exercises = sum(len(p["exercises"]) for p in data["pages"].values())
    assert exercises == len(
        re.findall(
            r'class="exercise" data-id=',
            "".join(p.read_text(encoding="utf-8") for p in site.rglob("*.html") if "authoring" not in p.parts),
        )
    )
