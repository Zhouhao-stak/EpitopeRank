# SpliceGAIP

**AI-driven Alternative Splicing Analysis Agent Platform**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

SpliceGAIP 是在开源项目 [BioGAIP](https://github.com/zhangjy859/BioGAIP) 的多智能体架构基础上，
结合剪接领域数据层（来自 SplicingNexus v2 的生产级事件标准化契约）重构而成的
**面向可变剪接下游分析的 AI 智能体平台**。

自然语言驱动分析 → 自动生成分析流程 → 自动统计分析 → 自动解释生物意义 → 自动生成科研报告。

---

## 演示与文档 · Demos & Docs

| 材料 Material | 内容 Content |
|---|---|
| 📘 [能力手册 HTML](docs/manual/SpliceGAIP_Capability_Manual_v0.1.0.html) · [PDF](docs/manual/SpliceGAIP_Capability_Manual_v0.1.0.pdf) · [Markdown](docs/manual/SpliceGAIP_Capability_Manual_v0.1.0.md) | v0.1.0：15 个功能模块、11 个规划项、3 份附录，按「分析人员 / 开发者 / 评审者」三条读法组织 |
| 🎬 [剪接来源候选新抗原 · 1:00](media/videos/splice-neoantigen-peptides.bilingual.mp4) | 事件 → 可翻译肽 → HLA 结合预测 → 132 条候选肽实录（中英双字幕轨） |
| 🎬 [完整分析流程 · 1:47](media/videos/pipeline-overview.bilingual.mp4) | 接入体检 → 六 Agent 流水线 → 火山图 / PSI 热图（中英双字幕轨） |
| 🗒 [双语讲解稿](docs/WALKTHROUGH.md) | 逐句中英对照，可直接当配音稿；含字幕重生成命令与术语对照表 |
| 🖼 [媒体素材索引](media/README.md) | 原始录屏、双轨软字幕版、`.srt` 文件清单与播放说明 |

[![剪接来源候选新抗原](media/posters/splice-neoantigen-peptides.jpg)](media/videos/splice-neoantigen-peptides.bilingual.mp4)
[![完整分析流程](media/posters/pipeline-overview.jpg)](media/videos/pipeline-overview.bilingual.mp4)

> 两段录屏均为**无配音界面实录**，讲解以字幕形式提供：`media/videos/*.bilingual.mp4` 内含
> 中文 / English 两条可切换字幕轨，原始无字幕文件与 `.srt` 同在 `media/` 下。
> 手册与讲解稿有在线版：<https://zhouhao-stak.github.io/SpliceGAIP/docs/manual/SpliceGAIP_Capability_Manual_v0.1.0.html>

## 定位（Phase 1）

```
已完成分析结果（rMATS / SUPPA2 / MAJIQ / LeafCutter / 标准化事件表）
        ↓
SpliceGAIP 多智能体系统（BioPlanner → BioAnalyst → BioInterpreter）
        ↓
可视化 + 候选基因排序 + 功能富集 + 文献证据 + 科研报告（HTML/PDF）
```

Phase 1 **不处理** FASTQ、比对（STAR/HISAT2）、转录本组装——这些属于 Phase 2。
输入是「已量化的剪接分析结果」，输出是「可解释、可复现、可发表的剪接分析报告」。

## 部署方式

### 🐳 Docker 容器部署

```bash
docker compose up -d
# API: http://localhost:8800
# UI:  http://localhost:8501
```

### 💻 Windows EXE 便携版

用 `packaging/` 下的 PyInstaller spec 重新打包（图标与运行时 hook 同目录）：

```bash
pyinstaller packaging/SpliceGAIP.spec        # 桌面端
pyinstaller packaging/SpliceGAIP-Web.spec    # Web 端
```

### 🔧 源码运行

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py serve --api --port 8800   # FastAPI
python run.py serve --ui  --port 8501   # Streamlit 仪表盘
```

---

## 从 BioGAIP 继承了什么

| 能力 | 来源 | 现状 |
|---|---|---|
| Multi-Agent 架构（AutoGen `SelectorGroupChat`） | BioGAIP `bioGen/biogen.py` | ✅ 保留，简化为 3 个核心 Agent |
| YAML 声明式 Agent/工具配置 | BioGAIP `config/load_config.py` | ✅ 保留（`config/agent_config.yaml`、`config/tool_config.yaml`） |
| Tool Calling（AutoGen `FunctionTool`） | BioGAIP 工具注册模式 | ✅ 保留，8 个平台工具 |
| RAG 知识增强（文献检索 + 持久文献库） | BioGAIP `bioGen/pubmed/` | ✅ 精简重建（`splicegaip/knowledge/`，SQLite 存储，NFS 安全） |
| 长上下文/记忆管理 | BioGAIP memory 体系 | ✅ 重组为 SQLite Analysis Memory |

## 从 SplicingNexus v2 继承了什么

| 资产 | 现状 |
|---|---|
| `AS_event_master` 事件契约（event_id/gene_id/event_type/PSI/ΔPSI/p/FDR + 质量列） | ✅ `splicegaip/splicing/schema.py` |
| rMATS JC 表标准化（含 0base→1-based 坐标转换、样本 PSI 展开） | ✅ `splicegaip/splicing/parsers/rmats.py` |
| 卡方检验 + BH FDR | ✅ `splicegaip/analysis/statistics.py` |
| 置信分级/质量门控思路 | ✅ `splicegaip/splicing/filtering.py` |
| 图件输出规范（PNG 300dpi + SVG） | ✅ `splicegaip/analysis/visualization.py` |

## 快速开始

```bash
# 1. 安装（Python >= 3.10）
pip install -r requirements.txt

# 2. 运行完整分析（无需 LLM key；自治内核按数据自己决策，不依赖模型）
python run.py analyze --input <已量化事件表目录> --query "分析RNA剪接变化"

# 3. 多轮追问 / 续跑：在已有项目上追加意图，从上次状态继续，不重跑整条流水线
python run.py followup --project-id <上一步的 PID> --query "zoom into TP53"

# 4. （可选）接入真实 LLM（环境变量 / .env 文件 / 界面「AI 解读 → 模型配置」三选一）
export MODEL_API_BASE_URL="https://api.deepseek.com"   # DeepSeek 无需 /v1
export MODEL_API_KEY="sk-..."
export MODEL_NAME="deepseek-flash"                     # DeepSeek-V4.1-Flash
export MODEL_THINKING=auto                             # 工具调用关推理、报告解读开推理
# 接入后，除多智能体编排外还会启用 8 项结果增强：目标理解、计划精炼、
# 叙述性解读、候选基因注释、文献摘要、局限性补充、研究假设与验证建议、自动审查。

# 5. 界面
python run.py serve --api --port 8800     # FastAPI: /api/analyze /api/status /api/report
python run.py serve --ui  --port 8501     # Streamlit 仪表盘
```

> **运行位置说明**：SQLite 状态库默认写本地磁盘 `/var/tmp/splicegaip/`（NFS 主目录
> 不支持 SQLite 文件锁，程序会自动探测并迁移）。

## 输入格式（Standard BioAnalysis Format）

自动识别以下输入（目录形式）：

| 输入 | 说明 |
|---|---|
| rMATS JC 表（`SE.MATS.JC.txt` 等 5 类）+ `sample_metadata.tsv` | 自动标准化为事件主表 |
| SUPPA2 `*.psi.tsv` | 自动解析（ΔPSI 来自均值差或外部文件） |
| MAJIQ TSV（含 `dPSI`/`P(dPSI)` 列） | 自动解析 |
| LeafCutter `*_cluster_significance.txt` | 自动解析 |
| `AS_event_master.tsv`（标准表） | 直接读取 |

可选附件：`gene_annotation.tsv`（GO/KEGG 列，用于富集）、`differential_expression.tsv`
（gene_id/log2FC/pvalue/padj/baseMean）。

`sample_metadata.tsv` 列：`sample_id, group, condition, tissue, batch`。

## Agent 架构

### 自治内核（`splicegaip/agent/`，默认启用）

```
观察(Profile) → 校验(Verify) → 决策(Decide) → 执行(Act) → 记录(Trace)
       ↑                                                      │
       └────────── 目标未达成 → 反思重试 / 重规划（有预算） ─────┘
```

| 组件 | 文件 | 职责 |
|---|---|---|
| AgentState | `agent/state.py` | 事实/问题/步骤黑板 + 可判定的目标验收标准（取代终止令牌） |
| Profile | `agent/profile.py` | 数据画像：规模、FDR 覆盖率、缺失、支持读数、组平衡 |
| Actions | `agent/actions.py` | 动作注册表（8 个既有工具 + profile / assess_quality / adapt_thresholds / deep_dive_gene） |
| DecisionEngine | `agent/decision.py` | **自我决策核心**：规则链优先，可选模型建议 |
| Verifier | `agent/verify.py` | 结果体检，产出 Issue(code, severity, suggestion) |
| Reflector | `agent/reflector.py` | 问题 → 补救动作（改阈值 / 重试 / 降级接受） |
| AutonomousAgent | `agent/loop.py` | OODA 主循环 + 步数/时间/错误三重预算 + 决策轨迹 + 续跑/持久化 |
| EpisodicMemory | `agent/episodic.py` | 跨运行经验：相似数据上次用什么阈值成功过 |
| Session | `agent/session.py` | 多轮追问：状态快照 save/load + 规则化意图解析 + followup 动作前缀 |

决策引擎**以规则为主、模型为辅**，所以离线（无 key）时同样是真决策而不是放录像。
例：默认 FDR<0.05 筛出 0 个事件时，agent 会按数据分布把阈值放宽到能产出结果的
位置重跑，并把「为什么改」写进报告 Methods 与 workflow log；若连最宽松的门都
筛不出东西，它会停止尝试并把这一点作为局限性写进报告。

切换：`config.yaml` 的 `agent.mode`（`agentic` / `scripted`）或
`SPLICEGAIP_AGENT_MODE`，或 CLI 的 `--agent-mode`。

### 自我质疑 + 外部知识（Phase 2，默认启用）

Phase 1 让 agent 会决策；Phase 2 让它在下结论前**先挑战自己的结果**，并且会用
外部知识库补证据。

**（a）假设检验 `test_hypothesis`**（`agent/hypothesis.py`，纯本地 scipy，离线一致）
在解读之前跑 5 个预注册检验，BH 校正后写进报告 3.3 节与局限性：

| 检验 | H0 | 方法 |
|---|---|---|
| `dpsi_shift` | ΔPSI 分布未偏离 0 | Wilcoxon 符号秩（小样本退化 t 检验） |
| `direction_balance` | 上调/下调事件均衡 | 二项检验 |
| `event_type_bias` | 显著事件类型构成 = 背景构成 | 卡方拟合优度 |
| `coverage_confound` | 效应量与测序深度无关 | Spearman 秩相关 |
| `gene_recurrence` | 命中不集中于少数基因 | 置换检验（1000 次） |

被拒绝的检验会直接变成 `result_confounded` 警告并进入报告 Limitations。

**（b）四大技能接进循环**（`agent/skills_bridge.py` + `skills/*`）
MyGene/PubMed/KEGG/剪接解读此前只能单独调 API，现在是 agent 动作：
`annotate_genes`、`search_literature`、`enrich_pathways`、`interpret_splice_event`。
桥接层保证：sync/async 隔离、单次超时、**每运行调用预算**、同参数缓存、
失败即降级（网络挂了不会拖垮分析，只会记一条局限性）。
开关：`agent.skills.enabled` / `SPLICEGAIP_ENABLE_SKILLS` / CLI `--skills off`。

**（c）开源后端适配**（`splicegaip/integrations/`，可选依赖，缺失自动降级）

| 组件 | 用途 | 安装 |
|---|---|---|
| GSEApy | GO/KEGG/Reactome/MSigDB 富集（Enrichr），替代手写 HTTP | `pip install gseapy` |
| MyGene | 基因/Ensembl/UniProt 注释官方客户端，支持批量 | `pip install mygene` |

可用性与版本通过 `capabilities()` 暴露给 API 与报告。

**（d）人在回路**（`agent/interactive.py`）
`autonomy: assisted` 时，三类决策会先问人：联网技能调用、放宽阈值偏离配置、
把阻塞问题降级为局限性。handler 可插拔（CLI stdin / API 回调），
`auto`（默认）自动批准但同样留痕。CLI：`--autonomy assisted`。

### 脚本式多智能体（`scripted` 模式，兼容保留）

```
用户查询 + 输入数据
      │
      ▼
┌─────────────┐   工作流 JSON（目标/步骤/输入/预期输出/局限）
│  BioPlanner │   不执行计算，只规划
└──────┬──────┘
       ▼
┌─────────────┐   summarize_dataset → filter_significant_events
│  BioAnalyst │   → rank_candidates → run_enrichment → generate_figures
└──────┬──────┘   （FDR<0.05 且 |ΔPSI|>0.1；评分 = 0.4显著性+0.3效应+0.2生物学+0.1文献）
       ▼
┌───────────────┐  collect_literature_evidence → interpret_candidates
│ BioInterpreter│  → generate_report → 终述（SPLICEGAIP_DONE 终止）
└───────────────┘
```

Agent 间通过结构化消息协作，全部操作写入 SQLite Analysis Memory
（输入指纹、分析计划、生成代码、结果、解释、工作流日志），保证科研可重复性。

## 输出

```
runtime/projects/<project_id>/
├── figures/            # volcano.png/svg, event_type_counts, psi_heatmap,
│                       # psi_distribution, candidate_ranking, enrichment
├── report.html         # 自包含报告（图内嵌 base64）
├── report.pdf          # PDF 版（reportlab）
└── ...                 # 记忆与日志在 runtime/splicegaip.sqlite3
```

> `runtime/` 是运行时产物，由程序在本地生成，不入库。

报告结构：Summary / Methods / Results（3.3 统计假设检验）/ Figures /
Biological Interpretation（5.5 外部知识发现）/ Limitations / References。

## 项目结构

```
SpliceGAIP/
├── splicegaip/
│   ├── agent/          # 自治内核：状态/画像/决策/校验/反思/循环/经验记忆
│   │                   # + hypothesis.py（假设检验）/ skills_bridge.py（技能桥接）
│   │                   # + interactive.py（人在回路）
│   ├── agents/         # 3 个核心 Agent + 确定性策略（scripted 模式）
│   ├── analysis/       # statistics / enrichment / visualization
│   ├── api/            # FastAPI
│   ├── config.py       # 配置加载
│   ├── data/           # loader / validator / ingestion（Standard BioAnalysis Format）
│   ├── integrations/   # 可选开源后端：GSEApy(Enrichr) / MyGene + 能力探测
│   ├── interface/      # Web UI / Streamlit
│   ├── knowledge/      # RAG（内置知识库 + PubMed + SQLite 文献库）
│   ├── llm/            # 模型客户端 / 离线 fallback / 结果增强
│   ├── mcp/            # MCP 集成
│   ├── memory/         # SQLite Analysis Memory
│   ├── observability.py
│   ├── pipeline.py
│   ├── report/         # generator.py（HTML + PDF）
│   ├── skills/         # gene_annotation / literature_search / pathway_enrichment / splice_interpretation
│   ├── splicing/       # schema + parsers(rmats/suppa/majiq/leafcutter) + filtering + ranking
│   ├── team.py
│   ├── tools/          # 平台工具注册
│   └── ui/             # 主题
├── config/             # config.yaml / agent_config.yaml / tool_config.yaml
├── docs/               # 能力手册 + 演示页 + 双语讲解稿
├── media/              # 演示视频 + 字幕 + 封面
├── packaging/          # PyInstaller spec + 图标（构建桌面/Web 便携版）
├── run.py / serve_ui.py / desktop_ui.py   # 入口
├── Dockerfile / docker-compose.yml
├── requirements.txt
└── README.md
```

## 设计原则

1. 保留 BioGAIP 成熟框架，不重建基础设施；
2. 增加剪接领域专用智能层（标准化、排序、证据）；
3. Phase 1 输出必须独立运行（无 LLM key 时确定性策略驱动全流程）；
4. Phase 2 可无缝接入（FASTQ → 比对 → 剪接检测 → 现有 AI 层）；
5. 全程可复现：workflow、参数、软件版本、日志全部留痕；
6. 所有结论必须有证据支撑，区分「已证实统计结果」与「待验证假设」。

## 路线图

- **Phase 2**：FASTQ 处理、比对 pipeline（rMATS/SUPPA2 在线运行）
- **Phase 3**：单细胞 RNA-seq、多组学
- **Phase 4**：AI autonomous bioinformatics researcher

## 致谢与许可

- BioGAIP：AGPL-3.0
- SplicingNexus v2 事件契约与统计实现移植自用户自有项目
- SpliceGAIP 新增代码随本仓库分发，详见 [LICENSE](LICENSE)
