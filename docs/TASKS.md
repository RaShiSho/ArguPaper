# ArguPaper Tasks

## 使用说明

本任务清单面向 MVP 实施，按依赖顺序排列。状态默认为 `TODO`。

优先级说明：

- `P0`：阻塞 MVP
- `P1`：MVP 完成后立即需要
- `P2`：可延后

## Milestone 0：契约与编排骨架

- `P0` T001 定义 MVP 统一领域模型：`SearchResult`、`StructuredSummary`、`EvidenceItem`、`DebateRoundResult`、报告中间结果。
  验收：核心模块不再随意传裸 `dict`，共享字段有明确模型。
- `P0` T002 设计并实现 `workflow` / `service` 编排层，承接 `analyze` 与 `search` 主流程。
  验收：CLI 命令只做参数处理、进度展示、结果输出。
- `P0` T003 明确报告装配契约，统一 `ResearchReport` 输入来源。
  验收：输出层无需依赖 CLI 内部字符串拼接。

## Milestone 1：真实检索链路

- `P0` T101 实现 [query_expansion.py](/E:/Code/Project/ArguPaper/src/argupaper/retrieval/query_expansion.py) 的基础扩展逻辑。
  验收：输入一个 query，返回原词、同义扩展词、方法词或数据集词列表。
- `P0` T102 实现 [semantic_scholar.py](/E:/Code/Project/ArguPaper/src/argupaper/retrieval/semantic_scholar.py) 的真实检索调用。
  验收：可返回标题、作者、年份、来源、引用数、URL。
- `P0` T103 实现 `arxiv.py` 的真实检索调用。
  验收：可返回与 Semantic Scholar 兼容的标准结果结构。
- `P0` T104 实现多源合并、去重、排序逻辑。
  验收：同一论文不会重复展示，结果按规则分排序。
- `P0` T105 替换 [commands.py](/E:/Code/Project/ArguPaper/src/argupaper/cli/commands.py) 中 `search` 的占位结果。
  验收：`argupaper search` 不再输出 simulated papers。
- `P1` T106 为检索模块补充单测和 API 失败场景测试。
  验收：正常返回、空结果、超时、限流均有覆盖。

## Milestone 2：结构化分析主链路

- `P0` T201 实现 [structured.py](/E:/Code/Project/ArguPaper/src/argupaper/extraction/structured.py) 的摘要抽取能力。
  验收：可稳定输出 Problem / Method / Experiment / Conclusion。
- `P0` T202 实现 [analysis.py](/E:/Code/Project/ArguPaper/src/argupaper/chains/analysis.py)。
  验收：输出研究问题、方法原理、技术路线等结构化分析内容。
- `P0` T203 实现 [evidence.py](/E:/Code/Project/ArguPaper/src/argupaper/chains/evidence.py)。
  验收：输出数据集、指标、实验设置、主要证据判断。
- `P0` T204 实现 [claim_checker.py](/E:/Code/Project/ArguPaper/src/argupaper/extraction/claim_checker.py) 的 claim-evidence 对齐与充分性检查。
  验收：可识别 unsupported claims、缺 baseline、缺 ablation。
- `P0` T205 将 PDFPipeline 与抽取/分析链路接入 `analyze` workflow。
  验收：本地 PDF 可生成非占位的中间分析结果。
- `P1` T206 针对 PDF 结构不完整、Markdown 为空、抽取字段缺失做降级逻辑。
  验收：失败时仍输出最小化报告或明确错误。

## Milestone 3：Debate、Judge 与报告生成

- `[DONE] P0` T301 实现 [support.py](/E:/Code/Project/ArguPaper/src/argupaper/agents/support.py)。
  验收：能基于分析结论与证据生成支持观点。
- `[DONE] P0` T302 实现 [skeptic.py](/E:/Code/Project/ArguPaper/src/argupaper/agents/skeptic.py)。
  验收：能针对 claim、实验设计和证据充分性提出质疑。
