# BSC Audit Engine v0.3.0-alpha.2

This patch release repairs demonstrated false-pass paths in `0.3.0-alpha.1`. It remains a research preview and does not convert structural checking into scientific truth verification.

## Security and scientific-integrity corrections

- Gate state is computed from every evidence record bound to the gate. A manifest cannot omit a bound failure or declare a pass over conflicting evidence.
- Theorem and theorem-schema support requires a hash-verified, passing proof-kind artifact explicitly bound to the claim.
- Evidence-maturity transitions require verified passing artifacts of an appropriate kind.
- Arithmetic-trace claims fail closed when typed domain configuration is absent or unsupported.
- The output ledger records checks that actually executed. Early termination leaves downstream checks in `checks.not_run`.
- Every command validates its released JSON Schema before semantic checking.

## Adversarial regression packet

The Null-Discrimination suite freezes a valid control and fatal mutations for:

1. referenced pass/fail conflict;
2. omitted bound failure;
3. failed proof presented as theorem support;
4. missing arithmetic-trace configuration;
5. prior schema/runtime disagreements;
6. semantic short-circuit ledger accuracy.

The suite is run by `python scripts/run_null_discrimination.py` and by the ordinary unit-test command.

## Release provenance

- Release builds require a clean Git worktree and exact tag `v0.3.0-alpha.2`.
- `RELEASE_MANIFEST.json` records the Git commit, Git tree, tag, locked toolchain hash, and excluded separately licensed files.
- Python `3.12.13` and setuptools `82.0.1` are the locked release toolchain.
- A container digest is not asserted by this release and is recorded as such.
- GitHub Actions supports pull requests, pushes, and manual `workflow_dispatch` execution.

## Licensing

Code, schemas, templates, and software documentation remain Apache-2.0. The `Audit_Descent_Calculus` PDF and its DOCX source are CC BY 4.0 and are excluded from Python distributions and the Apache-labelled software release bundle.

## Compatibility

Engine `0.3.0a2` continues to accept manifest schema `0.3.0`, with stricter enforcement of the already published contract. Prior alpha.1 artifacts remain preserved but must be rerun before being cited as clear under alpha.2.

BSC is offered as infrastructure for careful imagination. It permits ambition, but not free authority.
