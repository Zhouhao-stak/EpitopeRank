# 数据资源目录（Datasets）

> 本页只描述**仓库里实际存在、且已核对过**的数据，以及它们的可用边界。所有“能/不能加载”的
> 结论都来自对当前 checkout 的实际运行，不是推测。
>
> 平台当前的事件分析只接受两类输入：**rMATS 五类 JC 表**（`SE/A3SS/A5SS/MXE/RI.MATS.JC.txt`）
> 或标准事件主表 `AS_event_master.tsv`。肽预测还需要额外的 **CDS 对照表**（见第 7 节）。

---

## 1. 总览

| 数据集 | 位置 | 类型 | 能否直接 `run.py analyze` |
| --- | --- | --- | --- |
| PRELP 黑色素瘤 rMATS | `public_datasets/PRELP_melanoma_rmats/rmats_jc/` | rMATS JC 表 + 样本元数据 | ✅ 能（实测 27,103 事件 / 6 样本） |
| TCGA Pan-Cancer AS | `public_datasets/TCGA_PanCan_AS/` | 差异剪接检验结果（每基因最显著事件） | ❌ 不能（非 rMATS 列结构） |
| GSE319608 小鼠剪接 PSI | `public_datasets/GSE319608_rmats/` | PSI 矩阵（Excel） | ❌ 不能（非事件表，无 p/FDR） |
| HCC1395 pVACtools 输入 | `public_datasets/HCC1395_pVACtools/` | VCF / junction / GTF / 蛋白 FASTA / HLA | ❌ 不能（非剪接事件表） |
| splice2neo 源码与 toy 数据 | `public_datasets/splice2neo_public/` | R 包 + `.rda` toy 数据 | ❌ 不能（R 数据对象） |
| 肽参考表 | `epitoperank/peptide/reference/` | HLA 等位基因 / IEDB assay 抽取 | —（肽预测用） |
| 肽演示数据 | `examples/peptide_demo/` | 真实 IEDB 肽表 + 合成阳性对照 CDS | —（肽预测 demo） |

---

## 2. PRELP 黑色素瘤 rMATS（推荐入门）

**内容**

```
public_datasets/PRELP_melanoma_rmats/
├── PRELP-high_vs_PRELP-low_{SE,A3SS,A5SS,MXE}.xls   # 与 rmats_jc 下同名文件字节一致
└── rmats_jc/
    ├── SE.MATS.JC.txt
    ├── A3SS.MATS.JC.txt
    ├── A5SS.MATS.JC.txt
    ├── MXE.MATS.JC.txt
    └── sample_metadata.tsv
```

- `sample_metadata.tsv`：6 个样本，`PRELP-high` ×3 vs `PRELP-low` ×3，组织 `melanoma`，batch `B1`。
- 厂商 `.xls` 实际是**制表符文本**：`PRELP-high_vs_PRELP-low_SE.xls` 与
  `rmats_jc/SE.MATS.JC.txt` 的 SHA-256 相同
  （`8F08D1C7BB294BE82CE7684519566AAB9F7550A82114C59896FD130473E4210F`），
  因此两种命名都可作为输入，保留一份即可。
- 实测加载：**27,103 个事件、6 个样本**。

**能做什么**

```bash
python run.py analyze \
  --input public_datasets/PRELP_melanoma_rmats/rmats_jc \
  --query "分析 PRELP-high vs PRELP-low 的差异剪接"
```

支持平台的默认事件层分析（差异剪接、候选基因排序、GO/KEGG 富集、图件与 HTML/PDF 报告）；
实测加载为 27,103 个事件 / 6 个样本。也可以作为新抗原分阶段流程的事件输入（阶段 3 仍需自备
CDS 表）。

**局限**

- 只有 3 vs 3、无配对正常组织、无 HLA 分型；结论只能到“组间差异剪接”，不能声称肿瘤特异。
- 只有事件层 PSI/ΔPSI/FDR，没有转录本序列；要做肽预测必须另备 CDS 对照表。
- 厂商 `.xls` 与 rMATS 文本重复，上传时保留一套即可，避免被识别成多个输入。

---

## 3. TCGA Pan-Cancer AS

**内容**

```
public_datasets/TCGA_PanCan_AS/
├── results_alt_splice_difftest_gdc.tar.gz          # 约 33 MB，目录的 tar.gz 归档
└── results_alt_splice_difftest_gdc/
    ├── README.txt
    └── testing_<CANCER>-T_vs_<CANCER>-N_MERG/       # 14 个癌种目录，共 71 个文件
        ├── test_results_C2_alt_3prime.gene_unique.tsv
        ├── test_results_C2_alt_5prime.gene_unique.tsv
        ├── test_results_C2_exon_skip.gene_unique.tsv
        ├── test_results_C2_intron_retention.gene_unique.tsv
        └── test_results_C2_mutex_exons.gene_unique.tsv
```

