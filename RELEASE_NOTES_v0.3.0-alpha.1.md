# BSC Audit Engine v0.3.0-alpha.1

This release is a public research preview. It exposes the exact structural kernel to adversarial use while narrowing what a successful run is allowed to mean.

## Trust model

A no-blocking CLI result means only that the selected checks emitted no blocking finding for the supplied finite artifact. It does not certify an arbitrary theory, external proof, empirical replication, or deployment decision.

Research verdict, evidence maturity, deployment status, fatal-gate state, and CLI decision are now documented as separate coordinates.

## Release additions

- machine-readable manifest schema `0.3.0`;
- engine version `0.3.0a1` and `--version` route;
- structured JSON for malformed, duplicate-key, non-finite, and missing input;
- explicit exit codes for clear, blocked, malformed, and internal-failure outcomes;
- documentation index and worked usage route;
- source-coverage ledger for document audits;
- LLM prompt-injection and privacy boundary;
- governance, security, conduct, contribution, and issue-triage policies;
- accessible offline Start Here page;
- catalog of expected example outcomes.
- explicit `checks.run` and `checks.not_run` ledgers in structured output;
- resource ceilings for hostile or accidentally enormous inputs;
- reproducible wheel and source builds, conformance fixtures, an SPDX SBOM, and SHA-256 release checksums.

## Verification performed

- 58 deterministic source tests pass locally;
- the wheel installs and runs in an isolated environment without network access;
- the extracted source distribution passes the complete suite;
- repeated frozen-epoch builds produce byte-identical wheels and source archives;
- all documented examples match their expected decision and exit code;
- malformed, duplicate-key, non-finite, missing, and internal-failure routes return structured JSON;
- local documentation links, citation version, full license text, offline HTML accessibility invariants, and the research-note digest pass release checks;
- `SHA256SUMS`, `RELEASE_MANIFEST.json`, an SPDX SBOM, and a conformance bundle are generated from the final source tree.

CI repeats the supported Python-version matrix after publication. Artifact signing
is not asserted by this preview; the release manifest records that fact explicitly.

## Known boundaries

- LLM audits are drafts and may be incomplete or wrong.
- Local evidence artifacts are path-confined and hash-checked; their external scientific semantics are not automatically authenticated.
- Finite observation and transport checks establish only the declared finite obligation.
- The atomic command checks record consistency, not an external analytic proof.
- Arithmetic operator realization remains unresolved and blocked at the declared proof obligations.

BSC is offered as infrastructure for careful imagination. It permits ambition, but not free authority.
