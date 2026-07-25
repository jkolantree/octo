# Official Custom GPT status

The official [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) is built and link-shared as a research preview. This repository is the reproducible source for its configuration lineage, evaluation suite, and candidate updates. Anyone may inspect or reproduce that work, and may create an independent fork without implying official status.

This page deliberately separates service availability, configuration identity, Preview validation, source deployment, and immutable releases. A timestamped machine-readable snapshot is available in [PUBLICATION_STATUS.json](PUBLICATION_STATUS.json).

## Current state

Verified on 2026-07-22:

| Surface | State | Exact binding or boundary |
|---|---|---|
| Official Custom GPT | **live** | Public URL above; runtime identity smoke returned controller `0.3.0-alpha.8.dev0` and Profile SHA-256 `99d6f78d3af21c68ddb6545b034d340e77b73d2f1ffa657120d4147455128b90` |
| Alpha.8.dev0 Preview evaluation | **not completed** | No preserved complete post-update run satisfies the candidate's generated case gate; the identity smoke is not an evaluation |
| Repository `main` | **merged** | commit `1e5c60360d8473e170f828597241dc9ab5844d3b`, tree `f1460fb6e84c11ad363e3c8796ea22a3c2a4fde8` |
| GitHub Actions for that merge | **passed** | exact-audit and Pages publication both completed successfully |
| Public Pages | **deployed** | alpha.8.dev0 is live at [jkolantree.github.io/octo](https://jkolantree.github.io/octo/) |
| Japanese Pages route | **candidate; not deployed** | The planned `/octo/ja.html` route returned HTTP 404 at `2026-07-22T18:37:44Z`; do not advertise it as live until the post-deploy route and metadata smoke check passes |
| Latest GitHub Release | **unchanged** | [`v0.3.0-alpha.7`](https://github.com/jkolantree/octo/releases/tag/v0.3.0-alpha.7), commit `5ac1b85d4d573d15ce5cf68329443de11428b490` |
| Final alpha.8 release candidate | **pending gates** | `0.3.0-alpha.8`; isolated local gates and a fresh frozen 12-case compact-profile Preview regression are required before live Update, merge, tag, or release |

Repository CI passed and the public GPT's controller identity was confirmed. The complete alpha.8.dev0 behavior evaluation was not preserved, so its Preview-validation state remains **not completed**. Source checks and identity checks do not substitute for fresh-conversation behavior evaluation.

## Candidate scope

The final `0.3.0-alpha.8` candidate:

- keeps mutable service state in this timestamped record instead of embedding it in durable behavioral Knowledge;
- presents the official GPT first, with reproduction, evaluation, and forks as open-source capabilities;
- adds Japanese human-facing guidance while preserving canonical machine tokens;
- uses five public Knowledge uploads; the retired [`BSC_EXECUTION_AND_RECEIPTS.md`](standalone/BSC_EXECUTION_AND_RECEIPTS.md) derivative remains standalone repository history but is not uploaded to the official GPT;
- returns compact human-readable duties 1-9 for scientific audits within explicit 300/650/1,000-word budgets, including tables; official-product status-only responses bypass duties 1-9 and return only concise supplied canonical states;
- records source coverage only for case targets and evidence sources actually used or attempted, plus one short protocol-configuration note;
- keeps unexecuted BSC, formal, and empirical work `not_run`, never `not_applicable`;
- disables downloadable machine records, the artifact compiler, Base64/shards/transport, and section 10 in the official GPT; the compiler and Return Desk remain supervised standalone tooling.

No prior artifact-profile Preview result validates this changed compact candidate. Until it passes its complete fresh Preview gate, the public GPT remains available but is not promoted as alpha.8 Preview-validated.

The preserved 39-case artifact-profile suite, D01/D02 preflights, compiler/transport requirements, ordering, and results are historical and superseded for this compact profile. They neither govern nor validate its 12-case gate.

## Exact trust boundary

The GPT is an authenticated, owner-controlled research-preview interface. It is not a proof engine, certification system, independent replication service, or deployment authority.

- Custom GPT uploads are processed through ChatGPT under the user's applicable settings and terms; they are not local-only.
- The compact official profile may use Data Analysis for attachment inspection or a bounded calculation, but it does not create audit artifacts or run the artifact compiler.
- ChatGPT file access or Data Analysis is not a versioned BSC Python result unless the checker actually ran and the identified result is inspectable.
- Lean, SMT, interval, or empirical claims require separately identified supervised execution and admissible evidence.
- A fluent report, hash-shaped string, submitted receipt, or internally consistent `audit_return.json` does not establish truth, source authenticity, independent replay, or deployment permission.

## Promotion gate for alpha.8

Before any merge, live Update, or GitHub release:

1. Generate and validate the exact package from a clean candidate tree.
2. Verify the Instructions character limit and reserved headroom, the five exact Knowledge files and their offline release hashes, zero public-Knowledge digest values, metadata, capabilities, absence of Apps or Actions, and absence of the execution-and-receipts Knowledge upload.
3. Run the exact 12-case compact roster in a fresh Builder Preview conversation using each declared fixture and current compact `preview_prompt`; the preserved historical 39-case artifact suite is not this gate.
4. Confirm each response stays within its declared compact budget, completes the human audit, and does not offer machine records, compiler output, Base64, shards, transport, or section 10.
5. Preserve each raw response as exact UTF-8 and require native exit 0 from `python scripts/check_compact_preview_response.py --case-id <case-id> --response-file <saved-response.txt>` before scoring; exits 1 or 2 are automatic failures.
6. Score each checker-passing response against the generated oracle.
7. Require at least 18/20 and no automatic failure for every case; do not average away one failed case.
8. Run the repository, Pages, localization, privacy, release-integrity, and Null-Discrimination checks.
9. Only after all gates pass, update the live GPT and then reverify the public identity and timestamped status record.

## Preserved alpha.7 baseline

The immutable `v0.3.0-alpha.7` package completed 27/27 depth-explicit Preview cases at 18/20 or better with no automatic failures before its live Update. The preserved score distribution was 18 cases at 20/20, five at 19/20, and four at 18/20. Its limitations and deductions remain evidence, not silently repaired history.

| Alpha.7 artifact | SHA-256 |
|---|---|
| Release package | `855d905b8788059e6c14a7374a82a6510fb0f0a86224a08c292d654b8da574d4` |
| Raw Preview evidence | `f75818ef10c2d9b09239f2149867b7dec3b34880e9cd8681c3dc82ce408add01` |
| JSON scorecard | `b6d9827bcf112af7a1e8c4fff151c6250a70a6b9d064ddab1a1cfd2655b88585` |
| Markdown scorecard | `97c0b82b0c3bd13aa40710fb0982b603aeab4b6fc9a278edb565c9cb14c2cc3e` |

This historical baseline does not transfer to a changed controller, Knowledge set, Builder configuration, or evaluation suite.
