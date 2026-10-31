# Authoring Guide

How lesson, project, and reference pages in `docs/` are built. The live gallery of every component is
`docs/authoring/components.html` (`pixi run serve`, then open `/authoring/components.html`).

`pixi run check-site` validates links, anchors, quizzes, exercise test blocks, and visualizer names. It must pass.

## Page skeleton

Module pages live at `docs/modules/<id>-<slug>.html` with the exact `href` from `docs/assets/js/curriculum.js`.
Project pages live at `docs/projects/`, reference pages at `docs/reference/`. All use `data-root="../"`.

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>M09 · The Agent Loop · Agentic Systems Practicum</title>
<link rel="stylesheet" href="../assets/css/course.css">
<script src="../assets/js/curriculum.js"></script>
<script src="../assets/js/agentlab-src.js"></script>
<script src="../assets/js/viz.js" defer></script>
<script src="../assets/js/viz-agent.js" defer></script>
<script src="../assets/js/course.js" defer></script>
</head>
<body data-root="../" data-module="m09">
<main class="lesson">
  <header class="lesson-hero">
    <p class="eyebrow">Stage 2 · Tool Use and the Agent Loop · Module 09</p>
    <h1>Functions</h1>
    <p class="lede">One or two sentences on why this matters.</p>
    <div class="lesson-meta"><span>⏱ ~2.5 hours</span><span>Prerequisites: <a href="m04-control-flow.html">M04</a></span></div>
    <ul class="objectives"><li>…</li></ul>
  </header>
  <section class="lesson-section" id="some-topic"><h2>Some topic</h2> … </section>
  …
</main>
</body>
</html>
```

`course.js` wraps `<main>` with the header, sidebar, table of contents (built from each
`section.lesson-section[id] > h2`), the "Mark complete" box, notes, and previous/next links. Do not write those yourself.
Capstone pages use `data-module="c1"` (the manifest id) so completion tracking works; reference pages use
`data-page="ref-glossary"` etc.

## Required module structure

1. Hero: eyebrow, `h1`, lede, meta (time and prerequisites), objectives (4–7 items).
2. Six to ten teaching sections. Each one explains the idea in plain language, shows a worked example, and makes the
   learner do something: a runnable cell, a `data-predict` cell, a tracer, a visualizer, a transcript to diagnose, or a "think" callout.
3. `id="practice"`: three to six graded exercises, from easy to hard.
4. `id="mini-project"`: a `.project-box` with a small build the learner does locally with Pixi
   (spec, acceptance criteria as a `.checklist`, stretch goals).
5. `id="quiz"`: an end-of-module quiz of 10–15 questions mixing `single`, `multi`, `output`, and `text`.
6. `id="recap"`: a summary list, flashcards (8–12 cards), and "Going further" links to platform.claude.com/docs,
   docs.python.org, and similar.

Write for a motivated beginner who becomes a professional: define every term on first use, explain *why* as well as
*how*, show common mistakes, and finish each section with what to remember. Aim for the depth of a good textbook chapter.

## Components

### Static code

```html
<pre><code class="language-python">x = 1 &lt; 2</code></pre>
<pre data-label="Terminal"><code class="language-bash">pixi run python app.py</code></pre>
```

Escape `<`, `>`, and `&` inside `<pre>`. Languages: python, bash, toml, yaml, json, sql, ini, diff.

### Runnable cells (Pyodide, real CPython in the browser)

```html
<div class="runnable" data-title="Try it">
<textarea>
print("hello")
</textarea>
</div>
```

- Code inside `<textarea>` is written literally (no escaping) and dedented automatically. Never write `</textarea>`.
- `data-predict`: the learner must type a prediction, then Run compares it to the real output.
- `data-stdin="line1\nline2"`: lines fed to `input()`.
- `data-autorun`: run on page load (use sparingly).
- `data-local="reason"`: code that cannot run in the browser (threads needing real parallelism, multiprocessing,
  subprocess, sockets/network, `asyncio.run` with real I/O, packages missing from Pyodide such as torch, polars,
  duckdb, httpx, fastapi, structlog). The reason is shown to the learner.
- Browser packages that load automatically on import: the stdlib and `agentlab`. The real `anthropic` package is not
  available in the browser; cells that need it use `data-local`.
- matplotlib figures are rendered automatically after the cell finishes. Do not call `plt.show()`; it's unnecessary.
- `asyncio`: use top-level `await main()` in browser cells and explain that local scripts use `asyncio.run(main())`.

### Step-through tracer

```html
<div class="tracer" data-title="Watch the recursion">
<textarea>
def fact(n):
    return 1 if n == 0 else n * fact(n - 1)
