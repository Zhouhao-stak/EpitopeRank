# 肽预测（Peptide prediction）

> 适用对象：已经拿到**已量化剪接事件**和**读码框正确的 CDS 对照表**，希望把剪接来源的候选肽做
> MHC 结合、加工、稳定性预测、已知表位交叉核对和可解释排序的用户。
>
> 一句话边界：**结合预测 ≠ 抗原呈递 ≠ 免疫原性 ≠ 临床有效**。本层只做候选排序与证据留痕，
> 不做实验验证，也不从剪接坐标猜序列。

---

## 1. 它做什么

`epitoperank/peptide/` 是独立于既有剪接分析流水线的肽预测层，包含：

| 能力 | 实现 | 是否需要联网 |
| --- | --- | --- |
| 跨剪接连接点候选肽生成 | 翻译上游提供的 `reference_cds` / `altered_cds`，保留跨连接点且不在参考 ORF 中的 8–11 aa 肽 | 否 |
| 理化性质 | 分子量、pI、pH 7 净电荷、GRAVY、芳香性、脂肪族指数、疏水比例、Shannon 熵、低复杂度、P2/PΩ 锚定位 | 否 |
| HLA 解析与校验 | 两字段等位基因名、MHC 类别、部分超型映射、常用 panel | 否 |
| 自身/novelty 过滤 | 与用户提供的正常蛋白 FASTA 做**精确子串**匹配 | 否 |
| MHC-I 结合 | IEDB `mhci`（默认 NetMHCpan-4.1 EL） | 是 |
| MHC-II 结合 | IEDB `mhcii`（默认 NetMHCIIpan-4.1 EL），使用含侧翼的窗口 | 是 |
| MHC-I 加工 | IEDB `processing`（蛋白酶体 + TAP + MHC） | 是 |
| 肽-MHC 稳定性 | IEDB `mhci` 的 NetMHCstabpan-1.0 | 是 |
| MHC-NP | IEDB `mhcnp`（自然加工概率） | 是 |
| 已知表位查询 | IEDB Query API `tcell_search` | 是 |
| 综合排序 | 5 个分量加权 + 证据分层 A/B/C/D | 否 |

**不做**：FASTQ/BAM 事件发现、从坐标重建 ORF、NMD 判定、正常组织表达过滤、HLA 分型、
免疫肽组质谱验证、T 细胞实验。HLA 分型必须由 WES/WGS/RNA-seq 上游提供。

---

## 2. 快速开始

### 2.1 CDS 模式（推荐）

输入目录需能被现有加载器识别（rMATS 五类 JC 表或 `AS_event_master.tsv`），CDS 表必须是：

| 列 | 含义 |
| --- | --- |
| `event_id` | 必须与事件表完全一致 |
| `reference_cds` | 正常转录本 CDS，5′→3′，读码框已确定 |
| `altered_cds` | 剪接改变后 CDS，5′→3′，读码框已确定 |
| `junction_nt` | 异常 CDS 中**新连接点前**的核苷酸数（从 5′ 端计数） |

可选列：`orf_source`、`frame_status`（`in_frame`/`frameshift`）、`premature_stop`。

```bash
python run.py peptide \
  --input examples/peptide_demo \
  --cds examples/peptide_demo/splice_orfs.tsv \
  --alleles HLA-A*02:01 \
  --mhc-class class1 \
  --out out/peptide_demo
```

### 2.2 肽表 / FASTA 模式

肽表必须有 `peptide` 列（列名大小写不敏感），其余列原样带入候选表；也支持
`.fa`/`.fasta`/`.faa`。肽表模式接受 8–30 aa 的任意 IEDB 兼容长度（MHC-I 或
MHC-II 肽都可直接输入），超出 8–30 的行写入 `manifest.json` 的 `skipped`。

CDS 模式默认生成 `MHC_I_LENGTHS = (8, 9, 10, 11)`，可用 `--lengths 8,9,10,11`
限定；MHC-II 预测由 `--class2-window`（11–30，默认 15）自动从异常 ORF 截取窗口。

```bash
python run.py peptide \
  --peptides examples/peptide_demo/peptides.tsv \
  --alleles HLA-A*02:01 \
  --mhc-class class1 \
  --out out/peptide_table_demo
```

只做本地属性与排序（不联网）：

```bash
python run.py peptide \
  --peptides examples/peptide_demo/peptides.tsv \
  --predictor none \
  --out out/peptide_local_only
```

