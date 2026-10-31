import subprocess
from pathlib import Path
from typing import Any

import pytest

from practicum import projects
from practicum.projects import (
    ProjectError,
    Source,
    discover_projects,
    get_project,
    grade_project,
    load_project,
    resolve_source,
    start_project,
)


def test_load_project_reads_fields(fake_repo: Path) -> None:
    project = load_project(fake_repo / "projects" / "p01_demo")
    assert (project.id, project.title, project.part, project.package) == ("p01", "Demo", 1, "demo")
    assert project.starter_dir.name == "starter"
    assert project.solution_dir.name == "solution"
    assert project.tests_dir.name == "tests"


def test_load_project_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ProjectError, match="missing"):
        load_project(tmp_path)


def test_load_project_invalid_toml(tmp_path: Path) -> None:
    (tmp_path / "project.toml").write_text("id = ", encoding="utf-8")
    with pytest.raises(ProjectError, match="invalid TOML"):
        load_project(tmp_path)


def test_load_project_missing_key(tmp_path: Path) -> None:
    (tmp_path / "project.toml").write_text('id = "p9"\n', encoding="utf-8")
    with pytest.raises(ProjectError, match="missing key 'title'"):
        load_project(tmp_path)


def test_discover_sorts_by_id(fake_repo: Path) -> None:
    other = fake_repo / "projects" / "a_first"
    other.mkdir()
    (other / "project.toml").write_text('id = "p00"\ntitle = "Zero"\npart = 0\npackage = "z"\n', encoding="utf-8")
    assert [p.id for p in discover_projects(fake_repo)] == ["p00", "p01"]


def test_get_project_by_id_and_directory(fake_repo: Path) -> None:
    assert get_project(fake_repo, "p01").title == "Demo"
    assert get_project(fake_repo, "p01_demo").id == "p01"


def test_get_project_unknown(fake_repo: Path) -> None:
    with pytest.raises(ProjectError, match="unknown project 'p99'"):
        get_project(fake_repo, "p99")


def test_start_project_copies_starter(fake_repo: Path) -> None:
    project = get_project(fake_repo, "p01")
    destination = start_project(fake_repo, project)
    assert destination == fake_repo / "work" / "p01_demo"
    assert (destination / "demo" / "__init__.py").read_text(encoding="utf-8").startswith("def answer")


def test_start_project_refuses_to_overwrite(fake_repo: Path) -> None:
    project = get_project(fake_repo, "p01")
    start_project(fake_repo, project)
    with pytest.raises(ProjectError, match="already exists"):
        start_project(fake_repo, project)


def test_start_project_force_replaces(fake_repo: Path) -> None:
    project = get_project(fake_repo, "p01")
    destination = start_project(fake_repo, project)
    (destination / "scratch.txt").write_text("old", encoding="utf-8")
    start_project(fake_repo, project, force=True)
    assert not (destination / "scratch.txt").exists()


def test_resolve_source_prefers_work_dir(fake_repo: Path) -> None:
    project = get_project(fake_repo, "p01")
    assert resolve_source(fake_repo, project, None) == (Source.STARTER, project.starter_dir)
    start_project(fake_repo, project)
    assert resolve_source(fake_repo, project, None) == (Source.WORK, project.work_dir(fake_repo))
    assert resolve_source(fake_repo, project, Source.SOLUTION) == (Source.SOLUTION, project.solution_dir)


def test_grade_project_invokes_pytest_with_source(fake_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append({"command": command, **kwargs})
        return subprocess.CompletedProcess(command, 3)

    monkeypatch.setattr(projects.subprocess, "run", fake_run)
    project = get_project(fake_repo, "p01")
    code = grade_project(fake_repo, project, source=Source.SOLUTION, extra_args=["-q"])
    assert code == 3
    call = calls[0]
    assert call["command"][1:4] == ["-m", "pytest", str(project.tests_dir)]
    assert call["command"][-1] == "-q"
    assert call["env"][projects.SOURCE_ENV_VAR] == str(project.solution_dir)
    assert call["cwd"] == fake_repo
