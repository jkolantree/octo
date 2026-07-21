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
- an honest record of checks run and not run.

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

## LLM-specific threats

- prompt injection embedded in a paper, source comment, website, or dataset;
- fabricated source coverage, citations, hashes, proof-assistant output, or command output;
- silent truncation of long documents;
- instructions to disclose secrets or retrieve unrelated private material;
- confident conversion of analogy into implication;
- output-schema drift that produces plausible but invalid artifacts;
- same-model repetition mistaken for independent review.

The LLM packet treats target material as untrusted evidence, requires a coverage ledger, and forbids claims of execution without actual output. Users must still review generated artifacts.

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

The CLI must return structured errors for declared input failures. An internal failure exits separately and never produces a pass.

## Non-goals for v0.3.0-alpha.1

The engine does not provide:

- automated theorem proving;
- verification of arbitrary external proofs or evidence;
- empirical truth adjudication;
- legal, moral, clinical, or safety authorization;
- certified interval arithmetic;
- a complete scientific ontology;
- construction of the unresolved infinite-dimensional arithmetic operator;
- protection for secrets uploaded to external services;
- resistance to arbitrary local-code execution by a user who runs untrusted programs outside the checker.

## Required reporting discipline

Every audit report should disclose:

- engine and schema version;
- input hash;
- checks run and not run;
- source files and coverage;
- unresolved external evidence;
- findings and witnesses;
- exit code;
- responsible human reviewer;
- next demotion or review condition.

The strongest defense against overclaiming is a small, reproducible audit that another person can make fail.
