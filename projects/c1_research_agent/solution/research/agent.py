"""The agent loop: ask the model, run the tools it requests, repeat until it answers or a limit is hit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import structlog

from research.citations import check_citations, parse_citations
from research.corpus import Corpus
from research.tools import Toolbox, ToolError, tool_definitions

MODEL = "claude-opus-5-5"
DEFAULT_MAX_TOKENS = 2048
SYSTEM_PROMPT = """You are a careful research assistant with a small library of documents about honeybees.

Answer the user's question using only the library:
1. Call search with short keyword queries to find relevant documents.
2. Call read on every document you rely on. Search snippets are not enough to answer from.
3. Write a concise answer. After each claim, cite the document it came from with its id in square brackets,
   for example [waggle-dance]. Cite only documents you have read.

If the library does not contain the answer, say so plainly instead of guessing. When a tool returns an error,
read the message and correct your call."""

StopKind = Literal["end_turn", "max_tokens", "refusal", "max_steps", "stop_sequence", "pause_turn"]

log = structlog.get_logger(__name__)


@dataclass
class Usage:
    """Token totals across every request in a run.

    Attributes:
        input_tokens: Sum of ``usage.input_tokens``.
        output_tokens: Sum of ``usage.output_tokens``.
    """

    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, usage: Any) -> None:
        """Add one response's ``usage`` to the totals.

        Args:
            usage: An object with ``input_tokens`` and ``output_tokens`` (mock or real SDK).
        """
        self.input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
        self.output_tokens += int(getattr(usage, "output_tokens", 0) or 0)


@dataclass
class Answer:
    """The structured result of one run.

    Attributes:
        text: The model's final text (possibly partial when the run did not end normally).
        citations: Ids cited as ``[doc-id]`` in ``text``, in order.
        citation_problems: Problems found by :func:`research.citations.check_citations`.
        read_ids: Documents the agent read, in first-read order.
        steps: Number of ``messages.create`` calls made.
        usage: Token totals.
        stopped_because: ``end_turn`` for a normal answer, otherwise why the run ended
            (``max_steps``, ``max_tokens``, ``refusal``, ...).
        detail: Extra explanation, such as a refusal's ``stop_details.explanation``.
        messages: The full conversation history, for debugging with ``agentlab.format_transcript``.
    """

    text: str
    citations: list[str]
    citation_problems: list[str]
    read_ids: list[str]
    steps: int
    usage: Usage
    stopped_because: StopKind
    detail: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list, repr=False)

    @property
    def ok(self) -> bool:
        """Whether the run ended normally with sound citations.

        Returns:
            ``True`` when ``stopped_because == "end_turn"`` and there are no citation problems.
        """
        return self.stopped_because == "end_turn" and not self.citation_problems


def text_of(content: list[Any]) -> str:
    """Join the text blocks of a response's content.

    Args:
        content: ``response.content`` (mock or real SDK blocks).

    Returns:
        The concatenated text; empty when there is none.
    """
    return "".join(block.text for block in content if getattr(block, "type", None) == "text")


def execute_tool_calls(toolbox: Toolbox, content: list[Any]) -> list[dict[str, Any]]:
    """Run every ``tool_use`` block in a response and build the matching ``tool_result`` blocks.

    Failures never escape: a :class:`ToolError` (unknown tool, invalid input, bad id) becomes a result with
    ``is_error: True`` and the error message, so the model can correct itself.

    Args:
        toolbox: The run's tools.
        content: ``response.content``.

    Returns:
        One ``{"type": "tool_result", "tool_use_id", "content"[, "is_error"]}`` dict per ``tool_use`` block,
        in the same order, ready to send together in one user message.
    """
    results: list[dict[str, Any]] = []
    for block in content:
        if getattr(block, "type", None) != "tool_use":
            continue
        result: dict[str, Any] = {"type": "tool_result", "tool_use_id": block.id}
        try:
            result["content"] = toolbox.dispatch(block.name, dict(block.input))
            log.info("tool_ok", tool=block.name, input=block.input)
        except ToolError as exc:
            result["content"] = f"Error: {exc}"
            result["is_error"] = True
            log.warning("tool_error", tool=block.name, input=block.input, error=str(exc))
        results.append(result)
    return results


def run(
    client: Any,
    question: str,
    *,
    corpus: Corpus | None = None,
    max_steps: int = 8,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    model: str = MODEL,
) -> Answer:
    """Answer ``question`` by letting the model search and read the corpus in a loop.

    Each step sends the whole history with the system prompt and tool definitions. On ``tool_use`` every
    requested tool runs and all results go back in one user message. The loop ends on ``end_turn`` (or any other
    non-tool stop reason) or after ``max_steps`` requests.

    Args:
        client: ``agentlab.MockClient`` or ``anthropic.Anthropic()``; only ``client.messages.create`` is used.
        question: The user's question.
        corpus: Documents to research; defaults to the bundled corpus.
        max_steps: Maximum number of ``messages.create`` calls.
        max_tokens: ``max_tokens`` for each request.
        model: Model id.

    Returns:
        The answer with citations checked against the documents read in this run.
    """
    toolbox = Toolbox(corpus)
    tools = tool_definitions()
    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]
    usage = Usage()
    text = ""
    stopped: StopKind = "max_steps"
    detail: str | None = None
    steps = 0
    while steps < max_steps:
        steps += 1
        response = client.messages.create(
            model=model, max_tokens=max_tokens, system=SYSTEM_PROMPT, tools=tools, messages=messages
        )
        usage.add(response.usage)
        log.info("model_step", step=steps, stop_reason=response.stop_reason)
        if response.content:
            messages.append({"role": "assistant", "content": response.content})
        text = text_of(response.content)
        if response.stop_reason != "tool_use":
            stopped = response.stop_reason
            if stopped == "refusal" and response.stop_details is not None:
                detail = response.stop_details.explanation
            break
        messages.append({"role": "user", "content": execute_tool_calls(toolbox, response.content)})
    else:
        detail = f"no final answer after {max_steps} steps"
        text = ""
    citations = parse_citations(text)
    problems = check_citations(citations, toolbox.read_ids, toolbox.corpus.ids()) if stopped == "end_turn" else []
    log.info("run_done", stopped_because=stopped, steps=steps, citations=citations, problems=problems)
    return Answer(
        text=text,
        citations=citations,
        citation_problems=problems,
        read_ids=list(toolbox.read_ids),
        steps=steps,
        usage=usage,
        stopped_because=stopped,
        detail=detail,
        messages=messages,
    )
