from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_pages import PageParser  # noqa: E402


class DuplicateHtmlAttributeTests(unittest.TestCase):
    def test_duplicate_attributes_are_rejected_before_dictionary_collapse(self) -> None:
        mutations = {
            "html language": ('<html lang="en" LANG="ja">', ("html", "lang")),
            "script source": ('<script src="app.js" src="evil.js"></script>', ("script", "src")),
            "CSP content": (
                '<meta http-equiv="Content-Security-Policy" content="default-src self" content="default-src *">',
                ("meta", "content"),
            ),
            "link relation": ('<a href="/" rel="noopener" REL="opener">link</a>', ("a", "rel")),
        }
        for label, (html, expected) in mutations.items():
            with self.subTest(label=label):
                parser = PageParser()
                parser.feed(html)
                self.assertIn(expected, parser.duplicate_attributes)

    def test_reviewed_pages_have_no_duplicate_attributes(self) -> None:
        for filename in ("index.html", "ja.html"):
            with self.subTest(filename=filename):
                parser = PageParser()
                parser.feed((ROOT / "pages" / filename).read_text(encoding="utf-8"))
                self.assertEqual(parser.duplicate_attributes, [])


if __name__ == "__main__":
    unittest.main()
