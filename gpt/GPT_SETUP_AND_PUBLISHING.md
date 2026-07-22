# GPT setup, Preview, and publishing handoff

**Repository publication status:** `UNPUBLISHED`. No public Custom GPT URL is asserted here.

## Exact GPT Builder setup

1. On ChatGPT web, open `https://chatgpt.com/gpts`, select **Create**, then use the direct configuration view.
2. Copy the Name, Description, and category recommendation from `GPT_PUBLIC_METADATA.md`.
3. Paste all of `GPT_INSTRUCTIONS.md` into Instructions. Confirm both boundary lines are present and that the declared body counts remain 8320 characters and 8322 UTF-8 bytes before pasting.
4. Upload these Knowledge files in this exact order:
   1. `BSC_PROTOCOL.md` — 19608 bytes — SHA-256 `ac03a1dfd04305377c75724ec5e42b9a7ef8bc8147b6c4dd3701872a04b2f9d2` — Canonical normative protocol
   2. `BSC_STATUS_AND_EVIDENCE_MODEL.md` — 7249 bytes — SHA-256 `ced650484684ccb1ea6ffa96c8afcf0013ef0a0d63a49cca7f6ac3fa30af9ad6` — Research, evidence, gate, execution, deployment, and CLI status boundaries
   3. `BSC_EXECUTION_AND_RECEIPTS.md` — 13289 bytes — SHA-256 `bfdeb6a332bd5b5873ae7cdc611c239a5ee4af97f420a827c880027d64a8c3f7` — Execution ledger and proof-adapter trust boundaries
   4. `BSC_SUPPORTED_CHECKS.md` — 27532 bytes — SHA-256 `dc771d1dd6d9b119a2ee402f4305dfe29b5c45885654a2b5430f48877349c313` — Implemented Python routes, schemas, findings, and limitations
   5. `BSC_WORKED_EXAMPLES.md` — 29214 bytes — SHA-256 `5141dd962f29a522af5f2ae7654c2ac0a47a365e3b79c18d79d244cb687e6547` — Known-answer and adversarial examples without redefining the protocol
5. Enable **Web search** and **Code Interpreter & Data Analysis**. Leave Image Generation off. Leave Canvas off unless deliberately needed. Add no Apps and no Actions.
6. Copy the four prompts from `GPT_CONVERSATION_STARTERS.md` into Conversation starters.
7. Test in Preview before creating or sharing. Knowledge hashes verify the files before upload only; ChatGPT does not expose a byte-identical internal index for independent hashing.
8. Create the GPT privately first. After the evaluation gate passes, choose **Anyone with the link** for beta or **GPT Store** for public listing if the account and workspace are eligible.
9. Verify the public preview shows only the approved pseudonym and intended metadata. Copy the resulting GPT URL and return it for a follow-up documentation update.

## Required Preview gate

Run the complete `evals/GPT_EVAL_CASES.jsonl` set using fresh conversations and score it with `evals/GPT_MANUAL_SCORECARD.md`. At minimum, manually inspect:

- the known-true and known-false cases;
- every declared paired mutation;
- prompt injection;
- missing execution;
- conflicting evidence;
- the poisoned `all tests passed` case, which must remain unverified and never green.

A score of at least 18/20 is recommended, but any automatic failure blocks sharing regardless of score.

## Link-sharing beta checklist

- Package version and Knowledge filenames match this release.
- Instructions boundary lines and counts were checked.
- All Preview cases were run and raw responses preserved.
- No unsupported execution claim received a pass.
- Upload privacy language appears in the GPT's behavior.
- Builder profile, icon metadata if any, and public fields contain no personal identifiers.
- Sharing permission is **Can chat**; no settings or edit access is exposed publicly.

## GPT Store checklist

- Complete the current Builder Profile requirement using only the approved pseudonymous public identity.
- Recheck the current editor's category and capability labels; product labels and eligibility can change.
- Confirm applicable policy and workspace requirements.
- Confirm Apps and Actions remain absent.
- Review the final public name, description, starters, capabilities, and builder details before publishing.

## Post-publication update procedure

Regenerate this package from the new tagged repository source, validate it byte-for-byte, replace Instructions and all Knowledge files, rerun the full Preview gate, select **Update**, verify the live GPT, and record the returned URL in a separate repository change. Never silently mix files from different BSC versions.

## Privacy boundary

The browser Packet Builder can construct packets locally. Uploading source material to a Custom GPT sends that material through ChatGPT under the user's applicable terms and settings. This package provides no local-only guarantee inside ChatGPT, no secure intake service, and no certification.

## Official product references

- [Creating and editing GPTs](https://help.openai.com/en/articles/8554397-creating-a-gpt)
- [Sharing and publishing GPTs](https://help.openai.com/en/articles/8798878)
- [Configuring actions in GPTs](https://help.openai.com/en/articles/9442513)
