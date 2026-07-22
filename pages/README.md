# BSC Audit Packet Builder

This directory is the static source deployed to GitHub Pages. It has no build-time or runtime third-party dependencies.

The page reads only the versioned protocol served from `protocol/` and a generated audit profile in `profile.js`. Pasted text and selected files remain in browser memory; there is no form submission, analytics script, external asset, service worker, or storage API. Small text files may be embedded in the generated packet. Other files remain companion attachments and are not transmitted by this page.

The audit profile comes from `gpt/_source/GPT_PROFILE.json`, so the four depths and ten-section output order remain identical between the cross-model browser builder and the Custom GPT package. The profile adds no network request, storage, account, Action, or hosted API.

Do not edit generated files under `protocol/` or `profile.js` directly. Regenerate them from the canonical root packet and profile:

```bash
python scripts/build_publication_assets.py
python scripts/build_publication_assets.py --check
```

Run `python scripts/check_pages.py` and the repository tests before publishing. GitHub Pages deployment occurs only from `main` through the pinned workflow in `.github/workflows/pages.yml`.
