# Status Model

BSC keeps truth assessment, evidence maturity, deployment authority, gate results, and checker decisions separate. Combining them into one badge would erase important failure modes.

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

These states require progressively stronger attached records, but presence is not authenticity. A string naming a proof, dataset, or replication is not itself verification of that artifact.

## 3. Deployment status

The manifest separately records:

- `research_only`
- `sandboxed`
- `candidate`
- `admitted`
- `retired`

Only an accountable organization can authorize real deployment. The engine can prohibit a manifest from representing itself as admitted when required gates are unresolved; it cannot grant legal, moral, clinical, or operational permission.

## 4. Gate state

Each applicable fatal gate has one state:

- `unrun` - no adequate result exists;
- `pass` - the declared obligation passed with referenced evidence;
- `fail` - a prospective failure condition fired;
- `conflict` - incompatible verified conclusions coexist, including a decisive result mixed with an inconclusive bound record.

Admission requires every applicable fatal gate to be exactly `pass`. Conflict is preserved and blocked, never averaged.

The checker derives this coordinate from the complete set of evidence records bound to the gate. A manifest cannot hide a bound failure by omitting its identifier from the gate record, and a submitted state that disagrees with the derived state is blocked.

## 5. CLI decision

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

## 6. Exit codes

- `0`: no blocking finding, with or without warnings;
- `1`: blocked or demoted;
- `2`: malformed input or command usage;
- `70`: `internal_error`, an unexpected engine failure.

Automation should inspect both the exit code and structured JSON. It should never translate exit code `0` into “scientifically true” or “BSC compliant.”
