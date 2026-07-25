# BSC Audit Packet Builder and Audit Return Desk

This directory is the static source deployed to GitHub Pages. It has no build-time or runtime third-party dependencies.

The English entry point is `index.html`; `ja.html` is the first-class Japanese entry point. Both pages expose a visible language switch and share the same protocol, generated profile, Return Desk runtime, and application logic. Locale catalogs change only human-facing page text and the requested human report language. They do not translate or alter protocol identifiers, JSON keys or enum values, finding codes, paths, hashes, versions, filenames, artifact identifiers, or inspection JSON.

The page reads only the versioned protocol served from `protocol/` and a generated audit profile in `profile.js`. Its code makes no target-data network request and does not intentionally persist target material; there is no form submission, analytics script, external asset, service worker, or storage API. Browser or operating-system history, crash recovery, swap, accessibility services, enhanced spellcheck, extensions, clipboard contents, and downloaded files remain outside the page's control. Sensitive textareas explicitly disable spellcheck, autocomplete, autocorrect, and autocapitalization, but users still need an appropriate browser and operating-system threat model. Small files explicitly identified as text are embedded only when strict UTF-8 decoding succeeds; the page does not silently guess Shift-JIS, CP932, or another encoding. Other files remain companion attachments and are not transmitted by this page code.

The already-built official BSC Claim Auditor is shown before compatible-model alternatives on both language pages. Candidate source in this directory does not prove that the same bytes are installed or Preview-validated in the live GPT; the linked status record preserves that boundary. The official link leaves the browser-local surface: material uploaded to the Custom GPT is processed through ChatGPT under the user's applicable settings and terms.

The Return Desk accepts one strict `audit_return.json` draft plus locally selected artifact files. It rejects duplicate JSON keys, verifies the protocol and embedded schema bytes before use, recomputes cross-record semantics, and hashes selected artifacts locally. The browser reads at most 32 artifacts, hashes at most 64 MiB per file and 256 MiB total, and leaves files beyond those limits review-needed. File and inspection operations use cancellation epochs so Clear, typing, removal, or a newer selection cannot restore stale state. Each downloadable result binds the exact return-text SHA-256 and a canonical sorted attachment-descriptor list and SHA-256.

The audit profile comes from `gpt/_source/GPT_PROFILE.json`, so the four depths and ten-section output order remain identical between the cross-model browser builder and the Custom GPT package. The Return Desk contract comes from `schemas/audit-return-v0.1.schema.json`; its exact source bytes and SHA-256 are embedded in the generated profile. These additions create no target-data network request, storage, account, Action, or hosted API.

A `consistent` Return Desk result means only that the supplied envelope, projections, references, and available local byte bindings are internally consistent under implemented checks. It does not prove a claim, authenticate a source, establish that an external execution occurred, admit evidence, or grant deployment permission. Downloaded inspection JSON contains no attached file bytes but can reveal filenames, identifiers, and hashes; hashes do not anonymize private material.

Do not edit generated files under `protocol/` or `profile.js` directly. Regenerate them from the canonical root packet and profile:

```bash
python scripts/build_publication_assets.py
python scripts/build_publication_assets.py --check
```

Run the browser parity tests and Pages checks before publishing:

```bash
node --test tests/return_desk_runtime.test.cjs
python scripts/check_pages.py
python scripts/check_localization.py
```

GitHub Pages deployment occurs only from `main` through the pinned workflow in `.github/workflows/pages.yml`.
