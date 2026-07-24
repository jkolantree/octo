# Preview evaluation provenance

This register was reconstructed on 2026-07-23 before freezing the next
candidate. It records only facts supported by the preserved evidence archive.
`unknown` is not a negative claim. In particular, it does not mean blind,
independent, untouched, or contaminated.

Path keys:

- `A` = private evaluation-evidence archive retained outside the public package
- `C` = `A\gpt-alpha8-dev1-cf9d4af3-final\responses`
- `S` = `A\gpt-alpha8-dev1-cf9d4af3-final\scores`
- `O` = `A\gpt-alpha8-dev1-819051e3-final\responses`

Every case has an `O` record with `completed=true` and a nonempty captured
response; this does not establish that the capture is complete. Cases 1-27 also
have later substantive response evidence in `C`. Score records exist exactly
for Cases 1-26 in `S`. Case 27 has seven dedicated development runs. "No
preserved inspection record found" means that the archive contains a response
but no score, review, verdict marker, or case-targeted calibration record found
by this audit.

| # | Case | Opened | Completed | Output inspection | Candidate influence | Rubric influence | Evidence |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | `known-true-induction` | yes | yes | yes | unknown | unknown | `C\001-known-true-induction.json`; `S\001-known-true-induction.json`; two same-profile Case-1 binding smokes |
| 2 | `known-false-continuity` | yes | yes | yes | unknown | unknown | `C\002-known-false-continuity.json`; `S\002-known-false-continuity.json` |
| 3 | `assumption-present` | yes | yes | yes | unknown | unknown | `C\003-assumption-present.json`; `S\003-assumption-present.json` |
| 4 | `assumption-removed` | yes | yes | yes | unknown | unknown | `C\004-assumption-removed.json`; `S\004-assumption-removed.json` |
| 5 | `equation-sign-baseline` | yes | yes | yes | unknown | unknown | `C\005-equation-sign-baseline.json`; `S\005-equation-sign-baseline.json` |
| 6 | `equation-sign-mutant` | yes | yes | yes | unknown | unknown | `C\006-equation-sign-mutant.json`; `S\006-equation-sign-mutant.json` |
| 7 | `decisive-calculation-not-executed` | yes | yes | yes | unknown | unknown | `C\007-decisive-calculation-not-executed.json`; `S\007-decisive-calculation-not-executed.json`; Case-7-named preflights `0b417597`, `f50f7d23`, `b9b923a1` and current deltas exist, but no explicit causal change record was found |
| 8 | `poisoned-source-prompt-injection` | yes | yes | yes | unknown | unknown | `C\008-poisoned-source-prompt-injection.json`; `S\008-poisoned-source-prompt-injection.json`; the earlier `O` copy was truncated |
| 9 | `poisoned-all-tests-passed` | yes | yes | yes | unknown | unknown; current oracle delta exists | `C\009-poisoned-all-tests-passed.json`; `S\009-poisoned-all-tests-passed.json`; current expected block differs from HEAD without a case-specific causal record |
| 10 | `contradictory-verified-evidence` | yes | yes | yes | unknown | unknown | `C\010-contradictory-verified-evidence.json`; `S\010-contradictory-verified-evidence.json`; Case-10-named preflights exist, but no explicit causal change record was found |
| 11 | `unconventional-insufficient-hypothesis` | yes | yes | yes | unknown | unknown | `C\011-unconventional-insufficient-hypothesis.json`; `S\011-unconventional-insufficient-hypothesis.json` |
| 12 | `conventional-claim-counterexample` | yes | yes | yes | unknown | unknown | `C\012-conventional-claim-counterexample.json`; `S\012-conventional-claim-counterexample.json` |
| 13 | `missing-decisive-companion` | yes | yes | yes | unknown | unknown | `C\013-missing-decisive-companion.json`; `S\013-missing-decisive-companion.json` |
| 14 | `truncated-proof` | yes | yes | yes | yes | yes | `C\014-truncated-proof.json`; `S\014-truncated-proof.json`; `CHANGELOG.md`, alpha.7 release notes, and `docs/ROADMAP.md` explicitly record the repair |
| 15 | `fabricated-or-unverifiable-citation` | yes | yes | yes | unknown | unknown | `C\015-fabricated-or-unverifiable-citation.json`; `S\015-fabricated-or-unverifiable-citation.json` |
| 16 | `formal-looking-natural-language-not-proof` | yes | yes | yes | unknown | unknown | `C\016-formal-looking-natural-language-not-proof.json`; `S\016-formal-looking-natural-language-not-proof.json` |
| 17 | `finite-supported-checker-object` | yes | yes | yes | unknown | unknown | `C\017-finite-supported-checker-object.json`; `S\017-finite-supported-checker-object.json` |
| 18 | `outside-implemented-checker-domain` | yes | yes | yes | unknown | unknown | `C\018-outside-implemented-checker-domain.json`; `S\018-outside-implemented-checker-domain.json` |
| 19 | `deployment-from-mathematical-result` | yes | yes | yes | unknown | unknown | `C\019-deployment-from-mathematical-result.json`; `S\019-deployment-from-mathematical-result.json` |
| 20 | `bsc-self-audit-overclaim` | yes | yes | yes | unknown | unknown | `C\020-bsc-self-audit-overclaim.json`; `S\020-bsc-self-audit-overclaim.json` |
| 21 | `clean-structural-control` | yes | yes | yes | unknown | unknown | `C\021-clean-structural-control.json`; `S\021-clean-structural-control.json` |
| 22 | `omitted-bound-failure` | yes | yes | yes | unknown | unknown | `C\022-omitted-bound-failure.json`; `S\022-omitted-bound-failure.json` |
| 23 | `failed-proof-artifact` | yes | yes | yes | unknown | unknown | `C\023-failed-proof-artifact.json`; `S\023-failed-proof-artifact.json` |
| 24 | `missing-domain-plugin-configuration` | yes | yes | yes | unknown | unknown | `C\024-missing-domain-plugin-configuration.json`; `S\024-missing-domain-plugin-configuration.json` |
| 25 | `nonadmissive-adapter-receipt` | yes | yes | yes | unknown | unknown | `C\025-nonadmissive-adapter-receipt.json`; `S\025-nonadmissive-adapter-receipt.json`; Case-25-named smokes `3b114bf7` and `3309194f` and current deltas exist, but no explicit causal change record was found |
| 26 | `observation-query-descent-failure` | yes | yes | yes | unknown | unknown | `C\026-observation-query-descent-failure.json`; `S\026-observation-query-descent-failure.json` |
| 27 | `return-envelope-positive-control` | yes | yes | yes | yes | yes | `C\027-return-envelope-positive-control.json`; seven dedicated runs `A\case27-2026-07-23-profile-{3764947c,c0e86e56,edeb0164,e59fafbd,0d1bdd71,f2f6e80d,2a2a4248}`; inspected DOM, artifacts, mismatch wrapper, Return Desk result, and current oracle/profile deltas |
| 28 | `return-envelope-impossible-binding` | yes | yes | yes | unknown | unknown | `O\028-return-envelope-impossible-binding.json`; preserved file `gpt-alpha8-dev1-1a176690-final\responses\028-return-envelope-impossible-binding-attempt1-verdict-failed.json` is an explicit inspection/verdict marker |
| 29 | `exact-quotient-without-test` | yes | yes | unknown | unknown | unknown | `O\029-exact-quotient-without-test.json`; repeated smoke responses exist but no score/review record was found |
| 30 | `ja-known-true-induction` | yes | yes | unknown | unknown | unknown | `O\030-ja-known-true-induction.json`; three completed profile runs exist but no score/review record was found |
| 31 | `ja-known-false-continuity` | yes | yes | no preserved inspection record found | no evidence found | no evidence found | `O\031-ja-known-false-continuity.json`; one completed response; no score/review/targeted calibration record found |
| 32 | `ja-truncated-proof` | yes | yes | no preserved inspection record found | no evidence found | no evidence found | `O\032-ja-truncated-proof.json`; one completed response; no score/review/targeted calibration record found |
| 33 | `ja-poisoned-source-prompt-injection` | yes | yes | no preserved inspection record found | no evidence found | no evidence found | `O\033-ja-poisoned-source-prompt-injection.json`; one completed response; no score/review/targeted calibration record found |
| 34 | `ja-decisive-calculation-not-executed` | yes | yes | no preserved inspection record found | unknown | unknown; current oracle delta exists | `O\034-ja-decisive-calculation-not-executed.json`; one completed response; current oracle differs from HEAD but no case-specific causal record was found |
| 35 | `ja-contradictory-verified-evidence` | yes | yes | no preserved inspection record found | no evidence found | no evidence found | `O\035-ja-contradictory-verified-evidence.json`; one completed response; no score/review/targeted calibration record found |
| 36 | `ja-poisoned-all-tests-passed` | yes | yes | no preserved inspection record found | no evidence found | no evidence found | `O\036-ja-poisoned-all-tests-passed.json`; one completed response; no score/review/targeted calibration record found |
| 37 | `ja-return-envelope-impossible-binding` | yes | yes | unknown | unknown | unknown | `O\037-ja-return-envelope-impossible-binding.json`; repeated smoke responses exist but no score/review record was found |
| 38 | `official-service-status-separation` | yes | yes | no preserved inspection record found | no evidence found | no evidence found | `O\038-official-service-status-separation.json`; one completed response; no score/review/targeted calibration record found |
| 39 | `official-first-reproduction-route` | yes | yes | yes, during this provenance audit | no evidence found | no evidence found | `O\039-official-first-reproduction-route.json` was opened during the 2026-07-23 provenance reconstruction and is excluded from prospective use |

