"""The agent's tools: search, read, and list_sources over the corpus, plus their schemas and a dispatcher."""

from __future__ import annotations

from collections import Counter  # noqa: F401  (handy for counting words when scoring)
from typing import Any

import agentlab  # noqa: F401  (agentlab.validate checks tool input against a JSON Schema)
from research.corpus import Corpus, tokenize  # noqa: F401

MAX_LIMIT = 10
SNIPPET_CHARS = 200


class ToolError(Exception):
    """A tool call failed in a way the model can fix; the message is sent back as an ``is_error`` result."""


def tool_definitions() -> list[dict[str, Any]]:
    """Return the tool definitions to send as ``tools=`` on every request.

    Returns:
        A fresh list of ``{"name", "description", "input_schema"}`` dicts for ``search``, ``read``, ``list_sources``.
    """
    # TODO: Return three tool definitions, in this order: search, read, list_sources.
    #   - search: required string "query" (minLength 1), optional integer "limit" (1..MAX_LIMIT).
    #   - read: required string "doc_id".
    #   - list_sources: no properties.
    #   Every input_schema is {"type": "object", ...} with "additionalProperties": False.
    #   Descriptions (40+ characters) say what the tool returns and WHEN to use it, e.g. "read every document you cite".
    raise NotImplementedError


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
        # TODO: 1. terms = set of tokenize(query) words (optionally strip a plural "s"); none -> raise ToolError.
        #   2. For each document in self.corpus.documents(), score = sum(3 * title count + body count) per term.
        #   3. Keep score > 0; snippet = the first sentence of the body containing a term, cut to SNIPPET_CHARS.
        #   4. Sort by (-score, id) and return the first `limit` hits.
        raise NotImplementedError

    def read(self, doc_id: str) -> str:
        """Return one document's full text and record that it was read.

        Args:
            doc_id: The document id.

        Returns:
            The title line, an ``(id: doc-id)`` line, a blank line, then the body.

        Raises:
            ToolError: If no document has that id; the message tells the model how to find valid ids.
        """
        # TODO: Look the id up with self.corpus.get. Unknown -> ToolError that repeats the id and says to call
        #   search or list_sources. Known -> append to self.read_ids (once) and return the formatted text.
        raise NotImplementedError

    def list_sources(self) -> list[dict[str, str]]:
        """List every document's id and title.

        Returns:
            ``{"id", "title"}`` dicts ordered by id.
        """
        # TODO: One dict per document in self.corpus.documents().
        raise NotImplementedError

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
        # TODO: 1. Find the definition by name; unknown -> ToolError naming the available tools.
        #   2. problems = agentlab.validate(tool_input, definition["input_schema"]); any -> ToolError listing them.
        #   3. Call the method. Format search hits one per line as "[doc-id] Title (score N): snippet" (and say
        #      clearly when nothing matched), list_sources as "[doc-id] Title" lines, read as its text.
        raise NotImplementedError
