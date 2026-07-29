# Status Model

> **日本語ベータ版**: この文書は [`docs/STATUS_MODEL.md`](../STATUS_MODEL.md) の参考訳です。母語話者による用語レビューは未完了です。意味上の食い違いがある場合は英語版が優先されます。下記の backtick 内の status、enum、field、decision token は machine vocabulary なので翻訳しません。

BSC は、truth assessment、evidence maturity、execution status、deployment authority、gate result、checker decision を分離します。1 つの badge にまとめると重要な failure mode が消えてしまいます。

## 1. Research verdict

research verdict は、claim と evidence に対する責任ある人間の review によって付与されます。

| Verdict | 意味 |
|---|---|
| `proven` | 数学的 claim に complete proof または independently checkable exact certificate があり、unresolved dependency がない。 |
| `strongly_supported` | 経験的 claim が substantial declared testing と independent evidence を通過しているが、universal proof ではない。 |
| `plausible_but_unresolved` | claim は coherent で refute されていないが、essential obligation が残る。 |
| `refuted` | valid counterexample、contradiction、または decisive prospective falsifier が適用される。 |
| `ill_posed` | required object/domain/comparison/limit が、述べられた truth value を持つほど十分に定義されていない。 |
| `outside_current_knowledge` | claim は precise だが、decisive proof/refutation/accessible test が現在知られていない。 |

CLI はこの verdict を付与しません。

## 2. Evidence maturity

manifest field `claim.evidence_maturity` は workflow maturity を記録します。

- `declared`
- `structurally_checked`
- `empirically_passed`
- `externally_replicated`

後の state ほど強い attached record を必要としますが、存在は authenticity を意味しません。proof、dataset、replication の名前を持つ string は、それだけでは artifact の verification ではありません。同様に、local SHA-256 の一致は inspected bytes の identity を示すだけで、その bytes に valid result が含まれることを示しません。declared evidence result は、registered exact replay がその result を recompute しない限り evidence maturity に影響しません。manifest `0.4.0` には、意図的に closed な replay が現在 1 つだけあります。claim-bound `q-polynomial-identity-v0.1` certificate は authoritative formal AST と residual の exact symbolic replay 後に限り `structurally_checked` を support できます。empirical または independent-replication replay は登録されていないため、`empirically_passed` と `externally_replicated` は blocked のままです。general theorem prose、external-tool receipt、legacy manifest `0.3.0`、その他すべての artifact result は non-admissive のままです。

## 3. Execution status

execution status は何が実際に走ったかを記録します。research claim の真偽や、executed check が十分だったかは記録しません。

| Status | 意味 |
|---|---|
| `not_run` | activity は実行されなかった。 |
| `file_read_only` | ChatGPT Data Analysis が file を開く／inventory しただけで、mathematical、BSC Python、formal-tool、empirical verification は行っていない。この status は file-access boundary に限って有効。 |
| `ran` | activity が実行され、relevant output を inspection できる。 |
| `reported_but_unverified` | source は activity が走ったと述べるが、adequate execution record/receipt がない。 |
| `not_applicable` | activity は audited claim に無関係。`not_run` の代用にはならない。 |

各 audit execution ledger は次の activity を別々に記録します。

- model reasoning over supplied material;
- web search;
- cited source の independent opening/checking;
- ChatGPT Code Interpreter または Data Analysis;
- versioned BSC Python checker;
- external theorem prover、proof assistant、SMT solver、interval tool、その他 adapter;
- empirical experiment または measurement;
- proposed/described だが実行していない computation。

各 entry は status、scope/input、判明している tool/version、依存した result、receipt/transcript/citation/output identifier を記録します。record がなければ、その不在と理由を書きます。adequate bound record のない mechanical activity は `ran` にできません。model reasoning は mechanical execution ではありません。ChatGPT tool execution は BSC checker run ではありません。submitted adapter receipt は provenance object であり、declared execution と replay が independently established されない限り external proof-tool verification ではありません。

adequate bound record なしの `Python passed`, `Lean verified it`, `all tests passed` は false-pass risk です。`reported_but_unverified` を付け、evidence maturity を promote せず、verified conflicting evidence が `conflict` を要求する場合を除き dependent gate は `unrun` のままにします。これは unsupported execution claim の demotion であり、underlying research claim の自動的な refutation ではありません。

## 4. Deployment status

manifest は次も別々に記録します。

- `research_only`
- `sandboxed`
- `candidate`
- `admitted`
- `retired`

