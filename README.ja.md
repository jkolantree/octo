# BSC Audit Engine

> **日本語ベータ版**: この文書は [`README.md`](README.md) の参考訳です。母語話者による用語レビューは未完了です。英語の規範文書が常に優先されます。JSON のキーと enum、ルール／スキーマ ID、研究判定・ゲート・finding のトークン、パス、ハッシュ、コマンド、ファイル名、引用された原文は翻訳・正規化・音写しません。

数学的・科学的主張を、調査、反証、再現、降格しやすくするための研究プレビュー版ソフトウェアです。

**Official Custom GPT:** [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor)（live research preview）<br>
**現行 GitHub release:** `v0.3.0-alpha.7`<br>
**リリース候補:** `0.3.0-alpha.8`（local、Preview、live binding、merge、release の各 gate は未完了）<br>
**プロジェクト状態:** 実験的。研究監査と既知解テストには利用できますが、無人の科学・臨床・法律・安全・政策判断には使用できません。

[English](README.md) | [Timestamped publication status](docs/PUBLICATION_STATUS.json)

BSC は、慎重な想像力のための基盤です。大胆な仮説は許しますが、根拠のない権威は与えません。

## できること

エンジンは、宣言された限定的な構造上の義務を検査します。現在のルートには次が含まれます。

- manifest と hard gate の lint;
- 有理数上の厳密な行列・chain-complex 検査;
- certificate interchange の defect と有限 witness;
- square holonomy と path dependence;
- 厳密有理数上の任意 path に対する strict、derived、observed-derived holonomy;
- 再生可能な chain-homotopy または dual-obstruction certificate と厳密 residual;
- 有限 observation/query descent witness;
- conflict を平均しない product-valued gate;
- 非巡回 claim graph における fatal dependency propagation;
- finite atomic-modulus record 検査;
- 宣言された affine upper bound の厳密な伝播;
- 限定された arithmetic-trace と local/global recovery gate;
- 非 admissive で hash-bound な Lean/SMT/interval adapter receipt;
- 返却された audit envelope、ledger、projection、receipt、local artifact hash の非 admissive 検査;
- canonical JSON hashing。

エンジンは、任意の理論の真偽を決定したり、任意の証明を再構成したり、外部 evidence identifier を認証したり、経験的追試を保証したり、道徳・法律・臨床・配備の許可を与えたりはしません。`no_blocking_findings` は、実際に走った検査が blocking condition を見つけなかった、という意味に限られます。

## 入口を選ぶ

