"""Rough token estimates for offline exercises; real counts come from ``messages.count_tokens``."""

import json
import math
from typing import Any

CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Estimate how many tokens a piece of text uses.

    English prose averages about four characters per token. Real tokenizers differ by model and
    language, so use this only to reason about orders of magnitude.

    Args:
        text: Any text.

    Returns:
        ``ceil(len(text) / 4)``; zero for empty text.
    """
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def estimate_request_tokens(
    messages: list[dict[str, Any]],
    *,
    system: str | list[dict[str, Any]] | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> int:
    """Estimate the input tokens of a whole request: tools, system prompt, and every message.

    Args:
        messages: Conversation history as plain dicts.
        system: System prompt as a string or a list of text blocks.
        tools: Tool definitions.

    Returns:
        The estimated input token count.
    """
    parts: list[str] = []
    if tools:
        parts.append(json.dumps(tools, sort_keys=True))
    if isinstance(system, str):
        parts.append(system)
    elif system:
        parts.extend(str(block.get("text", "")) for block in system)
    for message in messages:
        content = message.get("content", "")
        parts.append(content if isinstance(content, str) else json.dumps(content, sort_keys=True, default=str))
    return sum(estimate_tokens(part) for part in parts) + 3 * len(messages)
