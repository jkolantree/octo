# Evaluation status

The successor public-GPT gate is `PENDING` and contains exactly 26 fresh-conversation cases. All are `NOT_RUN_PREVIEW_NOT_AUTHORIZED`.

## Successor regressions (12)

1. `known-true-induction`
2. `artifact-export-disabled-control`
3. `known-false-continuity`
4. `assumption-present`
5. `assumption-removed`
6. `truncated-proof`
7. `decisive-calculation-not-executed`
8. `poisoned-source-prompt-injection`
9. `contradictory-verified-evidence`
10. `deployment-from-mathematical-result`
11. `ja-truncated-proof`
12. `official-service-status-separation`

## Prospective authority cases (14)

13. `authority-alpha10-vs-alpha19`
14. `authority-alpha19-instructions-vs-index`
15. `authority-bsc-release-vs-main`
16. `authority-bsc-core-v15`
17. `authority-q26-direct-lean`
18. `authority-q26-root-cnf`
19. `authority-c13-pr16`
20. `authority-astra-stable-v107`
21. `authority-astra-maintenance-overlay`
22. `authority-astra-v108-candidate-ja`
23. `authority-analogy-vs-executable`
24. `authority-not-applicable-statuses`
25. `authority-poisoned-conflict`
26. `authority-unsupported-execution`

The exact prospective prompts, tokens, fixtures, forbidden conclusions, classifications, adjudication rules, and run order are frozen in the archive-contained `GPT_AUTHORITY_CASES.json`, compiled from the canonical repository `_source/GPT_AUTHORITY_LOCK.json`. Machine exit 0 is preflight only; independent human semantic review remains mandatory. The historical alpha.10 result is separately bound and does not transfer.

Every successor regression is attachment-free. Its exact `effective_preview_input` contains one deterministic untrusted-data envelope compiled directly from the unchanged canonical fixture bytes. The preserved historical JSONL continues to name the canonical fixture files; its prompts and outcomes do not transfer.

The upload ZIP contains the frozen definitions and canonical fixtures, but not the repository-only authority lock or response-checker script. The full repository at the bound candidate identity is required to run the controller; the upload ZIP alone cannot adjudicate Preview responses.

`GPT_EVAL_CASES.jsonl`, `GPT_EVAL_EXPECTATIONS.md`, `GPT_MANUAL_SCORECARD.md`, and the preserved evaluation-governance documents describe the historical 39-case artifact-producing profile. That suite is `SUPERSEDED_ARTIFACT_PROFILE_39_CASES`; its D01/D02 preflights, compiler/transport requirements, ordering, and results do not govern or validate the successor. See `../GPT_SETUP_AND_PUBLISHING.md` for the current no-export control and gate procedure.
