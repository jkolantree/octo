# Alpha.8 preflight repair addendum

**Date:** 2026-07-23
**Scope:** non-destructive record of the first D01 development preflight and the one consolidated repair it triggered.

## Superseded development freeze

The first D01 preflight used these exact candidate files:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `docs/GPT_FROZEN_CANDIDATE.json` | 28,650 | `7e61983d1a10fbbb442f2ca8259af45d8bab4cc55c77a32e6c520752a37b1f2c` |
| `gpt/GPT_INSTRUCTIONS.md` | 7,497 | `db39e7ce7b6504daa21815c797533932de1e438859d56a18df14fb4cafd53aa4` |
| `gpt/_source/GPT_PROFILE.json` | 25,824 | `e70098cc38d5498d352f595df2206967613de59d36e9464e91c2a2417e7c9811` |

These identities are retained as a superseded development freeze. They are not the final alpha.8 candidate and must not be published.

## Corrected trial classification

The candidate reconstructed the induction correctly. The preserved fallback stream also exposed substantive artifact contradictions, including an `audit_report.md` wrapper that declared 10,179 bytes and SHA-256 `fbd7be69f3f7671c82b070c12065b85cd40764b9c44d7f3f930eb8a4b532aa46`, while its canonical Base64 decoded to 10,179 bytes with SHA-256 `c97de741f38ff670f2ecd3746d8e6fe46296214cccd3d6aa9f79e86a52267a8e`.

The first controller nevertheless preserved its raw wrapper files by JSON reserialization instead of binding the exact browser code-block bytes and complete per-wrapper response. That controller-owned provenance defect makes the formal trial result:

- controller: `trial_invalid_controller`;
- candidate: `not_scored`;
- transport: `transport_identity_unresolved`;
- mathematical reconstruction: passed.

The independent fallback stream remains valid diagnostic evidence for the architectural repair, but it is not promoted into a scored candidate failure after the controller defect was discovered.

## What was and was not established

- The mathematical induction reconstruction passed.
- The independently preserved exported payload contradicted its declared digest and the return/ledger bindings.
- The machine return also contained an execution-output-as-receipt alias, omitted the request from model-reasoning inputs, and used incomplete or reversed output/input rosters.
- Strict downstream Base64 decoding reproduced the exported payload exactly.
- No direct browser download event yielded original download-button bytes.
- Browser corruption, download corruption, and byte identity with unavailable download-button bytes were not established.

## Consolidated repair boundary

The replacement candidate uses one runtime-reachable deterministic compiler to:

1. capture one session-reported runtime;
2. normalize the model-reasoning and Data Analysis execution topology;
3. generate report semantics from the same return object;
4. freeze artifact bytes before deriving hashes and sizes;
5. generate the bound execution-output ledger from final bytes;
6. serialize `audit_return.json` last; and
7. derive any one-file transport wrapper from one freshly read byte value.

The replacement controller binds each fallback prompt, the complete browser response outerHTML, the exact code-block text, the parser input, and the decoded payload. Missing or mutated controller evidence invalidates the trial before scoring. Transport uncertainty cannot rescue a substantive contradiction, and unavailable original bytes remain unresolved rather than being called corrupt.

## Superseded repaired-candidate D01

A later repaired D01 development run used candidate-manifest snapshot
`4397347de00ec876a370e07d57c9f9182e72287f961d743496fbbaa62c06000d`,
Instructions
`0d9239fdd7792a3b3a27d15d0a2301873dc9d3a920ce09b0321a45d25de5be53`,
and evaluation source
`9068dcbfb9e8064c48030cdfbdfcdf175c4a56752b6d9e0b5b3c3d82dd8cb005`.
The complete visible response and exact assistant `outerHTML` were preserved.
Five generated-file controls were visible, but no direct download event exposed
their bytes.

Before D01 could be closed or D02 consumed, a synthetic all-case controller
audit proved that Cases 38 and 39 were impossible to score: both intentionally
test official service and candidate status rather than scientific truth, while
the checker incorrectly required a nonempty scientific-verdict oracle for
every case. The run is therefore `superseded_pre_freeze`, not scored, and makes
no candidate-pass, candidate-failure, or controller-invalid claim for D01.
Unavailable original download bytes remain `transport_identity_unresolved`;
neither byte identity nor corruption was established.

