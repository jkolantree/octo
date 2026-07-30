# Status Model

BSC keeps truth assessment, evidence maturity, execution status, deployment authority, gate results, and checker decisions separate. Combining them into one badge would erase important failure modes.

## Typed conclusion boundary

Every registered replay conclusion records its exact subject and subject hash,
predicate, scope, method, evidence identity and evidence hash, authority, and
result. A consumer must match every coordinate. Shared labels such as `pass`,
`verified`, and `proven` do not transfer product correctness, artifact
identity, actual execution, harness validity, transport behavior, external
truth, or deployment authority. Unknown domain-check keys fail closed rather
than being silently treated as checked.

## 1. Research verdict

A research verdict is assigned by accountable human review of the claim and its evidence.

| Verdict | Meaning |
|---|---|
| `proven` | A mathematical claim has a complete proof or independently checkable exact certificate with no unresolved dependency. |
| `strongly_supported` | An empirical claim survives substantial declared testing and independent evidence, but is not a universal proof. |
| `plausible_but_unresolved` | The claim is coherent and not refuted, but essential obligations remain. |
| `refuted` | A valid counterexample, contradiction, or decisive prospective falsifier applies. |
| `ill_posed` | Required objects, domains, comparisons, or limits are not sufficiently defined to have the stated truth value. |
| `outside_current_knowledge` | The claim is precise, but no decisive proof, refutation, or accessible test is presently known. |

The CLI does not assign this verdict.

## 2. Evidence maturity

The manifest field `claim.evidence_maturity` records workflow maturity:

- `declared`
- `structurally_checked`
- `empirically_passed`
- `externally_replicated`

These states require progressively stronger attached records, but presence is not authenticity. A string naming a proof, dataset, or replication is not itself verification of that artifact. Likewise, a matching local SHA-256 proves which bytes were inspected, not that those bytes contain a valid result. No declared evidence result affects maturity unless a registered exact replay recomputes that result.

Manifest `0.5.0` has two closed profiles:

- a claim-bound `q-polynomial-identity-v0.1` certificate can support
  `structurally_checked` after exact replay of the authoritative AST and
  residual;
- a claim-bound `finite-census-affine-bound-v0.1` certificate can support
  `empirically_passed` after exact complete-frame and interval-bound replay,
  but only for the conditional observational proposition and four identified
  external premises carried by that profile.

The census profile does not establish its premise hashes, causation,
generalization beyond its exact frame, independent replication, or deployment
authority. No independent-replication replay is registered, so
`externally_replicated` remains blocked. General theorem prose, external-tool
receipts, older manifests, and every other artifact remain non-admissible as
results.

## 3. Execution status

Execution status records what actually ran. It does not record whether a research claim is true or whether an executed check was sufficient.

| Status | Meaning |
|---|---|
| `not_run` | The activity did not execute. |
| `file_read_only` | ChatGPT Data Analysis opened or inventoried a file but did not perform a mathematical, BSC Python, formal-tool, or empirical verification. This status is valid only for that file-access boundary. |
| `ran` | The activity executed and its relevant output is available for inspection. |
| `reported_but_unverified` | A source asserts that the activity ran, but no adequate execution record or receipt is available. |
| `not_applicable` | The activity is irrelevant to the audited claim; this is not a substitute for `not_run`. |

Every audit execution ledger records these activities separately:

- model reasoning over supplied material;
- web search;
- independent opening and checking of cited sources;
- ChatGPT Code Interpreter or Data Analysis;
- the versioned BSC Python checker;
- an external theorem prover, proof assistant, SMT solver, interval tool, or other adapter;
- an empirical experiment or measurement;
- a computation proposed or described but not run.

Each entry records its status, scope and inputs, tool and version when known, result relied upon, and receipt, transcript, citation, or output identifier. If no record is available, the ledger states that absence and why; a mechanical activity without an adequate bound record cannot receive `ran`. Model reasoning is not mechanical execution. ChatGPT tool execution is not a BSC checker run. A submitted adapter receipt is a provenance object and is not external proof-tool verification unless the declared execution and replay were independently established.

Claims such as `Python passed`, `Lean verified it`, or `all tests passed` without adequate bound records are false-pass risks. Assign `reported_but_unverified`, do not promote evidence maturity, and leave dependent gates `unrun` unless verified conflicting evidence requires `conflict`. This demotes the unsupported execution claim; it does not automatically refute the underlying research claim.

## 4. Deployment status

The manifest separately records:

- `research_only`
- `sandboxed`
- `candidate`
- `admitted`
- `retired`

Only an accountable organization can authorize real deployment. The engine can prohibit a manifest from representing itself as admitted when required gates are unresolved; it cannot grant legal, moral, clinical, or operational permission.

