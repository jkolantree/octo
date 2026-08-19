# BSC Claim Auditor: Japanese Glossary

## Beta disclosure

Japanese support is beta. This material has not received a claimed native-speaker terminology review. When the user requests Japanese, explain the audit in Japanese. Canonical technical tokens may remain in English, but they must be explained; an English-only list of machine tokens is not a Japanese response.

Runtime language routing is owned by the Instructions. This glossary owns only terminology mappings and Japanese examples.

## Three semantic lanes

| Canonical concept | Japanese explanation |
|---|---|
| Research proposition | 研究上の命題。数学的・科学的・技術的に何が成り立つかという主張。 |
| Evidence, execution, and gates | 証拠・実行・ゲート。資料の有無、実際に何を実行したか、結果が競合しているかという事実状態。 |
| Authority and deployment | 権限・導入判断。公開、運用、臨床、安全、法務、方針など、責任ある権限者が決める事項。 |

一つの文に複数のレーンが混在する場合は、結論を分けて説明します。数学的に正しいことだけで、実運用の許可や安全認証が得られるわけではありません。

## Research verdicts

| Token | Japanese mapping |
|---|---|
| `proven` | 証明済み。未解決の依存関係がない完全な数学的証明があるか、厳密な証明書が、特定された検証器・版・入力・主張範囲の下で実際に再実行され、成功している。 |
| `strongly_supported` | 強く支持される。経験的主張が明示された十分な検証と独立証拠を通過しているが、普遍的な証明ではない。 |
| `plausible_but_unresolved` | 妥当そうだが未解決。整合的で反証されていないが、重要な義務が残る。 |
| `refuted` | 反証済み。主張に適用できる反例、矛盾、または決定的な反証結果がある。 |
| `ill-posed` | 問いの定義が不十分。対象、範囲、比較、極限などが足りず、述べられた真偽を決められない。 |
| `outside_current_knowledge` | 明示した知識・検索範囲で未解決。正確な命題が、その明示範囲で未解決だと認められている場合に限る。世界のどこにも答えがないという意味ではない。通常の資料不足は、監査範囲内の `plausible_but_unresolved` とする。 |

## Dependency-local evidence boundary

各結論について、その結論を支える最小の前提または決定的な依存関係を確認します。重要な前提が未確立なら、その前提に依存する結論だけを条件付きまたは未解決にします。同じ資料に書かれていても、独立した根拠を持つ別の結論まで弱めません。

背景知識は、範囲を明示した評価や次の試験の提案に使えることがありますが、この監査で閲覧・観察・検証・実行した証拠とは呼びません。報告書を読むことは「報告書に何が書かれているか」を確認するだけで、報告された出来事の発生を自動的に確認するものではありません。証明書も、存在・構文解析・検証可能性だけでは `proven` にならず、上記の条件で実際に成功した再実行が必要です。

## Evidence and execution states

| Token | Japanese mapping |
|---|---|
| `observed` | 観察済み。指定された範囲で実際に確認した。 |
| `missing` | 欠落。必要な資料または記録がない。 |
| `not_run` | 未実行。計算、試験、ツールなどは実行されていない。 |
| `failed` | 失敗。対象となる確認またはゲートが失敗した。 |
| `conflict` | 競合。両立しない適切な結果が共存している。 |
| `reported_but_unverified` | 実行したとの報告はあるが、十分な記録で確認できていない。 |

例: 「モンテカルロ計算は計画されていますが、出力記録がないため `not_run（未実行）` です。予想された p 値を観測結果として扱うことはできません。」

## Authority states

| Token | Japanese mapping |
|---|---|
| `blocked` | ブロック中。必要な権限または条件が満たされていない。 |
| `not_assessed` | 未評価。権限判断を行っていない。 |
| `requires_authorized_review` | 権限を持つ担当者の審査が必要。 |
| `externally_authorized` | 外部の権限ある記録によって承認済み。提供された正式記録がある場合に限る。 |

例: 「安定性の数学的証明は研究命題を支えます。しかし、医療機器への導入は `requires_authorized_review（権限を持つ審査が必要）` であり、この監査から承認を作ることはできません。」

## Requested-language examples

**証拠が途中で切れている場合**

「結論: 提示された範囲では証明は未完です。後半の補題が欠けているため、命題は `plausible_but_unresolved（妥当そうだが未解決）` のままです。モデルが補題を補うことは修正案であり、提出済みの証拠ではありません。」

**状態を分離する場合**

「ソース候補の存在、評価の実行状態、公開サービスで観察された状態、内部インデックスのバイト同一性、エンジンの版、公開権限は別々です。一つの状態から他の状態を推定しません。」

Canonical tokens are supporting labels. Never replace the requested Japanese explanation with English-only tokens or an untranslated machine record.
