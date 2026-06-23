# SciFact Court Eval

此目录是 ArguPaper `paper_court_graph` 的独立实验评测入口，不并入主产品包。

## Milvus 隔离规则

- 默认 collection：`scifact_court_eval_chunks`
- 不调用 `argupaper rag index`
- 不写入、不删除、不搜索默认 `paper_chunks`
- SciFact chunk 的 `paper_id` 固定为 `scifact`
- chunk id 格式：`scifact:<doc_id>:sent:<sentence_idx>`
- metadata 保留 `doc_id`、`sentence_idx`、`title`、`gold_split`、`source`、`section`

## 运行

最小 smoke：

```powershell
uv run python scifact_court_eval/run_eval.py run --split dev --limit 3 --top-k 5 --max-rounds 1 --index-if-missing
```

资源受限环境建议只索引当前评测 claims 相关文档：

```powershell
uv run python scifact_court_eval/run_eval.py run --split dev --limit 3 --top-k 5 --max-rounds 1 --rebuild-index --index-scope claims
```

中等规模：

```powershell
uv run python scifact_court_eval/run_eval.py run --split dev --limit 50 --top-k 10 --max-rounds 1 --index-if-missing
```

清理评测索引：

```powershell
uv run python scifact_court_eval/run_eval.py cleanup-index
```

## 输出

默认写入 `output/scifact_court_eval/`：

- `results.jsonl`：每条 claim 的结构化结果
- `judge_traces.jsonl`：Judge LLM 结构化评分
- `summary.json`：聚合指标
- `summary.md`：Markdown 汇总
- `failures.md`：错误分类和高风险案例

运行日志默认写入 `data/logs/scifact/`，每次运行生成一个 JSONL 文件。日志包含索引进度、每条 claim 的 baseline/court/judge 事件、最终汇总，以及 Judge/Baseline 的 `raw_response_preview`，用于诊断模型没有返回 JSON 的原因。可用 `--log-dir` 覆盖日志目录。

## 依赖

运行完整评测需要可用的 Milvus、Ollama embedding 服务，以及项目 LLM provider 配置。若 Judge LLM 返回非 JSON 或调用失败，单条样本会记录为 `judge_failed`，批次不中断。

如果 Ollama embedding 在索引阶段返回 502，优先确认 `OLLAMA_EMBED_MODEL` 已存在；也可以显式降低批大小：

```powershell
uv run python scifact_court_eval/run_eval.py run --split dev --limit 3 --top-k 5 --max-rounds 1 --rebuild-index --index-scope claims --batch-size 1
```

如果 Milvus 报 `memory quota exhausted`，说明当前服务承载不了全 SciFact corpus 的 45952 个 sentence vectors。先使用 `--index-scope claims` 做 smoke；正式全库评测需要提高 Milvus 内存配额或减少待索引语料规模。
