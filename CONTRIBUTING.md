# Contributing

Contributions are evaluated by scope, reproducibility, and failure behavior. Unconventional claims are welcome; untyped authority is not.

## Good contributions

- a compact counterexample;
- a false-pass or false-block report;
- a known-answer fixture where a simpler baseline wins;
- a clearer type or schema contract;
- an accessibility or onboarding repair;
- a preservation or migration test;
- a narrow gate with an exact witness and retirement condition.

## Development setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
bsc-audit --version
python -m unittest discover -s tests -v
```

PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e .
python -m unittest discover -s tests -v
```

The zero-install test route is documented in [docs/PROGRAMMER_TUTORIAL.md](docs/PROGRAMMER_TUTORIAL.md).

## Before opening an issue

Search existing issues. Remove secrets and identifying or proprietary material. Include:

- engine and schema version;
- command and exit code;
- minimal sanitized input;
- actual structured output;
- expected output and why;
- whether the report is a false pass, false block, crash, documentation defect, or mathematical counterexample.

Use private vulnerability reporting for sensitive security defects; see [SECURITY.md](SECURITY.md).

## Pull-request requirements

Every behavior change includes:

1. a typed input contract;
2. exact or bounded output semantics;
3. a positive known-answer test;
4. a negative test with a minimal witness;
5. a malformed or boundary test where relevant;
6. a statement of what passing does not prove;
7. documentation and schema migration when public behavior changes;
8. a prospective demotion or retirement condition for new scientific diagnostics.

Run:

```bash
python scripts/run_tests.py
git diff --check
```

Do not weaken a fatal gate into a score. Do not delete a negative result because a preferred model fails it. Do not silently change prior output semantics.

When `START_HERE.md` changes, regenerate its offline page with Pandoc and inspect it at keyboard-only, narrow viewport, dark mode, print preview, and 200% zoom:

```bash
pandoc START_HERE.md --standalone \
  --metadata pagetitle='Start Here: BSC Audit Engine' \
  --metadata lang=en \
  --css docs/starter.css --embed-resources --no-highlight \
  --output START_HERE.html
```

## Fatal-gate proposals

A new or altered fatal gate must state:

- activation scope;
- mathematical or methodological basis;
- false-pass cost and false-block cost;
- counterexamples and ordinary baseline;
- witness format;
- versioning and migration effect;
- review and retirement condition.

These proposals follow [GOVERNANCE.md](GOVERNANCE.md).

## Contribution license

By submitting a contribution, you represent that you have the right to submit it and agree that it is distributed under the repository’s Apache-2.0 license unless a file clearly declares another license. Do not submit third-party material without compatible permission and attribution.

## Conduct

Review claims rigorously and people respectfully. Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
