from pathlib import Path
from typing import Any

import pytest

from practicum import cli
from practicum.exercises import ExerciseResult
from practicum.projects import Source
from practicum.workspace import ROOT_ENV_VAR


@pytest.fixture(autouse=True)
def in_repo(fake_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(ROOT_ENV_VAR, str(fake_repo))
    return fake_repo


def test_list(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["list"]) == 0
    err = capsys.readouterr().err
    assert "id=p01" in err
    assert "started=False" in err


def test_start_then_restart_without_force(in_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["start", "p01"]) == 0
    assert (in_repo / "work" / "p01_demo" / "demo").is_dir()
    assert cli.main(["start", "p01"]) == 2
    assert "already exists" in capsys.readouterr().err
    assert cli.main(["start", "p01", "--force"]) == 0


def test_extra_args_rejected_outside_grade() -> None:
    with pytest.raises(SystemExit):
        cli.main(["list", "--bogus"])


def test_unknown_project_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["grade", "p77"]) == 2
    assert "unknown project" in capsys.readouterr().err


def test_grade_forwards_source_and_args(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_grade(root: Path, project: Any, *, source: Source | None, extra_args: list[str]) -> int:
        seen.update(source=source, extra_args=extra_args, id=project.id)
        return 1

    monkeypatch.setattr(cli, "grade_project", fake_grade)
    assert cli.main(["grade", "p01", "--source", "solution", "-x"]) == 1
    assert seen == {"source": Source.SOLUTION, "extra_args": ["-x"], "id": "p01"}


def test_serve_handles_interrupt(monkeypatch: pytest.MonkeyPatch, in_repo: Path) -> None:
    seen: dict[str, Any] = {}

    def fake_serve(site_root: Path, host: str, port: int, *, open_browser: bool) -> None:
        seen.update(site_root=site_root, host=host, port=port, open_browser=open_browser)
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "serve", fake_serve)
    assert cli.main(["serve", "--port", "9999", "--no-browser"]) == 0
    assert seen == {"site_root": in_repo / "docs", "host": "127.0.0.1", "port": 9999, "open_browser": False}


def test_check_site_clean_and_dirty(in_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["check-site"]) == 0
    (in_repo / "docs" / "modules" / "m01.html").write_text("<title>x</title><a href='nope.html'>", encoding="utf-8")
    assert cli.main(["--json", "check-site"]) == 1
    assert "broken link: nope.html" in capsys.readouterr().err


def test_check_exercises_reports_failures(monkeypatch: pytest.MonkeyPatch, in_repo: Path) -> None:
    pages: list[Path] = []

    def fake_check(page: Path) -> list[ExerciseResult]:
        pages.append(page)
        return [ExerciseResult("a", True), ExerciseResult("b", False, "boom")]

    monkeypatch.setattr(cli, "check_page_exercises", fake_check)
    assert cli.main(["check-exercises"]) == 1
    assert pages == [in_repo / "docs" / "modules" / "m01.html"]
    monkeypatch.setattr(cli, "check_page_exercises", lambda page: [ExerciseResult("a", True)])
    assert cli.main(["check-exercises", "docs/modules/m01.html"]) == 0


def test_missing_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
    monkeypatch.setenv(ROOT_ENV_VAR, str(tmp_path_factory.mktemp("empty")))
    assert cli.main(["list"]) == 2


def test_bundle_writes_file(in_repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_write(site_root: Path, out: Path) -> tuple[int, int]:
        out.write_text("x", encoding="utf-8")
        return 3, 1

    monkeypatch.setattr(cli, "write_bundle", fake_write)
    assert cli.main(["bundle", "--out", "single.html"]) == 0
    assert (in_repo / "single.html").read_text(encoding="utf-8") == "x"
    assert "pages=3" in capsys.readouterr().err


def test_bundle_failure_returns_one(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(site_root: Path, out: Path) -> tuple[int, int]:
        raise cli.BundleError("no manifest")

    monkeypatch.setattr(cli, "write_bundle", broken)
    assert cli.main(["bundle"]) == 1
    assert "no manifest" in capsys.readouterr().err