## 5. Gate state

Each applicable fatal gate has one state:

- `unrun` - no adequate result exists;
- `pass` - the declared obligation passed with referenced evidence;
- `fail` - a prospective failure condition fired;
- `conflict` - incompatible verified conclusions coexist, including a decisive result mixed with an inconclusive bound record.

Admission requires every applicable fatal gate to be exactly `pass`, with that
state recomputed by a registered exact replay. Hash-verified but unreplayed
records—including negative records—remain attached and visible as provenance
while the gate computes to `unrun`. Their declared conclusion is non-admissible
until a registered replay establishes it, so even a declared failure cannot
trigger dependency propagation by assertion alone. Conflict is preserved and
blocked when registered replays produce incompatible results, never averaged.

The checker derives this coordinate from the complete set of evidence records bound to the gate. A manifest cannot hide a bound failure by omitting its identifier from the gate record, and a submitted state that disagrees with the derived state is blocked.

## 6. CLI decision

The CLI summarizes findings with one mechanical decision:

| Decision | Meaning |
|---|---|
| `no_blocking_findings` | Selected checks produced no blocking finding. |
| `no_blocking_findings_with_warnings` | No blocking finding, but warnings require review. |
| `blocked` | A required obligation is unresolved. |
| `demoted` | A prospective demotion condition fired. |
| `prohibited` | The input is malformed or violates a hard prohibition. |
| `internal_error` | The checker failed unexpectedly; no scientific result was produced. |

These outcomes describe only the checks actually executed. A trustworthy report also lists checks not run.

## 7. Source-coverage state

Source coverage is recorded separately from evidence maturity and execution. Each supplied or expected source receives exactly one state:

- `fully_inspected`
- `partially_inspected`
- `unreadable`
- `missing`
- `possibly_truncated`

The ledger also names the source version, inspected ranges, omissions, access mode, and execution mode. Inspecting every available byte does not justify `fully_inspected` when the object may be truncated. Sampling requires `partially_inspected` with the unreviewed remainder identified.

## 8. Audit Return Desk outcome

The Return Desk adds a separate returned-envelope consistency coordinate:

| Browser outcome | Python mapping | Meaning |
|---|---|---|
| `consistent` | `no_blocking_findings` | Implemented return checks found no blocking inconsistency or unavailable declared byte. |
| `needs_review` | `no_blocking_findings_with_warnings` | No blocking inconsistency was established, but a byte, source, receipt, or execution claim remains unavailable or unverified. |
| `blocked` | `blocked`, or `prohibited` for malformed/schema-invalid input | The return is stale, malformed, contradictory, unsupported, or integrity-failing. |

This outcome is non-admissive. It does not assign or validate the research verdict and does not establish truth, proof, citation authenticity, external execution, or deployment authority.

## 9. Exit codes

- `0`: no blocking finding, with or without warnings;
- `1`: blocked or demoted;
- `2`: malformed input or command usage;
- `70`: `internal_error`, an unexpected engine failure.

Automation should inspect both the exit code and structured JSON. It should never translate exit code `0` into “scientifically true” or “BSC compliant.”

## 10. External and live binding

A successful finite holonomy audit emits
`HOLONOMY_EXTERNAL_INTERPRETATION_NON_ADMISSIBLE`. Its witness records that the
algebra covers the submitted finite maps while source authenticity and
scientific truth remain `not_established`.

A successful finite-census replay has a different, narrower authority. It
establishes the exact affine-bound proposition over the declared finite frame
and measurement enclosures, conditional on the four hash-identified external
premises. Its witness keeps premise identity, exact execution, evidence bytes,
observational scope, causal non-authority, population non-generalization, and
deployment non-authority separate. It never emits an unrestricted
`scientific_truth` bit.

The live Custom GPT's indexed Knowledge state is
`NON_ADMISSIBLE_UNHASHABLE`. Saved-editor fields, filenames, public rendering,
and behavior can be observed, but ChatGPT does not expose independently
retrievable indexed Knowledge bytes. Those observations therefore cannot
satisfy an engine gate, theorem replay, or scientific admission. Repository
package hashes remain valid for the repository bytes separately.

## Separation rule

Research verdict, evidence maturity, execution status, deployment status, gate state, CLI decision, source coverage, Return Desk outcome, and live binding answer different questions. None may be inferred from another. In particular:

- a coherent or proven claim does not imply that a proposed execution ran;
- a finite check that ran does not prove a broader theory;
- a gate pass does not grant deployment authority;
- a CLI decision reports only implemented checks on the declared input;
- model confidence is not any BSC status.
