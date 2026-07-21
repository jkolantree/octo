# Example Catalog

Examples are known-answer fixtures for the checker. They are not evidence that the represented scientific claims are true. Run them from the repository root with engine `0.3.0a2`.

| File | Command | Expected decision | Exit | Lesson |
|---|---|---:|---:|---|
| `claim_valid.json` | `audit` | `no_blocking_findings` | 0 | A structurally valid manifest can clear the checks it activates without receiving a universal truth verdict. |
| `claim_arithmetic_no_go.json` | `audit` | `demoted` | 1 | A finite-dimensional exact prime-comb claim triggers both its prospective fatal gate and the scoped no-go rule. |
| `complex_valid_transport.json` | `complex` | `no_blocking_findings` | 0 | The supplied finite differentials and transport commute exactly. |
| `complex_broken_transport.json` | `complex` | `blocked` | 1 | A nonzero certificate-interchange column gives a finite witness. |
| `observation_failure.json` | `observe` | `blocked` | 1 | A query distinguishes a pair joined by the declared observation relation. |
| `atomic_modulus_valid.json` | `atomic` | `no_blocking_findings` | 0 | Finite records are consistent with the declared modulus; the external uniform proof is not inferred. |
| `atomic_modulus_evasion.json` | `atomic` | `demoted` | 1 | A sample exceeds the declared concentration bound. |
| `defect_composition_valid.json` | `defect` | `no_blocking_findings` | 0 | The declared composite encloses the exactly propagated affine upper bound. |
| `defect_composition_understated.json` | `defect` | `demoted` | 1 | The declared composite understates at least one propagated upper-bound coordinate. |
| `null_conflicting_referenced.json` | `audit` | `blocked` | 1 | A declared pass cannot conceal referenced passing and failing evidence. |
| `null_omitted_bound_failure.json` | `audit` | `blocked` | 1 | A gate record cannot omit a failure that is bound to that gate. |
| `null_failed_proof.json` | `audit` | `blocked` | 1 | A failed formal-proof artifact cannot satisfy theorem support. |
| `null_missing_arithmetic_config.json` | `audit` | `prohibited` | 2 | An arithmetic-trace claim cannot activate an empty domain plugin. |
| `schema_atomic_missing_name.json` | `atomic` | `prohibited` | 2 | Runtime acceptance follows the released atomic schema. |
| `schema_complex_missing_fields.json` | `complex` | `prohibited` | 2 | Runtime acceptance follows the released complex schema. |
| `schema_observation_nonstring_state.json` | `observe` | `prohibited` | 2 | Runtime acceptance follows the released observation schema. |

Example command:

```bash
python run_audit.py observe examples/observation_failure.json
```

A nonzero exit is expected for blocking and demotion fixtures. CI should test the expected decision and exit code rather than treating every nonzero example as an installation failure.

## Interpretation rules

- `no_blocking_findings` means only that the relevant command found no blocking condition in the supplied object.
- The checker does not establish that a finite relation, matrix, evidence identifier, or model is a faithful description of the external world.
- Example hashes and evidence references must resolve before an example is presented as a complete preservation packet.
- Do not edit a negative fixture into a passing example; add a new fixture so the original failure remains reproducible.

Templates under `templates/` contain placeholders and are not completed audits.
