# DONE

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
