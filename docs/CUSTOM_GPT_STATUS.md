# Custom GPT live-candidate status

**Repository package:** `v0.3.0-alpha.6` candidate

**Live GPT:** [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor)

**Live visibility observed:** anyone with the link

**Validation status:** incomplete; not publication-admitted

The link identifies an authenticated, owner-controlled GPT candidate. It does not establish that the live configuration byte-matches this repository release or that the complete Preview gate passed.

## Observed live configuration

The authenticated Builder showed:

- the approved name and description;
- all four approved conversation starters;
- the five expected Knowledge filenames and no extra Knowledge file;
- Web Search and Code Interpreter & Data Analysis enabled;
- Image Generation disabled;
- no configured Action;
- no recommended model;
- link sharing enabled;
- a 7,773-character alpha.5 workaround controller whose whitespace-normalized content matched the preserved handoff copy.

The Builder does not expose a byte-identical download of its internal Knowledge index. Repository hashes therefore bind the files before upload, not ChatGPT's internal representation.

## Preliminary live cases inspected

Each inspected case used a fresh conversation and the exact released fixture text pasted into the conversation.

| Case | Observed decisive behavior | Preliminary result |
|---|---|---|
| `known-true-induction` | Reconstructed base, induction hypothesis, and step; returned `proven`; disclosed that no Python, BSC, Lean, SMT, interval, or empirical run occurred | passed targeted expectations |
| `known-false-continuity` | Returned `refuted`; used `f(x)=|x|` at zero and checked continuity versus unequal one-sided derivatives | passed targeted expectations |
| `assumption-present` | Preserved `x >= 0` and the principal-square-root convention; returned `proven` | passed targeted expectations |
| `assumption-removed` | Returned `refuted`; used `x=-1` and repaired the statement to `sqrt(x^2)=|x|` or `x >= 0` | passed targeted expectations |

These targeted observations are not a complete scorecard and do not satisfy the 27-case gate. Any uninspected case remains `unrun` for publication purposes.

## Required promotion sequence

1. Build and verify the alpha.6 package.
2. Replace the live Instructions with the exact alpha.6 `GPT_INSTRUCTIONS.md`.
3. Replace all five Knowledge files with the alpha.6 files in the declared order.
4. Reconfirm name, description, starters, capabilities, absence of Apps and Actions, and link permission.
5. Run all 27 cases in fresh conversations and preserve the raw responses.
6. Score every case with `gpt/evals/GPT_MANUAL_SCORECARD.md`.
7. Require at least 18/20 and no automatic failure for every case.
8. Only then change the repository profile from `UNPUBLISHED` and record the exact live package binding.

Until that sequence completes, treat the URL as a link-shared research-preview candidate, not a verified proof engine, certification system, or deployment authority.
