"""What the RAG returns (``docs/modules/rag.md``).

Shared because the router, the answer step and the logging read them too:
``Hit.chunk.ref``, ``Hit.score`` and ``Hit.rank`` are the columns of
``faq_retrievals`` (``docs/architecture/database.md``, 6.7).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Chunk:
    """One section of a help guide: the unit the search returns."""

    ref: str
    """Stable id, relative to ``data/faqs/``: ``ayuda/12-bonos/bonos.md#crear-un-bono``.

    The intro of a guide (the text before its first ``##``) has no ``#...`` part.
    This is what ``faq_retrievals.faq_ref`` stores.
    """

    article: str
    """The guide it comes from, relative to ``data/faqs/``: ``ayuda/12-bonos/bonos.md``."""

    title: str
    """Where it sits in the guide: ``Bonos de sesiones › Preguntas frecuentes › ¿...?``."""

    text: str
    """The section body, in Markdown, without its heading."""


@dataclass(frozen=True, slots=True)
class Hit:
    """One search result."""

    chunk: Chunk
    score: float
    """BM25 relevance: higher is better. Only comparable within the same search."""

    rank: int
    """Position in the results (1 = most relevant)."""
