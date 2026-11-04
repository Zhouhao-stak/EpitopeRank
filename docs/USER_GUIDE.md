# SpliceGAIP 完整使用文档

> SpliceGAIP 是一个基于 AI 的 RNA 可变剪接分析与新抗原（候选肽）生成平台。
> 数据格式：**只支持 rMATS 输出格式**（其他格式请先用 rMATS 产出，或走「智能接入」重映射）。

> 🚩 **第一次用？先看图文教程** [`手把手教程.html`](手把手教程.html)：从启动到出肽，
> 12 张界面截图 + 一套真实数据的实跑数字，照着点一遍就会。本文档是查细节用的手册。

---

## 目录

1. [启动与访问](#1-启动与访问)
2. [快速上手（5 步跑通）](#2-快速上手5-步跑通)
3. [输入数据详解（重点）](#3-输入数据详解)
4. [分析流程与页面导览](#4-分析流程与页面导览)
5. [生成肽 / 剪接候选新抗原](#5-生成肽--剪接候选新抗原)
6. [历史记录与数据管理](#6-历史记录与数据管理)
7. [API 速查表](#7-api-速查表)
8. [常见问题](#8-常见问题)

---

## 1. 启动与访问

| 方式 | 启动命令 | 访问地址 |
|---|---|---|
| **Windows 桌面版**（推荐本机用） | 双击 `dist\SpliceGAIP\SpliceGAIP.exe` | 自动弹出深色窗口 |
| **源码网页版** | `python serve_ui.py --port 8800` | http://localhost:8800/ |
| **Docker 部署** | `cd deploy/docker && docker-compose up -d` | http://服务器IP:8800/ |
| **公网访问**（本服务器已部署） | 隧道已运行于服务器 tmux 会话 `cloudflared` | https://signing-viewing-uniprotkb-coalition.trycloudflare.com（临时域名，重启隧道会变） |

- 健康检查：`GET /api/health` 返回 `{"status":"ok"}` 即正常。
- 域名固定：临时域名重启会变；要永久域名需自购域名并使用 Cloudflare Named Tunnel，见 `docs/deploy/DEPLOY_NO_SUDO.md`。

---

## 2. 快速上手（5 步跑通）

1. **生成演示数据**（可选，没有真实数据时先试跑）：
   ```bash
   python examples/make_demo_data.py examples/demo_rmats
   ```
2. **新建分析**：仪表盘 →「启动新分析」→ 填项目名称和分析查询（如"分析肿瘤与正常组织的剪接变化"）→ 拖入 rMATS 文件 → 开始。
3. **看进度**：AI 流水线页显示 6 个 Agent 步骤（数据 → 质控 → 剪接检测 → 统计 → 注释 → 解读）。
4. **查结果**：事件浏览器（可筛选/排序/分页）→ 可视化页（火山图、ΔPSI 瀑布图等 13 张科研图）→ 基因浏览器（按基因查事件）。
5. **导出**：报告页生成 HTML/PDF；如需候选肽，进入「剪接候选新抗原」页（见第 5 节）。

> 没配大模型 API Key 也能用：系统会退回离线规则决策。要启用 AI 解读，在 AI 助手页或 `.env` 配置
> `MODEL_API_BASE_URL` / `MODEL_API_KEY` / `MODEL_NAME` / `MODEL_THINKING`。

---

## 3. 输入数据详解

### 3.1 rMATS 结果文件（必需）

放入 rMATS 输出目录中的 **Junction Count（JC）表**，支持全部 5 类事件，文件名必须完全一致：

| 事件类型 | 文件名 | 剪接类型 |
|---|---|---|
| SE | `SE.MATS.JC.txt` | 外显子跳跃 |
| A5SS | `A5SS.MATS.JC.txt` | 5' 选择性供体位点 |
| A3SS | `A3SS.MATS.JC.txt` | 3' 选择性受体位点 |
| MXE | `MXE.MATS.JC.txt` | 互斥外显子 |
| RI | `RI.MATS.JC.txt` | 内含子滞留 |

**可接受的目录结构（三选一）**：
1. **完整目录**：一个文件夹内放若干 JC 表 + 可选 `sample_metadata.tsv`（推荐）；
2. **单个 JC 表**：如只分析 SE 一类，直接上传 `SE.MATS.JC.txt`；
3. **内部标准表**：`AS_event_master.tsv`（本系统分析后的标准事件表，可用于复分析）。

**关键列**（解析器 `splicegaip/splicing/parsers/rmats.py`）：

| 列名 | 含义 | 必需 |
|---|---|---|
| `ID` | 事件编号 | ✅ |
| `GeneID` | 基因 ID | ✅ |
| `geneSymbol` | 基因符号 | ✅ |
| `chr` / `strand` | 染色体 / 链方向 | ✅ |
| `PValue` / `FDR` | 显著性 | ✅ |
| `IncLevel1` / `IncLevel2` | 两组各自平均 PSI（ΔPSI = IncLevel2 均值 − IncLevel1 均值，由系统计算，不读 IncLevelDifference 列） | ✅ |
| `IJC_SAMPLE_1/2`、`SJC_SAMPLE_1/2` | 两组包含/跳跃读数 | ✅ |
| 坐标列 | SE: `exonStart_0base`/`exonEnd`；MXE: `1stExonStart_0base`/`2ndExonEnd`；A5SS/A3SS: `longExonStart_0base`/`longExonEnd`；RI: `upstreamEE`/`downstreamES` | ✅（按类型） |

> 坐标为 0-based，系统内部自动转为 1-based inclusive。注意：JC 表中 `IJC/SJC` 列是逗号分隔的逐样本值。

### 3.2 样本元数据（可选但推荐）：`sample_metadata.tsv`

放同一目录下，用于分组比较和图表：

```
sample_id	group	condition	tissue	batch
S1	tumor	tumor	lung	b1
S2	tumor	tumor	lung	b1
S3	normal	normal	lung	b1
```

### 3.3 差异表达表（可选，用于剪接-表达联合分析）：`differential_expression.tsv`

必需列：`gene_id, log2FC, pvalue, padj, baseMean`。

### 3.4 智能接入（格式不标准时）

上传后系统会自动尝试解析；识别不出标准 rMATS 列时，会弹出「智能接入检查」让你确认列映射和样本分组（华大 RNAref 逐样本 `.xls` 就走这条路）。确认后自动转成标准表再分析。

### 3.5 高级阈值（可选）

在「启动新分析」的高级参数里可覆盖默认值：

| 参数 | 含义 |
|---|---|
| `fdr` | 显著性 FDR 阈值（默认 0.05） |
| `delta_psi` | ΔPSI 阈值（默认 0.1） |
| `min_support_reads` | 最小支持读数 |
| `min_valid_samples` | 最小有效样本数 |
| `top_candidates` | 候选事件保留数 |
| `enrichment_alpha` | 富集分析显著性水平 |

---

## 4. 分析流程与页面导览

| 页面 | 功能 |
|---|---|
| **仪表盘** | 样本/事件/显著事件统计卡、历史项目列表（可搜）、项目详情（分组、类型分布、Top10 候选、日志、报告/删除） |
| **AI 流水线** | 6 步 Agent 实时进度 |
| **事件浏览器** | 按基因/事件 ID/染色体搜索，SE/MXE/A3SS/A5SS/RI 勾选、仅显著开关、按 FDR/\|ΔPSI\|/基因排序，50 条/页 |
| **可视化** | 火山图、ΔPSI 瀑布、ECDF、碎石、类型分布、热图、箱线、富集点图等 13 张图，按需渲染 |
| **基因浏览器** | 输入基因符号（如 TP53）查看全部事件与文献证据 |
| **报告** | 生成/下载 HTML 与 PDF |
| **剪接候选新抗原** | 生成候选肽（见第 5 节） |
| **AI 助手** | 聊天 + 模型配置 + 四技能（基因注释/文献搜索/通路富集/剪接解读）+ MCP 工具控制台 |

---

## 5. 生成肽 / 剪接候选新抗原

入口：左侧导航「剪接候选新抗原」。系统提供 **三条路线**，按严谨程度递增。

### 5.1 路线 A：内置剪接连接肽生成（最快，需要 CDS 对照表）

**第 1 步：检查项目就绪**。点「检查项目数据」，系统返回 CDS 表状态（`available` 即可继续）。

**第 2 步：准备 CDS 编码序列对照表**（`.tsv / .csv / .txt`），**必需 4 列**：

✅ **文件名不限，列名可换**：系统按**表头内容**识别 CDS 表，不看文件名。
`客户给的_剪接CDS对照表.csv`、`第二批_候选表.tsv` 这类名字都能直接用；目录里有多份也没关系，
界面上会出现下拉框让你选。
列名支持常见写法：`event_id / Event ID / 事件ID`、`reference_cds / Reference CDS / 参考序列`、
`altered_cds / Altered CDS / 变异序列`、`junction_nt / Junction nt / 连接点`。
编码支持 UTF-8、UTF-8-BOM、GBK，分隔符自动判断 Tab 还是逗号。

**两种把表交给系统的办法（任选其一）**

1. **上传项目时一起放进去**：CDS 表和 5 个 rMATS 表放同一个文件夹一起上传，分析跑完即可直接生成肽。
2. **分析完成后再补**：进入「剪接候选新抗原」→ 点「从本机添加编码序列表…」选文件，
   **不需要重跑整个分析**；上传后会自动列进下拉框并选中。

> 表里缺列时，界面会直接说缺哪几列（例如"缺少列：altered_cds"），而不是只丢一句报错。

✅ **列名完全认不出来也能用（列映射）**：像 `序列1 / 序列2 / 位点 / 编号` 这种没有任何线索的表，
系统会**看单元格内容**判断角色——纯 ACGT 且长度是 3 的倍数的列是序列、能与事件表对上的列是事件 ID、
整数列是连接点位置；然后用真实数据回放一遍，判断哪列是参考、哪列是改变后（**即使两列顺序颠倒也能自动纠正**）。

判得不够确定时，页面上会出现「**确认列的含义**」面板：四个下拉框已按猜测预填，下方展示各类的样本内容，
确认一次即可。确认结果保存在表同目录的 `.cds_mapping.json`，**同一个项目以后不再询问**。
保存时会先试算，若这套映射一行肽都产不出来会给出提示（通常是参考/改变后填反了）。

> 只有极少数情况会真的卡住：表里连"哪两列是序列"都判断不出来（例如序列被拆成多段或含 N）。
> 这时页面会明说缺哪个角色，按提示在列映射里手选即可。


| 列名 | 含义 | 要求 |
|---|---|---|
| `event_id` | 事件编号 | 与分析事件表中的 `ID` 对应 |
| `reference_cds` | 参考（组成型）编码序列核酸 | 5'→3'，读码框已确定，只含 ACGT（U 按 T 处理），完整密码子 |
| `altered_cds` | 剪接改变后的编码序列核酸 | 同上 |
| `junction_nt` | **新剪接连接点在 `altered_cds` 中的核苷酸边界位置（整数）** | 满足 `1 ≤ junction_nt < len(altered_cds)`；即前 `junction_nt` 个核苷酸来自剪接点的 5' 侧，其后的来自 3' 侧。**不是序列，不要填碱基** |

**示例** `splice_cds.tsv`（可直接跑通，产出 8-mer 肽 `MAKIYSPD`）：

```
event_id	reference_cds	altered_cds	junction_nt
EV0001	ATGGCCAAGATCTACAGCTGA	ATGGCCAAGATCTACAGCCCTGACTGA	18
```

上例中 `reference_cds` 译作 `MAKIYS`，`altered_cds` 在第 18 个核苷酸后接上新的 6 nt（`CCTGAC`），译作 `MAKIYSPD`；跨连接点、且不在参考蛋白里的肽即被保留。

> 序列硬性要求：只含 `A/C/G/T`（`U` 自动按 `T` 处理）、长度为 3 的整数倍、无内部终止密码子（遇到 `*` 会截断）。

**第 3 步：填 HLA 型别（可选）**。格式必须为 `HLA-[ABC]*两位或三位:两位`，如 `HLA-A*02:01`、`HLA-B*07:02`，多个用逗号分隔。**留空则只出肽、不做免疫原性预测**。

**第 4 步：运行**。系统行为：

- 肽长固定为 **8、9、10、11 mer**（MHC-I 经典长度，不可改）；
- 只保留**横跨新剪接连接点**、且不出现在参考蛋白中的肽（即真正的剪接来源新肽）；
- 若填了 HLA，调用 **IEDB 在线服务**（NetMHCpan 4.1 EL 方法）做 MHC-I 结合预测——**需要联网**，系统按每批 100 条肽自动分批提交，几百条肽通常 30–90 秒；单次上限默认 **20000** 个肽-HLA 组合（`max_predictions` 可调），超出部分会在 manifest 里明确记为 `prediction_truncated`，**不会让整次运行失败**。

**输出文件**（项目目录 `neoantigen_results/` 下，可在结果面板复制/下载/打开目录）：

| 文件 | 内容 |
|---|---|
| `splice_peptides.tsv` | 全部剪接来源新肽 |
| `mhc_i_predictions.tsv` | IEDB 结合预测结果（填了 HLA 才有） |
| `neoantigen_manifest.json` | 运行清单，标注 `workflow_status: exploratory_only`（探索性结果） |

### 5.2 路线 B：moPepGen Docker（工业化标准流程）

用官方 moPepGen 1.4.6 容器直接从 rMATS 原始 JC 表生成变异肽 FASTA。需要传入 **三个版本一致的参考文件（不得 .gz 压缩）**：

| 输入 | 说明 |
|---|---|
| 基因组 FASTA | 如 `GRCh38.fa` |
| 基因注释 GTF | 与 FASTA 同一版本（GENCODE 或 ENSEMBL） |
| 蛋白 FASTA | 与 GTF 同一版本 |

在「剪接候选新抗原」页高级选项中填写：`reference_source`（GENCODE/ENSEMBL）、`reference_version`、三个文件名，可选指定参与的事件类型（se/a3ss/a5ss/mxe/ri）。输出：`events.gvf`、`variant_peptides.fasta`、`manifest.json`、两步日志。

> 路线 B 不产生 CDS 对照表；如需结合路线 A 的连接肽视角，两者可互补。

### 5.3 路线 C：分阶段证据审计工作流（最严谨）

面向课题级/投稿级产出，7 个阶段，每阶段必须显式确认（`parameters.confirm=true`）：

| 阶段 | 需要提供的数据 |
|---|---|
| 0 证据声明 | `normal_design`（正常对照设计）、`genome_build`、`annotation_version`、`coordinate_system`、`input_kind`、`hla_source`、`hla_confidence`、`has_frame_correct_cds` |
| 1 事件过滤 | 确认 `total_support_reads` 为 junction 支持读数；`min_support` / `min_samples` |
| 2 ORF 表 | CDS 四列之外额外需要 `orf_source`、`frame_status`、`premature_stop`（可选 `last_junction_nt`） |
| 3 蛋白组过滤 | 配对的正常组织 / GTEx / 全蛋白组 FASTA + junction 表 |
| 4 表达过滤 | 表 `event_id, expression, expression_unit`（可选复现率列） |
| 5 HLA | 肽-HLA 组合按每批 100 条自动分批预测（默认上限 20000） |
| 6 报告 | 自动生成六段式报告 |

会话保存在运行目录 `neoantigen_workflows/{workflow_id}.json`，重启后自动恢复。

> **科学边界**：仅凭剪接事件坐标无法唯一确定蛋白序列（读码框依赖上游外显子等），所以路线 A 的结果标记为 exploratory（探索性）；路线 C 通过多阶段证据审计收敛不确定性，是发表级推荐路径。

---

## 6. 历史记录与数据管理

### 数据存放位置

| 运行方式 | 运行根目录 |
|---|---|
| Windows 桌面版 / 源码 | `%LOCALAPPDATA%\SpliceGAIP`（旧版临时目录数据已自动迁移） |
| Linux 源码 | `~/.local/share/splicegaip` |
| Docker | 容器内 `/data`，对应命名卷 `splicegaip-data` |

目录结构：`splicegaip.sqlite3`（主库：项目/事件/工件）、`projects/<project_id>/`（图表、报告）、`neoantigen_workflows/`、`logs/`。可用环境变量 `SPLICEGAIP_RUNTIME_ROOT` 覆盖。

### 备份与恢复（服务器）

```bash
docker run --rm -v splicegaip-data:/data -v $PWD:/bak alpine tar -czf /bak/sg_backup.tar.gz /data
# 恢复：
docker run --rm -v splicegaip-data:/data -v $PWD:/bak alpine sh -c "cd / && tar -xzf /bak/sg_backup.tar.gz"
```

> ⚠️ `docker compose down -v` 会**删除数据卷**，慎用。

### 历史项目操作

仪表盘点任意历史项目 → 查看详情 / 打开 HTML 报告 / 下载 PDF / 浏览全部事件 / **删除**（同时删库行与项目目录，不可恢复）。聊天记录按项目保存在浏览器 `localStorage`（`splicegaip.chat.<projectId>`，上限 200 条）。

---

## 7. API 速查表

设了 `SPLICEGAIP_API_KEY` 后，除 `/api/health` 外所有 `/api/*` 需带 `X-API-Key` 请求头（或 Bearer Token）。

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/health` | GET | 健康检查 |
| `/api/upload` | POST | 上传文件（multipart，字段 `files`，可多文件，重名报 422） |
| `/api/ingest/preview` / `apply` / `groups` | POST | 智能接入：预览映射 / 应用映射 / 设样本分组 |
| `/api/analyze` | POST | 创建并运行分析（`query` + `input_dir` + 可选 `project_name`、`thresholds`） |
| `/api/projects` | GET | 项目列表 |
| `/api/projects/{id}/events` | GET | 事件分页查询（`page/size/q/event_type/significant_only/order_by`） |
| `/api/projects/{id}` | DELETE | 删除项目（库 + 目录） |
| `/api/report/{id}?format=html\|pdf` | GET | 生成/下载报告 |
| `/api/figure/{id}/{name}` | GET | 获取图表 |
| `/api/neoantigen/readiness/{id}` | GET | 肽生成就绪检查 |
| `/api/neoantigen/run` | POST | 运行路线 A（`project_id`、`alleles`、`max_predictions`） |
| `/api/neoantigen/mopepgen` | POST | 运行路线 B（`project_id`、`reference_source`、`genome`/`gtf`/`proteome`） |
| `/api/neoantigen/audit` | POST | 证据审计（阶段 0/2） |
| `/api/neoantigen/workflow/start` / `advance` | POST | 分阶段工作流启动/推进 |
| `/api/storage` | GET | 查看存储位置与迁移状态 |

---

## 8. 常见问题

**Q1：上传 rMATS 大文件报 413？**
nginx 前置时必须设置 `client_max_body_size 2048m;`（见 `deploy/nginx.conf`）。Docker 方案走直连 8800 无此问题。

**Q2：IncLevelDifference 列的值和系统算的不一样？**
系统不读该列，而是用 `IncLevel2` 均值 − `IncLevel1` 均值重新计算 ΔPSI，两列本身可能有细微差异。

**Q3：非 rMATS 格式（华大报告、自定义表格）能用吗？**
能，走「智能接入」：上传后确认列映射与分组即可转成标准 rMATS 风格表。但内部只保留 rMATS 事件模型（SE/A5SS/A3SS/MXE/RI）。

**Q4：服务器是 NFS 存储，SQLite 会不会坏？**
默认已关闭 WAL（`SPLICEGAIP_SQLITE_WAL` 默认 0）；本地磁盘部署可设 `SPLICEGAIP_SQLITE_WAL=1` 提升并发。

**Q5：历史记录找不到了？**
旧版数据在临时目录，新版启动时自动迁移到持久目录（逐表 `INSERT OR IGNORE` 幂等迁移），可用 `GET /api/storage` 确认迁移状态。

**Q6：公网域名会变吗？**
`trycloudflare.com` 临时域名在隧道重启后会变，重新生成方法见 `docs/deploy/DEPLOY_NO_SUDO.md`；生产建议绑定自己的域名（Cloudflare Named Tunnel）。

**Q7：IEDB 预测失败？**
路线 A 的 HLA 预测依赖 IEDB 在线服务（NetMHCpan 4.1 EL），服务器需能访问外网。常见原因：网络不通、IEDB 临时不可用、HLA 型别写错（必须是 `HLA-A*02:01` 这种格式）。系统会按每批 100 条肽自动分批重试，失败明细记录在 `neoantigen_manifest.json` 的 `prediction_errors` 里，其余结果不受影响。若只是"某几条没预测到"，多半是 IEDB 未返回该肽，可稍后重跑（结果有磁盘缓存，重复请求会很快返回）。

**Q8：肽长能改成 7-mer 吗？**
不能，路线 A 固定 8–11 mer（MHC-I 经典呈递长度）；moPepGen 路线由其自身参数控制。