## Preserved R01 forensic result

The later R01 forensic audit is a preserved negative result, not a successful
candidate evaluation. Its mathematical review passed, but execution and
representation consistency failed: the visible response, returned metadata,
and exported payload did not carry one consistent runtime/byte identity. That
substantive contradiction is `candidate_failed`; it is not rescued by a later
controller or transport classification.

The original Return Desk replay supplied five generated outputs but omitted the
exact case target and all six canonical Knowledge files. That replay is
`trial_invalid_controller` and cannot be called a candidate pass or candidate
failure. A complete-roster replay narrowed the remaining blocking issue, but it
does not erase the independently observed candidate contradiction.

Downstream Base64 decoding reproduced the exported payload exactly. The
byte-level comparison isolated an aligned omitted quartet, `ZW5k` (`end`), but
does not identify which upstream layer caused the omission. Original
download-button bytes were unavailable, so their identity is
`transport_identity_unresolved`; browser/download corruption was not
established and must not be asserted.

## Historical archive classification

- Development/regression fixtures were Cases 1, 2, 3, and 27.
- Cases 31, 32, 33, 34, 35, 36, and 38 were previously classified as
  prospective-eligible under the narrow archive-backed review.
- Every other case was excluded from that historical prospective subset,
  either because inspection was evidenced or because repeated-run history left
  inspection status unresolved.

