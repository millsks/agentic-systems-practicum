"""Validate ``messages.create`` arguments the way the Messages API does, and expose them to scripts."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any

from agentlab.errors import BadRequestError, NotFoundError
from agentlab.transcript import as_dict

DEFAULT_MODEL = "claude-opus-5-5"
MAX_OUTPUT_TOKENS = 128_000
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
_TOOL_NAME = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_ACCEPTED = frozenset(
    {
        "model",
        "max_tokens",
        "messages",
        "system",
        "tools",
        "tool_choice",
        "stop_sequences",
        "output_config",
        "thinking",
        "metadata",
        "cache_control",
        "stream",
    }
)
_REMOVED_SAMPLING = ("temperature", "top_p", "top_k")


@dataclass
class Request:
    """A validated request, as a scripted step sees it.

    Attributes:
        model: Model id.
        max_tokens: Output token limit.
        messages: Conversation with every content block converted to a plain dict.
        system: System prompt.
        tools: Tool definitions.
        stop_sequences: Strings that end generation.
        output_config: Effort and output format settings.
        tool_choice: Tool choice setting.
        rng: Seeded random generator shared by the client, for steps that vary their output.
    """

    model: str
    max_tokens: int
    messages: list[dict[str, Any]]
    system: str | list[dict[str, Any]] | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)
    stop_sequences: list[str] = field(default_factory=list)
    output_config: dict[str, Any] = field(default_factory=dict)
    tool_choice: dict[str, Any] | None = None
    rng: random.Random = field(default_factory=random.Random, repr=False, compare=False)

    @property
    def last_user_text(self) -> str:
        """Text of the most recent user message, ignoring tool results.

        Returns:
            The joined text, or an empty string.
        """
        for message in reversed(self.messages):
            if message["role"] == "user":
                return _text_of(message["content"])
        return ""

    @property
    def tool_results(self) -> list[dict[str, Any]]:
        """``tool_result`` blocks in the last message, when it is a user message.

        Returns:
            The blocks, in order; empty when the last turn carries none.
        """
        last = self.messages[-1]
        content = last["content"]
        if last["role"] != "user" or isinstance(content, str):
            return []
        return [b for b in content if b.get("type") == "tool_result"]

    @property
    def turn(self) -> int:
        """How many assistant turns the conversation already holds.

        Returns:
            The count; zero on the first request.
        """
        return sum(1 for m in self.messages if m["role"] == "assistant")

    @property
    def tool_names(self) -> list[str]:
        """Names of the tools offered on this request.

        Returns:
            Tool names, in order.
        """
        return [str(t["name"]) for t in self.tools]

    @property
    def effort(self) -> str:
        """Effort level, defaulting to ``medium`` as Claude Opus 5.5 does.

        Returns:
            One of ``low``, ``medium``, ``high``, ``xhigh``, ``max``.
        """
        return str(self.output_config.get("effort", "medium"))

    def tool(self, name: str) -> dict[str, Any] | None:
        """Look up an offered tool by name.

        Args:
            name: Tool name.

        Returns:
            The tool definition, or ``None`` when it was not offered.
        """
        return next((t for t in self.tools if t.get("name") == name), None)


def build_request(kwargs: dict[str, Any], rng: random.Random) -> Request:
    """Validate ``messages.create`` keyword arguments and build a :class:`Request`.

    Args:
        kwargs: The keyword arguments passed to ``create``, ``stream`` or ``count_tokens``.
        rng: The client's random generator.

    Returns:
        The validated request.

    Raises:
        TypeError: An argument the SDK does not accept at all.
        BadRequestError: A request the API would reject with HTTP 400.
        NotFoundError: An unknown model id.
    """
    for name in _REMOVED_SAMPLING:
        if name in kwargs:
            raise BadRequestError(
                f"{name}: sampling parameters are not supported on this API version. "
                "Steer the model with the prompt and output_config.effort instead."
            )
    unknown = sorted(set(kwargs) - _ACCEPTED)
    if unknown:
        raise TypeError(f"create() got an unexpected keyword argument {unknown[0]!r}")
    model = kwargs.get("model")
    if not isinstance(model, str) or not model:
        raise TypeError("create() missing required keyword argument: 'model'")
    if not model.startswith("claude-"):
        raise NotFoundError(f"model: {model}")
    max_tokens = kwargs.get("max_tokens")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool):
        raise TypeError("create() missing required keyword argument: 'max_tokens'")
    if not 1 <= max_tokens <= MAX_OUTPUT_TOKENS:
        raise BadRequestError(f"max_tokens: must be between 1 and {MAX_OUTPUT_TOKENS}, got {max_tokens}")
    _check_thinking(kwargs.get("thinking"))
    tool_choice = _check_tool_choice(kwargs.get("tool_choice"))
    output_config = _check_output_config(kwargs.get("output_config"))
    tools = _check_tools(kwargs.get("tools"))
    messages = _check_messages(kwargs.get("messages"))
    stop = kwargs.get("stop_sequences") or []
    if not isinstance(stop, list) or not all(isinstance(s, str) and s for s in stop):
        raise BadRequestError("stop_sequences: must be a list of non-empty strings")
    system = kwargs.get("system")
    if system is not None and not isinstance(system, str | list):
        raise BadRequestError("system: must be a string or a list of text blocks")
    return Request(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
        system=system,
        tools=tools,
        stop_sequences=list(stop),
        output_config=output_config,
        tool_choice=tool_choice,
        rng=rng,
    )


def _check_thinking(thinking: object) -> None:
    if thinking is None:
        return
    if not isinstance(thinking, dict) or thinking.get("type") != "adaptive":
        raise BadRequestError(
            "thinking: only {'type': 'adaptive'} is supported on this model; control depth with output_config.effort"
        )


def _check_tool_choice(choice: object) -> dict[str, Any] | None:
    if choice is None:
        return None
    if not isinstance(choice, dict) or choice.get("type") not in {"auto", "none", "any", "tool"}:
        raise BadRequestError("tool_choice: type must be one of 'auto', 'none', 'any', 'tool'")
    if choice["type"] in {"any", "tool"}:
        raise BadRequestError('tool_choice: type "tool" and "any" are not supported for this model.')
    return choice


def _check_output_config(config: object) -> dict[str, Any]:
    if config is None:
        return {}
    if not isinstance(config, dict):
        raise BadRequestError("output_config: must be an object")
    effort = config.get("effort")
    if effort is not None and effort not in EFFORT_LEVELS:
        raise BadRequestError(f"output_config.effort: must be one of {', '.join(EFFORT_LEVELS)}")
    fmt = config.get("format")
    if fmt is not None and (
        not isinstance(fmt, dict) or fmt.get("type") != "json_schema" or not isinstance(fmt.get("schema"), dict)
    ):
        raise BadRequestError("output_config.format: expected {'type': 'json_schema', 'schema': {...}}")
    return dict(config)


def _check_tools(tools: object) -> list[dict[str, Any]]:
    if tools is None:
        return []
    if not isinstance(tools, list):
        raise BadRequestError("tools: must be a list")
    seen: set[str] = set()
    checked: list[dict[str, Any]] = []
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            raise BadRequestError(f"tools.{index}: must be an object")
        name = tool.get("name")
        if not isinstance(name, str) or not _TOOL_NAME.match(name):
            raise BadRequestError(f"tools.{index}.name: must match ^[a-zA-Z0-9_-]{{1,64}}$")
        if name in seen:
            raise BadRequestError(f"tools: tool names must be unique, {name!r} appears twice")
        seen.add(name)
        schema = tool.get("input_schema")
        if not isinstance(schema, dict) or schema.get("type") != "object":
            raise BadRequestError(f"tools.{index}.input_schema: must be a JSON Schema with type 'object'")
        checked.append(tool)
    return checked


def _check_messages(messages: object) -> list[dict[str, Any]]:
    if not isinstance(messages, list) or not messages:
        raise BadRequestError("messages: at least one message is required")
    normalized = [_normalize(index, m) for index, m in enumerate(messages)]
    if normalized[0]["role"] != "user":
        raise BadRequestError("messages.0.role: the first message must use the 'user' role")
    if normalized[-1]["role"] == "assistant":
        raise BadRequestError(
            "messages: the final message must not be an assistant message; "
            "prefilling the assistant response is not supported on this model"
        )
    pending: list[str] = []
    for index, message in enumerate(normalized):
        blocks = message["content"] if isinstance(message["content"], list) else []
        if pending:
            _check_results_follow(index, message, blocks, pending)
        elif any(b.get("type") == "tool_result" for b in blocks):
            raise BadRequestError(
                f"messages.{index}: tool_result blocks must answer tool_use blocks in the previous assistant message"
            )
        pending = [str(b["id"]) for b in blocks if message["role"] == "assistant" and b.get("type") == "tool_use"]
    return normalized


def _check_results_follow(
    index: int, message: dict[str, Any], blocks: list[dict[str, Any]], pending: list[str]
) -> None:
    results = [b for b in blocks if b.get("type") == "tool_result"]
    answered = [str(b.get("tool_use_id")) for b in results]
    missing = [tool_id for tool_id in pending if tool_id not in answered]
    if message["role"] != "user" or missing:
        raise BadRequestError(
            f"messages.{index}: tool_use ids were found without tool_result blocks immediately after: "
            f"{', '.join(missing or pending)}. Each tool_use block must have a corresponding tool_result block "
            "in the next message."
        )
    unknown = [tool_id for tool_id in answered if tool_id not in pending]
    if unknown:
        raise BadRequestError(f"messages.{index}: tool_result references unknown tool_use id {unknown[0]}")
    first_other = next((i for i, b in enumerate(blocks) if b.get("type") != "tool_result"), len(blocks))
    if any(b.get("type") == "tool_result" for b in blocks[first_other:]):
        raise BadRequestError(f"messages.{index}: tool_result blocks must come before any other content")


def _normalize(index: int, message: object) -> dict[str, Any]:
    if not isinstance(message, dict):
        raise BadRequestError(f"messages.{index}: must be an object with 'role' and 'content'")
    role = message.get("role")
    if role not in {"user", "assistant", "system"}:
        raise BadRequestError(f"messages.{index}.role: must be 'user' or 'assistant', got {role!r}")
    if role == "system" and index == 0:
        raise BadRequestError("messages.0.role: a system message cannot be the first message")
    content = message.get("content")
    if isinstance(content, str):
        if not content.strip():
            raise BadRequestError(f"messages.{index}.content: text content must be non-empty")
        return {"role": role, "content": content}
    if not isinstance(content, list) or not content:
        raise BadRequestError(f"messages.{index}.content: must be a non-empty string or list of blocks")
    blocks: list[dict[str, Any]] = []
    for position, block in enumerate(content):
        try:
            plain = dict(as_dict(block))
        except TypeError as exc:
            raise BadRequestError(f"messages.{index}.content.{position}: {exc}") from exc
        if plain.get("type") == "text" and not str(plain.get("text", "")).strip():
            raise BadRequestError(f"messages.{index}.content.{position}: text content blocks must be non-empty")
        blocks.append(plain)
    return {"role": role, "content": blocks}


def _text_of(content: str | list[dict[str, Any]]) -> str:
    if isinstance(content, str):
        return content
    return " ".join(str(b.get("text", "")) for b in content if b.get("type") == "text")
