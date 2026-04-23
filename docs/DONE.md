# DONE

## Search / Judge / MinerU Correctness 修复

完成时间：2026-04-23

本次围绕 review 暴露的 4 个 correctness 问题做了集中修复，重点不是扩能力，而是把现有 `search` 和 `analyze` 主链路修回到结果可信的状态，主要包括：

- 修复 `MinerUClient` 对同步返回结果的处理，提交接口内联返回 `markdown` / `content` 时不再伪造 `sync_result` 并发起无效轮询。
- 为 `MinerUClient` 增加可配置 endpoint，`AnalyzeWorkflow` 创建 pipeline 时会显式传入 `config.pdf.api_endpoint`。
- 修复 `SearchWorkflow` 的跨源去重逻辑，按规范化标题和 URL 联合识别重复论文，避免同一篇论文在多源检索结果中重复展示。
- 修复 `ConsensusDetector` 的 skeptic 回退逻辑，正向结论如 `The support case is mostly credible.` / `No major blocking gap remains.` 不再被误写入 `Disagreement`。
- 新增回归测试，覆盖 MinerU 同步返回、自定义 endpoint、生效的跨源去重，以及正向 skeptic 结论不会污染最终报告。

本次验证：

- `uv run --python .venv\Scripts\python.exe --no-project python -m pytest --basetemp=.pytest/cache/pytest-tmp-fix -o cache_dir=.pytest/cache tests/pdf/test_mineru_client.py::TestMinerUClient::test_submit_task_preserves_inline_markdown_response tests/pdf/test_mineru_client.py::TestMinerUClient::test_custom_endpoint_is_used_for_submit_and_status_requests tests/workflows/test_search_papers.py tests/judge/test_consensus.py tests/integration/test_analyze_workflow.py::test_analyze_workflow_build_pipeline_honors_configured_mineru_endpoint tests/integration/test_analyze_workflow.py::test_analyze_workflow_report_excludes_positive_skeptic_sentence_from_disagreement -q`
- 结果：`6 passed`

已知限制：

- 当前 `.pytest/tmp` 目录存在历史 ACL 异常，按规范路径直接运行 pytest 会在创建临时目录时失败，因此本次验证临时改用 `.pytest/cache/pytest-tmp-fix` 作为 `basetemp`。
- 当前环境中 `uv run --python .venv\Scripts\python.exe --no-project ruff check src/ tests/` 与 `uv run --python .venv\Scripts\python.exe --no-project mypy src/` 均失败，原因是 `.venv` 中不存在 `ruff` / `mypy` 可执行文件。

## 2-Agent Debate 完成

完成时间：2026-04-22

本次新增并完善了 2-Agent debate 的 MVP 功能，主要包括：

- 完成 `SupportAgent` 与 `SkepticAgent` 的可执行实现
- 完成 `DebateChain` 的多轮辩论编排
- 已通过 `AnalyzeWorkflow` 接入 `argupaper analyze` 主流程
- 支持基于 `analysis` 与 `evidence` 上下文生成辩论内容
- 支持在证据充分时第 2 轮提前收敛
- 支持在 baseline / ablation / metrics 缺失时继续跑满配置轮数
- 为 `AgentMessage` 与 `DebateState` 修复可变默认值问题，避免状态串联
- 新增 `tests/chains/test_debate.py`，覆盖提前收敛、跑满轮数和状态隔离

当前边界：

- 当前没有独立的 `argupaper debate` CLI 子命令
- 2-Agent debate 仅作为 `argupaper analyze` 的内部阶段执行

后续增强项：

- 提升 `ConsensusDetector` 的结论提取质量
- 细化 confidence 的规则计算
- 增强 report 中对 debate 结果的结构化展示

已验证：

- `pytest tests/chains/test_debate.py`
- 结果：`3 passed`

## CLI MVP 升级

完成时间：2026-04-22

本次完成了 CLI 方向的 MVP 级实现与重构，主要包括：

