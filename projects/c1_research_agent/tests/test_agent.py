"""Milestones 3 and 4: the agent loop, graded against scripted model runs."""

from typing import Any

from research import SYSTEM_PROMPT, run

import agentlab as al

QUESTION = "How do honeybees tell nestmates where food is?"
GOOD_ANSWER = "Foragers perform a waggle dance whose angle gives direction and duration gives distance [waggle-dance]."


def roles(messages: list[dict[str, Any]]) -> list[str]:
    return [m["role"] for m in messages]


def test_single_search_then_answer() -> None:
    client = al.MockClient([al.tool_call("search", {"query": "waggle dance"}, id="toolu_1"), "Bees dance."])
    answer = run(client, QUESTION)
    assert answer.text == "Bees dance.", "the final text is the model's last reply"
    assert answer.stopped_because == "end_turn"
    assert answer.steps == 2, "one request per model call: tool call, then the answer"
    results = client.requests[1].tool_results
    assert len(results) == 1 and results[0]["tool_use_id"] == "toolu_1", "answer the tool_use with its own id"
    assert "[waggle-dance]" in results[0]["content"], "the search result content goes back to the model"
    assert not results[0].get("is_error"), "a successful call is not an error"


def test_chained_search_read_answer_with_sound_citations() -> None:
    client = al.MockClient(
        [
            al.tool_call("search", {"query": "waggle dance"}),
            al.tool_call("read", {"doc_id": "waggle-dance"}),
            GOOD_ANSWER,
        ]
    )
    answer = run(client, QUESTION)
    assert answer.steps == 3
    assert "angle of the waggle run" in client.requests[2].tool_results[0]["content"], "read returns the full text"
    assert answer.read_ids == ["waggle-dance"], "the run records which documents were read"
    assert answer.citations == ["waggle-dance"], "citations are parsed from the final text"
    assert answer.citation_problems == [], "a citation of a document read in this run is sound"
    assert answer.ok, "end_turn with sound citations is a good answer"


def test_parallel_reads_go_back_in_one_user_message() -> None:
    client = al.MockClient(
        [
            al.tool_calls([("read", {"doc_id": "swarming"}), ("read", {"doc_id": "waggle-dance"})], ids=["t_a", "t_b"]),
            "Scouts dance for nest sites [swarming] [waggle-dance].",
        ]
    )
    answer = run(client, "How do swarms pick a home?")
    last = client.requests[1].messages[-1]
    assert last["role"] == "user", "tool results travel in a user message"
    ids = [b["tool_use_id"] for b in last["content"]]
    assert ids == ["t_a", "t_b"], "all results go in ONE user message, in the same order as the tool_use blocks"
    assert answer.read_ids == ["swarming", "waggle-dance"]
    assert answer.ok, f"both cited documents were read; problems: {answer.citation_problems}"


def test_tool_error_is_reported_and_the_agent_recovers() -> None:
    client = al.MockClient(
        [
            al.tool_call("read", {"doc_id": "bee-dances"}),
            al.tool_call("read", {"doc_id": "waggle-dance"}),
            GOOD_ANSWER,
        ]
    )
    answer = run(client, QUESTION)
    error = client.requests[1].tool_results[0]
    assert error["is_error"] is True, "a failed tool call must come back with is_error: True, not crash the run"
    assert "bee-dances" in error["content"] and "search" in error["content"], "the error message must be actionable"
    assert answer.ok and answer.read_ids == ["waggle-dance"], "the agent keeps going after an error"


def test_unknown_tool_becomes_an_error_result() -> None:
    client = al.MockClient([al.tool_call("web_search", {"query": "bees"}), "I could not search the web."])
    answer = run(client, QUESTION)
    result = client.requests[1].tool_results[0]
    assert result["is_error"] is True, "an unknown tool name is an error result, not an exception"
    assert "web_search" in result["content"], "say which tool name was unknown"
    assert answer.stopped_because == "end_turn"


