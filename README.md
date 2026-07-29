# BSC Audit Engine

Research-preview software for making mathematical and scientific claims easier to inspect, challenge, reproduce, and demote.

**Official Custom GPT:** [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) (live research preview)<br>
**Current GitHub prerelease:** `v0.3.0-alpha.15`<br>
**Validation boundary:** the live indexed-Knowledge state is `NON_ADMISSIBLE_UNHASHABLE`; product observations and engine proofs remain separate, and this is a research preview rather than certification<br>
**Project status:** experimental; suitable for research audits and known-answer tests, not for unattended scientific, clinical, legal, safety, or policy decisions.

Related research: On Boundaries of Evidence / Boundary-State Calculus is maintained separately at https://github.com/jkolantree/BSC. This audit engine is an experimental companion; it does not certify the manuscript or establish theorem status.

[日本語](README.ja.md) | [Historical publication snapshot](docs/PUBLICATION_STATUS.json)

BSC is offered as infrastructure for careful imagination. It permits ambition, but not free authority.

## What it does

The engine checks a narrow set of declared structural obligations. Current routes include:

- manifest and hard-gate linting;
- exact symbolic replay of closed polynomial identities over `Q`;
- exact rational matrix and chain-complex checks;
- certificate-interchange defects and finite witnesses;
- square holonomy and path-dependence checks;
- arbitrary-path strict, derived, and observed-derived holonomy over exact rationals;
- short-exact-sequence certificates binding an observed quotient to its declared null subcomplex;
- replayable chain-homotopy solutions or dual-obstruction certificates over exact rationals;
- finite observation/query descent witnesses;
- product-valued gates with non-averaged conflict states;
- fatal dependency propagation in acyclic claim graphs;
- finite atomic-modulus record checks;
- exact propagation of declared affine upper bounds;
- scoped arithmetic-trace and local/global recovery gates;
- subject-, evidence-, method-, scope-, and authority-bound replay judgments;
- non-admissive, hash-bound Lean/SMT/interval adapter receipts;
- non-admissive inspection of returned audit envelopes, ledgers, projections, receipts, and local artifact hashes;
- canonical JSON hashing.

The engine does **not** determine whether an arbitrary theory is true, reconstruct an arbitrary proof, validate an external evidence identifier, certify empirical replication, or grant moral, legal, clinical, or deployment permission. Claim manifest `0.4.0` admits one closed theorem family: exact polynomial identities over `Q` whose authoritative AST, title, statement, and residual are deterministically recomputed by the bundled kernel. A replay result is decisive only for the exact subject, evidence bytes, predicate, scope, method, and authority recorded in its checked judgment; a shared label such as `pass` transfers none of those coordinates. Every other declared result—including hash-matched proofs, datasets, replications, and arithmetic-obligation evidence—remains provenance unless a registered exact replay recomputes it. A `no_blocking_findings` result means only that the checks actually run found no blocking condition.

## Choose an entry point

