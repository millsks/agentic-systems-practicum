import random
from typing import Any

import pytest

import agentlab as al
from agentlab.request import build_request

TOOL = {"name": "t", "description": "d", "input_schema": {"type": "object"}}


def build(**kwargs: Any) -> al.Request:
    base: dict[str, Any] = {"model": al.MODEL, "max_tokens": 10, "messages": [{"role": "user", "content": "hi"}]}
    return build_request({**base, **kwargs}, random.Random(0))


def bad(match: str, **kwargs: Any) -> None:
    with pytest.raises(al.BadRequestError, match=match):
        build(**kwargs)


def test_valid_request_defaults() -> None:
    request = build(system="s", output_config={"effort": "high"}, tool_choice={"type": "auto"})
    assert request.effort == "high"
    assert build().effort == "medium"
    assert request.tool_results == []


@pytest.mark.parametrize("name", ["temperature", "top_p", "top_k"])
def test_sampling_parameters_are_rejected(name: str) -> None:
    bad("sampling parameters", **{name: 0.5})


def test_argument_errors() -> None:
    with pytest.raises(TypeError, match="unexpected keyword"):
        build(bogus=1)
    with pytest.raises(TypeError, match="'model'"):
        build(model="")
    with pytest.raises(TypeError, match="'max_tokens'"):
        build(max_tokens=True)
    with pytest.raises(al.NotFoundError):
        build(model="gpt-x")
    bad("between 1 and", max_tokens=0)


def test_option_errors() -> None:
    bad("adaptive", thinking={"type": "enabled", "budget_tokens": 1024})
    build(thinking={"type": "adaptive"})
    bad("not supported for this model", tool_choice={"type": "any"})
    bad("must be one of 'auto'", tool_choice={"type": "x"})
    bad("must be an object", output_config="high")
    bad("effort", output_config={"effort": "extreme"})
    bad("json_schema", output_config={"format": {"type": "json"}})
    bad("stop_sequences", stop_sequences=[""])
    bad("system", system=3)


def test_tool_definition_errors() -> None:
    bad("must be a list", tools={})
    bad("must be an object", tools=["t"])
    bad("name", tools=[{**TOOL, "name": "has space"}])
    bad("unique", tools=[TOOL, TOOL])
    bad("input_schema", tools=[{**TOOL, "input_schema": {"type": "string"}}])


def test_message_shape_errors() -> None:
    bad("at least one message", messages=[])
    bad("must be an object", messages=["hi"])
    bad("must be 'user' or 'assistant'", messages=[{"role": "robot", "content": "x"}])
    bad("system message cannot be the first", messages=[{"role": "system", "content": "x"}])
    bad("non-empty", messages=[{"role": "user", "content": "  "}])
    bad("non-empty string or list", messages=[{"role": "user", "content": []}])
    bad("text content blocks must be non-empty", messages=[{"role": "user", "content": [{"type": "text", "text": ""}]}])
    bad("cannot convert", messages=[{"role": "user", "content": [object()]}])
    bad(
        "first message must use the 'user' role",
        messages=[{"role": "assistant", "content": "x"}, {"role": "user", "content": "y"}],
    )
    bad("prefilling", messages=[{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}])


def call(tool_id: str = "a") -> dict[str, Any]:
    return {"role": "assistant", "content": [al.ToolUseBlock(id=tool_id, name="t", input={})]}


def result(*ids: str, text_first: bool = False) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = [{"type": "tool_result", "tool_use_id": i, "content": "ok"} for i in ids]
    if text_first:
        blocks.insert(0, {"type": "text", "text": "note"})
    return {"role": "user", "content": blocks}


def test_tool_pairing_rules() -> None:
    first = {"role": "user", "content": "go"}
    ok = build(messages=[first, call(), result("a")])
    assert ok.tool_results[0]["tool_use_id"] == "a"
    bad("without tool_result blocks", messages=[first, call(), {"role": "user", "content": "next"}])
    bad("without tool_result blocks", messages=[first, call(), result("b")])
    bad("must come before any other content", messages=[first, call(), result("a", text_first=True)])
    bad("must answer tool_use blocks", messages=[first, result("a")])
    unknown = {"role": "user", "content": [*result("a")["content"], *result("z")["content"]]}
    bad("unknown tool_use id z", messages=[first, call(), unknown])


def test_last_user_text_skips_tool_results_and_reads_blocks() -> None:
    blocks = {"role": "user", "content": [{"type": "text", "text": "one"}, {"type": "text", "text": "two"}]}
    assert build(messages=[blocks]).last_user_text == "one two"
    assert build(messages=[{"role": "user", "content": "x"}, call(), result("a")]).last_user_text == ""
