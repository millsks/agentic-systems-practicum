/* Curriculum manifest. The object below must stay valid JSON: practicum check-site parses it. */
window.CURRICULUM = {
  "title": "Agentic Systems Practicum",
  "python": "3.14",
  "parts": [
    {
      "id": "part0",
      "number": 0,
      "title": "Orientation",
      "level": "Start here",
      "summary": "How the practicum works, the agentlab mock model, running code in the browser and locally, and keeping API keys safe.",
      "modules": [
        {
          "id": "m00",
          "title": "How This Practicum Works",
          "href": "modules/m00-orientation.html",
          "minutes": 45,
          "summary": "What an agent is, the eight-stage path, the agentlab MockClient, the real API, and API key hygiene."
        }
      ],
      "projects": []
    },
    {
      "id": "part1",
      "number": 1,
      "title": "Stage 1 · Talking to a Model",
      "level": "Level 1 · Novice",
      "summary": "One request, one response: tokens, the Messages API, limits and stop reasons, streaming, structured output, and prompts that hold up.",
      "modules": [
        {
          "id": "m01",
          "title": "What an LLM Call Is",
          "href": "modules/m01-llm-calls.html",
          "minutes": 90,
          "summary": "Tokens, context windows, why outputs vary, and what drives cost and latency."
        },
        {
          "id": "m02",
          "title": "The Messages API",
          "href": "modules/m02-messages-api.html",
          "minutes": 120,
          "summary": "Roles, system prompts, content blocks, the response object, and conversation history as a list you own."
        },
        {
          "id": "m03",
          "title": "Limits, Effort & Stop Reasons",
          "href": "modules/m03-limits-stop-reasons.html",
          "minutes": 90,
          "summary": "max_tokens, stop sequences, effort, every stop_reason and how to handle it, and why sampling knobs are gone."
        },
        {
          "id": "m04",
          "title": "Streaming",
          "href": "modules/m04-streaming.html",
          "minutes": 75,
          "summary": "messages.stream, text_stream, stream events, get_final_message, and why agents stream."
        },
        {
          "id": "m05",
          "title": "Structured Output",
          "href": "modules/m05-structured-output.html",
          "minutes": 120,
          "summary": "JSON Schema, output_config.format, validating what comes back, and recovering when it is wrong."
        },
        {
          "id": "m06",
          "title": "Prompting That Holds Up",
          "href": "modules/m06-prompting.html",
          "minutes": 120,
          "summary": "Clear instructions, context before questions, examples, XML-tagged inputs, and prompts as versioned, tested code."
        }
      ],
      "projects": []
    },
    {
      "id": "part2",
      "number": 2,
      "title": "Stage 2 · Tool Use and the Agent Loop",
      "level": "Level 1 · Novice",
      "summary": "Give the model tools, run its calls, and loop until it is done: the 50-line agent at the heart of every framework.",
      "modules": [
        {
          "id": "m07",
          "title": "Tools as Contracts",
          "href": "modules/m07-tools-as-contracts.html",
          "minutes": 120,
          "summary": "Tool names, descriptions, and input schemas the model can use correctly; strict tools."
        },
        {
          "id": "m08",
          "title": "One Tool Call by Hand",
          "href": "modules/m08-one-tool-call.html",
          "minutes": 90,
          "summary": "Read a tool_use block, run the function, send a tool_result with the matching id, and get the answer."
        },
        {
          "id": "m09",
          "title": "The Agent Loop",
          "href": "modules/m09-agent-loop.html",
          "minutes": 150,
          "summary": "Repeat until the model stops asking: stop reasons as control flow, parallel calls, and a complete agent from scratch."
        },
        {
          "id": "m10",
          "title": "Errors as Data",
          "href": "modules/m10-errors-as-data.html",
          "minutes": 90,
          "summary": "is_error tool results, validating tool input, unknown tools, and API errors you retry versus fix."
        },
        {
          "id": "m11",
          "title": "Stop Conditions & Budgets",
          "href": "modules/m11-stop-conditions.html",
          "minutes": 90,
          "summary": "Step limits, token and cost budgets, loop detection, and ending a run gracefully with a report."
        },
        {
          "id": "m12",
          "title": "Tool Design",
          "href": "modules/m12-tool-design.html",
          "minutes": 120,
          "summary": "Fewer, clearer tools; results the model can read; descriptions that beat clever prompts; testing tools alone."
        }
      ],
      "projects": [
        {
          "id": "c1",
          "title": "Capstone 1: Research Agent",
          "href": "projects/c1-research-agent.html",
          "summary": "Build a tool-using research agent that searches, reads sources, and writes a cited answer, graded against a scripted model."
        }
      ]
    }
  ],
  "reference": [
    {
      "id": "ref-roadmap",
      "title": "Roadmap: Levels 2-4",
      "href": "reference/roadmap.html",
      "summary": "What comes after Level 1: context and memory, workflows, evaluation, safety, shipping, and multi-agent systems."
    },
    {
      "id": "ref-agentlab",
      "title": "agentlab Reference",
      "href": "reference/agentlab.html",
      "summary": "Every MockClient method and script step, and how each maps to the real anthropic SDK."
    },
    {
      "id": "ref-loop",
      "title": "Agent Loop Cheat Sheet",
      "href": "reference/agent-loop-cheatsheet.html",
      "summary": "Request and response shapes, stop reasons, tool_result rules, and the loop on one page."
    },
    {
      "id": "ref-glossary",
      "title": "Glossary",
      "href": "reference/glossary.html",
      "summary": "Terms used in the course, with links to where each is taught."
    }
  ]
};
