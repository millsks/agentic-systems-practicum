import pytest

from practicum.exercises import Exercise, check_exercise

pytestmark = pytest.mark.integration


def make(solution: str, tests: str, stdin: str = "") -> Exercise:
    return Exercise("x-e1", solution, tests, stdin)


def test_passing_solution() -> None:
    exercise = make(
        "name = input()\nprint('hi', name)\ndef double(n):\n    return n * 2\n",
        "def test_double():\n    assert double(2) == 4\n"
        "def test_output():\n    assert program_output == 'hi Ada\\n'\n"
        "def test_capture():\n    assert capture_output(print, 'x') == (None, 'x\\n')\n",
        stdin="Ada\n",
    )
    assert check_exercise(exercise).ok


def test_top_level_await_is_supported() -> None:
    exercise = make(
        "import asyncio\nasync def f():\n    return 3\nvalue = await f()\n",
        "async def test_value():\n    assert value == 3\n",
    )
    assert check_exercise(exercise).ok


def test_failing_assertion_is_reported() -> None:
    result = check_exercise(make("x = 1\n", "def test_x():\n    assert x == 2, 'x should be 2'\n"))
    assert not result.ok
    assert "x should be 2" in result.detail


def test_solution_error_is_reported() -> None:
    result = check_exercise(make("raise ValueError('nope')\n", "def test_x():\n    pass\n"))
    assert "solution raised ValueError: nope" in result.detail


def test_broken_tests_are_reported() -> None:
    result = check_exercise(make("x = 1\n", "def test_x(:\n"))
    assert "tests failed to load" in result.detail


def test_system_exit_in_solution_is_allowed() -> None:
    assert check_exercise(make("x = 1\nraise SystemExit(0)\n", "def test_x():\n    assert x == 1\n")).ok


def test_missing_solution() -> None:
    assert "no reference solution" in check_exercise(make("  \n", "")).detail


def test_timeout() -> None:
    result = check_exercise(make("while True:\n    pass\n", ""), timeout=1)
    assert result.detail == "timed out after 1s"


def test_harness_crash() -> None:
    result = check_exercise(make("import os\nos._exit(3)\n", ""))
    assert "harness crashed" in result.detail
