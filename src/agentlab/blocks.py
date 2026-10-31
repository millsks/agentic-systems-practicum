"""Response objects shaped like the Anthropic Python SDK's ``Message`` and content blocks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

StopReason = Literal["end_turn", "max_tokens", "stop_sequence", "tool_use", "pause_turn", "refusal"]


@dataclass
class TextBlock:
    """A block of text the model wrote.

    Attributes:
        text: The text.
        type: Always ``"text"``.
    """

    text: str
    type: Literal["text"] = "text"

    def to_dict(self) -> dict[str, Any]:
        """Return the block as the plain dict the API accepts back in ``messages``.

        Returns:
            ``{"type": "text", "text": ...}``.
        """
        return {"type": "text", "text": self.text}


@dataclass
class ToolUseBlock:
    """A request from the model to call one of your tools.

    Attributes:
        id: Identifier your ``tool_result`` must echo as ``tool_use_id``.
        name: Name of the tool to call.
        input: Arguments, already parsed from JSON.
        type: Always ``"tool_use"``.
    """

    id: str
    name: str
    input: dict[str, Any]
    type: Literal["tool_use"] = "tool_use"

    def to_dict(self) -> dict[str, Any]:
        """Return the block as the plain dict the API accepts back in ``messages``.

        Returns:
            ``{"type": "tool_use", "id": ..., "name": ..., "input": ...}``.
        """
        return {"type": "tool_use", "id": self.id, "name": self.name, "input": dict(self.input)}


ContentBlock = TextBlock | ToolUseBlock


@dataclass
class Usage:
    """Token accounting for one request.

    Attributes:
        input_tokens: Tokens read from the request.
        output_tokens: Tokens the model generated.
        cache_creation_input_tokens: Tokens written to the prompt cache.
        cache_read_input_tokens: Tokens served from the prompt cache.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        """Return the usage as a dict.

        Returns:
            Every counter by name.
        """
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
        }


@dataclass
class StopDetails:
    """Why a request was refused; only set when ``stop_reason`` is ``"refusal"``.

    Attributes:
        category: Refusal category such as ``"cyber"``, or ``None``.
        explanation: Short human-readable reason.
        type: Always ``"refusal"``.
    """

    category: str | None
    explanation: str
    type: Literal["refusal"] = "refusal"


@dataclass
class Message:
    """A model response, shaped like ``anthropic.types.Message``.

    Attributes:
        content: Blocks the model produced, in order.
        stop_reason: Why generation stopped.
        model: Model id that produced the response.
        id: Response id.
        usage: Token accounting.
        stop_sequence: The stop sequence that ended generation, when ``stop_reason`` is ``"stop_sequence"``.
        stop_details: Refusal details, when ``stop_reason`` is ``"refusal"``.
        role: Always ``"assistant"``.
        type: Always ``"message"``.
    """

    content: list[ContentBlock]
    stop_reason: StopReason = "end_turn"
    model: str = ""
    id: str = ""
    usage: Usage = field(default_factory=Usage)
    stop_sequence: str | None = None
    stop_details: StopDetails | None = None
    role: Literal["assistant"] = "assistant"
    type: Literal["message"] = "message"

    @property
    def text(self) -> str:
        """All text blocks joined together; a convenience the real SDK does not have.

        Returns:
            The concatenated text, or an empty string when there is none.
        """
        return "".join(block.text for block in self.content if isinstance(block, TextBlock))

    def to_dict(self) -> dict[str, Any]:
        """Return the response as a plain dict.

        Returns:
            Every field, with blocks and usage converted to dicts.
        """
        return {
            "id": self.id,
            "type": self.type,
            "role": self.role,
            "model": self.model,
            "content": [block.to_dict() for block in self.content],
            "stop_reason": self.stop_reason,
            "stop_sequence": self.stop_sequence,
            "usage": self.usage.to_dict(),
        }

    def to_json(self) -> str:
        """Return the response as indented JSON.

        Returns:
            The JSON text.
        """
        return json.dumps(self.to_dict(), indent=2)


@dataclass(frozen=True)
class MessageTokensCount:
    """Result of ``messages.count_tokens``.

    Attributes:
        input_tokens: Tokens the request would read.
    """

    input_tokens: int
