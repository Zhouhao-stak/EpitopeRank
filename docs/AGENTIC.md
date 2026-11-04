# 智能体化升级：从「一次提示词」到「工具调用循环」

> 适用版本：SpliceGAIP 0.2.x（`splicegaip/agent/copilot.py`）
> 相关模块：`splicegaip/llm/chat.py`、`splicegaip/llm/structured.py`、`splicegaip/agent/copilot.py`

## 1. 之前的问题

原来的「AI 助手」页面只是一个壳：输入问题后返回固定话术；真正的模型调用集中在
`llm/enrich.py` 的 9 个一次性任务（理解意图、解读、假设、批评等）。这带来三个限制：

1. **不可追问**：模型看不到「上一轮工具查到了什么」，只能对一次性事实做改写。
2. **不能取数**：模型无法主动查询某个基因的事件、某个项目的质量、某条通路的富集。
3. **不可核对**：模型输出直接进报告，没有 schema 校验，也没有数字溯源。

## 2. 现在的架构

```
用户问题
   │
   ▼
┌──────────────────────────────────────────────────────────┐
│ Copilot 循环（splicegaip/agent/copilot.py）               │
│                                                          │
│  system prompt + 历史 + 问题                              │
│        │                                                 │
│        ▼                                                 │
│  ChatClient.complete(tools=[...])  ← 原生 function call   │
│        │                                                 │
│        ├─ 有 tool_calls → 校验参数 → 执行工具 → 结果回填   │
│        │        ▲                              │         │
│        └────────┴────────── 继续循环（≤6 步 / ≤24 次）     │
│                                                          │
│  无 tool_calls → 最终回答                                 │
└──────────────────────────────────────────────────────────┘
   │
   ▼
数字溯源（grounding_report）+ 工具轨迹 + token 统计
```

关键点：

| 能力 | 实现 |
|---|---|
| 原生工具调用 | OpenAI 兼容 `tools` / `tool_calls`，不解析文本里的伪 JSON |
| 多轮 | 工具结果作为 `role=tool` 消息回填，模型基于观察继续决策 |
| 预算 | 最多 6 步、每步 6 个工具、全局 24 次、单结果 6000 字符 |
| 参数校验 | `splicegaip/llm/structured.py::validate_schema`（type/required/enum/上下界） |
| 数字护栏 | `grounding_report` 把回答中的数字与工具返回事实比对，标出未溯源数字 |
| 可审计 | 每次工具调用记录参数、耗时、成功/失败、摘要 |
| 离线降级 | 无模型时执行确定性 briefing，并明确标注「未配置模型」 |
| 供应商适配 | DeepSeek 思考模式 + 工具调用会自动关闭 thinking，避免 400 |
| 失败容忍 | 网络/模型错误不会抛出到 UI，降级为确定性摘要并记录错误 |

## 3. 可用工具（只读，项目内）

| 工具 | 用途 |
|---|---|
| `list_projects` | 列出项目及事件数、显著事件数 |
| `project_overview` | 样本、分组、事件数、事件类型、Top 候选、富集、产物、日志 |
| `query_events` | 按基因 / 类型 / FDR / \|ΔPSI\| 查询事件 |
| `top_candidates` | 读取已排序候选 |
| `enrichment_summary` | 读取 GO/KEGG/Reactome 富集结果 |
| `dataset_quality` | 分组平衡、显著比例、存储的 plan 与质量提示 |
| `annotate_gene` | MyGene.info 基因注释（网络） |
| `search_literature` | PubMed 文献检索（网络） |
| `search_literature_passages` | Europe PMC 全文 + 本地 BM25 段落（网络，带 PMID/章节） |
| `pathway_enrichment` | Enrichr/GSEApy 富集（网络） |
| `predict_peptides` | 调用肽预测流水线（需要 CDS 表） |
| `read_interpretation` | 读取已保存的生物学解读 |
| `read_plan` | 读取分析计划、阈值、假设检验结果与局限 |

所有工具都限定在当前项目或已注册项目；没有 shell、没有任意文件路径、没有写操作
（`predict_peptides` 只写入运行目录下的 `peptide_results/`）。

## 4. 三种使用方式

### CLI

```bash
# 一次提问（自动带工具）
python run.py copilot --project-id SPN-XXXXXXXX \
  --message "这个项目的显著事件比例可信吗？先查数据质量再回答。"

# 只看工具与就绪状态
python run.py copilot --tools

# 不调用模型，输出确定性摘要
python run.py copilot --project-id SPN-XXXXXXXX --message "..." --offline
```

### HTTP API

```bash
curl -s http://127.0.0.1:8800/api/copilot/tools | jq .

curl -s -X POST http://127.0.0.1:8800/api/copilot/chat \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"SPN-XXXXXXXX","message":"最值得跟进的事件是什么？","max_steps":6}' | jq .
```

