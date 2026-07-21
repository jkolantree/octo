# Programmer Tutorial

This guide runs the v0.3.0-alpha.2 research preview from a source archive or editable installation.

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

The output must identify version:

```text
bsc-audit 0.3.0a2
```

Record this value with every audit.

## 2. Zero-install route

Run a fixture directly:

```bash
python run_audit.py audit examples/claim_valid.json
python run_audit.py observe examples/observation_failure.json
```

The second command is expected to return a blocking witness and exit code `1`.

### Run tests on macOS, Linux, or Windows

```bash
python scripts/run_tests.py
```

A passing suite establishes expected behavior on bundled fixtures, not scientific truth.

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

Each command checks only the supplied finite representation. For example, `observe` does not prove that the declared relation exhausts a real instrument’s observational equivalence.

## 5. Interpret structured output

Every subcommand returns JSON for valid input, malformed input, missing files, duplicate keys, and prohibited non-finite numeric values.

Example shape:

```json
{
  "engine_version": "0.3.0a2",
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

The machine-readable contract is [schemas/claim-manifest-v0.3.schema.json](../schemas/claim-manifest-v0.3.schema.json). The manifest version is `0.3.0`; it is independent of the engine’s PEP 440 version `0.3.0a2`.

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

Never report checker execution from simulated output.

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
python scripts/run_tests.py
git diff --check
```

Include the exact claim, prior and new decision, reproduction command, input hash, expected exit code, and smallest counterexample. See [CONTRIBUTING.md](../CONTRIBUTING.md).
