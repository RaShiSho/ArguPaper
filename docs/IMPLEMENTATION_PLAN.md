# ArguPaper Implementation Plan

## 1. 目标

本计划用于把 PRD 收敛成一个可执行的 MVP 技术方案。核心原则是：

- 复用当前目录结构，不做无必要重构
- 先打通端到端链路，再增加智能性
- 优先保证 CLI 可用、结果稳定、成本可控

## 2. 技术策略总览

MVP 采用“薄 CLI + 编排服务 + 能力模块”的结构：

```text
CLI
  -> Workflow / Service
  -> PDF / Retrieval / Extraction / Analysis / Debate / Judge / Memory
  -> Report Generator
```

当前仓库已经具备良好的模块分层雏形，因此不建议重写目录，只需要把占位接口补成最小可用实现。

当前实现状态补充：

- `argupaper analyze` 已通过 `CLI -> AnalyzeWorkflow -> DebateChain` 接通辩论主链路
- 2-Agent debate 已不再是架构空洞，当前重点转向输出质量、异常降级和测试覆盖

## 3. 建议架构

### 3.1 CLI 层

保留 [commands.py](/E:/Code/Project/ArguPaper/src/argupaper/cli/commands.py) 作为入口，但职责收缩为：

- 参数解析
- 配置加载
- 进度展示
- 调用编排服务
- 结果展示与写盘

不应继续在 CLI 文件内堆叠业务流程。

### 3.2 编排层

建议新增一个轻量编排层，例如：

- `src/argupaper/workflows/analyze_paper.py`
- `src/argupaper/workflows/search_papers.py`

职责：

- 组织模块调用顺序
- 处理降级逻辑
- 汇总中间结果
- 控制 Search-in-the-loop 的触发时机

这是 MVP 最关键的一层，因为当前缺的不是单个类，而是端到端串联。

### 3.3 检索层

在现有 `retrieval/` 目录下补齐：

- [semantic_scholar.py](/E:/Code/Project/ArguPaper/src/argupaper/retrieval/semantic_scholar.py)
- `arxiv.py`
- [query_expansion.py](/E:/Code/Project/ArguPaper/src/argupaper/retrieval/query_expansion.py)

建议实现：

- `SemanticScholarClient.search()`
- `ArxivClient.search()`
- `QueryExpander.expand()`
- `RetrievalOrchestrator.search()` 负责多源合并、去重、排序

MVP 排序建议采用简单规则分：

```text
score = citation_weight + recency_weight + exact_match_weight
```

不建议第一版就引入复杂 reranker。

### 3.4 抽取与分析层

在 `extraction/` 和 `chains/` 中补齐四类能力：

- 结构化摘要抽取
- 方法与实验抽取
- Analysis 生成
- Evidence 生成

建议：

- `StructuredExtractor` 输出标准 dict / Pydantic 模型
- `AnalysisChain` 负责“讲清楚论文做了什么、为什么这样做、与什么问题相关”
- `EvidenceChain` 负责“实验设计是否足够、证据是否支撑 claim”

MVP 阶段不必追求“全论文精确抽取”，重点是输出稳定且字段完整。

### 3.5 Debate 与 Judge 层

当前已完成的 MVP 基线：

- `SupportAgent.think()`
- `SkepticAgent.think()`
- `DebateChain.run()`
- `AnalyzeWorkflow` 中的 debate 调用与结果回传

待增强能力：

- `ConsensusDetector.detect_consensus()`
- `ConsensusDetector.compute_confidence()`
- debate 输出结构校验与异常降级
- report 对 debate/judge 结果的结构化呈现增强

MVP 方案：

- 只启用 `support` 和 `skeptic`
- 轮数默认 2，最大 3
- 使用固定模板约束输出字段
- `compute_confidence()` 先基于规则计算，而不是训练模型

规则化置信度建议：

- 支持观点数量
- 反对观点数量
- 是否存在明确证据支撑
- 是否存在关键矛盾

### 3.6 记忆与存储层

在 [paper_store.py](/E:/Code/Project/ArguPaper/src/argupaper/memory/paper_store.py) 中先落本地文件版：

- `data/papers/<paper_id>/metadata.json`
- `data/papers/<paper_id>/abstract.json`
- `data/papers/<paper_id>/paper.md`
- `data/papers/<paper_id>/report.md`

MVP 不引入数据库或向量库。

好处：

- 易调试
- 易测试
- 符合 CLI 本地优先模式

### 3.7 输出层

补齐 [report.py](/E:/Code/Project/ArguPaper/src/argupaper/output/report.py)：

- `generate()`：把分析中间结果映射成 [ResearchReport](/E:/Code/Project/ArguPaper/src/argupaper/output/structures.py)
- `format_markdown()`：生成最终 Markdown

建议让报告格式严格绑定 `ResearchReport`，避免 CLI 临时拼接字符串。

## 4. MVP 数据流

### 4.1 `analyze` 流程

