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
The exact retained GitHub transport object is separately registered in
[`privacy-commit-transport-policy.json`](privacy-commit-transport-policy.json),
without expanding the author allowlist.
The fail-closed checker is [`scripts/check_privacy.py`](scripts/check_privacy.py).
Run it before sharing a source tree:

```bash
python scripts/check_privacy.py --protected-history HEAD
```

The protected-history mode checks every author and committer after the
machine-registered enforcement base, not only the tip. Review of the entire reachable ancestry remains available with
`--history HEAD`; historical identity names can still fail the current policy.
Release construction additionally scans the generated wheel, source
distribution, source bundle, conformance packet, SBOM, and publication files.
Unsupported tracked binary formats and unreadable archives are blocking errors;
silence is never treated as a privacy pass.

One post-policy GitHub merge object is retained under an exact-object
exception: commit `4135c705a14ea6628481798da123dc62bee40885`. The policy binds
its commit ID, both parents, subject, author pair, and GitHub committer pair.
Its projected author name is not a declared project identity and is not
accepted for any other commit, document, package, or publication field.

## Prospective enforcement boundary

The ancestry through commit
`0659a7c41732d62271a001fe30cf50745905940f` predates this policy. A metadata-only
history migration replaced the owner's exposed personal email with the existing
GitHub noreply identity. Historical names, dates, messages, and source trees were
preserved. Some historical names remain outside the current allowlist, so a
complete `--history HEAD` scan can still fail. They are not added to the allowlist.

Protected-history enforcement retains the same boundary in the migrated graph.
Every later commit must pass, apart from the single exact retained merge object
documented above. Its commit and parent pins refer to the migrated objects;
its identity exception is unchanged and is not reusable on other objects.

See [History migration and historical evidence](docs/PRIVACY_HISTORY_MIGRATION.md)
for the distinction between current-main checks and original-history attestations.

## Publication metadata

The research DOCX and PDF may identify the author only as `J. Tree`. Their
creator and producer fields use the generic value `BSC publication pipeline`.
Creation timestamps, modification timestamps, detailed office-suite versions,
machine architectures, external document relationships, and revision-session
identifiers are removed by `scripts/sanitize_publications.py`.

## GitHub boundary

The repository owner, pre-policy commit metadata, public activity timestamps,
historical commit and release records, and links between repositories owned by
the same GitHub account remain public GitHub metadata. This policy does not
claim that a public GitHub account is unlinkable. It prevents new accidental
real-world contact data and machine or credential leakage inside the project's
controlled artifacts.
