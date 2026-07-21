# BSC Audit Packet Builder

This directory is the static source deployed to GitHub Pages. It has no build-time or runtime third-party dependencies.

The page reads only the versioned protocol served from `protocol/`. Pasted text and selected files remain in browser memory; there is no form submission, analytics script, external asset, service worker, or storage API. Small text files may be embedded in the generated packet. Other files remain companion attachments and are not transmitted by this page.

Do not edit generated files under `protocol/` directly. Regenerate them from the canonical root packet:

```bash
python scripts/build_publication_assets.py
python scripts/build_publication_assets.py --check
```

Run `python scripts/check_pages.py` and the repository tests before publishing. GitHub Pages deployment occurs only from `main` through the pinned workflow in `.github/workflows/pages.yml`.