查看可用模型、参考表与上限：

```bash
python run.py peptide --capabilities
python run.py peptide --help
```

---

## 3. 预测器与 IEDB 方法

### 3.1 方法键（`METHODS`）

| 键 | IEDB `method` | 标签 | 工具 | MHC |
| --- | --- | --- | --- | --- |
| `netmhcpan_el` | `netmhcpan_el-4.1` | NetMHCpan-4.1 EL（IEDB recommended epitope） | `mhci` | I |
| `netmhcpan_ba` | `netmhcpan_ba-4.1` | NetMHCpan-4.1 BA（结合亲和力） | `mhci` | I |
| `netmhcstabpan` | `netmhcstabpan-1.0` | NetMHCstabpan-1.0（肽-MHC 稳定性） | `mhci` | I |
| `netmhciipan_el` | `netmhciipan_el-4.1` | NetMHCIIpan-4.1 EL | `mhcii` | II |
| `netmhciipan_ba` | `netmhciipan_ba-4.1` | NetMHCIIpan-4.1 BA | `mhcii` | II |
| `processing` | `recommended` | IEDB MHC-I processing（蛋白酶体 + TAP + MHC） | `processing` | I |
| `mhcnp` | `mhcnp` | MHC-NP（自然加工） | `mhcnp` | I |

默认：MHC-I 用 `netmhcpan_el`，MHC-II 用 `netmhciipan_el`（见 `DEFAULT_METHODS`）。
CLI 用 `--methods-class1` / `--methods-class2` 覆盖；键名必须以 `--capabilities` 输出为准。

### 3.2 长度与窗口

- MHC-I：`MHC_I_LENGTHS = (8, 9, 10, 11)`；`junction_peptides` 只生成 8–11 aa。
- MHC-II：`MHC_II_LENGTHS = (15,)`；`--class2-window` 允许 11–30，默认 15。
- 对每个候选肽，从异常蛋白中截取以肽为中心的 `class2_window` 窗口（蛋白不足窗口时取全长），
  再把窗口提交给 IEDB。**模型报告的是窗口内 9-mer core 的排名，不是这个 8–11 aa 肽本身的排名**，
  这是 MHC-II 的常规约定，也是报告里必须写明的局限。

### 3.3 加工（processing）

`predict_processing` 返回 `proteasome_score`、`tap_score`、`total_score`、
`processing_score`、`ic50_score`。`proteasome` 可选 `immuno`（默认）或 `constitutive`。

IEDB processing 服务在“FASTA 批量 + 多个长度”组合下会返回 HTTP 500，因此客户端**按
(等位基因, 长度) 逐个发请求**；这比结合预测慢，但稳定。

### 3.4 稳定性与 MHC-NP

- `--stability`：调用 NetMHCstabpan-1.0，结果字段与结合预测一致（`score`、`percentile_rank`）。
- `--mhcnp`：返回 `mhcnp_probability`（IEDB 的 `prob_score`）。MHC-NP 只支持 IEDB 列出的
  部分等位基因，失败会进入 `errors`，不会中断整次运行。

---

## 4. 已知表位查询

`--lookup-epitopes` 会对排名前 `max_lookup`（默认 25）条肽查询 IEDB Query API 的
`tcell_search?linear_sequence=eq.<PEPTIDE>`（每条默认 `limit=3`），结果写入
`epitope_matches.tsv`，字段包括 `candidate_peptide`、`mhc_class`、`mhc_restriction`、
`qualitative_measure`、`assay`、`source_organism`、`antigen`、`pubmed_id`。

命中表示**这个确切序列此前被 IEDB 收录过**，可能是病毒表位或自身肽；它**不是**“这个候选是
新抗原”的证据。查询失败只记 `errors`，不影响主表。

---

## 5. 自身/novelty 过滤

`--fasta` 可重复传入正常蛋白 FASTA（配对 normal、GTEx 翻译蛋白、UniProt canonical 等）。
实现是 `SelfReference`：

- 所有蛋白用 `*`（不可能出现在肽中的字符）拼接后做一次子串扫描，命中位置二分映射回蛋白 header；
- 每条肽最多保留 `MAX_HITS_PER_PEPTIDE = 25` 个命中蛋白，避免低复杂度肽撑爆输出；
- 只做**精确子串**匹配，不做 BLAST、不做近同源/单错配搜索。

结果写入候选表：

