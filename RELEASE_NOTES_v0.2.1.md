# BSC Audit Engine v0.2.1

This is an onboarding and distribution release. The exact audit kernel is unchanged except for its reported version.

## Added

- `START_HERE.md` and a double-clickable standalone HTML version for first-time users;
- `AUDIT_WORKSHEET.md` for a code-free human audit;
- `BSC_AUDIT_LLM_PACKET.md` as a self-contained LLM protocol;
- `docs/PROGRAMMER_TUTORIAL.md` with Windows, macOS, and Linux instructions;
- `docs/SHARING_GUIDE.md` for GitHub, Zenodo, releases, and audience routing;
- `SHARE_THIS.md` with Reddit, Threads, direct-message, and objection-response copy;
- reusable claim, observation, transport, atomic-modulus, and defect-path templates;
- `run_audit.py` for zero-install execution directly from an extracted archive.

## Verification

- 17 deterministic tests pass;
- all five new JSON templates parse;
- the claim, transport, atomic-modulus, and defect templates pass their relevant checker routes;
- the zero-install launcher reports engine version 0.2.1.

## Known boundary

An LLM-generated audit remains a draft until its factual claims are reviewed. An LLM must not claim the Python checker ran unless actual checker output is supplied. A structurally checked manifest is not automatically a proof or an empirical replication.
