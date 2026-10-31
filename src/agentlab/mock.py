"""``MockClient``: a scripted stand-in for ``anthropic.Anthropic()`` that runs offline and deterministically."""

from __future__ import annotations

import copy
import json
import random
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from types import TracebackType
from typing import Any

from agentlab.blocks import (
    ContentBlock,
    Message,
    MessageTokensCount,
    StopDetails,
    StopReason,
    TextBlock,
    ToolUseBlock,
    Usage,
)
from agentlab.errors import APIError, MockScriptError
from agentlab.request import Request, build_request
from agentlab.schema import validate
from agentlab.tokens import CHARS_PER_TOKEN, estimate_request_tokens, estimate_tokens


@dataclass(frozen=True)
class Failure:
    """A scripted step that raises an API error instead of answering.

    Attributes:
        error: The exception to raise.
    """

    error: APIError


Step = Message | str | Failure | Callable[[Request], "Step"]


def reply(text: str) -> Message:
    """A step where the model answers with text and ends its turn.

    Args:
        text: The answer.

    Returns:
        The scripted response.
    """
    return Message(content=[TextBlock(text)], stop_reason="end_turn")


def tool_call(
    name: str, input: dict[str, Any] | None = None, *, text: str | None = None, id: str | None = None
) -> Message:
    """A step where the model asks to call one tool.

    Args:
        name: Tool name.
        input: Tool arguments.
        text: Optional text the model writes before the call.
        id: Tool use id; generated when omitted.

    Returns:
        The scripted response, with ``stop_reason="tool_use"``.
    """
    return tool_calls([(name, input or {})], text=text, ids=[id] if id else None)


def tool_calls(
    calls: list[tuple[str, dict[str, Any]]], *, text: str | None = None, ids: list[str] | None = None
) -> Message:
    """A step where the model asks for several tool calls at once (parallel tool use).

    Args:
        calls: ``(name, input)`` pairs, in order.
        text: Optional text the model writes before the calls.
        ids: Tool use ids, one per call; generated when omitted.

    Returns:
        The scripted response, with ``stop_reason="tool_use"``.
    """
    blocks: list[ContentBlock] = [TextBlock(text)] if text else []
    for position, (name, arguments) in enumerate(calls):
        blocks.append(ToolUseBlock(id=ids[position] if ids else "", name=name, input=dict(arguments)))
    return Message(content=blocks, stop_reason="tool_use")


def refusal(category: str | None = None, explanation: str = "The request was declined.") -> Message:
    """A step where the model declines the request.

    Args:
        category: Refusal category such as ``"cyber"``.
        explanation: Reason shown in ``stop_details``.

    Returns:
        The scripted response, with ``stop_reason="refusal"`` and no content.
    """
    return Message(content=[], stop_reason="refusal", stop_details=StopDetails(category, explanation))


def fail(error: APIError) -> Failure:
    """A step where the API call fails, for practicing retries and error handling.

    Args:
        error: The exception the call raises, such as ``RateLimitError()``.

    Returns:
        The scripted failure.
    """
    return Failure(error)


def one_of(*answers: str) -> Callable[[Request], Step]:
    """A step that picks one of several answers using the client's seeded random generator.

    Use it to show that the same prompt can produce different outputs.

    Args:
        answers: Candidate answers.

    Returns:
        A step that chooses an answer per request.
    """

    def choose(request: Request) -> Step:
        return reply(request.rng.choice(answers))

    return choose