| 列 | 含义 |
| --- | --- |
| `self_hit` | `yes` / `no` / 空（未执行） |
| `self_hit_proteins` | `文件名:header` 列表 |
| `self_hit_count` | 命中蛋白数 |
| `novelty_status` | `present_in_supplied_proteome` / `not_in_supplied_proteome` / `not_evaluated` |

**未提供 FASTA 时 novelty 状态是 `not_evaluated`，评分时不会把“缺失”当作“新”**（见第 6 节）。
“没命中”只说明不在你提供的序列里，不能证明肿瘤特异。

---

## 6. 综合评分与证据分层

权重（`scoring.DEFAULT_WEIGHTS`）：

| 分量 | 权重 | 公式（`COMPONENT_DEFINITIONS`） |
| --- | --- | --- |
| `binding` | 0.40 | `1 / (1 + percentile_rank / 0.5)`，越低（越好）的百分位得分越高 |
| `processing` | 0.20 | `1 / (1 + exp(-1.5 × total_score))` |
| `expression` | 0.15 | `log1p(expression) / log1p(100)`，封顶 1（依赖输入单位） |
| `effect` | 0.15 | `min(1, |ΔPSI| / 0.5)` |
| `novelty` | 0.10 | 不在提供的正常蛋白组中为 1，否则 0；只有 `self_hit` 为布尔值时才计入 |

实现细节：

- 缺失分量**不插补**：按实际存在分量的权重和重新归一化，`components_used` /
  `components_missing` 逐行记录；
- `expression` 只有输入肽表带 `expression` 列时才存在（CDS 模式默认不带）；
- 证据分层（`evidence_tier`）：
  - **A**：`binding + processing + novelty + expression`
  - **B**：`binding + novelty`
  - **C**：`binding`
  - **D**：以上都不满足（通常是没有结合预测）
- 排序：按 `composite_score` 降序，其次按 `percentile_rank` 升序，再按肽序列稳定排序。

`composite_score` 是**分诊排序**，不是概率，不能当作“免疫原性分数”。

---

## 7. 缓存与溯源

- 缓存目录：`EPITOPERANK_PEPTIDE_CACHE`；未设置时用
  `default_runtime_root()/peptide_cache`（Windows 默认
  `%LOCALAPPDATA%\EpitopeRank\peptide_cache`；Linux 默认
  `$XDG_DATA_HOME/epitoperank/peptide_cache` 或 `~/.local/share/epitoperank/peptide_cache`）。
- 缓存键：`sha256(json([url, sorted(payload)]))[:32]`，即 `request_id`。同一请求命中缓存时
  不再访问网络（`calls` 里记为 `cached: true`）。
- 每个预测记录带：`method`、`method_label`、`source`（`IEDB`/`mhcflurry`）、`request_id`、
  `raw`（服务原始表格行）；`mhc_predictions.tsv` 的 `raw_json` 是 `raw` 的 JSON 字符串。
- `manifest.json` 记录 `inputs`（含输入文件 sha256）、`options`、`prediction_summary`
  （方法标签、请求 id、错误、分层计数）、`references`、`scoring`、`limitations`。
- 网络失败重试 `retries=2`（指数退避，单次上限 8 秒），单请求超时 `timeout=45.0` 秒，
  请求间最小间隔 `min_interval=0.15` 秒；失败写入 `errors`，不影响本地属性/排序。
- `--no-cache` 会同时关闭缓存读和写（用于强制刷新或排查问题）。

---

## 8. 参考数据（内置）

`epitoperank/peptide/reference/`：

| 文件 | 行数 | 内容 |
| --- | --- | --- |
| `hla_class1_alleles.tsv` | 10,386 | IEDB `netmhcpan_el-4.1` 接受的 HLA-I 名称 |
| `hla_class2_alleles.tsv` | 4,960 | IEDB `netmhciipan_el-4.1` 接受的 HLA-II 名称 |
| `known_epitopes.tsv` | 1,078 | IEDB T 细胞 assay 抽取（12 个常见等位基因各取 120 条，去重后 1,078） |
| `manifest.json` | — | 抓取时间、来源 URL、每个文件 sha256 |

加载器会做严格校验：`hla_class1_alleles.tsv` 中 10 个 `HLA-E*` / `HLA-G*` 名称不符合
A/B/C 两字段规则被跳过，因此 `capabilities()` 报告的是 **10,376** 个可用 HLA-I 等位基因；
HLA-II 4,960 个全部可加载。`known_epitopes.tsv` 是**真实 IEDB assay 记录**（含
`Positive`/`Negative` 结局），但结局来自不同实验类型，**不是**结合亲和力基准。

