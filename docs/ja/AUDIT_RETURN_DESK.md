# Audit Return Desk

> **日本語ベータ版**: この文書は [`docs/AUDIT_RETURN_DESK.md`](../AUDIT_RETURN_DESK.md) の参考訳です。母語話者による用語レビューは未完了です。英語版が規範です。JSON keys/values、schema/rule IDs、status/verdict/gate/finding tokens、paths、hashes、commands、filenames、quoted source bytes はそのまま保持します。

Audit Return Desk は、明示的に non-admissive な contract の下で structured audit return を検査します。同じ contract の 2 implementation があります。

- `pages/` 内の browser-local Desk: strict JSON parsing と user-selected file の hash;
- `python run_audit.py return-desk PATH`: 同じ semantic inspection を行い、return file の directory から artifact を読む。

official service の現在の availability は [CUSTOM_GPT_STATUS.md](CUSTOM_GPT_STATUS.md) に分けて記録します。official-service availability、exact candidate binding、Preview validation、GitHub release state、Pages deployment は別々の fact であり、この source feature の存在だけからどれも推論できません。

## Authority boundary

Desk が検査するのは internal consistency です。truth を決めず、citation を authenticate せず、theorem を prove せず、external tool が実際に走ったことを establish せず、experiment を independently replicate せず、evidence を admit せず、deployment permission を grant しません。

accepted envelope は次の値を厳密に維持しなければなりません。

```json
{
  "return_version": "0.1.0",
  "authority": "non_admissive_return_inspection",
  "draft": true
}
```

closed schema は [`schemas/audit-return-v0.1.schema.json`](../../schemas/audit-return-v0.1.schema.json) です。canonical production rules は [LLM Audit Packet](../../BSC_AUDIT_LLM_PACKET.md) にあります。generated model output は Desk に対しても untrusted input です。

## Deterministic producer transaction

Custom GPT の machine record は、`BSC_EXECUTION_AND_RECEIPTS.md` に埋め込まれた完全な canonical `scripts/gpt_artifact_compiler.py` source によって finalize しなければなりません。model はその source を実行し、その動作を prose で再現したり、代替 finalizer を書いたりしてはいけません。

実行された compiler は自身の完全な `sys.version` を一度だけ capture し、model-authored spec からの runtime 指定や override を拒否します。compiler は exact frozen request/source/evidence bytes、report body、structured return template を受け取り、report を finalize し、final bytes から artifact identities と runtime ledger を導出し、execution/evidence topology を validate し、`chatgpt_data_analysis_output.txt` を書き、最後に `audit_return.json` を serialize します。compiler failure があれば return と、artifact production の成功に依存するすべての conclusion を禁止します。matching final snapshot だけでは historical write order を証明しないため、compiler execution と保存された output も candidate evidence の一部です。

standard Custom GPT artifact transaction の execution topology は固定です。

- `model_reasoning` の input は request、exact case target、6 個すべての canonical Knowledge files です。output は model-produced の role-`evidence` artifact すべてと `audit_report.md` です。`receipt_ids` は empty です。
- `chatgpt_data_analysis` の input も同じです。output はそれらの evidence artifacts、`audit_report.md`、`chatgpt_data_analysis_output.txt` です。`receipt_ids` は empty です。

external receipt は、それを実際に生成した external activity だけに属します。model reasoning や Data Analysis への alias にしてはいけません。

## Browser workflow

1. Pages module を開き、表示された protocol version と verification state が intended workflow と一致することを確認する。
2. complete `audit_return.json` object を 1 個 paste するか JSON file を選ぶ。
3. envelope が宣言する request、human report、sources、evidence、execution outputs、receipt files を選ぶ。
4. **Inspect return locally** を選ぶ。
5. blocking、needs-review、informational finding をすべて確認し、technical witness/repair があれば展開する。
6. metadata を安全に retain/share できる場合だけ deterministic inspection JSON を download する。

page は canonical protocol と embedded return-schema bytes を検証してから inspection を有効にします。duplicate JSON key、trailing data、stale protocol binding、unsafe/colliding filename、contradictory ledger、unsupported verdict promotion、concealed gate failure、unrelated execution reuse、ID/role 間の exact-byte artifact alias、local hash mismatch を reject します。

