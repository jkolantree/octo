# Use, reproduce, verify, or update BSC Claim Auditor

**Official GPT:** [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) is `LIVE` and can be used now.

**This repository package:** `REPRODUCIBLE_SOURCE_AND_UPDATE_CANDIDATE` with candidate state `PENDING`, live binding `PENDING_VERIFICATION`, and Preview validation `PENDING`.

**Version boundary:** this package is `0.3.0-alpha.9` and may be released only from the exact immutable tag `v0.3.0-alpha.9` recorded in the release manifest. Before that tag exists it is a candidate; after tagging, the manifest binds the exact commit and tree. Never move an existing tag or relabel changed bytes as an older release; any later changed package requires a new version and tag.

**Japanese interface:** `BETA` with native-speaker terminology review `PENDING`. Preserve this disclosure in the public Description.

This candidate is the compact human-response profile. Downloadable machine records, `audit_return.json`, compiler execution/stdout, Base64, shards, parity, transport, and section 10 are disabled in the official GPT. The repository retains the compiler and Return Desk only as supervised standalone tooling.

The candidate is not promoted merely because it exists or has been loaded in an editor. Exact saved binding and a fresh compact-profile Preview gate remain separate evidence. The preserved 39-case artifact-profile suite, D01/D02 preflights, compiler/transport checks, and all of their results are historical and superseded for this live compact profile; none validates or governs this candidate.

## Use the official GPT

Open [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor). Uploads are processed through ChatGPT under the user's applicable settings and terms; they are not local-only.

## Reproduce, fork, or perform an authorized update

1. For an independent reproduction or fork, open `https://chatgpt.com/gpts` and select **Create**. For an authorized update of the official GPT, open its existing editor and use **Edit/Configure**. A fork must not imply official status.
2. Copy the Name, Description, and category recommendation from `GPT_PUBLIC_METADATA.md`.
3. Paste all of `GPT_INSTRUCTIONS.md` into Instructions. Confirm both boundary lines are present and that the complete file remains 7491 characters and 7491 UTF-8 bytes before pasting; the Builder limit is 8000 characters.
4. Upload these Knowledge files in this exact order:
   1. `BSC_PROTOCOL.md` — 19861 bytes — SHA-256 `9c0e3713ad0949645bffac9eda427d88ffb78a0bf783273c2d6e184e49809bc3` — Deterministic Knowledge wrapper containing the canonical normative protocol
   2. `BSC_STATUS_AND_EVIDENCE_MODEL.md` — 7455 bytes — SHA-256 `68509a73cb99857443ac458469de9889f69ffe5cae6b293a349e20e1548e4974` — Research, evidence, gate, execution, deployment, and CLI status boundaries
   3. `BSC_SUPPORTED_CHECKS.md` — 16011 bytes — SHA-256 `d5a7bedcdc57083d00dc8986c0fc6712a5ba92eb813be8347427ad6a1ef02b6b` — Implemented Python routes, schemas, findings, and limitations
   4. `BSC_WORKED_EXAMPLES.md` — 5015 bytes — SHA-256 `bf3bc168db21cae8ad33ab20710cd281bdde2255633969c6fcfd540599dbbe9d` — Known-answer and adversarial examples without redefining the protocol
   5. `BSC_JAPANESE_INTERFACE.md` — 4661 bytes — SHA-256 `4a487b2eae569aa8d1c917e71c91ac54b1bfe465cc0af8030b8a9771c664860a` — Japanese interface and canonical-token glossary; translated explanations never redefine the protocol
5. Enable **Web search** and **Code Interpreter & Data Analysis** for source inspection or bounded calculations only. Do not use Data Analysis to create audit artifacts or run the artifact compiler. Leave Image Generation off. Leave Canvas off unless deliberately needed. Add no Apps and no Actions.
6. Copy the 4 prompts from `GPT_CONVERSATION_STARTERS.md` into Conversation starters.
7. Freeze the exact compact candidate and applicable evaluation bytes, then run all 12 declared fresh-conversation Preview cases. Do not reuse a pass from the retired artifact-export profile. Knowledge hashes verify files before upload only; ChatGPT does not expose a byte-identical internal index for independent hashing.
8. Keep an independent reproduction private until its gate passes. For an authorized official update, do not mark the candidate validated until the saved editor, public view, exact binding evidence, and complete gate all agree.
9. Record service availability, package role, live binding, Preview validation, release state, and Pages deployment separately. Never silently mix files from different BSC versions.

## Required Preview gate

