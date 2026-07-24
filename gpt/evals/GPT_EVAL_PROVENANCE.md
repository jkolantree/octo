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
