"""Whole-repository quality gates: the site is valid, every exercise and project is solvable."""

from pathlib import Path

import pytest

from practicum.exercises import check_page_exercises
from practicum.projects import Source, discover_projects, grade_project
from practicum.site import check_site
from tests.conftest import REPO_ROOT

pytestmark = pytest.mark.integration

PAGES = sorted((REPO_ROOT / "docs").rglob("*.html"))
PROJECTS = discover_projects(REPO_ROOT)


def test_site_has_no_issues() -> None:
    issues = check_site(REPO_ROOT / "docs")
    assert not issues, "\n".join(f"{i.path}: {i.message}" for i in issues)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.relative_to(REPO_ROOT / "docs").as_posix())
def test_exercise_solutions_pass(page: Path) -> None:
    failures = [r for r in check_page_exercises(page) if not r.ok]
    assert not failures, "\n".join(f"{r.id}: {r.detail}" for r in failures)


@pytest.mark.parametrize("project", PROJECTS, ids=lambda p: p.id)
def test_project_solution_passes(project: object) -> None:
    assert grade_project(REPO_ROOT, project, source=Source.SOLUTION, extra_args=["-q", "-p", "no:randomly"]) == 0  # type: ignore[arg-type]


@pytest.mark.parametrize("project", PROJECTS, ids=lambda p: p.id)
def test_project_starter_is_unsolved(project: object) -> None:
    assert grade_project(REPO_ROOT, project, source=Source.STARTER, extra_args=["-q", "-x"]) != 0  # type: ignore[arg-type]


def test_library_styles_load_before_course_styles() -> None:
    # Regression: CodeMirror's stylesheet was appended after course.css and won every tie,
    # leaving editors white in dark mode and fixed at 300px tall.
    course_js = (REPO_ROOT / "docs" / "assets" / "js" / "course.js").read_text(encoding="utf-8")
    load_css = course_js[course_js.index("function loadCss") : course_js.index("const icon")]
    assert "first.before(link)" in load_css
    assert "head.append(h(" not in load_css
