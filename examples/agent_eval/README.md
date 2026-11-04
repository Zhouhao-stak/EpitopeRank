# Agent evaluation golden set

`golden.jsonl` is the regression suite for the analysis copilot. Each line is
one case:

```json
{
  "id": "overview",
  "message": "这个项目里有什么？",
  "expected_tools": ["project_overview", "dataset_quality"],
  "forbid_tools": ["predict_peptides"],
  "strategy": "react",
  "tool_arguments": {"query_events": {"significant_only": true, "limit": 20}},
  "notes": "基线问题：先事实后解释"
}
```

| 字段 | 含义 |
|---|---|
| `id` | 唯一标识，报告里用它定位 |
| `message` | 用户问题 |
| `expected_tools` | 一个合格分析员应该调用的工具 |
| `forbid_tools` | 不该出现的工具（越界/无关/高风险） |
| `strategy` | `react` 或 `plan` |
| `tool_arguments` | 期望的工具参数（脚本模型会照此调用） |
| `project_required` | 是否需要当前项目（默认 true） |
| `notes` | 这条样本想守住什么行为 |

## 运行

```bash
# 确定性：ScriptedChat 按 expected_tools 回放，不联网、不花钱
python run.py eval-agent
python scripts/evaluate_copilot.py --demo

# 真实模型回归
python run.py eval-agent --mode live --allow-network --min-pass-rate 0.8
```

指标：工具召回率、工具精确率、禁用工具命中、四段结构、数字溯源、token、延迟。
报告输出到 `out/agent_eval/agent_eval.{json,md}`。

## 添加样本

1. 先写 case（问题 + 期望工具 + 想守住的行为）；
2. 跑 `--mode scripted` 确认 harness 本身通过；
3. 再跑 `--mode live` 看真实模型是否达标；
4. 改 prompt 后两条都要重跑，并在 PR 里附 `agent_eval.md` 的差异。

## 注意

- `expected_tools` 不是唯一正确答案；如果一个 case 有多种合理路径，放宽期望或拆成多个 case。
- 脚本模型的召回率只证明「harness → 工具」链路通，不证明模型会这样选工具；
  模型能力必须用 `--mode live` 衡量。
- 需要联网的 case 在 scripted 模式下工具会被禁用，但工具名仍会计入召回率。