返回字段：

```json
{
  "answer": "## 结论 ...",
  "mode": "llm",
  "tool_calls": [{"tool": "project_overview", "arguments": {}, "ok": true, "summary": "...", "elapsed_seconds": 0.06}],
  "steps": 2,
  "usage": {"prompt_tokens": 5616, "completion_tokens": 1040, "total_tokens": 6656, "calls": 2},
  "grounding": {"checked": 29, "unverified": [], "severity": "ok", "grounded_ratio": 1.0},
  "errors": []
}
```

### MCP

`splicegaip.mcp.splice_server` 新增：

- `copilot_tools()` — 工具清单与模型就绪状态
- `ask_copilot(question, project_id, max_steps)` — 直接调用分析助手

任何 MCP 客户端（Claude Desktop、Cursor、自建 agent）都能调用。

### Web UI

「🤖 AI 助手」页面现在把问题发到 `/api/copilot/chat`，右侧面板显示：

- 模式徽标（模型 + 工具 / 离线摘要）
- 步数、工具调用数、耗时、token
- 每次工具调用的参数、结果摘要、耗时
- 数字溯源警告（若有未溯源数字）

## 5. 模型配置

与原来一致，三种方式任选：

```bash
# .env / 配置大模型.env
MODEL_API_BASE_URL=https://api.deepseek.com
MODEL_API_KEY=sk-...
MODEL_NAME=deepseek-flash
MODEL_THINKING=auto          # 工具调用时自动关闭思考
MODEL_REASONING_EFFORT=low
```

也支持 OpenAI、Moonshot、DashScope、本地 vLLM / Ollama（OpenAI 兼容端点）。
界面「模型配置」保存后即时生效（API 每次请求重新读取 `.env`；CLI 启动时加载）。

## 6. 科学护栏

- system prompt 规定：只能引用工具返回的事实；缺数据要明说；结合预测不等于呈递，
  相关性不等于因果，无配对正常样本不能称「肿瘤特异」。
- 最终回答固定四段：结论 / 关键证据 / 建议的下一步 / 局限。
- `grounding_report` 会把回答中的数字与工具返回的 JSON 比对。百分比与小数互通，
  年份、Top-N 这类结构性数字不参与比对；未溯源数字会在 UI 中标黄。
- 工具结果只读；`predict_peptides` 的输出落在运行目录，不覆盖项目原始数据。

## 7. 与主流方案的对应关系

| 主流模式 | 本项目实现 |
|---|---|
| ReAct / tool-calling agent | `copilot.ask` 的 act→observe 循环 |
| Planner / Executor / Critic | `agent/planner.py`：结构化计划 → 执行 → 审稿 → 最多一次修订 |
| Function calling | OpenAI `tools` + JSON Schema 参数 |
| Structured outputs | `validate_schema` + `coerce_answer`（规划/审稿都用 JSON Schema 校验） |
| Context engineering | 工具结果 6000 字符截断、最多 8 轮历史、计划注入 system prompt |
| Guardrails | 参数校验、步数/工具/网络/模型调用四重预算、数字溯源、固定回答结构 |
| Observability | 工具轨迹、token/延迟、计划、审稿意见、`/api/copilot/tools` |
| Caching | `agent/tool_cache.py`：SQLite + TTL + 项目隔离 + 会话内去重 |
| RAG | `knowledge/literature_rag.py`：Europe PMC 全文 → 分块 → BM25 → 带 PMID 的段落 |
| Streaming | `POST /api/copilot/stream`（SSE）+ UI 停止按钮 + 步骤级取消 |
| Evaluation | `agent/evaluation.py` + `examples/agent_eval/golden.jsonl` + `run.py eval-agent` |
| Graceful degradation | 无模型 → 确定性 briefing；工具失败 → 错误入轨迹 |
| Multi-model routing | `MODEL_ANALYST_NAME` / `MODEL_CRITIC_NAME`（富集层） |

## 8. 计划 + 审稿（plan / critic）

`mode` 三个取值：

| 模式 | 行为 |
|---|---|
| `react` | 直接进入工具循环，回答前只做确定性审稿 |
| `plan` | 先产出 2–5 步证据计划，执行后用模型审稿，必要时修订一次 |
| `auto`（默认） | 问题较长、含两个以上问号或触发词（为什么/比较/建议/下一步…）时走 `plan` |

计划内容：`goal` / `steps[{action, tool, arguments, purpose}]` / `success_criteria` / `risks`。
模型返回必须通过 `PLAN_SCHEMA` 校验，否则退回规则计划（`heuristic_plan`）。
执行时计划会写进 system prompt，模型偏离计划会被审稿发现。