1. **Official Custom GPT - direct ChatGPT audit:** open the live [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor). The alpha.10 package gives all four bilingual starter literals explicit intake or example routes while preserving the bounded Quick contract; large artifact, hash, Base64, shard, and transport output is excluded from this public profile. Treat every output as a research-preview draft rather than a certificate. Uploads go through ChatGPT under the user's applicable settings and terms. The GPT has no Action, hosted API, account, analytics, or cloud-storage integration. See the separately observed [live/candidate status](docs/CUSTOM_GPT_STATUS.md).
2. **Local browser Packet Builder and Audit Return Desk:** [open the accessible English GitHub Pages module](https://jkolantree.github.io/octo/) or the deployed [Japanese route](https://jkolantree.github.io/octo/ja.html) to construct a versioned packet or inspect a returned `audit_return.json` draft and selected artifact bytes locally. Neither function uploads the target, calls an LLM, or runs Python.
3. **Repository and Python engine - exact checker route:** use [docs/PROGRAMMER_TUTORIAL.md](docs/PROGRAMMER_TUTORIAL.md) for versioned schemas, fixtures, finite exact checks, and preserved command output. This is the only route here that runs the BSC checker.

The repository contains the deterministic Custom GPT package lineage used for independent inspection, reproducible deployments, compatible forks, and verifiable updates. Alpha.10 is the separately observed live baseline; alpha.15 is an unvalidated repository update candidate and is not installed live in this release lane. The byte-identical protocol component remains versioned `0.3.0-alpha.13`, independently of the engine release. Indexed Knowledge bytes are not independently retrievable, so they cannot support engine gates. The older timestamped JSON snapshot is preserved as historical evidence.

Supporting routes:

- **First visit:** [START_HERE.md](START_HERE.md) or the accessible offline [START_HERE.html](START_HERE.html)
- **Japanese first visit:** use [START_HERE.ja.md](START_HERE.ja.md) or the deployed [Japanese Pages route](https://jkolantree.github.io/octo/ja.html).
- **Human-only audit:** [AUDIT_WORKSHEET.md](AUDIT_WORKSHEET.md)
- **Manual LLM packet:** [BSC_AUDIT_LLM_PACKET.md](BSC_AUDIT_LLM_PACKET.md)
- **Documentation map:** [docs/index.md](docs/index.md)
- **Example catalog:** [examples/README.md](examples/README.md)
- **Mathematical definitions:** [docs/MATHEMATICS.md](docs/MATHEMATICS.md)
- **Derived holonomy:** [docs/DERIVED_HOLONOMY.md](docs/DERIVED_HOLONOMY.md)
- **Spectral obstruction boundary:** [docs/SPECTRAL_OBSTRUCTIONS.md](docs/SPECTRAL_OBSTRUCTIONS.md)
- **New research packet:** [research/derived-witnessed-descent/README.md](research/derived-witnessed-descent/README.md)
- **Proof adapter boundary:** [docs/PROOF_CARRYING_ADAPTERS.md](docs/PROOF_CARRYING_ADAPTERS.md)
- **Audit Return Desk:** [docs/AUDIT_RETURN_DESK.md](docs/AUDIT_RETURN_DESK.md)
- **Pseudonymous publication policy:** [PRIVACY.md](PRIVACY.md)
- **Published corrections:** [ERRATA.md](ERRATA.md)

The Pages module's code makes no target-data network request, intentionally persists nothing, verifies the versioned audit protocol before enabling output, and prepares a packet for an LLM you choose. Browser, operating-system, extension, clipboard, and download behavior remains outside the page's control. Sending that packet or uploading directly to a Custom GPT crosses into the selected model service and is not local-only. Do not put sensitive material into any third-party model without separate authorization.

The Return Desk checks a closed return schema, bidirectional references, summary projections, fatal-gate derivation, execution disclosures, receipt limits, and available local artifact hashes. A consistent result is not a finding of truth, proof, source authenticity, independent execution, or deployment permission.

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

Inspect a returned audit envelope and any artifact files placed beside it:

```bash
python run_audit.py return-desk examples/audit_return_valid.json
python run_audit.py return-desk examples/audit_return_poisoned_summary.json
```

The first fixture is internally consistent and explicitly non-admissive. The second is blocked because its summary conceals the underlying claim verdict. Neither result decides whether the represented research claim is true.

Run the tests from a source checkout on every supported platform:

```bash
python scripts/verify.py core
```

Use `python scripts/verify.py pages` for the browser publication surface and
`python scripts/verify.py candidate` for the complete fail-fast integration
profile. For an installed command, create a virtual environment and run
`python -m pip install -e .`; then use `bsc-audit` instead of
`python run_audit.py`.

## Status model

Five status coordinates are deliberately separate:

1. **Research verdict:** `proven`, `strongly_supported`, `plausible_but_unresolved`, `refuted`, `ill_posed`, or `outside_current_knowledge`. This is assigned through human scientific review, not inferred from JSON parsing.
2. **Evidence maturity:** `declared`, `structurally_checked`, `empirically_passed`, or `externally_replicated`.
3. **Execution status:** `not_run`, `file_read_only`, `ran`, `reported_but_unverified`, or `not_applicable`, recorded separately for model reasoning, web and citation checks, ChatGPT tools, BSC Python, external proof tools, and empirical tests. `file_read_only` never establishes that a calculation or verifier ran.
4. **Deployment status:** `research_only`, `sandboxed`, `candidate`, `admitted`, or `retired`.
5. **Gate state:** `unrun`, `pass`, `fail`, or `conflict`.

The separate BSC CLI decision is `no_blocking_findings`, `no_blocking_findings_with_warnings`, `blocked`, `demoted`, `prohibited`, or the exceptional `internal_error`. See [docs/STATUS_MODEL.md](docs/STATUS_MODEL.md).

Admission is conjunctive: every applicable fatal gate must pass. An aggregate score cannot rescue an unrun, failed, or conflicting fatal gate.

## Trust boundary

- Inputs are user declarations. The checker does not know that a claim, citation, proof identifier, hash target, calibration record, or experiment is honest merely because it is syntactically present.
- Exact arithmetic applies only to the finite objects actually supplied to the relevant command.
- LLM-produced reports and manifests are drafts. Target documents are untrusted data and may contain prompt injection. ChatGPT Code Interpreter or Data Analysis output is not a versioned BSC Python result unless that checker actually ran and its output is preserved.
- Domain plugins activate only when their required typed fields are present. Output should say which checks ran and which did not.
- Negative results, conflicts, and fired demotions are preserved rather than averaged or silently overwritten.

Read [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) before relying on an audit and [SECURITY.md](SECURITY.md) before reporting a vulnerability or false-pass condition.

## Contributing and governance

Compact counterexamples, false-pass reports, false-block reports, accessibility fixes, and better kill conditions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md). Changes to fatal gates follow [GOVERNANCE.md](GOVERNANCE.md).

The software is maintained under the project identity **J. Tree** and distributed under Apache-2.0. The research note in `research/` is separately licensed under CC BY 4.0. The custom software release bundle and Python distributions exclude the research PDF and DOCX. GitHub's automatically generated tag source archives contain every tracked file, including those research artifacts; `research/LICENSE` governs them inside those archives. See the license file in each scope.

Public attribution is deliberately pseudonymous. The fail-closed privacy gate permits only the declared project identities and GitHub-controlled bot identities; see [PRIVACY.md](PRIVACY.md).
