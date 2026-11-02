# EpitopeRank

**AI-driven Alternative Splicing Analysis Agent Platform**

[简体中文](README.md) ｜ [繁體中文](README.zh-TW.md) ｜ **English**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

EpitopeRank is rebuilt on top of the multi-agent architecture from the open-source project [BioGAIP](https://github.com/zhangjy859/BioGAIP), fused with a splicing-domain data layer (the production-grade event-standardization contract from SplicingNexus v2) to form an **AI agent platform for downstream alternative-splicing analysis**.

Natural language drives the analysis → automatically generates the analysis workflow → automatically runs statistics → automatically interprets the biology → automatically produces a research report.

> This document is the full Markdown edition of the *EpitopeRank Capability Manual v0.1.0*. For the styled online edition see
> [Capability Manual HTML](docs/manual/EpitopeRank_Capability_Manual_v0.1.0.html) ·
> [PDF](docs/manual/EpitopeRank_Capability_Manual_v0.1.0.pdf).

---

## Quick Start

```bash
# 1. Install (Python >= 3.10)
pip install -r requirements.txt

# 2. Run a full analysis (no LLM key required; the autonomous core decides from the data itself)
python run.py analyze --input <quantified-event-table dir> --query "analyze RNA splicing changes"
# Report: runtime/projects/<PID>/report.html

# 3. Multi-turn follow-up / continue
python run.py followup --project-id <PID> --query "zoom into TP53"

# 4. (Optional) Plug in an LLM for enhancement
export MODEL_API_BASE_URL="https://api.deepseek.com"
export MODEL_API_KEY="sk-..."
export MODEL_NAME="deepseek-flash"

# 5. UI
python run.py serve --api --port 8800   # FastAPI
python run.py serve --ui  --port 8501   # Streamlit dashboard
```

### Deployment

| Form | Command |
|---|---|
| 🐳 Docker | `docker compose up -d` (API 8800 / UI 8501) |
| 💻 Windows EXE | `pyinstaller packaging/EpitopeRank.spec` |
| 🔧 Source | `python run.py serve --api --port 8800` |

### Demos & Docs

| Material | Content |
|---|---|
| 📘 [Capability Manual HTML](docs/manual/EpitopeRank_Capability_Manual_v0.1.0.html) · [PDF](docs/manual/EpitopeRank_Capability_Manual_v0.1.0.pdf) · [Markdown](docs/manual/EpitopeRank_Capability_Manual_v0.1.0.md) | v0.1.0: 15 feature modules, 11 planned items, 3 appendices |
| 🎬 [Splice-derived neoantigen candidates · 1:00](media/videos/splice-neoantigen-peptides.bilingual.mp4) | Events → translatable peptides → HLA binding prediction → 132 candidate peptides (bilingual subtitle tracks) |
| 🎬 [End-to-end analysis pipeline · 1:47](media/videos/pipeline-overview.bilingual.mp4) | Ingestion check → six-Agent pipeline → volcano plot / PSI heatmap (bilingual subtitle tracks) |
| 🗒 [Bilingual walkthrough](docs/WALKTHROUGH.md) | Line-by-line Chinese–English script, usable as voiceover; with subtitle regeneration commands |

[![Splice-derived neoantigen candidates](media/posters/splice-neoantigen-peptides.jpg)](media/videos/splice-neoantigen-peptides.bilingual.mp4)
[![End-to-end analysis pipeline](media/posters/pipeline-overview.jpg)](media/videos/pipeline-overview.bilingual.mp4)

> Both screen recordings are **silent captures**; narration is provided as subtitles. The `*.bilingual.mp4` files contain switchable Chinese / English subtitle tracks.

---

# EpitopeRank Capability Manual v0.1.0

**Version**: v0.1.0 (compiled from the 2026-10-29 repository code, `config/*.yaml`, `docs/`, and supporting documentation)
**Audience**: analysts (what it can do), developers (where to change things), reviewers (where the boundaries are)
**Status legend**: ✅ live & usable ｜ 🟡 partial / experimental ｜ 🔵 in development (spec defined, code not landed) ｜ ⚪ planned (roadmap only)

---

## 0. At a Glance

EpitopeRank is an **AI analysis agent platform for "already-quantified alternative-splicing results"**. It does not take FASTQ and does not do alignment; it ingests quantified event tables from rMATS / SUPPA2 / MAJIQ / LeafCutter / BGI RNAref, then runs an agent core that **decides for itself, challenges itself, calls external knowledge, and writes the report**, producing interpretable, reproducible, publishable analysis results.

```
quantified splicing event table  →  smart ingestion & standardization  →  autonomous agent (observe→decide→act→verify→reflect)
                                              ↓
                 statistics / ranking / figures / external knowledge / hypothesis tests / literature / lab experience
                                              ↓
                                   HTML+PDF research report / staged neoantigen workflow
```

Four design red lines (run through every feature):

1. It must run to completion without a model key (rule-based decisions + offline fallback — not a replay).
2. Never guess a sequence from coordinates; never describe single-sample descriptive PSI as "tumor-specific."
3. MHC binding prediction ≠ antigen presentation ≠ immunogenicity.
4. Every degradation, threshold relaxation, or skip must be written into the report's Methods and Limitations.

---

## 1. Module Overview

| # | Module | One-line purpose | Status | Main entry |
|---|---|---|---|---|
| M1 | Smart data ingestion | Reads headers, formats, groups; turns heterogeneous tables into a standard event table | ✅ | Web "Data ingestion" / `POST /api/ingest/*` |
| M2 | Splicing-event parsing & standardization | Four tool outputs → unified `AS_event_master` contract | ✅ | `epitoperank/splicing/parsers/` |
| M3 | Statistics & quality gating | Chi-square + BH FDR, threshold filtering, composite-score ranking | ✅ | Agent actions / `analysis/statistics.py` |
| M4 | Visualization figures | 6 standard + 7 on-demand plots, PNG 300dpi + SVG | ✅ | Web "Visualization" / `analysis/*` |
| M5 | Autonomous agent core | OODA loop, budgets, adaptive thresholds, cross-run experience | ✅ (default) | `run.py analyze` / `agent/*` |
| M6 | Self-scrutiny (hypothesis tests) | 5 pre-registered tests challenge the result before interpretation | ✅ | `agent/hypothesis.py` |
| M7 | External-knowledge skills | MyGene / PubMed / Enrichr / splice interpretation wired into the loop | ✅ (needs network) | `skills/*` + `skills_bridge` |
| M8 | Literature RAG & lab knowledge base | Evidence retrieval, cross-project recurrent-gene sedimentation | ✅ | `knowledge/*`, `memory/` |
| M9 | Scripted multi-agent | BioPlanner→BioAnalyst→BioInterpreter fixed pipeline | ✅ (compat) | `--agent-mode scripted` |
| M10 | LLM enhancement layer | 8 "writing & understanding" enhancements; auto-degrades without a key | ✅ (needs key) | `llm/enrich.py` |
| M11 | Report generation | Self-contained HTML + PDF, six-section scientific report | ✅ | Web "Report" / `report/generator.py` |
| M12 | MCP integration & AI assistant | Built-in splicing-tool server + natural-language→tool routing | 🟡 | Web "AI assistant" / `/api/mcp/*` |
| M13 | Splice-derived neoantigen workflow | 7 stages with per-stage confirmation; events→peptides→HLA prediction→six-section report | 🟡 | Web "Splice neoantigen" |
| M14 | Multi-form delivery | Web / desktop EXE / Docker / CLI / API | ✅ | `run.py serve`, `dist/` |
| M15 | Observability & reproducibility | End-to-end logging, SQLite memory, input fingerprint | ✅ | `observability.py`, `runtime/` |

---

## 2. Feature Modules in Detail

Each module follows: core purpose → usage → input/output → applicable scenarios.

### M1 Smart Data Ingestion (heterogeneous tables → standard event table)

**Core purpose**
Does not require the user to pre-format data into one shape. The system scans a directory (including subdirectories), identifies headers and delimiters, decides "this is a splicing event table / expression matrix / transcript quantification / metadata," then ingests accordingly.

**Usage**
1. On the Web "AI pipeline" page, upload a file or directory → auto-preview (reads only headers and up to three sample rows; does not scan the full table).
2. For tables with unseen column names, the configured model receives column names + samples and proposes a **mapping suggestion**; the suggestion must pass a "column really exists" check and be confirmed by the user before writing.
3. BGI RNAref single-sample reports (`OC_001/OC_001.SE.xls`, etc.) are recognized first, then the user **manually assigns a biological group to each sample**; the system merges them into `standardized/AS_event_master.tsv` + `sample_metadata.tsv`.
4. Or call the API directly: `POST /api/ingest/preview` → `POST /api/ingest/groups` → `POST /api/ingest/apply`.

**Input / output**

| Item | Content |
|---|---|
| Input | `.csv/.tsv/.txt/.tab`, tab-delimited `.xls`, real Excel `.xls/.xlsx/.xlsm`, `.gz` of the corresponding text tables |
| Output | `standardized/AS_event_master.tsv`, `sample_metadata.tsv`, an ingestion report (role and warnings per file) |
| Rejected | Expression matrices (FPKM/TPM/read_count) → prompt "please choose a splicing-event result instead"; transcript quantification (Bambu, etc.) → recognized but not entered into the event pipeline |

**Applicable scenarios**
- You have BGI/Novogene single-sample splicing reports with only descriptive PSI and no p-value.
- You have historical results from mixed tools and need to unify before analysis.
- You are unsure whether a file is an event table or an expression matrix.

**Boundaries (must know)**
- Single-sample reports have no between-group test; output `p_value`/`FDR` **stay blank** — you cannot claim significant differential splicing from them.
- Grouping is always confirmed by a human; the model never guesses groups.
- When only a p-value is present without FDR, the generic ingester can only run BH on the **current complete event table**; if a public file is only a significant subset, you must supply the FDR from the original complete result.

---

### M2 Splicing-event Parsing & Standardization

**Core purpose**
Folds different tool outputs into one event contract (`event_id / gene_id / event_type / PSI / ΔPSI / p / FDR` + quality columns); all downstream statistics, ranking, and reports build on this layer.

**Usage**
Auto-detected, no need to specify a parser manually (just put the right file names in the directory):

| Input | Notes |
|---|---|
| `SE.MATS.JC.txt` etc., rMATS 5 types + `sample_metadata.tsv` | Includes 0-based→1-based coordinate conversion, per-sample PSI expansion |
| SUPPA2 `*.psi.tsv` | ΔPSI from mean difference or an external file |
| MAJIQ TSV (with `dPSI` / `P(dPSI)`) | Auto-mapped |
| LeafCutter `*_cluster_significance.txt` | Auto-mapped |
| `AS_event_master.tsv` | Read directly (already standard) |

**Input / output**
- Input: any of the above event tables + optional `sample_metadata.tsv` (`sample_id, group, condition, tissue, batch`)
- Output: an in-memory `Dataset` (events / samples / validation) + a persisted standard table + validation warnings

**Applicable scenarios**
rMATS and SUPPA2 are mixed within one project; you want to reuse the same downstream after switching tools; you need to align contracts before cross-project comparison.

---

### M3 Statistics & Quality Gating

**Core purpose**
Determines "which events really changed" and ranks candidates by evidence strength.

**Usage**
All automatic by default; thresholds can be changed via CLI/config (`config/config.yaml → analysis`):

| Parameter | Default | Meaning |
|---|---|---|
| `fdr_threshold` | 0.05 | Significance gate |
| `delta_psi_threshold` | 0.10 | Effect-size gate |
| `min_support_reads` | 10 | Minimum junction support reads |
| `min_valid_samples` | 2 | Minimum valid samples per group |
| `top_candidates` | 20 | Number of candidates kept |
| `enrichment_alpha` | 0.05 | Enrichment-term FDR |

**Input / output**
- Input: standardized event table (M2 output)
- Output: significant-event set, candidate ranking table, enrichment results (GO/KEGG/Reactome/MSigDB), per-step pass/drop counts
- Method: chi-square test + BH FDR; composite score = 0.4×significance + 0.3×effect + 0.2×biology + 0.1×literature

**Applicable scenarios**
Standard two-group comparison (tumor vs normal, treated vs control); you need a "Methods-section-ready" record of thresholds and exclusion reasons.

---

### M4 Visualization Figures

**Core purpose**
Produces figures that can go straight into a submission or report, not debug plots for developers.

**Usage**
- 6 standard plots are auto-generated with each analysis, under `runtime/projects/<id>/figures/`: `volcano`, `event_type_counts`, `psi_heatmap`, `psi_distribution`, `candidate_ranking`, `enrichment`.
- 7 on-demand plots are triggered from the Web "Visualization" page: ΔPSI waterfall, ΔPSI ECDF, FDR scree, event-significance scatter, score breakdown, sample composition, event-structure schematic.
- Fetch a figure: `GET /api/figure/{project_id}/{figure_name}`.

**Input / output**
Input is persisted project state (no need to rerun analysis); output is PNG (300 dpi) + SVG; when data is missing, an annotated placeholder is produced instead of a blank error.

**Applicable scenarios**
Group meeting, paper Figures 1–3, reviewer-requested supplementary figures.

---

### M5 Autonomous Agent Core (default mode)

**Core purpose**
Lets the workflow follow the data rather than a hardcoded script.

```
Observe(Profile) → Verify → Decide → Act → Trace
      ↑                                       │
      └──────── goal not met → reflect/replan (within budget) ┘
```

**Usage**

```bash
# Default agentic: the agent looks at the data and sets its own thresholds
python run.py analyze --input examples/demo_rmats --query "analyze RNA splicing changes"

# Run under human supervision: network calls / threshold relaxation / accepting blockers will ask first
python run.py analyze --input data/ --query "..." --autonomy assisted

# Multi-turn follow-up: continue on an existing project without rerunning the whole pipeline
python run.py followup --project-id <PID> --query "zoom into TP53"
python run.py followup --project-id <PID> --query "SE events only"
```

**Core mechanisms & tunables** (`config.yaml → agent`)

| Mechanism | Description | Config |
|---|---|---|
| Goal acceptance | Uses a verifiable acceptance criterion instead of a "termination token" | `state.py` |
| Data profile | Scale, FDR coverage, missingness, support reads, group balance | `profile.py` |
| Adaptive thresholds | When the default gate yields 0 events, relax to where results appear and record **why it changed** | `adaptive_thresholds: true`, `target_significant: 100` |
| Result check + remedy | Produces Issue(code, severity, suggestion) → adjust threshold / retry / degrade-accept | `reflection: true` |
| Hard budget | Step / time / error triple cap; never loops forever | `max_steps: 20`, `max_seconds: 900`, `max_errors: 3` |
| Cross-run experience | What threshold worked last time on similar data | `episodic: true` |
| Multi-turn session | State snapshot save/load + rule-based intent parsing | `session.py` |
| Human-in-the-loop | Three high-risk decisions ask first; `auto` mode auto-approves but logs | `autonomy`, `interactive.py` |

**Built-in actions (19 total)**
- Data: `profile_dataset`, `assess_quality`
- Analysis: `summarize_dataset`, `filter_significant_events`, `rank_candidates`, `run_enrichment`, `generate_figures`, `deep_dive_gene`, `adapt_thresholds`
- Self-scrutiny: `test_hypothesis`
- External knowledge: `annotate_genes`, `annotate_genes_enhanced`, `enrich_pathways`, `enrich_pathways_bioservices`, `search_literature`, `interpret_splice_event`
- Delivery: `collect_literature_evidence`, `interpret_candidates`, `generate_report`
- Experience: `consult_knowledge`, `persist_knowledge`

**Applicable scenarios**
Data does not follow a "textbook distribution" (too few events, missing FDR, unbalanced groups); you need the report to honestly explain "why we ended up using FDR<0.1"; unattended batch runs.

---

### M6 Self-Scrutiny: Pre-registered Hypothesis Tests

**Core purpose**
Before drawing conclusions, systematically challenge the results; rejected tests become limitations in the report.

**Usage**
With `hypothesis_testing: true` it runs automatically before interpretation; CLI/API can also trigger it standalone.

| Test | H0 | Method |
|---|---|---|
| `dpsi_shift` | ΔPSI distribution does not deviate from 0 | Wilcoxon signed-rank (degrades to t-test for small samples) |
| `direction_balance` | Up/down-regulated events are balanced | Binomial test |
| `event_type_bias` | Significant-event type composition = background composition | Chi-square goodness-of-fit |
| `coverage_confound` | Effect size is independent of sequencing depth | Spearman rank correlation |
| `gene_recurrence` | Hits are not concentrated in a few genes | Permutation test (1000×) |

**Input / output**
Input is the current candidate and event set; output is per-test p-value + BH correction + conclusion, written into report section 3.3 and Limitations. For example, on the demo data `coverage_confound` is rejected, so the report explicitly states "large-ΔPSI events are confounded by sequencing depth."

**Applicable scenarios**
A reviewer asks "how did you rule out sequencing-depth confounding"; internal QC requires "every conclusion has a corresponding falsification attempt."

---

### M7 External-Knowledge Skills (4) & Open-source Backends

**Core purpose**
Turns "look up what this gene is, whether there is literature, what pathways are enriched, how to interpret this splicing event" into actions the agent can call autonomously.

**Usage**
- Agent auto-calls (`agent.skills.enabled: true`, default on).
- Standalone call: `GET /api/skills/list` for the schema, `POST /api/skills/execute` to run.
- Disable: `--skills off` or `EPITOPERANK_ENABLE_SKILLS=0`.

| Skill | Backend | Purpose |
|---|---|---|
| `gene_annotation` | MyGene.info | Gene symbol / Ensembl / UniProt annotation, batch-supported |
| `literature_search` | PubMed | Retrieve and summarize literature by gene/event |
| `pathway_enrichment` | Enrichr (GSEApy) | GO / KEGG / Reactome / MSigDB over-representation |
| `splice_interpretation` | Local rules + model | Explain the biological consequence of a specific splicing event |

**Bridge-layer guarantees**: sync/async isolation, per-call timeout (default 10 s), **per-run call budget** (default 4), same-argument caching; failure degrades gracefully — a network outage will not crash the analysis, only log a limitation.

**Input / output**
Input is a gene list / event / term set; output is structured results + data source and version. Availability is exposed via `capabilities()` to the API and report (`gseapy` / `mygene` / `scipy` / `httpx` installed? which version?).

**Applicable scenarios**
A candidate gene needs a one-sentence functional annotation; the report needs a "literature support" level; an offline environment needs to confirm which capabilities are currently unavailable.

---

### M8 Literature RAG & Lab Knowledge Base

**Core purpose**
Two memory layers: one for "literature evidence," one for "genes that recur across this lab's history."

**Usage**
- Literature: `knowledge/rag.py` (built-in knowledge base + PubMed + SQLite literature store, NFS-safe); retrieval results are injected as interpretation evidence.
- Lab knowledge: `consult_knowledge` queries the store before interpretation (default requires ≥2 historical-project hits); `persist_knowledge` writes the top candidates back to `lab_knowledge.sqlite3` after a successful run.
- Report rendering: section 5.5 "External-knowledge findings" and 5.6 "Lab-level recurrence."

**Input / output**
Input is candidate genes, query terms, project history; output is sourced literature entries and a cross-project recurrent-gene table.

**Applicable scenarios**
A lab runs consecutive tumor cohorts and wants "this is the third time we've seen this gene" to surface automatically; you need traceable evidence rather than the model speaking from memory.

---

### M9 Scripted Multi-Agent (compatibility mode)

**Core purpose**
Retains the classic BioGAIP three-role pipeline for **regression comparison** and teaching: on the same data, agentic vs scripted should produce explainable differences.

**Usage**
```bash
python run.py analyze --input examples/demo_rmats --query "analyze RNA splicing changes" --agent-mode scripted
```
or set `agent.mode: scripted` in `config.yaml`, or env var `EPITOPERANK_AGENT_MODE`.

**Structure**
```
BioPlanner (plans only, does not compute) → BioAnalyst (summarize→filter→rank→enrich→figures)
                            → BioInterpreter (literature→interpret→report, terminates on EPITOPERANK_DONE)
```
Roles and tools are declared in `config/agent_config.yaml` / `tool_config.yaml`; `max_turns: 40`; agents collaborate via structured messages; all operations are written to SQLite Analysis Memory.

**Input / output**
Input as in M5; output as in M11, but with fixed thresholds (FDR<0.05 and |ΔPSI|>0.1), no adaptation.

**Applicable scenarios**
Behavior comparison after version upgrades; deterministic scenarios requiring "identical results every run"; explaining the platform's three-stage division of responsibility to newcomers.

---

### M10 LLM Enhancement Layer (8 items)

**Core purpose**
The model only does "understanding and expression," never "computing the numbers." 8 features, each independently togglable:

| Feature | Role |
|---|---|
| `understand` | Natural-language analysis-goal understanding + parameter suggestions (`POST /api/understand`) |
| `plan` | Refine the Planner's goal and limitations wording |
| `interpret` | Narrative interpretation of results (lead-in / paragraphs / bullets) |
| `annotate` | Biological annotation of candidate genes |
| `literature` | Literature-evidence summary |
| `limitations` | Supplement study-design-level limitations |
| `hypotheses` | Research hypotheses + validation-experiment suggestions |
| `critique` | Auto-review of generated narrative (a separate review model can be set via `MODEL_CRITIC_NAME`) |

**Usage**
Three config channels, any one works: env vars / a `.env` in the project root / the UI "AI assistant → model config."

```bash
export MODEL_API_BASE_URL="https://api.deepseek.com"
export MODEL_API_KEY="sk-..."
export MODEL_NAME="deepseek-flash"
export MODEL_THINKING=auto      # reasoning off for tool calls, on for report interpretation
```

**Key parameters**: per-call timeout 120 s, max 16 calls per run, max 8 gene annotations, output language `auto` (follows the query language; can force zh/en), `provider: auto` (auto-detects deepseek/openai/moonshot/dashscope), keys in URLs are auto-redacted.

**Input / output**
Input is structured analysis results + the user query; output is text paragraphs / JSON suggestions, **which must pass local validation** (suggested column names, parameters, and genes must really exist).

**Applicable scenarios**
You need a paragraph of plain-language summary for clinical or biology colleagues; you want the model to help write Limitations; you want to run on a key-less server but enhance locally where a key is available.

**Degradation behavior**
No key / endpoint unreachable → `fallback.py` offline deterministic strategy takes over; the report is still generated, just without narrative polish, and the status explicitly marks "model not used."

---

### M11 Report Generation

**Core purpose**
When a run finishes, you immediately have something you can send out.

**Usage**
Auto-generated; or download from the Web "Report" page; or `GET /api/report/{project_id}?format=html|pdf`.

**Output structure**
```
runtime/projects/<project_id>/
├── figures/        # PNG 300dpi + SVG
├── report.html     # self-contained (images base64-embedded, single-file shareable)
└── report.pdf      # reportlab rendering
```
Sections: Summary / Methods / Results (incl. 3.3 statistical hypothesis tests) / Figures / Biological Interpretation (incl. 5.5 external knowledge, 5.6 lab recurrence) / Limitations / References.

**Highlights**
Methods provenance: thresholds, relaxation reasons, software versions, skipped steps, and rejected hypothesis tests all go into the body text, not an appendix.

**Applicable scenarios**
Group meeting, submission supplement, interim deliverable to collaborators, internal QC archiving.

---

### M12 MCP Integration & AI Assistant

**Core purpose**
Exposes platform capabilities **as standard tools** and lets natural language drive them directly.

**Usage**
- Built-in server `epitoperank-builtin` (`http://127.0.0.1:9100`, available with the process, no config), provides 5 tools: `list_projects`, `project_summary`, `search_events`, `explain_event_type`, `compute_delta_psi`.
- External servers: write `~/.epitoperank/mcp/servers.json`; supports `stdio` / `sse` / `http` transports, both the official MCP SDK and a simple `/tools` adapter protocol.
- View and call: `GET /api/mcp/servers` (with connection status and tool schemas), `POST /api/mcp/call`, `POST /api/mcp/agent` (natural language → pick tool → local validation → execute).
- The Web "AI assistant" page accepts natural-language commands such as "check which significant splicing events CD44 has."

**Input / output**
Input is a natural-language question + optional `project_id`; output is the tool-call result. The model only proposes `{server, tool, arguments}`; **validation and execution stay local**; without a model, a deterministic router falls back on the same contract.

**Applicable scenarios**
Let an IDE coding assistant query project results directly; plug the platform into an existing lab agent workflow; give non-technical colleagues a "ask one sentence, get the number" entry point.

**Status note**
Tool routing and the execution chain work; but the dual-pane chat panel on the "AI pipeline" page (v4 description) is still a **front-end demo state** — messages are template-rendered and not connected to a real multi-turn backend. This is the dividing line between M12 and planned item P7.

---

### M13 Splice-derived Neoantigen Workflow (staged)

**Core purpose**
Goes one layer below "splicing events" down to "candidate peptides + HLA binding prediction," and **every step requires human confirmation** — no running through.

**Usage**
Web "Splice neoantigen" → pick project → form → advance stage by stage with confirmation; progress is saved to the local run directory and resumes on restart; if project input changes, a fingerprint mismatch forces a re-audit.

| Stage | What it does | Must provide | Reject/stop conditions |
|---|---|---|---|
| 0 Audit | Declare how far this data can support | `normal_design`, `genome_build`, `annotation_version`, `coordinate_system`, `input_kind`, `hla_source`, `hla_confidence` | Missing key declarations → no further stages |
| 1 Events | Use upstream-quantified events; do not rediscover | Explicit "input is a quantified event table" confirmation + event-table completeness statement | Raw reads/BAM unsupported; empty or duplicate event_id → reject |
| 2 Event filter | Coordinate-level filtering | Support-read threshold, min sample count, and confirmation of whether the read count is junction support | No events survive → stop and log |
| 3 ORF | Read in an **upstream-reconstructed** ORF table | Four CDS columns + `orf_source`, `frame_status`, `premature_stop`, optional `last_junction_nt` | Missing fields → reject; does not reconstruct ORF itself |
| 4 Peptide-level normal filter | Paired-normal / GTEx / whole-proteome three-layer exact match + GTEx junction + normal-tissue expression | Three-layer FASTA, event-to-GTEx junction table (same genome build), normal-expression table | Skipping any layer requires explicitly acknowledging the limitation, else error |
| 5 Expression & recurrence | Whether there is a transcript, whether multi-patient recurrence | `event_id, expression, expression_unit`, optional `recurrence_count/total` | Recurrence is a ranking weight only, not a hard gate |
| 6 HLA prediction | IEDB **NetMHCpan 4.1 EL** | Real HLA-I alleles (e.g. `HLA-A*02:01`) + source + confidence | Combinations >200 → reject; prediction failures recorded per entry in manifest |
| 7 Output | Fixed six-section report | — | — |

**Input / output**
- Input: all files inside the project data directory (out-of-bound paths rejected outright): CDS table / ORF table / FASTA / junction table / expression table
- Output: `splice_peptides.tsv`, `mhc_i_predictions.tsv`, `neoantigen_manifest.json` (with skip reasons and prediction errors), six-section structured results

**Two independent capabilities**
- Standalone peptide generation: `neoantigen.run()` takes a CDS comparison table directly (`event_id, reference_cds, altered_cds, junction_nt`), translates to the first stop codon, retains 8–11 aa peptides spanning the junction, excludes peptides already present in the normal ORF.
- moPepGen adapter: `scripts/mopepgen_docker.py` calls the official 1.4.6 container, producing variant-event GVF and variant-peptide FASTA, and saves the command, input SHA-256, image digest, and log. **It does not produce the CDS comparison table needed by stage 3, nor is it the HLA prediction.**

**Applicable scenarios**
You have paired normal and HLA typing and want a quick "worth experimentally validating" candidate list; you need to deliver "honest half-way results" under methodological review.

**Boundaries (hard-coded)**
No sequence guessing; no prediction-as-presentation; no single-sample-as-tumor-specific; no composite-score ranking (explicitly declares "no evidence-supported composite score is defined").

---

### M14 Multi-form Delivery

**Core purpose**
One kernel, four usages: run for yourself, share with colleagues, deploy on a server, call from other agents.

| Form | Entry | Fit |
|---|---|---|
| CLI | `run.py analyze / followup / projects / status / serve` | Batch, scripting, reproducibility |
| Web SPA | `python run.py serve --ui` or `python serve_ui.py`; 9 pages: dashboard / AI pipeline / event browser / visualization / gene browser / report / splice neoantigen / AI assistant | Daily analysis main entry |
| Desktop window | `desktop_ui.py` (pywebview wrapping a local service); `dist/EpitopeRank.exe` no Python needed | For colleagues without an environment |
| API | FastAPI (default 8800): analysis, ingestion, status, report, figures, skills, MCP, neoantigen | Integration & automation |
| Container | `docker compose up -d` (API 8800 + UI 8501) | Team/server deployment |

**Streamlit dashboard** has a separate entry (`serve --ui`, default 8501): "upload + goal → results (candidates/figures/enrichment) → download report."

**Applicable scenarios**
Local exploration via desktop; team sharing via Docker; pipeline integration via API/CLI; no-Python environments via EXE.

---

### M15 Observability & Reproducibility

**Core purpose**
Keeps "where did this conclusion come from" always traceable.

**Mechanisms**
- Each run records: input fingerprint, analysis plan, generated code, results, interpretation, workflow log (SQLite Analysis Memory).
- Logging: `observability.py` unified structured output, with level/source/timestamp.
- The state DB defaults to local disk (`/var/tmp/epitoperank`; on Windows, the system temp dir), because NFS does not support SQLite file locks — the program auto-detects and migrates.
- Decision trace: every step's "what was observed → why this decision" goes into the report Methods and the workflow log.

**Applicable scenarios**
Reproducing a figure six months later; a reviewer questions a threshold; handoff to the next student.

---

## 3. Available Features List (ordered by "ready to use now")

| Capability | Command / entry | Dependency | Status |
|---|---|---|---|
| One-click full analysis (offline) | `run.py analyze --input ... --query ...` | Python 3.10+ | ✅ |
| Adaptive thresholds & self-correction | on by default | — | ✅ |
| Multi-turn follow-up | `run.py followup --project-id ... --query ...` | existing project | ✅ |
| 5 hypothesis tests | on by default | scipy | ✅ |
| 4 external-knowledge skills | on by default | network + `gseapy`/`mygene`/`httpx` | ✅ (auto-degrade if missing) |
| 8 LLM enhancements | configure key in `.env` | model endpoint | ✅ (degrade without key) |
| HTML + PDF report | auto / `GET /api/report/{pid}` | reportlab | ✅ |
| 13 figures | auto + on-demand from Visualization page | matplotlib | ✅ |
| 6 input formats auto-detected | upload directory | — | ✅ |
| BGI RNAref single-sample ingestion | ingestion wizard | manual grouping | ✅ |
| MCP built-in 5 tools | `GET /api/mcp/servers` | — | ✅ |
| External MCP server ingestion | `~/.epitoperank/mcp/servers.json` | `mcp` SDK | ✅ |
| Natural-language → MCP tool routing | `/api/mcp/agent` | model (optional) | 🟡 (deterministic router without model) |
| Neoantigen 7-stage workflow | Web neoantigen page | user-supplied ORF/FASTA/HLA | 🟡 (experimental, per-stage confirm) |
| Standalone peptide generation | `neoantigen.run()` | CDS comparison table | 🟡 |
| moPepGen container adapter | `scripts/mopepgen_docker.py` | Docker + image | 🟡 (exploratory, not wired into ORF stage) |
| Desktop EXE | `dist/EpitopeRank.exe` | — | ✅ |
| Docker deployment | `docker compose up -d` | Docker | ✅ |
| Human-in-the-loop confirmation | `--autonomy assisted` | — | ✅ |

---

## 4. Planned / In-development Features

> Status criteria: **🔵 in development** = spec and interface contract are defined in the repo (docs/config/fields) but core implementation is not landed; **⚪ planned** = appears only in the roadmap or config comments, no code trace.

### P1 Automatic ORF Reconstruction (automation of neoantigen stage 3)

| Item | Content |
|---|---|
| **Expected goal** | Given an event table + reference genome FASTA + GTF/CDS annotation, auto-assemble novel transcripts by event type (SE/RI/A3SS/A5SS/MXE), judge in-frame / frameshift, translate to the first stop codon, compute `junction_nt`, and produce NMD candidates by a 50 nt distance rule |
| **Concrete problem solved** | Stage 3 currently requires the user to supply a "reconstructed ORF table," the most labor-intensive and error-prone step in the chain; without it, neoantigen analysis breaks at step 3 for most users |
| **Current status** | 🔵 in development: `docs/prompts/splice-neoantigen-pipeline.md` already fixes the stage-3 methodology and field contract (`orf_source` / `frame_status` / `premature_stop` / `last_junction_nt`); the code explicitly states "automatic ORF reconstruction not yet implemented" |
| **Expected usage** | `Neoantigen page → stage 3 → pick genome FASTA + GTF → one-click reconstruct → auto-produce four-column CDS table + NMD flags, human spot-check then confirm to stage 4` |
| **Dependencies/risks** | Transcript annotation version must match event coordinates; different event types have different assembly rules, and misassembly silently produces false peptides — so a per-event traceable assembly log is mandatory |

### P2 Raw-data Online Processing (Phase 2: FASTQ → alignment → splicing detection)

| Item | Content |
|---|---|
| **Expected goal** | Complete FASTQ QC → STAR/HISAT2 alignment → rMATS/SUPPA2 online → auto-enter the existing analysis chain, all on-platform |
| **Concrete problem solved** | Phase 1 only eats "already-quantified event tables"; users must run a full bioinformatics pipeline on the command line before they can use the platform, which blocks non-bioinformatics users |
| **Current status** | ⚪ planned (README roadmap Phase 2; no alignment/quantification code in the repo) |
| **Expected usage** | `Upload 6 FASTQs + sample_metadata.tsv → pick GRCh38/GENCODE → platform queues alignment and rMATS → auto-generates SE.MATS.JC → straight into agent analysis` |
| **Dependencies/risks** | Heavy compute and a task queue needed; reference-genome version management; run time rises from minutes to hours |

### P3 Dedicated QC Agent

| Item | Content |
|---|---|
| **Expected goal** | An independent QC role that, before analysis, systematically checks sequencing depth, alignment rate, sample correlation, and batch effects, and gives a "can we continue" verdict |
| **Concrete problem solved** | QC is now scattered across `profile_dataset` / `assess_quality` and the hypothesis tests, with no dedicated "say no" role; bad data can still be analyzed all the way through |
| **Current status** | ⚪ planned (`config/agent_config.yaml` comment explicitly says "future extensions (e.g. a dedicated QC agent in Phase 2)") |
| **Expected usage** | `Auto-insert QC stage before run → detect sample 3 correlation <0.7 with others → report recommends dropping it with evidence → user confirms to continue or stop` |

### P4 Transcript-quantification Independent Pipeline (long-read / Bambu, etc.)

| Item | Content |
|---|---|
| **Expected goal** | Treat per-transcript count/CPM/TPM matrices as an independent data type (differential transcript usage, isoform switch), not force them into the event-PSI pipeline |
| **Concrete problem solved** | Long-read data can currently be "recognized" but is explicitly "not entered into this pipeline," leaving users with no path after recognition |
| **Current status** | ⚪ planned (README states "transcript-quantification analysis is an independent data type, not yet wired into this pipeline") |
| **Expected usage** | `Upload a Bambu transcript count matrix → choose "transcript quantification analysis" → output isoform-usage differential + isoform-switch plot` |

### P5 Single-cell RNA-seq & Multi-omics (Phase 3)

| Item | Content |
|---|---|
| **Expected goal** | Single-cell-level splicing analysis (cell-type-specific PSI), joint analysis with transcriptome/proteome/methylation |
| **Concrete problem solved** | All current statistical assumptions are built on bulk group comparison; cannot answer "which cell subpopulation underwent this splicing change" |
| **Current status** | ⚪ planned (roadmap Phase 3) |
| **Expected usage** | `Upload scRNA-seq splice junction counts → cluster by cell type → output subtype-specific splicing events and marker-gene linkage` |

### P6 Autonomous Bioinformatics Researcher (Phase 4)

| Item | Content |
|---|---|
| **Expected goal** | Evolve from "given data and a goal" to "given a scientific question," autonomously proposing hypotheses, designing analyses, iteratively validating, and writing submittable manuscripts |
| **Concrete problem solved** | The agent's autonomy is currently limited to "making decisions within a fixed pipeline"; scientific-question formulation still depends entirely on humans |
| **Current status** | ⚪ planned (roadmap Phase 4, long-term) |
| **Expected usage** | `Input "why is this tumor cohort insensitive to drug X" → autonomously generate splicing-related hypotheses → design and execute validation analyses → output an evidence-chained research report` |

### P7 AI Assistant Full Multi-turn Dialogue

| Item | Content |
|---|---|
| **Expected goal** | Connect the "AI pipeline" page's dual-pane chat panel to a real backend: real LLM replies, WebSocket streaming, multi-turn context memory, agent-collaboration visualization |
| **Concrete problem solved** | The panel's messages are currently front-end template-rendered; asking "why was this FDR threshold chosen" gets no real answer, while MCP tool routing already works — a "dialogue shell" is missing between them |
| **Current status** | 🟡 partial: `/api/mcp/agent` (natural language→tool→local execution) works, `/api/understand` (goal understanding) works; the panel itself is still demo state |
| **Expected usage** | `In the panel, type "why not FDR 0.01" → the agent reads this run's state and decision trace → answers "0.01 leaves only 2 events, below the acceptance target of 100, so it was relaxed to 0.05 and recorded in Methods"` |
| **Dependencies** | Need to expose `AgentState` and decision trace as queryable session context; a WebSocket channel |

### P8 Neoantigen Candidate Composite Score

| Item | Content |
|---|---|
| **Expected goal** | Define an **evidence-supported** composite score (expression × recurrence × binding rank × event quality) for candidate ranking |
| **Concrete problem solved** | The six-section report currently states explicitly "no evidence-supported composite score is defined; the candidate table is not ranked by composite score," so users must rank it themselves |
| **Current status** | ⚪ planned (declared in `neoantigen_workflow.py` limitations) |
| **Expected usage** | `Stage 7 outputs a candidate table sorted by composite score descending, with each weight contribution shown` |

### P9 Built-in Reference Database & Version Management

| Item | Content |
|---|---|
| **Expected goal** | Built-in/hosted GTEx junction table, UniProt whole proteome, CDS annotations for common genome builds, with version-consistency checks |
| **Concrete problem solved** | Stage 4 currently requires users to supply three-layer FASTA and a junction table, and "genome version must match" is entirely human-checked — the second high barrier of the neoantigen pipeline |
| **Current status** | ⚪ planned (docs repeatedly stress "file source, coverage, and version must be verified by the user") |
| **Expected usage** | `Stage 4 dropdown: GTEx v8 / UniProt 2024_05 / GRCh38 → system auto-checks event build version and flags mismatches` |

### P10 MHC-II & Immunopeptidome Evidence (mentioned in docs, unscheduled)

| Item | Content |
|---|---|
| **Expected goal** | Support MHC-II prediction models; integrate HLA immunopeptidome mass-spec evidence |
| **Concrete problem solved** | Currently only MHC-I (8–11 aa, NetMHCpan 4.1 EL); CD4+ T-cell-related candidates are entirely missing; and whether a peptide is actually presented cannot be confirmed |
| **Current status** | ⚪ planned (prompt explicitly notes "MHC-II is another model family, do not mix," as a methodology reminder, not a feature promise) |

### P11 Engineering-quality Items (non-functional, but affect usability)

| Item | Current | Target |
|---|---|---|
| Test coverage | 27%, CI gate 20% | Raise the gate gradually; fill in data-processing, agent, UI coverage |
| Doc completeness | `docs/` only has `prompts/`; README-referenced `docs/USAGE.md` is missing | Fill in the operations manual (this file is step one) |
| Logging/security | Structured logging and key redaction exist | Production-grade file rotation, permission model |

---

## 5. Old/New Feature Relationship & Evolution

### 5.1 Evolution Mainline (one diagram)

```
v1 Fixed-script three-agent (BioPlanner→BioAnalyst→BioInterpreter)
        │  Problem: thresholds hardcoded; non-conforming data yields empty results
        ▼
v2 Autonomous OODA core (decision engine + verify + reflect + budget + cross-run experience)
        │  Problem: can decide but cannot doubt itself, nor find external evidence
        ▼
v3 Self-scrutiny + external knowledge + human-in-the-loop (5 hypothesis tests / 4 skills / assisted mode)
        │  Problem: bulk event layer is topped out; users want to go down to peptides and HLA
        ▼
v4 Staged neoantigen workflow (events → ORF → peptides → expression → HLA → six-section report)
        │  Problem: stage 3 depends on manual ORF reconstruction; raw data still processed off-platform
        ▼
v5 (planned) Auto ORF reconstruction + built-in reference DB + FASTQ online pipeline + single-cell/multi-omics
```

### 5.2 Concrete replacement / enhancement relationships

| Old | New | Relationship | Compat strategy |
|---|---|---|---|
| Fixed-threshold filtering | Adaptive thresholds + cross-run experience memory | **Enhance** (old behavior reproducible via `target_significant` and fixed config) | `--agent-mode scripted` fully equivalent to historical behavior, for regression comparison |
| Three-role scripted pipeline | Autonomous OODA core | **Coexist** (former as comparison baseline, latter as default) | `agent.mode` switch; `config/agent_config.yaml` keeps role declarations |
| Single run | Multi-turn follow-up `followup` | **Enhance** (same project state snapshot, no rerun) | New subcommand; old commands unchanged |
| Hand-written HTTP enrichment | GSEApy/Enrichr + MyGene client | **Replace** (auto-falls back to hand-written impl if dep missing) | `capabilities()` exposes the actual backend and version |
| Skills only callable via API | Skills wired into agent loop (with budget/cache/degrade) | **Enhance** (from "tool" to "action") | `--skills off` one-switch revert |
| Only outputs results | Self-scrutinize before interpreting | **Enhance** (rejected tests enter Limitations) | `hypothesis_testing` toggle |
| Neoantigen one-shot script | 7-stage per-stage confirm + resumable state + input fingerprint | **Replace** (experimental script entry remains, but no longer recommended) | `neoantigen.run()` retained as standalone peptide generation |
| moPepGen used directly as result | Explicitly downgraded to "exploratory input," not wired into ORF stage | **Narrow** (capability boundary written into docs and UI prompts) | Output still saves command and hash for traceability |
| v3 single-pane UI | v4 dual-pane (workflow + dialogue + log) | **Enhance** (dialogue panel still demo, see P7) | `git checkout v3-professional-ui` can roll back |
| In-page embedded `web_ui` | Desktop EXE / Docker multi-form | **Expand** (same FastAPI + static UI) | All reuse the same `create_app()` |

### 5.3 Three principles of the evolution

1. **Capability goes deeper; the evidence chain does not relax**: from events to peptides to HLA, each extra step adds a layer of mandatory declaration and limitation, not a layer of "looks more impressive" numbers.
2. **Human-confirmation points move earlier, not away**: what stage-3 automation targets is the manual chore of "reconstructing ORF," not the safety valve of "skipping confirmation"; P1 still requires human spot-checks after landing.
3. **The default path gets stronger; the fallback path is retained**: every new mechanism (adaptive, skills, hypothesis tests, neoantigen) has a switch or an old mode; `scripted` mode is kept long-term as a behavior-equivalent baseline.

### 5.4 The three judgments readers most likely care about

- **Can I use it now?** Yes. Feed it an rMATS result and one command produces a report, no API key needed.
- **Can the neoantigen results be trusted?** You can trust "how far it got," not "it proved immunogenicity." The staged design exists to make that sentence auditable.
- **When can I upload FASTQ?** Roadmap Phase 2, planned; for now, run alignment and quantification upstream.

---

## 6. Capability Boundaries (explicitly not doing)

| Not doing | Reason | Alternative path |
|---|---|---|
| FASTQ QC / alignment / transcript assembly | Phase 1 is positioned as "downstream analysis" | Upstream STAR/HISAT2 + rMATS/SUPPA2; feed the result table to the platform (P2 planned) |
| Guessing CDS / ORF sequence from coordinates | Silently produces false peptides | Provide frame-correct CDS, or wait for P1 auto-reconstruction |
| Re-running BH on a significant subset | Statistically invalid | Provide the complete event table |
| Calling single-sample descriptive PSI tumor-specific | No between-group test | Provide paired normal and biological replicates |
| Back-deriving protein sequence from event ID | Same as above | Explicit input at stage 3 |
| Claiming antigen presentation / immunogenicity / clinical validity | Requires mass-spec and functional experiments | Experimental validation (tetramer / ELISpot / killing) |
| Treating "GTEx undetected" as "absent in normal tissue" | May just be no expression or insufficient depth | Sequence-level filtering + expression evidence |
| Infinite self-retry | Budget triple cap | Stop and write into limitations |

---

## 7. Three Typical Onboarding Paths

**Path A | Have an rMATS result, want a report fast (5 minutes)**
```bash
python run.py analyze --input examples/demo_rmats --query "analyze RNA splicing changes"
# open runtime/projects/<PID>/report.html
```

**Path B | Data is imperfect, want to see how the agent self-rescues**
```bash
python examples/make_hard_cases.py examples
python run.py analyze --input examples/hard_rescuable --query "find differential splicing events"  # relaxes thresholds to recover
python run.py analyze --input examples/hard_empty     --query "find differential splicing events"  # admits no solution and writes the limitation
```

**Path C | Have HLA typing, want to filter candidate peptides**
```
Web → Splice neoantigen → pick project → stage 0 audit (fill all 7 declarations)
    → stages 1/2 events & filter → stage 3 upload upstream ORF table → stage 4 three-layer normal filter
    → stage 5 expression & recurrence → stage 6 enter HLA (e.g. HLA-A*02:01) → stage 7 six-section report
```

---

## Appendix A | API Quick Reference

| Group | Endpoint |
|---|---|
| Health & model | `GET /api/health`, `GET /api/llm/status`, `POST /api/llm/config` |
| Understand | `POST /api/understand` |
| Analysis | `GET /api/projects`, `GET /api/status/{pid}`, `POST /api/analyze` |
| Ingestion | `POST /api/ingest/preview`, `POST /api/ingest/groups`, `POST /api/ingest/apply` |
| Upload | `POST /api/upload`, `POST /api/upload-debug` |
| Report/figures | `GET /api/report/{pid}?format=`, `GET /api/figure/{pid}/{name}` |
| Neoantigen | `GET /api/neoantigen/readiness/{pid}`, `POST /api/neoantigen/audit`, `POST /api/neoantigen/workflow/start|advance`, `GET /api/neoantigen/workflow/{id}`, `POST /api/neoantigen/run`, `POST /api/neoantigen/mopepgen`, `GET /api/neoantigen/file`, `POST /api/neoantigen/reveal` |
| Skills | `GET /api/skills/list`, `POST /api/skills/execute` |
| MCP | `GET /api/mcp/servers?refresh=`, `POST /api/mcp/call`, `POST /api/mcp/agent` |

## Appendix B | Config Quick Reference (`config/config.yaml`)

| Section | Key items | Defaults |
|---|---|---|
| `llm` | `features` (8 items, or all), `insight_timeout_seconds`, `max_calls_per_run`, `max_genes`, `language`, `thinking` | all / 120 / 16 / 8 / auto / auto |
| `analysis` | `fdr_threshold`, `delta_psi_threshold`, `min_support_reads`, `min_valid_samples`, `top_candidates`, `enrichment_alpha` | 0.05 / 0.1 / 10 / 2 / 20 / 0.05 |
| `agent` | `mode`, `max_steps`, `max_seconds`, `max_errors`, `adaptive_thresholds`, `target_significant`, `reflection`, `episodic`, `autonomy`, `hypothesis_testing` | agentic / 20 / 900 / 3 / true / 100 / true / true / auto / true |
| `agent.skills` | `enabled`, `max_calls`, `timeout` | true / 4 / 10 |
| `report` | `formats` | html, pdf |
| `paths` | state DB location (defaults to follow the runtime root) | system temp dir |

## Appendix C | Status Statistics

| Category | Count |
|---|---|
| Live & immediately usable | 20 items |
| Partial / experimental | 5 items (MCP NL routing, neoantigen 7-stage, standalone peptide generation, moPepGen adapter, neoantigen readiness check) |
| In development | 1 item (P1 auto ORF reconstruction) |
| Planned | 8 items (the planned items among P2–P10) |
| Engineering improvements | 3 items (coverage, docs, logging/security) |

---

*This manual is compiled from the repository's current state; for features marked 🟡/🔵/⚪, rely on actual run results — do not treat "spec defined" as "feature available."*