result = fact(4)
</textarea>
</div>
```

Records every line, call, and return; shows frames, locals, changed values, and object-identity tags (two names with
the same "obj N" tag point to the same object). Keep programs small (under 1500 steps). Optional `data-stdin`.

### Exercises (auto-graded in the browser)

```html
<div class="exercise" data-id="m09-e1" data-title="Write is_even">
  <div class="exercise-prompt"><p>Task description…</p></div>
<textarea class="starter">
def is_even(n):
    ...
</textarea>
  <script type="text/x-python" class="tests">
def test_even():
    assert is_even(4) is True, "is_even(4) should be True"
def test_prints():
    assert program_output.strip() == "ready", "print exactly 'ready'"
  </script>
  <details class="hint"><summary>Hint</summary><p>…</p></details>
  <details class="solution"><summary>Show solution</summary><pre><code class="language-python">…</code></pre></details>
</div>
```

- `data-id` must be unique across the site: `<module id>-e<n>` (for example `m09-e3`).
- Tests are `test_*` functions that run in the learner's namespace after their code. Every assert carries a helpful
  message. `program_output` holds everything the learner's code printed. `capture_output(func, *args, stdin=None)`
  returns `(result, printed_text)`. Tests must not contain `</script>`.
- Verify each solution passes its tests (paste both into `pixi run python` locally).

### Quizzes

```html
<div class="quiz" data-id="m09-quiz">
<script type="application/json">
{"title": "Functions quiz", "passScore": 0.7, "questions": [
  {"type": "single", "prompt": "HTML allowed", "code": "optional python shown above options", "options": ["a", "b"], "answer": 1, "explanation": "<p>Why.</p>"},
  {"type": "multi", "prompt": "…", "options": ["…", "…", "…"], "answer": [0, 2], "explanation": "…"},
  {"type": "output", "prompt": "What does this print?", "code": "print(1 + 1)", "answer": "2", "explanation": "…"},
  {"type": "text", "prompt": "Which keyword…?", "answer": ["def"], "explanation": "…"}
]}
</script>
</div>
```

The payload must be strict JSON (double quotes, no trailing commas, `\n` for newlines inside strings). `answer` is a
0-based index (`single`), a list of indexes (`multi`), or the exact text/accepted list (`output`/`text`; `text` is
case-insensitive). Every question needs an `explanation` that teaches, not just says "correct".

### Callouts, tags, and layout helpers

```html
<aside class="callout note|tip|warn|danger|pixi|pro|think"><p>…</p></aside>
<aside class="callout note" data-title="Custom heading"><p>…</p></aside>
<span class="tag pixi">pixi</span>
<div class="two-col">…</div>   <div class="card-grid"><div class="card"><h4>…</h4>…</div></div>
<div class="tabs"><div class="tab" data-label="Version A">…</div><div class="tab" data-label="Version B">…</div></div>
<details class="reveal"><summary>Reveal</summary>…</details>
<ul class="checklist" data-id="m09-mini">…</ul>          (persisted checkboxes; unique data-id)
<pre class="mermaid">flowchart LR; A-->B</pre>          (Mermaid diagrams)
<figure class="figure"><svg class="diagram" viewBox="…">…</svg><figcaption>…</figcaption></figure>
```

Inline SVG diagrams should use CSS variables for color (`fill="var(--viz-1)"`, `stroke="var(--fg-muted)"`) so they work
in light and dark themes.

### Project box

```html
<div class="project-box">
  <div class="widget-head"><span class="w-kind">Mini-project</span><span class="w-title">Title</span></div>
  <div class="widget-body"> spec, steps, <ul class="checklist" data-id="m09-mini">…</ul> </div>
