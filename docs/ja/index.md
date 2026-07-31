# 文書一覧

> **日本語ベータ版**: この文書は [`docs/index.md`](../index.md) の参考訳です。母語話者による用語レビューは未完了です。規範となるのは英語版です。machine vocabulary、JSON keys/enums、rule/schema IDs、verdict/gate/finding tokens、paths、hashes、commands、filenames、quoted source は変更しません。

この一覧は、初回利用、reference、governance、release work を分けています。本 project は research preview です。目的に合う route から始めてください。

[English documentation](../index.md) | [Historical publication snapshot](../PUBLICATION_STATUS.json)

[Translation manifest](TRANSLATION_MANIFEST.json) は、8 組の source/target と 2 つの日本語固有補助資料について exact bytes と staleness を検査します。翻訳品質や母語話者レビューの完了を認証するものではありません。

## はじめる

1. **Official Custom GPT — ChatGPT で直接監査:** [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) は build/link-share 済みです。alpha.10 source は bounded Quick contract を保持しながら 4 個の bilingual starter literal を explicit route します。exact saved-editor、public、Preview states は別に observe します。upload は ChatGPT 経由で処理され、GPT に Action/hosted API はありません。[exact live/candidate status](CUSTOM_GPT_STATUS.md) を参照してください（規範英語: `docs/CUSTOM_GPT_STATUS.md`）。
2. **Local browser Packet Builder と Audit Return Desk:** deployed [English](https://jkolantree.github.io/octo/) または [Japanese](https://jkolantree.github.io/octo/ja.html) interface で material をローカルに paste/attach し、versioned packet を copy/download してから LLM を別途選択します。Return Desk は returned envelope と selected artifact hash をローカル検査します。
3. **Repository と Python engine — exact checker route:** versioned schema、fixture、finite exact check、command output は [Programmer Tutorial](../PROGRAMMER_TUTORIAL.md) に従ってください。

その他の入口:

- [Start Here 日本語](../../START_HERE.ja.md) — 人手、manual LLM-assisted、programmer use を選ぶ（規範英語: `START_HERE.md`）
- [Custom GPT 日本語ガイド](GPT_INTERFACE.md) — official URL、日本語 response、privacy、任意の reproduction/fork route
- [正規トークン日本語用語集](GLOSSARY.md) — machine vocabulary を変更せず日本語で説明する補助資料
- [Human Audit Worksheet](../../AUDIT_WORKSHEET.md) — no-code claim audit
- [Example Catalog](../../examples/README.md) — 各 fixture の expected outcome と limitation

## Trust と解釈

- [Status Model 日本語](STATUS_MODEL.md) — research verdict、evidence maturity、execution、deployment、gate、source coverage、CLI decision（規範英語: `docs/STATUS_MODEL.md`）
- [Threat Model](../THREAT_MODEL.md) — false-pass、leakage、prompt injection、evidence risk
- [Manifest and Schema](../SCHEMA.md) — versioned interchange contract
- [Documentation Contract](../DOCUMENTATION.md) — rendering、conclusion typing、privacy、generation、preservation の規範英語
- [Pseudonymous publication policy](../../PRIVACY.md) — identity allowlist と fail-closed privacy gate
- [Errata](../../ERRATA.md) — immutable release を書き換えない訂正

## 数学リファレンス

- [Mathematics](../MATHEMATICS.md) — exact definition と theorem statement
- [BSC v1.2 Simulation-Evidence Crosswalk](../BSC_V1_2_SIMULATION_CROSSWALK.md) — immutable upstream F10 identity、exact recurrence projection、authority boundary
- [Exact Derived Holonomy](../DERIVED_HOLONOMY.md) — strict/homotopy/observation-reduced path comparison
- [Spectral Obstruction and Limit Gates](../SPECTRAL_OBSTRUCTIONS.md) — shifted-ladder と bounded-jet prime-block boundary
- [Proof-carrying Adapters](../PROOF_CARRYING_ADAPTERS.md) — non-admissive Lean/SMT/interval receipt boundary
- [Audit Return Desk 日本語](AUDIT_RETURN_DESK.md) — non-admissive returned-envelope/ledger/projection/local-byte inspection（規範英語: `docs/AUDIT_RETURN_DESK.md`）
- [Derived witnessed-descent packet](../../research/derived-witnessed-descent/README.md) — 保存された note/report/provenance/reproduction limit

## Project operation

- [Roadmap](../ROADMAP.md)
- [Sharing and Release Guide](../SHARING_GUIDE.md)
- [Custom GPT live status 日本語](CUSTOM_GPT_STATUS.md)（規範英語: `docs/CUSTOM_GPT_STATUS.md`）
- [Contributing](../../CONTRIBUTING.md)
- [Governance](../../GOVERNANCE.md)
- [Retired release-operation branches](../OPERATIONS_ARCHIVE.md)
- [Security](../../SECURITY.md)
- [Code of Conduct](../../CODE_OF_CONDUCT.md)
- [Changelog](../../CHANGELOG.md)

## LLM use

[LLM Audit Packet](../../BSC_AUDIT_LLM_PACKET.md) は drafting protocol であり executable verifier ではありません。material を attach する前に privacy、prompt-injection、source-coverage rules を読んでください。

static [Pages module](../../pages/README.md) は同じ canonical packet への accessible front door です。alpha.20 は renderer-safe documentation と alpha.19 engine schema を保持し、existing affine-bound kernel に bounded BSC v1.2 F10 crosswalk だけを追加します。general simulation validator または deployment authority は追加しません。independently versioned protocol component は alpha.13 と byte-identical のままです。committed protocol、return schema、checksum metadata は mechanically checked for drift です。

repository には official [Custom GPT](../../gpt/README.md) の deterministic package もあります。これは configuration review、reproducible deployment、compatible fork、verifiable official update を支える source です。direct upload は ChatGPT で処理され、Pages module の local-only boundary を継承しません。package に GPT Action、hosted checker API、account system、cloud-storage service はありません。live availability、exact configuration binding、Preview validation、GitHub release、Pages deployment は別々の state として report されます。

[Audit Return Desk](AUDIT_RETURN_DESK.md) は、fluent output、hash 形式の文字列、submitted receipt を independent checker evidence とみなさず returned model output を検査します。

## Release identity

release documentation は project を **BSC Audit Engine**、maintainer identity を **J. Tree** とします。citation file と archive metadata は repository root にあります。

BSC は慎重な想像力のための基盤です。大胆な仮説は許しますが、根拠のない権威は与えません。
