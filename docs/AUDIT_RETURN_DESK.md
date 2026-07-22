# Audit Return Desk

The Audit Return Desk is an unreleased `0.3.0-alpha.8` development feature for inspecting structured audit returns. It has two implementations with the same contract:

- the browser-local Desk in `pages/`, for strict JSON parsing and hashes of files selected by the user; and
- `python run_audit.py return-desk PATH`, for the same semantic inspection with artifacts read from the return file's directory.

The live Custom GPT and current GitHub release remain bound to validated `v0.3.0-alpha.7`. Alpha.8 is not installed in the live GPT, released, or publicly deployed yet.

## Authority boundary

The Desk checks internal consistency. It does not decide truth, authenticate a citation, prove a theorem, establish that an external tool actually ran, independently replicate an experiment, admit evidence, or grant deployment permission.

Every accepted envelope must keep these values exactly:

```json
{
  "return_version": "0.1.0",
  "authority": "non_admissive_return_inspection",
  "draft": true
}
```

The closed schema is [`schemas/audit-return-v0.1.schema.json`](../schemas/audit-return-v0.1.schema.json). The canonical production rules are in the [LLM Audit Packet](../BSC_AUDIT_LLM_PACKET.md). Generated model output is still untrusted input to the Desk.

## Browser workflow

1. Open the Pages module after the alpha.8 change is merged and deployed.
2. Paste one complete `audit_return.json` object or select the JSON file.
3. Select the request, human report, sources, evidence, execution outputs, and receipt files declared by that envelope.
4. Select **Inspect return locally**.
5. Review every blocking, needs-review, and informational finding. Expand technical witnesses and repairs when present.
6. Download the deterministic inspection JSON only if its metadata is safe to retain or share.

The page verifies the canonical protocol and embedded return-schema bytes before enabling inspection. It rejects duplicate JSON keys, trailing data, stale protocol bindings, unsafe or colliding filenames, contradictory ledgers, unsupported verdict promotion, concealed gate failures, unrelated execution reuse, exact-byte artifact aliases across IDs or roles, and local hash mismatches.

Return JSON is limited to 8 MiB of UTF-8. Browser hashing is limited to 32 selected return artifacts, 64 MiB per file, and 256 MiB in total; additional declared files remain unavailable and force `needs_review`. The Python route enforces the same 32-file, 64-MiB-per-file, and 256-MiB-total bounds and blocks an envelope that exceeds its declared-file or aggregate local-byte budget. Split a larger review into explicitly scoped returns without omitting material evidence. The page code reads selected bytes for hashing, makes no target-data network request, intentionally stores nothing, and collects no browser file path. Browser and operating-system history, crash recovery, swap, extensions, clipboard, and downloaded inspection files remain outside the page's control.

The downloaded result contains no attached file bytes, but it may disclose filenames, identifiers, expected and observed hashes, witnesses, and repairs. SHA-256 values do not anonymize private or low-entropy material.

## Python workflow

Place the envelope and its declared artifacts in one directory, with unique portable basenames, then run:

```bash
python run_audit.py return-desk path/to/audit_return.json
```

Known controls:

```bash
python run_audit.py return-desk examples/audit_return_valid.json
python run_audit.py return-desk examples/audit_return_missing_artifact.json
python run_audit.py return-desk examples/audit_return_poisoned_summary.json
```

The first returns `no_blocking_findings`, the second returns `no_blocking_findings_with_warnings`, and the poisoned summary returns `blocked`. Exit code `0` means only that this inspection found no blocking inconsistency; it is not a scientific pass.

## What is recomputed

The semantic layer checks:

- exact protocol version and SHA-256;
- globally unique IDs and complete references;
- request/report roles and portable filename uniqueness;
- bidirectional claim, evidence, gate, and obligation bindings;
- claim-scoped gate evidence and complete summary projections;
- local artifact hashes and eligible evidence roles;
- source coverage and source-byte requirements for `proven`, `strongly_supported`, and `refuted`;
- the exact eight-activity execution roster and `file_read_only` boundary;
- execution input, output, receipt, claim, and gate scope;
- receipt authority, kind, artifact uniqueness, and single-activity use;
- fatal-gate state and conjunctive admission recomputation; and
- the prohibition on receipt-only proof and deployment overreach.

Missing bytes normally cause review-needed status. A declared hash mismatch, placeholder hash, stale protocol, invalid schema, concealed failure, unsupported promotion, or contradictory binding blocks. Missing material alone never refutes a claim.

## Browser and Python outcomes

| Meaning | Browser | Python CLI |
|---|---|---|
| No blocking finding or unavailable byte | `consistent` | `no_blocking_findings` |
| Internally coherent but something remains unavailable or unverified | `needs_review` | `no_blocking_findings_with_warnings` |
| Malformed, contradictory, unsupported, stale, or integrity-failing | `blocked` | `blocked` or `prohibited` for schema/malformed input |

These outcomes are a separate coordinate from research verdict, evidence maturity, execution status, gate state, deployment status, and the decisions of other BSC routes.