</div>
```

### Visualizers

```html
<div class="viz" data-viz="NAME" data-config='{"key": "value"}'></div>
```

`data-config` is optional JSON. Available visualizers (`viz-agent.js`):

| Name | Purpose | Config (all optional) |
|---|---|---|
| `agent-loop` | Steps through the loop between your code, the model, and tools while the message list grows | `scenario`: `weather` \| `chain` \| `error` \| `runaway` |
| `token-meter` | Approximate tokens, share of the context window, and input cost for editable text | `text`, `calls`, `title` |

## agentlab: the mock model every exercise uses

Lesson cells and exercises `import agentlab`. In the browser the package is injected into Pyodide from
`assets/js/agentlab-src.js` (generated by `pixi run sync-runtime` from `src/agentlab/`); locally it is installed in the
Pixi environment, so `pixi run check-exercises` runs exactly the same code. Read `reference/agentlab.html` for the
full API. The essentials:

```python
import agentlab as al

client = al.MockClient([
    al.tool_call("get_weather", {"city": "Paris"}),   # step 1: the model asks for a tool
    "It's 18°C in Paris.",                              # step 2: a string is shorthand for al.reply(...)
])
response = client.messages.create(model=al.MODEL, max_tokens=1024, tools=TOOLS, messages=messages)
```

- `MockClient` has the real SDK's surface: `messages.create(...)`, `messages.create(..., stream=True)`,
  `messages.stream(...)` (with `text_stream`, iteration over events, and `get_final_message()`), and
  `messages.count_tokens(...)`. Responses are `al.Message` objects with `.content` (a list of `TextBlock` /
  `ToolUseBlock`), `.stop_reason`, `.stop_sequence`, `.stop_details`, `.usage`, `.id`, `.model`, and a mock-only
  convenience `.text`.
- Script steps, consumed one per request: `al.reply(text)` or a plain string, `al.tool_call(name, input, text=None)`,
  `al.tool_calls([(name, input), ...])` for parallel calls, `al.refusal(category)`, `al.fail(al.RateLimitError())`,
  `al.one_of("a", "b")` (seeded variation), or any function `request -> step`. A `responder=` function answers once the
  script is exhausted. `client.requests` records every validated `al.Request` (`.messages`, `.tools`, `.system`,
  `.last_user_text`, `.tool_results`, `.turn`, `.effort`); exercise tests inspect it.
- The mock validates requests like the API and raises the SDK's exception names: `al.BadRequestError` for a first
  message that is not `user`, a final `assistant` message (prefill), a `tool_use` without a matching `tool_result` in
  the next message, a `tool_result` that does not answer one, `tool_result` blocks after other content, empty text,
  `temperature`/`top_p`/`top_k`, forced `tool_choice` (`any`/`tool`), non-adaptive `thinking`, a bad tool definition.
  `al.NotFoundError` for a model id that does not start with `claude-`. A script that runs out raises
  `al.MockScriptError` (an exercise bug, not a learner bug).
- `max_tokens` truncates scripted text at about 4 characters per token and sets `stop_reason="max_tokens"`;
  `stop_sequences` cut text and set `stop_reason="stop_sequence"`; `output_config.format` checks scripted JSON;
  tools with `"strict": True` check scripted input against the schema.
- Helpers: `al.format_transcript(messages, response=None)` (print it to debug a run), `al.validate(value, schema)`
  (a small JSON Schema validator returning a list of problems), `al.estimate_tokens(text)`,
  `al.estimate_request_tokens(messages, system=, tools=)`, `al.as_dict(block)`.
- `al.get_client()` returns a real `anthropic.Anthropic()` when that package is installed locally; in the browser it
  raises `al.LiveModelUnavailableError`. Use it only in `data-local` cells and mini-projects.

Use `model=al.MODEL` (it is `"claude-opus-5-5"`) in every request so code ports to the real API unchanged.

## Facts about the current Claude API to teach (and never contradict)

- Default model `claude-opus-5-5`; also `claude-sonnet-5-5` and `claude-haiku-5-5`. Never append date suffixes.
  Prices per million tokens (input/output): Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, Haiku 5.5 $0.10/$0.50. 1M-token
  context window, up to 128K output tokens (large values need streaming).
- The API is stateless: send the full history every request. The first message is `user`. Consecutive same-role
  messages are merged. Append `response.content` (the blocks, not just the text) to keep tool and other blocks.
- `temperature`, `top_p` and `top_k` are rejected (400) on current models and API versions. Steer with the prompt and
  `output_config={"effort": "low"|"medium"|"high"|"xhigh"|"max"}`; Opus 5.5 defaults to `medium`.
- Thinking is adaptive (`thinking={"type": "adaptive"}` or omitted); `{"type": "disabled"}` and `budget_tokens` are
  rejected on Opus 5.5. Assistant prefill (ending `messages` with an assistant turn) is rejected.
- Stop reasons: `end_turn`, `max_tokens`, `stop_sequence`, `tool_use`, `pause_turn` (server tools; re-send to
  continue), `refusal` (check `stop_details`). Always check `stop_reason` before reading `content`.
- Tools: `{"name", "description", "input_schema"}` with an object schema; optional `"strict": True` (requires
  `additionalProperties: false` and `required`) guarantees schema-valid input. `tool_choice` is `auto` by default;
  forcing a call (`any` / `tool`) is rejected on Opus 5.5, so steer with the prompt instead.
- Parallel tool use is on by default: return **all** `tool_result` blocks in **one** user message, each with the
  matching `tool_use_id`, before any text. A failed tool returns `"is_error": True` with a helpful message; never drop it.
- Structured output: `output_config={"format": {"type": "json_schema", "schema": {...}}}` (the old `output_format`
  parameter is deprecated). The SDK's `client.messages.parse(...)` validates into a Pydantic model.
- Streaming: `with client.messages.stream(...) as stream:` then `stream.text_stream` and `stream.get_final_message()`.
- The SDK's beta tool runner (`client.beta.messages.tool_runner`, `@beta_tool`) automates the loop; Level 1 teaches
  the manual loop first so learners know what the runner hides. The Claude Agent SDK is a separate product.
- Errors: `anthropic.BadRequestError` (400, fix the request), `AuthenticationError` (401), `NotFoundError` (404),
  `RateLimitError` (429, retry after a delay), `InternalServerError` (5xx) and `APIConnectionError` (retry with
  backoff). The SDK retries 408/409/429/5xx twice by default.
- Credentials come from the environment (`ANTHROPIC_API_KEY` or an `ant auth login` profile). Never put a key in code,
  a notebook, a lesson cell, or a commit.

## Pixi conventions taught by the course

Pixi is the only tool learners use to install Python and packages, and to run code. Never tell the learner to use
`pip install`, `python -m venv`, `uv`, or bare `python`/`pytest`. Use `pixi init`, `pixi add <pkg>` (conda-forge
first; `anthropic` is on conda-forge), `pixi run python file.py`, `pixi run <task>`, and `pixi shell`.
Capstone pages use this repository's helpers: `pixi run projects`, `pixi run start c1`, `pixi run grade c1`.

Lesson cells use `print()` to show results. Mini-projects that build real tools should log with structlog and say why.
