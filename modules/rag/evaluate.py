"""Measures whether the search finds the right guide (``docs/modules/rag.md``).

Usage (from the repo root)::

    python -m modules.rag.evaluate
    python -m modules.rag.evaluate --failures            # list the misses
    python -m modules.rag.evaluate --out storage/rag-eval.json

Asks every question of ``data/faqs/evaluacion-ayuda/preguntas.jsonl`` and
checks if the guides in its ``referencias`` come up. It measures retrieval
only: no model is called and the expected answers are never read.

Scored per guide, not per section: the evaluation set names guides. Several
sections of the same guide count once, at the position of the first one.
"""

import argparse
import json
import posixpath
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from modules.rag.search import GUIDES_DIR, REPO_ROOT, HelpIndex

QUESTIONS = REPO_ROOT / "data" / "faqs" / "evaluacion-ayuda" / "preguntas.jsonl"
CUTOFFS = (1, 3, 5)
SECTIONS_TO_FETCH = 50
"""Sections asked for per question; enough to rank the first guides."""


@dataclass(frozen=True, slots=True)
class CaseResult:
    id: str
    question: str
    behaviour: str
    """``conducta_esperada``: responder, aclarar or abstenerse_dato_cuenta."""
    expected: list[str]
    ranked: list[str]
    """Guides found, best first (each one once)."""
    first_relevant: int | None
    """Position of the first expected guide (1 = top), or None if not found."""


def load_cases(path: Path = QUESTIONS) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def to_article(reference: str) -> str:
    """``../ayuda/12-bonos/bonos.md`` → ``ayuda/12-bonos/bonos.md`` (how chunks name it)."""
    return posixpath.normpath(posixpath.join("evaluacion-ayuda", reference))


def rank_articles(chunk_articles: list[str]) -> list[str]:
    """Section results → guides, best first, each guide once."""
    return list(dict.fromkeys(chunk_articles))


def evaluate_case(index: HelpIndex, case: dict) -> CaseResult:
    hits = index.search(case["pregunta"], k=SECTIONS_TO_FETCH)
    ranked = rank_articles([hit.chunk.article for hit in hits])
    expected = [to_article(ref) for ref in case["referencias"]]
    positions = [ranked.index(a) + 1 for a in expected if a in ranked]
    return CaseResult(
        id=case["id"],
        question=case["pregunta"],
        behaviour=case["conducta_esperada"],
        expected=expected,
        ranked=ranked,
        first_relevant=min(positions, default=None),
    )


def metrics(results: list[CaseResult]) -> dict[str, float]:
    """Recall@k (share of expected guides in the top k, averaged) and MRR."""
    if not results:
        return {}
    n = len(results)
    summary: dict[str, float] = {"n": n}
    for k in CUTOFFS:
        recall = sum(
            len(set(r.expected) & set(r.ranked[:k])) / len(set(r.expected)) for r in results
        )
        summary[f"recall@{k}"] = recall / n
    summary["mrr"] = sum(1 / r.first_relevant for r in results if r.first_relevant) / n
    return summary


def run(index: HelpIndex, cases: list[dict]) -> tuple[dict, list[CaseResult]]:
    results = [evaluate_case(index, case) for case in cases]
    by_behaviour: dict[str, list[CaseResult]] = defaultdict(list)
    for result in results:
        by_behaviour[result.behaviour].append(result)
    report = {
        "all": metrics(results),
        "by_behaviour": {b: metrics(rs) for b, rs in sorted(by_behaviour.items())},
    }
    return report, results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--questions", type=Path, default=QUESTIONS)
    parser.add_argument("--failures", action="store_true", help="list questions whose guide is not in the top 3")
    parser.add_argument("--out", type=Path, help="write the full results as JSON (keep it out of git)")
    args = parser.parse_args(argv)

    index = HelpIndex.load(GUIDES_DIR)
    report, results = run(index, load_cases(args.questions))

    print(f"Guías: {len({c.article for c in index.chunks.values()})}, trozos: {len(index.chunks)}")
    _print_table(report)

    if args.failures:
        misses = [r for r in results if r.first_relevant is None or r.first_relevant > 3]
        print(f"\nFallos (la guía esperada no está entre las 3 primeras): {len(misses)}")
        for r in misses:
            where = f"puesto {r.first_relevant}" if r.first_relevant else "no aparece"
            print(f"\n- {r.id} [{r.behaviour}] {r.question}")
            print(f"  esperada: {', '.join(r.expected)} ({where})")
            print(f"  top 3:    {', '.join(r.ranked[:3]) or '(nada)'}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "retriever": "bm25-fts5",
            "report": report,
            "cases": [asdict(r) for r in results],
        }
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nResultados guardados en {args.out}")
    return 0


def _print_table(report: dict) -> None:
    columns = ["n", *(f"recall@{k}" for k in CUTOFFS), "mrr"]
    rows = [("todas", report["all"]), *report["by_behaviour"].items()]
    print(f"\n{'conjunto':<24}" + "".join(f"{c:>10}" for c in columns))
    for name, values in rows:
        cells = "".join(
            f"{int(values[c]):>10}" if c == "n" else f"{values[c]:>10.3f}" for c in columns
        )
        print(f"{name:<24}{cells}")


if __name__ == "__main__":
    sys.exit(main())
