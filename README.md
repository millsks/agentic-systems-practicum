# agentic-systems-practicum

An interactive, novice-to-professional curriculum for building AI agents with large language models: the Messages
API, tool use and the agent loop, context and memory, workflow patterns, evaluation, safety, and production. Everything
is managed with Pixi.

[![CI](https://github.com/millsks/agentic-systems-practicum/actions/workflows/ci.yml/badge.svg)](https://github.com/millsks/agentic-systems-practicum/actions/workflows/ci.yml)
![coverage](https://img.shields.io/badge/coverage-%E2%89%A590%25-brightgreen)
![python](https://img.shields.io/badge/python-3.14-blue)
![pixi](https://img.shields.io/badge/managed%20by-pixi-orange)

## What's inside

- **Level 1 (Novice), available now:** an orientation module, Stage 1 *Talking to a model* (6 modules) and Stage 2
  *Tool use and the agent loop* (6 modules), published as static HTML in [`docs/`](docs/).
- **Levels 2-4** (context and memory, workflows, evaluation, safety, shipping, multi-agent systems) are on the
  [roadmap](docs/reference/roadmap.html).
- **Real Python in the browser** (Pyodide). Every lesson has runnable cells, graded exercises, a quiz, and flashcards.
- **`agentlab`**, the course's teaching library in [`src/agentlab/`](src/agentlab/): `MockClient` is a scripted,
  offline stand-in for `anthropic.Anthropic()` with the same `messages.create` / `messages.stream` /
  `messages.count_tokens` surface. It validates requests the way the real API does, so code written against it
  ports to the real client by changing one line.
- **Capstones** in [`projects/`](projects/): starter code, a test suite, and a reference solution.

## Installation

Install [Pixi](https://pixi.sh), then:

```sh
git clone https://github.com/millsks/agentic-systems-practicum.git
cd agentic-systems-practicum
pixi install
pixi run bootstrap    # pre-commit hooks (only needed if you contribute)
```

## Quick start

```sh
pixi run serve        # opens the course at http://127.0.0.1:8000/
```

Start with **Module 00: How this practicum works**. When a level ends, build its capstone:

```sh
pixi run projects     # list capstones and whether you've started them
pixi run start c1     # copy the starter code into work/c1_research_agent/
pixi run grade c1     # run the capstone's tests against your code in work/
```

## Development

```sh
pixi run test               # unit tests (fast)
pixi run test-integration   # every exercise solution and capstone solution is verified
pixi run check-site         # validate links, anchors, quizzes, and exercises in docs/
pixi run sync-runtime       # regenerate docs/assets/js/agentlab-src.js after changing src/agentlab/
pixi run bundle             # build the single-file edition: dist/agentic-systems-practicum.html
pixi run ci                 # pre-commit, build, mypy, ruff, and tests with a coverage gate (>= 90%)
```

Lesson authors should read [`docs/AUTHORING.md`](docs/AUTHORING.md).

## License

[MIT](LICENSE)
