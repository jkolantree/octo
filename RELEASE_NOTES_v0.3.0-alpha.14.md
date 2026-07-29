# BSC Audit Engine v0.3.0-alpha.14

Released 2026-07-29 as a public research prerelease.

## One exact mapping-complex kernel

Chain-map legality and chain homotopy now compile through the same graded
mapping-complex differential over `Q`,

`(delta_r phi)_n = d_D phi_n - (-1)^r phi_(n-1) d_C`.

The implementation tests `delta_(r-1) delta_r = 0`, degree-zero agreement with
the prior transport defect, degree-one agreement with every preserved
holonomy system, rational basis-change invariance, gapped complexes, forged
certificates, and resource limits. The public holonomy schemas are unchanged.

For an inconsistent exact linear system, the decisive certificate is the dual
obstruction `y` satisfying `y^T A = 0` and `y^T b != 0`. Replaying that witness
no longer depends on a later coordinate-dependent least-squares calculation.
Historical decisions, finding-code order, dual witnesses, and pairings are
preserved; non-authoritative residual-magnitude diagnostics are no longer
emitted on failure.

## Replay-only manifest authority

Matching an artifact SHA-256 now establishes provenance, not the truth of its
declared `result`. A gate, maturity state, admission decision, conflict, or
dependency demotion may use only a result recomputed by a registered exact
replay. Hash-matched generic and empirical records therefore compute their
gates as `unrun` and cannot promote themselves by saying `pass`.

The closed polynomial profile is additionally bound to:

- one deterministic formal title and human-readable statement projection of
  the authoritative AST;
- a fixed formal-only scope;
- `structurally_checked` evidence maturity;
- `research_only` or `sandboxed` deployment.

The replay witness states the exact canonical formula, its formal-only
authority, `scientific_truth=not_established`, and
`deployment_authority=not_granted`. Permanent regressions cover both a generic
empirical false pass and a valid polynomial certificate relabeled as a
universal medical claim with fabricated replication and admission status.
Arithmetic-trace obligation bindings now consume the same internal registered
replay ledger; a hash-matched artifact relabeled `pass` cannot certify an
infinite-dimensional construction.

## Independent component identity

A strict, package-owned component contract now binds the public protocol,
exact theorem kernel, and Audit Return Desk schema independently of the
distribution version. Release assembly records those component identities
without rewriting them.

The canonical protocol packet is byte-identical to its
`0.3.0-alpha.13` component:

`3615c6d81e2c297e68a6ee798fe1a34aa4014a75e0670580ec002c28a933fd1a`

The alpha.14 engine and repository package may therefore evolve without
pretending that unchanged protocol bytes acquired a new semantic identity.

## One verification spine

Local checks, CI, Pages, and clean-tag release assembly now invoke explicit
profiles from one fail-fast verification entry point. The three-Python-version matrix runs
the Python core, while one patch-pinned integration job owns browser,
localization, package, privacy, and release-integrity checks. Distribution
reproducibility, wheel installation, source-distribution replay, exact tag
binding, the closed 17-file release directory, keyless attestations, and
pre/post-publication redownload comparisons remain required.

Release source files are read from the exact tagged Git objects rather than
dereferenced workspace paths. Tracked symbolic links are rejected, and a
second tracked-tree check after all gates prevents a generator from changing
bytes after the original commit/tree identity was recorded.

## Preserved boundary

The live Custom GPT remains the separately observed alpha.10 interface. No
live Update or Preview campaign is part of this release. Indexed Knowledge
bytes remain `NON_ADMISSIBLE_UNHASHABLE`. Alpha.13 and all earlier tags,
releases, assets, failures, and historical evidence remain unchanged. This
release does not modify `jkolantree/BSC`, publish to PyPI or Zenodo, or restart
the retired 39-case browser campaign.
