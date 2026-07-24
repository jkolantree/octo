# BSC Audit Engine v0.3.0-alpha.8

Alpha.8 is a public research preview of the BSC Audit Engine and the repository-backed BSC Claim Auditor configuration.

## Root-cause repair

This release replaces model-mediated artifact identity with one acyclic final-byte transaction:

- have the executed compiler capture its own Data Analysis `sys.version` once, reject model-authored overrides, and label the value session-reported rather than independently authenticated;
- finalize request, source, evidence, and report bytes before deriving hashes and sizes;
- generate one bound `chatgpt_data_analysis_output.txt` from that captured value and frozen metadata;
- have the report reference the bound output rather than manually recopying the runtime;
- serialize `audit_return.json` only after every referenced artifact is final;
- canonicalize all eight execution activities and the report-facing execution projection before any report, ledger, hash, or return bytes are derived;
- keep Base64 outside the primary proof path and treat any fallback only as the identity of the exported payload actually received;
- replace unbounded whole-file fallback responses with stable-read, zlib-compressed, fixed-size indexed chunks whose decoded transport payload is capped at 2,048 bytes per response.

The evaluation controller now validates the exact target, all six canonical Knowledge files, and generated outputs before Return Desk replay or candidate scoring. It records visible output controls separately from acquired bytes, validates every chunk prompt/response/parser binding before reassembly, and preserves three independent outcomes: `candidate_failed`, `trial_invalid_controller`, and `transport_identity_unresolved`.

The frozen-suite checker independently revalidates each trial's manifest-bound candidate snapshot and raw evidence, enforces fresh Preview-session identities and the exact `C001` through `C039` order, and encodes the one-repair/two-complete-suite release ceiling without allowing controller or transport states to rescue a substantive candidate contradiction.

A pre-freeze synthetic audit found that the two official-status cases intentionally have no scientific verdict, while the prior checker required one for every case. The corrected score-result v2 contract makes every generated case explicit: scientific cases require a nonempty allowed projection, exact claim/verdict mappings are enforced where frozen, and status-only cases require `{}` with no scientific verdict. A real omission or invented verdict is `candidate_failed`; a forged scoring mode or derived flag is `trial_invalid_controller`.

## Audit Return Desk and public interface

Alpha.8 adds:

- matching Python and browser-local inspectors for the non-admissive `audit-return-v0.1` envelope;
- strict JSON, artifact, source, evidence, execution, receipt, gate, obligation, and summary-projection checks;
- an accessible English/Japanese Pages interface and deterministic localization freshness checks;
- six deterministic Knowledge files and 39 depth-explicit evaluation cases;
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

## Authority and privacy boundary

The Custom GPT is an interpretive research-preview interface. It is not a proof engine, independent replication service, certification system, or deployment authority. The Return Desk checks internal consistency and locally supplied byte bindings; it does not authenticate external execution or scientific truth.

This release adds no GPT Action, hosted verification API, account integration, analytics, or cloud storage. ChatGPT uploads are processed under the user's applicable settings and terms and are not covered by the Pages interface's local-only processing boundary.

The release does not publish to PyPI or Zenodo.
