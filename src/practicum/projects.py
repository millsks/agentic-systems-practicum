"""Discover, start, and grade the curriculum's hands-on projects."""

import os
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

SOURCE_ENV_VAR = "PRACTICUM_SRC"


class ProjectError(RuntimeError):
    """Raised for an unknown project or an invalid project definition."""


class Source(StrEnum):
    """Which copy of a project's code a grading run imports."""

    WORK = "work"
    STARTER = "starter"
    SOLUTION = "solution"


@dataclass(frozen=True, slots=True)
class Project:
    """A hands-on project defined by a ``project.toml`` file.

    Attributes:
        id: Short identifier such as ``p01``.
        title: Human-readable title.
        part: Curriculum part the project closes.
        package: Import name of the package the learner implements.
        path: Directory holding the project definition.
    """

    id: str
    title: str
    part: int
    package: str
    path: Path

    @property
    def starter_dir(self) -> Path:
        """Directory containing the starter code."""
        return self.path / "starter"

    @property
    def solution_dir(self) -> Path:
        """Directory containing the reference solution."""
        return self.path / "solution"

    @property
    def tests_dir(self) -> Path:
        """Directory containing the grading tests."""
        return self.path / "tests"

    def work_dir(self, root: Path) -> Path:
        """Return the learner's working copy location.

        Args:
            root: Repository root.

        Returns:
            The path ``work/<project directory name>`` under ``root``.
        """
        return root / "work" / self.path.name


def load_project(project_dir: Path) -> Project:
    """Load a project definition from ``project_dir/project.toml``.

    Args:
        project_dir: Directory containing ``project.toml``.

    Returns:
        The parsed project.

    Raises:
        ProjectError: If the file is missing or lacks required keys.
    """
    config_path = project_dir / "project.toml"
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProjectError(f"missing {config_path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ProjectError(f"invalid TOML in {config_path}: {exc}") from exc
    try:
        return Project(
            id=str(data["id"]),
            title=str(data["title"]),
            part=int(data["part"]),
            package=str(data["package"]),
            path=project_dir,
        )
    except KeyError as exc:
        raise ProjectError(f"{config_path} is missing key {exc.args[0]!r}") from exc


def discover_projects(root: Path) -> list[Project]:
    """Return every project under ``root/projects`` sorted by id.

    Args:
        root: Repository root.

    Returns:
        Projects ordered by identifier.
    """
    projects_dir = root / "projects"
    found = [load_project(p.parent) for p in projects_dir.glob("*/project.toml")]
    return sorted(found, key=lambda p: p.id)


def get_project(root: Path, project_id: str) -> Project:
    """Look up a project by id or directory name.

    Args:
        root: Repository root.
        project_id: Identifier such as ``p01`` or a directory name such as ``p01_budget_ledger``.

    Returns:
        The matching project.

    Raises:
        ProjectError: If no project matches.
    """
    for project in discover_projects(root):
        if project_id in (project.id, project.path.name):
            return project
    raise ProjectError(f"unknown project {project_id!r}; run `pixi run projects` to list them")


def start_project(root: Path, project: Project, *, force: bool = False) -> Path:
    """Copy a project's starter code into the learner's ``work/`` directory.

    Args:
        root: Repository root.
        project: Project to start.
        force: Replace an existing working copy.

    Returns:
        The working copy directory.

    Raises:
        ProjectError: If a working copy exists and ``force`` is false.
    """
    destination = project.work_dir(root)
    if destination.exists():
        if not force:
            raise ProjectError(f"{destination} already exists; pass --force to overwrite your work")
        shutil.rmtree(destination)
    shutil.copytree(project.starter_dir, destination)
    return destination


def resolve_source(root: Path, project: Project, source: Source | None) -> tuple[Source, Path]:
    """Pick which code directory a grading run imports.

    With no explicit choice the learner's working copy is preferred, falling back to the starter.

    Args:
        root: Repository root.
        project: Project being graded.
        source: Explicit source, or ``None`` to choose automatically.

    Returns:
        The chosen source and its directory.
    """
    if source is None:
        source = Source.WORK if project.work_dir(root).is_dir() else Source.STARTER
    directories = {
        Source.WORK: project.work_dir(root),
        Source.STARTER: project.starter_dir,
        Source.SOLUTION: project.solution_dir,
    }
    return source, directories[source]


def grade_project(
    root: Path, project: Project, *, source: Source | None = None, extra_args: list[str] | None = None
) -> int:
    """Run a project's grading tests against the chosen source directory.

    Args:
        root: Repository root.
        project: Project to grade.
        source: Which code to import; see :func:`resolve_source`.
        extra_args: Additional arguments forwarded to pytest.

    Returns:
        The pytest exit code (0 means every test passed).
    """
    _, code_dir = resolve_source(root, project, source)
    env = {**os.environ, SOURCE_ENV_VAR: str(code_dir)}
    command = [sys.executable, "-m", "pytest", str(project.tests_dir), "-p", "no:cacheprovider", *(extra_args or [])]
    completed = subprocess.run(command, cwd=root, env=env, check=False)
    return completed.returncode
