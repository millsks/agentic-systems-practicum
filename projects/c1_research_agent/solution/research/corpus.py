"""The offline document collection the research agent searches (provided; no TODOs here)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

CORPUS_DIR = Path(__file__).parent / "corpus"
_WORD = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    "a an and are as at be by do does for from has have how in is it its of on or that the their this to was what "
    "when where which who why will with".split()
)


@dataclass(frozen=True, slots=True)
class Document:
    """One source document.

    Attributes:
        id: Stable identifier, the file name without ``.md`` (for example ``waggle-dance``).
        title: The document's ``# heading``.
        text: The body below the heading.
    """

    id: str
    title: str
    text: str


def tokenize(text: str) -> list[str]:
    """Split text into lowercase words, dropping common stopwords.

    Args:
        text: Any text.

    Returns:
        The words in order, for example ``tokenize("How do bees dance?") == ["bees", "dance"]``.
    """
    return [word for word in _WORD.findall(text.lower()) if word not in STOPWORDS]


def parse_document(doc_id: str, raw: str) -> Document:
    """Build a :class:`Document` from markdown whose first line is ``# Title``.

    Args:
        doc_id: The document id.
        raw: The file contents.

    Returns:
        The parsed document.

    Raises:
        ValueError: If the first line is not a ``#`` heading.
    """
    first, _, body = raw.strip().partition("\n")
    if not first.startswith("# "):
        raise ValueError(f"{doc_id}: the first line must be a '# Title' heading")
    return Document(id=doc_id, title=first[2:].strip(), text=body.strip())


class Corpus:
    """An in-memory, read-only collection of documents keyed by id."""

    def __init__(self, documents: list[Document]) -> None:
        """Index the documents.

        Args:
            documents: The documents; ids must be unique.

        Raises:
            ValueError: If two documents share an id.
        """
        self._docs: dict[str, Document] = {}
        for doc in documents:
            if doc.id in self._docs:
                raise ValueError(f"duplicate document id {doc.id!r}")
            self._docs[doc.id] = doc

    @classmethod
    def load(cls, directory: Path = CORPUS_DIR) -> Corpus:
        """Load every ``*.md`` file in ``directory``.

        Args:
            directory: Folder of markdown documents; defaults to the bundled corpus.

        Returns:
            The corpus, ordered by id.
        """
        paths = sorted(directory.glob("*.md"))
        return cls([parse_document(p.stem, p.read_text(encoding="utf-8")) for p in paths])

    def __len__(self) -> int:
        """Return the number of documents."""
        return len(self._docs)

    def __contains__(self, doc_id: object) -> bool:
        """Return whether ``doc_id`` names a document."""
        return doc_id in self._docs

    def ids(self) -> list[str]:
        """Return every document id, sorted.

        Returns:
            The ids.
        """
        return sorted(self._docs)

    def get(self, doc_id: str) -> Document | None:
        """Look up a document.

        Args:
            doc_id: The id.

        Returns:
            The document, or ``None`` when no document has that id.
        """
        return self._docs.get(doc_id)

    def documents(self) -> list[Document]:
        """Return every document, ordered by id.

        Returns:
            The documents.
        """
        return [self._docs[doc_id] for doc_id in self.ids()]
