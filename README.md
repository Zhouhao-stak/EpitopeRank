# SpliceGAIP

**AI-driven Alternative Splicing Analysis Agent Platform**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

SpliceGAIP 是在开源项目 [BioGAIP](https://github.com/zhangjy859/BioGAIP) 的多智能体架构基础上，结合剪接领域数据层（来自 SplicingNexus v2 的生产级事件标准化契约）重构而成的**面向可变剪接下游分析的 AI 智能体平台**。

自然语言驱动分析 → 自动生成分析流程 → 自动统计分析 → 自动解释生物意义 → 自动生成科研报告。

> 本文档即《SpliceGAIP 能力手册 v0.1.0》的完整 Markdown 版。带样式在线版见
> [能力手册 HTML](docs/manual/SpliceGAIP_Capability_Manual_v0.1.0.html) ·
> [PDF](docs/manual/SpliceGAIP_Capability_Manual_v0.1.0.pdf)。

---

## 快速上手

```bash
# 1. 安装（Python >= 3.10）
pip install -r requirements.txt

# 2. 运行完整分析（无需 LLM key；自治内核按数据自己决策）
python run.py analyze --input <已量化事件表目录> --query "分析RNA剪接变化"
# 报告：runtime/projects/<PID>/report.html

# 3. 多轮追问 / 续跑
python run.py followup --project-id <PID> --query "zoom into TP53"

# 4. （可选）接入 LLM 增强
export MODEL_API_BASE_URL="https://api.deepseek.com"
export MODEL_API_KEY="sk-..."
export MODEL_NAME="deepseek-flash"

# 5. 界面
python run.py serve --api --port 8800   # FastAPI
python run.py serve --ui  --port 8501   # Streamlit 仪表盘
```

### 部署方式

| 形态 | 命令 |
|---|---|
| 🐳 Docker | `docker compose up -d`（API 8800 / UI 8501） |
| 💻 Windows EXE | `pyinstaller packaging/SpliceGAIP.spec` |
| 🔧 源码 | `python run.py serve --api --port 8800` |

### 演示与文档

| 材料 | 内容 |
|---|---|
| 📘 [能力手册 HTML](docs/manual/SpliceGAIP_Capability_Manual_v0.1.0.html) · [PDF](docs/manual/SpliceGAIP_Capability_Manual_v0.1.0.pdf) · [Markdown](docs/manual/SpliceGAIP_Capability_Manual_v0.1.0.md) | v0.1.0：15 个功能模块、11 个规划项、3 份附录 |
| 🎬 [剪接来源候选新抗原 · 1:00](media/videos/splice-neoantigen-peptides.bilingual.mp4) | 事件 → 可翻译肽 → HLA 结合预测 → 132 条候选肽（中英双字幕轨） |
| 🎬 [完整分析流程 · 1:47](media/videos/pipeline-overview.bilingual.mp4) | 接入体检 → 六 Agent 流水线 → 火山图 / PSI 热图（中英双字幕轨） |
| 🗒 [双语讲解稿](docs/WALKTHROUGH.md) | 逐句中英对照，可直接当配音稿 |

[![剪接来源候选新抗原](media/posters/splice-neoantigen-peptides.jpg)](media/videos/splice-neoantigen-peptides.bilingual.mp4)
[![完整分析流程](media/posters/pipeline-overview.jpg)](media/videos/pipeline-overview.bilingual.mp4)

> 两段录屏均为**无配音界面实录**，讲解以字幕形式提供：`*.bilingual.mp4` 内含中文 / English 两条可切换字幕轨。

---

# SpliceGAIP 能力手册

**版本**：v0.1.0（依据 2026-10-29 仓库代码、`config/*.yaml`、`docs/` 与说明文档整理）
**适用对象**：分析人员（想知道能做什么）、开发者（想知道改哪里）、评审者（想知道边界在哪）
**状态图例**：✅ 已上线可用 ｜ 🟡 部分上线（有条件/实验性）｜ 🔵 开发中（规范已定、代码未落地）｜ ⚪ 规划中（仅路线图）

---

## 0. 一页速览

SpliceGAIP 是一个**面向"已完成可变剪接定量结果"的 AI 分析智能体平台**。它不接受 FASTQ，也不做比对；它接收 rMATS / SUPPA2 / MAJIQ / LeafCutter / 华大 RNAref 的已量化事件表，然后用一个**会自己决策、会自我质疑、会调用外部知识、会写报告**的智能体内核，产出可解释、可复现、可发表的分析结果。

```
已量化剪接事件表  →  智能接入与标准化  →  自治智能体（观察→决策→执行→校验→反思）
                                              ↓
                 统计/排序/图件 / 外部知识 / 假设检验 / 文献证据 / 实验室经验
                                              ↓
                                   HTML+PDF 科研报告 / 分阶段新抗原工作流
```

四条设计红线（贯穿全部功能）：

1. 没有模型 key 也必须能跑完（规则决策 + 离线 fallback，不是放录像）。
2. 不得从坐标猜序列、不得把单样本描述性 PSI 说成"肿瘤特异"。
3. MHC 结合预测 ≠ 抗原呈递 ≠ 免疫原性。
4. 每一次降级、放宽、跳过，都必须写进报告的方法与局限性。

---

## 1. 功能模块总览

| # | 模块 | 一句话用途 | 状态 | 主要入口 |
|---|---|---|---|---|
| M1 | 数据智能接入 | 认表头、认格式、认分组，把异构表格变成标准事件表 | ✅ | Web「数据接入」/ `POST /api/ingest/*` |
| M2 | 剪接事件解析与标准化 | 四类工具输出 → 统一 `AS_event_master` 契约 | ✅ | `splicegaip/splicing/parsers/` |
| M3 | 统计分析与质量门控 | 卡方+BH FDR、阈值过滤、综合评分排序 | ✅ | 智能体动作 / `analysis/statistics.py` |
| M4 | 可视化图件 | 6 张标准图 + 7 张按需图，PNG 300dpi + SVG | ✅ | Web「可视化」/ `analysis/*` |
| M5 | 自治智能体内核 | OODA 循环、预算、自适应阈值、跨运行经验 | ✅（默认） | `run.py analyze` / `agent/*` |
| M6 | 自我质疑（假设检验） | 解读前用 5 个预注册检验挑战自己的结果 | ✅ | `agent/hypothesis.py` |
| M7 | 外部知识技能 | MyGene / PubMed / Enrichr / 剪接解读接入循环 | ✅（需网络） | `skills/*` + `skills_bridge` |
| M8 | 文献 RAG 与实验室知识库 | 证据检索、跨项目复现基因沉淀 | ✅ | `knowledge/*`、`memory/` |
| M9 | 脚本式多智能体 | BioPlanner→BioAnalyst→BioInterpreter 固定流程 | ✅（兼容保留） | `--agent-mode scripted` |
| M10 | LLM 增强层 | 8 项"写作与理解"增强，无 key 自动降级 | ✅（需 key） | `llm/enrich.py` |
| M11 | 报告生成 | 自包含 HTML + PDF，六段式科学报告 | ✅ | Web「报告」/ `report/generator.py` |
| M12 | MCP 集成与 AI 助手 | 内置剪接工具服务端 + 自然语言→工具路由 | 🟡 | Web「AI 助手」/ `/api/mcp/*` |
| M13 | 剪接候选新抗原工作流 | 7 阶段逐一确认，事件→肽→HLA 预测→六段报告 | 🟡 | Web「剪接候选新抗原」 |
| M14 | 多形态交付 | Web / 桌面 EXE / Docker / Coolify / CLI / API | ✅ | `run.py serve`、`dist/` |
| M15 | 可观测性与可复现 | 全链路日志、SQLite 记忆、输入指纹 | ✅ | `observability.py`、`runtime/` |

---

## 2. 已有功能详解

每个模块统一按「核心用途 → 使用方式 → 输入/输出 → 适用场景」说明。

### M1 数据智能接入（异构表格 → 标准事件表）

**核心用途**
不要求用户先把数据整理成某一种格式。系统扫描目录（含子目录），识别表头与分隔符，判断"这是剪接事件表 / 表达矩阵 / 转录本定量 / 元数据"，再决定怎么接。

**使用方式**
1. Web 进入「AI 流水线」上传文件或目录 → 自动出预览（只读表头与最多三行样例，不遍历全表）。
2. 对未见过列名的表格，已配置的模型会拿到列名 + 样例，提出**映射建议**；建议必须通过"列是否真实存在"的校验，并由用户确认后才写入。
3. 华大 RNAref 单样本报告（`OC_001/OC_001.SE.xls` 等）会先被识别，再由用户**手工指定每个样本的生物学分组**，系统合并为 `standardized/AS_event_master.tsv` + `sample_metadata.tsv`。
4. 也可直接调接口：`POST /api/ingest/preview` → `POST /api/ingest/groups` → `POST /api/ingest/apply`。

**输入 / 输出**

| 项 | 内容 |
|---|---|
| 输入 | `.csv/.tsv/.txt/.tab`、制表符文本 `.xls`、真 Excel `.xls/.xlsx/.xlsm`、对应文本表的 `.gz` |
| 输出 | `standardized/AS_event_master.tsv`、`sample_metadata.tsv`、识别报告（每个文件的角色与告警） |
| 拒绝 | 表达量矩阵（FPKM/TPM/read_count）→ 提示"请另选剪接事件结果"；转录本定量（Bambu 等）→ 识别但不进事件流程 |

**适用场景**
- 手上是华大/诺禾等公司的单样本剪接报告，只有描述性 PSI，没有 p 值。
- 手上是各工具混用的历史结果，需要先统一再分析。
- 不确定某个文件到底是事件表还是表达矩阵。

**边界（必须知道）**
- 单样本报告没有组间检验，输出的 `p_value`/`FDR` **保持空白**，不能据此声称显著差异剪接。
- 分组永远由人确认，模型不猜分组。
- 只有 p 值没有 FDR 时，通用接入器只能对**当前完整事件表**做 BH；如果公开文件只是显著子集，必须补原始完整结果的 FDR。

---

### M2 剪接事件解析与标准化

**核心用途**
把不同工具的输出折叠成同一套事件契约（`event_id / gene_id / event_type / PSI / ΔPSI / p / FDR` + 质量列），后续所有统计、排序、报告都建立在这一层之上。

**使用方式**
自动识别，无需手动指定解析器（目录里放对文件名即可）：

| 输入 | 说明 |
|---|---|
| `SE.MATS.JC.txt` 等 rMATS 5 类 + `sample_metadata.tsv` | 含 0-based→1-based 坐标转换、逐样本 PSI 展开 |
| SUPPA2 `*.psi.tsv` | ΔPSI 来自均值差或外部文件 |
| MAJIQ TSV（含 `dPSI` / `P(dPSI)`） | 自动映射 |
| LeafCutter `*_cluster_significance.txt` | 自动映射 |
| `AS_event_master.tsv` | 直接读取（已是标准表） |

**输入 / 输出**
- 输入：上述任一事件表 + 可选 `sample_metadata.tsv`（`sample_id, group, condition, tissue, batch`）
- 输出：内存中的 `Dataset`（events / samples / validation）+ 落盘的标准表 + 校验告警

**适用场景**
同一课题里 rMATS 和 SUPPA2 混用；换工具后想复用同一套下游；做跨项目比较前先对齐契约。

---

### M3 统计分析与质量门控

**核心用途**
判断"哪些事件真的变了"，并把候选按证据强度排出先后。

**使用方式**
默认全部自动执行；也可在 CLI/配置里改阈值（`config/config.yaml → analysis`）：

| 参数 | 默认 | 含义 |
|---|---|---|
| `fdr_threshold` | 0.05 | 显著性门 |
| `delta_psi_threshold` | 0.10 | 效应量门 |
| `min_support_reads` | 10 | junction 支持读数下限 |
| `min_valid_samples` | 2 | 每组最少有效样本 |
| `top_candidates` | 20 | 保留候选数 |
| `enrichment_alpha` | 0.05 | 富集术语 FDR |

**输入 / 输出**
- 输入：标准化事件表（M2 产物）
- 输出：显著事件集合、候选排序表、富集结果（GO/KEGG/Reactome/MSigDB）、每步的通过/剔除计数
- 方法：卡方检验 + BH FDR；综合评分 = 0.4×显著性 + 0.3×效应量 + 0.2×生物学 + 0.1×文献

**适用场景**
标准两组对照（肿瘤 vs 正常、处理 vs 对照）；需要一份"能写进论文 Methods"的阈值与剔除理由。

---

### M4 可视化图件

**核心用途**
出可直接进投稿或汇报的图，而不是给开发看的调试图。

**使用方式**
- 标准 6 图随分析自动生成，落在 `runtime/projects/<id>/figures/`：`volcano`、`event_type_counts`、`psi_heatmap`、`psi_distribution`、`candidate_ranking`、`enrichment`。
- 按需 7 图在 Web「可视化」页触发：ΔPSI 瀑布图、ΔPSI ECDF、FDR scree、事件显著性散点、评分分解、样本构成、事件结构示意。
- 取图：`GET /api/figure/{project_id}/{figure_name}`。

**输入 / 输出**
输入为已持久化的项目状态（无需重跑分析）；输出 PNG（300 dpi）+ SVG 双份，缺数据时输出带说明的占位图而不是空白报错。

**适用场景**
组会汇报、论文 Figure 1–3、审稿人要求补充图。

---

### M5 自治智能体内核（默认模式）

**核心用途**
让流程按数据自己走，而不是按写死的脚本走。

```
观察(Profile) → 校验(Verify) → 决策(Decide) → 执行(Act) → 记录(Trace)
      ↑                                              │
      └──────── 目标未达成 → 反思重试 / 重规划（有预算） ┘
```

**使用方式**

```bash
# 默认 agentic：智能体自己看数据、自己定阈值
python run.py analyze --input examples/demo_rmats --query "分析RNA剪接变化"

# 想在人把关下跑：联网调用 / 放宽阈值 / 接受阻塞问题会先问你
python run.py analyze --input data/ --query "..." --autonomy assisted

# 多轮追问：在已有项目上续跑，不重跑整条流水线
python run.py followup --project-id <PID> --query "zoom into TP53"
python run.py followup --project-id <PID> --query "只看 SE 事件"
```

**核心机制与可调项**（`config.yaml → agent`）

| 机制 | 说明 | 配置 |
|---|---|---|
| 目标验收 | 用可判定的验收标准取代"终止令牌" | `state.py` |
| 数据画像 | 规模、FDR 覆盖率、缺失、支持读数、组平衡 | `profile.py` |
| 自适应阈值 | 默认门筛出 0 个事件时，按分布放宽到能出结果处，并记录**为什么改** | `adaptive_thresholds: true`、`target_significant: 100` |
| 结果体检 + 补救 | 产出 Issue(code, severity, suggestion) → 改阈值/重试/降级接受 | `reflection: true` |
| 硬预算 | 步数 / 时间 / 错误三重上限，绝不无限循环 | `max_steps: 20`、`max_seconds: 900`、`max_errors: 3` |
| 跨运行经验 | 相似数据上次用什么阈值成功过 | `episodic: true` |
| 多轮会话 | 状态快照 save/load + 规则化意图解析 | `session.py` |
| 人在回路 | 三类高风险决策先问人，`auto` 模式自动批准但留痕 | `autonomy`、`interactive.py` |

**内置动作（共 19 个）**
- 数据类：`profile_dataset`、`assess_quality`
- 分析类：`summarize_dataset`、`filter_significant_events`、`rank_candidates`、`run_enrichment`、`generate_figures`、`deep_dive_gene`、`adapt_thresholds`
- 自我质疑：`test_hypothesis`
- 外部知识：`annotate_genes`、`annotate_genes_enhanced`、`enrich_pathways`、`enrich_pathways_bioservices`、`search_literature`、`interpret_splice_event`
- 交付类：`collect_literature_evidence`、`interpret_candidates`、`generate_report`
- 经验类：`consult_knowledge`、`persist_knowledge`

**适用场景**
数据不合"教科书分布"（事件太少、FDR 缺失、组不平衡）；需要在报告里诚实交代"为什么最后用了 FDR<0.1"；无人值守跑批量项目。

---

### M6 自我质疑：预注册假设检验

**核心用途**
在下结论之前，先系统性地挑战自己的结果，被拒绝的检验直接变成报告里的局限性。

**使用方式**
`hypothesis_testing: true` 时自动在解读前执行，无需调用；CLI/接口也可单独触发。

| 检验 | H0 | 方法 |
|---|---|---|
| `dpsi_shift` | ΔPSI 分布未偏离 0 | Wilcoxon 符号秩（小样本退化 t 检验） |
| `direction_balance` | 上调/下调均衡 | 二项检验 |
| `event_type_bias` | 显著事件类型构成 = 背景构成 | 卡方拟合优度 |
| `coverage_confound` | 效应量与测序深度无关 | Spearman 秩相关 |
| `gene_recurrence` | 命中不集中于少数基因 | 置换检验（1000 次） |

**输入 / 输出**
输入为当前候选与事件集合；输出为逐项 p 值 + BH 校正 + 结论，写入报告 3.3 节与 Limitations。例如 demo 数据上 `coverage_confound` 被拒绝，报告就会主动声明"大 ΔPSI 事件受测序深度混杂"。

**适用场景**
审稿人问"你怎么排除测序深度混杂"；内部质控要求"每个结论都有对应的证伪尝试"。

---

### M7 外部知识技能（4 项）与开源后端

**核心用途**
把"查一下这个基因是什么、有没有文献、富集到什么通路、这个剪接事件该怎么解读"变成智能体可自主调用的动作。

**使用方式**
- 智能体自动调用（`agent.skills.enabled: true`，默认开）。
- 单独调用：`GET /api/skills/list` 取 schema，`POST /api/skills/execute` 执行。
- 关闭：`--skills off` 或 `SPLICEGAIP_ENABLE_SKILLS=0`。

| 技能 | 后端 | 用途 |
|---|---|---|
| `gene_annotation` | MyGene.info | 基因符号 / Ensembl / UniProt 注释，支持批量 |
| `literature_search` | PubMed | 按基因/事件检索文献并摘要 |
| `pathway_enrichment` | Enrichr（GSEApy） | GO / KEGG / Reactome / MSigDB 过表征分析 |
| `splice_interpretation` | 本地规则 + 模型 | 解释特定剪接事件的生物学后果 |

**桥接层的四个保证**：sync/async 隔离、单次超时（默认 10 s）、**每运行调用预算**（默认 4 次）、同参数缓存；失败即降级——网络挂了不会拖垮分析，只会记一条局限性。

**输入 / 输出**
输入为基因列表 / 事件 / 术语集；输出为结构化结果 + 数据来源与版本。可用性通过 `capabilities()` 暴露给 API 与报告（`gseapy` / `mygene` / `scipy` / `httpx` 是否装好、什么版本）。

**适用场景**
候选基因需要一句话功能注释；报告需要"文献支持度"；离线环境需要确认哪些能力当前不可用。

---

### M8 文献 RAG 与实验室知识库

**核心用途**
两层记忆：一层是"文献证据库"，一层是"本实验室历史上反复出现的基因"。

**使用方式**
- 文献：`knowledge/rag.py`（内置知识库 + PubMed + SQLite 文献库，NFS 安全），检索结果作为解读证据注入。
- 实验室知识：`consult_knowledge` 在解读前查库（默认要求 ≥2 个历史项目命中），`persist_knowledge` 在成功运行后把 Top 候选写回 `lab_knowledge.sqlite3`。
- 报告呈现：5.5「外部知识发现」与 5.6「实验室级复现」。

**输入 / 输出**
输入为候选基因、查询词、项目历史；输出为带来源的文献条目、跨项目复现基因表。

**适用场景**
同一实验室连续做多个肿瘤队列，希望"这个基因我们第三次看到了"这件事自动浮出来；需要证据可追溯而不是模型凭记忆说话。

---

### M9 脚本式多智能体（兼容模式）

**核心用途**
保留 BioGAIP 的经典三角色流水线，用于**回归对比**和教学演示：同一份数据，agentic 与 scripted 应当给出可解释的差异。

**使用方式**
```bash
python run.py analyze --input examples/demo_rmats --query "分析RNA剪接变化" --agent-mode scripted
```
或在 `config.yaml` 设 `agent.mode: scripted`、或环境变量 `SPLICEGAIP_AGENT_MODE`。

**结构**
```
BioPlanner（只规划，不计算） → BioAnalyst（summarize→filter→rank→enrich→figures）
                            → BioInterpreter（文献→解读→报告，终止令牌 SPLICEGAIP_DONE）
```
角色与工具在 `config/agent_config.yaml` / `tool_config.yaml` 声明；`max_turns: 40`；Agent 间用结构化消息协作，全部操作写入 SQLite Analysis Memory。

**输入 / 输出**
输入同 M5；输出同 M11，但阈值固定（FDR<0.05 且 |ΔPSI|>0.1），不做自适应。

**适用场景**
版本升级后的行为对比；需要"每次运行结果完全一致"的确定性场景；给新人讲清平台的三段式职责划分。

---

### M10 LLM 增强层（8 项）

**核心用途**
模型只负责"理解与表达"，不负责"算出数字"。8 项能力可逐项开关：

| 特性 | 作用 |
|---|---|
| `understand` | 自然语言分析目标理解 + 参数建议（`POST /api/understand`） |
| `plan` | Planner 的目标与局限性措辞精炼 |
| `interpret` | 结果的叙述性解读（导语 / 段落 / 要点） |
| `annotate` | 候选基因生物学注释 |
| `literature` | 文献证据摘要 |
| `limitations` | 补充研究设计层面的局限性 |
| `hypotheses` | 研究假设 + 验证实验建议 |
| `critique` | 对生成叙述做自动审查（可用 `MODEL_CRITIC_NAME` 单独指定审查模型） |

**使用方式**
三种配置途径任选：环境变量 / 项目根目录 `.env` / 界面「AI 助手 → 模型配置」。

```bash
export MODEL_API_BASE_URL="https://api.deepseek.com"
export MODEL_API_KEY="sk-..."
export MODEL_NAME="deepseek-flash"
export MODEL_THINKING=auto      # 工具调用关推理、报告解读开推理
```

**关键参数**：单次超时 120 s、每运行最多 16 次调用、最多 8 个基因注释、输出语言 `auto`（跟随提问语种，可强制 zh/en）、`provider: auto`（自动识别 deepseek/openai/moonshot/dashscope）、URL 中的密钥自动脱敏。

**输入 / 输出**
输入为结构化分析结果 + 用户查询；输出为文本段落 / JSON 建议，**必须经过本地校验**（建议的列名、参数、基因必须真实存在）。

**适用场景**
需要一段人话总结给临床或生物同事；需要模型帮着写 Limitations；想在无 key 的服务器上跑但本地有 key 时临时增强。

**降级行为**
无 key / 端点不通 → `fallback.py` 的离线确定性策略接管，报告照常生成，只是少了叙述润色，并在状态里标明"未使用模型"。

---

### M11 报告生成

**核心用途**
一次运行结束，直接拿到能发出去的东西。

**使用方式**
自动生成；或 Web「报告」页下载；或 `GET /api/report/{project_id}?format=html|pdf`。

**输出结构**
```
runtime/projects/<project_id>/
├── figures/        # PNG 300dpi + SVG
├── report.html     # 自包含（图片 base64 内嵌，可单文件传阅）
└── report.pdf      # reportlab 渲染
```
章节：Summary / Methods / Results（含 3.3 统计假设检验）/ Figures / Biological Interpretation（含 5.5 外部知识、5.6 实验室复现）/ Limitations / References。

**特点**
方法学留痕：阈值、放宽理由、软件版本、跳过步骤、被拒绝的假设检验全部进正文，而不是塞在附录里。

**适用场景**
组会汇报、投稿附件、给合作方的阶段性交付、内部质控归档。

---

### M12 MCP 集成与 AI 助手

**核心用途**
把平台能力**对外暴露成标准工具**，并让自然语言可以直接驱动这些工具。

**使用方式**
- 内置服务端 `splicegaip-builtin`（`http://127.0.0.1:9100`，随进程可用，无需配置），提供 5 个工具：`list_projects`、`project_summary`、`search_events`、`explain_event_type`、`compute_delta_psi`。
- 外部服务端：写 `~/.splicegaip/mcp/servers.json`，支持 `stdio` / `sse` / `http` 三种传输、官方 MCP SDK 与简易 `/tools` 适配两种协议。
- 查看与调用：`GET /api/mcp/servers`（含连接状态与工具 schema）、`POST /api/mcp/call`、`POST /api/mcp/agent`（自然语言 → 选工具 → 本地校验 → 执行）。
- Web「AI 助手」页可填自然语言指令，例如"查一下 CD44 有哪些显著剪接事件"。

**输入 / 输出**
输入为自然语言问题 + 可选 `project_id`；输出为工具调用结果。模型只提出 `{server, tool, arguments}`，**校验与执行留在本地**；无模型时确定性路由器按同一契约兜底。

**适用场景**
让 IDE 里的编码助手直接查项目结果；把平台接进实验室已有的 Agent 工作流；给非技术同事一个"问一句话就出数"的入口。

**现状说明**
工具路由与执行链路已通；但「AI 流水线」页那份双栏对话面板（v4 描述）仍是**前端演示态**——消息为模板渲染，未接真实多轮对话后端。这是 M12 与规划项 P7 的分界。

---

### M13 剪接候选新抗原工作流（分阶段）

**核心用途**
从"剪接事件"再往下走一层，走到"候选肽 + HLA 结合预测"，且**每一步都必须人工确认**，不允许一把梭。

**使用方式**
Web「剪接候选新抗原」→ 选项目 → 表单 → 逐阶段确认推进；进度存本机运行目录，重启可恢复；项目输入一变，指纹不匹配就强制重新审计。

| 阶段 | 做什么 | 必须提供 | 拒绝/停止条件 |
|---|---|---|---|
| 0 审计 | 声明这份数据最多能支撑到第几步 | `normal_design`、`genome_build`、`annotation_version`、`coordinate_system`、`input_kind`、`hla_source`、`hla_confidence` | 关键声明缺失即不进入后续阶段 |
| 1 事件 | 使用上游已量化事件，不重新发现 | 明确确认"输入是已量化事件表" + 事件表完整性声明 | 原始 reads/BAM 不支持；event_id 为空或重复即拒绝 |
| 2 事件过滤 | 坐标层过滤 | 支持读数阈值、最小样本数、且须确认该读数是否为 junction 支持 | 无事件存活 → 流程停止并记录 |
| 3 ORF | 读入**上游重建**的 ORF 表 | 四个 CDS 列 + `orf_source`、`frame_status`、`premature_stop`，可选 `last_junction_nt` | 缺字段即拒绝；不自行重建 ORF |
| 4 肽级正常过滤 | 配对正常 / GTEx / 全蛋白组三层精确匹配 + GTEx junction + 正常组织表达 | 三层 FASTA、事件与 GTEx 连接点表（同基因组版本）、正常表达表 | 跳过任一层须显式承认局限，否则报错 |
| 5 表达与复现率 | 是否有转录本、是否多患者复现 | `event_id, expression, expression_unit`，可选 `recurrence_count/total` | 复现率只作排序权重，不当硬门槛 |
| 6 HLA 预测 | IEDB **NetMHCpan 4.1 EL** | 真实 HLA-I 型别（如 `HLA-A*02:01`）+ 来源 + 置信度 | 组合数 >200 拒绝；预测失败逐条记入 manifest |
| 7 输出 | 固定六段报告 | — | — |

**输入 / 输出**
- 输入：项目数据目录内的全部文件（越界路径直接拒绝），CDS 表 / ORF 表 / FASTA / 连接点表 / 表达表
- 输出：`splice_peptides.tsv`、`mhc_i_predictions.tsv`、`neoantigen_manifest.json`（含跳过原因与预测错误）、六段结构化结果

**另有两项独立能力**
- 独立肽生成：`neoantigen.run()` 直接吃 CDS 对照表（`event_id, reference_cds, altered_cds, junction_nt`），翻译到首个终止密码子，保留跨连接点的 8–11 aa 肽，排除正常 ORF 内已出现的肽。
- moPepGen 适配：`scripts/mopepgen_docker.py` 调官方 1.4.6 容器，产出变异事件 GVF 与变异肽 FASTA，并保存命令、输入 SHA-256、镜像摘要与日志。**它不产出本流程阶段 3 需要的 CDS 对照表，也不是 HLA 预测**。

**适用场景**
已有配对 normal 与 HLA 分型、想快速得到"值得做实验验证"的候选清单；需要在方法学审查下交付"诚实的半程结果"。

**边界（写死在代码里）**
不猜序列；不把预测当呈递；不把单样本当肿瘤特异；不做综合评分排序（明确声明"未定义有证据支持的综合评分"）。

---

### M14 多形态交付

**核心用途**
同一套内核，四种用法：给自己跑、给同事用、给服务器部署、给其他 Agent 调。

| 形态 | 入口 | 适用 |
|---|---|---|
| CLI | `run.py analyze / followup / projects / status / serve` | 批量、脚本化、复现 |
| Web 单页应用 | `python run.py serve --ui` 或 `python serve_ui.py`；9 个页面：仪表盘 / AI 流水线 / 事件浏览器 / 可视化 / 基因浏览器 / 报告 / 剪接候选新抗原 / AI 助手 | 日常分析主入口 |
| 桌面窗口 | `desktop_ui.py`（pywebview 包一层本地服务）；`dist/SpliceGAIP.exe` 免 Python | 给不装环境的同事 |
| API | FastAPI（默认 8800）：分析、接入、状态、报告、图件、技能、MCP、新抗原 | 集成与自动化 |
| 容器 | `docker compose up -d`（API 8800 + UI 8501）；Coolify 一键；`nginx.conf` 反代 | 团队/服务器部署 |

**Streamlit 仪表盘**另有独立入口（`serve --ui`，默认 8501），页面为「上传+目标 → 结果（候选/图/富集）→ 下载报告」。

**适用场景**
本地探索用桌面版；团队共享用 Docker/Coolify；流水线集成用 API/CLI；无 Python 环境用 EXE。

---

### M15 可观测性与可复现

**核心用途**
让"这个结论是怎么来的"永远可追。

**机制**
- 每次运行记录：输入指纹、分析计划、生成代码、结果、解释、工作流日志（SQLite Analysis Memory）。
- 日志：`observability.py` 统一结构化输出，级别/来源/时间齐全。
- 状态库默认写本地磁盘（`/var/tmp/splicegaip`；Windows 为系统临时目录），因为 NFS 不支持 SQLite 文件锁——程序会自动探测并迁移。
- 决策轨迹：每一步"观察到了什么 → 为什么这么决定"都进 report Methods 与 workflow log。

**适用场景**
半年后要复现一张图；审稿人质疑阈值；交接给下一个学生。

---

## 3. 已有功能清单（按"能立刻用"排序）

| 能力 | 命令 / 入口 | 依赖 | 状态 |
|---|---|---|---|
| 一键完整分析（离线可用） | `run.py analyze --input ... --query ...` | Python 3.10+ | ✅ |
| 自适应阈值与自我纠错 | 默认开启 | — | ✅ |
| 多轮追问 | `run.py followup --project-id ... --query ...` | 已有项目 | ✅ |
| 5 项假设检验 | 默认开启 | scipy | ✅ |
| 4 项外部知识技能 | 默认开启 | 网络 + `gseapy`/`mygene`/`httpx` | ✅（缺依赖自动降级） |
| 8 项 LLM 增强 | `.env` 配 key | 模型端点 | ✅（无 key 降级） |
| HTML + PDF 报告 | 自动 / `GET /api/report/{pid}` | reportlab | ✅ |
| 13 张图件 | 自动 + 可视化页按需 | matplotlib | ✅ |
| 6 类输入格式自动识别 | 上传目录 | — | ✅ |
| 华大 RNAref 单样本接入 | 接入向导 | 人工分组 | ✅ |
| MCP 内置 5 工具 | `GET /api/mcp/servers` | — | ✅ |
| 外部 MCP 服务端接入 | `~/.splicegaip/mcp/servers.json` | `mcp` SDK | ✅ |
| 自然语言 → MCP 工具路由 | `/api/mcp/agent` | 模型（可选） | 🟡（无模型走确定性路由） |
| 新抗原 7 阶段工作流 | Web 新抗原页 | 用户自备 ORF/FASTA/HLA | 🟡（实验性，逐阶段确认） |
| 独立肽生成 | `neoantigen.run()` | CDS 对照表 | 🟡 |
| moPepGen 容器适配 | `scripts/mopepgen_docker.py` | Docker + 镜像 | 🟡（探索性，不接 ORF 阶段） |
| 桌面 EXE | `dist/SpliceGAIP.exe` | — | ✅ |
| Docker / Coolify 部署 | `docker compose up -d` | Docker | ✅ |
| 人机交互确认 | `--autonomy assisted` | — | ✅ |

---

## 4. 规划中 / 开发中功能

> 状态判定标准：**🔵 开发中** = 规范与接口契约已在仓库中定义（文档/配置/字段），但核心实现未落地；**⚪ 规划中** = 仅出现在路线图或配置注释中，无代码痕迹。

### P1 自动 ORF 重建（新抗原阶段 3 的自动化）

| 项 | 内容 |
|---|---|
| **预期目标** | 输入事件表 + 参考基因组 FASTA + GTF/CDS 注释，自动按事件类型（SE/RI/A3SS/A5SS/MXE）拼接 novel transcript，判定 in-frame / frameshift，翻译至首个终止密码子，计算 `junction_nt`，并按 50 nt 距离规则给出 NMD 候选 |
| **解决的具体问题** | 目前阶段 3 必须由用户提供"已重建的 ORF 表"，这是整条链路里人工成本最高、最容易出错的一步；没有它，新抗原分析对绝大多数用户直接断在第三步 |
| **当前状态** | 🔵 开发中：`docs/prompts/splice-neoantigen-pipeline.md` 已把阶段 3 的方法学与字段契约写死（`orf_source` / `frame_status` / `premature_stop` / `last_junction_nt`），代码中明确声明"自动 ORF 重建尚未实现" |
| **使用示例（预期）** | `新抗原页 → 阶段 3 → 选择基因组 FASTA + GTF → 一键重建 → 自动产出四列 CDS 表 + NMD 标记，人工抽查后确认进入阶段 4` |
| **依赖/风险** | 转录本注释版本必须与事件坐标一致；不同事件类型的拼接规则不同，误拼会静默产生假肽——因此必须有逐事件可追溯的拼接日志 |

### P2 原始数据在线处理（Phase 2：FASTQ → 比对 → 剪接检测）

| 项 | 内容 |
|---|---|
| **预期目标** | 平台上直接完成 FASTQ 质控 → STAR/HISAT2 比对 → rMATS/SUPPA2 在线运行 → 自动进入现有分析链路 |
| **解决的具体问题** | 当前 Phase 1 只吃"已量化事件表"，用户必须在命令行里自己跑完一整套生信流程才能用上平台；这把非生信背景的用户挡在门外 |
| **当前状态** | ⚪ 规划中（README 路线图 Phase 2；目录中无比对/定量代码） |
| **使用示例（预期）** | `上传 6 个 FASTQ + sample_metadata.tsv → 选择 GRCh38/GENCODE → 平台排队跑比对与 rMATS → 自动生成 SE.MATS.JC → 直接进智能体分析` |
| **依赖/风险** | 需要重型算力与任务队列；参考基因组版本管理；运行时间从分钟级升到小时级 |

### P3 专用 QC 智能体

| 项 | 内容 |
|---|---|
| **预期目标** | 独立的质控角色，在分析前对测序深度、比对率、样本相关性、批次效应做系统体检并给出"能否继续"的判定 |
| **解决的具体问题** | 现在质控散落在 `profile_dataset` / `assess_quality` 两个动作与假设检验中，缺少一个"专职说不"的角色；坏数据仍可能被一路分析下去 |
| **当前状态** | ⚪ 规划中（`config/agent_config.yaml` 注释明确写"future extensions (e.g. a dedicated QC agent in Phase 2)"） |
| **使用示例（预期）** | `运行前自动插入 QC 阶段 → 检出样本 3 与其余样本相关性 <0.7 → 报告建议剔除并给出依据 → 用户确认后继续或中止` |

### P4 转录本定量独立流程（长读长 / Bambu 等）

| 项 | 内容 |
|---|---|
| **预期目标** | 把逐转录本 count/CPM/TPM 矩阵当作独立数据类型分析（差异转录本使用、isoform switch），而不是硬塞进事件 PSI 流程 |
| **解决的具体问题** | 目前长读长数据能被"识别"但明确"不进本流程"，用户拿到识别结果后无路可走 |
| **当前状态** | ⚪ 规划中（README 已声明"转录本定量分析是独立数据类型，尚未接入本流程"） |
| **使用示例（预期）** | `上传 Bambu 的 transcript count 矩阵 → 选择"转录本定量分析" → 输出 isoform 使用差异 + isoform switch 图` |

### P5 单细胞 RNA-seq 与多组学（Phase 3）

| 项 | 内容 |
|---|---|
| **预期目标** | 单细胞层面的剪接分析（cell-type 特异 PSI）、与转录组/蛋白组/甲基化的联合分析 |
| **解决的具体问题** | 现有全部统计假设建立在 bulk 组间比较上，无法回答"哪个细胞亚群发生了这个剪接改变" |
| **当前状态** | ⚪ 规划中（路线图 Phase 3） |
| **使用示例（预期）** | `上传 scRNA-seq 的 splice junction count → 按细胞类型聚类 → 输出亚群特异剪接事件与标记基因联动` |

### P6 自主生物信息学研究员（Phase 4）

| 项 | 内容 |
|---|---|
| **预期目标** | 从"给定数据和目标"进化到"给定科学问题"，自主提出假设、设计分析、迭代验证、撰写可投稿文稿 |
| **解决的具体问题** | 当前智能体的自主性局限于"在既定流水线内做决策"，科学问题的提出仍完全依赖人 |
| **当前状态** | ⚪ 规划中（路线图 Phase 4，远景） |
| **使用示例（预期）** | `输入"这批肿瘤样本为什么对某药不敏感" → 自主生成剪接相关假设 → 设计并执行验证分析 → 输出带证据链的研究报告` |

### P7 AI 助手完整多轮对话

| 项 | 内容 |
|---|---|
| **预期目标** | 把「AI 流水线」页的双栏对话面板接上真实后端：真实 LLM 回复、WebSocket 流式、多轮上下文记忆、Agent 协作可视化 |
| **解决的具体问题** | 目前对话面板的消息是前端模板渲染，用户问"为什么选这个 FDR 阈值"得不到真实回答；而 MCP 工具路由已经能用，两者之间缺一层"对话壳" |
| **当前状态** | 🟡 部分上线：`/api/mcp/agent`（自然语言→工具→本地执行）已通，`/api/understand`（目标理解）已通；面板本身仍为演示态 |
| **使用示例（预期）** | `在面板输入"为什么不选 FDR 0.01" → 智能体读取本次运行的状态与决策轨迹 → 回答"0.01 下仅剩 2 个事件，低于验收标准 100，因此放宽到 0.05 并记录在 Methods"` |
| **依赖** | 需要把 `AgentState` 与决策轨迹暴露为可查询的会话上下文；WebSocket 通道 |

### P8 新抗原候选综合评分

| 项 | 内容 |
|---|---|
| **预期目标** | 定义一个**有证据支持**的综合评分（表达 × 复现率 × 结合 rank × 事件质量），用于候选排序 |
| **解决的具体问题** | 当前六段报告明确写"未定义有证据支持的综合评分，候选表未作综合评分排序"，用户拿到候选表后仍需自己排序 |
| **当前状态** | ⚪ 规划中（`neoantigen_workflow.py` 局限性中显式声明） |
| **使用示例（预期）** | `阶段 7 输出按综合评分降序的候选表，并显示每项权重贡献` |

### P9 内置参考数据库与版本管理

| 项 | 内容 |
|---|---|
| **预期目标** | 内置/托管 GTEx junction 表、UniProt 全蛋白组、常见基因组版本的 CDS 注释，并做版本一致性校验 |
| **解决的具体问题** | 阶段 4 现在要求用户自备三层 FASTA 与连接点表，且"基因组版本需一致"完全靠人核对；这是新抗原流程第二个高门槛 |
| **当前状态** | ⚪ 规划中（文档反复强调"文件来源、覆盖范围及版本须由用户核实"） |
| **使用示例（预期）** | `阶段 4 下拉选择 GTEx v8 / UniProt 2024_05 / GRCh38 → 系统自动校验事件构建版本并提示不匹配项` |

### P10 MHC-II 与免疫肽组证据（文档提及，未排期）

| 项 | 内容 |
|---|---|
| **预期目标** | 支持 MHC-II 预测模型；接入 HLA 免疫肽组质谱证据 |
| **解决的具体问题** | 当前仅 MHC-I（8–11 aa, NetMHCpan 4.1 EL），CD4+ T 细胞相关候选完全缺失；且无法确认肽是否真被呈递 |
| **当前状态** | ⚪ 规划中（提示词中明确"MHC-II 是另一套模型，不要混用"，属方法学提醒而非功能承诺） |

### P11 工程质量项（非功能，但影响可用性）

| 项 | 现状 | 目标 |
|---|---|---|
| 测试覆盖率 | 27%，CI 门槛 20% | 逐步提高门槛；补齐数据处理、Agent、UI 覆盖 |
| 文档完整度 | `docs/` 仅 `prompts/`；README 引用的 `docs/USAGE.md` 缺失 | 补齐操作手册（本文件为第一步） |
| 日志/安全 | 已有结构化日志与密钥脱敏 | 生产级文件轮转、权限模型 |

---

## 5. 新旧功能关系与演进方向

### 5.1 演进主线（一张图看清）

```
v1 固定脚本三智能体（BioPlanner→BioAnalyst→BioInterpreter）
        │  问题：阈值写死，数据不合假设就交出空结果
        ▼
v2 自治内核 OODA（决策引擎 + 校验 + 反思 + 预算 + 跨运行经验）
        │  问题：会决策但不会怀疑自己，也不会找外部证据
        ▼
v3 自我质疑 + 外部知识 + 人在回路（5 项假设检验 / 4 项技能 / assisted 模式）
        │  问题：bulk 事件层到顶了，用户还想往下走到肽和 HLA
        ▼
v4 分阶段新抗原工作流（事件 → ORF → 肽 → 表达 → HLA → 六段报告）
        │  问题：阶段 3 依赖人工重建 ORF；原始数据仍需在平台外处理
        ▼
v5（规划）自动 ORF 重建 + 内置参考库 + FASTQ 在线 pipeline + 单细胞/多组学
```

### 5.2 具体替代 / 增强关系

| 旧功能 | 新功能 | 关系 | 兼容策略 |
|---|---|---|---|
| 固定阈值过滤 | 自适应阈值 + 跨运行经验记忆 | **增强**（旧行为可通过 `target_significant` 与固定配置复现） | `--agent-mode scripted` 完全等价历史行为，用于回归对比 |
| 三角色脚本流水线 | 自治 OODA 内核 | **并存**（前者为对照基线，后者为默认） | `agent.mode` 切换，`config/agent_config.yaml` 保留角色声明 |
| 单次运行 | 多轮追问 `followup` | **增强**（同一项目状态快照续跑，不重跑流水线） | 新增子命令，旧命令不变 |
| 手写 HTTP 富集 | GSEApy/Enrichr + MyGene 客户端 | **替换**（缺依赖自动回落到手写实现） | `capabilities()` 暴露实际后端与版本 |
| 技能只能单独调 API | 技能接入智能体循环（含预算/缓存/降级） | **增强**（从"工具"变成"动作"） | `--skills off` 一键回退 |
| 只出结果 | 先自我质疑再解读 | **增强**（被拒绝的检验进 Limitations） | `hypothesis_testing` 开关 |
| 新抗原脚本一把梭 | 7 阶段逐一确认 + 状态可恢复 + 输入指纹 | **替代**（实验性脚本入口仍在，但不再作为推荐路径） | `neoantigen.run()` 保留为独立肽生成 |
| moPepGen 直接当结果 | 明确降级为"探索性输入"，不接 ORF 阶段 | **收窄**（能力边界写进文档与界面提示） | 输出仍保存命令与哈希供追溯 |
| v3 单栏 UI | v4 双栏（工作流+对话+日志） | **增强**（对话面板仍为演示态，见 P7） | `git checkout v3-professional-ui` 可回滚 |
| 网页内嵌 `web_ui` | 桌面 EXE / Docker / Coolify 多形态 | **扩展**（同一 FastAPI + 静态 UI） | 全部复用同一 `create_app()` |

### 5.3 演进方向的三条原则

1. **能力往下走，证据链不放松**：从事件走到肽、走到 HLA，每多走一步就多一层强制声明与局限性，而不是多一层"看起来更厉害"的数字。
2. **人工确认点前移而非取消**：阶段 3 要自动化的是"重建 ORF"这个体力活，而不是"跳过确认"这个安全阀；P1 落地后仍要求人工抽查。
3. **默认路径变强，回退路径保留**：每个新机制（自适应、技能、假设检验、新抗原）都有开关或旧模式；`scripted` 模式被长期保留为行为等价基线。

### 5.4 读者最可能关心的三个判断

- **现在能用吗？** 能。给一份 rMATS 结果，一条命令出报告，无需任何 API key。
- **新抗原能信吗？** 能信"它做到了哪一步"，不能信"它证明了免疫原性"。阶段化设计就是为了让这句话可核查。
- **什么时候能上传 FASTQ？** 路线图 Phase 2，属规划中；当前请在上游跑完比对与定量。

---

## 6. 能力边界（明确不做什么）

| 不做 | 原因 | 替代路径 |
|---|---|---|
| FASTQ 质控 / 比对 / 转录本组装 | Phase 1 定位为"下游分析" | 上游 STAR/HISAT2 + rMATS/SUPPA2，结果表喂给平台（P2 规划中） |
| 从坐标猜 CDS / ORF 序列 | 会静默产生假肽 | 提供 frame-correct CDS，或等 P1 自动重建 |
| 对显著子集重算 BH | 统计上不成立 | 提供完整事件表 |
| 把单样本描述性 PSI 说成肿瘤特异 | 无组间检验 | 提供配对 normal 与生物学重复 |
| 从事件 ID 反推蛋白序列 | 同上 | 阶段 3 显式输入 |
| 声称抗原呈递 / 免疫原性 / 临床有效 | 需要质谱与功能实验 | 实验验证（四聚体 / ELISpot / 杀伤） |
| 把 GTEx 未检出等同于"正常组织不存在" | 可能只是不表达或深度不足 | 序列层过滤 + 表达证据 |
| 无限自我重试 | 预算三重上限 | 停止并写入局限性 |

---

## 7. 三条典型上手路径

**路径 A｜有一份 rMATS 结果，想尽快出报告（5 分钟）**
```bash
python run.py analyze --input examples/demo_rmats --query "分析RNA剪接变化"
# 打开 runtime/projects/<PID>/report.html
```

**路径 B｜数据不理想，想看智能体怎么自救**
```bash
python examples/make_hard_cases.py examples
python run.py analyze --input examples/hard_rescuable --query "找出差异剪接事件"  # 放宽阈值救回
python run.py analyze --input examples/hard_empty     --query "找出差异剪接事件"  # 承认无解并写明局限
```

**路径 C｜已有 HLA 分型，想筛候选肽**
```
Web → 剪接候选新抗原 → 选项目 → 阶段 0 审计（填齐 7 项声明）
    → 阶段 1/2 事件与过滤 → 阶段 3 上传上游 ORF 表 → 阶段 4 三层正常过滤
    → 阶段 5 表达与复现 → 阶段 6 填 HLA（如 HLA-A*02:01）→ 阶段 7 六段报告
```

---

## 附录 A｜接口速查

| 分组 | 端点 |
|---|---|
| 健康与模型 | `GET /api/health`、`GET /api/llm/status`、`POST /api/llm/config` |
| 理解 | `POST /api/understand` |
| 分析 | `GET /api/projects`、`GET /api/status/{pid}`、`POST /api/analyze` |
| 接入 | `POST /api/ingest/preview`、`POST /api/ingest/groups`、`POST /api/ingest/apply` |
| 上传 | `POST /api/upload`、`POST /api/upload-debug` |
| 报告/图件 | `GET /api/report/{pid}?format=`、`GET /api/figure/{pid}/{name}` |
| 新抗原 | `GET /api/neoantigen/readiness/{pid}`、`POST /api/neoantigen/audit`、`POST /api/neoantigen/workflow/start|advance`、`GET /api/neoantigen/workflow/{id}`、`POST /api/neoantigen/run`、`POST /api/neoantigen/mopepgen`、`GET /api/neoantigen/file`、`POST /api/neoantigen/reveal` |
| 技能 | `GET /api/skills/list`、`POST /api/skills/execute` |
| MCP | `GET /api/mcp/servers?refresh=`、`POST /api/mcp/call`、`POST /api/mcp/agent` |

## 附录 B｜配置速查（`config/config.yaml`）

| 段 | 关键项 | 默认 |
|---|---|---|
| `llm` | `features`（8 项，或 all）、`insight_timeout_seconds`、`max_calls_per_run`、`max_genes`、`language`、`thinking` | all / 120 / 16 / 8 / auto / auto |
| `analysis` | `fdr_threshold`、`delta_psi_threshold`、`min_support_reads`、`min_valid_samples`、`top_candidates`、`enrichment_alpha` | 0.05 / 0.1 / 10 / 2 / 20 / 0.05 |
| `agent` | `mode`、`max_steps`、`max_seconds`、`max_errors`、`adaptive_thresholds`、`target_significant`、`reflection`、`episodic`、`autonomy`、`hypothesis_testing` | agentic / 20 / 900 / 3 / true / 100 / true / true / auto / true |
| `agent.skills` | `enabled`、`max_calls`、`timeout` | true / 4 / 10 |
| `report` | `formats` | html, pdf |
| `paths` | 状态库位置（默认随 runtime 根目录迁移） | 系统临时目录 |

## 附录 C｜状态统计

| 分类 | 数量 |
|---|---|
| 已上线可立即使用 | 20 项 |
| 部分上线 / 实验性 | 5 项（MCP 自然语言路由、新抗原 7 阶段、独立肽生成、moPepGen 适配、新抗原就绪检查） |
| 开发中 | 1 项（P1 自动 ORF 重建） |
| 规划中 | 8 项（P2–P10 中的规划项） |
| 工程改进项 | 3 项（覆盖率、文档、日志/安全） |

---

*本手册依据仓库现状整理；标注为 🟡/🔵/⚪ 的功能请以实际运行结果为准，不要把"规范已定义"当作"功能已可用"。*
