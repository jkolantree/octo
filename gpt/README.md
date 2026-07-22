# BSC Claim Auditor reproducible package

The official [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) is `LIVE`. This directory is the deterministic, repository-backed BSC `0.3.0-alpha.8.dev1` source and update candidate used to inspect, reproduce, verify, or fork its configuration.

Candidate state is `PENDING`; live binding is `PENDING_VERIFICATION`; Preview validation is `PENDING`. These states do not change merely because the official service exists or candidate files were generated.

## Use the official GPT

Open [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor). You do not need to build a GPT to use the official service.

## Build and validate

From a repository checkout, regenerate and validate with:

```bash
python scripts/build_gpt_package.py
python scripts/build_gpt_package.py --check
python scripts/check_gpt_package.py
```

Release builds generate a downloadable archive. Verify its files against `SHA256SUMS`, then follow `GPT_SETUP_AND_PUBLISHING.md`; the archive intentionally does not contain executable build scripts.

Generated files must not be edited by hand. Canonical GPT-specific behavior lives in `_source/GPT_PROFILE.json`; evaluation inputs live in `_source/GPT_EVAL_SPEC.json`; the full protocol remains `../BSC_AUDIT_LLM_PACKET.md`.

## Reproduce, verify, fork, or update

Use `GPT_SETUP_AND_PUBLISHING.md`. Paste `GPT_INSTRUCTIONS.md`, upload all six Knowledge files in order, and run all 39 Preview evaluations. Creating a separate GPT is optional and produces a fork; updating the official GPT requires owner authorization and separate saved-binding evidence.

## Boundaries

This package adds no Action, API, account, analytics, or cloud storage. The GPT is an interpretive audit interface. It does not imply that the BSC Python checker or an external proof tool ran. Uploads to ChatGPT are not local-only.

This alpha.8 package emits the draft audit-return envelope consumed by the repository's non-admissive Audit Return Desk. The GPT does not run that browser or Python inspection itself.
