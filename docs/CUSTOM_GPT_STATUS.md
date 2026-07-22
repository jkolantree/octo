# Custom GPT live-candidate status

**Repository package:** `v0.3.0-alpha.7` candidate

**Live GPT:** [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor)

**Live visibility observed:** anyone with the link

**Validation status:** alpha.7 not yet installed or publication-admitted

The link identifies an authenticated, owner-controlled research-preview candidate. The public GPT was not updated from the failed alpha.6 draft, so the live configuration does not yet claim to match alpha.6 or alpha.7.

## Observed account and configuration boundary

The authenticated Builder showed:

- the approved name and description;
- all four approved conversation starters;
- the five expected Knowledge filenames and no extra Knowledge file;
- Web Search and Code Interpreter & Data Analysis enabled;
- Image Generation disabled;
- no configured App or Action;
- no recommended model;
- link sharing enabled.

The Builder does not expose a byte-identical download of its internal Knowledge index. Repository hashes therefore bind the files before upload, not ChatGPT's internal representation. The Builder also strips the controller's single terminal line feed; the persisted visible text otherwise matched the supplied draft exactly.

## Preserved alpha.6 full-run result

All 27 released cases were exercised in fresh Builder Preview conversations against their exact fixture material, and every raw response was preserved locally. The procedure did not explicitly repeat each case's `audit_depth` in the sent prompt, so some responses correctly used the controller's `standard` default. Alpha.7 removes that procedural ambiguity by generating an exact depth-explicit `preview_prompt` for every case.

| Result | Count | Detail |
|---|---:|---|
| 19-20/20 and no automatic failure | 26 | Decisive expected behaviors observed |
| 18/20 with automatic failure | 1 | `truncated-proof` reconstructed the omitted induction step, declared the theorem `proven`, and said no mathematical obligation remained despite missing Part II and appendices |

The failing response did identify the missing source and incomplete coverage, but that did not cure the promotion. Missing decisive proof material must leave the affected audited claim unresolved. No live Update was performed.

The preserved alpha.6 raw-evidence JSONL has SHA-256 `16462d8801099661e9a9a53fb90b4d71bdad8f67c7007a65fafef425731c4f71`.

## Alpha.7 repair

Alpha.7:

- makes a model-completed missing or truncated proof only a proposed repair, never grounds for `proven` or closed proof obligations;
- binds that rule in the canonical protocol, compact controller, case oracle, dedicated automatic-failure list, and tests;
- generates and validates an exact `preview_prompt` containing the declared audit depth for every case;
- requires the exact fixture and generated prompt in each fresh Preview conversation.

## Required promotion sequence

1. Build, hash, and verify the exact alpha.7 package.
2. Replace the draft Instructions with the exact alpha.7 `GPT_INSTRUCTIONS.md`.
3. Replace all five Knowledge files with the alpha.7 files in the declared order.
4. Reconfirm name, description, starters, capabilities, absence of Apps and Actions, and link permission.
5. Run all 27 cases in fresh conversations using each exact fixture and generated `preview_prompt`.
6. Preserve every raw response and score it with `gpt/evals/GPT_MANUAL_SCORECARD.md`.
7. Require at least 18/20 and no automatic failure for every case.
8. Only then select Update, verify the public GPT from a fresh view, and record the exact live package binding in a follow-up status commit.

Until that sequence completes, treat the URL as a link-shared research-preview candidate, not a verified proof engine, certification system, or deployment authority.