class MockClient:
    """A scripted client with the same ``messages`` surface as ``anthropic.Anthropic()``.

    Each call to ``messages.create`` validates the request like the real API, then takes the next
    step from the script. A step is a :class:`Message`, a string (shorthand for :func:`reply`), a
    :class:`Failure`, or a function that receives the :class:`Request` and returns a step.

    Attributes:
        messages: The Messages resource: ``create``, ``stream`` and ``count_tokens``.
        requests: Every validated request, in order; inspect it in tests.
    """

    def __init__(
        self, script: list[Step] | None = None, *, responder: Callable[[Request], Step] | None = None, seed: int = 0
    ) -> None:
        """Create a client.

        Args:
            script: Steps answered in order, one per request.
            responder: A function answering every request; used once the script is exhausted.
            seed: Seed for the random generator used by :func:`one_of` and responders.
        """
        self._script: list[Step] = list(script or [])
        self._responder = responder
        self._rng = random.Random(seed)
        self._ids = 0
        self.requests: list[Request] = []
        self.messages = Messages(self)

    @property
    def remaining(self) -> int:
        """Scripted steps not yet used.

        Returns:
            The count.
        """
        return len(self._script)

    def _respond(self, kwargs: dict[str, Any]) -> Message:
        request = build_request(kwargs, self._rng)
        self.requests.append(request)
        if self._script:
            step: Step = self._script.pop(0)
        elif self._responder is not None:
            step = self._responder
        else:
            raise MockScriptError(f"the mock's script is used up after {len(self.requests) - 1} responses")
        while callable(step):
            step = step(request)
        if isinstance(step, Failure):
            raise step.error
        return self._finish(reply(step) if isinstance(step, str) else copy.deepcopy(step), request)

    def _next_id(self, prefix: str) -> str:
        self._ids += 1
        return f"{prefix}_mock_{self._ids:04d}"

    def _finish(self, message: Message, request: Request) -> Message:
        for block in message.content:
            if isinstance(block, ToolUseBlock) and not block.id:
                block.id = self._next_id("toolu")
        _check_strict_tools(message, request)
        _apply_stop_sequences(message, request.stop_sequences)
        _apply_max_tokens(message, request.max_tokens)
        _check_output_format(message, request)
        message.id = message.id or self._next_id("msg")
        message.model = request.model
        input_tokens = estimate_request_tokens(request.messages, system=request.system, tools=request.tools)
        message.usage = Usage(input_tokens=input_tokens, output_tokens=_output_tokens(message))
        return message


class Messages:
    """The ``client.messages`` resource."""

    def __init__(self, client: MockClient) -> None:
        """Bind the resource to its client.

        Args:
            client: The owning client.
        """
        self._client = client

    def create(self, **kwargs: Any) -> Any:
        """Send a request and return the model's response.

        Args:
            **kwargs: ``model``, ``max_tokens``, ``messages`` and the optional request fields.

        Returns:
            A :class:`Message`, or an iterator of :class:`StreamEvent` when ``stream=True``.
        """
        if kwargs.pop("stream", False):
            return iter(_events(self._client._respond(kwargs)))
        return self._client._respond(kwargs)

    def stream(self, **kwargs: Any) -> MessageStream:
        """Send a request and stream the response, like the SDK's ``messages.stream`` helper.

        Args:
            **kwargs: The same arguments as :meth:`create`.

        Returns:
            A context manager with ``text_stream`` and ``get_final_message()``.
        """
        kwargs.pop("stream", None)
        return MessageStream(self._client._respond(kwargs))

    def count_tokens(self, **kwargs: Any) -> MessageTokensCount:
        """Estimate the input tokens of a request without generating anything.

        Args:
            **kwargs: ``model``, ``messages`` and optionally ``system`` and ``tools``.

        Returns:
            The estimated count.
        """
        kwargs.setdefault("max_tokens", 1)
        request = build_request(kwargs, self._client._rng)
        return MessageTokensCount(estimate_request_tokens(request.messages, system=request.system, tools=request.tools))


@dataclass
class Delta:
    """The ``delta`` of a streaming event.

    Attributes:
        type: ``text_delta``, ``input_json_delta`` or ``message_delta``.
        text: New text, for ``text_delta``.
        partial_json: A fragment of tool input JSON, for ``input_json_delta``.
        stop_reason: Final stop reason, for ``message_delta``.
        stop_sequence: Matched stop sequence, for ``message_delta``.
    """

    type: str
    text: str = ""
    partial_json: str = ""
    stop_reason: StopReason | None = None
    stop_sequence: str | None = None


@dataclass
class StreamEvent:
    """One server-sent event of a streamed response.

    Attributes:
        type: ``message_start``, ``content_block_start``, ``content_block_delta``,
            ``content_block_stop``, ``message_delta`` or ``message_stop``.
        index: Content block index, for block events.
        message: The (empty) message, for ``message_start``.
        content_block: The block being started, for ``content_block_start``.
        delta: The change, for delta events.
        usage: Final usage, for ``message_delta``.
    """

    type: str
    index: int | None = None
    message: Message | None = None
    content_block: ContentBlock | None = None
    delta: Delta | None = None
    usage: Usage | None = None