审稿分两层：

1. **确定性**（永远执行）：没读项目数据就下结论 → high；数字未溯源 → high；
   计划中的工具没执行 → medium；缺四段结构 → low。
2. **模型审稿**（仅 `plan` 模式）：检查数字/基因/通路是否出现在工具结果、
   是否把结合预测说成呈递、是否把相关性说成因果。

模型审稿**不能降低**确定性检查的 high 级问题；反过来，程序也不让模型凭摘要臆断：
数字溯源由 `grounding_report` 权威判定，当它是 `ok` 时，模型以“数字未出现在工具结果里”
为由的 high 会被降为 medium。只有确定性 high 或语义类 high（例如把结合预测说成呈递、
把相关性说成因果）才会触发修订。

结构化调用（计划/审稿）使用“先正常思考模式、失败再无思考重试”的两段式：
DeepSeek 的 reasoning token 可能吃满 completion 预算导致空回复，第二段会关闭 thinking。
修订输出会做模板残留清洗；如果清洗后缺少四段或只剩工具调用标记，则保留原回答并记录
`revision_rejected`，不会把坏文本交给用户。

## 9. 工具缓存与预算

`CopilotTools` 对**联网工具**启用两级缓存：

| 层级 | 作用域 | 说明 |
|---|---|---|
| 会话缓存 | 单次问答 | 相同工具 + 相同参数不重复执行 |
| 持久缓存 | 跨问答/跨用户 | SQLite `runtime_root/cache/tool_cache.sqlite3`，默认 TTL 1800 s |

缓存键 = `sha256(project_id + tool + canonical_json_arguments)`，因此**不会跨项目串数据**。
只有成功结果才写缓存；缓存损坏时自动降级为「无缓存」，不影响回答。
`--no-cache` / `use_cache=false` 可绕过。

预算：

| 预算 | 默认值 |
|---|---|
| 模型轮数 | 6（可调至 10） |
| 工具调用总数 | 24 |
| 单轮工具调用 | 6 |
| 联网工具调用 | 8 |
| 模型调用（含计划/审稿/修订） | 10 |
| 单个工具结果字符 | 6000 |

## 10. 流式与取消

`POST /api/copilot/stream` 返回 `text/event-stream`，事件序列：

```text
plan → step → tool_start → tool_result → (critique) → (revision) → final → done
```

- 前端用 `fetch` + `ReadableStream` 解析，不需要额外依赖；
- 「停止」按钮 abort 请求，服务端在下一个步骤边界检查 `cancel` 并停止；
- 已完成的工具调用不会回滚，取消后返回 `cancelled=true`。

## 11. 全文文献 RAG

`search_literature_passages` 工具：

1. Europe PMC 检索 `OPEN_ACCESS:y` 文章；
2. 抓取 JATS 全文 XML（本地缓存，7 天内不重复下载）；
3. 解析 Abstract/Body 章节，按 ~170 词分块；
4. 本地 BM25（含轻量复数归一化）排序；
5. 返回带 `article_id / title / section / text / score / source` 的段落。

没有全文时退回摘要并标 `source=abstract`。段落是**抽取式原文**，
回答应引用 `article_id`，不要改写成没有出处的结论。

## 12. 评测

```bash
# 确定性（脚本模型，不联网、不花钱）
python run.py eval-agent
python scripts/evaluate_copilot.py --demo

# 真实模型回归
python run.py eval-agent --mode live --allow-network --min-pass-rate 0.8
```

指标：工具召回/精确率、禁用工具命中、四段结构、数字溯源、token、延迟。
报告写到 `out/agent_eval/agent_eval.{json,md}`。
黄金样本在 `examples/agent_eval/golden.jsonl`（当前 22 条），新增问题时先加样本再改 prompt。
仓库整体测试：316 passed / 覆盖率 50%（含 copilot、肽预测、全文 RAG、API/UI）。

## 13. 已知边界

- Copilot 读取的是**已完成分析的结果**，不会重新跑统计；需要重算时先跑 `analyze`。
- 文献/基因/通路工具依赖公网，失败会在轨迹中显示，不会伪造结果。
- 全文 RAG 只覆盖开放获取文章；付费文献只能拿到摘要。
- 计划与审稿增加 1–3 次模型调用，短问题的 token 成本会上升；用 `mode=react` 可关闭。
- 离线模式没有模型可规划：`mode=plan` 会返回启发式计划并发出 `plan` 事件，但不会做模型审稿。
- 人在回路（网络工具执行前确认）尚未实现，目前用 `allow_network=false` 做整轮禁用。

不要做的事：让模型直接写数据库、让模型生成 SQL、把「没有查到」当成「不存在」。
这三件事会让可复现性瞬间归零。