- 将 CLI 从占位实现重构为 `commands -> workflows -> modules` 的分层结构
- 为 `argupaper` 增加 `--version` 能力
- 重构 `analyze` 命令，补齐参数校验、阶段进度、报告输出、warning 展示和文件写出
- 重构 `search` 命令，移除模拟结果，接入真实检索工作流
- 新增 workflow 契约与模型：
  - `AnalyzeWorkflow`
  - `SearchWorkflow`
  - `AnalyzeOptions` / `SearchOptions`
  - `AnalyzeWorkflowResult` / `SearchWorkflowResult`
- 新增基础检索实现：
  - Semantic Scholar API 客户端
  - arXiv API 客户端
  - Query expansion
  - 多源合并、去重、排序
- 新增 MVP 级分析链路：
  - 结构化抽取
  - Analysis / Evidence
  - 2-Agent Debate
  - Consensus / Confidence
  - Report 生成
  - 本地 PaperStore 落盘
- 更新 CLI formatter，支持：
  - 搜索结果表格
  - 分析摘要
  - warning / success / error / info 面板
  - markdown 报告渲染

## 测试

新增：

- `tests/cli/test_commands.py`
- `tests/conftest.py`

已验证：

- `.\.venv\Scripts\python.exe -m pytest tests/cli/test_commands.py tests/pdf/test_pipeline.py`
- 结果：`15 passed`

## 当前状态

CLI 已具备 MVP 可用性：

- `argupaper analyze <local.pdf>` 可跑通真实工作流骨架
- `argupaper search <query>` 可返回真实检索结果
- URL PDF 分析仍明确排除在 MVP 外
- 深层分析质量目前仍是 MVP 级启发式实现，后续可继续替换为更强的链路与模型能力

## 检索 Agent 集成完成

完成时间：2026-04-22

本次新增了面向 `argupaper search` 的检索 Agent，主要包括：

- 将 `search` 升级为“双模式兼容”入口，同时支持纯关键词和自然语言请求
- 新增基于弱 LLM 的请求解析层，提取关键词、数量、年份等筛选条件
- 对“权威期刊”等模糊条件增加 CLI 二次确认，避免系统暗自猜测
- 复用现有 Semantic Scholar / arXiv 检索链路做候选召回
- 新增过滤层，对年份、发表源、数量等条件做结果筛选
- 新增搜索 Agent trace 落盘，保存原始请求、解析结果、原始候选、过滤结果和最终结果
- 新增通用 OpenAI 兼容 LLM provider 配置，为后续其他 Agent 复用做准备
- 新增 Prompt 独立目录，避免把 Agent Prompt 硬编码在 Python 中

已验证：

- `uv run pytest -q`
- 结果：`44 passed`

## Analyze 主链路稳定性增强

完成时间：2026-04-22

本次围绕 `argupaper analyze` 主链路做了稳定性收口，重点不是扩展更多 Agent，而是让当前链路更可解释、更可降级、更可验证，主要包括：

- 强化 `AnalyzeWorkflow` 的主链路契约，统一 judge/report 使用的中间结果结构
- 为 supplementary retrieval、debate、judge、report 增加显式 warning 汇总与局部失败降级
- 重写 `ConsensusDetector`，让共识、分歧、supporting evidence、confidence、conflict intensity 基于 debate/evidence/supplementary retrieval 信号生成
- 重构 `ReportGenerator`，让 `Method Comparison`、`Debate Summary`、`Consensus vs Disagreement`、`Warnings` 结构化输出
- 新增 `tests/integration/test_analyze_workflow.py`，覆盖 happy path、降级路径与 `rounds` 参数传递

当前收益：

- `argupaper analyze` 在局部失败时不再轻易整体中断
- 报告中的 debate 与 judge 信息更清晰，warning 能直接暴露给用户
- analyze 主链路具备基础集成测试，便于后续继续增强 Judge、Report 和 Debate

本次验证：

- `uv run pytest tests/integration/test_analyze_workflow.py tests/chains/test_debate.py -q`
- 结果：`6 passed`

已知限制：

- 当前环境中 `uv run ruff` 与 `uv run mypy` 命令不可用，因此未完成静态检查验证