class MessageStream:
    """A streamed response; iterate it for events or ``text_stream`` for text."""

    def __init__(self, final: Message) -> None:
        """Wrap a finished response so it can be replayed as a stream.

        Args:
            final: The complete response.
        """
        self._final = final
        self._events = iter(_events(final))

    def __enter__(self) -> MessageStream:
        """Enter the ``with`` block.

        Returns:
            The stream itself.
        """
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        """Leave the ``with`` block; nothing to close for the mock."""

    def __iter__(self) -> Iterator[StreamEvent]:
        """Yield the remaining events.

        Returns:
            An iterator of events.
        """
        return self._events

    @property
    def text_stream(self) -> Iterator[str]:
        """Yield only the text fragments, as they arrive.

        Returns:
            An iterator of text fragments.
        """
        return (e.delta.text for e in self._events if e.delta is not None and e.delta.type == "text_delta")

    def get_final_message(self) -> Message:
        """Consume the rest of the stream and return the complete response.

        Returns:
            The accumulated message.
        """
        for _ in self._events:
            pass
        return self._final

    def until_done(self) -> None:
        """Consume the rest of the stream."""
        self.get_final_message()


def _events(final: Message) -> list[StreamEvent]:
    start = copy.copy(final)
    start.content, start.stop_reason = [], "end_turn"
    events = [StreamEvent("message_start", message=start)]
    for index, block in enumerate(final.content):
        if isinstance(block, TextBlock):
            events.append(StreamEvent("content_block_start", index=index, content_block=TextBlock("")))
            pieces = re.findall(r"\S+\s*|\s+", block.text)
            events.extend(
                StreamEvent("content_block_delta", index=index, delta=Delta("text_delta", text=p)) for p in pieces
            )
        else:
            empty = ToolUseBlock(id=block.id, name=block.name, input={})
            events.append(StreamEvent("content_block_start", index=index, content_block=empty))
            raw = json.dumps(block.input)
            chunks = [raw[i : i + 16] for i in range(0, len(raw), 16)]
            events.extend(
                StreamEvent("content_block_delta", index=index, delta=Delta("input_json_delta", partial_json=c))
                for c in chunks
            )
        events.append(StreamEvent("content_block_stop", index=index))
    final_delta = Delta("message_delta", stop_reason=final.stop_reason, stop_sequence=final.stop_sequence)
    events.append(StreamEvent("message_delta", delta=final_delta, usage=Usage(output_tokens=final.usage.output_tokens)))
    events.append(StreamEvent("message_stop"))
    return events


def _check_strict_tools(message: Message, request: Request) -> None:
    for block in message.content:
        if not isinstance(block, ToolUseBlock):
            continue
        tool = request.tool(block.name)
        if tool is None:
            if not request.tools:
                raise MockScriptError(f"the script calls tool {block.name!r} but the request offered no tools")
            continue
        if tool.get("strict"):
            problems = validate(block.input, tool["input_schema"])
            if problems:
                raise MockScriptError(f"strict tool {block.name!r} got invalid scripted input: {'; '.join(problems)}")


def _apply_stop_sequences(message: Message, stops: list[str]) -> None:
    if not stops or message.stop_reason not in {"end_turn", "tool_use"}:
        return
    for index, block in enumerate(message.content):
        if not isinstance(block, TextBlock):
            continue
        hits = [(block.text.find(s), s) for s in stops if s in block.text]
        if hits:
            position, sequence = min(hits)
            block.text = block.text[:position]
            message.content = [b for b in message.content[: index + 1] if not isinstance(b, TextBlock) or b.text]
            message.stop_reason, message.stop_sequence = "stop_sequence", sequence
            return


def _apply_max_tokens(message: Message, max_tokens: int) -> None:
    budget = max_tokens * CHARS_PER_TOKEN
    kept: list[ContentBlock] = []
    for block in message.content:
        size = len(block.text) if isinstance(block, TextBlock) else len(json.dumps(block.input)) + len(block.name)
        if size <= budget:
            kept.append(block)
            budget -= size
            continue
        if isinstance(block, TextBlock) and budget > 0:
            kept.append(TextBlock(block.text[:budget]))
        message.content, message.stop_reason, message.stop_sequence = kept, "max_tokens", None
        return


def _check_output_format(message: Message, request: Request) -> None:
    fmt = request.output_config.get("format")
    if not fmt or message.stop_reason != "end_turn":
        return
    try:
        data = json.loads(message.text)
    except json.JSONDecodeError as exc:
        raise MockScriptError(f"output_config.format is set but the scripted reply is not JSON: {exc}") from exc
    problems = validate(data, fmt["schema"])
    if problems:
        raise MockScriptError(f"the scripted reply does not match output_config.format: {'; '.join(problems)}")


def _output_tokens(message: Message) -> int:
    total = 0
    for block in message.content:
        total += (
            estimate_tokens(block.text) if isinstance(block, TextBlock) else estimate_tokens(json.dumps(block.input))
        )
    return total
