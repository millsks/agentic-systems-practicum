"""research: a tool-using agent that answers questions from a small document library, with checked citations."""

from research.agent import MODEL, SYSTEM_PROMPT, Answer, Usage, execute_tool_calls, run
from research.citations import check_citations, parse_citations
from research.corpus import Corpus, Document
from research.tools import Toolbox, ToolError, tool_definitions

__all__ = [
    "MODEL",
    "SYSTEM_PROMPT",
    "Answer",
    "Corpus",
    "Document",
    "ToolError",
    "Toolbox",
    "Usage",
    "check_citations",
    "execute_tool_calls",
    "parse_citations",
    "run",
    "tool_definitions",
]