Return JSON は UTF-8 で 8 MiB までです。browser hashing は selected return artifact 32 files、1 file 64 MiB、total 256 MiB までです。追加の declared file は unavailable のままで `needs_review` を強制します。Python route も同じ 32-file、64-MiB-per-file、256-MiB-total bound を enforce し、declared-file/aggregate local-byte budget を超える envelope を block します。大きな review は material evidence を omit せず、明示的 scope の複数 return に分割してください。

page code は selected bytes を hashing のために読み、target-data network request を行わず、意図的に保存せず、browser file path を収集しません。ただし browser/OS history、crash recovery、swap、extension、clipboard、downloaded inspection file は page の管理外です。

downloaded result は attached file bytes を含みませんが、filename、identifier、expected/observed hash、witness、repair を開示する可能性があります。SHA-256 は private/low-entropy material を anonymize しません。

## Python workflow

envelope と declared artifact を、unique portable basename で 1 directory に置き、実行します。

```bash
python run_audit.py return-desk path/to/audit_return.json
```

Known controls:

```bash
python run_audit.py return-desk examples/audit_return_valid.json
python run_audit.py return-desk examples/audit_return_missing_artifact.json
python run_audit.py return-desk examples/audit_return_poisoned_summary.json
```

1 つ目は `no_blocking_findings`、2 つ目は `no_blocking_findings_with_warnings`、poisoned summary は `blocked` を返します。exit code `0` は、この inspection が blocking inconsistency を見つけなかったという意味だけで、scientific pass ではありません。

## 再計算されるもの

semantic layer は次を検査します。

- exact protocol version と SHA-256;
- globally unique ID と complete reference;
- request/report role と portable filename uniqueness;
- bidirectional claim/evidence/gate/obligation binding;
- claim-scoped gate evidence と complete summary projection;
- local artifact hash と eligible evidence role;
- `proven`, `strongly_supported`, `refuted` に必要な source coverage/source bytes;
- exact eight-activity execution roster と `file_read_only` boundary;
- execution input/output/receipt/claim/gate scope;
- receipt authority/kind/artifact uniqueness/single-activity use;
- fatal-gate state と conjunctive admission の recomputation;
- receipt-only proof と deployment overreach の prohibition。

missing bytes は通常 review-needed status になります。declared hash mismatch、placeholder hash、stale protocol、invalid schema、concealed failure、unsupported promotion、contradictory binding は block します。missing material だけで claim を `refuted` にしてはいけません。

## Browser と Python の outcome

| 意味 | Browser | Python CLI |
|---|---|---|
| blocking finding も unavailable byte もない | `consistent` | `no_blocking_findings` |
| internally coherent だが unavailable/unverified のものがある | `needs_review` | `no_blocking_findings_with_warnings` |
| malformed、contradictory、unsupported、stale、integrity-failing | `blocked` | `blocked`、または schema/malformed input では `prohibited` |

これら outcome は research verdict、evidence maturity、execution status、gate state、deployment status、他 BSC route の decision とは別 coordinate です。

## Preview transport boundary

evaluation controller は最初に direct generated-file control を試みます。original compile transaction は、final exportable bytes を、file control や semantic artifact として公開しない fresh private directory に seal します。interface が direct download を提供しない場合、または observable download event がない場合、controller は 1 filename と 1 chunk index だけを対象とする exact fallback prompt を送信できます。candidate は指定された private snapshot に対して compiler の `export-chunk` command を新たに実行し、他の prose を付けず、1 個の code block 内に 1 個の strict JSON object を返さなければなりません。各 wrapper の decoded compressed bytes は最大 2,048 bytes で、payload 全体と compressed stream の identity を繰り返します。固定 fallback order は `audit_return.json`、`chatgpt_data_analysis_output.txt`、その後に残りの generated output であり、各 turn では 1 file の連続する 1 index だけを取得します。

controller は各 exact prompt、code-block text bytes、parser input、完全な transport-response `outerHTML` を別々に保存します。各 response が要求された wrapper を 1 個だけ含むこと、canonical Base64、chunk size/digest、連続 index、payload と compressed stream の反復 identity を検証してから、再構成・展開・local-byte 比較を行います。parsed object の re-serialize は raw transport record ではなく、trial を `trial_invalid_controller` にします。これらが証明するのは、実際に受け取った exported payload の identity だけです。original download-button bytes が unavailable のままなら、その identity は `transport_identity_unresolved` であり、identity も corruption も確立されていません。
