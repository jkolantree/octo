# Manifest and Schema Contract

The current research-preview manifest uses:

```json
"manifest_version": "0.4.0"
```

The machine-readable contract is [schemas/claim-manifest-v0.4.schema.json](../schemas/claim-manifest-v0.4.schema.json). Manifest `0.3.0` remains accepted for structural inspection under its immutable schema, but every attached result is nonsemantic until a registered replay recomputes it; legacy gate passes and maturity therefore fail closed. The schemas and linter are structural tools, not scientific truth certificates.

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

Research verdict, evidence maturity, execution status, deployment status, fatal-gate state, and any CLI decision are independent; see [STATUS_MODEL.md](STATUS_MODEL.md). The claim manifest records only the coordinates in its released contract. A separate execution ledger must not be fabricated as manifest evidence. In particular:

- `externally_replicated` requires a passing result recomputed by a registered independent-replication replay; no such replay is currently registered;
- manifest `0.4.0` admits theorem claims only through the closed `theorem_schema` / `q-polynomial-identity-v0.1` family, whose sole hard gate is `exact_polynomial_identity`, with an authoritative formal AST and a claim-bound exact certificate whose hash and replay share one bounded byte buffer and whose canonical residual is recomputed over `Q`;
- every evidence record outside a registered exact replay—including legacy manifest `0.3.0`, general theorem claims, audit reports, datasets, replications, and counterexamples—is provenance only; its declared `result` cannot decide a gate, raise maturity, trigger dependency propagation, or support promotion;
- an evidence record and matching artifact hash establish byte identity, never automatic validation of the artifact's mathematical, empirical, or scientific content;
- `admitted` is structurally representable only after all applicable fatal gates pass.

## Exact and approximate representation

An `exact_quotient` must supply an equivalence test and must not be inferred from numerical closeness. Approximate output-law similarity is generally nontransitive and belongs in a pseudometric, confusability graph, or identified set.

When a quotient is mathematically singular or not computably represented, preserve the relation, groupoid, or identified set rather than forcing a convenient quotient object.

## Closed theorem replay

[`theorem-certificate-v0.1.schema.json`](../schemas/theorem-certificate-v0.1.schema.json)
defines one decidable language: polynomial equality in `Q[x_1,...,x_n]`.
Terms contain only exact constants, declared variables, negation, addition,
multiplication, and bounded nonnegative integer powers. The checker expands the
two sides symbolically and compares the canonical sparse residual. It never
proves by finite sampling. Runtime ceilings include 256 AST nodes, depth 32,
arity 16, exponent 16, 4,096 normal-form monomials, 8,192-bit rational
intermediates, 50,000 counted coefficient operations, and a 1 MiB certificate;
one audit accepts at most 32 unique theorem artifact bindings and starts at
most 16 unique content-addressed theorem normalizations. Exceeding any ceiling
fails closed with `THEOREM_RESOURCE_LIMIT`.

The manifest's `claim.formal_statement` is authoritative. For this closed
profile, `claim.title` and `claim.statement` must equal the checker's
deterministic formal projections of that AST exactly, and `claim.scope` must
use the fixed formal-only boundary. Free-form theorem prose is non-admissible.
Maturity is limited to `structurally_checked`, deployment is limited to
`research_only` or `sandboxed`, and the replay explicitly reports that
scientific truth and deployment authority are not established. Certificate
claim ID, formal statement, artifact hash, declared residual, and evidence
result must all agree with the recomputation.
An empty residual is a pass. A valid nonempty residual is a countercertificate
and demotes the bound fatal gate. The language contains no division,
inequality, transcendental function, quantifier alternation, imported axiom, or
external-tool result.

## Dependency graphs

An optional claim dependency graph is acyclic and names a root claim. Failed or conflicting fatal gates propagate along declared dependency edges. This is a logical dependency filter, not an operator ideal or physical mechanism.

## Compatibility policy

Pre-1.0 schema versions may change incompatibly. A release must state the schema versions it accepts. Migration must preserve the original manifest, prior outputs, failures, and status history.

| Engine release | Manifest schema |
|---|---|
| `0.3.0a1` | `0.3.0` |
| `0.3.0a2` | `0.3.0` |
| `0.3.0a3` | `0.3.0`; derived holonomy `0.1.0` |
| `0.3.0a4` | `0.3.0`; derived holonomy `0.1.0`; research recovery `v1` |
| `0.3.0a5` | `0.3.0`; derived holonomy `0.1.0`; research recovery `v1`; Custom GPT release manifest `bsc-custom-gpt-release-manifest-v1` |
| `0.3.0a6` | `0.3.0`; derived holonomy `0.1.0`; research recovery `v1`; Custom GPT release manifest `bsc-custom-gpt-release-manifest-v1` |
| `0.3.0a7` | `0.3.0`; derived holonomy `0.1.0`; research recovery `v1`; Custom GPT release manifest `bsc-custom-gpt-release-manifest-v1` |
| `0.3.0a8` | prior formats plus non-admissive audit return `0.1.0` |
| `0.3.0a9` | same machine schemas as `0.3.0a8`; maintenance and compact-profile reconciliation only |
| `0.3.0a10` | same machine schemas as `0.3.0a9`; exact four-starter dispatch correction only |
| `0.3.0a11` | prior formats plus version-dispatched derived holonomy `0.2.0` with exact observation-kernel certificates |
| `0.3.0a12` | prior formats plus claim manifest `0.4.0` and theorem certificate `0.1.0` for closed exact-Q polynomial identities |
| `0.3.0a13` | same machine schemas and exact-Q theorem semantics as `0.3.0a12`; annotated-tag release-guard correction only |
| `0.3.0a14` | same released schemas; only registered exact replay may determine gates or maturity, and the closed theorem profile is bound to its canonical AST projection and formal-only authority |
| `0.3.0a16` | same released schemas; registered results are carried as subject-, evidence-, predicate-, scope-, method-, and authority-bound judgments, and unknown domain-check keys fail closed |
| `0.3.0a17` | same released schemas and engine algorithms as `0.3.0a16`; documentation rendering, status wording, generated projections, and documentation lint are corrected |

The independent derived-holonomy route dispatches `holonomy_version: 0.1.0`
records to the immutable
[`derived-holonomy-v0.1.schema.json`](../schemas/derived-holonomy-v0.1.schema.json)
and `0.2.0` records to
[`derived-holonomy-v0.2.schema.json`](../schemas/derived-holonomy-v0.2.schema.json).
The latter adds an exact-kernel observed-derived route. Keeping the schemas
closed prevents fields from one version being silently accepted by the other.
Neither route alters the strict square semantics of `complex-v0.3`.

Consumers must reject an unknown major or minor schema unless an explicit migration is applied.

The `v0.3.0-alpha.7` Custom GPT package did not enlarge the claim-manifest schema or the Python checker's authority. Its exact controller and Knowledge package completed the authenticated 27-case Preview gate recorded in [CUSTOM_GPT_STATUS.md](CUSTOM_GPT_STATUS.md). Uploads go through ChatGPT, and no GPT Action or hosted BSC API is included.

Alpha.8 added the separate closed [`audit-return-v0.1.schema.json`](../schemas/audit-return-v0.1.schema.json); alpha.17 preserves it unchanged under the independently versioned alpha.13 protocol component. It describes a draft, non-admissive returned-audit envelope and does not enlarge the claim-manifest schema or grant the checker truth, proof, citation, execution-authentication, evidence-admission, or deployment authority. See [AUDIT_RETURN_DESK.md](AUDIT_RETURN_DESK.md).
