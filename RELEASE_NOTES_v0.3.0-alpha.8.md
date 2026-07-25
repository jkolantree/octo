# BSC Audit Engine v0.3.0-alpha.8

Alpha.8 is designated as a public research preview of the BSC Audit Engine and the repository-backed BSC Claim Auditor configuration. That designation does not itself establish publication; publication status is established only by the recorded local, Preview, live-binding, CI, and immutable-release gates.

## Compact public GPT pivot

The official GPT now performs one job: a bounded human-readable audit. It covers duties 1-9 within 500 words at `quick`, 1,200 at `standard`, and 2,000 at `adversarial` or `formal-mathematical` depth unless the user explicitly requests expansion. It does not generate files, hashes, `audit_return.json`, compiler stdout, Base64, shards, parity, transport, or section 10.

The live Knowledge roster is reduced to five files; `BSC_EXECUTION_AND_RECEIPTS.md` is no longer uploaded. Data Analysis remains available for actual attachment inspection or bounded calculations, but not for packaging the audit. The repository keeps the compiler, controller, return schema, and Audit Return Desk as separately invoked supervised tooling.

The current Preview gate is 12 fresh compact-profile cases, including an explicit request for the disabled export feature. The former 39-case artifact suite and D01/D02 transport preflights are preserved as historical evidence and do not validate this changed profile.

## Retained standalone compiler repairs

For explicitly selected offline repository workflows, this release replaces model-mediated artifact identity with one acyclic final-byte transaction:

- have the executed compiler capture its own Data Analysis `sys.version` once, reject model-authored overrides, and label the value session-reported rather than independently authenticated;
- finalize request, source, evidence, and report bytes before deriving hashes and sizes;
- generate one bound `chatgpt_data_analysis_output.txt` from that captured value and frozen metadata;
- have the report reference the bound output rather than manually recopying the runtime;
- serialize `audit_return.json` only after every referenced artifact is final;
- canonicalize all eight execution activities and the report-facing execution projection before any report, ledger, hash, or return bytes are derived;
- keep Base64 outside the primary proof path and treat any fallback only as the identity of the exported payload actually received;
- derive one deterministic bounded multi-artifact container from the compiler's same final in-memory output bytes after `audit_return.json` is serialized;
- retain compiler v7's bounded-transport contract through compiler v9: split the zlib stream into contiguous data shards of at most 2,048 bytes and add one `xor_parity_v1` shard in same-response transport v2;
- retain compiler v8's explicit `report_body_lines` contract in compiler v9, reject every Unicode category `Cc` code point in each line and in every generated JSON key and value, join validated report lines with compiler-owned LF separators, and fail without stripping, splitting, substitution, or other auto-repair;
- have compiler v9 validate the complete gate/obligation contract before rendering or hashing and project schema field `statement`, while keeping exact refutation closure separate from the open workflow duty to retire, narrow, or amend a failed claim before admission;
- include that dormant zlib/Base64 transport envelope in the original canonical compiler stdout, eliminating every later-turn `/mnt/data` dependency.

The retained historical/offline evaluation controller validates the exact target, the legacy six-file Knowledge roster, and generated outputs before Return Desk replay or candidate scoring. It records visible output controls and explicit per-file direct-acquisition outcomes separately from acquired bytes, never infers `no_download_event` from absence alone, validates the complete original-response compiler block and every container/member identity before local reconstruction, and preserves three independent outcomes: `candidate_failed`, `trial_invalid_controller`, and `transport_identity_unresolved`. Parity may recover exactly one content-faulted data shard only when its metadata and expected ASCII Base64 text length are intact and all other data plus parity are valid; the controller then reruns every aggregate, container, member, and topology check. Aligned-quartet omission, metadata mutation, multiple bad data, or bad data plus bad parity remains unrecoverable. Valid data with only exact-length bad parity records `parity_degraded_not_used`. This controller is not invoked by the compact public GPT.

The frozen-suite checker independently revalidates each trial's manifest-bound candidate snapshot and raw evidence, enforces fresh Preview-session identities and the exact `C001` through `C039` order, and encodes the explicitly authorized three-repair/four-complete-suite release ceiling without allowing controller or transport states to rescue a substantive candidate contradiction.

A pre-freeze synthetic audit found that the two official-status cases intentionally have no scientific verdict, while the prior checker required one for every case. The corrected score-result v2 contract makes every generated case explicit: scientific cases require a nonempty allowed projection, exact claim/verdict mappings are enforced where frozen, and status-only cases require `{}` with no scientific verdict. A real omission or invented verdict is `candidate_failed`; a forged scoring mode or derived flag is `trial_invalid_controller`.

