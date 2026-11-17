import unittest

from modules.rag.evaluate import CaseResult, metrics, rank_articles, to_article


def result(expected: list[str], ranked: list[str]) -> CaseResult:
    positions = [ranked.index(a) + 1 for a in expected if a in ranked]
    return CaseResult(
        id="T",
        question="?",
        behaviour="responder",
        expected=expected,
        ranked=ranked,
        first_relevant=min(positions, default=None),
    )


class EvaluateTest(unittest.TestCase):
    def test_references_are_turned_into_chunk_articles(self):
        self.assertEqual(to_article("../ayuda/12-bonos/bonos.md"), "ayuda/12-bonos/bonos.md")

    def test_sections_of_the_same_guide_count_once(self):
        self.assertEqual(rank_articles(["a", "b", "a", "c", "b"]), ["a", "b", "c"])

    def test_recall_and_mrr(self):
        report = metrics(
            [
                result(["a"], ["a", "b"]),  # found first
                result(["a"], ["b", "c", "a"]),  # found third
                result(["a"], ["b"]),  # not found
                result(["a", "b"], ["a", "x", "y", "z", "w", "b"]),  # one of two in the top 5
            ]
        )
        self.assertEqual(report["n"], 4)
        self.assertAlmostEqual(report["recall@1"], (1 + 0 + 0 + 0.5) / 4)
        self.assertAlmostEqual(report["recall@3"], (1 + 1 + 0 + 0.5) / 4)
        self.assertAlmostEqual(report["recall@5"], (1 + 1 + 0 + 0.5) / 4)
        self.assertAlmostEqual(report["mrr"], (1 + 1 / 3 + 0 + 1) / 4)

    def test_no_results_no_metrics(self):
        self.assertEqual(metrics([]), {})
