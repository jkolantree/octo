# Governance

## Scope

This document governs the BSC Audit Engine repository. It does not create scientific, legal, clinical, institutional, or moral authority outside the project.

The project is maintained under the identity **J. Tree**. The maintainer manages releases, repository access, and final merges. Contributors and reviewers remain responsible for the claims and evidence they submit.

## Principles

1. Scope before authority.
2. Exact witnesses before aggregate impressions.
3. Hard gates remain noncompensating.
4. Negative results and prior statuses remain visible.
5. Ordinary methods and baselines retain priority in their domains.
6. Conflicts are recorded, not averaged.
7. Affected users may contest a false pass or false block.
8. No maintainer status converts a claim into scientific truth.

BSC is offered as infrastructure for careful imagination. It permits ambition, but not free authority.

## Change classes

### Routine

Documentation corrections, accessibility improvements, and tests that do not change public semantics may be merged after maintainer review.

### Behavioral

Changes to output, exit codes, schemas, canonicalization, arithmetic, or public interfaces require tests, changelog entry, and compatibility review.

### Scientific gate

Any new fatal gate or scope expansion requires:

- a written gate proposal;
- activation criteria based on typed fields;
- mathematical or methodological justification;
- positive, negative, and ordinary-baseline fixtures;
- false-pass and false-block analysis;
- minimal witness and repair language;
- prospective retirement condition;
- independent domain review.

If independent review is unavailable, the gate may be merged only as explicitly experimental and must not control `admitted` status by default.

## Decisions and disagreement

The maintainer records the decision and rationale in the pull request or issue. Substantive unresolved disagreement is preserved in the record. A contributor may request reconsideration with a counterexample, new evidence, or a narrower formulation.

No vote can override a mathematical counterexample. No authority claim can replace missing evidence.

## False-pass and false-block appeals

- A **false pass** report alleges that the engine returned no blocking finding despite a violated supported obligation.
- A **false block** report alleges that a gate rejected a claim outside the gate’s valid scope or on incorrect mathematics.

Both receive a minimal reproducer, stable issue label, responsible owner, and resolution in a patch release when public semantics are affected. Prior outputs are not silently rewritten; release notes state the invalidated range.

## Releases

- Pre-1.0 releases may change incompatibly but must publish schema compatibility and migration notes.
- Tags are immutable once shared publicly.
- Release artifacts include hashes and known limitations.
- A security or scientific false-pass repair receives a new release rather than a moved tag.
- Archived negative fixtures remain available unless law or privacy requires removal; the removal and reason are documented without exposing protected material.

## Succession

A future maintainer should preserve repository history, licenses, schemas, known failures, release hashes, and the power to demote prior claims. Transfer of repository control does not transfer authorship or scientific endorsement automatically.
