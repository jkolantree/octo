# Programmer Tutorial

The current public prerelease is `v0.3.0-alpha.15`. The `holonomy` route first appeared in alpha.3; the closed `theorem` route first appeared in alpha.12. Preserve the exact engine version with every output.

This is the repository and Python exact-checker route. It is distinct from the official live [Custom GPT](CUSTOM_GPT_STATUS.md) and the [local browser Pages module](https://jkolantree.github.io/octo/). The repository GPT package is reproducible source and an update candidate; its existence does not prove that its exact bytes are installed or Preview-validated in the live service. ChatGPT uploads are not local-only, ChatGPT tools are not automatically BSC Python, and neither surface provides a GPT Action or hosted checker API.

## Requirements

- Python 3.11 or newer
- a terminal
- Git only for version history and collaboration

The runtime checker has no third-party dependencies.
Release distributions are built with the installed setuptools backend via
`python scripts/build_dist.py`; the backend version is printed and recorded in
the release manifest.

## 1. Verify the version

From the extracted project folder:

```bash
python run_audit.py --version
```

The output must identify the source you intended to audit. The current development checkout reports:

```text
bsc-audit 0.3.0a15
```

The published alpha.3 release reports:

```text
bsc-audit 0.3.0a3
```

Record the exact value with every audit and do not attribute alpha.3 route output to an earlier release.

## 2. Zero-install route

Run a fixture directly:

```bash
python run_audit.py audit examples/claim_valid.json
python run_audit.py theorem examples/theorem_binomial_identity.json
python run_audit.py audit examples/claim_polynomial_identity.json
python run_audit.py observe examples/observation_failure.json
python run_audit.py return-desk examples/audit_return_valid.json
python run_audit.py return-desk examples/audit_return_missing_artifact.json
python run_audit.py return-desk examples/audit_return_poisoned_summary.json
```

The legacy `claim_valid.json` command is expected to block with exit code `1`
because hash verification alone cannot replay its declared result. The two
closed polynomial commands pass their exact formal checks. The observation
failure and poisoned Return Desk examples also block with exit code `1`.

### Run tests on macOS, Linux, or Windows

```bash
python scripts/verify.py core
```

Use `python scripts/verify.py pages` for the bounded browser surface and
`python scripts/verify.py candidate` for the complete fail-fast integration
profile. A passing profile establishes expected behavior on bundled fixtures,
not scientific truth.

## 3. Editable installation

Use an isolated environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
bsc-audit --version
```

PowerShell activation:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e .
bsc-audit --version
```

## 4. Command map

| Command | Input | Supported check |
|---|---|---|
| `lint` | claim manifest | schema-facing manifest and evidence-transition rules |
| `audit` | claim manifest | lint, gate product, dependency propagation, and activated domain plugins |
| `complex` | finite exact transport document | chain-complex law, interchange defect, and square holonomy |
| `observe` | finite states, relation, and queries | constancy of each query on each declared relation pair |
| `atomic` | exact finite concentration record | consistency with a declared power-modulus record |
| `defect` | exact rational defect path | affine propagation and understatement check |
| `adapter` | hash-bound external-tool receipt | non-admissive receipt structure and consistency only |
| `holonomy` | finite rational complexes and path relations | strict, chain-homotopy, and observed-derived equivalence certificates |
| `theorem` | closed exact-Q polynomial certificate | symbolic canonical-normal-form proof or countercertificate |
| `return-desk` | draft `audit_return.json` plus sibling artifacts | non-admissive protocol, projection, reference, execution, receipt, and local-byte consistency |

Each command checks only the supplied finite representation. For example, `observe` does not prove that the declared relation exhausts a real instrument’s observational equivalence.

The `holonomy` command additionally requires content-addressed semantic basis records. It verifies those byte bindings but does not validate their external interpretation. See [Exact Derived Holonomy](DERIVED_HOLONOMY.md).

## 5. Interpret structured output

Every subcommand returns JSON for valid input, malformed input, missing files, duplicate keys, and prohibited non-finite numeric values.

Example shape:

```json
{
  "engine_version": "0.3.0a15",
  "checks": {
    "run": ["strict_json_parse", "finite_observation_descent"],
    "not_run": ["claim_manifest_lint", "gate_product", "domain_plugins"]
  },
  "decision": "blocked",
  "findings": [
    {
      "severity": "BLOCKED",
      "code": "QUERY_DESCENT_FAILURE",
      "path": "queries.declared_query",
      "message": "query distinguishes states joined by the declared relation",
      "witness": {"left": "state_a", "right": "state_b"}
    }
  ]
}
```

Actual fields are governed by the released command and schema; do not fabricate output from this illustration.

Exit codes:

- `0`: `no_blocking_findings` or `no_blocking_findings_with_warnings`;
- `1`: `blocked` or `demoted`;
- `2`: malformed input or command usage;
- `70`: `internal_error`, an unexpected engine failure.

Treat internal failure as failure to audit, never as a scientific pass.

## 6. Start a new manifest

Copy the template:

```bash
mkdir -p work
cp templates/claim_manifest_template.json work/my_claim.json
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force work
Copy-Item templates\claim_manifest_template.json work\my_claim.json
```

Replace every placeholder. Keep all unsupported gates `unrun`. Then validate:

```bash
python -m json.tool work/my_claim.json
python run_audit.py lint work/my_claim.json
python run_audit.py audit work/my_claim.json
```

The current claim-manifest contract is [schemas/claim-manifest-v0.4.schema.json](../schemas/claim-manifest-v0.4.schema.json); immutable manifest `0.3.0` remains accepted. The closed theorem certificate is [schemas/theorem-certificate-v0.1.schema.json](../schemas/theorem-certificate-v0.1.schema.json). The separate returned-audit contract is [schemas/audit-return-v0.1.schema.json](../schemas/audit-return-v0.1.schema.json). Their schema versions are independent of the release candidate's PEP 440 version `0.3.0a15`; the public protocol component separately remains `0.3.0-alpha.13`.

## 7. Evidence and hashes

Evidence identifiers must resolve inside the preservation packet or through a stable external identifier. The linter cannot infer that a named proof or dataset is authentic.

Save:

```text
audits/<claim-id>/
  README.md
  claim.json
  target/
  certificates/
  checker-output.json
  human-report.md
  source-coverage.json
  counterexamples/
  environment.txt
  SHA256SUMS
```

Commit the frozen input before revising the claim. Preserve failed and superseded manifests instead of overwriting them.

## 8. Use LLM-generated artifacts safely

Treat generated JSON as untrusted source code:

1. inspect every field;
2. compare every claim with the cited source location;
3. remove invented evidence identifiers and hashes;
4. reset unjustified gate passes to `unrun`;
5. check source coverage and truncation;
6. run JSON validation and the mechanical checker yourself;
7. preserve both the original draft and reviewed revision.

Never report checker execution from simulated output. If ChatGPT Code Interpreter or Data Analysis ran, record that as ChatGPT tool execution. Record a BSC Python run only when the correct versioned checker actually executed and its output is preserved with the relevant input.

The official Custom GPT is live. A candidate still requires a fresh complete Preview gate before it can be called behaviorally validated, but indexed Knowledge bytes are not independently retrievable: `live_binding_state=NON_ADMISSIBLE_UNHASHABLE`. Saved-editor and public observations cannot satisfy engine gates. The [Audit Return Desk](AUDIT_RETURN_DESK.md) inspects returned output and receipts for internal consistency only; it does not turn them into admissible evidence or certify that an external execution occurred.

## 9. Add a domain gate

Domain rules live in `src/bsc_audit/plugins.py`. A proposed gate must:

1. activate only on a declared typed family;
2. specify its input and output contract;
3. state the mathematical or methodological basis;
4. return a stable code and minimal witness when possible;
5. include positive, negative, and ordinary-baseline fixtures;
6. state what passing does not prove;
7. include a prospective retirement condition.

Fatal-gate changes follow [GOVERNANCE.md](../GOVERNANCE.md). A gate may not be added merely because a claim is unconventional.

## 10. Reproducible pull request

Before opening a pull request:

```bash
python scripts/verify.py candidate
```

Include the exact claim, prior and new decision, reproduction command, input hash, expected exit code, and smallest counterexample. See [CONTRIBUTING.md](../CONTRIBUTING.md).
