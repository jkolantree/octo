# Machine-readable schemas

These Draft 2020-12 JSON Schemas describe the public `0.3` interchange
formats. The engine also applies semantic checks that JSON Schema cannot
express, including matrix shape compatibility, totality of query families,
exact chain equations, hash verification, and evidence-to-gate bindings.

| Command | Schema |
| --- | --- |
| `audit`, `lint` | `claim-manifest-v0.3.schema.json` |
| `complex` | `complex-v0.3.schema.json` |
| `observe` | `observation-v0.3.schema.json` |
| `atomic` | `atomic-modulus-v0.3.schema.json` |
| `defect` | `defect-v0.3.schema.json` |
| `adapter` | `adapter-receipt-v0.1.schema.json` |
| `holonomy` | `derived-holonomy-v0.1.schema.json` |

No external JSON Schema package is required at runtime. Producers can use any
Draft 2020-12 validator before invoking the engine, then rely on the engine for
the exact semantic layer.

The adapter-receipt format is an explicitly non-admissive preview. Passing its
structural and hash checks does not satisfy a theorem gate; see
[`docs/PROOF_CARRYING_ADAPTERS.md`](../docs/PROOF_CARRYING_ADAPTERS.md).

The derived-holonomy format is exact only over `field: "Q"`. JSON Schema checks
the closed record shape; the engine additionally checks semantic-basis digest
coverage, chain-map legality, path composition, projection surjectivity, and
the emitted rational primal or dual certificate. See
[`docs/DERIVED_HOLONOMY.md`](../docs/DERIVED_HOLONOMY.md).
