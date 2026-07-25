# BSC 日本語用語集

> **日本語ベータ版**: 母語話者による用語レビューは未完了です。英語の規範プロトコルと機械語彙が常に優先されます。

この用語集は説明を日本語化するための補助資料です。左側のコード表記が正規トークンです。JSON、Schema、コマンド、ファイル名、識別子、ハッシュでは正規トークンだけを使用します。

## 研究上の判定

| 正規トークン | 日本語の説明 |
|---|---|
| `proven` | 依存関係を含む完全な証明または適切な証明書がある |
| `strongly_supported` | 強い証拠があるが、完全な証明とは限らない |
| `plausible_but_unresolved` | もっともらしいが決定的な証拠・証明が不足している |
| `refuted` | 反例または決定的な反証がある |
| `ill_posed` | 主張が不定、型不正、または評価可能な形になっていない |
| `outside_current_knowledge` | 主張は精密だが、決定的な証明・反証・実行可能な検査が現在知られていない |

`proven` は「形式証明支援系を実行した」という意味ではありません。証明支援系の実行は execution ledger で別に記録します。資料の欠落だけを理由に `refuted` にしてはいけません。

## 証拠成熟度

| 正規トークン | 日本語の説明 |
|---|---|
| `declared` | 申告された段階 |
| `structurally_checked` | 実装された構造検査を通した段階 |
| `empirically_passed` | 宣言された実験・評価を通した段階 |
| `externally_replicated` | 独立した外部再現が確認された段階 |

## 実行状態

| 正規トークン | 日本語の説明 |
|---|---|
| `not_run` | 実行していない |
| `file_read_only` | ファイルを読んだだけで、計算・検証は実行していない |
| `ran` | 特定されたツール、入力、出力で実行した |
| `reported_but_unverified` | 実行したとの報告はあるが検証可能な記録がない |
| `not_applicable` | この活動は対象外 |

`model_reasoning`、`web_research`、`independent_source_check`、`chatgpt_data_analysis`、`bsc_python_checker`、`external_proof_tool`、`empirical_test`、`proposed_computation` は別々の activity です。

## Fatal gate

| 正規トークン | 日本語の説明 |
|---|---|
| `pass` | 必要な証拠と確認方法がそろい、ゲートが通過した |
| `fail` | 検証済みの失敗証拠がある |
| `unrun` | 必要な証拠・実行が不足し、判定を実行できない |
| `conflict` | 同じゲートに矛盾する有効な証拠がある |

Fatal gate は連言的です。`unrun`、`fail`、`conflict` を平均点で救済してはいけません。

## 配備状態

| 正規トークン | 日本語の説明 |
|---|---|
| `research_only` | 研究・検討用途のみ |
| `sandboxed` | 隔離された環境でのみ使用 |
| `candidate` | 配備候補だが承認前 |
| `admitted` | 独立した必要条件を満たし、定義された範囲で承認済み |
| `retired` | 使用停止・撤回済み |

数学的に正しいこと、構造検査が clean であること、証拠成熟度が高いことだけでは `admitted` になりません。

## CLI decision と Return Desk

| 正規トークン | 日本語の説明 |
|---|---|
| `no_blocking_findings` | 実行した検査では blocking condition が見つからなかった |
| `no_blocking_findings_with_warnings` | blocking condition は確定しないが未確認事項がある |
| `blocked` | required obligation または blocking finding があり、Return Desk では return が stale、malformed、contradictory、unsupported、または integrity-failing である |
| `demoted` | 宣言された状態より弱い状態へ降格した |
| `prohibited` | 入力または方針上、処理・昇格が禁止された |
| `internal_error` | 入力判定とは別の内部失敗 |
| `consistent` | Return Desk の実装済み整合性検査で矛盾が見つからなかった |
| `needs_review` | 不整合は確定しないが、未提供・未確認の要素が残る |

Return Desk の browser outcome は `consistent`、`needs_review`、`blocked` の 3 つだけです。

`no_blocking_findings` と `consistent` は、真理、証明、出典の真正性、独立実行、証拠採用、配備許可を意味しません。

## サービスと候補パッケージの状態

| 正規トークン | 日本語の説明 |
|---|---|
| `LIVE` | 公式サービスへアクセスできる |
| `REPRODUCIBLE_SOURCE_AND_UPDATE_CANDIDATE` | 公開ソースから再現できる更新候補 |
| `PENDING` | 必要な結合確認または Preview 評価が完了していない |
| `PENDING_VERIFICATION` | 保存済み構成と候補パッケージの厳密な対応をまだ確認していない |
| `VERIFIED` | 定義された確認手順と証拠がそろっている |

公式サービスが `LIVE` でも、特定候補の binding または Preview validation が `PENDING` の場合があります。これらを一つの「公開済み／未公開」状態にまとめてはいけません。

## 翻訳規則

- 正規トークンはコード書式のまま保持します。
- 日本語説明はトークンの後ろに添えます。
- 引用の翻訳には「翻訳」と明記し、重要な原文を残します。
- 固有名詞、URL、DOI、ファイル名、パス、コマンド、ハッシュ、Schema ID、finding code は変更しません。
- Unicode 正規化、改行変換、翻訳を行ったバイト列で元資料のハッシュを置き換えません。