def test_invalid_input_is_rejected_before_the_tool_runs() -> None:
    client = al.MockClient([al.tool_call("search", {"q": "wax"}), al.tool_call("search", {"query": "wax"}), "Done."])
    run(client, "What is comb made of?")
    result = client.requests[1].tool_results[0]
    assert result["is_error"] is True, "input that does not match the schema is an error result"
    assert "query" in result["content"], "the validation message names the missing property"
    assert not client.requests[2].tool_results[0].get("is_error"), "the corrected call succeeds"


def test_max_steps_stops_a_runaway_agent() -> None:
    client = al.MockClient(responder=lambda request: al.tool_call("search", {"query": "bees"}))
    answer = run(client, QUESTION, max_steps=3)
    assert len(client.requests) == 3, "max_steps=3 allows exactly three model calls"
    assert answer.steps == 3
    assert answer.stopped_because == "max_steps", "report why the run ended"
    assert not answer.ok, "a run that never answered is not ok"


def test_refusal_ends_the_run() -> None:
    client = al.MockClient([al.refusal("cyber", "Declined.")])
    answer = run(client, QUESTION)
    assert answer.stopped_because == "refusal"
    assert answer.steps == 1 and answer.text == "", "a refusal has no content to read"
    assert answer.detail == "Declined.", "keep stop_details.explanation in Answer.detail"
    assert not answer.ok


def test_max_tokens_returns_the_partial_text() -> None:
    client = al.MockClient(["Foragers perform a waggle dance on the comb to share where flowers are [waggle-dance]."])
    answer = run(client, QUESTION, max_tokens=8)
    assert client.requests[0].max_tokens == 8, "pass max_tokens through to every request"
    assert answer.stopped_because == "max_tokens", "a truncated reply must be reported, not treated as complete"
    assert answer.text.startswith("Foragers perform"), "return the partial text so the caller can see it"
    assert not answer.ok


def test_citing_an_unread_document_is_flagged() -> None:
    client = al.MockClient(
        [al.tool_call("search", {"query": "varroa"}), "Mites spread viruses [varroa-mite] [colony-collapse-disorder]."]
    )
    answer = run(client, "What harms colonies?")
    assert answer.stopped_because == "end_turn"
    assert answer.citations == ["varroa-mite", "colony-collapse-disorder"]
    assert len(answer.citation_problems) == 2, "search snippets do not count as reading: both citations are unread"
    assert not answer.ok, "an answer with unread citations is not ok"


def test_requests_are_well_formed() -> None:
    client = al.MockClient(
        [
            al.tool_call("search", {"query": "drones"}, text="Let me look that up."),
            al.tool_call("read", {"doc_id": "drones"}),
            "Drones mate and die [drones].",
        ]
    )
    answer = run(client, "What do drones do?")
    for request in client.requests:
        assert request.model.startswith("claude-"), "use a real model id such as claude-opus-5-5"
        assert request.system == SYSTEM_PROMPT, "send the system prompt on every request (the API is stateless)"
        assert request.tool_names == ["search", "read", "list_sources"], "send the tool definitions every time"
        assert request.messages[0] == {"role": "user", "content": "What do drones do?"}, "start with the question"
    final = client.requests[-1].messages
    assert roles(final) == ["user", "assistant", "user", "assistant", "user"], "history alternates user/assistant"
    first_turn = final[1]["content"]
    assert first_turn[0] == {"type": "text", "text": "Let me look that up."}, "append response.content, text included"
    assert first_turn[1]["type"] == "tool_use", "keep the tool_use block in the assistant turn"
    assert roles(answer.messages) == [*roles(final), "assistant"], "Answer.messages holds the full history"


def test_usage_is_totalled_across_requests() -> None:
    client = al.MockClient([al.tool_call("read", {"doc_id": "propolis"}), "Bee glue [propolis]."])
    answer = run(client, "What is propolis?")
    expected_input = sum(
        al.estimate_request_tokens(r.messages, system=r.system, tools=r.tools) for r in client.requests
    )
    assert answer.usage.input_tokens == expected_input, "sum usage.input_tokens over every response"
    assert answer.usage.output_tokens > 0, "sum usage.output_tokens over every response"
