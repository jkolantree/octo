# Official Custom GPT status

> **日本語ベータ版**: この文書は [`docs/CUSTOM_GPT_STATUS.md`](../CUSTOM_GPT_STATUS.md) の参考訳です。母語話者による用語レビューは未完了です。英語版が規範です。SHA-256、commit/tree/tag、URL、filename、command、status/verdict/gate/finding token、JSON/schema/rule ID は原文どおりで、翻訳・正規化しません。

official [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) は build/link-share 済みの research preview です。repository package は、その reproducible configuration/evaluation source と current update candidate を提供します。誰でも configuration を inspect/reproduce でき、official status を示唆しない independent fork を作成できます。

この page は service availability、configuration identity、Preview validation、source deployment、immutable release を意図的に分離します。timestamped machine-readable snapshot は [PUBLICATION_STATUS.json](../PUBLICATION_STATUS.json) にあります。

## Current state

2026-07-24 に確認:

| Surface | State | Exact binding または boundary |
|---|---|---|
| Official Custom GPT | **live** | 上記 public URL。supported alpha.8 surface は bounded human-readable audit |
| Targeted alpha.8 live regressions | **passed** | canonical status-only routing は pass。conflicting verified evidence は admission を block し、SHA-256 digest を出力しなかった |
| Complete 12-case Preview evaluation | **not completed** | この prerelease は `pass_12_of_12` または complete live Builder-byte binding を主張しない |
| GitHub prerelease | **published** | [`v0.3.0-alpha.8`](https://github.com/jkolantree/octo/releases/tag/v0.3.0-alpha.8)。immutable tag と release assets が exact repository binding |
| Public Pages | **deployed** | English interface は [jkolantree.github.io/octo](https://jkolantree.github.io/octo/) で live |
| Japanese Pages route | **candidate; not deployed** | 予定 `/octo/ja.html` route は `2026-07-22T18:37:44Z` に HTTP 404。post-deploy English/JA/protocol route/metadata smoke が pass するまで live として案内しない |

この release は「working research preview」と「fully Preview-validated」を明確に分離します。repository checks と、repair された 2 つの high-risk live route は pass しました。full 12-case roster は未完了なので、source CI と targeted checks を broader evaluation の代用として表現してはいけません。

## Released compact scope

`0.3.0-alpha.8` prerelease は、service availability と validation を混同せず、日本語 accessibility と exact evidence boundary を強化します。この release は:

- uploaded Knowledge から mutable service-state claim を除き、現在状態は timestamped repository record に分離する;
- 利用者向けの official URL と、任意の reproduction/fork/update route を明確に分ける;
- canonical machine token を保った Japanese human-facing guidance を追加する;
- official GPT の Knowledge を 5 files にし、`BSC_EXECUTION_AND_RECEIPTS.md` は standalone repository tooling に限定する;
- scientific audit では human-readable duties 1-9 のみを 300/650/1,000-word budget 内で返す; official-product status-only response は duties 1-9 を bypass し、提供された canonical state だけを簡潔に返す;
- downloadable machine record、compiler stdout、Base64、shards、transport、section 10 を official GPT では無効化する;
- fresh 12-case compact-profile Preview gate で Japanese behavior と corrected evidence boundary を検証する。

preserved 39-case artifact-profile suite、D01/D02 preflight、compiler/transport results は historical and superseded です。これらは compact candidate を validate せず、12-case gate の代用になりません。

prior artifact-profile Preview result は、この changed compact profile を validate しません。public GPT と GitHub prerelease は利用できますが、`pass_12_of_12` または fully Preview-validated として promote しません。

## Exact trust boundary

GPT は authenticated owner-controlled research-preview interface です。proof engine、certification system、independent replication service、deployment authority ではありません。

- Custom GPT upload は applicable ChatGPT settings/terms の下で処理され、local-only ではない。
- ChatGPT file access/Data Analysis は、checker が実際に走り identified output が保存されない限り versioned BSC Python result ではない。
- Lean/SMT/interval/empirical claim には separately identified supervised execution と admissible evidence が必要。
- fluent report、hash-shaped string、submitted receipt、internally consistent `audit_return.json` は truth、source authenticity、independent replay、deployment permission を確立しない。

## Alpha.8 release boundary

exact repository candidate が deterministic local checks と branch CI を pass し、repair された status-routing と conflicting-evidence path が targeted live regression を pass した場合、この minimal prerelease を ship できます。これが supported alpha.8 claim です。

exact 12-case compact roster は、将来 `pass_12_of_12` または fully Preview-validated と主張するための gate として残ります。未完了状態は明示し、平均化や黙った relabel はしません。former 39-case artifact workflow、compiler output、downloadable machine record、Base64、shards、transport は supported public-GPT surface に含まれません。

Instructions、Knowledge、capabilities、Builder configuration を後から変更する場合は、新しい binding record と相応の regression testing が必要です。この prerelease は changed service bytes を validate しません。

## Preserved alpha.7 baseline

immutable `v0.3.0-alpha.7` package は live Update 前に、depth-explicit Preview 27/27 件を 18/20 以上、automatic failure なしで完了しました。保存された score distribution は 20/20 が 18 cases、19/20 が 5、18/20 が 4 です。limitation/deduction は evidence として残り、history を黙って repair しません。

| Alpha.7 artifact | SHA-256 |
|---|---|
| Release package | `855d905b8788059e6c14a7374a82a6510fb0f0a86224a08c292d654b8da574d4` |
| Raw Preview evidence | `f75818ef10c2d9b09239f2149867b7dec3b34880e9cd8681c3dc82ce408add01` |
| JSON scorecard | `b6d9827bcf112af7a1e8c4fff151c6250a70a6b9d064ddab1a1cfd2655b88585` |
| Markdown scorecard | `97c0b82b0c3bd13aa40710fb0982b603aeab4b6fc9a278edb565c9cb14c2cc3e` |

この historical baseline は changed controller、Knowledge set、Builder configuration、evaluation suite へ transfer しません。
