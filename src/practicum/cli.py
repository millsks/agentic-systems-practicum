"""Command-line interface: ``practicum list|start|grade|serve|check-site|check-exercises|bundle|sync-runtime``."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from practicum import __version__
from practicum.bundle import BundleError, write_bundle
from practicum.exercises import check_page_exercises
from practicum.log import configure_logging, get_logger
from practicum.projects import (
    ProjectError,
    Source,
    discover_projects,
    get_project,
    grade_project,
    resolve_source,
    start_project,
)
from practicum.runtime import write_runtime
from practicum.serve import serve
from practicum.site import check_site
from practicum.workspace import WorkspaceNotFoundError, find_root


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for every subcommand.

    Returns:
        The configured parser.
    """
    parser = argparse.ArgumentParser(prog="practicum", description="Agentic Systems Practicum learner tools.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--json", action="store_true", help="emit JSON log lines")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="list every project and whether you have started it")

    start = commands.add_parser("start", help="copy a project's starter code into work/")
    start.add_argument("project", help="project id, e.g. c1")
    start.add_argument("--force", action="store_true", help="overwrite an existing working copy")

    grade = commands.add_parser(
        "grade", help="run a project's tests against your code (unrecognized options are passed to pytest)"
    )
    grade.add_argument("project", help="project id, e.g. c1")
    grade.add_argument("--source", choices=[s.value for s in Source], help="which copy of the code to grade")

    serve_cmd = commands.add_parser("serve", help="serve the course website locally")
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8000)
    serve_cmd.add_argument("--no-browser", action="store_true", help="do not open a browser window")

    commands.add_parser("check-site", help="validate links, quizzes, and exercises in docs/")

    bundle = commands.add_parser("bundle", help="build the single-file edition of the course website")
    bundle.add_argument(
        "--out",
        type=Path,
        default=Path("dist/agentic-systems-practicum.html"),
        help="output file, relative to the repository root",
    )

    commands.add_parser("sync-runtime", help="regenerate the in-browser agentlab runtime from src/agentlab")

    exercises = commands.add_parser("check-exercises", help="run each exercise's reference solution against its tests")
    exercises.add_argument("pages", nargs="*", type=Path, help="HTML pages to check (default: every page in docs/)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Arguments excluding the program name; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = build_parser()
    args, extra = parser.parse_known_args(argv)
    if extra and args.command != "grade":
        parser.error(f"unrecognized arguments: {' '.join(extra)}")
    args.pytest_args = extra
    configure_logging(json=args.json)
    log = get_logger()
    try:
        root = find_root()
        return _dispatch(args, root)
    except (WorkspaceNotFoundError, ProjectError) as exc:
        log.error("command_failed", command=args.command, reason=str(exc))
        return 2


def _dispatch(args: argparse.Namespace, root: Path) -> int:
    log = get_logger()
    site_root = root / "docs"
    if args.command == "list":
        for project in discover_projects(root):
            started = project.work_dir(root).is_dir()
            log.info("project", id=project.id, part=project.part, title=project.title, started=started)
        return 0
    if args.command == "start":
        project = get_project(root, args.project)
        destination = start_project(root, project, force=args.force)
        log.info("project_started", id=project.id, work_dir=str(destination.relative_to(root)))
        return 0
    if args.command == "grade":
        project = get_project(root, args.project)
        source, code_dir = resolve_source(root, project, Source(args.source) if args.source else None)
        log.info("grading", id=project.id, source=source.value, code_dir=str(code_dir.relative_to(root)))
        code = grade_project(root, project, source=source, extra_args=args.pytest_args)
        log.info("graded", id=project.id, passed=code == 0, exit_code=code)
        return code
    if args.command == "serve":
        log.info("serving", url=f"http://{args.host}:{args.port}/", root=str(site_root))
        try:
            serve(site_root, args.host, args.port, open_browser=not args.no_browser)
        except KeyboardInterrupt:
            log.info("server_stopped")
        return 0
    if args.command == "sync-runtime":
        log.info("runtime_written", path=str(write_runtime(root).relative_to(root)))
        return 0
    if args.command == "bundle":
        return _bundle(site_root, root / args.out)
    if args.command == "check-exercises":
        return _check_exercises(args.pages or sorted(site_root.rglob("*.html")))
    issues = check_site(site_root)
    for issue in issues:
        log.error("site_issue", path=issue.path, message=issue.message)
    log.info("site_checked", issues=len(issues))
    return 1 if issues else 0


def _bundle(site_root: Path, out: Path) -> int:
    log = get_logger()
    try:
        pages, size = write_bundle(site_root, out)
    except BundleError as exc:
        log.error("bundle_failed", reason=str(exc))
        return 1
    log.info("bundled", pages=pages, bytes=size, out=str(out))
    return 0


def _check_exercises(pages: list[Path]) -> int:
    log = get_logger()
    failed = 0
    total = 0
    for page in pages:
        for result in check_page_exercises(page):
            total += 1
            if not result.ok:
                failed += 1
                log.error("exercise_failed", page=str(page), id=result.id, detail=result.detail)
    log.info("exercises_checked", total=total, failed=failed)
    return 1 if failed else 0
