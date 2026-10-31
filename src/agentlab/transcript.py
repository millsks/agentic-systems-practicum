"""Readable one-line-per-block rendering of a conversation, for debugging agent runs."""

import json
from typing import Any

from agentlab.blocks import Message

_LIMIT = 160


def as_dict(block: object) -> dict[str, Any]:
    """Convert a content block object or dict into a plain dict.

    Args:
        block: A dict, or any object with a ``to_dict()`` method (agentlab or SDK blocks).

    Returns:
        A plain dict.

    Raises:
        TypeError: The block is neither a dict nor convertible.
    """
    if isinstance(block, dict):
        return block
    for method in ("to_dict", "model_dump"):
        convert = getattr(block, method, None)
        if callable(convert):
            result = convert()
            if isinstance(result, dict):
                return result
    raise TypeError(f"cannot convert {type(block).__name__} to a content block dict")


def format_block(block: dict[str, Any]) -> str:
    """Render one content block as a short line.

    Args:
        block: A content block as a dict.

    Returns:
        Text such as ``tool_use get_weather {"city": "Paris"} [toolu_01]``.
    """
    kind = block.get("type")
    if kind == "text":
        return _clip(str(block.get("text", "")))
    if kind == "tool_use":
        return f"tool_use {block.get('name')} {_clip(json.dumps(block.get('input', {})))} [{block.get('id')}]"
    if kind == "tool_result":
        flag = " (error)" if block.get("is_error") else ""
        return f"tool_result [{block.get('tool_use_id')}]{flag} {_clip(_result_text(block.get('content', '')))}"
    return f"{kind} block"


def format_transcript(messages: list[dict[str, Any]], response: Message | None = None) -> str:
    """Render a conversation, and optionally the latest response, one block per line.

    Args:
        messages: Conversation history.
        response: A response not yet appended to ``messages``.

    Returns:
        Lines like ``user: What is 2+2?`` and ``assistant: 4``, joined by newlines.
    """
    lines: list[str] = []
    turns: list[tuple[str, object]] = [(str(m.get("role")), m.get("content", "")) for m in messages]
    if response is not None:
        turns.append(("assistant", response.content))
    for role, content in turns:
        if isinstance(content, str):
            lines.append(f"{role}: {_clip(content)}")
            continue
        for block in content if isinstance(content, list) else []:
            lines.append(f"{role}: {format_block(as_dict(block))}")
    if response is not None:
        lines.append(f"(stop_reason={response.stop_reason})")
    return "\n".join(lines)


def _result_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(as_dict(b).get("text", "")) for b in content)
    return str(content)


def _clip(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= _LIMIT else flat[: _LIMIT - 3] + "..."