- 14 个癌种目录（BLCA、BRCA、COAD、HNSC、KIRC、KIRP、LIHC、LUAD、LUSC、PRAD、READ、
  STAD、THCA、UCEC；目录名形如 `testing_BLCA-T_vs_BLCA-N_MERG`）。
- 列结构（实测表头）：
  `event_id, gene, p_val, p_val_adj, mean_event_count_A, mean_event_count_B,
  log2FC_event_count, mean_gene_exp_A, mean_gene_exp_B, log2FC_gene_exp`。
- `README.txt` 原文：**Each result file contains the most significant event for each gene.**

**能做什么**

- 作为“泛癌差异剪接”的**发现/示意/对照**素材：挑癌种、按 `p_val_adj` 看显著基因、做
  基因层面的汇总或作图。
- 作为外部证据与自有 rMATS 结果做基因层交叉核对。

**不能做什么**

- 不能直接 `run.py analyze`：实测报错
  `No recognizable rMATS data ...`。平台的数据入口是 rMATS 事件表（文件名不限，
  按表头自动识别）或 `AS_event_master.tsv`；这里是一张基因层汇总表，缺少
  逐样本 PSI 与事件类型列，属于“内容不匹配”而非“命名不匹配”。
- **不能在这张表上重做全表 BH 校正**：文件已经是“每基因最显著事件”的子集，`p_val_adj`
  是上游在全表上算好的；把它当完整事件表重新校正会得到错误结论。
- 没有逐样本 PSI、没有事件类型列，不能进入肽预测的 ORF 重建。

**补充**：`public_datasets/kich_test.download` 是一个 1,318,912 字节的
`PSI_download_KICH.zip` 未完成下载（`zipfile` 报 `BadZipFile`），
`_headers_kich.txt` 是当时的 HTTP 响应头；两者都不是可用输入，建议重新下载。

---

## 4. GSE319608 小鼠剪接 PSI

**内容**

```
public_datasets/GSE319608_rmats/
├── GSE319608_rMATS_36.xlsx     # 可读：1 个 sheet「36 Exon Subset」
├── GSE319608_rMATS_all.xlsx    # 31,546,172 字节，当前无法读取（见下）
├── fix02.bin                   # 1,879,493 字节，来源/用途不明，代码未引用
└── fix05.bin                   # 491,520 字节，来源/用途不明，代码未引用
```

`GSE319608_rMATS_36.xlsx` 实测：**36 行数据、100 列** = `Gene` + `Coordinates` + **98 个样本列**：

| 样本列前缀 | 列数 |
| --- | --- |
| `Gastroc_1..24` | 24 |
| `Timecourse_gastroc_1..20` | 20 |
| `Timecourse_quad_1..24` | 24 |
| `EU_total_quad_1..10` | 10 |
| `EU_nascent_quad_1..10` | 10 |
| `3month_quad_1..10` | 10 |

- `Gene` 是小鼠基因符号（如 `Abcc9`、`Atp2a1`），`Coordinates` 形如
  `chr6:-:<start>:<end>:<...>`（含染色体、链、起止坐标），单元格值是 **PSI（0–1）**，
  例如 `0.361`、`0.996`。
- 表里**没有 p 值、FDR、事件类型、ΔPSI**，只有 PSI 矩阵。

**能做什么**

- 描述性分析：样本间 PSI 分布、热图、聚类、时间序列/处理组趋势比较。
- 作为“PSI-only 数据”的例子，验证平台的类型识别不会把 PSI 矩阵误当成事件表。

**不能做什么**

- 不能做差异检验（没有 p/FDR，也没有生物学重复的组定义）；不能生成事件级候选表。
- 不能直接 `run.py analyze`：实测报错 `No recognizable rMATS data ...`。
- `GSE319608_rMATS_all.xlsx` 当前**不可用**：zip 中央目录记录的偏移为负值（如
  `xl/worksheets/sheet1.xml` 的 `header_offset = -7,880,801`），`openpyxl` 读取时报
  `OSError: [Errno 22] Invalid argument`。请从 GEO 重新下载完整文件后再用；不要基于
  该文件下结论。`fix02.bin` / `fix05.bin` 不是可识别的表格，代码也没有引用。

---

## 5. HCC1395 pVACtools 输入

