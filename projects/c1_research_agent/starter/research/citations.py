"""Find ``[doc-id]`` citations in an answer and check them against what the agent actually read."""

from __future__ import annotations

import re
from collections.abc import Collection

CITATION = re.compile(r"\[([a-z0-9]+(?:-[a-z0-9]+)*)\]")


def parse_citations(text: str) -> list[str]:
    """Return the ids cited as ``[doc-id]`` in ``text``.

    An id is lowercase letters and digits, optionally joined by single hyphens. ``[Note]`` and ``[1 2]`` are not
    citations.

    Args:
        text: The answer text.

    Returns:
        Unique ids in order of first appearance, for example ``["waggle-dance", "swarming"]``.
    """
    # TODO: CITATION.findall(text), de-duplicated while keeping first-seen order.
    raise NotImplementedError


def check_citations(cited: list[str], read_ids: Collection[str], known_ids: Collection[str]) -> list[str]:
    """List every problem with an answer's citations.

    Args:
        cited: Ids the answer cites, from :func:`parse_citations`.
        read_ids: Ids of documents the agent read with the ``read`` tool during this run.
        known_ids: Every id in the corpus.

    Returns:
        One message per problem, empty when the citations are sound:
        ``"the answer cites no sources"`` when ``cited`` is empty,
        ``"[x] is not a document in the corpus"`` for an unknown id, and
        ``"[x] was cited but never read"`` for a real document the agent did not read.
    """
    # TODO: Produce exactly the messages described above, one per problem, in citation order.
    raise NotImplementedError
