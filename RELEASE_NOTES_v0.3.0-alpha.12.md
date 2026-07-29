# BSC Audit Engine v0.3.0-alpha.12

Released 2026-07-29 as a public research prerelease.

## Exact semantic theorem replay

Alpha.12 adds the closed `q-polynomial-identity-v0.1` kernel. It parses a
bounded formal AST over the exact field `Q`, symbolically normalizes both sides
to canonical sparse polynomials, and compares `left - right` without sampling
or floating-point arithmetic.

Claim manifest `0.4.0` makes that formal AST authoritative. The fixed
`exact_polynomial_identity` gate of a `theorem_schema` claim may use an
`exact_certificate` only when:

- the local certificate bytes match their declared SHA-256;
- that SHA-256 is recomputed from the same bounded byte buffer that is parsed
  and replayed;
- the certificate claim ID and formal statement exactly match the manifest;
- the declared canonical residual equals the engine's recomputed residual;
- the evidence result equals the computed `pass` or `fail`.

The bundled positive control proves
`(x + y)^2 = x^2 + 2xy + y^2` in `Q[x,y]`. Permanent adversarial tests reject a
forged zero residual, a swapped claim or statement, undeclared variables,
noncanonical rationals, unsupported operators, and resource-limit attacks. A
valid nonzero residual is a countercertificate and demotes the affected fatal
gate. The runtime also fails closed before exceeding 50,000 counted exact
coefficient operations, preventing compact exponent trees from hiding
unbounded normalization work. Within one audit, repeated evidence aliases share
one artifact verification and one replay for the same immutable
path/hash/claim/statement binding; exact-certificate verification uses the same
1 MiB ceiling as replay. A single audit admits at most 32 unique theorem
artifact bindings and starts at most 16 unique content-addressed theorem
normalizations.

Manifest `0.3.0` remains available with its historical meaning: hash-bound
proof-like files do not become semantic theorem evidence. General theorem
prose, proof-assistant receipts, and scientific declarations are also outside
the new closed kernel.

## Declared algebra is not external truth

Every otherwise successful holonomy audit now emits
`HOLONOMY_EXTERNAL_INTERPRETATION_NON_ADMISSIBLE`. Its machine witness fixes
the algebraic scope at the submitted finite maps and records both scientific
truth and source authenticity as `not_established`. The exact calculations are
unchanged; the new finding prevents a clean algebraic result from being
laundered into a scientific claim.

The live Custom GPT remains the separately observed alpha.10 interface. Because
ChatGPT does not expose independently retrievable indexed Knowledge bytes, its
binding state is now `NON_ADMISSIBLE_UNHASHABLE`. Editor fields, filenames,
public behavior, and Preview smokes remain useful product observations, but
they cannot satisfy engine gates or theorem replay. No live GPT update is part
of this release.

## Keyless release provenance

The new exact-tag workflow:

1. requires an annotated prerelease tag at the exact current `origin/main`;
2. runs the existing clean-tag build and complete release gates;
3. verifies the closed 17-file manifest, ledger, commit, tree, and tag;
4. creates one signed Sigstore-backed GitHub attestation over all 17 files;
5. verifies that attestation before creating a draft release;
6. redownloads and byte-compares every draft asset before publication; and
7. repeats byte and attestation verification after publication.

The attestations authenticate released bytes and their repository/workflow
provenance. They do not establish mathematical meaning, scientific truth, or
source authenticity.

## Preserved history

Alpha.11 and all earlier tags, releases, assets, and negative evidence remain
unchanged. This release does not modify `jkolantree/BSC`, publish to PyPI or
Zenodo, update the live GPT, or restart the retired 39-case browser campaign.
