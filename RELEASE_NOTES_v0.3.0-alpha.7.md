# BSC Audit Engine v0.3.0-alpha.7

Released 2026-07-21 as a public research preview.

## Fail-closed repair

Alpha.7 closes a false-promotion path discovered during the complete alpha.6 Builder Preview evaluation. When decisive submitted proof material is missing or truncated, an auditor-generated completion is now only a proposed repair. It cannot ground a `proven` verdict or close the affected proof obligations.

The correction is bound through:

- the canonical BSC language-model protocol;
- the deterministic Builder-bounded controller;
- the `truncated-proof` expected and forbidden behaviors;
- a dedicated automatic-failure condition;
- package and regression tests.

The Python checker's finite routes and schema authority are unchanged.

## Depth-explicit Preview procedure

Each of the 27 machine-readable evaluation records now contains an exact generated `preview_prompt` that states its validated `audit_depth`. The setup guide and human-readable expectations require the evaluator to attach the exact fixture and send that exact prompt in a fresh Preview conversation. This removes reliance on the controller's default depth.

The package remains deterministic and includes:

- one controller that must fit ChatGPT Builder's 8,000-character Instructions field;
- five ordered Knowledge files;
- public metadata and four conversation starters;
- known-answer, paired-mutation, prompt-injection, missing-execution, conflicting-evidence, missing-source, and poisoned-false-pass cases;
- a manual scorecard, manifest, source bindings, and SHA-256 ledger.

## Preserved alpha.6 negative result

The full alpha.6 draft run was not promoted. Twenty-six cases scored 19-20 with no automatic failure. `truncated-proof` scored 18/20 but incurred an automatic failure after the model supplied the omitted induction completion, declared the theorem `proven`, and said no mathematical obligation remained despite missing Part II and appendices. The live GPT was not updated.

Alpha.7 must still pass all 27 exact depth-explicit cases at 18/20 or better with no automatic failure before the authenticated Builder Update is selected.

## Integrity and authority boundary

This release adds no GPT Action, hosted API, account integration, analytics, cloud storage, proof engine, or deployment authority. ChatGPT uploads are processed under the user's applicable terms and settings and are not local-only. Repository hashes bind package bytes before upload; they do not authenticate ChatGPT's internal Knowledge index or guarantee future model behavior.

A GPT response, hash match, clean structural check, or submitted receipt does not establish external scientific truth, independent replication, proof-assistant execution, or safe deployment. The Custom GPT is an interpretive research-preview interface; the versioned BSC Python checker and external proof tools remain separate execution layers.

## Reproduction and authenticated handoff

From the exact tagged tree:

```bash
python scripts/build_gpt_package.py --check
python scripts/check_gpt_package.py
python scripts/run_tests.py
python scripts/run_null_discrimination.py
python scripts/check_privacy.py --protected-history HEAD
python scripts/build_release.py --output release
```

Then:

1. paste the exact alpha.7 `GPT_INSTRUCTIONS.md`;
2. replace all five Knowledge files with the alpha.7 files in order;
3. recheck metadata, starters, capabilities, absence of Apps and Actions, and sharing;
4. run all 27 exact fixtures with each generated `preview_prompt` in fresh conversations;
5. preserve and score every response;
6. select Update only if every case reaches at least 18/20 with no automatic failure.

The Audit Return Desk remains planned and is not implemented in alpha.7.
