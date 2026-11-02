# 演示视频讲解稿 · Demo Video Walkthrough

> 中英对照的双语讲解稿，对应 `media/videos/` 下的两段录屏。
> Bilingual narration script for the two screen recordings in `media/videos/`.

两段录屏都是**无配音的界面实录**（`肽.mp4` 音轨完全静音，`初步分析.MP4` 只有极低的操作声），
所以这里提供的是**字幕式讲解**：每个时间点配一句中文、一句英文，可直接当配音稿念，也可直接读字幕。

Both clips are silent screen captures — the audio track of `肽.mp4` is fully muted, and
`初步分析.MP4` carries only faint UI noise. The narration below is therefore subtitle-style:
one Chinese line and one English line per time range. Use it as a voice-over script or just read the subtitles.

| 视频 Video | 时长 Length | 分辨率 Resolution | 内容 Content |
|---|---|---|---|
| [`splice-neoantigen-peptides.mp4`](../media/videos/splice-neoantigen-peptides.mp4) | 1:00 | 1280×720 | 剪接来源候选新抗原：事件 → 肽 → HLA 预测 |
| [`pipeline-overview.mp4`](../media/videos/pipeline-overview.mp4) | 1:47 | 3834×2160 | 全流程：接入体检 → 六 Agent 流水线 → 图件 |

带中英双轨软字幕的版本（播放器里可切换语言）：
Bilingual soft-subtitle versions (switchable in any modern player):

- [`splice-neoantigen-peptides.bilingual.mp4`](../media/videos/splice-neoantigen-peptides.bilingual.mp4)
- [`pipeline-overview.bilingual.mp4`](../media/videos/pipeline-overview.bilingual.mp4)

---

## 一、剪接来源候选新抗原 · Splice-Derived Neoantigen Candidates

**一句话 / In one line**：从一条剪接事件，走到值得拿去做实验验证的候选肽。
From one splicing event to a shortlist of peptides worth bench validation.

**画面顺序 / Screen order**：
项目数据检查 → 填 HLA-I 型别 → 三步进度（加载编码序列 / 解析可翻译事件 / HLA 预测）
→ 完成摘要（132 肽 / 486 事件）→ 候选肽结果表（#/序列/长度/来源事件/HLA/亲和力/Rank%）。

| 时间 | 中文讲解 | English narration |
|---|---|---|
| 00:00–00:05 | EpitopeRank「剪接来源候选新抗原」：从一条剪接事件，走到值得拿去做实验的候选肽。 | EpitopeRank, "splice-derived neoantigen candidates": from a single splicing event to peptides worth testing at the bench. |
| 00:05–00:10 | 项目 test2 已载入 100,512 条剪接事件。平台先做数据检查：编码序列列表还没找到，这是进入新抗原流程的前提。 | Project test2 already holds 100,512 splicing events. The platform checks the data first: the coding-sequence list is still missing, and that list is the precondition for this workflow. |
| 00:10–00:14 | 第二步填入受试者 HLA-I 型别：HLA-A\*02:01 与 HLA-B\*07:02，然后点「生成候选肽」。 | Step two: enter the subject's HLA class I types, HLA-A\*02:01 and HLA-B\*07:02, then click "Generate candidate peptides". |
| 00:14–00:20 | 三步依次点亮：加载参考编码序列 → 解析可翻译的剪接事件 → HLA 结合预测。 | Three steps light up in order: load reference coding sequences, parse translatable events, predict HLA binding. |
| 00:20–00:25 | 只有跨过剪接连接点、且能翻译成 8–11 个氨基酸的肽段才进候选池，正常蛋白组里已经出现过的肽会被剔掉。 | Only peptides that span the splice junction and translate into 8–11 residues enter the pool; peptides already present in the normal proteome are removed. |
| 00:25–00:31 | 这也是它不「一把梭」的原因：每个阶段都是一道人工确认门，进度、跳过原因、预测失败都会留痕。 | That is why it never runs unattended end to end: every stage is a human confirmation gate, and skips or failures are logged. |
| 00:31–00:36 | 81% 时进入最后一步 HLA 结合预测：调用 IEDB NetMHCpan 4.1 EL，按真实分型逐条算亲和力与 Rank%。 | At 81% the last step begins: HLA binding prediction via IEDB NetMHCpan 4.1 EL, scoring affinity and Rank% against the real HLA types. |
| 00:36–00:42 | 完成：132 条候选肽，来自 486 条可翻译的剪接事件，结果保存在本项目目录里。 | Done: 132 candidate peptides from 486 translatable splicing events, saved into the project directory. |
| 00:42–00:48 | 打开候选肽表：序列、长度、来源事件、HLA 型别、预测亲和力 (nM)、Rank%，支持筛选与导出 CSV。 | The table lists sequence, length, source event, HLA type, predicted affinity (nM) and Rank%, with filtering and CSV export. |
| 00:48–00:54 | 第一行 ALVPGTSSK：9 个氨基酸，来自 SE_0123，HLA-A\*02:01，预测亲和力 12.4 nM，Rank 0.12%。 | Row one, ALVPGTSSK: 9 residues, from event SE_0123, HLA-A\*02:01, predicted affinity 12.4 nM, Rank 0.12%. |
| 00:54–01:00 | 边界要记牢：结合预测 ≠ 抗原呈递 ≠ 免疫原性。这是一份「值得做实验验证」的候选清单，不是结论。 | Mind the boundary: binding prediction is not presentation, and not immunogenicity. This is a shortlist for validation, not a conclusion. |

