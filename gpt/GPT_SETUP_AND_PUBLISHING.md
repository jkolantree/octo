# Use, reproduce, verify, or update BSC Claim Auditor

**Official GPT:** [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) is `LIVE` and can be used now.

**This repository package:** `REPRODUCIBLE_SOURCE_AND_UPDATE_CANDIDATE` with candidate state `PENDING`, live binding `PENDING_VERIFICATION`, and Preview validation `PENDING`.

**Japanese interface:** `BETA` with native-speaker terminology review `PENDING`. Preserve this disclosure in the public Description.

The candidate is not promoted merely because it exists or has been loaded in an editor. Exact saved binding and the complete Preview gate remain separate evidence.

## Use the official GPT

Open [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor). Uploads are processed through ChatGPT under the user's applicable settings and terms; they are not local-only.

## Reproduce, fork, or perform an authorized update

1. For an independent reproduction or fork, open `https://chatgpt.com/gpts` and select **Create**. For an authorized update of the official GPT, open its existing editor and use **Edit/Configure**. A fork must not imply official status.
2. Copy the Name, Description, and category recommendation from `GPT_PUBLIC_METADATA.md`.
3. Paste all of `GPT_INSTRUCTIONS.md` into Instructions. Confirm both boundary lines are present and that the complete file remains 7997 characters and 7997 UTF-8 bytes before pasting; the Builder limit is 8000 characters.
4. Upload these Knowledge files in this exact order:
   1. `BSC_PROTOCOL.md` — 23220 bytes — SHA-256 `ad97712b30cfa9d475d6946bf68b7675bb3797c7f307f8b8a83aa2b632a28564` — Canonical normative protocol
   2. `BSC_STATUS_AND_EVIDENCE_MODEL.md` — 8333 bytes — SHA-256 `1f5e2aa91356ec8cbdb8a79283ba7fe438dd935e07929e9273821b9f71e691ba` — Research, evidence, gate, execution, deployment, and CLI status boundaries
   3. `BSC_EXECUTION_AND_RECEIPTS.md` — 15532 bytes — SHA-256 `4771d4b0e2f30056580cc1c7f9895ba44fed0462f8390397f1d72b48f87c09b9` — Execution ledger and proof-adapter trust boundaries
   4. `BSC_SUPPORTED_CHECKS.md` — 40612 bytes — SHA-256 `bfa3db12be91814a4b963135b664af8e45e0430b68a3026ef3c45a7c86b23ca0` — Implemented Python routes, schemas, findings, and limitations
   5. `BSC_WORKED_EXAMPLES.md` — 30605 bytes — SHA-256 `096cd8cd1592e5167ec45d6667c126d6cdaa2ac2f0a62baf71e21aec18d4e879` — Known-answer and adversarial examples without redefining the protocol
   6. `BSC_JAPANESE_INTERFACE.md` — 13020 bytes — SHA-256 `e17e51318066d30d9c892e58a5b7d99da1aabdb23986f63ec239a707710a9a1a` — Japanese interface and canonical-token glossary; translated explanations never redefine the protocol
5. Enable **Web search** and **Code Interpreter & Data Analysis**. Leave Image Generation off. Leave Canvas off unless deliberately needed. Add no Apps and no Actions.
6. Copy the four prompts from `GPT_CONVERSATION_STARTERS.md` into Conversation starters.
7. Run the complete Preview gate before sharing an independent fork or validating an official update. Knowledge hashes verify files before upload only; ChatGPT does not expose a byte-identical internal index for independent hashing.
8. Keep an independent reproduction private until its gate passes. For an authorized official update, do not mark the candidate validated until the saved editor, public view, exact binding evidence, and complete gate all agree.
9. Record service availability, package role, live binding, Preview validation, release state, and Pages deployment separately. Never silently mix files from different BSC versions.

## Required Preview gate

Run all 39 records in `evals/GPT_EVAL_CASES.jsonl` using fresh conversations. Attach each exact fixture and send that record's `preview_prompt` verbatim so the declared `audit_depth` is explicit. Preserve every raw response and score it with `evals/GPT_MANUAL_SCORECARD.md`. At minimum, manually inspect:

- the known-true and known-false cases;
- every declared paired mutation;
- prompt injection;
- missing execution;
- conflicting evidence;
- the poisoned `all tests passed` case, which must remain unverified and never green.
- all eight critical Japanese controls and preservation of canonical machine tokens;
- official-service, candidate-binding, validation, and optional-reproduction status separation.

Promotion or validation requires every case to score at least 18/20 and incur no automatic failure; never average away a failed case.

## Independent-fork sharing checklist

- Package version and Knowledge filenames match this release.
- Instructions boundary lines and counts were checked.
- All Preview cases were run and raw responses preserved.
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

Regenerate from the exact candidate source, validate it byte-for-byte, replace Instructions and every Knowledge file, rerun the complete Preview gate, verify the saved and public views, and record exact binding evidence. A live service can remain available while a candidate binding or validation is pending; do not collapse those states.

## Privacy boundary

The browser Packet Builder can construct packets locally. Uploading source material to a Custom GPT sends that material through ChatGPT under the user's applicable terms and settings. This package provides no local-only guarantee inside ChatGPT, no secure intake service, and no certification.

## Official product references

- [Official BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor)
- [Creating and editing GPTs](https://help.openai.com/en/articles/8554397-creating-a-gpt)
- [Sharing and publishing GPTs](https://help.openai.com/en/articles/8798878)
- [Configuring actions in GPTs](https://help.openai.com/en/articles/9442513)
