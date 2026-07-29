# BSC Audit Engine v0.3.0-alpha.16

Alpha.16 carries the alpha.15 typed-coherence candidate forward under a new
immutable identity and repairs the cross-platform release-order defect that
blocked alpha.15 before publication.

## What changed

- Exact linear certificates are strict variants. A primal certificate carries
  an exact solution, recomputed zero residual, and recomputed squared norm. A
  dual certificate carries only an annihilator and recomputed nonzero pairing.
  Contradictory and wrong-variant fields are rejected.
- Registered replay results are checked judgments whose subject, subject hash,
  predicate, scope, method, evidence identity and hash, authority, and result
  must all match the consuming obligation.
- Unknown domain-check keys now fail explicitly.
- The release manifest is projected from a deterministic pre-manifest receipt
  of the exact local stages it names. It does not manufacture finer-grained
  pass claims from one aggregate command. The final closed-directory privacy
  scan is a separate, non-self-referential gate.
- Release completeness is defined by semantic artifact roles, not a magic file
  count. The byte-identical `bsc-audit-complete.zip` alias is removed; the
  versioned tracked-source archive remains.
- Every release-artifact sequence and checksum ledger uses explicit UTF-8
  filename-byte order, independent of host filesystem case-order semantics.
- A Windows-path positive regression and a correctly rehashed case-fold-order
  negative make the cross-platform ordering boundary permanent.
- CI reuses its primary distribution build as reproducibility side A and keeps
  one independent build B. Wheel installation, source-distribution replay,
  browser runtime, privacy, Pages, package, and exact-tag release checks remain.

Direct Python consumers must migrate with the authority boundary: the
non-authoritative `least_squares_solution` field is removed,
`LinearCertificate.to_json(...)` now requires the exact matrix and right-hand
side for replay, caller-supplied replay/cache mappings are removed, and audit
cache state is private to one engine audit. These interfaces are intentionally
not shimmed because accepting caller-constructed authority would reopen the
defect.

The current release directory contains fourteen role-bearing artifacts plus
`RELEASE_MANIFEST.json` and `SHA256SUMS`. That count is descriptive only; the
checker derives completeness from the exact role-to-filename contract.

## Authority boundary

Each receipt judgment identifies its exact candidate commit, tree, and tag;
predicate; stage-specific scope; method; evidence-record digest; authority;
and result. Those judgments establish only the declared local execution or
artifact property. Publication policy, keyless GitHub attestations, transport
redownload comparison, external scientific truth, and deployment authority
remain separate. After manifest and checksum creation, the builder scans the
complete closed directory separately; that later scan is not retroactively
represented inside the receipt it inspects.

The exact finite algebra verifies the supplied maps and certificates, not the
scientific truth or completeness of their declarations. The closed polynomial
replay remains the only admissible theorem family. General theorem prose,
external-tool receipts, empirical declarations, and indexed live Knowledge
remain non-admissive to engine gates unless a separately registered replay
exists.

## Preserved state

- The failed local `v0.3.0-alpha.15` annotated tag remains fixed; it was never
  pushed and has no GitHub release or assets.
- The public protocol component remains byte-identical to
  `0.3.0-alpha.13`.
- The official Custom GPT remains the separately observed alpha.10 live state.
  No live Instructions, live Knowledge, starter, capability, App, Action,
  owner-editor, or live Preview change is part of this release.
- Indexed live Knowledge bytes remain `NON_ADMISSIBLE_UNHASHABLE`.
- Alpha.14 and every earlier public tag, release, asset, and preserved negative
  result remain unchanged.
- `jkolantree/BSC` remains a separate research repository and was not mutated.

## Deferred

The next mathematical increment is a closed degree-two route that either
produces `Q` with `delta_2 Q = H - K` for two explicitly bound homotopies, or
produces a dual obstruction. It is intentionally not exposed in alpha.16 and
is scheduled no earlier than alpha.17.