---

## 二、完整分析流程 · End-to-End Analysis Pipeline

**一句话 / In one line**：一份已量化的剪接事件表进去，一份带方法学留痕的报告和可投稿的图出来。
A quantified event table goes in; a figures-and-report package with a full methods trail comes out.

**画面顺序 / Screen order**：
仪表盘与新建项目弹窗 → 智能接入检查（90 事件 / 20 样本 / 100% FDR）→ 分组确认
→ AI 流水线 50% → 83% → 100%（六个 Agent）→ 火山图 → PSI 热图。

| 时间 | 中文讲解 | English narration |
|---|---|---|
| 00:00–00:05 | EpitopeRank 的完整分析流程：从一份已量化的剪接事件表，到可以投稿的图和报告。 | The full EpitopeRank flow: from a quantified splicing-event table to publication-ready figures and a report. |
| 00:05–00:10 | 新建分析项目：命名 test，用一句话写清分析目标「进行分组差异」，上传的是上游已经完成定量的结果表。 | Create a project: name it test, state the goal in one line ("group difference"), and upload the results quantified upstream. |
| 00:10–00:17 | rMATS、SUPPA2、MAJIQ、LeafCutter、华大 RNAref 都能直接认；FASTQ 和比对不在这一层——平台从下游开始接手。 | rMATS, SUPPA2, MAJIQ, LeafCutter and BGI RNAref are recognised automatically. No FASTQ or alignment here — the platform starts downstream. |
| 00:17–00:23 | 点「智能分析」后先做接入体检：90 个有效事件、20 个样本、FDR 覆盖 100%、ΔPSI 覆盖 100%。 | "Smart analysis" runs an ingestion check first: 90 valid events, 20 samples, 100% FDR coverage, 100% ΔPSI coverage. |
| 00:23–00:30 | 样本分组 Tumor vs Normal 必须由人确认才写入，模型不猜分组——这是写进代码的规则之一。 | Sample groups, Tumor vs Normal, must be confirmed by a human before being written. The model never guesses groups — that rule is hard-coded. |
| 00:30–00:35 | 流水线启动，六个 Agent 串行推进：数据 → 质控 → 剪接检测 → 统计 → 注释 → 解读。 | The pipeline starts. Six agents run in sequence: data, QC, splice detection, statistics, annotation, interpretation. |
| 00:35–00:42 | 50%：统计 Agent 在工作。卡方检验配 BH 校正的 FDR，再叠一道 ΔPSI 效应量门槛，把「真的变了」的事件挑出来。 | 50%: the statistics agent is working. Chi-square tests with BH-corrected FDR plus a ΔPSI effect-size gate isolate events that genuinely changed. |
| 00:42–00:49 | 默认阈值筛不出结果时，它会按数据分布自适应放宽，并把「为什么放宽」写进 Methods，而不是悄悄改数字。 | When default thresholds return nothing, it relaxes them adaptively by the observed distribution and writes down why — rather than quietly moving numbers. |
| 00:49–00:56 | 每个 Agent 的状态、结果都实时回报，前四个已经绿灯，注释与解读还在队列里排队。 | Every agent reports status and results in real time: the first four are green, annotation and interpretation are still queued. |
| 00:56–01:02 | 83%：解读 Agent 正在生成生物学解读，证据来自基因注释与文献检索的结果。 | 83%: the interpretation agent is drafting the biological reading, drawing on gene annotation and literature retrieval. |
| 01:02–01:18 | 六个 Agent 全部完成，结果落进项目目录：一组标准图件、候选排序表、HTML + PDF 报告，方法学留痕都在正文里。 | All six agents finish and results land in the project directory: standard figures, a ranked candidate table, an HTML + PDF report with methods trails in the body. |
| 01:18–01:25 | 进入「可视化」：火山图，横轴 ΔPSI，纵轴 −log10(FDR)，红色虚线是 FDR = 0.05 的门槛。 | Into "Visualisation": the volcano plot, ΔPSI on x and −log10(FDR) on y, with FDR = 0.05 as a red dashed line. |
| 01:25–01:32 | 这一轮共 90 个事件入库，橙色点是同时通过 FDR < 0.05 与 \|ΔPSI\| > 0.1 的候选。 | 90 events are in this run; orange points pass both FDR < 0.05 and \|ΔPSI\| > 0.1. |
| 01:32–01:40 | 切到 PSI 热图：Top 25 事件 × 20 个样本，颜色是 0–1 的 PSI，哪一组整体偏移，一眼能看出来。 | Switching to the PSI heatmap: top 25 events by ΔPSI across 20 samples, colour is PSI from 0 to 1, so a group-wide shift is visible at a glance. |
| 01:40–01:47 | 图件出 300 dpi PNG 加 SVG 双份，能直接进投稿件；要补图不必重跑分析——图件从持久化的项目状态里取。 | Figures come as 300 dpi PNG plus SVG, ready for a manuscript. No rerun needed — figures come from persisted project state. |

