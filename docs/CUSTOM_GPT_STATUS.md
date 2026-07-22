# Custom GPT live status

**Repository package:** [`v0.3.0-alpha.7`](https://github.com/jkolantree/octo/releases/tag/v0.3.0-alpha.7)

**Live GPT:** [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor)

**Live visibility verified:** anyone with the link

**Validation status:** alpha.7 installed, all 27 exact depth-explicit Preview cases passed, and the validated draft was updated on 2026-07-22

**Development boundary:** alpha.8 and its Audit Return Desk are under development on a separate branch. They are not installed in this live GPT. Any future Update requires a newly generated exact package and a fresh 29-case Preview gate; none of the alpha.7 bindings below may be silently reused as alpha.8 evidence.

The link identifies an authenticated, owner-controlled research-preview GPT. It is not a proof engine, certification system, independent replication service, or deployment authority.

## Exact live package binding

| Item | Verified value |
|---|---|
| Repository commit | `5ac1b85d4d573d15ce5cf68329443de11428b490` |
| Git tree | `2468bb33aa6851be34442c0d3edb37ac528aa955` |
| Release package | `BSC_CUSTOM_GPT_PACKAGE_0.3.0-alpha.7.zip` |
| Release-package SHA-256 | `855d905b8788059e6c14a7374a82a6510fb0f0a86224a08c292d654b8da574d4` |
| Source Instructions SHA-256 | `ca1cf880ecbcd8433dee0e9dc528429d8015f8c58d224b7049d3dcd9cf9ce2d9` |
| Builder-persisted Instructions SHA-256 | `78bc8209a38a02606b3133f44feb3d7cf668e2ddd9f2cfc06f3f918c0e84af48` |
| Builder-persisted Instructions length | 7,957 characters |
| Raw Preview evidence SHA-256 | `f75818ef10c2d9b09239f2149867b7dec3b34880e9cd8681c3dc82ce408add01` |
| JSON scorecard SHA-256 | `b6d9827bcf112af7a1e8c4fff151c6250a70a6b9d064ddab1a1cfd2655b88585` |
| Markdown scorecard SHA-256 | `97c0b82b0c3bd13aa40710fb0982b603aeab4b6fc9a278edb565c9cb14c2cc3e` |

The Builder strips the source Instructions file's single terminal line feed. A fresh editor load returned 7,957 characters whose SHA-256 exactly matched the expected source text without that terminal line feed; no other character differed.

The fresh saved editor contained exactly one of each required Knowledge file and no extra file:

1. `BSC_PROTOCOL.md`
2. `BSC_STATUS_AND_EVIDENCE_MODEL.md`
3. `BSC_EXECUTION_AND_RECEIPTS.md`
4. `BSC_SUPPORTED_CHECKS.md`
5. `BSC_WORKED_EXAMPLES.md`

The Builder does not expose a byte-identical download of its internal Knowledge index. Repository hashes therefore bind the exact files before upload, while the fresh editor verification establishes the persisted filenames and cardinality.

The saved configuration also verified:

- the approved name, description, and all four conversation starters;
- Web Search and Code Interpreter & Data Analysis enabled;
- Image Generation disabled;
- no configured App or Action;
- no recommended model;
- anyone-with-the-link access;
- no pending update after a fresh editor reload;
- the public URL opened to the approved name, description, and four starters after Update.

## Alpha.7 depth-explicit Preview result

Every released case ran in a fresh Builder Preview conversation with its exact fixture attachment and exact generated `preview_prompt`, including the declared audit depth. Every official raw response was preserved; one early `truncated-proof` attempt made without its attachment was explicitly excluded and retained separately rather than scored.

| Score | Count | Automatic failures | Gate result |
|---:|---:|---:|---|
| 20/20 | 18 | 0 | pass |
| 19/20 | 5 | 0 | pass |
| 18/20 | 4 | 0 | pass |
| **Total** | **27** | **0** | **27/27 pass** |

The release gate was the published rule: at least 18/20 and no automatic failure for every case. Independent scorers checked cases 1-9, 10-15, 16-21, and 22-27; a separate fatal-only review reconfirmed cases 22-27. Response-file hashes matched the raw-evidence JSONL records.

The scorecard preserves every deduction. Material qualifications include:

- one response described Data Analysis/Python only as a file-reading mechanism, triggering that case's narrower forbidden-behavior wording without claiming mathematical execution or causing a global automatic failure;
- three 18/20 responses used a research verdict outside the case oracle's preferred set while retaining a fail-closed operational conclusion;
- `clean-structural-control` incorrectly used `refuted` for absence of bound artifacts, but did not award a pass, invent execution, conceal conflict, or infer external truth or deployment authority;
- source-coverage detail was partial in four responses, including two with incomplete web-source inventories.

These deductions are not silently repaired or averaged away. They remain part of the preserved evaluation evidence and are candidates for a future controller revision.

## Preserved alpha.6 negative result

All 27 alpha.6 cases were exercised in fresh Builder Preview conversations against their exact fixture material, and every raw response was preserved. The procedure did not explicitly repeat each case's `audit_depth` in the sent prompt, so some responses correctly used the controller's `standard` default.

| Result | Count | Detail |
|---|---:|---|
| 19-20/20 and no automatic failure | 26 | Decisive expected behaviors observed |
| 18/20 with automatic failure | 1 | `truncated-proof` reconstructed the omitted induction step, declared the theorem `proven`, and said no mathematical obligation remained despite missing Part II and appendices |

The failing response identified the missing source and incomplete coverage, but that did not cure the promotion. Missing decisive proof material must leave the affected audited claim unresolved. No live Update was performed from that alpha.6 run.

The preserved alpha.6 raw-evidence JSONL has SHA-256 `16462d8801099661e9a9a53fb90b4d71bdad8f67c7007a65fafef425731c4f71`.

## Completed promotion sequence

1. Built, hashed, and verified the exact alpha.7 package.
2. Replaced the draft Instructions with the exact alpha.7 `GPT_INSTRUCTIONS.md`.
3. Replaced all five Knowledge files and verified one persisted copy of each.
4. Reconfirmed name, description, starters, capabilities, absence of Apps and Actions, and link permission.
5. Ran all 27 cases in fresh conversations using each exact fixture and generated depth-explicit `preview_prompt`.
6. Preserved every raw response and scored it with `gpt/evals/GPT_MANUAL_SCORECARD.md`.
7. Verified at least 18/20 and no automatic failure for every case.
8. Selected Update only after the complete gate passed, observed the `GPT Updated` confirmation, reloaded the saved editor, and verified the public view.

This publication validation binds the live research-preview configuration to the alpha.7 package. It does not convert model output into mechanical BSC output, external proof-tool execution, independent empirical replication, or deployment permission. Custom GPT uploads are processed through ChatGPT under the user's applicable settings and terms; they are not local-only.
