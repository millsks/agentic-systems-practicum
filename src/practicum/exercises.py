"""Verify that each in-page exercise's reference solution passes its own tests."""

import json
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

HARNESS = r"""
import ast, asyncio, contextlib, inspect, io, json, sys

payload = json.loads(sys.stdin.read())

def capture_output(func, *args, stdin=None, **kwargs):
    buf = io.StringIO()
    old_in = sys.stdin
    if stdin is not None:
        sys.stdin = io.StringIO(stdin)
    try:
        with contextlib.redirect_stdout(buf):
            result = func(*args, **kwargs)
    finally:
        sys.stdin = old_in
    return result, buf.getvalue()

async def run(code, ns, filename):
    compiled = compile(code, filename, "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    result = eval(compiled, ns)
    if inspect.iscoroutine(result):
        await result

async def main():
    ns = {"__name__": "__main__"}
    out = io.StringIO()
    sys.stdin = io.StringIO(payload["stdin"])
    try:
        with contextlib.redirect_stdout(out):
            await run(payload["code"], ns, "<solution>")
    except SystemExit:
        pass
    except BaseException as e:
        return {"error": f"solution raised {type(e).__name__}: {e}"}
    ns["program_output"] = out.getvalue()
    ns["capture_output"] = capture_output
    try:
        await run(payload["tests"], ns, "<tests>")
    except BaseException as e:
        return {"error": f"tests failed to load: {type(e).__name__}: {e}"}
    failures = []
    for name, fn in list(ns.items()):
        code_obj = getattr(fn, "__code__", None)
        if not (name.startswith("test_") and code_obj and code_obj.co_filename == "<tests>"):
            continue
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                value = fn()
                if inspect.iscoroutine(value):
                    await value
        except BaseException as e:
            failures.append(f"{name}: {type(e).__name__}: {e}")
    return {"failures": failures}

sys.stdout.write(json.dumps(asyncio.run(main())))
"""


@dataclass(frozen=True, slots=True)
class Exercise:
    """An exercise extracted from a page.

    Attributes:
        id: The exercise ``data-id``.
        solution: Reference solution source, or an empty string when the page has none.
        tests: Test source.
        stdin: Text fed to ``input()``.
    """

    id: str
    solution: str
    tests: str
    stdin: str


@dataclass(frozen=True, slots=True)
class ExerciseResult:
    """Outcome of checking one exercise.

    Attributes:
        id: The exercise ``data-id``.
        ok: Whether the solution passed every test.
        detail: Failure details; empty when ``ok``.
    """

    id: str
    ok: bool
    detail: str = ""


class _ExerciseParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.exercises: list[Exercise] = []
        self._depth = 0
        self._current: dict[str, str] | None = None
        self._exercise_depth = 0
        self._solution_depth: int | None = None
        self._capture: str | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {k: v or "" for k, v in attrs}
        classes = set(attributes.get("class", "").split())
        if tag not in {"br", "hr", "img", "input", "meta", "link", "wbr", "source", "col", "area", "base", "embed"}:
            self._depth += 1
        if "exercise" in classes and self._current is None:
            stdin = attributes.get("data-stdin", "").replace("\\n", "\n")
            self._current = {"id": attributes.get("data-id", ""), "solution": "", "tests": "", "stdin": stdin}
            self._exercise_depth = self._depth
        elif self._current is not None:
            if tag == "details" and "solution" in classes:
                self._solution_depth = self._depth
            elif tag == "script" and "tests" in classes:
                self._capture, self._buffer = "tests", []
            elif tag == "code" and self._solution_depth is not None and not self._current["solution"]:
                self._capture, self._buffer = "solution", []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._current is not None:
            if (self._capture == "tests" and tag == "script") or (self._capture == "solution" and tag == "code"):
                self._current[self._capture] = "".join(self._buffer)
                self._capture = None
            if self._solution_depth == self._depth and tag == "details":
                self._solution_depth = None
            if self._depth == self._exercise_depth:
                current = self._current
                self.exercises.append(
                    Exercise(
                        id=current["id"],
                        solution=_clean(current["solution"]),
                        tests=_clean(current["tests"]),
                        stdin=current["stdin"],
                    )
                )
                self._current = None
        self._depth -= 1


def _clean(source: str) -> str:
    return textwrap.dedent(source.replace("\t", "    ")).strip("\n") + "\n"


def extract_exercises(html: str) -> list[Exercise]:
    """Extract every exercise from a page.

    Args:
        html: Page source.

    Returns:
        Exercises in page order.
    """
    parser = _ExerciseParser()
    parser.feed(html)
    parser.close()
    return parser.exercises


def check_exercise(exercise: Exercise, *, timeout: float = 60.0) -> ExerciseResult:
    """Run an exercise's reference solution against its tests in a fresh interpreter.

    Args:
        exercise: The exercise to check.
        timeout: Seconds before the run is abandoned.

    Returns:
        The outcome.
    """
    if not exercise.solution.strip():
        return ExerciseResult(exercise.id, False, "no reference solution in a details.solution block")
    payload = json.dumps({"code": exercise.solution, "tests": exercise.tests, "stdin": exercise.stdin})
    try:
        completed = subprocess.run(
            [sys.executable, "-c", HARNESS],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ExerciseResult(exercise.id, False, f"timed out after {timeout:.0f}s")
    try:
        outcome = json.loads(completed.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return ExerciseResult(exercise.id, False, f"harness crashed: {completed.stderr.strip()[-500:]}")
    if "error" in outcome:
        return ExerciseResult(exercise.id, False, str(outcome["error"]))
    failures: list[str] = outcome["failures"]
    return ExerciseResult(exercise.id, not failures, "; ".join(failures))


def check_page_exercises(page: Path) -> list[ExerciseResult]:
    """Check every exercise on one page.

    Args:
        page: HTML file to check.

    Returns:
        One result per exercise.
    """
    return [check_exercise(e) for e in extract_exercises(page.read_text(encoding="utf-8"))]
