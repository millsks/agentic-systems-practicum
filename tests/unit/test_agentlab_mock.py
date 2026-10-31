from typing import Any

import pytest

import agentlab as al
from agentlab.request import Request

WEATHER = {
    "name": "get_weather",
    "description": "Current weather for a city.",
    "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
}


def ask(client: al.MockClient, messages: list[dict[str, Any]], **kwargs: Any) -> al.Message:
    return client.messages.create(model=al.MODEL, max_tokens=kwargs.pop("max_tokens", 200), messages=messages, **kwargs)  # type: ignore[no-any-return]


def user(text: str) -> list[dict[str, Any]]:
    return [{"role": "user", "content": text}]


def test_string_step_is_a_reply_with_usage_and_ids() -> None:
    client = al.MockClient(["Paris."])
    response = ask(client, user("Capital of France?"))
    assert response.text == "Paris."
    assert response.stop_reason == "end_turn"
    assert response.model == al.MODEL
    assert response.id.startswith("msg_mock_")
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens == 2
    assert client.remaining == 0
    assert client.requests[0].last_user_text == "Capital of France?"


def test_full_tool_round_trip_records_requests() -> None:
    client = al.MockClient([al.tool_call("get_weather", {"city": "Paris"}, text="Checking."), "18C in Paris."])
    messages = user("Weather in Paris?")
    first = ask(client, messages, tools=[WEATHER])
    assert first.stop_reason == "tool_use"
    call = first.content[1]
    assert isinstance(call, al.ToolUseBlock)
    assert call.id.startswith("toolu_mock_")
    messages.append({"role": "assistant", "content": first.content})
    messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": call.id, "content": "18C"}]})
    second = ask(client, messages, tools=[WEATHER])
    assert second.text == "18C in Paris."
    request = client.requests[1]
    assert request.turn == 1
    assert request.tool_names == ["get_weather"]
    assert request.tool_results[0]["tool_use_id"] == call.id
    assert request.tool("missing") is None


def test_parallel_calls_keep_explicit_ids() -> None:
    client = al.MockClient(
        [al.tool_calls([("get_weather", {"city": "A"}), ("get_weather", {"city": "B"})], ids=["t1", "t2"])]
    )
    response = ask(client, user("A and B?"), tools=[WEATHER])
    assert [b.id for b in response.content if isinstance(b, al.ToolUseBlock)] == ["t1", "t2"]


def test_callable_step_and_responder_and_exhaustion() -> None:
    def echo(request: Request) -> str:
        return f"you said {request.last_user_text}"

    client = al.MockClient([echo], responder=lambda r: "fallback")
    assert ask(client, user("hi")).text == "you said hi"
    assert ask(client, user("again")).text == "fallback"
    bare = al.MockClient([])
    with pytest.raises(al.MockScriptError, match="used up after 0"):
        ask(bare, user("hi"))


def test_one_of_is_seeded() -> None:
    picks = {ask(al.MockClient([al.one_of("a", "b", "c")], seed=s), user("x")).text for s in range(20)}
    assert picks == {"a", "b", "c"}
    again = [ask(al.MockClient([al.one_of("a", "b", "c")], seed=3), user("x")).text for _ in range(2)]
    assert again[0] == again[1]


def test_fail_and_refusal_steps() -> None:
    client = al.MockClient([al.fail(al.RateLimitError(retry_after=2.5)), al.refusal("cyber")])
    with pytest.raises(al.RateLimitError) as caught:
        ask(client, user("x"))
    assert caught.value.retry_after == 2.5
    assert caught.value.status_code == 429
    refused = ask(client, user("x"))
    assert refused.stop_reason == "refusal"
    assert refused.content == []
    assert refused.stop_details is not None and refused.stop_details.category == "cyber"


def test_max_tokens_truncates_text_and_drops_tool_calls() -> None:
    client = al.MockClient(["word " * 50, al.tool_call("get_weather", {"city": "Paris" * 20}, text="ok")])
    cut = ask(client, user("x"), max_tokens=5)
    assert cut.stop_reason == "max_tokens"
    assert len(cut.text) == 20
    dropped = ask(client, user("x"), max_tokens=3, tools=[WEATHER])
    assert dropped.stop_reason == "max_tokens"
    assert [b.type for b in dropped.content] == ["text"]


def test_stop_sequences_cut_text() -> None:
    client = al.MockClient(["one, two, STOP three", "no match here", "STOP at start"])
    first = ask(client, user("x"), stop_sequences=["STOP", "two"])
    assert first.text == "one, "
    assert first.stop_reason == "stop_sequence"
    assert first.stop_sequence == "two"
    assert ask(client, user("x"), stop_sequences=["STOP"]).stop_reason == "end_turn"
    empty = ask(client, user("x"), stop_sequences=["STOP"])
    assert empty.content == [] and empty.stop_sequence == "STOP"


def test_output_format_checks_scripted_json() -> None:
    schema = {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}
    fmt = {"format": {"type": "json_schema", "schema": schema}}
    client = al.MockClient(['{"n": 3}', "not json", '{"n": "x"}'])
    assert ask(client, user("x"), output_config=fmt).text == '{"n": 3}'
    with pytest.raises(al.MockScriptError, match="not JSON"):
        ask(client, user("x"), output_config=fmt)
    with pytest.raises(al.MockScriptError, match="does not match"):
        ask(client, user("x"), output_config=fmt)


def test_strict_tools_and_undeclared_tools() -> None:
    strict = {**WEATHER, "strict": True}
    client = al.MockClient([al.tool_call("get_weather", {"city": 3}), al.tool_call("other", {}), al.tool_call("x")])
    with pytest.raises(al.MockScriptError, match="strict tool"):
        ask(client, user("x"), tools=[strict])
    assert ask(client, user("x"), tools=[WEATHER]).content[0].type == "tool_use"
    with pytest.raises(al.MockScriptError, match="offered no tools"):
        ask(client, user("x"))


def test_stream_helper_and_events() -> None:
    client = al.MockClient(["Hello there world", al.tool_call("get_weather", {"city": "Paris"}), "done"])
    with client.messages.stream(model=al.MODEL, max_tokens=100, messages=user("hi")) as stream:
        assert "".join(stream.text_stream) == "Hello there world"
        final = stream.get_final_message()
    assert final.text == "Hello there world"
    with client.messages.stream(model=al.MODEL, max_tokens=100, messages=user("hi"), tools=[WEATHER], stream=True) as s:
        events = list(s)
        s.until_done()
    kinds = [e.type for e in events]
    assert kinds[0] == "message_start" and kinds[-1] == "message_stop"
    assert "".join(e.delta.partial_json for e in events if e.delta and e.delta.type == "input_json_delta") == (
        '{"city": "Paris"}'
    )
    stop = next(e for e in events if e.type == "message_delta")
    assert stop.delta is not None and stop.delta.stop_reason == "tool_use"
    raw = list(client.messages.create(model=al.MODEL, max_tokens=50, messages=user("x"), stream=True))
    assert raw[1].type == "content_block_start"


def test_count_tokens() -> None:
    client = al.MockClient()
    count = client.messages.count_tokens(model=al.MODEL, messages=user("a" * 40), system="b" * 8)
    assert count.input_tokens == 10 + 2 + 3


def test_message_serialization() -> None:
    response = ask(al.MockClient([al.tool_call("get_weather", {"city": "P"}, text="t")]), user("x"), tools=[WEATHER])
    data = response.to_dict()
    assert data["content"][1]["name"] == "get_weather"
    assert '"stop_reason": "tool_use"' in response.to_json()
