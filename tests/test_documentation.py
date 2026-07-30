from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_documentation import (  # noqa: E402
    check_markdown,
)


class DocumentationTests(unittest.TestCase):
    def write_document(self, root: Path, text: str, name: str = "guide.md") -> Path:
        path = root / "docs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def test_github_math_fence_preserves_literal_latex_escapes(self) -> None:
        text = r"""# Mathematical guide

The literal commands remain source text and never become control bytes.

```math
\forall x,\qquad
\frac{a}{b},\qquad
\begin{aligned}
f(\theta)&=\theta^2.
\end{aligned}
```
"""
        with tempfile.TemporaryDirectory(prefix="bsc-docs-positive-") as directory:
            root = Path(directory)
            path = self.write_document(root, text)
            self.assertEqual(check_markdown(path, root=root), [])
            data = path.read_bytes()
            for literal in (b"\\forall", b"\\frac", b"\\begin", b"\\theta"):
                self.assertIn(literal, data)
            self.assertNotIn(b"\x0c", data)

    def test_unsupported_math_delimiters_and_setext_formula_fail(self) -> None:
        text = r"""# Broken mathematics

\[
(L_2,\varepsilon_2)\star(L_1,\varepsilon_1)
=
(L_2L_1,\varepsilon_2+L_2\varepsilon_1).
\]

Inline \(x\) is also unsupported.
"""
        with tempfile.TemporaryDirectory(prefix="bsc-docs-delimiters-") as directory:
            root = Path(directory)
            path = self.write_document(root, text)
            failures = check_markdown(path, root=root)
            self.assertTrue(any("unsupported display-math opener" in item for item in failures))
            self.assertTrue(any("unsupported inline-math opener" in item for item in failures))
            self.assertTrue(any("Setext '='" in item for item in failures))

    def test_code_examples_may_name_rejected_syntax_without_triggering_it(self) -> None:
        text = r"""# Migration guide

Use neither `\[` nor `\(` in public prose. The literal `\operatorname` is
documentation, not active mathematics.

```text
C:\private\example
<script>alert("inert")</script>
\operatorname{inert}
```
"""
        with tempfile.TemporaryDirectory(prefix="bsc-docs-code-") as directory:
            root = Path(directory)
            path = self.write_document(root, text)
            self.assertEqual(check_markdown(path, root=root), [])

    def test_github_rejected_macro_fails_inline_and_fenced_math(self) -> None:
        text = r"""# Broken mathematics

Inline $\operatorname{Ker}(Q)$ must fail.

```math
\operatorname{Desc}(R)=Q.
```
"""
        with tempfile.TemporaryDirectory(prefix="bsc-docs-macro-") as directory:
            root = Path(directory)
            path = self.write_document(root, text)
            failures = check_markdown(path, root=root)
            rejected = [
                item for item in failures if "unapproved GitHub math macro" in item
            ]
            self.assertEqual(len(rejected), 2)
            self.assertTrue(all(r"\operatorname" in item for item in rejected))

    def test_unknown_math_macro_requires_renderer_review(self) -> None:
        text = r"""# Future mathematics

```math
\futuremacro{x}=x.
```
"""
        with tempfile.TemporaryDirectory(prefix="bsc-docs-future-macro-") as directory:
            root = Path(directory)
            path = self.write_document(root, text)
            failures = check_markdown(path, root=root)
            self.assertTrue(
                any(
                    r"unapproved GitHub math macro \futuremacro" in item
                    for item in failures
                )
            )

    def test_math_control_symbols_have_a_reviewed_set(self) -> None:
        accepted = r"""# Reviewed symbols

Inline $\{x\,y\}$ is supported.
"""
        rejected = r"""# Unreviewed symbol

Inline $x\?y$ must fail.
"""
        with tempfile.TemporaryDirectory(prefix="bsc-docs-symbol-") as directory:
            root = Path(directory)
            accepted_path = self.write_document(root, accepted, "accepted.md")
            rejected_path = self.write_document(root, rejected, "rejected.md")
            self.assertEqual(check_markdown(accepted_path, root=root), [])
            self.assertTrue(
                any(
                    r"unapproved GitHub math control symbol \?" in item
                    for item in check_markdown(rejected_path, root=root)
                )
            )

    def test_math_environments_are_approved_and_paired(self) -> None:
        text = r"""# Environment review

```math
\begin{future}
x=y.
\end{future}
```

```math
\begin{aligned}
x&=y.
```
"""
        with tempfile.TemporaryDirectory(prefix="bsc-docs-environment-") as directory:
            root = Path(directory)
            path = self.write_document(root, text)
            failures = check_markdown(path, root=root)
            self.assertTrue(
                any("unapproved GitHub math environment future" in item for item in failures)
            )
            self.assertTrue(
                any("unclosed math environment: aligned" in item for item in failures)
            )

    def test_controls_paths_active_html_and_magic_counts_fail(self) -> None:
        text = (
            "# Unsafe guide\n\n"
            "Publish C:" + "\\Users\\Example\\capture.txt.\n\n"
            "<iframe src=\"https://example.invalid\"></iframe>\n\n"
            "The workflow attests all 17 assets.\n\n"
            "Invisible override: \u202e\n"
        )
        with tempfile.TemporaryDirectory(prefix="bsc-docs-safety-") as directory:
            root = Path(directory)
            path = self.write_document(root, text, "SHARING_GUIDE.md")
            failures = check_markdown(path, root=root)
            self.assertTrue(any("local absolute path" in item for item in failures))
            self.assertTrue(any("active form or embedded HTML" in item for item in failures))
            self.assertTrue(any("magic asset count" in item for item in failures))
            self.assertTrue(any("U+202E" in item for item in failures))

    def test_unclosed_fence_multiple_h1_and_heading_jump_fail(self) -> None:
        text = """# First

# Second

### Jump

```math
x=y
"""
        with tempfile.TemporaryDirectory(prefix="bsc-docs-structure-") as directory:
            root = Path(directory)
            path = self.write_document(root, text)
            failures = check_markdown(path, root=root)
            self.assertTrue(
                any("expected exactly one top-level heading" in item for item in failures)
            )
            self.assertTrue(any("heading jumps" in item for item in failures))
            self.assertTrue(any("unclosed fenced block" in item for item in failures))

    def test_headingless_document_and_malformed_table_fail(self) -> None:
        text = """## No title

| left | right |
| --- | --- |
| only one |
"""
        with tempfile.TemporaryDirectory(prefix="bsc-docs-table-") as directory:
            root = Path(directory)
            path = self.write_document(root, text)
            failures = check_markdown(path, root=root)
            self.assertTrue(
                any("expected exactly one top-level heading" in item for item in failures)
            )
            self.assertTrue(any("table row has 1 columns" in item for item in failures))

    def test_latex_drive_like_token_is_not_a_local_path(self) -> None:
        text = r"""# Mathematical guide

The historical notation below is presentation text, not a Windows path.

$C:\mathrm{supp}(c)$
"""
        with tempfile.TemporaryDirectory(prefix="bsc-docs-latex-path-") as directory:
            root = Path(directory)
            path = self.write_document(root, text)
            self.assertEqual(check_markdown(path, root=root), [])

    def test_root_drive_file_is_a_local_path(self) -> None:
        text = """# Unsafe guide

Do not publish C:\\secret.txt.
"""
        with tempfile.TemporaryDirectory(prefix="bsc-docs-root-path-") as directory:
            root = Path(directory)
            path = self.write_document(root, text)
            self.assertTrue(
                any(
                    "local absolute path" in item
                    for item in check_markdown(path, root=root)
                )
            )

    def test_unix_private_path_and_preserved_style_security_fail(self) -> None:
        text = """presentation-preserved research

Do not publish {private_path} or [run](javascript:alert(1)).
"""
        text = text.format(private_path="/" + "root/private/capture.txt")
        with tempfile.TemporaryDirectory(prefix="bsc-docs-preserved-safety-") as directory:
            root = Path(directory)
            path = self.write_document(root, text)
            failures = check_markdown(path, root=root, check_style=False)
            self.assertTrue(any("local absolute path" in item for item in failures))
            self.assertTrue(any("unsafe URI scheme" in item for item in failures))

    def test_balanced_link_references_and_local_anchor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-docs-links-rich-") as directory:
            root = Path(directory)
            target = self.write_document(
                root,
                "# Target\n\n## Exact section\n",
                "target.md",
            )
            good = self.write_document(
                root,
                (
                    "# Links\n\n"
                    "[Balanced](https://example.test/a_(b))\n\n"
                    "[Target](target.md#exact-section)\n\n"
                    "[Reference][target-ref]\n\n"
                    "[target-ref]: target.md#exact-section\n"
                ),
                "good.md",
            )
            self.assertTrue(target.exists())
            self.assertEqual(check_markdown(good, root=root), [])

            missing_reference = self.write_document(
                root,
                "# Links\n\n[Missing][unknown]\n",
                "missing-reference.md",
            )
            self.assertTrue(
                any(
                    "undefined reference-style link" in item
                    for item in check_markdown(missing_reference, root=root)
                )
            )

            missing_anchor = self.write_document(
                root,
                "# Links\n\n[Missing](target.md#unknown)\n",
                "missing-anchor.md",
            )
            self.assertTrue(
                any(
                    "missing Markdown anchor" in item
                    for item in check_markdown(missing_anchor, root=root)
                )
            )

    def test_malformed_inline_and_reference_links_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-docs-links-negative-") as directory:
            root = Path(directory)
            self.write_document(root, "# Target\n", "target.md")
            malformed = self.write_document(
                root,
                "# Links\n\n[Target](target.md\n",
                "malformed.md",
            )
            self.assertTrue(
                any(
                    "malformed inline link destination" in item
                    for item in check_markdown(malformed, root=root)
                )
            )

            reference_image = self.write_document(
                root,
                "# Links\n\n![Alt][missing]\n",
                "reference-image.md",
            )
            self.assertTrue(
                any(
                    "undefined reference-style link" in item
                    for item in check_markdown(reference_image, root=root)
                )
            )

            duplicate = self.write_document(
                root,
                (
                    "# Links\n\n"
                    "[Reference][r]\n\n"
                    "[r]: missing.md\n"
                    "[r]: target.md\n"
                ),
                "duplicate.md",
            )
            failures = check_markdown(duplicate, root=root)
            self.assertTrue(
                any("duplicate reference definition" in item for item in failures)
            )
            self.assertTrue(any("broken local link" in item for item in failures))

    def test_relative_link_must_resolve_inside_repository(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-docs-links-") as directory:
            root = Path(directory)
            target = root / "schemas" / "present.json"
            target.parent.mkdir(parents=True)
            target.write_text("{}\n", encoding="utf-8")
            good = self.write_document(
                root,
                "# Links\n\n[Present](../schemas/present.json)\n",
                "good.md",
            )
            bad = self.write_document(
                root,
                "# Links\n\n[Missing](../schemas/missing.json)\n",
                "bad.md",
            )
            self.assertEqual(check_markdown(good, root=root), [])
            self.assertTrue(
                any(
                    "broken local link" in item
                    for item in check_markdown(bad, root=root)
                )
            )


if __name__ == "__main__":
    unittest.main()
