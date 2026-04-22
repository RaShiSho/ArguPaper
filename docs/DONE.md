# DONE

## 2-Agent Debate 完成

完成时间：2026-04-22

本次新增并完善了 2-Agent debate 的 MVP 功能，主要包括：

- 完成 `SupportAgent` 与 `SkepticAgent` 的可执行实现
- 完成 `DebateChain` 的多轮辩论编排
- 支持基于 `analysis` 与 `evidence` 上下文生成辩论内容
- 支持在证据充分时第 2 轮提前收敛
- 支持在 baseline / ablation / metrics 缺失时继续跑满配置轮数
- 为 `AgentMessage` 与 `DebateState` 修复可变默认值问题，避免状态串联
- 新增 `tests/chains/test_debate.py`，覆盖提前收敛、跑满轮数和状态隔离

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
