# Scientific and Operational Threat Model

This threat model covers erroneous scientific promotion, malformed artifacts, adversarial inputs, LLM use, and preservation failure. It is not a substitute for a security audit of Python or its host environment.

## Protected properties

The project aims to preserve:

- literal claim scope and version history;
- separation of exact, empirical, heuristic, analogous, and normative content;
- non-averaged fatal gates;
- evidence provenance and legal filtration;
- reproducible negative results and demotions;
- deterministic exact arithmetic for supported finite objects;
- an honest record separating model reasoning, web and citation checking, ChatGPT tools, versioned BSC Python, external proof tools, empirical tests, and proposed-only computations.

## Primary scientific threats

1. **False pass:** unsupported material receives a no-blocking decision because a relevant check was absent, bypassed, or underspecified.
2. **False block:** a valid claim is blocked because a gate is incorrectly scoped, mathematically wrong, or applied outside its domain.
3. **Placeholder evidence:** a name, path, DOI, proof identifier, hash-shaped string, or gate label is mistaken for verified evidence.
4. **Hidden quotient change:** an exact relation is replaced by numerical similarity or a different observation model after results are known.
5. **Local-to-global promotion:** local nondegeneracy, finite testing, or in-distribution fit is promoted without fiber, boundary, transport, or external validation.
6. **Leakage:** future outcomes, held-out labels, duplicate subjects, or post-hoc boundaries influence the evaluated candidate.
7. **Null mismatch:** candidates receive more parameters, search exposure, data, smoothness, or tuning than the declared null family.
8. **Soft rescue:** an aggregate score conceals a failed or conflicting fatal gate.
9. **Path suppression:** order- or route-dependent transport is reported as canonical.
10. **Limit evasion:** finite admissibility is used to hide a forbidden singularity or unbounded defect in a limit.
11. **Plugin bypass:** a relevant domain check is omitted because its activation fields were absent or mislabeled.
12. **Status inflation:** `structurally_checked` is presented as `proven`, `externally_replicated`, or safe to deploy.
13. **Equivalence-level confusion:** a strict representative defect is reported as a homology obstruction, or an observed-derived pass is promoted as unobserved equality.
14. **Semantic padding:** an ungrounded direct-sum basis changes homology while retaining the appearance of the original certificate model.
15. **Unlawful quotient:** a non-chain-map or nonsurjective projection is used to erase a path defect.
16. **Report promotion:** a preserved numerical or exact finite report is presented as independently regenerated or as a universal theorem.

## LLM-specific threats

- prompt injection embedded in a paper, source comment, website, or dataset;
- fabricated source coverage, citations, hashes, proof-assistant output, or command output;
- silent truncation of long documents;
- instructions to disclose secrets or retrieve unrelated private material;
- confident conversion of analogy into implication;
- output-schema drift that produces plausible but invalid artifacts;
- same-model repetition mistaken for independent review.
- ChatGPT Code Interpreter or Data Analysis presented as if the versioned BSC Python checker ran;
- an unsupported `Python passed`, `Lean verified it`, or `all tests passed` statement promoted without a bound execution record;
- public metadata implying that an unpublished Custom GPT, GPT Action, or hosted checker API exists.

The LLM packet treats target material as untrusted evidence, requires a coverage ledger, and forbids claims of execution without actual output. Users must still review generated artifacts.

## Product-surface boundaries

The three entry points do not share one privacy or execution boundary:

1. The public Custom GPT package prepares a direct ChatGPT audit experience, but the GPT is **UNPUBLISHED** until an authenticated human completes setup and Preview evaluation. Uploads are processed through ChatGPT under the user's applicable settings and terms. The first package contains no Action, hosted API, account, analytics, or cloud storage.
2. The browser Packet Builder constructs a versioned packet in browser memory without sending the target to an LLM. Sending its output to any model is a separate action governed by that service.
3. The repository and Python engine run versioned finite checks locally or in the operator's selected environment. A GPT response or ChatGPT tool result is not BSC Python output unless the correct checker actually ran and its result is bound to the inputs.

For mechanical activity, `ran` requires inspectable output or a bound receipt. A source-only success claim is `reported_but_unverified`; dependent gates remain `unrun` unless verified conflicting evidence requires `conflict`. Missing execution blocks or demotes the dependent conclusion without automatically refuting the research claim.

## Privacy and confidentiality threats

The repository contains no secure enclave or privacy guarantee. Do not place secrets or identifying, medical, legal, proprietary, classified, or export-controlled information in public issues, fixtures, LLM prompts, or release bundles. Hashes can still identify low-entropy private material. Synthetic data can still leak source records.

Sensitive vulnerability reports follow [SECURITY.md](../SECURITY.md). Scientific false-pass and false-block reports that contain no sensitive information may use the issue forms.

## Input and runtime threats

- malformed JSON, duplicate keys, or prohibited `NaN`/infinite values;
- resource exhaustion from huge matrices, graphs, nesting, or strings;
- malicious file paths or evidence references;
- unexpected internal exceptions misread as a passing audit;
- terminal or log injection through untrusted strings;
- unpinned build and release dependencies.
- flattened exact systems whose dimensions or intermediate rational growth exhaust resources;
- filesystem alternate streams, reparse points, or cloud transport metadata that are invisible to ordinary content hashes.

The CLI must return structured errors for declared input failures. An internal failure exits separately and never produces a pass.

## Non-goals for the current development line

The engine does not provide:

- automated theorem proving;
- verification of arbitrary external proofs or evidence;
- empirical truth adjudication;
- legal, moral, clinical, or safety authorization;
- certified interval arithmetic;
- a complete scientific ontology;
- construction of the unresolved infinite-dimensional arithmetic operator;
- derived-holonomy equivalence over arbitrary rings;
- proof that a semantic-basis meaning string faithfully represents the external world;
- independent regeneration of preserved reports whose original generators are absent;
- Lean, Coq, Isabelle, or other kernel verification of the new research notes;
- protection for secrets uploaded to external services;
- a published Custom GPT or public GPT URL before the authenticated human handoff is completed;
- a GPT Action, hosted BSC checker API, account system, analytics service, or cloud-storage service;
- the planned Audit Return Desk inspection and receipt layer;
- resistance to arbitrary local-code execution by a user who runs untrusted programs outside the checker.

## Required reporting discipline

Every audit report should disclose:

- engine and schema version;
- input hash;
- a per-activity execution ledger with status, scope, tool version, and receipt or an explicit statement that no receipt exists;
- source files and coverage;
- unresolved external evidence;
- findings and witnesses;
- exit code;
- responsible human reviewer;
- next demotion or review condition.

The strongest defense against overclaiming is a small, reproducible audit that another person can make fail.

The Audit Return Desk is the next planned trust-layer priority for checking returned model output and receipts. It is not implemented in this development line.
