# Documentation

This index separates first use, reference material, governance, and release work. The project is a research preview; begin with the route matching your task.

[日本語ドキュメント](ja/index.md) | [Historical publication snapshot](PUBLICATION_STATUS.json)

## Getting started

1. **Official Custom GPT - direct ChatGPT audit:** the [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) is built and link-shared. The alpha.10 source explicitly routes all four bilingual starter literals while preserving the bounded Quick contract; exact saved-editor, public, and Preview states are observed separately. Uploads are handled through ChatGPT, and the GPT includes no Action or hosted API. See the exact [live/candidate status](CUSTOM_GPT_STATUS.md).
2. **Local browser Packet Builder and Audit Return Desk:** paste or attach material locally in the deployed [English](https://jkolantree.github.io/octo/) or [Japanese](https://jkolantree.github.io/octo/ja.html) interface, then copy or download the versioned packet and separately choose an LLM. The Return Desk locally inspects returned envelopes and selected artifact hashes.
3. **Repository and Python engine - exact checker route:** follow the [Programmer Tutorial](PROGRAMMER_TUTORIAL.md) for versioned schemas, fixtures, finite exact checks, and command output.

Additional starting points:

- [Start Here](../START_HERE.md) - choose human, manual LLM-assisted, or programmer use
- [Human Audit Worksheet](../AUDIT_WORKSHEET.md) - no-code claim audit
- [Example Catalog](../examples/README.md) - expected outcome and limitation of each fixture

## Trust and interpretation

- [Status Model](STATUS_MODEL.md) - research verdict, evidence maturity, execution, deployment, gate, source coverage, and CLI decision
- [Threat Model](THREAT_MODEL.md) - false-pass, leakage, prompt injection, and evidence risks
- [Manifest and Schema](SCHEMA.md) - versioned interchange contract
- [Documentation Contract](DOCUMENTATION.md) - rendering, conclusion typing, privacy, generation, and preservation rules
- [Pseudonymous publication policy](../PRIVACY.md) - identity allowlist and fail-closed privacy gate
- [Errata](../ERRATA.md) - corrections that do not rewrite immutable releases

## Mathematical reference

- [Mathematics](MATHEMATICS.md) - exact definitions and theorem statements
- [Exact Derived Holonomy](DERIVED_HOLONOMY.md) - strict, homotopy, and observation-reduced path comparison
- [Spectral Obstruction and Limit Gates](SPECTRAL_OBSTRUCTIONS.md) - shifted-ladder and bounded-jet prime-block boundaries
- [Proof-carrying Adapters](PROOF_CARRYING_ADAPTERS.md) - non-admissive Lean, SMT, and interval receipt boundary
- [Audit Return Desk](AUDIT_RETURN_DESK.md) - non-admissive returned-envelope, ledger, projection, and local-byte inspection
- [Derived witnessed-descent packet](../research/derived-witnessed-descent/README.md) - preserved notes, reports, provenance, and reproduction limits

## Project operation

- [Roadmap](ROADMAP.md)
- [Sharing and Release Guide](SHARING_GUIDE.md)
- [Custom GPT live-candidate status](CUSTOM_GPT_STATUS.md)
- [Contributing](../CONTRIBUTING.md)
- [Governance](../GOVERNANCE.md)
- [Retired release-operation branches](OPERATIONS_ARCHIVE.md)
- [Security](../SECURITY.md)
- [Code of Conduct](../CODE_OF_CONDUCT.md)
- [Changelog](../CHANGELOG.md)

## LLM use

The [LLM Audit Packet](../BSC_AUDIT_LLM_PACKET.md) is a drafting protocol, not an executable verifier. Read its privacy, prompt-injection, and source-coverage rules before attaching material.

The static [Pages module](../pages/README.md) is the accessible front door to that same canonical packet. Alpha.18 retains the alpha.16 engine and Audit Return Desk, replaces the alpha.17 GitHub-rejected math macro with renderer-safe notation, validates active math macros as well as Markdown structure, and serves the exact return schema linked by the protocol. The independently versioned protocol component remains byte-identical to alpha.13; its committed packet, return schema, and checksum metadata are mechanically checked for drift.

The repository also contains the deterministic package behind the official [Custom GPT](../gpt/README.md). It supports configuration review, reproducible deployments, compatible forks, and verifiable official updates. Direct uploads are processed through ChatGPT and do not inherit the Pages module's local-only boundary. The package includes no GPT Action, hosted checker API, account system, or cloud-storage service. Live availability, exact configuration binding, Preview validation, GitHub release, and Pages deployment are reported as separate states.

The [Audit Return Desk](AUDIT_RETURN_DESK.md) inspects returned model output and receipts without treating fluent output, hash-shaped strings, or submitted receipts as independent checker evidence.

## Release identity

Release documentation names the project **BSC Audit Engine**, maintained under the project identity **J. Tree**. A citation file and archive metadata live at the repository root.

BSC is offered as infrastructure for careful imagination. It permits ambition, but not free authority.
