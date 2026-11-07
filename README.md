# EpitopeRank

**AI 驱动的可变剪接分析 + 剪接新抗原候选肽生成平台**

[![Tests](https://github.com/Zhouhao-stak/SpliceGAIP/actions/workflows/test.yml/badge.svg)](https://github.com/Zhouhao-stak/SpliceGAIP/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/Zhouhao-stak/SpliceGAIP?display_name=tag)](https://github.com/Zhouhao-stak/SpliceGAIP/releases)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)

丢进一批 rMATS 结果，出来一份能读懂、能复现、能直接写进论文的剪接分析报告；
需要往下游走一步时，再把它变成 HLA 呈递的候选新抗原肽。

```
rMATS JC 五类事件表 + 样本元数据
        ↓
多智能体分析（画像 → 统计 → 排序 → 富集 → 文献 → 报告）
        ↓
可视化 + 候选基因 + 通路富集 + HTML/PDF 报告
        ↓
剪接连接肽（8–11mer）→ HLA 结合预测 → 候选新抗原排序
```

**不做**：FASTQ 质控、比对（STAR/HISAT2）、转录本组装。输入是「已量化的剪接结果」，
不是原始测序数据。

> 📖 **零基础用户** → [图文手把手教程](docs/手把手教程.html)（12 张真实界面截图 + 一套公开数据的实跑数字）
>
> 📚 **全部文档** → [docs/README.md](docs/README.md)

---

## 目录

- [下载即用](#下载即用)
- [从源码运行](#从源码运行)
- [一次完整分析长什么样](#一次完整分析长什么样)
- [输入数据](#输入数据)
- [生成候选肽](#生成候选肽)
- [结果在哪](#结果在哪)
- [架构](#架构)
- [项目结构](#项目结构)
- [测试与 CI](#测试与-ci)
- [文档索引](#文档索引)
- [致谢与许可](#致谢与许可)
- [模型轨迹录制与决策重放](#模型轨迹录制与决策重放)

## 下载即用

到 [Releases](https://github.com/Zhouhao-stak/SpliceGAIP/releases) 下载最新的
`EpitopeRank-*-windows.zip`，解压后双击 `EpitopeRank-Desktop.exe`。

> 最新版新增：**模型调用轨迹录制与严格离线重放**（`record → replay → compare`）、MHC-II 11–30 aa 长肽预测、深色主题结果表格可读性修复。
> 详见文末 [模型轨迹录制与决策重放](#模型轨迹录制与决策重放)。

程序会在本机起一个服务并自动打开浏览器（地址形如 `http://127.0.0.1:8800/`），
**不需要装 Python，也不需要联网**——只有想用 AI 解读或跑 HLA 预测时才需要网络。

首次运行前，在同目录新建 `.env`（可参考压缩包里的 `.env.example`）：

```ini
# 可选：接入大模型做结果解读（不配也能跑，自治内核用规则决策）
MODEL_API_BASE_URL=https://api.deepseek.com
MODEL_API_KEY=sk-...
MODEL_NAME=deepseek-flash
```

## 从源码运行

```bash
# 1. 环境（Python >= 3.10）
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate         # macOS / Linux
pip install -r requirements.txt

# 2. 起服务（两种入口任选）
python serve_ui.py --port 8800                 # Web 界面 + API
python serve_ui.py --port 8800 --workers 8     # 多进程（服务器上用）

# 3. 浏览器打开
# http://127.0.0.1:8800/
```

命令行也能跑：

```bash
# 造一份演示数据（合成 rMATS 输出：3 对照 + 3 肿瘤，47 个事件）
python examples/make_demo_data.py examples/demo_rmats

# 完整分析（无大模型 key 也能跑）
python run.py analyze --input examples/demo_rmats --query "分析RNA剪接变化"

# 在已有项目上追问，不重跑整条流水线
python run.py followup --project-id SPN-XXXX --query "只看 SE 事件"
```

> 需要复现一次带模型参与的分析？见文末 [模型轨迹录制与决策重放](#模型轨迹录制与决策重放)。

Docker：

```bash
docker compose up -d
# Web UI + API: http://localhost:8800（页面在 /）
```

Coolify 一键部署、无 root 服务器部署等方案见 [docs/deploy/](docs/deploy/)。

## 一次完整分析长什么样

1. **新建分析** — 填项目名、写一句分析意图（如「pDC 活化后可变剪接变化」），
   把 rMATS 五类表 + 元数据拖进去。
2. **自动画像与决策** — 平台先看数据（规模、FDR 覆盖率、组平衡、支持读数），
   再决定用哪套阈值。默认 FDR<0.05 筛不出东西时，会按数据分布放宽阈值重跑，
   并把「为什么改」写进报告 Methods 与流程日志；确实筛不出就如实写明局限。
3. **统计分析** — 卡方检验 + BH 校正，自算 ΔPSI（IncLevel2 − IncLevel1）。
4. **候选排序** — 显著性 0.4 + 效应量 0.3 + 生物学 0.2 + 文献 0.1。
5. **假设检验** — 5 个预注册检验（ΔPSI 偏移、方向平衡、事件类型偏倚、
   深度混杂、基因复现性），被拒绝的检验直接变成报告里的警告。
6. **富集与文献** — GO/KEGG 富集 + PubMed 检索 + 全文段落检索（BM25）。
7. **出报告** — HTML（图内嵌，可直接发人）+ PDF，覆盖 Summary / Methods /
   Results / Figures / Interpretation / Limitations / References。

## 输入数据

平台**只接受 rMATS 格式**（SUPPA2 / MAJIQ / LeafCutter / 预计算 ΔPSI 表已移除）。

| 输入 | 说明 |
|---|---|
| `*.MATS.JC.txt` × 5（SE / A5SS / A3SS / MXE / RI）+ `sample_metadata.tsv` | 标准用法，自动标准化为事件主表 |
| 单个 rMATS JC 表 | 单事件类型快速分析 |
| 厂商逐样本 rMATS 导出（如华大 RNAref `.xls`） | 经「智能接入」重映射为标准表 |
| `AS_event_master.tsv`（内部标准表） | 由上面前置生成，也可直接读 |

`sample_metadata.tsv` 列：`sample_id, group, condition, tissue, batch`。

可选附件：`gene_annotation.tsv`（GO/KEGG 列，用于富集）、
`differential_expression.tsv`（gene_id/log2FC/pvalue/padj/baseMean）。

格式细节见 [docs/USER_GUIDE.md](docs/USER_GUIDE.md)。

## 生成候选肽

这是「剪接 → 新抗原」那一步。核心是一个四列的 CDS 对照表：

| 列 | 含义 |
|---|---|
| `event_id` | 对应 rMATS 事件 ID（如 `RI:4579`） |
| `reference_cds` | 正常（参考）转录本的 CDS 序列 |
| `altered_cds` | 发生剪接改变后的 CDS 序列 |
| `junction_nt` | 新连接点在 CDS 中的位置（**整数边界，不是序列**） |

**表名和列名都可以随便起。** 平台按内容识别而不是按文件名：

- 文件名随意，`splice_orfs.tsv`、`客户给的剪接对照表.csv` 都行；目录里有多份时让你选。
- 表头不认识也能用——比如客户导出的是 `编号 / 位点 / 序列1 / 序列2`，
  平台会按单元格内容画像（序列占比、数字占比、事件 ID 形状）猜列角色，
  连「序列1 和序列2 哪个是参考」都会用 junction 肽回放来判方向。
- 猜完之后界面弹「**确认列的含义**」面板，四个下拉框已预填，核对一下点确认即可；
  同一项目只问一次。
- rMATS 的 `*.MATS.JC.txt` 不会被误当成残缺的编码序列表（按表头特征列识别后静默跳过）。

填 HLA 就跑免疫原性预测（IEDB NetMHCpan 4.1 EL）：

```
HLA-A*02:01,HLA-B*07:02
```

- 按每批 100 条提交 IEDB，自动重试与节流，结果落磁盘缓存；
- 单次最多 20000 个「肽 × 等位基因」组合，超了截断并在 manifest 里标注；
- 留空则只出肽、不联网。

**CDS 对照表不用再手工造**：新抗原页的「自动重建编码序列表」直接从项目里的 rMATS 事件坐标
重建 ORF，产出四列表 + 可审计 manifest（`epitoperank/splicing/orf_builder.py`）。
参考源可选 Ensembl REST（联网、缓存到运行根）或本地 GTF + FASTA（离线可复现）；
支持 SE / RI，其余事件类型记录跳过原因。坐标必须与参考基因组版本一致。

**结果自动分级**：预测完成后额外写出 `ranked_candidates.tsv`，按 `percentile_rank` 升序，
标注 `strong`（<0.5%）/ `weak`（<2%）/ `none`，并带基因、事件、ΔPSI、FDR 等元数据；
manifest 与界面状态栏同时给出分档计数。

**自主智能体与外网**：`agent.autonomous_planning` 让大模型在 OODA 每一步从完整动作表
（含 `web_fetch`、`rebuild_orf_table`、`call_mcp_tool`）里选下一步，规则链始终作为安全回退；
工具权限可用 `agent.allow_network` / `agent.allow_file_write` 关闭。设置页可连接外部 MCP 服务器，
内置 `web_fetch` 工具按域名白名单访问 Ensembl/NCBI/IEDB 等站点。

命令行：

```bash
python run.py peptide --input examples/peptide_demo \
  --cds examples/peptide_demo/splice_orfs.tsv \
  --alleles HLA-A*02:01 --mhc-class both --out out/peptide_run
```

> **判读口径**：按 `percentile_rank` 升序，**<0.5% 才是强结合**，<2% 属弱结合。
> 报结果前先看这两档，别拿 1.2% 当阳性。

方法细节见 [docs/PEPTIDE.md](docs/PEPTIDE.md) 与 [docs/NEOANTIGEN.md](docs/NEOANTIGEN.md)。

## 结果在哪

分析跑完，除了项目目录，还会**自动导出到独立的成果文件夹**：

```
<结果根>/results/<项目名>_<SP编号>/
├── report.html / report.pdf
├── figures/              # volcano / heatmap / ranking / enrichment（PNG 300dpi + SVG）
├── neoantigen_results/   # 生成过肽才有
└── 项目说明.txt           # 样本数 / 事件数 / 显著数
```

一个项目约 **4MB**。项目详情页有两个按钮：**📁 成果文件夹**（直接打开）和
**📦 打包 ZIP**（生成可发人的压缩包）。

**运行根目录**：Windows `%LOCALAPPDATA%\EpitopeRank`，Linux `~/.local/share/epitoperank`，
Docker 容器内 `/data`（命名卷 `epitoperank-data`），可用 `EPITOPERANK_RUNTIME_ROOT` 覆盖。
结果根可用 `EPITOPERANK_RESULTS_ROOT` 单独指定，默认在运行根下的 `results/`。

云端备份是可选的：服务器上部署后会暴露 `POST /api/cloud/upload`，
客户端在 `.env` 填 `EPITOPERANK_CLOUD_URL` 即可把成果 ZIP 推上去。

## 架构

### 自治内核（`epitoperank/agent/`，默认启用）

```
观察(Profile) → 校验(Verify) → 决策(Decide) → 执行(Act) → 记录(Trace)
       ↑                                                      │
       └────────── 目标未达成 → 反思重试 / 重规划（有预算） ─────┘
```

| 组件 | 文件 | 职责 |
|---|---|---|
| AgentState | `agent/state.py` | 事实/问题/步骤黑板 + 可判定的验收标准 |
| Profile | `agent/profile.py` | 数据画像：规模、FDR 覆盖率、缺失、支持读数、组平衡 |
| Actions | `agent/actions.py` | 24 个动作注册表（画像/质检/调阈值/统计检验/外网/ORF 重建/MCP） |
| DecisionEngine | `agent/decision.py` | 自我决策核心：规则链优先，模型建议为辅 |
| Verifier | `agent/verify.py` | 结果体检，产出 Issue(code, severity, suggestion) |
| Reflector | `agent/reflector.py` | 问题 → 补救动作（改阈值 / 重试 / 降级接受） |
| AutonomousAgent | `agent/loop.py` | OODA 主循环 + 步数/时间/错误三重预算 + 决策轨迹 |
| EpisodicMemory | `agent/episodic.py` | 跨运行经验：相似数据上次用什么阈值成功过 |
| Session | `agent/session.py` | 多轮追问：状态快照 + 意图解析 + followup |
| ModelTrace | `llm/trace.py` | 录制每次模型调用（prompt/响应/采样参数）并支持严格离线重放 |

决策**以规则为主、模型为辅**，所以离线（无 key）时同样是真决策，不是放录像。

### 自我质疑 + 外部知识

解读之前先跑 5 个预注册检验（纯本地 scipy，离线一致），BH 校正后写进报告：

| 检验 | H0 | 方法 |
|---|---|---|
| `dpsi_shift` | ΔPSI 分布未偏离 0 | Wilcoxon 符号秩 |
| `direction_balance` | 上调/下调事件均衡 | 二项检验 |
| `event_type_bias` | 显著事件类型构成 = 背景构成 | 卡方拟合优度 |
| `coverage_confound` | 效应量与测序深度无关 | Spearman 秩相关 |
| `gene_recurrence` | 命中不集中于少数基因 | 置换检验（1000 次） |

被拒绝的检验直接变成警告并进报告 Limitations——不遮掩对自己不利的结论。

### 设置页

左侧「⚙️ 设置」放两件事：

- **模型配置** —— 填 Base URL / 模型名 / API Key 即可启用报告里的 AI 解读，
  密钥只写本机 `.env`，不进报告、不进日志。
- **MCP 工具台** —— 手动选择服务器与工具并传 JSON 参数调用；也可以用一句自然语言
  让模型挑工具（模型只给 `{server, tool, arguments}` 建议，校验和执行都在本地）。

## 项目结构

```
EpitopeRank/
├── agent/             # 自治内核：状态/画像/决策/校验/反思/循环/经验记忆
│                      # + hypothesis.py / skills_bridge.py / interactive.py
├── agents/            # 3 个核心 Agent + 确定性策略（scripted 模式）
├── integrations/      # 可选后端：GSEApy(Enrichr) / MyGene，缺失自动降级
├── data/              # loader.py / validator.py（Standard BioAnalysis Format）
├── splicing/          # schema + parsers(rmats) + filtering + ranking
├── analysis/          # statistics / enrichment / visualization
├── knowledge/         # RAG（内置知识库 + PubMed + 全文 BM25 段落检索）
├── llm/               # 模型客户端 / 增强任务 / trace.py（轨迹录制与重放）
├── memory/            # SQLite Analysis Memory（项目/事件/候选/日志）
├── peptide/           # 肽预测：序列/理化/HLA/IEDB 客户端/novelty/评分/流水线
├── neoantigen*.py     # 剪接候选新抗原：junction 肽、分阶段流程、审计
├── results_export.py  # 成果文件夹导出 / 打包 ZIP / 云端上传
├── report/            # generator.py（HTML + PDF）
├── api/               # FastAPI
├── interface/         # Web UI（单文件内嵌）
├── config/            # config.yaml / agent_config.yaml / tool_config.yaml
├── tests/             # 单元 + 集成测试
├── examples/          # 演示数据生成器
├── packaging/         # PyInstaller spec
├── docs/              # 使用文档 / 教程 / 部署
└── legacy/            # BioGAIP 原始代码（归档保留）
```

## 测试与 CI

```bash
pip install -r requirements-dev.txt

pytest tests/unit tests/integration -v
pytest --cov=epitoperank --cov-report=html
```

当前 **331 个测试全部通过**（单元 + API/UI 集成，含轨迹录制与重放回归）。

CI 在每次推送时跑：

- 单元测试（Python 3.10 / 3.11 / 3.12）
- 代码风格（Black、Flake8）
- 类型检查（MyPy）
- 覆盖率门槛（当前 20%，随覆盖率提升逐步收紧）

推送 `v*` tag 会自动构建 Windows 便携版并发布 Release（[.github/workflows/release.yml](.github/workflows/release.yml)）。

## 文档索引

| 文档 | 说明 |
|---|---|
| [手把手教程.html](docs/手把手教程.html) | **零基础图文教程**，12 张真实截图 |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | **完整使用手册**：输入格式、生成肽三条路线、API 速查、FAQ |
| [QUICKSTART.md](docs/QUICKSTART.md) | 三步跑通第一个分析 |
| [NEOANTIGEN.md](docs/NEOANTIGEN.md) | 剪接新抗原流程与结果解读 |
| [PEPTIDE.md](docs/PEPTIDE.md) | 肽预测层：MHC-I/II、加工、稳定性、novelty、评分 |
| [DATASETS.md](docs/DATASETS.md) | 可用数据集与参考表来源 |
| [DATA_AND_DEPLOY.md](docs/DATA_AND_DEPLOY.md) | 数据存哪 · 部署 · 域名与 HTTPS |
| [智能体的手册.md](docs/智能体的手册.md) | 能力全清单与边界 |
| [docs/README.md](docs/README.md) | 完整索引 |

## 设计原则

1. 复用 BioGAIP 成熟框架，不重建基础设施；
2. 增加剪接领域专用智能层（标准化、排序、证据）；
3. 无 LLM key 时全流程仍可运行（规则驱动的确定性决策）；
4. 可无缝接入 Phase 2（FASTQ → 比对 → 剪接检测 → 现有 AI 层）；
5. 全程可复现：workflow、参数、软件版本、日志全部留痕；模型调用写入 `agent_state.json`，可用 `run.py replay` 严格离线重放、`run.py compare` 逐项比对；
6. 结论必须有证据支撑，严格区分「已证实的统计结果」与「待验证的假设」。

## 路线图

- **Phase 2**：FASTQ 处理、比对 pipeline（rMATS 在线运行）
- **Phase 3**：单细胞 RNA-seq、多组学
- **Phase 4**：AI autonomous bioinformatics researcher

## 致谢与许可

本项目基于开源项目 [BioGAIP](https://github.com/zhangjy859/BioGAIP) 的多智能体架构演进，
并复用了 SplicingNexus v2 的事件标准化契约与统计实现。

- 本仓库：**AGPL-3.0**，见 [LICENSE](LICENSE)
- BioGAIP 原始代码保留在 `legacy/`，遵循其原始 AGPL-3.0 许可
- 第三方预测能力来自 IEDB（NetMHCpan 4.1 EL 等），使用时请遵守其许可与引用要求

## 模型轨迹录制与决策重放

默认 `agentic` 分析会把本次完整生命周期的模型调用写入输出项目的
`agent_state.json`：包括分析前的意图理解、`model_plan`、`insight`、
`enrichment:<feature>`（叙述、解读、自评等）。无需额外录制开关。
`model_calls` 保存有序编号、脱敏后的完整 prompt、SHA-256、模型名、实际生效温度、
max_tokens/json_output、原始响应、解析对象、耗时、重试次数与时间。
`meta` 保存 schema_version=1、输入文件指纹、脱敏配置快照、完整决策序列、
排序结果及报告 SHA-256。旧版无这些字段的状态仍可用于普通 load_state/followup，
但不能当作完整的重放轨迹。

在项目根目录执行（PowerShell；录制时模型凭据沿用本地环境）：

```powershell
$env:EPITOPERANK_ENABLE_PUBMED = "false"
venv/Scripts/python.exe run.py analyze --input examples/demo_rmats --query "Analyze splicing" --agent-mode agentic --skills off --project-id TRACE-DEMO --out artifacts/record
venv/Scripts/python.exe run.py replay --input examples/demo_rmats --trace artifacts/record/TRACE-DEMO/agent_state.json --out artifacts/replay
venv/Scripts/python.exe run.py compare artifacts/record/TRACE-DEMO/agent_state.json artifacts/replay/TRACE-DEMO/agent_state.json
```

也可在 YAML 中配置 `agent.replay: <agent_state.json 路径>`，随后调用
`run_analysis()`。重放会校验输入内容和 query，恢复录制时的 agent/llm/analysis
配置，保留录制项目 ID；`--out` 是项目根目录。必须使用独立输出目录。
重放不需要模型密钥，不调用 `LLMEnhancer.complete()`，直接调用该方法会抛出
`ReplayError`。动作工具仍正常执行，叙述增强消费录制响应。此功能针对全新分析，
不支持将 replay 配置用于 followup 或绕过 pipeline 的低层入口。

轨迹缺失、顺序或 prompt/参数不匹配、输入指纹变化、完整性校验失败、排序结果或
报告哈希不同均使重放失败；不会悄悄退回规则链。错误写入输出目录中的
`replay_errors.json` 的 `errors`；已有运行状态也标记失败。CLI 返回非零。
整体 SHA-256 用于检测文件意外改动，并非数字签名。

报告时间与 PDF 元数据固定以实现字节一致。报告 Methods 展示录制时每个动作的
`source=llm/rule/reflection/...`，并说明实际执行来源以运行状态为准：
重放状态/API 的决策步骤标记 `source=replay`。报告保留原始来源，因此可以逐字节
比较；运行来源、执行耗时、输出目录消息属于运行元数据。
`compare` 比较动作、参数、状态、消息、排序与报告哈希，归一化输出目录，忽略
`source` 和 `seconds` 的预期差异；一致打印 `identical` 并返回 0。

重放只冻结模型响应与决策，不冻结外部服务（包括 IEDB）、文献库或实验室知识库。
请保留相同输入、依赖版本和外部缓存；这些服务返回值或本地数据库变化可能使
重新执行工具后的报告不同，此时严格重放报错，不宣称复现成功。
轨迹写盘前删除密钥字段并脱敏 prompt/响应中的凭据；完整 prompt 可能包含输入
研究信息，应按项目数据管理。
