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

## R16 invalid D01 and transport-representation repair

The next D01 development run used candidate manifest
`cb3276d360f33f1cae0e8f3264a03630074940c16e16de9f0f0a96114bbb4e06`,
Instructions
`6373f4f0c556a491557d4cd1d823c6100a457ed748c5889796b5e309c8e31168`,
profile
`d1a9eff5ed8d759b7a13f497b90dccabfc0271ba13fda334a024ba90e74ec010`,
and evaluation source
`24c4dd2960d1a7239ea08505a6ce52fdb4df29716280221b48dffe5ad075c4c5`.
The complete visible mathematical response and assistant `outerHTML` were
preserved. Five generated-file controls were visible. Clicking
`audit_report.md` emitted no observable download event.

The exact chunk-zero fallback for `audit_return.json` returned a 3,222-byte
JSON code block with SHA-256
`993de0547e40d051b49e6e9be22c5ce12850e22f30fa810226b21b2652a1fc3f`.
It declared a 7,055-byte payload with SHA-256
`fbfdcbb2230102eab2bb0cd15461dfe1dfe79f9633545c89abfdecee9474c5bc`,
but the rendered code block omitted the compiler's required final LF. The
controller record had SHA-256
`fe5dfce5b1abe2a5509b8e93dadf533101c01d075c7a04a43f89e6e27f9be5a6`.
Because the controller had not yet attempted fallback for the other four
visible, unacquired controls, the preserved trial is
`trial_invalid_controller` and was not scored. It makes no candidate-pass or
candidate-failure claim.

The pre-freeze repair changes the shared representation boundary rather than a
case string, fixture, oracle, rubric, or verdict. Compiler transport wrappers
now have a transport-specific canonical JSON form with no terminal LF, so the
literal command stdout and the rendered code block can remain byte-identical;
canonical JSON artifacts retain their existing final LF. Controller validation
compares the recorded roster with every portable generated-file control in the
bound response and still requires a chunk-zero attempt for every visible,
unacquired output. Parser mutation remains invalid, candidate contradictions
remain candidate failures, and unavailable download-button bytes remain
`transport_identity_unresolved`. The package, all local gates, D01, and D02
restart on the regenerated candidate.

## R20 controller-valid D01 and mandatory-invocation repair

The next D01 run used frozen candidate manifest
`380f128c5b93f8fd6ef9d50d3168c54d96c240fe73baf678dfb59d80a20eeefd`.
The controller record had SHA-256
`a2eb83d499efc6a8d9449aea32e79224ff6162d55688882dfd0d286247848546`.
It bound the exact target, all six Knowledge files, all five visible generated
file controls, and one exact chunk-zero fallback prompt and complete response
for each unacquired control. The controller was valid.

Each of the five fallback responses contained only model-authored
`export_failed`. No Data Analysis invocation or command stdout was observed.
The candidate therefore failed while transport identity remained
`transport_identity_unresolved`; no unavailable download-button bytes were
called corrupt. This is not an invalid-controller retry and is not a candidate
pass.

The generic repair removes the prompt language that allowed a model to infer a
failure. Every fallback now requires one visible current-turn Data Analysis
invocation of the exact controller command. The only permitted response is the
compiler's verbatim canonical no-terminal-LF JSON stdout, whether it carries a
chunk or a handled blocked record. Missing invocation or stdout is a candidate
transport failure, and the model may never author or infer `export_failed`.
No fixture, oracle, rubric, score threshold, controller-validity rule, or
transport-identity boundary is relaxed.

## R23 controller-valid D01 and private transport-snapshot repair

The regenerated D01 run used frozen candidate manifest
`d1c5aeb942f0ada6bf3bac00051103efb0bc930fa10ceb4afc0ab18ee6da9128`.
Its controller record had SHA-256
`fb90a8cf936ad6941f28374af8c0aeca5151035e79a9e1defc3a332e1b7176a2`.
All five exact fallback commands visibly ran and returned canonical compiler
stdout, so the prior missing-invocation defect was repaired and the controller
was valid.

