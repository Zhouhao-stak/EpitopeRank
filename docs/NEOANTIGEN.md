# 剪接来源候选新抗原分析

桌面界面会先检查当前项目是否包含剪接事件及编码序列表。检查只识别表头，不验证序列是否来自正确读码框。找到编码序列表后可直接生成探索性候选肽；HLA 留空时不执行 MHC 预测。分阶段审计、moPepGen 与手动选择其他文件位于“高级选项”中。

## Docker 中的 moPepGen

对于原始 rMATS JC 事件表，项目提供 `scripts/mopepgen_docker.py` 调用官方 moPepGen 1.4.6 容器。它生成变异事件 GVF 和变异肽 FASTA，**不生成本项目阶段 3 所需的参考/异常 CDS 对照表，也不是 HLA 结合预测**；默认肽生成参数用于蛋白质组学的酶切肽。不要把其输出直接当作已验证的剪接新抗原。

在已启动 Docker 的终端中调用，路径需替换为真实文件，且输出目录必须不存在：

```powershell
.\venv\Scripts\python.exe scripts\mopepgen_docker.py --se path\SE.MATS.JC.txt --genome path\genome.fa --gtf path\annotation.gtf --proteome path\proteome.fa --reference-source GENCODE --reference-version "GRCh38, GENCODE release <版本>" --output path\new_output
```

也可以增加 `--a3ss`、`--a5ss`、`--mxe`、`--ri`。基因组 FASTA、GTF 与蛋白 FASTA 版本必须一致，并与事件坐标和染色体命名对应；版本声明不能代替核验。脚本保存命令、输入 SHA-256、容器镜像摘要和日志。不同版本的工具可能要求原始 rMATS 完整列，供应商转换表和技术性分组不能自动等同于原始组间统计。桌面界面会自动识别项目目录中标准命名的 rMATS JC 文件并调用 Docker，结果仍不能自动进入 ORF 阶段。

**当前状态：探索性分析，尚未实现 `docs/prompts/splice-neoantigen-pipeline.md` 中的完整流程。** 现有网页生成入口不会自动执行该文档要求的事件质量门控、ORF 重建、NMD 判断、配对正常/GTEx/全蛋白组过滤、表达与复现率分析，也不生成完整的六段报告。不得将其结果解释为经过这些阶段验证的新抗原。

网页提供分阶段入口：选择当前项目，填写表单并逐步确认。进度保存到本机运行目录，可在重启后恢复；项目输入改变时须重新审计。输入必须是已经量化的事件表，阶段 1 不执行 reads/BAM 事件发现或 BH 校正。阶段 2 需提供明确阈值并确认 `total_support_reads` 是 junction 支持读数；缺失质量字段的事件不会被当成通过。

阶段 3 使用上游重建的 ORF 表，除四个 CDS 列外还必须提供 `orf_source`、`frame_status`（`in_frame` 或 `frameshift`）和 `premature_stop`（`yes` 或 `no`）。提前终止单独列出；可提供 `last_junction_nt`（自编码起点到最后外显子连接点的核苷酸数，允许位于 3′ UTR），以 50 nt 距离规则估计 NMD 候选，缺少时为未知。这是经验性预测而非实测结果。

阶段 4 对配对正常、GTEx 蛋白及全蛋白组 FASTA 分层精确过滤。事件连接点表必须有 `event_id, chromosome, intron_start, intron_end, strand`；GTEx 表有相同坐标列（不含 event_id），均为 1-based inclusive 内含子范围，基因组版本需一致。任何一个事件连接点命中即排除该事件的候选肽；GTEx 未检出不能证明正常组织中不存在。正常表达表包含 `gene_id, tissue, expression, unit`，报告观测值，缺失不等于零，不自动设高表达阈值。文件来源、覆盖范围及版本须由用户核实。

阶段 5 表含 `event_id, expression, expression_unit`，可选 `recurrence_count, recurrence_total`。阶段 6 填写 HLA、来源和置信度后发送 IEDB；阶段 7 输出六段结构化报告。所有输入文件须位于项目数据目录。自动 ORF 重建尚未实现，且本入口仍是实验性实现，不是完整符合文档的流程。

## 输入与边界

提供剪接事件数据及编码序列对照表。系统**按表头内容**识别对照表，文件名不限（历史上常用的 `splice_orfs` / `coding_pairs` 仍优先）；支持 `.tsv`、`.txt`、`.csv`，分隔符与 UTF-8/GBK 编码自动判断。表头列名可使用常见别名（如 `事件ID / 参考序列 / 变异序列 / 连接点`）。分析完成后也可在页面上「从本机添加编码序列表」直接补交，无需重跑分析。事件数据可使用标准事件表或加载器支持的原始格式；`event_id` 必须与加载后的事件 ID 一致。每行必须包含：

| 列 | 含义 |
| --- | --- |
| `event_id` | 必须与标准事件表完全一致 |
| `reference_cds` | 正常转录本的编码序列，5′→3′，已确定读码框 |
| `altered_cds` | 剪接改变后转录本的编码序列，5′→3′，已确定读码框 |
| `junction_nt` | 异常 CDS 中新剪接连接点前的核苷酸数，从 5′ 端计数 |

CDS 接受完整的 A/C/G/T 密码子，也接受 U 并将其视作 T。模块翻译至首个终止密码子，只保留跨连接点的 8–11 aa 肽段，并排除在该行正常 ORF 内出现的肽段。结果 `splice_peptides.tsv` 中 `start_aa` 是从 1 开始的肽起点，`junction_aa` 是连接点前完整密码子的数量；连接点位于密码子内部时，该密码子跨越连接点。事件 ID 重复导致无法确定关联时，该行会跳过。`neoantigen_manifest.json` 记录跳过原因和预测错误。

网页“剪接候选新抗原”入口可上传事件表、CDS 对照表和可选的样本分组表。可留空 HLA；填写真实 HLA-I 型别（例如 `HLA-A*02:01`）后，会将候选肽段发送到 IEDB 官方接口，使用 **NetMHCpan 4.1 EL** 模型预测，并保存 `mhc_i_predictions.tsv` 的原始响应、score 和 percentile rank。EL 是抗原呈递相关的模型分数，并非实测亲和力；未填写 HLA 不执行预测。预测按每批 100 条肽自动分批提交，单次上限默认 20000 个肽段与 HLA 组合（超出部分记入 manifest 的 `prediction_truncated`，不会让整次运行失败）。CDS 表的列按表头别名与单元格内容识别，列名无法确定时可用 `POST /api/neoantigen/column-map` 保存人工确认的映射（存于表同目录的 `.cds_mapping.json`）。此功能依赖互联网和 IEDB 服务，错误记录在 manifest 中，软件不包含离线 NetMHCpan。

## 科学解释

标准事件坐标和 PSI **不足以确定新蛋白序列**。必须使用与样本一致的参考基因组、转录本 CDS 注释、读码框及剪接连接点，或来自可信上游工具的已重建 ORF。本功能不会从坐标猜测序列。特别是华大单样本报告没有组间显著性，不能据此声称肿瘤特异剪接。

“候选肽段”表示与所提供正常 ORF 相比的新序列；并未排除其他正常转录本或全蛋白组中的相同肽段。IEDB MHC-I 结合预测不是抗原呈递、免疫原性或临床有效性的证明。正式研究还需肿瘤正常配对、表达证据、HLA 分型、正常组织过滤及实验验证。

方法参考：[pVACsplice 文档](https://pvactools.readthedocs.io/en/stable/pvacsplice.html)；[IEDB 官方 API](https://tools.iedb.org/main/tools-api/)。
