# DONE

## CLI 错误处理与空内容降级提示收口

完成时间：2026-04-25

本次将 CLI 输入错误、配置缺失和外部检索源全失败统一收敛到 workflow error 类型，并增强了用户可读错误面板。

主要调整：

- `load_config()` 在缺少 `MINERU_API_KEY` 时抛出 `ConfigurationError`，不再使用普通 `ValueError`。
- `analyze`、`search`、`papers` 的参数错误统一抛出 `InputValidationError`。
- 检索源全部失败时抛出 `ExternalServiceError`，错误面板会提示检查网络、API credentials 与检索源配置。
- `format_error()` 增加 Next step 提示，避免只显示异常类型。
- `AnalyzeWorkflow` 在 PDF 转换返回空 Markdown 时追加 warning，并跳过补充检索，避免静默使用空内容触发无意义外部搜索。

当前验收方式：

- 参考 [SMOKE.md](/E:/Code/Project/ArguPaper/docs/SMOKE.md) 中的 CLI 错误处理表单执行手工验收。

## 本地论文历史记录读取入口完成

完成时间：2026-04-25

本次补齐了面向本地 PaperStore 的 CLI 读取入口，用户可以通过 `argupaper papers` 查看 analyze 已保存的论文记录。

主要调整：

- 新增 `PaperStore.list_papers()`，按最近更新时间列出已保存记录。
- 增强 `PaperStore.get_paper()`，支持使用完整 paper id 或唯一 hash 前缀读取记录，并限制输入不能越过存储目录。
- 新增 `argupaper papers` 命令，支持列出记录、`--query` 本地搜索、按 paper id 查看结构化摘要，并可用 `--report` / `--markdown` 渲染保存内容。
- README、任务清单与 smoke 表单已同步补充。

当前验收方式：

- 参考 [SMOKE.md](/E:/Code/Project/ArguPaper/docs/SMOKE.md) 中的本地论文历史记录读取表单执行手工验收。

## Claim-Evidence 对齐与证据充分性检查完成

完成时间：2026-04-25

本次补齐了 `ClaimChecker` 的 MVP 规则实现，并将其接入 `EvidenceChain`，让 analyze 主链路可以产出 `claims`、`aligned_claims`、`unsupported_claims`、`contradictions` 与 `missing_analyses` 等结构化信号。

主要调整：

- 实现 claim 文本抽取、证据文本归一化、token overlap 对齐、强 claim 直接证据检查和正反向证据冲突识别。
- 实现 evidence sufficiency 检查，显式识别 dataset、metric、baseline、ablation 缺口。
- `EvidenceChain` 会从 Abstract / Introduction / Conclusion 中抽取候选 claim，并把 claim-evidence 结果传给 debate、judge 与报告链路。
- 修复 `agents`、`chains`、`workflows` 包级重导出导致的循环导入问题，改为懒加载导出，保证单模块导入可用。
- `docs/TASKS.md` 与 `docs/SMOKE.md` 已同步补充本次变更。

当前验收方式：

- 参考 [SMOKE.md](/E:/Code/Project/ArguPaper/docs/SMOKE.md) 中的 Claim-Evidence 对齐表单执行手工验收。

## 搜索相对年份解析修复

完成时间：2026-04-25

本次修复了搜索请求里相对年份表达的归一化问题，重点是避免弱 LLM 将 `近一年` 这类请求解析成过期年份范围。

主要调整：

- 在 `SearchRequestParser` 中新增统一的相对年份归一化逻辑，对弱 LLM 输出和启发式解析统一生效。
- 当前本地日期会动态注入到搜索解析 prompt 中，减少模型受静态示例年份误导的概率。
- `parse_request_schema.txt` 中的年份示例从固定年份改为 `null`，去掉对过期年份的暗示。
- `docs/SMOKE.md` 增加相对时间解析的手工验收项。

## 测试与静态检查体系移除

完成时间：2026-04-25

本次清理删除了项目中的 `pytest`、`ruff`、`mypy` 相关依赖、配置和说明，同时移除了整个 `tests/` 目录，并把项目验收方式统一收敛到 [SMOKE.md](/E:/Code/Project/ArguPaper/docs/SMOKE.md)。

主要调整：

- 删除 `tests/` 目录，不再维护自动化测试代码。
- 从 `pyproject.toml` 中移除 `pytest`、`pytest-asyncio`、`ruff`、`mypy` 及相关工具配置。
- 从 `AGENTS.md`、`CLAUDE.md`、`README.md`、`openspec/config.yaml` 和两个 active change 中删除自动验证要求。
- 新增 `docs/SMOKE.md`，作为项目唯一的手工 smoke 验收入口。
- 在 `AGENTS.md` 中新增规则：以后新增功能、主链路变更或行为修复，都必须同步更新 `docs/SMOKE.md`。

当前验收方式：

- 统一参考 [SMOKE.md](/E:/Code/Project/ArguPaper/docs/SMOKE.md) 执行手工 smoke 验收。

## Search / Judge / MinerU Correctness 修复

完成时间：2026-04-23

本次围绕 review 暴露的 4 个 correctness 问题做了集中修复，重点不是扩能力，而是把现有 `search` 和 `analyze` 主链路修回到结果可信的状态，主要包括：

- 修复 `MinerUClient` 对同步返回结果的处理，提交接口内联返回 `markdown` / `content` 时不再伪造 `sync_result` 并发起无效轮询。
- 为 `MinerUClient` 增加可配置 endpoint，`AnalyzeWorkflow` 创建 pipeline 时会显式传入 `config.pdf.api_endpoint`。
- 修复 `SearchWorkflow` 的跨源去重逻辑，按规范化标题和 URL 联合识别重复论文，避免同一篇论文在多源检索结果中重复展示。
- 修复 `ConsensusDetector` 的 skeptic 回退逻辑，正向结论如 `The support case is mostly credible.` / `No major blocking gap remains.` 不再被误写入 `Disagreement`。

当前验收方式：

- 参考 [SMOKE.md](/E:/Code/Project/ArguPaper/docs/SMOKE.md) 中的检索与 analyze 表单进行手工验收。

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

当前边界：

- 当前没有独立的 `argupaper debate` CLI 子命令
- 2-Agent debate 仅作为 `argupaper analyze` 的内部阶段执行

后续增强项：

- 提升 `ConsensusDetector` 的结论提取质量
- 细化 confidence 的规则计算
- 增强 report 中对 debate 结果的结构化展示

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

## Analyze 主链路稳定性增强

完成时间：2026-04-22

本次围绕 `argupaper analyze` 主链路做了稳定性收口，重点不是扩展更多 Agent，而是让当前链路更可解释、更可降级，主要包括：

- 强化 `AnalyzeWorkflow` 的主链路契约，统一 judge/report 使用的中间结果结构
- 为 supplementary retrieval、debate、judge、report 增加显式 warning 汇总与局部失败降级
- 重写 `ConsensusDetector`，让共识、分歧、supporting evidence、confidence、conflict intensity 基于 debate/evidence/supplementary retrieval 信号生成
- 重构 `ReportGenerator`，让 `Method Comparison`、`Debate Summary`、`Consensus vs Disagreement`、`Warnings` 结构化输出

当前收益：

- `argupaper analyze` 在局部失败时不再轻易整体中断
- 报告中的 debate 与 judge 信息更清晰，warning 能直接暴露给用户
- analyze 主链路具备更清晰的手工 smoke 验收入口，便于后续继续增强 Judge、Report 和 Debate