`audit_request.txt` and `proof_reconstruction.md` reassembled exactly. The
three paths created by the compiler transaction—`audit_report.md`,
`audit_return.json`, and `chatgpt_data_analysis_output.txt`—instead returned
the compiler's exact handled block because the later-turn paths no longer
satisfied the regular, non-linked file contract. The preserved result is
`candidate_failed` with `transport_identity_unresolved`. It does not establish
which of the compiler's symlink, junction, or non-file predicates applied, and
it does not establish download corruption.

The newly authorized repair changes the lifecycle source, not the acceptance
rule. Compiler v5 derives a private, unexposed transport roster from non-source
artifact roles plus `audit_return.json` and atomically seals exact copies from
the same final in-memory byte objects before reporting compile success. Later
controller prompts run the unchanged bounded `export-chunk` operation against
those private snapshots while every wrapper retains the public artifact
basename. Snapshots never enter `audit_return.artifacts`, the execution ledger,
the compile output roster, or assistant file controls. Public symlinks remain
rejected, original download-button identity remains unresolved when
unavailable, and any missing, changed, linked, or stale private snapshot still
fails the candidate gate.

## R24 protocol-binding closure before Preview

The first clean local-gate snapshot for compiler v5 was commit
`5e5b1d3c742bee101825fd2f69c5a354a64663ae`, tree
`acb32392293f5d141a73bc6a15df50a23952b336`. Gates 00–04 passed. Gate
05 then ran 338 Python tests and stopped on one failure, with four documented
Windows skips: the Return Desk still expected the prior protocol-packet digest
after the sealed-snapshot wording changed the packet bytes.

The actual `BSC_AUDIT_LLM_PACKET.md` SHA-256 was
`d694a2ee46466d9f7eaec3d44d7917322feec53b9c982331d53eb73ab9d948f1`.
That digest is now propagated through the Return Desk constant, the profile
atom, generated Instructions, and all eight positive/negative return fixtures.
The fixture semantics, verdict boundaries, controller classifications, score
threshold, and negative expectations are unchanged. The failed gate remains
preserved as a candidate-consistency failure caught before any new Preview
trial.

## R25 generated profile projection closure before Preview

The next clean snapshot was commit
`70eac92b6ab14613cd18faef0c48121882dcfea2`, tree
`8e95d1c7810987dc7f1fa8d67bb9c996b8601694`. Gates 00–04 passed and
gate 05 again ran 338 Python tests with four documented Windows skips. The
protocol fixture test now passed; the sole failure was the Pages checker
detecting that `pages/profile.js` still projected the profile identity from
before the protocol digest was updated.

`scripts/build_publication_assets.py` regenerated that public projection from
the canonical profile. No GPT behavior, fixture meaning, checker, oracle,
rubric, verdict boundary, or threshold changed. The failed snapshot is
preserved and is not reused as release evidence.

## R26 localization-binding closure before Preview

The next clean snapshot was commit
`809f8d1f68b3ae204c08d4b53a35a346a22c2cad`, tree
`39403874b5f7f1ced492b3c7defd003c842afd2f`. Gates 00–12 passed,
including 338 Python tests with four documented Windows skips, the Node Return
Desk, Null Discrimination, package, frozen-candidate, Pages, and deterministic
publication checks. Gate 13 then stopped because the localization manifest
still bound the English and Japanese Return Desk files to their pre-repair
hashes.

The manifest now binds the exact current English SHA-256
`be43a059108ae5ecc7b8968bdab97e1b17215726c60045b3d9ac7d5b23d4dce9`
and Japanese SHA-256
`8a4fff173c7b30056b3d5e85e31038a3140b2d5f864b17dd37af840f88c3af67`;
its canonical payload self-hash is regenerated. The translation text and its
beta/native-review caveats are unchanged. The stopped snapshot is preserved
and is not reused as release evidence.

## R27 live cross-turn lifecycle failure and in-turn transport repair

The clean compiler-v5 candidate used manifest
`82a9cba5bc40d94cfc2d5145ad2e17321e6df4489d32e4833c014ff79db61495`,
commit `41d7e6d52fe349d8d2743612f2d24974a026ba06`, and tree
`22c3ca97abf32212d23d93dba4d25f6608eec734`. All 49 isolated local
gates passed, including 338 Python tests with four documented Windows skips.

