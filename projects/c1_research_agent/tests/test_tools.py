"""Milestone 1: the tools, their schemas, and the dispatcher, tested without any model."""

import pytest
from research import Corpus, Toolbox, ToolError, tool_definitions


@pytest.fixture
def toolbox() -> Toolbox:
    return Toolbox()


def test_bundled_corpus_loads() -> None:
    corpus = Corpus.load()
    assert len(corpus) >= 10, "the bundled corpus should hold at least 10 documents"
    assert "waggle-dance" in corpus, "document ids are file names without .md"
    doc = corpus.get("waggle-dance")
    assert doc is not None and doc.title == "The Waggle Dance", "the title comes from the '# ' heading"


def test_search_ranks_the_most_relevant_document_first(toolbox: Toolbox) -> None:
    hits = toolbox.search("waggle dance")
    assert hits, "search('waggle dance') should find something"
    assert hits[0]["id"] == "waggle-dance", f"the waggle-dance document should rank first, got {hits[0]['id']}"
    assert set(hits[0]) >= {"id", "title", "snippet", "score"}, "each hit needs id, title, snippet, and score"
    snippet = hits[0]["snippet"].lower()
    assert "waggle" in snippet or "dance" in snippet, "the snippet should show a sentence containing a query word"
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True), "hits must be sorted by score, highest first"


def test_search_limits_no_matches_and_empty_queries(toolbox: Toolbox) -> None:
    assert len(toolbox.search("bees", limit=3)) == 3, "limit caps the number of hits"
    assert toolbox.search("quantum blockchain") == [], "a query no document matches returns an empty list"
    with pytest.raises(ToolError):
        toolbox.search("the of and")  # only stopwords: tell the model to use real keywords


def test_read_returns_the_document_and_records_it(toolbox: Toolbox) -> None:
    text = toolbox.read("swarming")
    assert "Swarming and Choosing a New Home" in text, "read should include the document title"
    assert "quorum" in text, "read should return the full body text"
    assert toolbox.read_ids == ["swarming"], "a successful read is recorded in read_ids"


def test_read_unknown_id_raises_a_helpful_tool_error(toolbox: Toolbox) -> None:
    with pytest.raises(ToolError) as caught:
        toolbox.read("bee-dances")
    message = str(caught.value)
    assert "bee-dances" in message, "the error should repeat the bad id"
    assert "search" in message, "the error should tell the model how to find valid ids (search or list_sources)"
    assert toolbox.read_ids == [], "a failed read must not count as read"


def test_list_sources_lists_every_document(toolbox: Toolbox) -> None:
    sources = toolbox.list_sources()
    assert [s["id"] for s in sources] == toolbox.corpus.ids(), "list_sources returns every id, sorted"
    assert all(s["title"] for s in sources), "every source has a title"


def test_tool_definitions_are_valid_contracts() -> None:
    tools = {t["name"]: t for t in tool_definitions()}
    assert set(tools) == {"search", "read", "list_sources"}, "define exactly search, read, and list_sources"
    for name, tool in tools.items():
        assert len(tool["description"]) >= 40, f"{name}: write a description that says when to use the tool"
        assert tool["input_schema"]["type"] == "object", f"{name}: input_schema must be an object schema"
    assert tools["search"]["input_schema"]["required"] == ["query"], "search requires only query"
    assert "limit" in tools["search"]["input_schema"]["properties"], "search accepts an optional limit"
    assert tools["read"]["input_schema"]["required"] == ["doc_id"], "read requires doc_id"


def test_dispatch_formats_results_with_ids(toolbox: Toolbox) -> None:
    out = toolbox.dispatch("search", {"query": "varroa", "limit": 2})
    assert isinstance(out, str), "dispatch returns text for the tool_result content"
    assert "[varroa-mite]" in out, "search results show each id in square brackets so the model can cite it"
    assert "[waggle-dance]" in toolbox.dispatch("list_sources", {}), "list_sources output includes ids"
    assert "quorum" in toolbox.dispatch("read", {"doc_id": "swarming"}), "dispatch routes read to Toolbox.read"


def test_dispatch_validates_input_and_rejects_unknown_tools(toolbox: Toolbox) -> None:
    with pytest.raises(ToolError, match="query"):
        toolbox.dispatch("search", {"limit": 3})
    with pytest.raises(ToolError, match="limit"):
        toolbox.dispatch("search", {"query": "wax", "limit": 500})
    with pytest.raises(ToolError) as caught:
        toolbox.dispatch("web_search", {"query": "bees"})
    assert "search" in str(caught.value) and "read" in str(caught.value), "name the tools that do exist"
