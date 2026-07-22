# GPT setup, Preview, and publishing handoff

**Repository publication status:** `UNPUBLISHED`. No public Custom GPT URL is asserted here.

## Exact GPT Builder setup

1. On ChatGPT web, open `https://chatgpt.com/gpts`, select **Create**, then use the direct configuration view.
2. Copy the Name, Description, and category recommendation from `GPT_PUBLIC_METADATA.md`.
3. Paste all of `GPT_INSTRUCTIONS.md` into Instructions. Confirm both boundary lines are present and that the complete file remains 7987 characters and 7987 UTF-8 bytes before pasting; the Builder limit is 8000 characters.
4. Upload these Knowledge files in this exact order:
   1. `BSC_PROTOCOL.md` — 19608 bytes — SHA-256 `c7e8528fc4b11b935e28bd47ae7f9644cdfe1a66eddac6fba83aa1d9eed3dd7a` — Canonical normative protocol
   2. `BSC_STATUS_AND_EVIDENCE_MODEL.md` — 7249 bytes — SHA-256 `ff572f7e218966ac71b9786ee4e8185800d3c7af6811fa2d5ccc4cd1aec37a2d` — Research, evidence, gate, execution, deployment, and CLI status boundaries
   3. `BSC_EXECUTION_AND_RECEIPTS.md` — 13289 bytes — SHA-256 `92ff94a05eecd011c78f5ec18bd7b3a6675220ad83a165fb2370afaf724a3577` — Execution ledger and proof-adapter trust boundaries
   4. `BSC_SUPPORTED_CHECKS.md` — 27586 bytes — SHA-256 `e616d7c283ecc7f17a4264e6d29be0faaabe9b56658d06d6e959d3c89c2662e2` — Implemented Python routes, schemas, findings, and limitations
   5. `BSC_WORKED_EXAMPLES.md` — 29214 bytes — SHA-256 `a9b5c11075952721480daa4b295d27a9f524d34cf2216b440c351ff03b396d3a` — Known-answer and adversarial examples without redefining the protocol
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