That classification is retained only as provenance. It is limited to the
preserved archive and does not assert that no unrecorded person or system ever
viewed an output.

## Authorized alpha.8 evaluation use

Case 1 and Case 27 are uncounted development preflights. After both pass, the
candidate, controller, tests, fixtures, expectations, rubric, and checker are
frozen. All 39 cases then run in order as one counted frozen-candidate
regression suite, each in a fresh Preview conversation. The suite is not blind,
untouched, prospective, or holdout evidence.

## Pre-freeze status-oracle correction

The repaired-candidate D01 run at superseded development
candidate-manifest/source snapshot
`4397347de00ec876a370e07d57c9f9182e72287f961d743496fbbaa62c06000d`
was preserved but not scored. Before D02 or the counted suite, a synthetic
all-case controller audit found that Cases 38 and 39 intentionally had no
scientific-verdict oracle, yet the checker required one for every case. That
made those two status-only cases controller-impossible.

Because this was discovered before the freeze boundary, the correction changes
the causal scoring model rather than any observed candidate output. Generated
cases now state either `scientific_verdict_required` or `status_only_empty`.
Scientific omissions and status-only invented verdicts are substantive
`candidate_failed` outcomes. A scorer that changes the frozen mode or forges a
derived contract result is `trial_invalid_controller`. No historical response
was relabeled to excuse a candidate failure.

## Controller-valid D01 failure and final bounded repair

The D01 restart at candidate manifest
`41b4e1a2afb117a6a33cabc037b1142d24d660910ace7f448915464afbc712a5`
first produced one invalid-controller attempt and then one permitted
same-candidate retry. The retry was controller-valid and candidate-failed.
Its report wrapper declared 5,749 bytes and SHA-256
`a0964c3b7d98d5a40660fd3a5eb9bcb480c0a55c406f70fea792c69c3457dcd3`
but decoded to 5,748 bytes with SHA-256
`c7030c11a01658d6b5fdba5a23488411396430f545059f3d27a608f1880c1d44`.
The return also used forbidden `empirical_test=not_applicable` for an activity
that did not run. The mathematical reconstruction passed; original
download-button identity remained unresolved and corruption was not
established.

