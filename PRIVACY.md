# Pseudonymous publication policy

This repository is pseudonymous, not anonymous. Its declared public project
identities are `J. Tree`, `Tree, J.`, `jtree`, and `jkolantree`. GitHub-controlled
bot identities may appear where GitHub creates or signs repository objects.

No other maintainer identity, personal email address, affiliation, ORCID,
telephone number, postal address, precise location, workstation path, credential,
or private key belongs in a tracked file or release artifact. Commit author and
committer email addresses must use GitHub's `users.noreply.github.com` service;
GitHub's own `noreply@github.com` committer is also permitted.

The machine-readable allowlist is [`privacy-policy.json`](privacy-policy.json).
The fail-closed checker is [`scripts/check_privacy.py`](scripts/check_privacy.py).
Run it before sharing a source tree:

```bash
python scripts/check_privacy.py --protected-history HEAD
```

The protected-history mode checks every author and committer after the
machine-registered enforcement base, not only the tip. Forensic review of the
entire immutable ancestry remains available with `--history HEAD`.
Release construction additionally scans the generated wheel, source
distribution, source bundle, conformance packet, SBOM, and publication files.
Unsupported tracked binary formats and unreadable archives are blocking errors;
silence is never treated as a privacy pass.

## Prospective enforcement boundary

The immutable ancestry through commit
`2c611ab693f09bc2f3b5304f972d9a3b8a8f1969` predates this policy and contains
commit identities or addresses that do not satisfy the current GitHub-noreply
contract. Those values are not added to the allowlist and a complete
`--history HEAD` scan continues to report them. Rewriting that ancestry would
also rewrite the released and tagged audit trail, so the CI-blocking guarantee
is prospective from the registered base commit. Every later commit must pass.

## Publication metadata

The research DOCX and PDF may identify the author only as `J. Tree`. Their
creator and producer fields use the generic value `BSC publication pipeline`.
Creation timestamps, modification timestamps, detailed office-suite versions,
machine architectures, external document relationships, and revision-session
identifiers are removed by `scripts/sanitize_publications.py`.

## GitHub boundary

The repository owner, pre-policy commit metadata, public activity timestamps,
immutable commit and release history, and links between repositories owned by
the same GitHub account remain public GitHub metadata. This policy does not
claim that a public GitHub account is unlinkable. It prevents new accidental
real-world contact data and machine or credential leakage inside the project's
controlled artifacts.
