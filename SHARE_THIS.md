# Public Sharing Copy

Use the final tagged repository URL in place of `<RELEASE_URL>`.

## Short description

BSC Audit Engine is experimental open-source software for making mathematical and scientific claims easier to test, challenge, reproduce, and demote. It checks selected finite structural obligations and returns concrete witnesses when possible. It does not certify arbitrary truth or authorize deployment.

## GitHub or forum post

### Title

An open-source claim-audit tool that preserves counterexamples and hard failure conditions

### Body

I’m releasing an early research preview of BSC Audit Engine.

The basic idea is simple: freeze one claim, type its objects and observation process, state the ordinary baseline, pre-register independent hard gates, and preserve the result when something fails.

The current Python checker supports a narrow exact core:

- rational chain complexes and transport defects;
- path-dependence witnesses;
- finite observation/query descent;
- product-valued fatal gates with explicit conflict states;
- dependency propagation;
- finite atomic-modulus record checks;
- exact propagation of declared affine upper bounds;
- scoped arithmetic and local/global recovery gates.

It is not a truth machine or automated peer reviewer. A no-blocking result means only that the checks actually run found no blocking condition in the supplied artifact.

There are three routes:

1. a human worksheet with no code;
2. an LLM packet that produces a draft audit while treating the target as untrusted evidence;
3. a deterministic local checker for supported JSON artifacts.

The most useful contribution is often a compact counterexample, false-pass report, false-block report, or better kill condition. Negative results are preserved as release artifacts.

Start here: `<RELEASE_URL>`

## Short post

I released an experimental open-source audit engine for scientific and mathematical claims. It freezes scope, separates observation from inference, preserves fatal gates, and returns finite witnesses for the checks it supports. Human, LLM-assisted, and local Python routes are included. It is not a truth certificate. `<RELEASE_URL>`

## Direct message

I’m testing a research-preview claim-audit toolkit. If you have one precise mathematical, scientific, or computational claim, the workflow can separate its proof, evidence, assumptions, observation limits, counterexample searches, and demotion conditions. You do not need to code. Please do not send confidential or identifying material. Would you like to try a small public example?

## Reply: “Is this an AI truth checker?”

No. The LLM route is a drafting protocol with prompt-injection, privacy, and source-coverage rules. The local checker deterministically checks selected finite JSON obligations. Neither route establishes arbitrary scientific truth.

## Reply: “Who chooses the gates?”

Claim authors propose prospective gates, reviewers attack them, and some narrow domain gates are implemented in code. Every gate is visible and versioned. A new fatal gate needs scoped activation, known-answer tests, a minimal witness, false-pass and false-block analysis, and a retirement condition.

## Reply: “What does a green result mean?”

There is intentionally no universal green compliance badge. `no_blocking_findings` means only that the selected checks found no blocking issue. The report must also show checks not run, unresolved evidence, research verdict, and deployment status.

## Reply: “Can I upload a private paper to the LLM route?”

Only if you are authorized to share it with that service. Remove secrets and personal, legal, medical, proprietary, classified, or export-controlled information. For sensitive work, use an approved local process and publish only a sanitized audit packet.

## Stable closing line

BSC is offered as infrastructure for careful imagination. It permits ambition, but not free authority.
