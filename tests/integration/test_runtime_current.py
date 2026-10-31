"""The in-browser agentlab runtime must match src/agentlab, and course.js must install it."""

import pytest

from practicum.runtime import runtime_is_current
from tests.conftest import REPO_ROOT

pytestmark = pytest.mark.integration


def test_committed_runtime_matches_sources() -> None:
    assert runtime_is_current(REPO_ROOT), "docs/assets/js/agentlab-src.js is stale: run `pixi run sync-runtime`"


def test_course_js_installs_runtime_modules() -> None:
    course_js = (REPO_ROOT / "docs" / "assets" / "js" / "course.js").read_text(encoding="utf-8")
    assert "window.PP_PY_MODULES" in course_js
    assert "_pp_install_modules(_pp_modules)" in course_js


def test_every_page_loads_the_runtime_before_course_js() -> None:
    for page in sorted((REPO_ROOT / "docs").rglob("*.html")):
        html = page.read_text(encoding="utf-8")
        if "course.js" not in html:
            continue
        assert "agentlab-src.js" in html, f"{page.name} does not load agentlab-src.js"
        assert html.index("agentlab-src.js") < html.index("course.js"), f"{page.name} loads the runtime too late"
