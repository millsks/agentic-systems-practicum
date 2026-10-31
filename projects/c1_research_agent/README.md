# Capstone 1: Research Agent

Closes Stage 2 (Tool Use and the Agent Loop). Course page: `docs/projects/c1-research-agent.html`.

## Scenario

You will build `research`, a small agent that answers questions about honeybees from an offline library of 14 short
documents. The model never sees the library directly. It has three tools, `search`, `read`, and `list_sources`, and
your loop runs whatever it asks for until it writes an answer. Every claim in the answer must cite a document as
`[doc-id]`, and your code checks that every cited document was actually read during the run.

The agent talks to the model only through `client.messages.create(...)`, so the same code runs against
`agentlab.MockClient` (the graded tests) and a real `anthropic.Anthropic()` client (the CLI).

## Getting started

```bash
pixi run start c1                          # copies starter/ into work/c1_research_agent/
pixi run grade c1                          # runs the 25 tests against your work/ copy
pixi run practicum grade c1 -k tools -x    # one milestone only, stop at the first failure
```

Run it for real once the tests pass (needs `pixi add anthropic` and `ANTHROPIC_API_KEY`):

```bash
cd work/c1_research_agent
pixi run python -m research "How do honeybees tell each other where food is?"
```

## What is provided

- `research/corpus/*.md`: the library. Each file is one document; its id is the file name without `.md` and its
  title is the `# ` heading.
- `research/corpus.py`: `Document`, `Corpus` (load, `get`, `ids`, `documents`) and `tokenize` (complete).
- `research/cli.py` and `__main__.py`: the command-line entry point, structlog setup, and answer formatting
  (complete).
- `research/agent.py`: `SYSTEM_PROMPT`, the `Answer` dataclass, and `Usage` (fields complete; `Usage.add` is yours).

Everything else raises `NotImplementedError` with `TODO` comments.

## Milestones

1. **Tools** (`tools.py`): `tool_definitions`, `Toolbox.search`, `read`, `list_sources`, `dispatch` (validates input
   with `agentlab.validate`; unknown tools and bad input raise `ToolError`).
2. **Citations** (`citations.py`): `parse_citations` and `check_citations`, pure functions the loop tests rely on.
3. **The loop** (`agent.py`): `Usage.add`, `text_of`, `execute_tool_calls`, `run`. Parallel calls return all results
   in one user message; `run` fills `Answer.citations` and `Answer.citation_problems`.
4. **Errors and stops**: `ToolError` becomes an `is_error` result; `max_steps`, `max_tokens`, and `refusal` end the
   run with `stopped_because` set.
5. **CLI and a live run**: run the agent against Claude and save one transcript.

## Grading

`pixi run grade c1` runs 25 tests in `tests/`. All must pass. The tests never touch the network.

## Stretch goals

- Add `"strict": True` to the tool definitions and explain what it changes and what validation you still need.
- A token or cost budget that stops the run (M11), and loop detection for repeated identical calls.
- An eval set: 10 questions with expected source ids, scored for citation precision and recall against the real API.
- A `quote` check: every sentence that cites `[x]` shares at least one keyword with document `x`.
