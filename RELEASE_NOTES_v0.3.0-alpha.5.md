# BSC Audit Engine v0.3.0-alpha.5

Released 2026-07-21 as a public research preview.

## What this release adds

Alpha.5 adds a deterministic, repository-backed Custom GPT configuration and evaluation package. Its strong controlling Instructions and five ordered Knowledge files are generated from canonical repository sources. The GPT and the accessible, local-only Pages Packet Builder use the same four audit depths and the same beginner-first output order, reducing drift between the two interfaces.

The package includes 27 serious Preview evaluation cases. They cover known-true and known-false controls, paired mutations, prompt injection, missing or inflated execution claims, conflicting evidence, non-admissive proof receipts, structural failures, and a poisoned `all tests passed` false pass that must remain unverified and must never receive a green result.

Package validation is fail closed. Repository checks bind generated files through a release manifest and SHA-256 records, reject malformed JSONL, detect stale outputs and incomplete source coverage, and forbid GPT Actions or a server-side verification API in this release. These checks establish repository artifact integrity; they do not expose or authenticate ChatGPT's internal Knowledge index.

## Publication and privacy status

The repository contains the setup package, not a published GPT. No public GPT URL, completed Builder Preview, link-sharing state, or GPT Store listing is claimed. A human must configure the Builder, upload the five Knowledge files, run and preserve all 27 Preview evaluations, and review the public identity before sharing.

The Custom GPT is not local-only. Material uploaded to it is processed through ChatGPT under the user's applicable terms, workspace controls, and settings. Users should not upload sensitive, proprietary, identifying, medical, legal, classified, export-controlled, or otherwise restricted material without appropriate authorization and review. The Pages Packet Builder remains the local-only preparation route; its privacy property does not extend to ChatGPT uploads.

No GPT Action, BSC verification API, account integration, analytics, or cloud-storage component is included.

## Exact execution and authority boundaries

- **GPT reasoning:** The GPT can read supplied material and draft an audit. Retrieving Instructions or Knowledge does not execute repository code, prove a theorem, validate a citation, or independently replicate a result.
- **ChatGPT tools:** Web search and Code Interpreter or Data Analysis, if actually used, must be recorded as separate ChatGPT execution. They are not automatically versioned BSC Python execution.
- **BSC Python:** A BSC checker result may be claimed only when the identified versioned Python engine actually runs against identified inputs and its output is preserved. A `no_blocking_findings` decision means only that no implemented blocking condition fired within the declared scope.
- **External tools:** Lean, SMT, interval arithmetic, empirical experiments, and other external systems require their own supervised execution, pinned tool identity, transcripts or certificates, exact input binding, and admissibility review. Submitted adapter receipts remain non-admissive provenance unless that workflow occurred.
- **Deployment:** Neither a GPT draft, a hash match, a passing finite check, nor an external receipt grants scientific truth, independent replication, or clinical, legal, policy, safety, or deployment certification.

## Known limitations

- The GPT can misunderstand sources, miss counterexamples, reconstruct a claim incorrectly, overlook relevant evidence, or produce malformed draft records.
- Long or inaccessible material may be only partially inspected; coverage must be disclosed and cannot be inferred from a fluent summary.
- Manifest and SHA-256 checks bind repository bytes and detect stale generated assets, but hashes do not establish anonymity, truth, provenance outside the repository, or byte-identical internal indexing after upload.
- The 27-case suite is a human Preview gate, not proof of behavior for every prompt or future model revision.
- The Custom GPT has not been published by this release and no live-service availability is asserted.

## Next trust-layer priority

The Audit Return Desk is the next planned layer for receiving and validating returned audit artifacts. It is not implemented in alpha.5.
