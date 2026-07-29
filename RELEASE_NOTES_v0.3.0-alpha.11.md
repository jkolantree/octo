# BSC Audit Engine v0.3.0-alpha.11

Released 2026-07-28 as a public research prerelease.

## Exact observation kernels

Alpha.11 adds `holonomy_version: 0.2.0` and the
`observed_derived_exact_kernel` relation. For declared chain maps
`i: N -> D` and `pi: D -> O`, the engine replays over the exact rational
field:

```text
rank(i_n) = dim(N_n)
rank(pi_n) = dim(O_n)
pi_n i_n = 0
dim(N_n) + dim(O_n) = dim(D_n)
```

These conditions prove `image(i_n) = ker(pi_n)` degree by degree. A projection
can no longer erase an unnamed extra direction while satisfying this stronger
route. The positive fixture records the short-exact-sequence certificate; the
negative over-quotient fixture exits `2` with
`OBSERVATION_KERNEL_SEQUENCE_FAIL`.

Runtime schema validation dispatches v0.1 and v0.2 documents to separate closed
contracts. New fields cannot be smuggled into a v0.1 record and silently
ignored. Within v0.2, exact-kernel fields are legal only on the exact-kernel
mode, so a document cannot carry stronger-looking declarations while selecting
a weaker unchecked mode. The immutable v0.1 schema and its narrower legacy
meaning remain available.

## Proof bytes are not proof semantics

The claim-manifest route no longer treats a hash-matched file labeled
`proof`, `formal_proof`, or `exact_certificate` as semantic theorem replay.
For theorem and theorem-schema claims, hash-only proof evidence leaves the
gate `unrun`, blocks theorem promotion, and reports the evidence IDs as
provenance only. This closes a concrete false pass in which arbitrary proof
prose with the correct file hash could support an unrelated false universal.

No admissive supervised theorem-replay contract is claimed in this release.
The proof-carrying adapter remains explicitly non-admissive.

## Product and release boundary

The official Custom GPT remains on its separately verified alpha.10 live
state. Alpha.11 regenerates the repository package because its mathematical
Knowledge projection changed, but that package is an unvalidated update
candidate: it is not installed in the live GPT, and no alpha.11 Preview result
or byte-identical indexed Knowledge binding is claimed.

The alpha.10, alpha.9, and alpha.8 tags, releases, assets, and historical
negative evidence remain unchanged. This release does not modify
`jkolantree/BSC`, publish to PyPI or Zenodo, add an Action, or restart the
retired 39-case browser campaign.

## Verification boundary

Release assets are built reproducibly from the exact clean tagged commit and
bind their commit, tree, tag, toolchain, sizes, and SHA-256 values in
`RELEASE_MANIFEST.json` and `SHA256SUMS`. Exact finite algebra does not establish
that the declared null subcomplex is scientifically correct, and a clean audit
does not establish an arbitrary theory, empirical claim, or deployment.
