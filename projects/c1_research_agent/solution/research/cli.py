"""Command-line entry point (provided): ask the agent a question against the real Claude API."""

from __future__ import annotations

import argparse
import sys
from typing import Any, TextIO

import structlog

import agentlab
from research.agent import DEFAULT_MAX_TOKENS, MODEL, Answer, run

ENABLE_LIVE = """The real Claude API is not available here: {reason}

To run the agent against Claude:
  1. pixi add anthropic                      (adds the SDK from conda-forge)
  2. export ANTHROPIC_API_KEY=...            (or sign in with `ant auth login`; never put the key in code)
  3. pixi run python -m research "How do honeybees tell each other where food is?"

The graded tests never need this: `pixi run grade c1` runs offline against agentlab.MockClient.
"""

log = structlog.get_logger(__name__)


def configure_logging(verbose: bool, stream: TextIO) -> None:
    """Send structlog output as key=value lines to ``stream`` (stderr), keeping stdout for the answer.

    Args:
        verbose: Log every step at info level; otherwise only warnings and errors.
        stream: Where log lines go.
    """
    structlog.configure(
        processors=[structlog.processors.add_log_level, structlog.processors.KeyValueRenderer(sort_keys=True)],
        wrapper_class=structlog.make_filtering_bound_logger(20 if verbose else 30),
        logger_factory=structlog.PrintLoggerFactory(file=stream),
        cache_logger_on_first_use=False,
    )


def format_answer(answer: Answer) -> str:
    """Render an answer for the terminal.

    Args:
        answer: The run result.

    Returns:
        The answer text, its sources, any citation warnings, and a one-line run summary.
    """
    lines = [answer.text.strip() or f"(no answer: {answer.stopped_because})", ""]
    if answer.citations:
        lines.append("Sources: " + ", ".join(answer.citations))
    lines.extend(f"Warning: {problem}" for problem in answer.citation_problems)
    if answer.detail:
        lines.append(f"Note: {answer.detail}")
    lines.append(
        f"[{answer.steps} steps, {answer.usage.input_tokens} input / {answer.usage.output_tokens} output tokens, "
        f"stopped: {answer.stopped_because}]"
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        The parser.
    """
    parser = argparse.ArgumentParser(prog="research", description="Answer a question from the honeybee library.")
    parser.add_argument("question", help="the question to research")
    parser.add_argument("--max-steps", type=int, default=8, help="maximum model calls (default 8)")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="max_tokens per request")
    parser.add_argument("--model", default=MODEL, help=f"model id (default {MODEL})")
    parser.add_argument("-v", "--verbose", action="store_true", help="log every step to stderr")
    return parser


def main(argv: list[str] | None = None, *, client: Any = None) -> int:
    """Parse arguments, run the agent, and write the answer to stdout.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).
        client: A client to use instead of the real API (tests pass an ``agentlab.MockClient``).

    Returns:
        0 for a sound answer, 1 when the run stopped early or citations have problems, 2 when no client is available.
    """
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose, sys.stderr)
    if client is None:
        try:
            client = agentlab.get_client()
        except agentlab.LiveModelUnavailableError as exc:
            sys.stderr.write(ENABLE_LIVE.format(reason=exc))
            return 2
    try:
        answer = run(client, args.question, max_steps=args.max_steps, max_tokens=args.max_tokens, model=args.model)
    except Exception as exc:  # the real SDK raises its own error types (auth, rate limit, connection)
        log.error("api_call_failed", error_type=type(exc).__name__, error=str(exc))
        sys.stderr.write(ENABLE_LIVE.format(reason=f"{type(exc).__name__}: {exc}"))
        return 2
    sys.stdout.write(format_answer(answer))
    return 0 if answer.ok else 1