```text
CLI analyze
  -> load_config
  -> PDFPipeline.process
  -> StructuredExtractor
  -> AnalysisChain
  -> EvidenceChain
  -> optional retrieval supplement
  -> DebateChain
  -> ConsensusDetector
  -> ReportGenerator
  -> PaperStore.save_paper
  -> output markdown
```

说明：其中 `DebateChain` 已经接入当前 `analyze` workflow，后续工作主要是增强输出质量与失败兜底。

### 4.2 `search` 流程

```text
CLI search
  -> QueryExpander
  -> SemanticScholar / arXiv
  -> merge + dedupe + rank
  -> formatter output
```

## 5. 模块设计建议

### 5.1 配置

继续使用 [config.py](/E:/Code/Project/ArguPaper/src/argupaper/config.py) 统一配置，但建议补充：

- `ARXIV_ENABLED`
- `SEARCH_DEFAULT_LIMIT`
- `SEARCH_MAX_RESULTS`
- `ANALYZE_ENABLE_RETRIEVAL_LOOP`
- `PAPER_STORE_PATH`

### 5.2 领域模型

当前很多接口直接返回 `dict`，MVP 阶段建议新增几个轻量模型，减少字段漂移：

- `PaperMetadata`
- `SearchResult`
- `StructuredSummary`
- `EvidenceItem`
- `DebateRoundResult`

这些模型不需要过度设计，但要覆盖 CLI、Report、Store 的共享字段。

### 5.3 错误处理

需要定义并统一以下错误面：

- 检索 API 调用失败
- LLM 输出字段缺失
- 论文结构抽取失败
- Debate 中单角色生成失败
- 存储层落盘失败

要求：

- 主流程可识别是否可降级
- 对用户显示清晰错误，不暴露大段栈信息

### 5.4 Search-in-the-loop 触发规则

MVP 推荐用简单规则，不用 agent 自主策略：

- Evidence 检测到缺 baseline -> 搜索 baseline
- Skeptic 指出“缺少对比方法” -> 搜索相关方法
- Analysis 无法判断 novelty -> 搜索同主题论文 3 篇补充比较

限制：

- 最多触发 1 次
- 最多拉取 3 到 5 篇候选
- 仅进入方法比较和证据补充，不回灌整条大流程

## 6. 分阶段实施

### Phase 0：收敛契约与骨架

目标：

- 固定数据模型
- 固定编排层接口
- 明确报告结构

输出：

- `workflow` 层设计完成
- 核心模型定义完成
- CLI 改为调用 workflow

### Phase 1：完成真实检索能力

目标：

- `search` 不再输出占位数据

输出：

- Query expansion
- Semantic Scholar / arXiv 集成
- 结果合并、去重、排序

### Phase 2：完成结构化分析主链路

目标：

- `analyze` 能输出结构化简读、分析与证据结果

输出：

- StructuredExtractor
- AnalysisChain
- EvidenceChain
- ReportGenerator 初版

### Phase 3：增强已集成的 Debate 与 Judge

目标：

- 提升 `analyze` 主链路中 debate/judge 的稳定性与解释质量

输出：

- 增强 `ConsensusDetector`
- 细化规则化 confidence score
- debate/judge 结构校验与降级处理
- 更清晰的报告呈现

### Phase 4：补齐记忆与集成测试

目标：

- 形成可复用的本地知识沉淀
- 稳定主链路

输出：

- PaperStore 本地实现
- analyze/search 集成测试
- 降级与错误处理完善

## 7. 风险与应对

### 风险 1：外部 API 不稳定

应对：

- 检索与 PDF 转换都做超时和降级
- 报告中标记“补充检索失败”

### 风险 2：LLM 输出结构不稳定

应对：

- 统一 prompt 模板
- 强制结构化字段
- 在链路层做字段校验和兜底默认值

### 风险 3：MVP 范围失控

应对：

- 不在 MVP 中实现完整 4-Agent、知识图谱、URL 分析
- Search-in-the-loop 限制为单次规则触发

### 风险 4：CLI 文件继续膨胀

应对：

- 业务流程移入 workflow/service 层
- CLI 只负责输入输出

## 8. 建议的完成定义

技术上，以下状态意味着实施计划达标：

1. `search` 与 `analyze` 都基于真实能力模块执行，不再依赖占位实现。
2. 代码结构中存在清晰的 workflow 层，CLI 不再承担编排职责。
3. 论文分析结果能稳定映射到统一的 `ResearchReport`。
4. 本地 PaperStore 可以保存和读取历史分析结果。
5. 主链路具备基础测试和错误降级能力。

## 9. 本轮建议结论

下一阶段不该直接扩展更多“智能功能”，而应优先完成三件事：

1. 固定数据契约与 workflow 编排层。
2. 增强真实报告生成、异常降级与主链路测试。
3. 在已接入 Debate 的基础上细化 Judge/Confidence 与记忆库能力。