1. **Official Custom GPT — ChatGPT 上で直接監査:** live [BSC Claim Auditor](https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor) を開きます。現在は alpha.8.dev0 controller identity を report しますが、その version の gate を満たす complete post-update Preview evaluation は保存されていません。すべての output を research-preview draft として扱ってください。upload は applicable ChatGPT settings/terms の下で処理されます。GPT に Action、hosted API、account、analytics、cloud-storage integration はありません。[exact live/candidate status](docs/ja/CUSTOM_GPT_STATUS.md) を参照してください（規範英語: `docs/CUSTOM_GPT_STATUS.md`）。
2. **ローカル browser Packet Builder と Audit Return Desk:** [deployed English GitHub Pages module](https://jkolantree.github.io/octo/) で versioned packet を作成したり、返却された `audit_return.json` draft と selected artifact bytes をローカル検査したりできます。[Japanese Pages candidate](pages/ja.html) は source tree にありますが、public deployment は pending です。post-deploy English/JA/protocol route/metadata smoke が pass するまで予定 URL を live として共有しないでください。どちらの interface も target を upload せず、LLM を呼び出さず、Python を実行しません。
3. **Repository と Python engine — exact checker route:** versioned schema、fixture、finite exact check、保存された command output については [docs/PROGRAMMER_TUTORIAL.md](docs/PROGRAMMER_TUTORIAL.md) を参照してください。ここで BSC checker を実行するのはこのルートだけです。

repository には、official Custom GPT の configure/evaluate に使用した exact package と current update candidate もあります。これにより、independent inspection、reproducible deployment、compatible fork、verifiable official update が可能です。

補助的な入口:

- **初回:** [START_HERE.ja.md](START_HERE.ja.md)（規範英語: `START_HERE.md`）または accessible offline [START_HERE.html](START_HERE.html)
- **Japanese Pages candidate（public deployment pending）:** [pages/ja.html](pages/ja.html)
- **Custom GPT 日本語ガイド（ベータ）:** [docs/ja/GPT_INTERFACE.md](docs/ja/GPT_INTERFACE.md)
- **正規トークン日本語用語集（ベータ）:** [docs/ja/GLOSSARY.md](docs/ja/GLOSSARY.md)
- **人手のみの監査:** [AUDIT_WORKSHEET.md](AUDIT_WORKSHEET.md)
- **手動 LLM packet:** [BSC_AUDIT_LLM_PACKET.md](BSC_AUDIT_LLM_PACKET.md)
- **文書マップ:** [docs/ja/index.md](docs/ja/index.md)（規範英語: `docs/index.md`）
- **例の一覧:** [examples/README.md](examples/README.md)
- **数学的定義:** [docs/MATHEMATICS.md](docs/MATHEMATICS.md)
- **Derived holonomy:** [docs/DERIVED_HOLONOMY.md](docs/DERIVED_HOLONOMY.md)
- **Spectral obstruction boundary:** [docs/SPECTRAL_OBSTRUCTIONS.md](docs/SPECTRAL_OBSTRUCTIONS.md)
- **新しい research packet:** [research/derived-witnessed-descent/README.md](research/derived-witnessed-descent/README.md)
- **Proof adapter boundary:** [docs/PROOF_CARRYING_ADAPTERS.md](docs/PROOF_CARRYING_ADAPTERS.md)
- **Audit Return Desk:** [docs/ja/AUDIT_RETURN_DESK.md](docs/ja/AUDIT_RETURN_DESK.md)（規範英語: `docs/AUDIT_RETURN_DESK.md`）
- **Pseudonymous publication policy:** [PRIVACY.md](PRIVACY.md)
- **公開済み訂正:** [ERRATA.md](ERRATA.md)

Pages module の code は target data を network request に載せず、意図的な永続保存を行わず、versioned audit protocol を検証してから output を有効にします。ただし browser、OS、extension、clipboard、download の挙動は page の管理外です。packet を送信する、または Custom GPT に直接 upload する時点で選択した model service に渡り、local-only ではなくなります。別途の許可なしに、機密情報を第三者 model へ渡さないでください。

Return Desk は、closed return schema、双方向 reference、summary projection、fatal-gate derivation、execution disclosure、receipt limit、利用可能な local artifact hash を検査します。`consistent` は真理、証明、source authenticity、independent execution、deployment permission の判定ではありません。

## 30 秒の例

package を install せずに既知の descent failure を実行します。

```bash
python run_audit.py --version
python run_audit.py observe examples/observation_failure.json
```

この例では、宣言された observation relation が同一視する 2 state に対して query が異なる値を返します。checker は exact pair とともに `blocked` を返します。これは supplied finite relation と query について descent failure を示しますが、その relation が物理実験の完全な model であることは示しません。

passing structural example:

```bash
python run_audit.py complex examples/complex_valid_transport.json
```

homology 上では harmless な strict mismatch:

```bash
python run_audit.py holonomy examples/holonomy_contractible_derived_pass.json
```

output は strict defect を warning として残し、exact chain homotopy を出します。検査範囲は supplied finite rational complexes と semantic bindings のみです。

返却された audit envelope と、その隣に置いた artifact files を検査します。

```bash
python run_audit.py return-desk examples/audit_return_valid.json
python run_audit.py return-desk examples/audit_return_poisoned_summary.json
```

1 つ目の fixture は内部整合し、明示的に non-admissive です。2 つ目は summary が underlying claim verdict を隠すため `blocked` になります。どちらも represented research claim の真偽を決定しません。

source checkout から、すべての supported platform で test を実行します。

```bash
python scripts/run_tests.py
```

installed command を使う場合は virtual environment を作り、`python -m pip install -e .` を実行してから、`python run_audit.py` の代わりに `bsc-audit` を使います。

## Status model

次の 5 coordinate は意図的に分離されています。

1. **Research verdict:** `proven`, `strongly_supported`, `plausible_but_unresolved`, `refuted`, `ill_posed`, `outside_current_knowledge`。これは人間の科学的 review によって付与され、JSON parsing から推論されません。
2. **Evidence maturity:** `declared`, `structurally_checked`, `empirically_passed`, `externally_replicated`。
3. **Execution status:** `not_run`, `file_read_only`, `ran`, `reported_but_unverified`, `not_applicable`。model reasoning、web/citation check、ChatGPT tools、BSC Python、external proof tools、empirical tests ごとに別々に記録します。`file_read_only` は calculation や verifier が走ったことを決して示しません。
4. **Deployment status:** `research_only`, `sandboxed`, `candidate`, `admitted`, `retired`。
5. **Gate state:** `unrun`, `pass`, `fail`, `conflict`。

別 coordinate の BSC CLI decision は `no_blocking_findings`, `no_blocking_findings_with_warnings`, `blocked`, `demoted`, `prohibited`, 例外的な `internal_error` です。[docs/ja/STATUS_MODEL.md](docs/ja/STATUS_MODEL.md) を参照してください（規範英語: `docs/STATUS_MODEL.md`）。

Admission は conjunction です。適用されるすべての fatal gate が `pass` でなければなりません。aggregate score は `unrun`、`fail`、`conflict` の fatal gate を救済できません。

## Trust boundary

- Input は利用者の declaration です。claim、citation、proof identifier、hash target、calibration record、experiment が構文上存在するだけで、その内容が正直だとは checker には分かりません。
- Exact arithmetic の範囲は relevant command に実際に渡された finite object だけです。
- LLM が生成した report と manifest は draft です。target document は untrusted data であり prompt injection を含む可能性があります。ChatGPT Code Interpreter / Data Analysis output は、versioned BSC Python checker が実際に走り output が保存されない限り、BSC Python result ではありません。
- Domain plugin は required typed field がそろった場合だけ activate します。output は run 済み／未 run の check を列挙する必要があります。
- Negative result、conflict、fired demotion は平均化や黙示的 overwrite をせず保存します。

監査に依存する前に [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) を読み、vulnerability や false-pass condition の報告前に [SECURITY.md](SECURITY.md) を読んでください。

## Contributing と governance

簡潔な counterexample、false-pass report、false-block report、accessibility fix、より良い kill condition を歓迎します。[CONTRIBUTING.md](CONTRIBUTING.md) から始めてください。fatal gate の変更は [GOVERNANCE.md](GOVERNANCE.md) に従います。

software は project identity **J. Tree** の下で保守され、Apache-2.0 で配布されます。`research/` の research note は別途 CC BY 4.0 です。custom software release bundle と Python distribution は research PDF/DOCX を除外します。GitHub が自動生成する tag source archive は research artifacts を含む全 tracked file を収録し、その中では `research/LICENSE` が適用されます。各 scope の license file を確認してください。

公開 attribution は意図的に pseudonymous です。fail-closed privacy gate が許可するのは宣言された project identity と GitHub-controlled bot identity だけです。[PRIVACY.md](PRIVACY.md) を参照してください。