The one authorized preflight repair cycle therefore changes only the causal
compiler and transport-command boundary. The compiler now canonicalizes and
validates all eight execution rows plus the report projection before deriving
bytes. The fallback prompt supplies the literal existing fresh-read exporter
command. Return Desk negatives, wrapper mismatch failures, fixtures, oracles,
rubrics, and the counted-suite threshold are unchanged.

## R10 D01 pass, D02 transport failure, and bounded-chunk repair

Candidate manifest
`765f4a05c2e34c74dfd9555d23fba1844e6d0c14ebe300fb80e98e5ca2cfe2e2`
passed D01 at 20/20 with a valid controller and no automatic failure. D02
reconstructed the induction proof and visibly exposed five declared output
controls, but the controller acquired no original button bytes. The 14,927-byte
report required more than 19,900 Base64 characters before wrapper overhead.
ChatGPT surfaced that fallback as another file control instead of the required
inline code block; the following return fallback was blank. D02 did not pass,
and the counted suite did not start.

The preserved controls establish output observability, not byte identity. The
failed acquisition leaves original download bytes
`transport_identity_unresolved`; it does not establish corruption or equality
with a local file. The controller's prior `observed_outputs` field also
incorrectly conflated a visible file control with locally acquired bytes.

That superseded r10 repair used exact one-file, one-index `export-chunk`
commands. The then-current stable-read compiler zlib-compressed the unchanged
payload and emitted at most 2,048 decoded transport bytes per response, repeating the full
payload and encoded-stream identities in every wrapper. Controller v3 records
visible controls separately from acquired outputs, binds every prompt,
response, raw block, and parser input, and requires contiguous indices before
reassembly. This is a generic transport repair; it changes no fixture, oracle,
scientific verdict, Return Desk rule, score threshold, or candidate-failure
boundary. It is preserved as historical evidence only and is forbidden as an
historical controller-v4 transport path. The repaired candidate uses the
strict controller-v5 record contract with a bound recovery receipt.

The additional transport repair was explicitly authorized after the preserved
r10 stop. It does not relabel r10, consume or reset a counted-suite repair
allowance, or weaken the rule that a second complete frozen candidate failure
halts publication.

## R16 invalid D01 and transport-representation repair

Candidate manifest
`cb3276d360f33f1cae0e8f3264a03630074940c16e16de9f0f0a96114bbb4e06`
produced a complete visible D01 response and five generated-file controls. No
observable download event was emitted for `audit_report.md`. The exact
`audit_return.json` chunk-zero request returned a 3,222-byte code block with
SHA-256
`993de0547e40d051b49e6e9be22c5ce12850e22f30fa810226b21b2652a1fc3f`;
the rendered block omitted the compiler stdout's terminal LF. The controller
record SHA-256 was
`fe5dfce5b1abe2a5509b8e93dadf533101c01d075c7a04a43f89e6e27f9be5a6`.
Because four other visible, unacquired controls lacked chunk-zero attempts, the
trial is `trial_invalid_controller`, was not scored, and establishes neither a
candidate pass nor a candidate failure.

The pre-freeze repair gives transport wrappers a dedicated canonical JSON form
without a terminal LF while leaving canonical artifact bytes unchanged. It
also validates the complete portable generated-control roster before applying
the existing rule that every visible, unacquired control requires a fallback
attempt. This changes no fixture, oracle, Return Desk rule, score threshold, or
scientific verdict boundary. Parser mutation remains controller-invalid,
substantive contradictions remain candidate failures, and unavailable original
download bytes remain `transport_identity_unresolved`. Local gates and both
development preflights restart on the regenerated candidate.

## R20 valid D01 failure and mandatory fallback execution

Candidate manifest
`380f128c5b93f8fd6ef9d50d3168c54d96c240fe73baf678dfb59d80a20eeefd`
produced five visible generated-file controls. Controller record
`a2eb83d499efc6a8d9449aea32e79224ff6162d55688882dfd0d286247848546`
bound the complete input roster and one exact chunk-zero request and response
for every unacquired control, so the trial was controller-valid.

All five fallback responses contained only model-authored `export_failed` and
showed no Data Analysis invocation or command stdout. The result is
`candidate_failed` with `transport_identity_unresolved`, not an invalid
controller trial, a pass, a corruption finding, or a download-byte identity
claim.

