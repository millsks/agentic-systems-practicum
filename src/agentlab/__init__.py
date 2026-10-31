"""agentlab: the practicum's teaching library: a scripted mock of the Messages API and small helpers."""

from agentlab.blocks import Message, MessageTokensCount, StopDetails, TextBlock, ToolUseBlock, Usage
from agentlab.errors import (
    APIConnectionError,
    APIError,
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    MockScriptError,
    NotFoundError,
    OverloadedError,
    RateLimitError,
)
from agentlab.live import LiveModelUnavailableError, get_client
from agentlab.mock import (
    Failure,
    MessageStream,
    MockClient,
    StreamEvent,
    fail,
    one_of,
    refusal,
    reply,
    tool_call,
    tool_calls,
)
from agentlab.request import DEFAULT_MODEL, Request
from agentlab.schema import validate
from agentlab.tokens import estimate_request_tokens, estimate_tokens
from agentlab.transcript import as_dict, format_block, format_transcript

MODEL = DEFAULT_MODEL

__all__ = [
    "DEFAULT_MODEL",
    "MODEL",
    "APIConnectionError",
    "APIError",
    "APIStatusError",
    "AuthenticationError",
    "BadRequestError",
    "Failure",
    "InternalServerError",
    "LiveModelUnavailableError",
    "Message",
    "MessageStream",
    "MessageTokensCount",
    "MockClient",
    "MockScriptError",
    "NotFoundError",
    "OverloadedError",
    "RateLimitError",
    "Request",
    "StopDetails",
    "StreamEvent",
    "TextBlock",
    "ToolUseBlock",
    "Usage",
    "as_dict",
    "estimate_request_tokens",
    "estimate_tokens",
    "fail",
    "format_block",
    "format_transcript",
    "get_client",
    "one_of",
    "refusal",
    "reply",
    "tool_call",
    "tool_calls",
    "validate",
]
