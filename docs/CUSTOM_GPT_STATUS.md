# Official Custom GPT status

The official [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) is built and link-shared as a research preview. This repository is the reproducible source for its configuration lineage, evaluation suite, and candidate updates. Anyone may inspect or reproduce that work, and may create an independent fork without implying official status.

This page deliberately separates service availability, configuration identity, Preview validation, source deployment, and immutable releases. A timestamped machine-readable snapshot is available in [PUBLICATION_STATUS.json](PUBLICATION_STATUS.json).

## Current state

Verified on 2026-07-24:

| Surface | State | Exact binding or boundary |
|---|---|---|
| Official Custom GPT | **live** | Public URL above; supported alpha.8 surface is a bounded human-readable audit |
| Targeted alpha.8 live regressions | **passed** | Canonical status-only routing passed; conflicting verified evidence blocked admission without emitting a SHA-256 digest |
| Complete 12-case Preview evaluation | **not completed** | This prerelease does not claim `pass_12_of_12` or complete live Builder-byte binding |
| GitHub prerelease | **published** | [`v0.3.0-alpha.8`](https://github.com/jkolantree/octo/releases/tag/v0.3.0-alpha.8); the immutable tag and release assets are the exact repository binding |
| Public Pages | **deployed** | English interface is live at [jkolantree.github.io/octo](https://jkolantree.github.io/octo/) |
| Japanese Pages route | **candidate; not deployed** | The planned `/octo/ja.html` route returned HTTP 404 at `2026-07-22T18:37:44Z`; do not advertise it as live until the post-deploy route and metadata smoke check passes |

The release deliberately separates “working research preview” from “fully Preview-validated.” Repository checks and the two repaired high-risk live routes passed. The full 12-case roster was not completed, so source CI and targeted checks must not be represented as a substitute for that broader evaluation.

## Released compact scope

The `0.3.0-alpha.8` prerelease:

- keeps mutable service state in this timestamped record instead of embedding it in durable behavioral Knowledge;
- presents the official GPT first, with reproduction, evaluation, and forks as open-source capabilities;
- adds Japanese human-facing guidance while preserving canonical machine tokens;
- uses five public Knowledge uploads; the retired [`BSC_EXECUTION_AND_RECEIPTS.md`](standalone/BSC_EXECUTION_AND_RECEIPTS.md) derivative remains standalone repository history but is not uploaded to the official GPT;
- returns compact human-readable duties 1-9 for scientific audits within explicit 300/650/1,000-word budgets, including tables; official-product status-only responses bypass duties 1-9 and return only concise supplied canonical states;
- records source coverage only for case targets and evidence sources actually used or attempted, plus one short protocol-configuration note;
- keeps unexecuted BSC, formal, and empirical work `not_run`, never `not_applicable`;
- disables downloadable machine records, the artifact compiler, Base64/shards/transport, and section 10 in the official GPT; the compiler and Return Desk remain supervised standalone tooling.

No prior artifact-profile Preview result validates this changed compact profile. The public GPT and GitHub prerelease are available, but neither is promoted as `pass_12_of_12` or fully Preview-validated.

The preserved 39-case artifact-profile suite, D01/D02 preflights, compiler/transport requirements, ordering, and results are historical and superseded for this compact profile. They neither govern nor validate its 12-case gate.

## Exact trust boundary

The GPT is an authenticated, owner-controlled research-preview interface. It is not a proof engine, certification system, independent replication service, or deployment authority.

- Custom GPT uploads are processed through ChatGPT under the user's applicable settings and terms; they are not local-only.
- The compact official profile may use Data Analysis for attachment inspection or a bounded calculation, but it does not create audit artifacts or run the artifact compiler.
- ChatGPT file access or Data Analysis is not a versioned BSC Python result unless the checker actually ran and the identified result is inspectable.
- Lean, SMT, interval, or empirical claims require separately identified supervised execution and admissible evidence.
- A fluent report, hash-shaped string, submitted receipt, or internally consistent `audit_return.json` does not establish truth, source authenticity, independent replay, or deployment permission.

## Alpha.8 release boundary

This minimal prerelease may ship when the exact repository candidate passes deterministic local checks and branch CI, and the repaired status-routing and conflicting-evidence paths pass targeted live regression. That is the supported alpha.8 claim.

The exact 12-case compact roster remains the gate for any future `pass_12_of_12` or fully Preview-validated claim. Its incomplete state is disclosed rather than averaged away or silently relabeled. The former 39-case artifact workflow, compiler output, downloadable machine records, Base64, shards, and transport are not part of the supported public-GPT surface.

Any later change to Instructions, Knowledge, capabilities, or Builder configuration requires a new binding record and proportionate regression testing; this prerelease does not validate changed service bytes.

## Preserved alpha.7 baseline

The immutable `v0.3.0-alpha.7` package completed 27/27 depth-explicit Preview cases at 18/20 or better with no automatic failures before its live Update. The preserved score distribution was 18 cases at 20/20, five at 19/20, and four at 18/20. Its limitations and deductions remain evidence, not silently repaired history.

| Alpha.7 artifact | SHA-256 |
|---|---|
| Release package | `855d905b8788059e6c14a7374a82a6510fb0f0a86224a08c292d654b8da574d4` |
| Raw Preview evidence | `f75818ef10c2d9b09239f2149867b7dec3b34880e9cd8681c3dc82ce408add01` |
| JSON scorecard | `b6d9827bcf112af7a1e8c4fff151c6250a70a6b9d064ddab1a1cfd2655b88585` |
| Markdown scorecard | `97c0b82b0c3bd13aa40710fb0982b603aeab4b6fc9a278edb565c9cb14c2cc3e` |

This historical baseline does not transfer to a changed controller, Knowledge set, Builder configuration, or evaluation suite.