A fresh live transport canary then ran the exact compiler-v5 `export-chunk`
command for the private `audit_return.json` snapshot. The visible Data
Analysis invocation returned the compiler's exact handled block:
`transport snapshot directory must be one regular non-linked directory`.
That proves only that the parent was a symlink, junction, or not a directory
at the later turn. It does not identify which predicate applied, prove that
the payload existed then, establish changed bytes, or establish corruption.
The canary step is `candidate_failed` with
`transport_identity_unresolved`. The enclosing D01 development trial was
deliberately not completed or scored and is neither a candidate pass nor
failure.

A separate non-counted probe confirmed that a generated-file control caused
ChatGPT to request a message-bound interpreter download and content resource,
but the supported controller interface emitted no download event, rejected
export of that response-body asset kind, and wrote no locally observable file.
The resource binding was observable; its response bytes were not. No signed
resource URL, cookie, or private conversation identifier is retained here.

Compiler v6 removes the failed lifecycle assumption. After serializing
`audit_return.json`, the same original compiler transaction derives one
deterministic bounded multi-artifact container directly from the finalized
in-memory output bytes and includes its complete canonical transport envelope
in stdout. The candidate copies that stdout byte-for-byte once in the original
response. The controller tries direct acquisition first and, only when it is
unavailable, reconstructs the already-preserved container without any later
`/mnt/data` path or tool call. Valid fallback bytes still do not authenticate
unavailable download-button bytes. No fixture, oracle, scorer, verdict
boundary, 18/20 threshold, automatic-failure rule, or negative Return Desk
case is weakened.

## Old-freeze C001 layered failure and one-cycle parity repair

The first counted C001 attempt used the old freeze identified by prefix
`2593db7d`. The preserved response mentioned the compiler version once in
inline prose and then contained the required canonical stdout in its final
fenced code block. The old controller mistook the inline occurrence for a
second compiler block. That false-duplicate result is preserved as the outer
`trial_invalid_controller` layer and is not converted into a scored trial.

The corrected block recognizer replayed the exact preserved fence rather than
reserializing it. The fence is 10,470 bytes with SHA-256
`5c5001e261333f2f27d4dc1189fd30a1cf349f4f0f67bc9ed1d4400e9d3b06cc`.
Chunk 0 decoded to its declared 2,048 bytes but had actual SHA-256
`03db73735fdaed7ea1e3f7ed1b6e415204ea0f5f5c42fd389d6ffa772d3abbab`
instead of declared
`90468d82f4c2e48af82cb5c6d5e4f9c58cc3433b4cac3d3b61ab47920c9f0401`.
Chunks 1 and 2 matched. The 5,444-byte decoded aggregate therefore had actual
SHA-256
`7ef6294f376ecf59b48d5877900d3742b7316cba9d6def6348f75a068ec5a59f`
instead of declared
`5923a7cb8499316e363833803a2c6f6b150212b49386ebc3b6edb86e2984d281`.
The completed candidate response thus contains a genuine
`candidate_failed` transport result beneath the controller-invalid outer
layer. Neither layer establishes the identity or corruption of unavailable
download-button bytes; that axis remains `transport_identity_unresolved`.

This counted-suite candidate failure consumes the single post-suite
root-cause-repair allowance. Compiler v7 keeps the 2,048-byte zlib data shards,
same-response transport v2 adds one `xor_parity_v1` shard, and controller-record
v5 binds the deterministic recovery receipt. The parity shard is defined as the
bytewise XOR of every data shard padded with zero bytes to the maximum width.
The controller may recover exactly one content-faulted data shard only when
its metadata and expected ASCII Base64 text length are intact and every other
data shard and parity are valid. It then reruns every aggregate, container,
member, and topology check. Aligned-quartet omission, metadata mutation,
multiple bad data, or bad data plus bad parity remains unrecoverable. Valid
data with only exact-length bad parity is accepted without using parity and
records deterministic state `parity_degraded_not_used`.

Because the candidate and controller changed, the old freeze is not reusable.
All local gates and both preflights must pass again, a new exact freeze is
required, and the complete counted suite must restart at C001. R01 and every
other preserved negative remain unchanged. This repair is not evidence of a
passing suite, live binding, merge, tag, release, or publication.