**内容**

```
public_datasets/HCC1395_pVACtools/
├── HCC1395_inputs.zip                 # 输入归档
├── ref_genome.tar.partial             # 文件名带 .partial，不能视为完整参考
└── HCC1395_inputs/
    ├── HCC1395.splice_junctions.tsv   # STAR junction 表
    ├── annotated.expression.vcf.gz    # 表达注释 VCF（+ .tbi）
    ├── phased.vcf.gz                  # 定相 VCF（+ .tbi）
    ├── star-fusion.fusion_predictions.tsv
    ├── Homo_sapiens.GRCh38.105.chr.gtf.gz
    ├── Homo_sapiens.GRCh38.pep.all.fa.gz
    ├── optitype_normal_result.tsv     # HLA 分型（OptiType）
    └── agfusion_results/              # 20 个融合基因结果目录
```

- `HCC1395.splice_junctions.tsv` 表头：
  `chrom, start, end, name, score, strand, splice_site, acceptors_skipped,
  exons_skipped, donors_skipped, anchor, known_donor, known_acceptor,
  known_junction, gene_names, gene_ids, transcripts, variant_info`。
- `optitype_normal_result.tsv` 实测 HLA：
  `A*29:02 / A*29:02`、`B*45:01 / B*82:02`、`C*06:02 / C*06:02`
  （正常样本，OptiType；可直接作为 `--alleles` 的来源之一，但要注明分型方法）。
- 参考：GRCh38 GENCODE 105 的 GTF 与蛋白 FASTA；`ref_genome.tar.partial` 文件名带
  `.partial`，不要当完整参考使用。

**能做什么**

- pVACtools / moPepGen 类新抗原流程的输入素材（VCF + junction + GTF + 蛋白 FASTA）。
- 作为 HLA 分型来源，喂给肽预测：

```bash
python run.py peptide \
  --peptides examples/peptide_demo/peptides.tsv \
  --alleles "HLA-A*29:02,HLA-B*45:01,HLA-C*06:02" \
  --mhc-class class1 \
  --out out/hcc1395_hla_demo
```

（是否被 IEDB 方法支持以 `peptide --capabilities` 和 IEDB 返回为准。）

**不能做什么**

- 不能直接 `run.py analyze`：没有 rMATS JC 表；`splice_junctions.tsv` 是 junction 计数，
  不是事件 PSI/ΔPSI/FDR 表。
- 不能从这份数据自动得到 ORF/CDS；仍需上游重建流程。

---

## 6. splice2neo 源码与 toy 数据

**内容**：`public_datasets/splice2neo_public/` 是 R 包源码（38 个 `R/*.R` 文件），
`data/` 下是 `.rda` toy 对象：`toy_cds.rda`、`toy_junc_df.rda`、`toy_junc_id.rda`、
`toy_junc_id_enst.rda`、`toy_transcripts.rda`、`toy_transcripts_gr.rda`、
`canonical_juncs.rda`、`unsorted_junc_df.rda`。包内还有
`R/add_peptide.R`、`R/modify_tx.R`、`R/parse_gtf.R`、`R/mmsplice.R` 等函数。

**能做什么**

- 作为“从剪接事件到肽”的方法学参考（尤其 `add_peptide`、`choose_tx`、`modify_tx`）。
- 在 R 环境中用 toy 数据生成 CDS 对照表，再交给本平台的 `--cds` 流程。

**不能做什么**

- 平台不读取 `.rda`；也不能直接 `run.py analyze`。
- toy 数据只适合流程验证，不能用于生物学结论。

---

## 7. 真实 ORF/CDS 输入（肽预测的前提）

任何“从剪接事件到肽”的步骤都必须先有**读码框正确**的 CDS 对照表：

| 列 | 要求 |
| --- | --- |
| `event_id` | 与事件表一致；重复/缺失会被跳过并写入 `manifest.json` |
| `reference_cds` | 正常转录本 CDS，5′→3′，完整密码子，仅 A/C/G/T（U 视为 T） |
| `altered_cds` | 剪接改变后的 CDS，同上 |
| `junction_nt` | 异常 CDS 中**新连接点前**的核苷酸数，必须落在 CDS 内部 |

平台**不会**从 `chromosome/strand/exonStart` 等坐标猜序列。如果你只有 rMATS 表，需要先用
STAR + GTF + 基因组 FASTA（或用 moPepGen / pVACsplice / splice2neo）重建 ORF；
`NEOANTIGEN.md` 描述了本仓库已有的分阶段入口与 moPepGen 容器调用方式。

---