刷新：

```bash
python scripts/fetch_peptide_reference.py --epitopes-per-allele 120
# 只更新等位基因表：
python scripts/fetch_peptide_reference.py --skip-epitopes
```

脚本默认写入包内 `reference/`，可用 `--output` 改目录。等位基因表是**方法可用名称**，
不是人群频率；频率加权请用 AFND/IEDB 针对研究队列的数据，本仓库不内置。

---

## 9. API（FastAPI）

> 以仓库实现为准；字段若与 `epitoperank/api/app.py` 不一致，以后者为准。

| 方法 | 路径 | 请求 | 返回 |
| --- | --- | --- | --- |
| GET | `/api/peptide/capabilities` | — | `epitoperank.peptide.capabilities()` |
| GET | `/api/peptide/reference` | `mhc_class=1\|2`、`search=`、`limit=500`（上限 5000） | `{"total", "items":[{"allele","locus","supertype","mhc_class","source"}], "manifest":{...}}` |
| POST | `/api/peptide/predict` | `{"peptides":[...], "alleles":[...], "mhc_class":"class1\|class2\|both", "predictor":"iedb\|local\|auto\|none", "processing":bool（默认 true）, "lookup_epitopes":bool}` | `{"candidate_count","prediction_count","predictions":[...],"errors":[...],"methods":{...},"epitope_matches":[...]}` |
| POST | `/api/peptide/run` | `{"project_id"?,"input_dir"?,"cds_table"?,"peptides_file"?,"alleles":[...],"mhc_class"?,"predictor"?,"processing"?,"self_fastas"?:[...],"class2_window"?,"lookup_epitopes"?}` | `run()` 结果（含 `manifest`）；输出目录固定 `<input_dir>/peptide_results` |
| GET | `/api/peptide/file` | `input_dir=`、`name=` | 白名单文件：`splice_peptides.tsv` / `mhc_predictions.tsv` / `ranked_candidates.tsv` / `epitope_matches.tsv` / `manifest.json` / `summary.md` |

`/api/peptide/predict` 限制：**≤2000 条肽、≤8 个等位基因**，肽长 8–30 aa（否则 422）；
`lookup_epitopes=true` 时最多查前 **10** 条肽。预测需要联网（IEDB）或本地 `mhcflurry`；
`predictor=none` 时不调用模型、只返回空预测（用于离线冒烟）。`processing` 默认 `true`。

`/api/peptide/run` 的 `cds_table` 与 `peptides_file` 只能二选一；两者都不给且提供
`project_id` 时，会按表头自动识别项目目录里的编码序列对照表（文件名不限；多份时优先 `splice_orfs` / `coding_pairs`），也可用 `cds_table` 显式指定。所有输入文件
（含 `self_fastas`）必须位于 `input_dir` 内。`predictor` 同样接受 `none`（只做本地属性/排序）。

---

## 10. MCP 工具

启动：

```bash
python -m epitoperank.mcp.splice_server
```

新增工具（均惰性导入，模块导入本身不需要网络）：

| 工具 | 参数 | 上限 | 返回 |
| --- | --- | --- | --- |
| `peptide_capabilities` | — | — | `capabilities()` |
| `peptide_properties` | `peptides: list[str]` | 50 条 | `{"peptides":[describe(...)...]}` 或 `{"error": ...}` |
| `predict_mhc_binding` | `peptides`, `alleles`, `mhc_class="class1"`, `processing=false` | 20 条肽 / 4 个等位基因 | `{"predictions", "errors", "warning"}` |
| `lookup_epitope` | `peptides: list[str]` | 10 条 | `{"matches", "note"}` 或 `{"error": ...}` |

`predict_mhc_binding` 固定走 IEDB（`predictor="iedb"`），`processing=true` 时同时请求加工分数；
返回里的 `warning` 固定为 “Binding prediction is not presentation or immunogenicity.”。

---

## 11. 输出文件

| 文件 | 说明 |
| --- | --- |
| `splice_peptides.tsv` | 候选肽 + 事件元数据 + 理化性质 + novelty（字段见 `PEPTIDE_FIELDS`） |
| `mhc_predictions.tsv` | 长表，一行一个（肽, 等位基因, 方法）预测（字段见 `PREDICTION_FIELDS`） |
| `ranked_candidates.tsv` | 每个肽一行，含 `rank`、`composite_score`、`evidence_tier`、`components_used` 等（`RANKED_FIELDS`） |
| `epitope_matches.tsv` | 仅当 `--lookup-epitopes` 且有命中时生成 |
| `manifest.json` | 输入哈希、参数、方法、请求 id、错误、参考表、评分定义、局限性 |
| `summary.md` | 中文摘要（前 10 名 + 局限性） |

