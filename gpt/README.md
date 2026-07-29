# BSC Claim Auditor reproducible package

The official [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) is `LIVE`. This directory preserves the deterministic, repository-backed BSC `0.3.0-alpha.10` package used to inspect, reproduce, verify, or fork its configuration.

Candidate state is `PENDING`; live binding is `PENDING_VERIFICATION`; Preview validation is `PENDING`. These states do not change merely because the official service exists or candidate files were generated.

This package may be released only from the exact immutable tag `v0.3.0-alpha.10` recorded in its release manifest. Before tagging it remains a candidate. Never move an existing tag, and use a new version and tag for any later changed package.

The current compact gate is exactly 12 fresh-conversation cases. The preserved 39-case artifact-profile suite, its D01/D02 preflights, compiler/transport requirements, and prior results are historical and superseded; they neither govern nor validate this compact candidate.

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

Use `GPT_SETUP_AND_PUBLISHING.md` and its exact 12-case compact Preview roster. Paste `GPT_INSTRUCTIONS.md`, upload all five Knowledge files in order, validate the compact human-response profile, freeze exact candidate/evaluation bytes, and run only the declared compact gate. Creating a separate GPT is optional and produces a fork; updating the official GPT requires owner authorization and separate saved-binding evidence.

## Boundaries

This package adds no Action, API, account, analytics, or cloud storage. The GPT is an interpretive audit interface. It does not imply that the BSC Python checker or an external proof tool ran. Uploads to ChatGPT are not local-only.

The official GPT compact profile emits no draft audit-return envelope or downloadable machine record. The repository's compiler and non-admissive Audit Return Desk remain available only as separately invoked, supervised standalone tooling.
