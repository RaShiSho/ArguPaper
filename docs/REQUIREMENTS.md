# ArguPaper Requirements

## 1. 文档目的

本文档基于 [PRD.md](/E:/Code/Project/ArguPaper/docs/PRD.md) 与当前仓库实现现状，收敛出 ArguPaper 的近期交付目标，明确：

- 需求分析
- MVP 范围
- 当前代码与目标之间的差距
- MVP 验收标准

说明：用户提到“项目根目录的 `PRD.md`”，实际仓库内存在的是 [PRD.md](/E:/Code/Project/ArguPaper/docs/PRD.md)。

## 2. 当前项目现状

当前仓库并非从零开始，已经具备如下基础：

- CLI 基础入口已存在：[commands.py](/E:/Code/Project/ArguPaper/src/argupaper/cli/commands.py)
- PDF 转 Markdown 主链路基本可用：[pipeline.py](/E:/Code/Project/ArguPaper/src/argupaper/pdf/pipeline.py)
- PDF 缓存与本地服务已有测试覆盖：`tests/pdf/*`
- 输出结构已定义：[structures.py](/E:/Code/Project/ArguPaper/src/argupaper/output/structures.py)
- 检索、抽取、分析、辩论、裁决、记忆库多数仍是接口占位

这意味着 MVP 应优先补齐“端到端可运行链路”，而不是大规模重构目录或追求完整研究系统。

## 3. 产品目标

ArguPaper 的目标不是“论文摘要工具”，而是一个面向科研阅读与批判分析的 CLI 系统，支持：

1. 输入一篇论文 PDF，输出结构化分析报告。
2. 输入一个研究主题，返回候选论文列表。
3. 在分析过程中引入外部论文证据，而不是只对单篇论文做封闭式总结。

MVP 阶段只要求做到“单篇论文分析 + 基础检索 + 轻量对抗分析 + 结构化报告”。

## 4. 目标用户

- 需要快速筛选论文的研究生/研究人员
- 需要做相关工作调研的工程师
- 需要获得“初步批判视角”而非纯摘要的学术用户

## 5. 核心用户场景

### 场景 A：分析本地 PDF

用户执行：

```bash
argupaper analyze ./paper.pdf --output report.md --rounds 2
```

系统完成：

1. 解析 PDF 为 Markdown
2. 提取论文结构化信息
3. 生成分析层结论
4. 提取实验与证据
5. 进行 2-Agent 轻量辩论
6. 输出 Markdown 报告并保存基础记忆

### 场景 B：检索研究主题

用户执行：

```bash
argupaper search "retrieval augmented generation" --limit 10
```

系统完成：

1. 生成扩展查询
2. 调用 Semantic Scholar / arXiv
3. 合并与去重结果
4. 基于引用数、年份等字段做基础排序
5. 输出候选论文列表

### 场景 C：分析过程中的补充检索

在 `analyze` 流程中，当系统发现以下情况时，可触发一次有限补充检索：

- 缺少 baseline
- 关键 claim 需要对照证据
- 需要一个反例或相近方法做比较

MVP 中该能力只做“单次、规则触发、有限结果数”的 Search-in-the-loop。

## 6. MVP 范围

### 6.1 MVP 必须包含

- `argupaper analyze <local_pdf>`
- `argupaper search <query>`
- PDF 转 Markdown
- 结构化简读
- Analysis Layer
- Evidence Layer
- 2-Agent 简化 Debate
- 基础报告生成
- 基础记忆库存储
- 基础 Search-in-the-loop

### 6.2 MVP 明确不包含

- Web UI
- 知识图谱
- 多轮自优化
- 完整 4-Agent Debate
- 高级置信度建模
- 跨论文复杂推理
- 直接分析远程 URL PDF
- 实时流式异步任务编排平台

### 6.3 P1 范围

- 完整 Debate 角色体系：support / skeptic / comparator / evidence
- Judge 层聚合
- 更稳定的置信度分数
- 更通用的动态检索引擎
- URL 分析支持

### 6.4 P2 范围

- 知识图谱
- 引文扩展追踪
- 多轮迭代优化
- 更强的跨论文记忆与冲突检测

## 7. 功能需求

### FR-1 CLI 入口

- 系统必须提供 `analyze` 与 `search` 两个主命令。
- CLI 必须输出清晰的阶段进度、错误原因和最终结果。
- CLI 参数必须支持 `--output`、`--rounds`、`--limit`、`--source` 等核心选项。

### FR-2 PDF 处理

- 系统必须支持本地 PDF 输入。
- 系统必须将 PDF 转换为 Markdown，并缓存结果。
- 当缓存存在且未指定强制重跑时，应优先复用缓存。

### FR-3 结构化简读

- 系统必须从论文中抽取至少以下字段：
  - Problem
  - Method
  - Experiment
  - Conclusion
- 简读结果必须可直接写入最终报告。

### FR-4 检索能力

