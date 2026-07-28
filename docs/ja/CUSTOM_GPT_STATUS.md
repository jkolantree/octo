# Official Custom GPT status

> **日本語ベータ版**: この文書は [`docs/CUSTOM_GPT_STATUS.md`](../CUSTOM_GPT_STATUS.md) の参考訳です。母語話者による用語レビューは未完了です。英語版が規範です。SHA-256、commit/tree/tag、URL、filename、command、status/verdict/gate/finding token、JSON/schema/rule ID は原文どおりで、翻訳・正規化しません。

official [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) は build/link-share 済みの research preview です。repository package は、その reproducible configuration/evaluation source と current update candidate を提供します。誰でも configuration を inspect/reproduce でき、official status を示唆しない independent fork を作成できます。

この page は service availability、configuration identity、Preview validation、source deployment、release identity を分離します。[PUBLICATION_STATUS.json](../PUBLICATION_STATUS.json) は superseded した 2026-07-22 snapshot を historical evidence として保存するもので、current-state feed ではありません。

## Current state

2026-07-28 の alpha.9 update 前に read-only 確認:

| Surface | State | Exact binding または boundary |
|---|---|---|
| Official Custom GPT | **live; alpha.9 update 前に inspected** | owner editor は `Live`、link access、Quick-UX Instructions、5 Knowledge filenames、Web Search on、Data Analysis on、Image Generation off、Action なしを示した |
| Conversation-starter boundary | **editor 6; public 4; alpha.9 source 4** | owner editor は 6 starters を保持し、public page は先頭 4 個のみを render した。alpha.9 はその 4 個を exact public order の complete canonical list とする |
| Exact live/source binding | **post-save verification まで unresolved** | update 前の editor/source starter count は異なる。ChatGPT は indexed Knowledge bytes を independent hash 用に expose しない |
| Complete 12-case Preview evaluation | **この Knowledge-changing candidate に required** | historical evidence から `pass_12_of_12` を infer しない。exact alpha.9 freeze が fresh 12 cases 全件に pass する必要がある |
| Repository release line | **v0.3.0-alpha.9** | exact commit、tree、tag、assets は immutable tag と `RELEASE_MANIFEST.json` に bind される。changed alpha.9 bytes を alpha.8 と label しない |
| Prior GitHub prerelease | **preserved historical release** | [`v0.3.0-alpha.8`](https://github.com/jkolantree/octo/releases/tag/v0.3.0-alpha.8) は commit `c6120093e49c658318553900028761a171dbf47b`、tree `a4f7d89ac2e09f2887797c0c16b6f603a29d27ea` のまま。tag を move しない |
| GitHub release object | **mutable service record** | GitHub は `immutable=false` と報告した。release assets と release-page metadata を intrinsically immutable と表現しない |
| Public Pages | **deployment は separately verified** | [English](https://jkolantree.github.io/octo/) と [Japanese](https://jkolantree.github.io/octo/ja.html) route は Pages deployment 後に merged alpha.9 protocol metadata と一致する必要がある |

availability、targeted regression、source CI は complete Preview validation の代用ではありません。preserved 39-case artifact-profile campaign、D01/D02 preflight、compiler/transport requirements、negative results は historical evidence として残し、compact 12-case gate に restart/splice しません。

## Current compact contract and maintenance boundary

live Instructions は ordinary no-depth claim を Quick に route します。verdict first、250 words 以下、4 short blocks 以下で、materially necessary でない table は使いません。alpha.9 は generated Knowledge projection を同じ contract に reconcile します。

canonical starter list は exactly:

1. Start a 60-second claim audit
2. 60秒で主張を点検する
3. Show a simple example first
4. まず簡単な例を見る

official GPT は引き続き 5 public Knowledge uploads を使います。retired `BSC_EXECUTION_AND_RECEIPTS.md` derivative は standalone repository history です。downloadable machine record、compiler output、Base64、shards、transport、section 10 は public GPT の外に残ります。

prior artifact-profile result は compact profile を validate しません。exact 12-case roster は、将来 `pass_12_of_12` または fully Preview-validated と主張するための gate です。

## Exact trust boundary

GPT は authenticated owner-controlled research-preview interface です。proof engine、certification system、independent replication service、deployment authority ではありません。

- Custom GPT upload は applicable ChatGPT settings/terms の下で処理され、local-only ではない。
- ChatGPT file access/Data Analysis は、checker が実際に走り identified output が保存されない限り versioned BSC Python result ではない。
- Lean/SMT/interval/empirical claim には separately identified supervised execution と admissible evidence が必要。
- fluent report、hash-shaped string、submitted receipt、internally consistent `audit_return.json` は truth、source authenticity、independent replay、deployment permission を確立しない。

## Alpha.8 and alpha.9 boundary

Alpha.8 は `c6120093…` の exact tagged package です。later live/main UX hotfix と alpha.9 maintenance bytes は含みません。tagged release notes の当時の 300-word Quick 記述は historical release evidence として残します。

Alpha.9 は new version、binding record、deterministic release gates、immutable tag を使用します。later changed exact package には another new version/tag が必要です。existing tags と release history を rewrite しません。

## Preserved alpha.7 baseline

immutable `v0.3.0-alpha.7` package は live Update 前に、depth-explicit Preview 27/27 件を 18/20 以上、automatic failure なしで完了しました。保存された score distribution は 20/20 が 18 cases、19/20 が 5、18/20 が 4 です。limitation/deduction は evidence として残り、history を黙って repair しません。

| Alpha.7 artifact | SHA-256 |
|---|---|
| Release package | `855d905b8788059e6c14a7374a82a6510fb0f0a86224a08c292d654b8da574d4` |
| Raw Preview evidence | `f75818ef10c2d9b09239f2149867b7dec3b34880e9cd8681c3dc82ce408add01` |
| JSON scorecard | `b6d9827bcf112af7a1e8c4fff151c6250a70a6b9d064ddab1a1cfd2655b88585` |
| Markdown scorecard | `97c0b82b0c3bd13aa40710fb0982b603aeab4b6fc9a278edb565c9cb14c2cc3e` |

この historical baseline は changed controller、Knowledge set、Builder configuration、evaluation suite へ transfer しません。