## Audit Return Desk and public interface

Alpha.8 adds:

- matching Python and browser-local inspectors for the non-admissive `audit-return-v0.1` envelope;
- strict JSON, artifact, source, evidence, execution, receipt, gate, obligation, and summary-projection checks;
- an accessible English/Japanese Pages interface and deterministic localization freshness checks;
- five deterministic public-GPT Knowledge files and a 12-case compact Preview gate, while preserving the former 39-case artifact suite as superseded history;
- exact package, release, privacy, research-packet, Null-Discrimination, and reproducible-build gates.

## Preserved R01 negative result

The alpha.8.dev1 R01 induction trial passed mathematically but failed execution/representation consistency. Its original Return Desk replay was independently controller-incomplete, strict downstream Base64 decoding reproduced the exported payload exactly, and unavailable original download bytes did not establish browser or download corruption. The [forensic addendum](docs/R01_FORENSIC_ADDENDUM.md) preserves those facts without rewriting the original evidence.

The first alpha.8 D01 development preflight then exposed the same missing runtime-reachable finalization boundary and a separate raw-controller provenance defect. It is preserved as `trial_invalid_controller`, `not_scored`, and `transport_identity_unresolved`; its independently captured artifact contradictions informed one consolidated repair but are not relabeled as a scored result. The [preflight repair addendum](docs/ALPHA8_PREFLIGHT_REPAIR_ADDENDUM.md) records the superseded freeze and exact boundary.

A later repaired-candidate D01 response was also preserved but not scored. Before D02 or the counted suite, the all-case controller audit found the status-only oracle defect, so that development snapshot was superseded and the package, local gates, editor binding, and both preflights were required to restart. No generated artifact bytes, controller result, candidate result, or download-byte identity was inferred from unavailable evidence.

The next frozen D01 restart produced one invalid-controller attempt followed by
one permitted same-candidate retry. The retry was controller-valid and
candidate-failed: its report wrapper's declared size/hash contradicted its
strictly decoded payload, and its return labeled an unexecuted empirical test
`not_applicable`. The mathematics still passed and unavailable download-button
bytes remained unresolved. The one authorized preflight repair therefore made
the existing compiler own the complete execution ledger/report projection and
made the fallback invoke the existing one-file fresh-read exporter literally;
it did not relax any candidate, controller, transport, Return Desk, fixture,
oracle, rubric, or promotion boundary.

The subsequent r10 candidate passed D01 at 20/20 but did not pass D02. D02
visibly exposed all five declared output controls, while no original button
bytes were acquired. Its unbounded report fallback was surfaced as another
downloadable wrapper file and the following return fallback was blank. The
negative result is preserved without calling unavailable bytes corrupt or
pretending the counted suite ran. The fixed-size chunk transport repairs that
generic response-size assumption; it does not weaken the D02 artifact gate.

The later r23 D01 run showed that the literal bounded fallback and Data Analysis
invocation worked: `audit_request.txt` and `proof_reconstruction.md`
reconstructed exactly. The three public paths created by the compiler no
longer satisfied its regular/non-linked check on later turns, so the
controller-valid trial remained `candidate_failed` with unresolved transport
identity. The compiler v5 snapshot repair changes only that lifecycle source.
It neither follows public links nor calls unavailable button bytes corrupt.

The following live compiler-v5 canary then showed that a hidden snapshot
directory itself was not a stable cross-turn source. The exact handled block
established only a symlink, junction, or non-directory parent state; it did not
establish changed bytes or corruption. The canary step is preserved as
`candidate_failed` with `transport_identity_unresolved`, while the enclosing
D01 trial was not completed or scored. Compiler v6 replaces that environmental
assumption with the original-turn container described above. Direct
acquisition remains primary, and valid fallback reconstruction still does not
authenticate unavailable download-button bytes.

The first counted C001 attempt under the old freeze identified by prefix
`2593db7d` is also preserved without collapsing two different failures. The
controller falsely treated an inline compiler-version mention as a second
transport block, so the outer trial remains `trial_invalid_controller`.
Exact-fence replay after that parser repair found that chunk 0 retained its
declared 2,048-byte size but had a different SHA-256 while chunks 1 and 2
matched; the aggregate identity consequently failed too. The candidate
transport is therefore `candidate_failed` beneath the controller-invalid outer
layer, with unavailable download-button identity still
`transport_identity_unresolved`.

