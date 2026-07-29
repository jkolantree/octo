# Machine-readable schemas

These Draft 2020-12 JSON Schemas describe the public `0.3` interchange
formats. The engine also applies semantic checks that JSON Schema cannot
express, including matrix shape compatibility, totality of query families,
exact chain equations, hash verification, and evidence-to-gate bindings.

| Command | Schema |
| --- | --- |
| `audit`, `lint` | version-dispatched: `claim-manifest-v0.3.schema.json` or `claim-manifest-v0.4.schema.json` |
| `complex` | `complex-v0.3.schema.json` |
| `observe` | `observation-v0.3.schema.json` |
| `atomic` | `atomic-modulus-v0.3.schema.json` |
| `defect` | `defect-v0.3.schema.json` |
| `adapter` | `adapter-receipt-v0.1.schema.json` |
| `holonomy` | version-dispatched: `derived-holonomy-v0.1.schema.json` or `derived-holonomy-v0.2.schema.json` |
| `theorem` | `theorem-certificate-v0.1.schema.json` |
| `return-desk` | `audit-return-v0.1.schema.json` |

No external JSON Schema package is required at runtime. Producers can use any
Draft 2020-12 validator before invoking the engine, then rely on the engine for
the exact semantic layer.

The adapter-receipt format is an explicitly non-admissive preview. Passing its
structural and hash checks does not satisfy a theorem gate; see
[`docs/PROOF_CARRYING_ADAPTERS.md`](../docs/PROOF_CARRYING_ADAPTERS.md).

The theorem-certificate format is admissible only for its closed exact-Q
polynomial-identity language and only when claim manifest `0.4.0` binds the
same authoritative formal statement to the fixed `exact_polynomial_identity`
hard gate. The engine hashes, parses, and replays one bounded byte buffer and
symbolically recomputes the canonical residual; it does not rely on
evaluations, free-form proof prose, or an asserted result. Manifest `0.3.0`
keeps its historical non-admissive theorem semantics.

The audit-return format is also explicitly non-admissive. Its closed schema
defines a draft returned-audit envelope; the Python and browser semantic layers
add protocol/hash binding, portable filename rules, claim-scoped gate
recomputation, execution/input/output/receipt binding, high-verdict source-byte
requirements, and deployment-overreach checks. Internal consistency does not
establish truth, proof, citation authenticity, independent execution, evidence
admissibility, or deployment authority. See
[`docs/AUDIT_RETURN_DESK.md`](../docs/AUDIT_RETURN_DESK.md).

The derived-holonomy format is exact only over `field: "Q"`. JSON Schema checks
the closed record shape; the engine additionally checks semantic-basis digest
coverage, chain-map legality, path composition, projection surjectivity, and
the emitted rational primal or dual certificate. The v0.2 exact-kernel route
also certifies a degreewise short exact sequence for the declared null
subcomplex and observation quotient. See
[`docs/DERIVED_HOLONOMY.md`](../docs/DERIVED_HOLONOMY.md).
Every otherwise successful holonomy result carries an explicit
`HOLONOMY_EXTERNAL_INTERPRETATION_NON_ADMISSIBLE` warning: exact algebra on the
submitted maps does not authenticate their source or establish scientific
truth.
