"""The agent's tools: search, read, and list_sources over the corpus, plus their schemas and a dispatcher."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import agentlab
from research.corpus import Corpus, tokenize

MAX_LIMIT = 10
SNIPPET_CHARS = 200
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "search",
        "description": (
            "Keyword search over the honeybee research library. Returns up to `limit` documents as "
            "'[doc-id] Title (score N): snippet' lines, best match first. Use it first to find which documents "
            "are relevant; snippets are not enough to answer from, so read the documents you plan to cite. "
            "Use short keyword queries such as 'waggle dance distance', not full sentences."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "description": "Keywords to look for."},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_LIMIT,
                    "description": "Maximum number of results (default 5).",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read",
        "description": (
            "Return the full text of one document by its id (an id from search or list_sources results, such as "
            "'waggle-dance'). Read every document you cite; only documents you have read may be cited."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"doc_id": {"type": "string", "minLength": 1, "description": "The document id."}},
            "required": ["doc_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_sources",
        "description": (
            "List the id and title of every document in the library. Use it when a search finds nothing or to "
            "see what the library covers; it does not return document text."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


class ToolError(Exception):
    """A tool call failed in a way the model can fix; the message is sent back as an ``is_error`` result."""


def tool_definitions() -> list[dict[str, Any]]:
    """Return the tool definitions to send as ``tools=`` on every request.

    Returns:
        A fresh list of ``{"name", "description", "input_schema"}`` dicts for ``search``, ``read``, ``list_sources``.
    """
    return [dict(tool) for tool in TOOL_DEFINITIONS]


def _stem(word: str) -> str:
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _terms(text: str) -> list[str]:
    return [_stem(word) for word in tokenize(text)]


def _snippet(text: str, terms: set[str]) -> str:
    sentences = _SENTENCE_END.split(text.replace("\n", " "))
    best = next((s for s in sentences if terms & set(_terms(s))), sentences[0])
    return best if len(best) <= SNIPPET_CHARS else best[: SNIPPET_CHARS - 3].rstrip() + "..."


class Toolbox:
    """The tools for one agent run, bound to a corpus.

    Attributes:
        corpus: The documents the tools search and read.
        read_ids: Ids of documents successfully read during this run, in first-read order.
    """

    def __init__(self, corpus: Corpus | None = None) -> None:
        """Create the toolbox.

        Args:
            corpus: Documents to use; defaults to the bundled corpus.
        """
        self.corpus = corpus if corpus is not None else Corpus.load()
        self.read_ids: list[str] = []

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Rank documents by keyword overlap with ``query``.

        A document scores 3 points per occurrence of a query word in its title and 1 per occurrence in its body.
        Words are lowercased, stopwords dropped, and a plural ``s`` ignored. Documents scoring 0 are left out.

        Args:
            query: Keywords.
            limit: Maximum number of hits.

        Returns:
            Hits ``{"id", "title", "snippet", "score"}`` sorted by score (highest first), then id.

        Raises:
            ToolError: If the query has no searchable words (for example only stopwords).
        """
        terms = set(_terms(query))
        if not terms:
            raise ToolError(f"the query {query!r} has no searchable keywords; use specific words like 'waggle dance'")
        hits: list[dict[str, Any]] = []
        for doc in self.corpus.documents():
            title_counts = Counter(_terms(doc.title))
            body_counts = Counter(_terms(doc.text))
            score = sum(3 * title_counts[t] + body_counts[t] for t in terms)
            if score > 0:
                hits.append({"id": doc.id, "title": doc.title, "snippet": _snippet(doc.text, terms), "score": score})
        hits.sort(key=lambda hit: (-hit["score"], hit["id"]))
        return hits[:limit]

    def read(self, doc_id: str) -> str:
        """Return one document's full text and record that it was read.

        Args:
            doc_id: The document id.

        Returns:
            The title line, an ``(id: doc-id)`` line, a blank line, then the body.

        Raises:
            ToolError: If no document has that id; the message tells the model how to find valid ids.
        """
        doc = self.corpus.get(doc_id)
        if doc is None:
            raise ToolError(
                f"no document with id {doc_id!r}. Ids look like 'waggle-dance'; call search or list_sources "
                "to find valid ids."
            )
        if doc_id not in self.read_ids:
            self.read_ids.append(doc_id)
        return f"# {doc.title}\n(id: {doc.id})\n\n{doc.text}"

    def list_sources(self) -> list[dict[str, str]]:
        """List every document's id and title.

        Returns:
            ``{"id", "title"}`` dicts ordered by id.
        """
        return [{"id": doc.id, "title": doc.title} for doc in self.corpus.documents()]

    def dispatch(self, name: str, tool_input: dict[str, Any]) -> str:
        """Validate a tool call, run it, and format the result as text for the model.

        Args:
            name: Tool name from the ``tool_use`` block.
            tool_input: Arguments from the ``tool_use`` block.

        Returns:
            The text to send back as the ``tool_result`` content.

        Raises:
            ToolError: For an unknown tool, input that does not match the schema, or a failing tool.
        """
        definitions = tool_definitions()
        definition = next((t for t in definitions if t["name"] == name), None)
        if definition is None:
            available = ", ".join(sorted(t["name"] for t in definitions))
            raise ToolError(f"unknown tool {name!r}; available tools: {available}")
        problems = agentlab.validate(tool_input, definition["input_schema"])
        if problems:
            raise ToolError(f"invalid input for {name!r}: {'; '.join(problems)}")
        if name == "search":
            query = tool_input["query"]
            hits = self.search(query, tool_input.get("limit", 5))
            if not hits:
                return f"No documents matched {query!r}. Try other keywords, or call list_sources to see every title."
            lines = [f"[{h['id']}] {h['title']} (score {h['score']}): {h['snippet']}" for h in hits]
            return f"{len(hits)} result(s) for {query!r}:\n" + "\n".join(lines)
        if name == "read":
            return self.read(tool_input["doc_id"])
        return "\n".join(f"[{s['id']}] {s['title']}" for s in self.list_sources())