現実の deployment を authorize できるのは accountable organization だけです。engine は required gate が unresolved のとき manifest が `admitted` を名乗ることを prohibit できますが、legal/moral/clinical/operational permission を grant できません。

## 5. Gate state

適用される各 fatal gate は 1 state を持ちます。

- `unrun` — adequate result がない;
- `pass` — declared obligation が referenced evidence とともに pass;
- `fail` — prospective failure condition が発火;
- `conflict` — incompatible verified conclusion が共存。decisive result と inconclusive bound record の混在も含む。

Admission には適用される全 fatal gate が厳密に `pass` であり、その state が registered exact replay によって recompute されていることが必要です。hash-verified だが replay されていない record は、negative record を含めて provenance として保持・表示されますが、gate は `unrun` と compute されます。declared conclusion は registered replay が確立するまで non-admissive なので、declared failure だけで dependency propagation を trigger することもできません。registered replay が incompatible result を生成した場合は `conflict` を保存して block し、平均化しません。

checker は gate に bind された全 evidence record と registered replay judgment からこの coordinate を derive します。manifest は gate record から identifier を省いて bound record を隠せません。submitted state が derived state と違えば block されます。

## 6. CLI decision

CLI は finding を 1 つの mechanical decision に要約します。

| Decision | 意味 |
|---|---|
| `no_blocking_findings` | selected check は blocking finding を生成しなかった。 |
| `no_blocking_findings_with_warnings` | blocking finding はないが warning の review が必要。 |
| `blocked` | required obligation が unresolved。 |
| `demoted` | prospective demotion condition が発火。 |
| `prohibited` | input が malformed、または hard prohibition に違反。 |
| `internal_error` | checker が予期せず失敗し、scientific result は生成されなかった。 |

これらの outcome は実際に executed した check だけを表します。trustworthy report は run しなかった check も列挙します。

## 7. Source-coverage state

source coverage は evidence maturity と execution から分離して記録します。supplied/expected source はそれぞれ厳密に 1 state を持ちます。

- `fully_inspected`
- `partially_inspected`
- `unreadable`
- `missing`
- `possibly_truncated`

ledger は source version、inspected range、omission、access mode、execution mode も記載します。全 available byte を見ても object が truncated の可能性があれば `fully_inspected` とはできません。sampling した場合は `partially_inspected` とし、unreviewed remainder を明示します。

## 8. Audit Return Desk outcome

Return Desk は returned-envelope consistency という別 coordinate を追加します。

| Browser outcome | Python mapping | 意味 |
|---|---|---|
| `consistent` | `no_blocking_findings` | implemented return check は blocking inconsistency や unavailable declared byte を見つけなかった。 |
| `needs_review` | `no_blocking_findings_with_warnings` | blocking inconsistency は確立されていないが、byte/source/receipt/execution claim の一部が unavailable/unverified。 |
| `blocked` | `blocked`、または malformed/schema-invalid input では `prohibited` | return が stale、malformed、contradictory、unsupported、integrity-failing。 |

この outcome は non-admissive です。research verdict の付与／検証をせず、truth、proof、citation authenticity、external execution、deployment authority を確立しません。

## 9. Exit codes

- `0`: warning の有無を問わず blocking finding なし;
- `1`: `blocked` または `demoted`;
- `2`: malformed input または command usage;
- `70`: `internal_error`、すなわち unexpected engine failure。

automation は exit code と structured JSON の両方を検査する必要があります。exit code `0` を “scientifically true” や “BSC compliant” に変換してはいけません。

## 10. External and live binding

successful holonomy audit は `HOLONOMY_EXTERNAL_INTERPRETATION_NON_ADMISSIBLE`
を emit します。submitted finite maps の algebra だけが scope であり、source
authenticity と scientific truth は `not_established` です。

live Custom GPT の indexed Knowledge state は
`NON_ADMISSIBLE_UNHASHABLE` です。saved editor、filename、public behavior は
observe できますが、independently retrievable な indexed bytes ではないため、
engine gate、theorem replay、scientific admission の evidence にはなりません。

## Separation rule

Research verdict、evidence maturity、execution status、deployment status、gate state、CLI decision、source coverage、Return Desk outcome、live binding は別の質問に答えます。相互に推論してはいけません。特に:

- coherent/proven claim は proposed execution が走ったことを意味しない;
- ran finite check は broader theory を prove しない;
- gate `pass` は deployment authority を grant しない;
- CLI decision は declared input に対して implemented check が出した結果だけを report する;
- model confidence は BSC status のどれでもない。
