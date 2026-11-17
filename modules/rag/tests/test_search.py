import tempfile
import unittest
from pathlib import Path

from modules.rag.search import GUIDES_DIR, HelpIndex, build_match_query

from .helpers import GuidesTestCase


class SearchTest(GuidesTestCase):
    def setUp(self):
        super().setUp()
        self.index = HelpIndex.load(self.guides_dir)

    def test_finds_the_section_that_answers(self):
        # Exact words only: "creo" would not match "crear" (no stemming yet).
        [best, *_] = self.index.search("¿Dónde está el botón Nuevo bono en la ficha?")
        self.assertEqual(best.chunk.ref, "ayuda/12-bonos/bonos.md#crear-un-bono")
        self.assertEqual(best.rank, 1)

    def test_accents_and_capitals_do_not_matter(self):
        [best, *_] = self.index.search("SESIÓN GASTADA")
        self.assertEqual(best.chunk.ref, "ayuda/12-bonos/bonos.md#una-sesion-gastada-se-puede-devolver")

    def test_section_titles_are_searchable(self):
        refs = [hit.chunk.ref for hit in self.index.search("cifras")]
        self.assertIn("ayuda/13-cobros/cobros.md#que-significan-las-cifras", refs)

    def test_image_descriptions_are_searchable(self):
        refs = [hit.chunk.ref for hit in self.index.search("reembolso")]
        self.assertEqual(refs, ["ayuda/13-cobros/cobros.md#que-significan-las-cifras"])

    def test_link_targets_are_not_searchable(self):
        # "12-bonos" only appears inside a link target of the bonos guide.
        self.assertEqual(self.index.search("12"), [])

    def test_returns_nothing_when_no_guide_matches(self):
        self.assertEqual(self.index.search("horario de verano en Google Calendar"), [])

    def test_a_greeting_alone_matches_nothing(self):
        self.assertEqual(self.index.search("Hola, buenas tardes"), [])
        self.assertEqual(self.index.search(""), [])

    def test_results_are_sorted_and_limited(self):
        hits = self.index.search("bono", k=2)
        self.assertEqual([hit.rank for hit in hits], [1, 2])
        self.assertGreaterEqual(hits[0].score, hits[1].score)
        self.assertGreater(hits[1].score, 0)

    def test_what_the_customer_writes_is_never_read_as_query_syntax(self):
        for text in ['bono"', "bono NOT", "bono*", "NEAR(bono)", "title:bono", "- bono ^", "AND OR"]:
            with self.subTest(text=text):
                self.index.search(text)  # must not raise

    def test_an_empty_folder_is_an_error(self):
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(FileNotFoundError):
                HelpIndex.load(Path(empty))


class BuildMatchQueryTest(unittest.TestCase):
    def test_keeps_meaningful_words_joined_by_or(self):
        self.assertEqual(build_match_query("¿Cómo cancelo una cita?"), '"cancelo" OR "cita"')

    def test_repeated_words_appear_once(self):
        self.assertEqual(build_match_query("bono bono Bono"), '"bono"')


class RealGuidesTest(unittest.TestCase):
    """The real ``data/faqs/`` folder."""

    def test_only_the_guides_are_indexed_never_the_evaluation_set(self):
        index = HelpIndex.load()
        self.assertEqual(GUIDES_DIR.name, "ayuda")
        refs = list(index.chunks)
        self.assertGreater(len(refs), 100)
        self.assertTrue(all(ref.startswith("ayuda/") for ref in refs))
