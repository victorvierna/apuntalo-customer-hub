import unittest

from modules.rag.chunker import load_guides, plain_text, slugify, split_guide

from .helpers import BONOS, COBROS, GuidesTestCase

ARTICLE = "ayuda/12-bonos/bonos.md"


class SplitGuideTest(unittest.TestCase):
    def setUp(self):
        self.chunks = split_guide(ARTICLE, BONOS)
        self.by_ref = {c.ref: c for c in self.chunks}

    def test_the_text_before_the_first_section_is_the_intro(self):
        intro = self.chunks[0]
        self.assertEqual(intro.ref, ARTICLE)
        self.assertEqual(intro.title, "Bonos de sesiones")
        self.assertIn("varias sesiones", intro.text)

    def test_each_section_and_question_is_one_chunk(self):
        self.assertEqual(
            [c.ref for c in self.chunks],
            [
                ARTICLE,
                f"{ARTICLE}#crear-un-bono",
                f"{ARTICLE}#una-sesion-gastada-se-puede-devolver",
                f"{ARTICLE}#caduca-el-bono",
            ],
        )

    def test_a_heading_without_text_gives_no_chunk_but_stays_in_the_title(self):
        question = self.by_ref[f"{ARTICLE}#caduca-el-bono"]
        self.assertEqual(
            question.title, "Bonos de sesiones › Preguntas frecuentes › ¿Caduca el bono?"
        )
        self.assertNotIn(f"{ARTICLE}#preguntas-frecuentes", self.by_ref)

    def test_the_heading_is_not_repeated_in_the_text(self):
        section = self.by_ref[f"{ARTICLE}#crear-un-bono"]
        self.assertTrue(section.text.startswith("1. Abre"))
        self.assertEqual(section.article, ARTICLE)

    def test_repeated_headings_get_different_refs(self):
        refs = [c.ref for c in split_guide("ayuda/13-cobros/cobros.md", COBROS)]
        self.assertEqual(len(refs), len(set(refs)))
        self.assertIn("ayuda/13-cobros/cobros.md#caduca-el-bono-2", refs)

    def test_a_table_stays_in_one_chunk(self):
        [figures] = [c for c in split_guide("a.md", COBROS) if c.ref == "a.md#que-significan-las-cifras"]
        self.assertIn("| Cobrado online |", figures.text)
        self.assertIn("| Neto online |", figures.text)

    def test_a_hash_inside_a_code_block_is_not_a_heading(self):
        chunks = split_guide("a.md", "# Guía\n\n## Paso\n\n```\n## no es un título\n```\n")
        self.assertEqual([c.ref for c in chunks], ["a.md#paso"])


class LoadGuidesTest(GuidesTestCase):
    def test_refs_start_with_the_guides_folder_and_the_readme_is_skipped(self):
        refs = [c.ref for c in load_guides(self.guides_dir)]
        self.assertTrue(all(ref.startswith("ayuda/") for ref in refs))
        self.assertFalse(any("README" in ref for ref in refs))
        self.assertIn("ayuda/12-bonos/bonos.md#crear-un-bono", refs)


class PlainTextTest(unittest.TestCase):
    def test_link_targets_are_dropped_and_image_descriptions_kept(self):
        text = plain_text("Ver [recordatorios](../09-recordatorios/x.md). ![Pantalla de pago](../img/p.png)")
        self.assertEqual(text, "Ver recordatorios. Pantalla de pago")

    def test_emphasis_marks_are_removed(self):
        self.assertEqual(plain_text("Pulsa **Guardar** o `Cancelar`"), "Pulsa Guardar o Cancelar")


class SlugifyTest(unittest.TestCase):
    def test_accents_and_punctuation(self):
        self.assertEqual(slugify("¿Qué significa «Neto online»?"), "que-significa-neto-online")

    def test_a_title_without_letters_still_gets_a_slug(self):
        self.assertEqual(slugify("¿?"), "seccion")
