# Sharing and Release Guide

The v0.3.0-alpha.1 release is a research preview. Every public description should preserve that status and link to a worked positive and negative example.

## Two public surfaces

1. **GitHub is the living workshop.** Source history, issues, pull requests, fixtures, and active releases live there.
2. **Zenodo is the immutable archive.** Frozen software releases and foundations papers receive separate citable records linked in both directions.

## GitHub release contents

Create tag `v0.3.0-alpha.1` and attach:

- `bsc-audit-engine-0.3.0-alpha.1.zip`;
- `BSC_AUDIT_LLM_PACKET.md`;
- the versioned foundations paper, if released;
- `SHA256SUMS`;
- a machine-readable source archive or the automatically generated GitHub source archive.

Do not manually zip a working directory containing caches or untracked files. Build from the tagged tree. Preserve the prior `v0.2.1` tag rather than moving it.

Replace these placeholders before publishing:

```text
https://github.com/<OWNER>/<REPOSITORY>/releases/tag/v0.3.0-alpha.1
https://raw.githubusercontent.com/<OWNER>/<REPOSITORY>/v0.3.0-alpha.1/BSC_AUDIT_LLM_PACKET.md
```

## Zenodo records

Use separate related records:

- **Software:** the frozen GitHub release, Apache-2.0.
- **Publication or preprint:** the mathematical foundations paper under its declared document license.

Add reciprocal `isSupplementTo`/`isSupplementedBy` or equivalent relations and include the final repository URL in both `CITATION.cff` and `.zenodo.json`.

The creator identity remains **J. Tree** unless the maintainer deliberately updates it. Do not invent an ORCID, institution, or endorsement.

## What a trustworthy audit release contains

```text
audit-name/
  README.md
  target/
  claim.json
  source-coverage.json
  human-report.md
  checker-output.json
  counterexamples/
  environment.txt
  SHA256SUMS
```

The README states:

- exact frozen claim;
- research verdict and reviewer;
- evidence maturity and deployment status;
- engine and schema version;
- commands and expected exit codes;
- checks run and not run;
- unresolved evidence;
- first demotion condition.

## Audience routes

### Curious reader

Share [START_HERE.md](../START_HERE.md) and one small worked audit. Do not begin with the full mathematical framework.

### Programmer

Share the tagged repository and [PROGRAMMER_TUTORIAL.md](PROGRAMMER_TUTORIAL.md). Ask for the exact manifest, JSON output, version, and minimal counterexample in any report.

### LLM user

Share the versioned [BSC_AUDIT_LLM_PACKET.md](../BSC_AUDIT_LLM_PACKET.md) together with its privacy warning. Never invite a user to upload confidential material casually.

### Scientific reviewer

Share a frozen target, source-coverage ledger, manifest, actual checker output, certificates, hashes, and human report. Do not ask the reviewer to reconstruct which branch or prompt produced the claim.

## Release checklist

- [ ] A clean checkout passes documented commands on supported Python versions.
- [ ] `bsc-audit --version`, package metadata, citation metadata, and release notes agree.
- [ ] Manifest schema and compatibility table are present.
- [ ] All CLI failures remain structured JSON with documented exit codes.
- [ ] Positive and adversarial fixtures have documented expected outcomes.
- [ ] Links and evidence identifiers resolve.
- [ ] No placeholder owners, hashes, repository URLs, or proof identifiers remain in release examples presented as complete.
- [ ] Full license text and contribution-license statement are present.
- [ ] Accessibility checks cover language, heading order, keyboard focus, narrow view, and 200% zoom.
- [ ] LLM packet covers prompt injection, privacy, source coverage, and fabricated execution.
- [ ] `SECURITY.md`, governance, issue forms, and conduct policy are linked.
- [ ] SHA-256 sums are generated from final assets.
- [ ] A negative result or known limitation is visible in release notes.

## Public wording

Preferred:

> BSC Audit Engine is experimental research software that checks selected structural obligations and emits finite witnesses. It does not certify arbitrary scientific truth or authorize deployment.

Avoid:

- “truth engine”;
- “automated peer review”;
- “formally verified science” unless a named formal system actually supplies the proof;
- “BSC compliant”;
- claims that an LLM ran the Python checker without actual output.
