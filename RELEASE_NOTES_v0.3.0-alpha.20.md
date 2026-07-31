# BSC Audit Engine v0.3.0-alpha.20

Alpha.20 adds one bounded bridge from the separately published Boundary-State
Calculus v1.2.0 simulation profile into octo's existing affine-defect kernel.
It introduces no general simulation validator, new schema, CLI semantics, or
live Custom GPT change.

## What changed

- The release binds BSC v1.2.0 commit
  `5fdcb3e1de15b04ed037da135717d316e45f28b1`, tree
  `7328eee577c7595c5381e129c62d5c0b1fe78e30`, version DOI
  `10.5281/zenodo.21711341`, paper SHA-256
  `106631826fc417549d68927418759b856e5610c7c0c27ab53c33665994a60b8c`,
  and the exact simulation-profile, F10-input, and F10-receipt hashes.
- Two valid `defect-v0.3` examples project the ten Host A and Host B stages
  through `AffineDefect.then`.
- Permanent regressions recompute every rational prefix. Host A ends at
  `1023/51200`, leaving `1537/51200` below tolerance. Host B remains below
  tolerance at step 6, crosses first at step 7 by `217031/100000000`, and
  ends above tolerance by `1513215599/100000000000`.
- A typed crosswalk record preserves
  `violation_basis = exact_actual_error_above_tolerance`.
- Documentation distinguishes BSC's admission inequality from a stricter octo
  policy that reserves explicit positive `gamma` headroom.

## Typed authority boundary

- **Product correctness:** the kernel definition and exact-arithmetic
  regression design compose the supplied rational affine bounds; a result from
  running them requires a separately identified execution receipt.
- **Artifact identity:** the crosswalk binds the exact published upstream
  source slice and receipt identities.
- **Actual execution:** these static notes assert no fresh octo execution
  receipt. The separately identified BSC receipt records the upstream exact
  state paths.
- **Harness validity:** when run, octo tests recompute every prefix and
  comparison. They do not replace the upstream F10 checker, schema, or negative
  mutants, and their validity is independent of any product result.
- **Transport behavior:** repository and release checks bind source and
  package bytes; they do not establish live indexed-Knowledge identity.
- **External truth:** F10 proves only the declared exact finite fixture
  disposition. It establishes no accuracy for an untested simulator,
  operating region, coupling, horizon, or physical system.
- **Deployment authority:** not granted.

## Preserved state

- All schemas and CLI behavior remain unchanged.
- The public protocol component remains byte-identical to
  `0.3.0-alpha.13`.
- The official Custom GPT remains the separately observed alpha.10 live state;
  no editor, Instructions, Knowledge, starter, capability, App, Action, or
  Preview change is part of this release.
- Indexed live Knowledge remains `NON_ADMISSIBLE_UNHASHABLE`.
- `v0.3.0-alpha.19` and every earlier tag, release, asset, and negative result
  remain unchanged.
- The separate `jkolantree/BSC` research repository is not mutated.
