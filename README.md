# BSC Audit Engine

Research-preview software for making mathematical and scientific claims easier to inspect, challenge, reproduce, and demote.

**Current release:** `v0.3.0-alpha.3`<br>
**Development version:** `0.3.0a4.dev0`<br>
**Project status:** experimental; suitable for research audits and known-answer tests, not for unattended scientific, clinical, legal, safety, or policy decisions.

BSC is offered as infrastructure for careful imagination. It permits ambition, but not free authority.

## What it does

The engine checks a narrow set of declared structural obligations. Current routes include:

- manifest and hard-gate linting;
- exact rational matrix and chain-complex checks;
- certificate-interchange defects and finite witnesses;
- square holonomy and path-dependence checks;
- arbitrary-path strict, derived, and observed-derived holonomy over exact rationals;
- replayable chain-homotopy or dual-obstruction certificates with exact residuals;
- finite observation/query descent witnesses;
- product-valued gates with non-averaged conflict states;
- fatal dependency propagation in acyclic claim graphs;
- finite atomic-modulus record checks;
- exact propagation of declared affine upper bounds;
- scoped arithmetic-trace and local/global recovery gates;
- non-admissive, hash-bound Lean/SMT/interval adapter receipts;
- canonical JSON hashing.

The engine does **not** determine whether an arbitrary theory is true, reconstruct an arbitrary proof, validate an external evidence identifier, certify empirical replication, or grant moral, legal, clinical, or deployment permission. A `no_blocking_findings` result means only that the checks actually run found no blocking condition.

## Choose an entry point

- **First visit:** [START_HERE.md](START_HERE.md) or the accessible offline [START_HERE.html](START_HERE.html)
- **Human-only audit:** [AUDIT_WORKSHEET.md](AUDIT_WORKSHEET.md)
- **LLM-assisted draft:** [BSC_AUDIT_LLM_PACKET.md](BSC_AUDIT_LLM_PACKET.md)
- **Programmer route:** [docs/PROGRAMMER_TUTORIAL.md](docs/PROGRAMMER_TUTORIAL.md)
- **Documentation map:** [docs/index.md](docs/index.md)
- **Example catalog:** [examples/README.md](examples/README.md)
- **Mathematical definitions:** [docs/MATHEMATICS.md](docs/MATHEMATICS.md)
- **Derived holonomy:** [docs/DERIVED_HOLONOMY.md](docs/DERIVED_HOLONOMY.md)
- **Spectral obstruction boundary:** [docs/SPECTRAL_OBSTRUCTIONS.md](docs/SPECTRAL_OBSTRUCTIONS.md)
- **New research packet:** [research/derived-witnessed-descent/README.md](research/derived-witnessed-descent/README.md)
- **Proof adapter boundary:** [docs/PROOF_CARRYING_ADAPTERS.md](docs/PROOF_CARRYING_ADAPTERS.md)
- **Pseudonymous publication policy:** [PRIVACY.md](PRIVACY.md)
- **Published corrections:** [ERRATA.md](ERRATA.md)

## Thirty-second example

Run a known descent failure without installing the package:

```bash
python run_audit.py --version
python run_audit.py observe examples/observation_failure.json
```

The example declares two states that the observation relation identifies and a query that gives them different values. The checker returns `blocked` together with the exact pair. This proves a failure of descent for the supplied finite relation and query. It does not prove that the supplied relation is a complete model of a physical experiment.

Run a passing structural example:

```bash
python run_audit.py complex examples/complex_valid_transport.json
```

Run a strict mismatch that is harmless on homology:

```bash
python run_audit.py holonomy examples/holonomy_contractible_derived_pass.json
```

The output preserves the strict defect as a warning and emits an exact chain homotopy. It checks only the supplied finite rational complexes and semantic bindings.

Run the tests from a source checkout on every supported platform:

```bash
python scripts/run_tests.py
```

For an installed command, create a virtual environment and run `python -m pip install -e .`; then use `bsc-audit` instead of `python run_audit.py`.

## Status model

Four coordinates are deliberately separate:

1. **Research verdict:** `proven`, `strongly_supported`, `plausible_but_unresolved`, `refuted`, `ill_posed`, or `outside_current_knowledge`. This is assigned through human scientific review, not inferred from JSON parsing.
2. **Evidence maturity:** `declared`, `structurally_checked`, `empirically_passed`, or `externally_replicated`.
3. **Deployment status:** `research_only`, `sandboxed`, `candidate`, `admitted`, or `retired`.
4. **Gate state:** `unrun`, `pass`, `fail`, or `conflict`.

CLI decisions are `no_blocking_findings`, `no_blocking_findings_with_warnings`, `blocked`, `demoted`, `prohibited`, or the exceptional `internal_error`. See [docs/STATUS_MODEL.md](docs/STATUS_MODEL.md).

Admission is conjunctive: every applicable fatal gate must pass. An aggregate score cannot rescue an unrun, failed, or conflicting fatal gate.

## Trust boundary

- Inputs are user declarations. The checker does not know that a claim, citation, proof identifier, hash target, calibration record, or experiment is honest merely because it is syntactically present.
- Exact arithmetic applies only to the finite objects actually supplied to the relevant command.
- LLM-produced reports and manifests are drafts. Target documents are untrusted data and may contain prompt injection.
- Domain plugins activate only when their required typed fields are present. Output should say which checks ran and which did not.
- Negative results, conflicts, and fired demotions are preserved rather than averaged or silently overwritten.

Read [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) before relying on an audit and [SECURITY.md](SECURITY.md) before reporting a vulnerability or false-pass condition.

## Contributing and governance

Compact counterexamples, false-pass reports, false-block reports, accessibility fixes, and better kill conditions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md). Changes to fatal gates follow [GOVERNANCE.md](GOVERNANCE.md).

The software is maintained under the project identity **J. Tree** and distributed under Apache-2.0. The research note in `research/` is separately licensed under CC BY 4.0. The custom software release bundle and Python distributions exclude the research PDF and DOCX. GitHub's automatically generated tag source archives contain every tracked file, including those research artifacts; `research/LICENSE` governs them inside those archives. See the license file in each scope.

Public attribution is deliberately pseudonymous. The fail-closed privacy gate permits only the declared project identities and GitHub-controlled bot identities; see [PRIVACY.md](PRIVACY.md).