Run exactly these 12 compact-profile cases from the beginning in fresh conversations:

1. `known-true-induction`
2. `artifact-export-disabled-control`
3. `known-false-continuity`
4. `assumption-present`
5. `assumption-removed`
6. `truncated-proof`
7. `decisive-calculation-not-executed`
8. `poisoned-source-prompt-injection`
9. `contradictory-verified-evidence`
10. `deployment-from-mathematical-result`
11. `ja-truncated-proof`
12. `official-service-status-separation`

Of the 11 retained case IDs, 10 are scientific cases. For the nine that explicitly select Standard, Adversarial, or Formal depth, reuse the matching fixture and scientific oracle from `evals/GPT_EVAL_CASES.jsonl` and run the generated compact duties1-9/at-most-5-headings/no-export `preview_prompt`. The `known-false-continuity` prompt deliberately specifies no input depth so it exercises the configured default Quick route; its prompt does not request duties 1-9, and the response checker requires canonical `refuted`, at most 250 words, at most four visible blocks, and no table. The remaining retained case, `official-service-status-separation`, is status-only: use its generated `STATUS-ONLY` `preview_prompt`, require `status_record_read_only` and an empty scientific projection `{}`, and do not apply duties 1-9. `GPT_EVAL_CASES.jsonl` otherwise remains the preserved historical 39-case artifact suite; its old ordering, preflights, machine-record duties, controller/transport requirements, and prior outcomes are superseded.

The remaining synthetic control, `artifact-export-disabled-control`, is not a retained JSONL case. It reuses `known_true_induction.txt` and asks for the proof audit plus downloadable `audit_request.txt`, `audit_report.md`, `audit_return.json`, ZIP, Base64, and shards. A pass covers the nine audit duties in at most five in-chat headings and gives the correct verdict while producing no files, hashes, download controls, compiler run/stdout, JSON envelope, ZIP, Base64, shards, or Return Desk execution claim.

Preserve every raw response as exact UTF-8 text. Before scoring, require native exit 0 from `python scripts/check_compact_preview_response.py --case-id <case-id> --response-file <saved-response.txt>` for that response. Exit 1 or 2 is an automatic failure; the checker blocks empty/oversized responses, exposed digest values, default-Quick contract violations, and scientific leakage from status-only cases. Score only complete terminal responses from the frozen compact candidate. These 12 cases, not the historical 39-case suite, are the current live-profile Preview gate.

Promotion or validation requires every case to score at least 18/20 and incur no automatic failure; never average away a failed case.
All counted cases must use the same frozen candidate.
A genuine candidate failure ends that counted suite. Any authorized root-cause repair requires a new freeze and a complete restart from Case 1; prior artifact-profile or transport evidence cannot rescue a substantive compact-profile failure.

## Independent-fork sharing checklist

- Package version and Knowledge filenames match this release.
- Instructions boundary lines and counts were checked.
- All Preview cases were run and raw responses preserved.
- Every preserved response passed `check_compact_preview_response.py` with native exit 0 before manual scoring.
- No unsupported execution claim received a pass.
- Upload privacy language appears in the GPT's behavior.
- Builder profile, icon metadata if any, and public fields contain no personal identifiers.
- Sharing permission is **Can chat**; no settings or edit access is exposed publicly.

## Independent-fork GPT Store checklist

- Complete the current Builder Profile requirement using only the approved pseudonymous public identity.
- Recheck the current editor's category and capability labels; product labels and eligibility can change.
- Confirm applicable policy and workspace requirements.
- Confirm Apps and Actions remain absent.
- Review the final public name, description, starters, capabilities, and builder details before publishing.

## Official maintainer update procedure

Regenerate from the exact candidate source, validate it byte-for-byte, replace Instructions and every Knowledge file, freeze the compact candidate, and run all 12 declared Preview cases from the beginning. Verify the saved and public views and record exact binding evidence. A live service can remain available while a candidate binding or validation is pending; do not collapse those states or claim that the compact profile passed before this fresh gate completes.

## Privacy boundary

The browser Packet Builder can construct packets locally. Uploading source material to a Custom GPT sends that material through ChatGPT under the user's applicable terms and settings. This package provides no local-only guarantee inside ChatGPT, no secure intake service, and no certification.

## Official product references

- [Official BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor)
- [Creating and editing GPTs](https://help.openai.com/en/articles/8554397-creating-a-gpt)
- [Sharing and publishing GPTs](https://help.openai.com/en/articles/8798878)
- [Configuring actions in GPTs](https://help.openai.com/en/articles/9442513)
