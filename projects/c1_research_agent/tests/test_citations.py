"""Milestone 2: parsing [doc-id] citations and checking them against what was read."""

from research import check_citations, parse_citations


def test_parse_citations_in_order_without_duplicates() -> None:
    text = "Bees dance [waggle-dance]. Swarms vote [swarming]. Again [waggle-dance]. Not these: [Note], [a b], [x_y]."
    assert parse_citations(text) == ["waggle-dance", "swarming"], "unique lowercase-hyphen ids, first-seen order"


def test_check_citations_flags_unread_unknown_and_missing() -> None:
    known = ["drones", "swarming", "waggle-dance"]
    assert check_citations(["swarming"], ["swarming"], known) == [], "a cited, read, real document is fine"
    problems = check_citations(["swarming", "drones", "bee-tv"], ["swarming"], known)
    assert len(problems) == 2, f"expected two problems, got {problems}"
    assert any("drones" in p and "never read" in p for p in problems), "flag a real document that was not read"
    assert any("bee-tv" in p and "not a document" in p for p in problems), "flag an id not in the corpus"
    assert check_citations([], ["swarming"], known) == ["the answer cites no sources"], "an uncited answer is flagged"
