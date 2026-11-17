"""Splits the help guides into sections (``docs/modules/rag.md``, "Troceo").

Each guide has one ``#`` title, ``##`` sections and ``###`` questions. Every
``##`` or ``###`` with text becomes one ``Chunk``; the text before the first
``##`` is the guide's intro. Tables and lists are never split.
"""

import re
import unicodedata
from pathlib import Path

from shared.types.rag import Chunk

SEPARATOR = " › "

_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_EMPHASIS = re.compile(r"(\*\*|__|`)")


def load_guides(guides_dir: Path) -> list[Chunk]:
    """Reads every ``.md`` under ``guides_dir`` (sorted, so ids are stable).

    ``README.md`` is skipped: it is only the index of titles and would match
    every search. Refs are relative to the parent of ``guides_dir``
    (``data/faqs/``), so they start with the folder name (``ayuda/...``).
    """
    base = guides_dir.parent
    chunks: list[Chunk] = []
    for path in sorted(guides_dir.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        article = path.relative_to(base).as_posix()
        chunks.extend(split_guide(article, path.read_text(encoding="utf-8")))
    return chunks


def split_guide(article: str, markdown: str) -> list[Chunk]:
    """Splits one guide. Headings without text of their own (a ``##`` followed
    straight by ``###``) produce no chunk, but stay in their children's title."""
    chunks: list[Chunk] = []
    used_slugs: set[str] = set()
    headings: list[str | None] = [None, None, None]  # current #, ## and ###
    body: list[str] = []
    in_fence = False

    def flush() -> None:
        text = "\n".join(body).strip()
        body.clear()
        if not text:
            return
        path = [h for h in headings if h]
        if headings[1] is None and headings[2] is None:
            ref = article  # the intro, before the first ##
        else:
            ref = f"{article}#{_unique(slugify(path[-1]), used_slugs)}"
        title = SEPARATOR.join(path) or article
        chunks.append(Chunk(ref=ref, article=article, title=title, text=text))

    for line in markdown.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
        heading = None if in_fence else _HEADING.match(line)
        if heading is None:
            body.append(line)
            continue
        flush()
        level = len(heading.group(1))
        headings[level - 1] = heading.group(2).strip()
        headings[level:] = [None] * (3 - level)
    flush()
    return chunks


def plain_text(markdown: str) -> str:
    """What gets indexed: no link targets (paths like ``../09-recordatorios/...``
    would add words the reader never sees), image alt text kept."""
    text = _IMAGE.sub(r"\1", markdown)
    text = _LINK.sub(r"\1", text)
    return _EMPHASIS.sub("", text)


def slugify(text: str) -> str:
    """``¿Qué significa «Neto online»?`` → ``que-significa-neto-online``."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-") or "seccion"


def _unique(slug: str, used: set[str]) -> str:
    candidate, n = slug, 2
    while candidate in used:
        candidate, n = f"{slug}-{n}", n + 1
    used.add(candidate)
    return candidate