`ranked_candidates.tsv` 关键列：

```
rank  peptide  length  event_id  gene_symbol  event_type  fdr  delta_psi
best_allele  percentile_rank  mhc_class2_allele  mhc_class2_percentile
processing_total_score  evidence_tier  composite_score  components_used  self_hit
```

示例（离线运行，无预测，全部 D 层）：

```
rank  peptide    length  event_id    gene_symbol   event_type  fdr   delta_psi  ...  evidence_tier  composite_score
1     ATLGFGAY   8       DEMO:SE:3   DEMO_GENE_3   SE          0.01            ...  D              0
```

---

## 12. 解释规则与局限

1. **percentile rank 不是 Kd**：IEDB 返回的是百分位排名（0.06 表示排名前 0.06%），
   EL 模型输出的是洗脱配体排名，不是实测结合强度。
2. **结合 ≠ 呈递 ≠ 免疫原性**：没有 HLA 免疫肽组质谱，不能声称肽被呈递；没有四聚体/
   ELISpot/靶细胞杀伤，不能声称免疫原性。
3. **novelty 只在提供的蛋白组内成立**：没命中不等于正常组织不表达；GTEx junction 未检出
   也不等于序列不存在（可能只是组织不表达或深度不够）。
4. **MHC-II 是窗口排名**：报告的是含侧翼窗口（默认 15-mer，可配 11–30）内 9-mer core 的
   排名，不是 8–11 aa 肽本身的排名。
5. **ORF 必须来自上游**：平台不从剪接坐标、PSI 或基因名推测序列；`junction_nt` 必须与
   提供的 `altered_cds` 一致。
6. **上限**：IEDB 单请求最多 100 条序列（`MAX_SEQUENCES_PER_REQUEST`）；
   `PeptideOptions.max_predictions`（默认 2,000）会在预测前按
   `候选肽 × 等位基因 ×（processing 再算一遍）` 估算，超限直接抛错并要求显式放宽。
   API `/api/peptide/predict` 另有 2000 肽 / 8 等位基因 / 10 条 lookup 的硬上限。
7. **速率与可用性**：IEDB 是公共服务，客户端默认 0.15 秒最小间隔、2 次重试；服务故障会
   降级为 `errors`，不会伪造预测。
8. **HLA 分型来源**：RNA-seq 分型精度低于 WES/WGS；`hla_source` / `hla_confidence` 必须由
   用户提供并写入报告（新抗原分阶段流程已有该字段；本 CLI 不收集，需在报告中手工注明）。

---

## 13. 排错

| 症状 | 原因 / 处理 |
| --- | --- |
| `IEDB did not return a table` | 等位基因或长度不被该方法接受；先用 `--capabilities` 核对方法键，再用 IEDB 网页确认该等位基因受支持 |
| processing 返回 HTTP 500 | IEDB processing 对“FASTA + 多长度”不稳定；客户端已改为每个 (等位基因, 长度) 单独请求。若仍失败，检查是否被网关拦截 |
| `HLA allele ...` 报错 | 必须是两字段名，如 `HLA-A*02:01`、`HLA-DRB1*15:01`；`A*02:01` 也可，`HLA-E*01:01` 不受支持 |
| `mhcflurry is not installed` | `--predictor local` 需要 `pip install mhcflurry`；或用 `--predictor iedb` / `auto` |
| 运行成功但没有预测 | 检查是否有 `errors`；`--predictor none` 只做本地属性/排序；`predictor≠none` 但未填 `--alleles` 会直接报错 |
| 肽表行被跳过 | 长度不在 8–30 aa，或序列含非标准残基；见 `manifest.json` 的 `skipped` |
| 复现结果不一致 | 方法版本已固定（如 `netmhcpan_el-4.1`）；IEDB 服务端仍可能更新版本，`request_id` 与 `raw` 用于核对 |

---

## 14. 参考链接

- IEDB Analysis Resource Tools-API：<https://tools.iedb.org/main/tools-api/>
- IEDB Query API：<https://query-api.iedb.org/>
- IEDB 主页：<https://www.iedb.org/>