## 8. 肽参考数据（本仓库新增）

`epitoperank/peptide/reference/`：

| 文件 | 行数 | 内容 | 来源 |
| --- | --- | --- | --- |
| `hla_class1_alleles.tsv` | 10,386 | IEDB `netmhcpan_el-4.1` 接受的 HLA-I 名称 | IEDB Tools API |
| `hla_class2_alleles.tsv` | 4,960 | IEDB `netmhciipan_el-4.1` 接受的 HLA-II 名称 | IEDB Tools API |
| `known_epitopes.tsv` | 1,078 | 12 个常见等位基因各取 120 条、去重后的 T 细胞 assay 抽取 | IEDB Query API `tcell_search` |
| `manifest.json` | — | 抓取时间、URL、行数、sha256 | 脚本生成 |

- 加载器严格校验后可用 **10,376** 个 HLA-I（10 个 `HLA-E*`/`HLA-G*` 不受支持被跳过）、
  **4,960** 个 HLA-II。
- `known_epitopes.tsv` 列：`peptide, length, mhc_class, mhc_restriction,
  qualitative_measure, assay, source_organism, pubmed_id, source`；是**真实 assay 结局**
  （含 Positive/Negative），不是结合亲和力基准。
- 刷新：`python scripts/fetch_peptide_reference.py --epitopes-per-allele 120`
  （`--skip-epitopes` 只更新等位基因表；`--output` 改目录）。
- 这些表是**方法可用名称**，不是人群频率；频率加权请使用 AFND/IEDB 针对研究队列的数据。

---

## 9. 肽演示数据（`examples/peptide_demo/`）

| 文件 | 性质 | 用途 |
| --- | --- | --- |
| `peptides.tsv` | **真实** IEDB assay 抽取（200 条；`peptide, known_hla, known_outcome, source_organism, pubmed_id`） | 肽表模式预测、回归测试 |
| `AS_event_master.tsv` | **合成**事件（`DEMO:SE:*`，FDR=0.01、ΔPSI=0.35 为占位值） | 走通 CDS 模式 |
| `splice_orfs.tsv` | **合成阳性对照**：`altered_cds` 在合成连接点处编码真实表位；参考 CDS 为突变版 | 验证“事件→肽”链路 |
| `README.md` | 说明数据性质 | 必读 |

生成脚本：`python examples/make_peptide_demo.py`（依赖
`epitoperank/peptide/reference/known_epitopes.tsv`）。合成数据只用于流程验证，
**不能**作为生物学发现写进报告。

```bash
# 只做预测（真实肽）
python run.py peptide --peptides examples/peptide_demo/peptides.tsv \
  --alleles HLA-A*02:01 --mhc-class class1 --out out/peptide_table_demo

# 事件 -> 肽（合成阳性对照）
python run.py peptide --input examples/peptide_demo \
  --cds examples/peptide_demo/splice_orfs.tsv \
  --alleles HLA-A*02:01 --mhc-class class1 --out out/peptide_splice_demo
```

---

## 10. 从哪里获取更多公开数据

只列常用、稳定的入口；下载后请自行核对**基因组版本、注释版本、样本分组、坐标基准**。

| 资源 | 入口 | 适合补充什么 |
| --- | --- | --- |
| GEO | <https://www.ncbi.nlm.nih.gov/geo/>（本仓库对应 <https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE319608>） | 原始/处理后的表达与剪接数据 |
| GDC / TCGA | <https://portal.gdc.cancer.gov/> | 泛癌 RNA-seq、临床与分型 |
| IEDB | <https://www.iedb.org/>；工具 API <https://tools.iedb.org/main/tools-api/>；Query API <https://query-api.iedb.org/> | 表位、MHC 结合/加工预测、assay 记录 |
| UniProt | <https://www.uniprot.org/>；REST <https://rest.uniprot.org/> | 正常蛋白组（novelty 过滤的参考 FASTA） |
| Ensembl | <https://www.ensembl.org/>；REST <https://rest.ensembl.org/> | GTF、转录本/CDS 序列 |
| GTEx | <https://gtexportal.org/> | 正常组织表达/junction（novelty 与表达证据） |
| AFND | <http://www.allelefrequencies.net/> | HLA 人群频率（本仓库不内置频率） |

建议流程：先用 GEO/GDC 拿到**带生物学重复**的剪接结果 → 用 Ensembl GTF + 基因组 FASTA
重建 ORF → 用 UniProt/GTEx 做 normal 过滤 → 再用 IEDB 做结合/加工预测。任何一步缺失，
都要在报告里写成局限，而不是用默认值补齐。
