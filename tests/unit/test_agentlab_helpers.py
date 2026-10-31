import sys
import types
from typing import Any

import pytest

import agentlab as al
from agentlab.errors import APIStatusError


def test_validate_types_and_bounds() -> None:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 2, "maxLength": 4},
            "age": {"type": "integer", "minimum": 0, "maximum": 130},
            "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
            "kind": {"enum": ["a", "b"]},
            "fixed": {"const": 1},
            "maybe": {"type": ["string", "null"]},
        },
        "required": ["name", "age"],
        "additionalProperties": False,
    }
    assert al.validate({"name": "Ann", "age": 3.0, "tags": ["x"], "kind": "a", "fixed": 1, "maybe": None}, schema) == []
    problems = al.validate({"name": "A", "age": 200, "tags": [1, 2, 3], "kind": "z", "fixed": 2, "extra": 1}, schema)
    assert "$.name: length 1 is below minLength 2" in problems
    assert "$.age: value 200 is above maximum 130" in problems
    assert "$.tags: item count 3 is above maxItems 2" in problems
    assert "$.tags[0]: expected string, got int" in problems
    assert "$.kind: 'z' is not one of ['a', 'b']" in problems
    assert "$.fixed: expected 1" in problems
    assert "$: unexpected property 'extra'" in problems
    assert al.validate({}, schema) == ["$: missing required property 'name'", "$: missing required property 'age'"]
    assert al.validate(True, {"type": "integer"}) == ["$: expected integer, got bool"]
    assert al.validate(1.5, {"type": "integer"}) == ["$: expected integer, got float"]
    assert al.validate(None, {"type": "string"}) == ["$: expected string, got null"]
    assert al.validate("abcdef", {"maxLength": 3}) == ["$: length 6 is above maxLength 3"]
    assert al.validate(-1, {"minimum": 0}) == ["$: value -1 is below minimum 0"]


def test_token_estimates() -> None:
    assert al.estimate_tokens("") == 0
    assert al.estimate_tokens("abcde") == 2
    blocks = [{"type": "text", "text": "x" * 8}]
    total = al.estimate_request_tokens(
        [{"role": "user", "content": "a" * 8}, {"role": "assistant", "content": blocks}],
        system=[{"type": "text", "text": "s" * 4}],
        tools=[{"name": "t"}],
    )
    assert total > 2 + 1 + 6


def test_format_transcript_and_blocks() -> None:
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "What is " + "very " * 60 + "big?"},
        {"role": "assistant", "content": [al.ToolUseBlock(id="t1", name="calc", input={"x": 1})]},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "t1",
                    "content": [{"type": "text", "text": "boom"}],
                    "is_error": True,
                }
            ],
        },
        {
            "role": "user",
            "content": [{"type": "image", "source": {}}, {"type": "tool_result", "tool_use_id": "t2", "content": 7}],
        },
    ]
    response = al.Message(content=[al.TextBlock("Done.")], stop_reason="end_turn")
    text = al.format_transcript(messages, response)
    lines = text.splitlines()
    assert lines[0].endswith("...") and len(lines[0]) <= 166
    assert lines[1] == 'assistant: tool_use calc {"x": 1} [t1]'
    assert lines[2] == "user: tool_result [t1] (error) boom"
    assert lines[3] == "user: image block"
    assert lines[4] == "user: tool_result [t2] 7"
    assert lines[-2:] == ["assistant: Done.", "(stop_reason=end_turn)"]


def test_as_dict_variants() -> None:
    assert al.as_dict({"type": "text"}) == {"type": "text"}

    class Pydanticish:
        def model_dump(self) -> dict[str, str]:
            return {"type": "text", "text": "hi"}

    assert al.as_dict(Pydanticish())["text"] == "hi"
    with pytest.raises(TypeError):
        al.as_dict(42)


def test_usage_and_errors() -> None:
    assert al.Usage(1, 2).to_dict()["output_tokens"] == 2
    assert al.BadRequestError("x").status_code == 400
    assert APIStatusError("teapot", status_code=418).status_code == 418
    assert al.OverloadedError("busy").status_code == 529
    assert al.InternalServerError("x").message == "x"
    assert issubclass(al.APIConnectionError, al.APIError)


def test_get_client_without_and_with_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "anthropic", None)
    with pytest.raises(al.LiveModelUnavailableError):
        al.get_client()
    fake = types.ModuleType("anthropic")
    fake.Anthropic = lambda **options: ("client", options)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    assert al.get_client(max_retries=5) == ("client", {"max_retries": 5})
