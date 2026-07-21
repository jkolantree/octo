# BSC Audit Engine v0.3.0-alpha.3

This feature prerelease adds exact finite derived-holonomy auditing, non-admissive proof-adapter receipts, and fail-closed pseudonymous-publication controls. It remains a research preview: its certificates establish only the declared finite equations and bindings that the engine checks.

## Exact derived holonomy

- The new `holonomy` route compares arbitrary presented paths strictly, up to chain homotopy, or after an explicit observation projection over bounded finite-dimensional complexes over `Q`.
- Every complex and transport edge is checked before a derived class is constructed. Observed-derived comparisons additionally require a chain-map, degreewise-surjective projection.
- Semantic basis records are content-addressed. Their hashes bind the finite coordinates to declared meanings without certifying those meanings externally.
- Passing derived relations carry replayable exact rational homotopies. Failures carry dual obstructions when available, together with exact least-squares residual data.
- Strict defects remain visible when a weaker derived or observed-derived relation passes. Resource ceilings bound path length, matrix dimensions, rational growth, and the flattened solve.

## Proof-adapter boundary

- Versioned Lean 4, SMT-LIB 2, and interval receipt schemas check finite structure, hashes, result consistency, replay declarations, and assumption policy.
- Receipts are explicitly non-admissive. This release does not execute a theorem prover, SMT solver, or interval backend, and no receipt field can confer theorem authority.
- Adversarial fixtures preserve path-escape, substitution, inconsistent-result, unverified-pass, and authority-escalation failures.

## Research packet and provenance

- Two supplied research notes and three JSON reports are preserved under `research/derived-witnessed-descent/` with a complete local digest ledger and path-free provenance record.
- The repository checker verifies strict JSON shape, content hashes, and selected exact internal invariants. It does not reconstruct the three absent source generators or turn numerical corroboration into proof.
- The bounded-jet orthogonal-prime-block obstruction remains separate from the unresolved operator-realization and absolute-continuity obligations.

## Privacy and release integrity

- The privacy gate scans tracked text, document metadata, archives, release assets, and protected Git history against a machine-readable pseudonymous identity policy.
- Operational branch tips and the alpha.2 publication erratum remain preserved as auditable records.
- Release builds require a clean, exactly tagged tree and locked Python `3.12.13` with setuptools `82.0.1`; reproducible distributions are built twice and compared byte for byte.
- Artifact signatures are not performed. The release manifest and checksum ledger record this limitation explicitly.

## Compatibility and limits

Engine `0.3.0a3` continues to accept manifest schema `0.3.0` and adds derived-holonomy schema `0.1.0`. Alpha.2 remains immutable and available for comparison.

The engine does not validate arbitrary scientific truth, reconstruct missing generators, certify an infinite-dimensional operator, prove the Riemann hypothesis, or authorize clinical, legal, safety, policy, or deployment decisions.
