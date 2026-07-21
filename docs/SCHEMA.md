# Manifest and Schema Contract

The v0.3 research-preview manifest uses:

```json
"manifest_version": "0.3.0"
```

The machine-readable contract is [schemas/claim-manifest-v0.3.schema.json](../schemas/claim-manifest-v0.3.schema.json). The schema and linter are structural tools, not truth certificates.

## Required sections

1. `claim` - stable identity, type, exact statement, scope, evidence maturity, and deployment state.
2. `system` - domain, boundary, typed states, controls, context, outputs, and local kernel.
3. `observation` - instrument or kernel, calibration, uncertainty, sampling, and legal filtration.
4. `representation` - exact quotient, approximate confusability, or another declared representation convention.
5. `target` - outcome, horizon, population or apparatus, action set, and loss.
6. `experiment` - intervention, ordinary baseline, candidate family, matched nulls, frozen splits, and search budget.
7. `admission` - ordered hard gates and evidence-backed gate coordinates.
8. `demotion` - owner, prospective triggers, status transition, and negative-result archive.
9. `preservation` - hashes, test vectors, failures, migration plan, and review date.

Optional domain objects and dependency graphs must satisfy their own scoped contracts.

## Drafts and placeholders

Templates are starting material. Placeholder strings such as `replace-me`, `unassigned`, and placeholder proof identifiers are not evidence. A draft must not be described as structurally checked or admitted. Before review:

- replace every placeholder;
- reset unjustified gate passes to `unrun`;
- verify that evidence identifiers resolve to preserved artifacts;
- compute real hashes over the named files or canonical JSON;
- state which fields remain assumptions.

## Status transitions

Evidence maturity and deployment are independent; see [STATUS_MODEL.md](STATUS_MODEL.md). In particular:

- `externally_replicated` requires a declared independent-replication record;
- theorem claims require a proof, formal-proof, or exact-certificate record;
- an evidence record is a reference, not automatic validation of its content;
- `admitted` is structurally representable only after all applicable fatal gates pass.

## Exact and approximate representation

An `exact_quotient` must supply an equivalence test and must not be inferred from numerical closeness. Approximate output-law similarity is generally nontransitive and belongs in a pseudometric, confusability graph, or identified set.

When a quotient is mathematically singular or not computably represented, preserve the relation, groupoid, or identified set rather than forcing a convenient quotient object.

## Dependency graphs

An optional claim dependency graph is acyclic and names a root claim. Failed or conflicting fatal gates propagate along declared dependency edges. This is a logical dependency filter, not an operator ideal or physical mechanism.

## Compatibility policy

Pre-1.0 schema versions may change incompatibly. A release must state the schema versions it accepts. Migration must preserve the original manifest, prior outputs, failures, and status history.

| Engine release | Manifest schema |
|---|---|
| `0.3.0a1` | `0.3.0` |
| `0.3.0a2` | `0.3.0` |
| `0.3.0a3` | `0.3.0`; derived holonomy `0.1.0` |

The independent derived-holonomy route is governed by
[`derived-holonomy-v0.1.schema.json`](../schemas/derived-holonomy-v0.1.schema.json).
It does not alter the strict square semantics of `complex-v0.3`.

Consumers must reject an unknown major or minor schema unless an explicit migration is applied.