- 系统必须支持基于主题词检索候选论文。
- 系统必须支持基础 query expansion。
- 系统必须支持来自多个来源的结果合并与去重。
- 系统必须输出最少包含标题、作者、年份、来源、引用数、URL。

### FR-5 分析层

- 系统必须输出论文的方法原理拆解。
- 系统必须输出技术路线或研究问题分析。
- 系统必须生成可阅读的结构化结论，而不是仅返回原文摘录。

### FR-6 证据层

- 系统必须抽取实验相关信息：
  - 数据集
  - 指标
  - 样本或实验设置
- 系统必须识别实验是否支撑主要 claim。
- 系统必须指出明显缺失项，如 baseline 或 ablation 缺失。

### FR-7 轻量辩论

- 系统必须支持最少 2 个角色参与辩论：`support` 与 `skeptic`。
- 辩论轮数必须可配置。
- 每轮辩论必须围绕已有分析结论和证据展开。
- MVP 阶段允许使用模板化或半结构化输出，不要求复杂 agent 社会模拟。

### FR-8 Search-in-the-loop

- 在分析流程中，系统必须允许辩论或证据模块触发补充检索。
- MVP 中仅要求支持一次补充检索，不要求多轮闭环。
- 检索结果必须进入报告中的“Method Comparison”或“Evidence Table”。

### FR-9 报告输出

- 系统必须生成 Markdown 报告。
- 报告结构至少包含：
  - Research Overview
  - Method Comparison
  - Evidence Table
  - Debate Summary
  - Contradictions
  - Weakness Analysis
  - Consensus vs Disagreement
- `confidence_score` 在 MVP 中可以是规则化分值，不要求复杂统计模型。

### FR-10 基础记忆库

- 系统必须保存每篇论文的基础元数据、摘要信息、Markdown 或其引用路径。
- 系统必须支持按论文 ID 或 hash 读取历史记录。
- MVP 不要求真正的语义向量检索，可先用本地文件索引。

## 8. 非功能需求

### NFR-1 稳定性

- 单个外部服务失败时，系统应给出可解释错误，而不是静默失败。
- 无法完成补充检索时，主分析流程应允许降级继续。

### NFR-2 可测试性

- 每个核心模块都需要可独立单测。
- `analyze` 主流程至少需要一个集成测试桩链路。

### NFR-3 可配置性

- API Key、模型名、缓存目录、最大轮数等必须由环境变量或 CLI 参数控制。

### NFR-4 可维护性

- CLI 层保持薄，业务编排不能堆在命令函数中。
- 外部 API 客户端、LLM 调用、存储层应保持清晰边界。

### NFR-5 成本控制

- MVP 阶段优先采用“有限轮数 + 有限检索数 + 结构化 prompt”策略控制调用成本。

## 9. 关键取舍

### 取舍 1：MVP 只做本地 PDF 分析

原因：

- 当前 [commands.py](/E:/Code/Project/ArguPaper/src/argupaper/cli/commands.py) 中 URL 分析明确未实现
- 加入 URL 下载会引入额外错误面、缓存策略和来源合法性问题

### 取舍 2：MVP 用 2-Agent Debate，而不是完整 4-Agent

原因：

- 当前 agent 与 debate 实现均为空壳
- 2-Agent 足以先验证“对抗性能否提升分析质量”

### 取舍 3：MVP 记忆库采用本地文件存储

原因：

- 当前项目尚未引入向量库依赖
- 对单机 CLI 场景，文件级索引即可支撑初版

### 取舍 4：Search-in-the-loop 采用规则触发

原因：

- 规则触发更容易测试与控制成本
- 多轮自适应检索应留到 P1 后再做

## 10. 当前差距分析

已具备：

- PDF 解析主链路
- CLI 基础框架
- 输出结构模型
- 配置与缓存机制

主要缺失：

- 实际可用的检索客户端
- Query expansion
- Structured extraction
- Analysis / Evidence / Debate 的真实执行逻辑
- Judge / Confidence 逻辑
- Report formatter
- PaperStore 落盘与读取
- `analyze` 端到端编排

## 11. MVP 验收标准

当以下条件同时成立时，视为 MVP 完成：

1. 用户可对本地 PDF 执行 `argupaper analyze` 并生成 Markdown 报告。
2. 报告至少包含概览、证据表、辩论摘要、问题点与结论分歧。
3. 用户可执行 `argupaper search` 获取真实检索结果，而非占位数据。
4. 分析流程可在缺少补充检索结果时降级完成。
5. 系统会缓存 PDF 转换结果，并保存基础论文记录。
6. 关键模块具备基础测试覆盖，端到端主链路至少有一条集成测试。

## 12. 建议的交付顺序

1. 打通 `search` 的真实结果链路。
2. 打通 `analyze` 的“PDF -> 抽取 -> 分析 -> 报告”最短主链路。
3. 在主链路上插入 Evidence 与 2-Agent Debate。
4. 最后补基础记忆库和 Search-in-the-loop。