- `[DONE] P0` T303 实现 [debate.py](/E:/Code/Project/ArguPaper/src/argupaper/chains/debate.py) 的 2-Agent 多轮编排。
  验收：轮数可配置，至少支持 2 轮。
- `[TODO] P0` T304 增强 [consensus.py](/E:/Code/Project/ArguPaper/src/argupaper/judge/consensus.py)。
  验收：提升 consensus、disagreements、supporting_evidence、confidence score 的提取质量与解释性。
- `[TODO] P0` T305 增强 [report.py](/E:/Code/Project/ArguPaper/src/argupaper/output/report.py) 的 `generate()` 与 `format_markdown()`。
  验收：更清晰地呈现 debate/judge 结果，并保持符合 `ResearchReport` 的 Markdown 报告输出。
- `[DONE] P0` T306 替换 [commands.py](/E:/Code/Project/ArguPaper/src/argupaper/cli/commands.py) 中 `analyze` 的占位报告逻辑。
  验收：`argupaper analyze` 输出真实结构化报告。
- `[TODO] P1` T307 为 Debate 和 Judge 增加结构校验与兜底默认值。
  验收：单角色输出异常时，不会导致整个报告崩溃。

## Milestone 4：基础记忆库与 Search-in-the-loop

- `P0` T401 实现 [paper_store.py](/E:/Code/Project/ArguPaper/src/argupaper/memory/paper_store.py) 的本地文件存储。
  验收：保存 metadata、abstract、markdown、report。
- `P0` T402 在 `analyze` 完成后自动写入基础论文记录。
  验收：分析后 `data/papers/<paper_id>/` 下出现完整文件。
- `P0` T403 实现一次性、规则触发的 Search-in-the-loop。
  验收：当检测到缺 baseline 或缺对比时，自动补充 3 到 5 篇候选论文。
- `P1` T404 将补充检索结果接入 `Method Comparison` 或 `Evidence Table`。
  验收：报告中能显式展示补充检索带来的比较依据。
- `P1` T405 实现历史论文记录读取能力。
  验收：可按 paper id 或 hash 读取已保存记录。

## Milestone 5：测试、稳定性与发布前清理

- `[TODO] P0` T501 为 `analyze` workflow 增加一条端到端集成测试。
  验收：从模拟 PDF 转换结果到最终报告的主流程可跑通。
- `[TODO] P0` T502 为 `search` workflow 增加集成测试。
  验收：支持多源结果合并、去重和排序验证。
- `[TODO] P0` T503 统一错误处理与用户可读报错格式。
  验收：配置缺失、API 失败、空结果、解析失败都有明确提示。
- `[TODO] P1` T504 清理配置项与 `.env.example`，补齐新增环境变量。
  验收：文档与代码一致，启动不依赖隐式配置。
- `[TODO] P1` T505 补充 README 的 MVP 使用说明。
  验收：新用户可以按文档完成一次检索和一次分析。
- `[TODO] P0` T506 为 `analyze` workflow 增加覆盖 debate 链路的集成测试。
  验收：测试可验证 `--rounds` 参数传递、`Debate Summary` 输出以及 debate 失败时的降级或 warning 行为。

## 延后项

- `P1` T601 支持远程 URL PDF 分析。
- `P1` T602 扩展为 4-Agent Debate。
- `P1` T603 引入更稳定的 confidence 计算策略。
- `P2` T701 知识图谱与跨论文推理。
- `P2` T702 引文扩展追踪。
- `P2` T703 多轮自优化与更复杂的动态检索闭环。

## 建议执行顺序

1. 先做 T001-T005 级别的契约与编排骨架。
2. 再做 T101-T105，先让 `search` 可用。
3. 接着做 T201-T205 与 T306，打通 `analyze` 最短链路。
4. 优先补 T304、T305、T307 与 T506，增强已接入的辩论、裁决和报告链路。
5. 最后做 T401-T403 与其余测试收尾。
