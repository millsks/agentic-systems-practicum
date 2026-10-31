import json
from pathlib import Path

import pytest

from practicum import cli
from practicum.runtime import collect_sources, render_runtime, runtime_is_current, runtime_path, write_runtime
from practicum.workspace import ROOT_ENV_VAR


@pytest.fixture
def repo(fake_repo: Path) -> Path:
    package = fake_repo / "src" / "agentlab"
    (package / "sub").mkdir(parents=True)
    (package / "__pycache__").mkdir()
    (package / "__init__.py").write_text("X = '</script>'\n", encoding="utf-8")
    (package / "sub" / "deep.py").write_text("Y = 1\n", encoding="utf-8")
    (package / "__pycache__" / "junk.py").write_text("ignored\n", encoding="utf-8")
    return fake_repo


def test_collect_sources_skips_caches(repo: Path) -> None:
    sources = collect_sources(repo / "src" / "agentlab")
    assert list(sources) == ["agentlab/__init__.py", "agentlab/sub/deep.py"]


def test_render_escapes_closing_tags(repo: Path) -> None:
    text = render_runtime(collect_sources(repo / "src" / "agentlab"))
    assert "</script>" not in text
    payload = json.loads(text.split("window.PP_PY_MODULES = ", 1)[1].rstrip(";\n"))
    assert payload["agentlab/__init__.py"] == "X = '</script>'\n"


def test_write_and_check_current(repo: Path) -> None:
    assert not runtime_is_current(repo)
    path = write_runtime(repo)
    assert path == runtime_path(repo)
    assert runtime_is_current(repo)
    (repo / "src" / "agentlab" / "sub" / "deep.py").write_text("Y = 2\n", encoding="utf-8")
    assert not runtime_is_current(repo)


def test_cli_sync_runtime(repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv(ROOT_ENV_VAR, str(repo))
    assert cli.main(["sync-runtime"]) == 0
    assert "runtime_written" in capsys.readouterr().err
    assert runtime_is_current(repo)