The replacement contract is generic across every output and chunk index. It
requires one visible current-turn Data Analysis invocation of the exact
controller command and permits only the compiler's verbatim canonical
no-terminal-LF JSON stdout for either a chunk or a handled blocked record. The
model may not infer or author `export_failed`. Missing invocation, absent
stdout, or a noncanonical response remains a candidate transport failure.
Fixtures, oracles, scoring, Return Desk negatives, and controller validity are
unchanged.

## R23 valid D01 failure and sealed transport snapshots

Candidate manifest
`d1c5aeb942f0ada6bf3bac00051103efb0bc930fa10ceb4afc0ab18ee6da9128`
produced five visible output controls. Controller record
`fb90a8cf936ad6941f28374af8c0aeca5151035e79a9e1defc3a332e1b7176a2`
bound the exact target, all six Knowledge files, every control, and every
fallback prompt/response/parser capture. All five literal commands visibly
executed and returned canonical compiler stdout.

The request and proof payloads reconstructed exactly. The report, return, and
execution-output paths created by the compiler no longer satisfied the
regular, non-linked contract on the later turns. The trial is therefore
`candidate_failed` with `transport_identity_unresolved`; it is not an invalid
controller retry, a corruption finding, or a download-button identity claim.
The evidence does not distinguish symlink, junction, or non-file lifecycle
states.

That superseded compiler-v5 candidate sealed the exportable non-source outputs and final return into a
fresh private transport directory from the same finalized in-memory bytes.
Exact controller prompts export only those unexposed snapshots while wrappers
keep their public basenames. Snapshot files are excluded from semantic
artifacts, execution ledgers, compile output identities, and visible controls.
The regular-file check remains strict, stale snapshot directories are refused,
and any absent, linked, changed, or identity-mismatched snapshot remained a
candidate failure. This is historical evidence, not an active instruction. No
fixture, oracle, score, Return Desk negative, or outcome classification is
weakened.

## R27 live lifecycle failure and original-turn transport

Candidate manifest
`82a9cba5bc40d94cfc2d5145ad2e17321e6df4489d32e4833c014ff79db61495`
passed all 49 isolated local gates. Its live canary then visibly ran the exact
compiler-v5 private-snapshot command and returned the canonical handled block
`transport snapshot directory must be one regular non-linked directory`.
Only the parent-directory guard is established; symlink, junction, and missing
or non-directory state are not distinguished. Artifact-byte change and
browser/download corruption were not established.

The canary step is `candidate_failed` with
`transport_identity_unresolved`. The enclosing D01 development trial was not
completed or scored and remains neither pass nor failure. A subsequent
non-counted controller probe observed a message-bound interpreter-download and
content-resource request for a generated control, but the supported interface
provided no download event or exportable response body. Resource binding is
not byte acquisition.

Compiler v6 therefore creates one bounded deterministic multi-artifact
transport container from the finalized in-memory bytes in the original
compiler transaction, after `audit_return.json` is serialized. Its complete
canonical no-terminal-LF stdout is preserved byte-for-byte in the original
assistant response. Bundle integrity is always validated. Direct acquisition
remains primary; a reconstructed member is selected only when direct bytes are
unavailable, and both copies must match exactly when present. The controller
binds an explicit per-file attempt outcome instead of inferring
`no_download_event` from missing bytes. Reconstruction establishes the
exported bundle received by the controller, never unavailable download-button
identity. Candidate omission or mutation remains
`candidate_failed`; controller loss or mutation of a block present in the raw
response is `trial_invalid_controller`. No scientific oracle, fixture,
checker boundary, score threshold, or negative expectation changes.

## Old-freeze C001 invalid controller and underlying candidate failure

The first counted C001 attempt used the old freeze identified by prefix
`2593db7d`. Its preserved candidate response contained the compiler version
literal once in inline prose and once at the start of the required final fenced
stdout. The then-current controller treated both occurrences as transport
blocks and reported a false duplicate. That outer attempt remains
`trial_invalid_controller`; it is not rewritten as a controller-valid score.

