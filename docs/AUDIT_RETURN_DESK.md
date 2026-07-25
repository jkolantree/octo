# Audit Return Desk

The Audit Return Desk inspects structured audit returns under an explicitly non-admissive contract. It has two implementations with the same contract:

- the browser-local Desk in `pages/`, for strict JSON parsing and hashes of files selected by the user; and
- `python run_audit.py return-desk PATH`, for the same semantic inspection with artifacts read from the return file's directory.

Current official-service availability is recorded separately in [CUSTOM_GPT_STATUS.md](CUSTOM_GPT_STATUS.md). Official-service availability, exact candidate binding, Preview validation, GitHub release state, and Pages deployment are separate facts; none can be inferred solely from the presence of this source feature.

The official compact Custom GPT does not generate or export machine records and does not upload `BSC_EXECUTION_AND_RECEIPTS.md`. This Desk and its compiler workflow remain available only as supervised standalone repository tooling; their presence does not imply that the public GPT ran them.

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

## Standalone deterministic producer transaction

An explicitly selected supervised standalone machine-record workflow must be finalized by the complete canonical
`scripts/gpt_artifact_compiler.py` source preserved in the retired
[`BSC_EXECUTION_AND_RECEIPTS.md`](standalone/BSC_EXECUTION_AND_RECEIPTS.md) derivative. The model must execute that source, not
reproduce its behavior in prose or write a substitute finalizer.

The executed compiler captures its own full `sys.version` once; the
model-authored spec cannot supply or override it. It accepts exact frozen
request/source/evidence bytes, an explicit control-free `report_body_lines`
array, and a structured return template,
then derives artifact identities and the runtime ledger from the final bytes,
validates execution/evidence topology, writes
`chatgpt_data_analysis_output.txt`, and serializes `audit_return.json` last. A
compiler failure prohibits the return and every conclusion that depended on
successful artifact production. A matching final snapshot does not, by itself,
prove the historical write order; compiler execution and its preserved output
are therefore part of the candidate evidence.

For the retained standalone artifact transaction, the legacy execution
topology is fixed:

- `model_reasoning` inputs are the request, exact case target, and all six
  canonical Knowledge files; its outputs are every model-produced
  role-`evidence` artifact and `audit_report.md`; `receipt_ids` is empty.
- `chatgpt_data_analysis` has those same inputs; its outputs are those evidence
  artifacts, `audit_report.md`, and
  `chatgpt_data_analysis_output.txt`; `receipt_ids` is empty.

External receipts belong only to their actual external activity. They cannot be
aliased to model reasoning or Data Analysis.

## Browser workflow

1. Open the Pages module and confirm that its displayed protocol version and verification state match the workflow you intend to use.
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

## Preview transport boundary

The evaluation controller first attempts the direct generated-file control.
After serializing `audit_return.json`, the original compiler-v9 transaction
constructs one deterministic bounded container from the same finalized
in-memory generated-output bytes. Same-response transport v2 compresses the
container, splits the zlib stream into contiguous data shards of at most 2,048
bytes, and adds one `xor_parity_v1` shard: the bytewise XOR of every data shard
padded with zero bytes to the maximum shard width. The compiler includes the
complete envelope in canonical no-terminal-LF stdout. The candidate must append
that complete stdout byte-for-byte in one final fenced code block, with no
following prose. The bundle is transport-only: it is not a semantic artifact,
execution output, or file control, and it never depends on a later `/mnt/data`
path.

The controller preserves the complete original response `outerHTML` and the
exact compiler-block text. It requires one canonical compiler block, a sorted
unique portable member roster, contiguous shards, canonical Base64, bounded
decompression, exact container framing, and matching container/member sizes
and SHA-256 values before reconstructing local bytes. It may recover exactly
one data shard only when its metadata and expected ASCII Base64 text length are
intact, its content fails decoding or its declared byte binding, and all other
data shards and parity are valid. Every aggregate, container, member, and
topology check is then rerun, and deterministic receipt state
`data_shard_recovered` is recorded; a pristine bundle records `not_needed`.
Aligned-quartet omission, metadata mutation, more than one bad data shard, or
bad data plus bad parity is unrecoverable. When all data shards are valid and
only exact-length parity content is bad, parity is not used and the receipt
state is `parity_degraded_not_used`.

Bundle integrity is always validated. Direct acquisition remains the primary
candidate-byte path; the reconstructed member is selected only when the
interface exposes no direct bytes. When both copies exist, their exact bytes
must match or the candidate fails. For every visible file control, the
controller binds an explicit per-file attempt outcome; missing bytes alone
never imply `no_download_event`. The controller derives
`artifact_transport.json` deterministically from those bound observations and
bytes, and binds the deterministic recovery receipt in
`controller_record.json`.

A completed response that omits or truncates the bundle, or leaves a mutation
outside the one permitted recovery, is `candidate_failed`. Controller loss or
mutation of a block demonstrably present in the bound raw response is
`trial_invalid_controller`. A valid or validly recovered bundle establishes
only the exported payload actually received. If original download-button bytes
remain unavailable, their identity is `transport_identity_unresolved`; neither
identity nor corruption is established.