That candidate failure consumes the one post-suite repair allowance. The
compiler-v7/transport-v2 parity change, strict controller-record v5 recovery
receipt, and frozen-evaluation protocol v4 are the bounded repair; they do not
alter fixtures, scientific oracles,
scoring, Return Desk negatives, thresholds, or the preserved R01 result. The
old freeze cannot be reused. All local gates and both preflights must pass, a
new exact freeze must be recorded, and the full counted suite must restart from
C001. No passing suite, live update, merge, tag, release, or publication is
claimed here.

## 2026-07-24 D01 control-byte boundary and compiler v8

The next frozen candidate, commit
`0f753a6d61f3e06ca35e95f6c5a3e25bf13c8544` and tree
`977131ac08adab65a91d4eb25123ffd29d5b3079`, passed all 49 local deterministic
gates. Fresh Preview attempt `D01-A01` was nevertheless
`controller_valid` and `candidate_failed`, with
`transport_identity_unresolved`, because artifact validation prohibited
scoring. Exact compiler-v7 transport reconstructed the 13,194-byte
`audit_report.md` and found ASCII form feed (`0x0C`) at zero-based offsets 3032
and 3538. Both occur in contexts indicating intended `\forall`. Ordinary
Python- or JSON-string `\f` escape decoding is the strong explanation, but the
exact model-side construction layer was not preserved and is therefore not
claimed as proven.

The user explicitly authorized one additional consolidated root-cause repair
cycle on 2026-07-24. Compiler v8 changes only the construction and validation
contract: explicit `report_body_lines` must contain no Unicode category `Cc`
characters, compiler-owned LF joins validated lines, and JSON keys and values
must contain no `Cc`, including LF, TAB, and CR. It rejects rather than
silently repairing invalid text. Regression coverage binds the ordinary-string
collisions for `\forall`, `\theta`, `\rho`, and `\nabla` while accepting the
corresponding Unicode mathematics and safely doubled literal backslashes.

This second authorization did not rewrite the historical compiler-v7/C001
failure or parity repair. That artifact-capable candidate subsequently failed
again and was superseded by the compact product scope above. Its cases,
fixtures, controller results, and Return Desk negatives remain preserved as
history; they are not counted toward the new 12-case compact gate.

## 2026-07-24 C004 obligation boundary and compiler v9

The following candidate at commit
`b8461ca7ef4ac44e86e49bd3c4182872062b40ae` and tree
`ab1e2e7e68306f7ba041fe8b1daead50b126ee0c` passed all 49 local gates, both
development preflights at 20/20, and counted C001 through C003 at 20/20.
`C004-A03` was controller-valid but candidate-failed before scoring. Its
machine record correctly preserved x = -1 as a decisive counterexample,
`research_verdict: "refuted"`, the fatal gate at `fail`, and admission at
`fail`; it omitted the open obligation required for every nonpassing gate.
Return Desk therefore blocked it with
`RETURN_UNRESOLVED_GATE_OBLIGATION_OMITTED`.

The user explicitly authorized a third consolidated root-cause repair cycle on
2026-07-24. Compiler v9 validates unique claim, gate, evidence, and obligation
identifiers; pass/nonpass obligation closure; exact bidirectional bindings;
claim-owner and cited-evidence scope; and exact summary projection before any
report, hash, serialization, or transport bytes are derived. It also corrects
the deterministic report projection from nonexistent field `description` to
schema field `statement`.

The compact controller now requires every `fail`, `unrun`, or `conflict` gate
to retain a scoped open obligation. For an exact counterexample, that
obligation is workflow disposition—retire, narrow, or amend the frozen claim
before admission—not scientific uncertainty. The `refuted` verdict and
negative evidence remain unchanged.

No case, fixture, scientific expectation or oracle, scorer, rubric, threshold,
automatic-failure rule, or Return Desk negative changes. The failed freeze is
not reusable. All local gates, both fresh preflights, and the complete counted
suite from C001 must restart before any live Update, push, merge, tag, Release,
or publication.

## Authority and privacy boundary

The Custom GPT is an interpretive research-preview interface. It is not a proof engine, independent replication service, certification system, or deployment authority. The Return Desk checks internal consistency and locally supplied byte bindings; it does not authenticate external execution or scientific truth.

This release adds no GPT Action, hosted verification API, account integration, analytics, or cloud storage. ChatGPT uploads are processed under the user's applicable settings and terms and are not covered by the Pages interface's local-only processing boundary.

The release does not publish to PyPI or Zenodo.
