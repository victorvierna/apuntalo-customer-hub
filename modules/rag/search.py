"""Searches the help guides by words (BM25 over SQLite FTS5).

Usage::

    index = HelpIndex.load()             # reads data/faqs/ayuda/
    hits = index.search("¿Cómo creo un bono?")

If nothing matches, ``search`` returns ``[]``: the assistant must not answer
without guides behind it (``AGENTS.md``). It does not decide whether the best
score is good enough; that threshold belongs to the router.
"""

import re
import unicodedata
from pathlib import Path

from modules.rag.chunker import load_guides, plain_text
from shared.db import faq_index
from shared.types.rag import Chunk, Hit

REPO_ROOT = Path(__file__).resolve().parents[2]
GUIDES_DIR = REPO_ROOT / "data" / "faqs" / "ayuda"
"""Only this folder is indexed. ``data/faqs/evaluacion-ayuda/`` holds the
expected answers of the evaluation and must never be searchable."""

DEFAULT_K = 5

_WORD = re.compile(r"\w+")

# Words that say nothing about the topic. Compared without accents ("como"
# covers "cómo"). BM25 already gives little weight to common words; removing
# these also stops a question made only of them from matching everything.
STOPWORDS = frozenset(
    """
    a al algo algun alguna algunas alguno algunos ante antes aqui asi aun cada
    como con contra cual cuales cuando cuanta cuantas cuanto cuantos de del desde
    donde durante e el ella ellas ellos en entre era eres es esa esas ese eso esos
    esta estan estas este esto estos estoy fue ha han has hay he hola la las le les
    lo los me mi mis mucho muy mas ni no nos nosotros o os otra otro para pero poco
    por porque que quien se sea segun ser si sin sobre son su sus tambien te ti tu
    tus un una unas uno unos usted ustedes vosotros y ya yo gracias favor buenas
    buenos dias tardes noches
    """.split()
)


class HelpIndex:
    """The guides, split into sections and indexed in memory."""

    def __init__(self, chunks: list[Chunk]):
        self.chunks = {chunk.ref: chunk for chunk in chunks}
        if len(self.chunks) != len(chunks):
            raise ValueError("Two chunks share the same ref.")
        self._conn = faq_index.create_index()
        faq_index.add_chunks(
            self._conn,
            ((c.ref, c.title, plain_text(c.text)) for c in chunks),
        )

    @classmethod
    def load(cls, guides_dir: Path = GUIDES_DIR) -> "HelpIndex":
        chunks = load_guides(guides_dir)
        if not chunks:
            raise FileNotFoundError(f"No guides found in {guides_dir}.")
        return cls(chunks)

    def search(self, question: str, k: int = DEFAULT_K) -> list[Hit]:
        """The ``k`` most relevant sections, best first. ``[]`` if none match."""
        match = build_match_query(question)
        if not match or k <= 0:
            return []
        rows = faq_index.search(self._conn, match, k)
        return [
            Hit(chunk=self.chunks[ref], score=score, rank=rank)
            for rank, (ref, score) in enumerate(rows, start=1)
        ]


def build_match_query(question: str) -> str:
    """Turns free text into an FTS5 query: its meaningful words joined by OR.

    OR, not FTS5's default AND: a short, informal DM rarely shares every word
    with a guide. Each word is quoted, so whatever the customer writes ("NOT",
    ``*``, ``"``, ``:``) is searched as text and never read as FTS5 syntax.
    """
    terms: list[str] = []
    for word in _WORD.findall(question.lower()):
        if word.replace("_", "") == "" or _fold(word) in STOPWORDS:
            continue
        if word not in terms:
            terms.append(word)
    return " OR ".join(f'"{term}"' for term in terms)


def _fold(word: str) -> str:
    return unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode()