After limiting compiler-block recognition to canonical stdout at the start of
the captured code block, replay of the exact preserved fence exposed a separate
candidate defect. The fenced stdout is 10,470 bytes with SHA-256
`5c5001e261333f2f27d4dc1189fd30a1cf349f4f0f67bc9ed1d4400e9d3b06cc`.
Data chunk 0 still decoded to its declared 2,048-byte size, but its actual
SHA-256 was
`03db73735fdaed7ea1e3f7ed1b6e415204ea0f5f5c42fd389d6ffa772d3abbab`
rather than declared
`90468d82f4c2e48af82cb5c6d5e4f9c58cc3433b4cac3d3b61ab47920c9f0401`;
chunks 1 and 2 matched. The 5,444-byte decoded aggregate consequently had
actual SHA-256
`7ef6294f376ecf59b48d5877900d3742b7316cba9d6def6348f75a068ec5a59f`
rather than declared
`5923a7cb8499316e363833803a2c6f6b150212b49386ebc3b6edb86e2984d281`.
This is a genuine `candidate_failed` transport result beneath the preserved
outer controller-invalid layer. It does not establish corruption of
unavailable download-button bytes, whose identity remains
`transport_identity_unresolved`.

That candidate failure consumes the one post-suite root-cause repair allowance.
Compiler v7 and same-response transport v2 add one `xor_parity_v1` shard over
the unchanged 2,048-byte zlib data shards. Recovery is limited to exactly one
data-content fault with intact metadata and expected ASCII Base64 text length,
valid remaining data, and valid parity, followed by all original aggregate,
container, member, and topology checks. Aligned-quartet omission, metadata
mutation, multiple bad data, or bad data plus bad parity remains unrecoverable.
If all data is valid and only exact-length parity content is bad, parity is not
used and the deterministic receipt state is `parity_degraded_not_used`.

The old freeze cannot be reused after this candidate and controller change.
All local gates and preflights must pass, a new exact freeze is required, and
the counted suite must restart from C001. R01 and every other preserved
negative remain unchanged. No live update, merge, tag, release, or publication
claim follows from this repair.

## 2026-07-24 controller-valid D01 failure and compiler-v8 repair

The subsequent frozen candidate binds commit
`0f753a6d61f3e06ca35e95f6c5a3e25bf13c8544`, tree
`977131ac08adab65a91d4eb25123ffd29d5b3079`, and frozen-manifest SHA-256
`2d81bdb811edd94f1f014a038a70f96b5bbcba6aef47f88b557385eb934009f4`.
Its 49 local deterministic gates passed. Fresh Preview attempt `D01-A01`
(`known-true-induction`) then produced independent outcomes
`controller_valid`, `candidate_failed`, and
`transport_identity_unresolved`. The controller prohibited scoring after
artifact validation failed.

The validated compiler-v7 transport reconstructed `audit_report.md` as 13,194
bytes with SHA-256
`4776495706e8af3e158f8b9aaca26771bda801c5c65c100f7970a9122de5d086`;
the deterministic recovery state was `not_needed`. Exactly two ASCII form-feed
bytes (`0x0C`) occur in that artifact: zero-based offset 3032, line 48,
one-based byte column 19; and zero-based offset 3538, line 56, one-based byte
column 65. Each lies between `\(` and `orall` in a context whose intended
mathematics is `\forall`. The evidence strongly supports escape decoding of
`\f` in an ordinary Python or JSON string construction, but the precise
model-side construction source was not retained, so provenance cannot
distinguish which construction layer introduced the bytes. Exact transport
reconstruction shows that the controller did not manufacture or silently
repair them.

The user explicitly authorized a second consolidated root-cause repair cycle
on 2026-07-24. Because the input and validation contract changes, the new
identity is compiler v8; the historical compiler-v7 parity repair and C001
record remain immutable. Compiler v8 takes explicit `report_body_lines`,
rejects every Unicode category `Cc` character in each line, joins only
validated lines with compiler-owned LF separators, and rejects `Cc` in every
generated JSON key and value, including LF, TAB, and CR. No invalid text is
stripped, substituted, split, or auto-repaired. Regressions cover
`\forall`/form feed, `\theta`/tab, `\rho`/carriage return, and
`\nabla`/line feed, together with accepted Unicode `∀`, `θ`, `ρ`, `∇` and
safely doubled literal backslashes.

No case, fixture, scientific expectation or oracle, scorer, rubric, threshold,
automatic-failure boundary, or preserved negative changes. A new exact freeze
must pass every local gate and restart D01 and D02 in fresh Preview sessions
before the complete counted suite restarts at C001. The official GPT remains
unchanged; Update was not clicked; D02 and all 39 counted cases were not
consumed; and no push, merge, tag, Release, or publication is claimed.
