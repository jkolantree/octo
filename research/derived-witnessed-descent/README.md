# Derived witnessed descent research packet

This directory preserves two research notes and three machine-readable reports supplied for the next BSC development step. The imported source bytes are unchanged, but they were materialized as fresh regular files so filesystem transport metadata is not published.

## What entered the executable framework

The `holonomy` command implements the finite exact core over the rational field `Q`:

1. validate content-addressed semantic bases;
2. verify every edge is a chain map;
3. compare arbitrary presented paths strictly;
4. solve the chain-homotopy equation exactly;
5. emit a rational homotopy on success or a dual obstruction on failure;
6. optionally repeat the comparison after a lawful, degreewise-surjective observation projection;
7. report an exact squared least-squares residual `eta_squared`.

See [Derived holonomy](../../docs/DERIVED_HOLONOMY.md), the [schema](../../schemas/derived-holonomy-v0.1.schema.json), and the [known-answer examples](../../examples/README.md).

## Evidence boundary

| Artifact | Classification |
|---|---|
| Derived-holonomy engine tests and emitted certificates | Independently executable exact checks in this repository |
| Imported derived-holonomy report | Exact mechanical record; internally checked, but its original generator was not supplied |
| Imported shifted-ladder report | Exact finite identity claims plus high-precision numerical corroboration; original generator not supplied |
| Imported prime-block report | Exact finite jet records plus double-precision cutoff corroboration; original generator not supplied |
| Universal mathematical statements in the notes | Constructive paper proofs requiring mathematical review |
| Lean, Coq, or Isabelle certification | Not performed |
| Historical novelty | Unresolved |

The supplied partial checksum record names three generator scripts that were not present. Therefore the imported reports are preserved as non-admissive research fixtures, not represented as independently regenerated evidence. The repository checker validates their hashes, strict JSON shape, and selected internal invariants without executing or reconstructing absent code.

The later [constructive proof and obstruction note](Formal_Verification_and_Prime_Block_Obstruction.md) supersedes the earlier note's conditional status for the bounded-jet orthogonal-prime-block theorem. It does not construct a prime-local self-adjoint operator, prove the Riemann hypothesis, or settle the stated escape routes.

## Integrity and provenance

- `DIGESTS.sha256` is the authoritative complete ledger for this directory, excluding the ledger itself.
- `PROVENANCE.json` records intake status and checks without host paths, source URLs, timestamps, or personal identifiers.
- `verification/SOURCE_SHA256SUMS.partial.sha256` is preserved only as the supplied partial record.
- `verification/SOURCE_README.md` is preserved for context; its reproduction commands cannot be completed because the named generators are absent.
- `ERRATA.md` records non-destructive clarifications.

The research material is governed by [CC BY 4.0](../LICENSE). Code, schemas, tests, and software documentation remain Apache-2.0.