---

## 三、字幕文件与重新生成 · Subtitles and Rebuild

字幕为纯 UTF-8 无 BOM 的 `.srt`，一条时间轴一份语言文件，方便单独校对：

| 文件 | 语言 | 对应视频 |
|---|---|---|
| `media/subtitles/pipeline-overview.zh.srt` | 中文 | 全流程 |
| `media/subtitles/pipeline-overview.en.srt` | English | 全流程 |
| `media/subtitles/splice-neoantigen-peptides.zh.srt` | 中文 | 新抗原候选肽 |
| `media/subtitles/splice-neoantigen-peptides.en.srt` | English | 新抗原候选肽 |

改完字幕，用 ffmpeg 重新封装双轨软字幕版（**不重编码画面**，几秒完成，体积几乎不变）：

```bash
# 需要 ffmpeg 4.x+；画面与音轨直接 copy，只新增两条字幕轨
for n in splice-neoantigen-peptides pipeline-overview; do
  ffmpeg -y -i "media/videos/$n.mp4" \
    -sub_charenc UTF-8 -i "media/subtitles/$n.zh.srt" \
    -sub_charenc UTF-8 -i "media/subtitles/$n.en.srt" \
    -map 0:v -map 0:a? -map 1 -map 2 \
    -c:v copy -c:a copy -c:s mov_text \
    -metadata:s:s:0 language=zho -metadata:s:s:1 language=eng \
    "media/videos/$n.bilingual.mp4"
done
```

想要**硬字幕**版（直接压在画面上，任何人下载即看），把字幕滤镜加上重编码：

```bash
ffmpeg -y -i media/videos/pipeline-overview.mp4 \
  -vf "subtitles=media/subtitles/pipeline-overview.zh.srt:force_style='FontName=Microsoft YaHei,FontSize=22,Outline=2'" \
  -c:v libx264 -crf 20 -c:a copy media/videos/pipeline-overview.hardsub.zh.mp4
```

---

## 四、术语对照 · Glossary

| 中文 | English | 说明 |
|---|---|---|
| 剪接事件 | splicing event | 一次可变剪接产生的具体结构变化（SE / RI / A3SS / A5SS / MXE 等） |
| PSI | percent spliced in | 该事件「被剪进去」的比例，0–1 |
| ΔPSI | delta PSI | 两组间 PSI 之差，默认效应量门槛 0.10 |
| FDR | false discovery rate | BH 校正后的错误发现率，默认门 0.05 |
| 自适应阈值 | adaptive thresholds | 默认门筛不出结果时按分布放宽，并记录原因 |
| 假设检验 | pre-registered hypothesis testing | 5 项，被拒绝的检验写进 Limitations |
| 候选肽 | candidate peptide | 跨剪接连接点、8–11 aa、正常蛋白组未见 |
| HLA 结合预测 | HLA binding prediction | IEDB NetMHCpan 4.1 EL，输出 nM 与 Rank% |
| 抗原呈递 / 免疫原性 | presentation / immunogenicity | 需要质谱与功能实验，平台不做承诺 |
| 方法学留痕 | methods trail | 阈值、放宽理由、版本、跳过步骤全部进正文 |
