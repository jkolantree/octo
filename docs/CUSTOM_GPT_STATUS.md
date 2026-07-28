# Official Custom GPT status

The official [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) is built and link-shared as a research preview. This repository is the reproducible source for its configuration lineage, evaluation suite, and candidate updates. Anyone may inspect or reproduce that work, and may create an independent fork without implying official status.

This page separates service availability, configuration identity, Preview validation, source deployment, and release identity. [PUBLICATION_STATUS.json](PUBLICATION_STATUS.json) preserves a superseded 2026-07-22 snapshot for historical evidence; it is not a current-state feed.

## Current state

Pre-update read-only verification on 2026-07-28:

| Surface | State | Exact binding or boundary |
|---|---|---|
| Official Custom GPT | **live; inspected before alpha.9 update** | Public URL above; owner editor showed `Live`, link access, the Quick-UX Instructions, five Knowledge filenames, Web Search on, Data Analysis on, Image Generation off, and no Action |
| Conversation-starter boundary | **editor six; public four; alpha.9 source four** | The owner editor contained six starters while the public page rendered only the first four. Alpha.9 intentionally makes those four visible starters the complete canonical list, in exact public order |
| Exact live/source binding | **unresolved until post-save verification** | The pre-update editor/source starter counts differ. ChatGPT also does not independently expose indexed Knowledge bytes for hashing |
| Complete 12-case Preview evaluation | **required for this Knowledge-changing candidate** | No `pass_12_of_12` is inferred from historical evidence; the exact alpha.9 freeze must pass all 12 fresh cases |
| Repository release line | **v0.3.0-alpha.9** | The exact commit, tree, tag, and assets are bound by the immutable tag and `RELEASE_MANIFEST.json`; changed alpha.9 bytes must never be labeled alpha.8 |
| Prior GitHub prerelease | **preserved historical release** | [`v0.3.0-alpha.8`](https://github.com/jkolantree/octo/releases/tag/v0.3.0-alpha.8) remains at commit `c6120093e49c658318553900028761a171dbf47b`, tree `a4f7d89ac2e09f2887797c0c16b6f603a29d27ea`; the tag must not move |
| GitHub release object | **mutable service record** | GitHub reported `immutable=false`; release assets and release-page metadata must not be described as intrinsically immutable |
| Public Pages | **deployment verified separately** | [English](https://jkolantree.github.io/octo/) and [Japanese](https://jkolantree.github.io/octo/ja.html) routes must match the merged alpha.9 protocol metadata after Pages deployment |

Availability, targeted regressions, and source CI do not substitute for complete Preview validation. The preserved 39-case artifact-profile campaign, D01/D02 preflights, compiler/transport requirements, and negative results remain historical evidence and must not be restarted or spliced into the compact 12-case gate.

## Current compact contract and maintenance boundary

The live Instructions route an ordinary no-depth claim to Quick: verdict first, at most 250 words and four short blocks, with no table unless materially necessary. Alpha.9 reconciles the generated Knowledge projection to that same contract.

The canonical starter list is exactly:

1. Start a 60-second claim audit
2. 60秒で主張を点検する
3. Show a simple example first
4. まず簡単な例を見る

The official GPT continues to use five public Knowledge uploads; the retired [`BSC_EXECUTION_AND_RECEIPTS.md`](standalone/BSC_EXECUTION_AND_RECEIPTS.md) derivative remains standalone repository history. Downloadable machine records, compiler output, Base64, shards, transport, and section 10 remain outside the public GPT.

No prior artifact-profile result validates this compact profile. The 12-case compact roster remains the gate for any future `pass_12_of_12` or fully Preview-validated claim.

## Exact trust boundary

The GPT is an authenticated, owner-controlled research-preview interface. It is not a proof engine, certification system, independent replication service, or deployment authority.

- Custom GPT uploads are processed through ChatGPT under the user's applicable settings and terms; they are not local-only.
- The compact official profile may use Data Analysis for attachment inspection or a bounded calculation, but it does not create audit artifacts or run the artifact compiler.
- ChatGPT file access or Data Analysis is not a versioned BSC Python result unless the checker actually ran and the identified result is inspectable.
- Lean, SMT, interval, or empirical claims require separately identified supervised execution and admissible evidence.
- A fluent report, hash-shaped string, submitted receipt, or internally consistent `audit_return.json` does not establish truth, source authenticity, independent replay, or deployment permission.

## Alpha.8 and alpha.9 boundary

Alpha.8 is the exact tagged package at `c6120093…`; it does not contain the later live/main UX hotfix or alpha.9 maintenance bytes. Its tagged release notes retain the then-current 300-word Quick description as historical release evidence.

Alpha.9 uses a new version, binding record, deterministic release gates, and immutable tag. Any later changed exact package requires another new version and tag. Existing tags and release history must not be rewritten.

## Preserved alpha.7 baseline

The immutable `v0.3.0-alpha.7` package completed 27/27 depth-explicit Preview cases at 18/20 or better with no automatic failures before its live Update. The preserved score distribution was 18 cases at 20/20, five at 19/20, and four at 18/20. Its limitations and deductions remain evidence, not silently repaired history.

| Alpha.7 artifact | SHA-256 |
|---|---|
| Release package | `855d905b8788059e6c14a7374a82a6510fb0f0a86224a08c292d654b8da574d4` |
| Raw Preview evidence | `f75818ef10c2d9b09239f2149867b7dec3b34880e9cd8681c3dc82ce408add01` |
| JSON scorecard | `b6d9827bcf112af7a1e8c4fff151c6250a70a6b9d064ddab1a1cfd2655b88585` |
| Markdown scorecard | `97c0b82b0c3bd13aa40710fb0982b603aeab4b6fc9a278edb565c9cb14c2cc3e` |

This historical baseline does not transfer to a changed controller, Knowledge set, Builder configuration, or evaluation suite.
