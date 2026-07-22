# BSC public Custom GPT package

Deterministic, repository-backed setup package for BSC `0.3.0-alpha.8.dev0`. The Custom GPT itself is **UNPUBLISHED** until an authenticated human completes the editor and Preview steps.

## Build and validate

From a repository checkout, regenerate and validate with:

```bash
python scripts/build_gpt_package.py
python scripts/build_gpt_package.py --check
python scripts/check_gpt_package.py
```

Release builds generate a downloadable archive. Verify its files against `SHA256SUMS`, then follow `GPT_SETUP_AND_PUBLISHING.md`; the archive intentionally does not contain executable build scripts.

Generated files must not be edited by hand. Canonical GPT-specific behavior lives in `_source/GPT_PROFILE.json`; evaluation inputs live in `_source/GPT_EVAL_SPEC.json`; the full protocol remains `../BSC_AUDIT_LLM_PACKET.md`.

## Human handoff

Use `GPT_SETUP_AND_PUBLISHING.md`. Paste `GPT_INSTRUCTIONS.md`, upload the five Knowledge files in order, run every Preview evaluation, and only then choose link sharing or GPT Store publication.

## Boundaries

This package adds no Action, API, account, analytics, or cloud storage. The GPT is an interpretive audit interface. It does not imply that the BSC Python checker or an external proof tool ran. Uploads to ChatGPT are not local-only.

This alpha.8 package emits the draft audit-return envelope consumed by the repository's non-admissive Audit Return Desk. The GPT does not run that browser or Python inspection itself.
