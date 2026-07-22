# BSC Audit Engine v0.3.0-alpha.6

Released 2026-07-21 as a public research preview.

## Corrected Builder controller

Alpha.6 repairs the alpha.5 Custom GPT handoff after the authenticated Builder exposed an 8,000-character Instructions limit. The alpha.5 generated file could not be pasted in full. The replacement is generated deterministically from the same normative profile and is 7,987 characters and 7,987 UTF-8 bytes.

The compact rendering preserves, verbatim:

- all 29 fatal rule texts;
- all nine required rule texts;
- the four canonical depth IDs;
- the ten-section output titles and order;
- the exact five-file Knowledge boundary;
- fail-closed missing-Knowledge behavior;
- separate ChatGPT, BSC Python, formal-tool, adapter, empirical, and proposed-only execution status;
- the Custom GPT upload privacy boundary.

The controller includes the normative profile SHA-256. Generation and package validation now fail if the complete controller exceeds 8,000 characters or if a reviewed rule text is absent or duplicated. Setup documentation reports complete-file character and byte counts rather than an unpasteable body-count wrapper.

## Live-candidate and Preview status

A link-shared [BSC Claim Auditor candidate](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) was observed through the authenticated owner account. Its name, description, four starters, five Knowledge filenames, enabled Web Search and Data Analysis capabilities, disabled Image Generation, absent Action, default-model setting, and link visibility were inspected.

Four targeted alpha.5 cases were inspected in fresh conversations: known-true induction, known-false continuity, the square-root domain baseline, and the removed-domain mutation. Their decisive expected behaviors were observed. This is not the complete 27-case scorecard. The live candidate remains unverified for alpha.6 until its controller and Knowledge files are replaced and every Preview case passes without an automatic failure.

Repository status therefore remains `UNPUBLISHED` for a fully Preview-validated GPT configuration. The live URL is a research-preview candidate, not proof authority or certification.

## Integrity and authority boundary

Alpha.6 does not add a GPT Action, hosted API, account integration, analytics, cloud storage, proof engine, or deployment authority. ChatGPT uploads are processed under the user's applicable terms and settings and are not local-only. Repository hashes bind the pre-upload package bytes; they do not authenticate ChatGPT's internal Knowledge index or the behavior of a future model revision.

The Python engine's finite check scope and manifest schemas are unchanged. A clean structural result, GPT response, hash match, or receipt does not establish external scientific truth, independent replication, theorem-prover execution, or safe deployment.

## Required authenticated update

1. Paste the exact alpha.6 `GPT_INSTRUCTIONS.md`.
2. Replace all five Knowledge files with the alpha.6 package files in order.
3. Recheck capabilities, starters, public identity, and sharing permission.
4. Run all 27 cases in fresh conversations and preserve the raw responses.
5. Require at least 18/20 and no automatic failure for every case.

The Audit Return Desk remains planned and is not implemented in alpha.6.
