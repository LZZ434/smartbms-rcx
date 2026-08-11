import unittest

from smartbms.i18n import (
    LANGUAGE_NAMES,
    PAGE_IDS,
    TRANSLATIONS,
    page_label,
    t,
)


class TranslationCoreTests(unittest.TestCase):
    def test_catalogs_have_identical_keys_and_nonempty_values(self):
        self.assertEqual(set(TRANSLATIONS["zh"]), set(TRANSLATIONS["en"]))
        for key in TRANSLATIONS["en"]:
            self.assertNotEqual(TRANSLATIONS["zh"][key], "")
            self.assertNotEqual(TRANSLATIONS["en"][key], "")

    def test_unsupported_language_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported language"):
            t("fr", "app.title")

    def test_page_labels_are_unique_in_both_languages(self):
        self.assertEqual(len(PAGE_IDS), 6)
        for language in LANGUAGE_NAMES:
            labels = [page_label(page_id, language) for page_id in PAGE_IDS]
            self.assertEqual(len(set(labels)), 6)
        self.assertEqual(page_label("overview", "zh"), "项目概览")
        self.assertEqual(page_label("overview", "en"), "Overview")


if __name__ == "__main__":
    unittest.main()