The causal repair makes research-projection applicability explicit. Scientific
cases require a nonempty allowed verdict projection. The two reviewed
status-only cases require the exact empty projection `{}` and prohibit an
invented scientific verdict. A real omission or extra verdict remains
`candidate_failed`; a scorer that forges the frozen mode or derived result is
`trial_invalid_controller`. The package, local gates, editor binding, D01, and
D02 must all restart on the regenerated candidate.

## Controller-valid D01 failure and bounded final repair

The next D01 restart used frozen candidate manifest
`41b4e1a2afb117a6a33cabc037b1142d24d660910ace7f448915464afbc712a5`.
Its first attempt was invalid because the controller did not capture the
candidate-declared output basename. The same candidate was retried once in a
fresh Preview conversation under the frozen invalid-trial rule.

That retry was controller-valid and therefore scoreable. It produced the
following exact outcome:

- controller: `controller_valid`;
- candidate: `candidate_failed`;
- transport: `transport_identity_unresolved`;
- disposition: `candidate_failed`.

The `audit_report.md` fallback wrapper declared 5,749 bytes and SHA-256
`a0964c3b7d98d5a40660fd3a5eb9bcb480c0a55c406f70fea792c69c3457dcd3`;
its strict canonical Base64 decoded to 5,748 bytes with SHA-256
`c7030c11a01658d6b5fdba5a23488411396430f545059f3d27a608f1880c1d44`.
The machine return also recorded the unexecuted `empirical_test` activity as
`not_applicable`, which the unchanged Return Desk correctly rejected. The
mathematical induction reconstruction itself passed. Unavailable
download-button bytes remained unresolved and were not called corrupt.

This valid candidate failure activated the one authorized preflight repair
cycle. The bounded repair does not change a fixture, oracle, rubric, or Return
Desk rule. It makes the standalone compiler own the exact eight-row execution
roster and deterministic report projection before any output identity is
derived, and makes the controller fallback spell out the existing fresh-read
one-file export command. Missing or contradictory execution bindings still
block, wrapper size/hash mismatches remain candidate failures, and the package,
local gates, editor binding, D01, and D02 restart on the regenerated candidate.

## Pushed r10 preflight result and transport repair boundary

The next regenerated candidate used frozen manifest
`765f4a05c2e34c74dfd9555d23fba1844e6d0c14ebe300fb80e98e5ca2cfe2e2`,
Instructions
`322ba066bdfd5810be6744b70ee4b1e25295c034418aff03e9efa741e6a91dcd`,
profile
`eeb1e57cf69790d33ff168498ff0117ce66127a07e7ef4ade7e36a8d2885e9e4`,
and evaluation source
`e1c71255591526ea462939896a52760c4fd799d09ecbee50405bbdaf51648a2e`.
Its exact tested tree was later pushed as commit
`9a9e5b2af545767b96d7cbd8b4b7303430fdf8c9`.

D01 was controller-valid, scored 20/20, and had no automatic failure. D02
correctly reconstructed the supplied induction proof and visibly exposed file
controls for all five declared outputs. The controller acquired none of those
button bytes. Its first whole-file fallback would have required more than
19,900 Base64 characters before JSON overhead for the 14,927-byte report;
ChatGPT exposed a new wrapper-file control instead of the required inline code
block. The following return fallback ended with a blank assistant response.
Required artifact bytes therefore remained unavailable and D02 did not pass.
The counted 39-case suite, live Update, merge, tag, and release were not run.

This evidence does not establish that the visible output controls lacked files,
that their unavailable bytes were corrupt, or that a wrapper-file button had
the same bytes as any local artifact. It establishes that the controller and
candidate transport contract incorrectly assumed an unbounded whole-file
wrapper would remain inline, and that the controller record conflated a visible
output control with an acquired output.

The replacement transport is generic rather than Case-27-specific. Direct
controls remain primary. A fallback uses exact, controller-generated
`export-chunk` commands over a stable-read payload. The compiler compresses the
unchanged payload, emits at most 2,048 decoded transport bytes per indexed
wrapper, and repeats the full payload and compressed-stream identities in every
chunk. The controller separately records visible controls and acquired bytes,
binds every exact prompt, complete response, code block, and parser input,
requires contiguous indices, and reassembles only after all chunk and aggregate
checks pass. Unavailable original download bytes remain
`transport_identity_unresolved`; candidate contradictions and controller
mutations retain their existing fail-closed classifications.

This additional transport repair was expressly authorized after the preserved
r10 stop; it does not retroactively change r10's failed release gate or reset a
counted-suite repair allowance.
