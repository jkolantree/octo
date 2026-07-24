# Official Custom GPT status

> **日本語ベータ版**: この文書は [`docs/CUSTOM_GPT_STATUS.md`](../CUSTOM_GPT_STATUS.md) の参考訳です。母語話者による用語レビューは未完了です。英語版が規範です。SHA-256、commit/tree/tag、URL、filename、command、status/verdict/gate/finding token、JSON/schema/rule ID は原文どおりで、翻訳・正規化しません。

official [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) は build/link-share 済みの research preview です。repository package は、その reproducible configuration/evaluation source と current update candidate を提供します。誰でも configuration を inspect/reproduce でき、official status を示唆しない independent fork を作成できます。

この page は service availability、configuration identity、Preview validation、source deployment、immutable release を意図的に分離します。timestamped machine-readable snapshot は [PUBLICATION_STATUS.json](../PUBLICATION_STATUS.json) にあります。

## Current state

2026-07-22 に確認:

| Surface | State | Exact binding または boundary |
|---|---|---|
| Official Custom GPT | **live** | 上記 public URL。runtime identity smoke は controller `0.3.0-alpha.8.dev0` と Profile SHA-256 `99d6f78d3af21c68ddb6545b034d340e77b73d2f1ffa657120d4147455128b90` を返した |
| Alpha.8.dev0 Preview evaluation | **not completed** | candidate の generated case gate を満たす preserved complete post-update run はない。identity smoke は evaluation ではない |
| Repository `main` | **merged** | commit `1e5c60360d8473e170f828597241dc9ab5844d3b`、tree `f1460fb6e84c11ad363e3c8796ea22a3c2a4fde8` |
| GitHub Actions for that merge | **passed** | exact-audit と Pages publication はともに成功 |
| Public Pages | **deployed** | alpha.8.dev0 が [jkolantree.github.io/octo](https://jkolantree.github.io/octo/) で live |
| Japanese Pages route | **candidate; not deployed** | 予定 `/octo/ja.html` route は `2026-07-22T18:37:44Z` に HTTP 404。post-deploy English/JA/protocol route/metadata smoke が pass するまで live として案内しない |
| Latest GitHub Release | **unchanged** | [`v0.3.0-alpha.7`](https://github.com/jkolantree/octo/releases/tag/v0.3.0-alpha.7)、commit `5ac1b85d4d573d15ce5cf68329443de11428b490` |
| Final alpha.8 release candidate | **pending gates** | `0.3.0-alpha.8`。live Update、merge、tag、release の前に isolated local gates と fresh frozen 12-case compact-profile Preview regression が必要 |

alpha.8.dev0 について確認済みなのは、repository CI と runtime identity smoke です。fresh Preview conversation による complete behavior evaluation は保存されていないため、CI と identity は Preview validation の代用にはなりません。利用可能な service の output も human-review research-preview draft として扱います。

## Next candidate

final `0.3.0-alpha.8` は、service availability と candidate validation を混同せず、日本語 accessibility と exact evidence boundary を強化する release candidate です。この candidate は:

- uploaded Knowledge から mutable service-state claim を除き、現在状態は timestamped repository record に分離する;
- 利用者向けの official URL と、任意の reproduction/fork/update route を明確に分ける;
- canonical machine token を保った Japanese human-facing guidance を追加する;
- official GPT の Knowledge を 5 files にし、`BSC_EXECUTION_AND_RECEIPTS.md` は standalone repository tooling に限定する;
- human-readable duties 1-9 のみを 500/1,200/2,000-word budget 内で返す;
- downloadable machine record、compiler stdout、Base64、shards、transport、section 10 を official GPT では無効化する;
- fresh 12-case compact-profile Preview gate で Japanese behavior と corrected evidence boundary を検証する。

preserved 39-case artifact-profile suite、D01/D02 preflight、compiler/transport results は historical and superseded です。これらは compact candidate を validate せず、12-case gate の代用になりません。

candidate が complete Preview gate を通過し、saved configuration との exact binding が確認されるまで、`0.3.0-alpha.8` を installed、bound、Preview-validated、または released として promote しません。official service の現在の availability は上記 timestamped state と machine-readable snapshot で確認します。

## Exact trust boundary

GPT は authenticated owner-controlled research-preview interface です。proof engine、certification system、independent replication service、deployment authority ではありません。

- Custom GPT upload は applicable ChatGPT settings/terms の下で処理され、local-only ではない。
- ChatGPT file access/Data Analysis は、checker が実際に走り identified output が保存されない限り versioned BSC Python result ではない。
- Lean/SMT/interval/empirical claim には separately identified supervised execution と admissible evidence が必要。
- fluent report、hash-shaped string、submitted receipt、internally consistent `audit_return.json` は truth、source authenticity、independent replay、deployment permission を確立しない。

## Promotion gate for alpha.8

merge、live Update、GitHub release の前に:

1. clean candidate tree から exact package を generate/validate する。
2. Instructions character limit、Profile SHA、Knowledge filenames/hashes、metadata、capabilities、Apps/Actions 不在を verify する。
3. 12 個の compact-profile evaluation case をすべて fresh Builder Preview conversation で exact fixture と exact depth-explicit `preview_prompt` を使って実行する。
4. raw response を各々保存し、generated oracle に対して score する。
5. 各 case に 18/20 以上かつ automatic failure なしを要求する。1 failed case を average で消してはいけない。
6. repository、Pages、localization、privacy、release-integrity、Null-Discrimination checks を実行する。
7. 全 gate pass 後にだけ live GPT を update し、public identity と timestamped status record を再 verify する。

## Preserved alpha.7 baseline

immutable `v0.3.0-alpha.7` package は live Update 前に、depth-explicit Preview 27/27 件を 18/20 以上、automatic failure なしで完了しました。保存された score distribution は 20/20 が 18 cases、19/20 が 5、18/20 が 4 です。limitation/deduction は evidence として残り、history を黙って repair しません。

| Alpha.7 artifact | SHA-256 |
|---|---|
| Release package | `855d905b8788059e6c14a7374a82a6510fb0f0a86224a08c292d654b8da574d4` |
| Raw Preview evidence | `f75818ef10c2d9b09239f2149867b7dec3b34880e9cd8681c3dc82ce408add01` |
| JSON scorecard | `b6d9827bcf112af7a1e8c4fff151c6250a70a6b9d064ddab1a1cfd2655b88585` |
| Markdown scorecard | `97c0b82b0c3bd13aa40710fb0982b603aeab4b6fc9a278edb565c9cb14c2cc3e` |

この historical baseline は changed controller、Knowledge set、Builder configuration、evaluation suite へ transfer しません。
