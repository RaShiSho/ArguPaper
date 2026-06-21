
# ArguPaper v0.3 PRD：面向个人科研阅读的多 Agent 论文记忆与关联分析系统

## 1. 产品定位

ArguPaper v0.3 是一个面向个人科研学习与论文阅读的本地化 Research Agent。系统不再以“自动判断论文是否有缺陷”为核心目标，而是帮助用户围绕本地论文库完成论文理解、论文联想、相关工作组织、多轮问答和多 Agent 研究讨论。

一句话定位：

> ArguPaper 是一个具有本地论文记忆、多轮对话、工具调用和多 Agent 研究讨论能力的个人科研阅读助手。

## 2. 目标用户

主要用户为本科生、研究生、科研入门者和需要长期阅读论文的个人开发者。

典型痛点：

* 读完论文后难以和之前读过的论文建立联系
* 不清楚当前论文属于哪条研究路线
* 难以快速比较两篇论文的方法、任务、实验和贡献
* 缺少一个可以围绕本地论文库持续追问的科研对话系统
* 希望保留一定的多 Agent 前沿性，但不希望系统过度宣称自动审稿能力

## 3. 设计原则

### 3.1 从“论文裁判”转向“科研阅读助手”

系统不直接断言论文质量好坏，而是输出“可能需要人工检查的问题”“与本地论文的相似点/差异点”“推荐继续阅读的方向”。

### 3.2 从“一次性命令”升级为“多轮 Research Agent”

保留 CLI 命令，同时新增对话式入口。Agent 需要维护当前论文、当前研究主题、最近检索结果、用户追问历史和本地论文库上下文。

### 3.3 多 Agent 辩论保留，但用途调整

原有 Debate 不再用于强行判断论文缺陷，而是用于多视角研究讨论，例如：

* 当前论文的贡献如何理解
* 它和本地论文库中哪些论文相关
* 它可能属于哪条研究路线
* 哪些问题需要继续查证或人工判断

## 4. 核心功能

### 4.1 Paper Memory：本地论文记忆库

系统保存用户已转换和已分析的论文，并结构化存储以下信息：

* 标题
* 摘要
* 关键词
* 研究问题
* 方法
* 数据集
* baseline
* claim
* evidence
* 本地 Markdown 内容
* 分析报告
* 向量索引信息

目标是支持跨论文检索、跨论文比较和多轮对话中的记忆调用。

### 4.2 Research Chat：多轮科研对话入口

新增 `argupaper chat` 和 Web Chat 页面。

Agent 支持用户用自然语言发起任务，例如：

```bash
argupaper chat
```

示例问题：

```text
这篇论文和我之前读过的 speculative decoding 论文有什么关系？
帮我找本地论文库中和这篇论文最像的 5 篇论文。
这篇论文可以放进哪条研究路线？
把这几篇论文组织成一个课程汇报思路。
```

Chat Agent 需要具备：

* 当前论文状态管理
* 用户意图识别
* 工具调用
* 本地论文库检索
* 多轮上下文记忆
* 回答中的证据引用
* 必要时向用户追问

### 4.3 Relate：本地论文联想

新增命令：

```bash
argupaper relate <paper-name>
```

功能：

* 根据当前论文的标题、摘要、方法、关键词、claim，从本地论文库中检索相关论文
* 输出相关论文 Top-K
* 解释相关原因
* 判断它们之间是方法相似、任务相似、应用相似、引用相关，还是研究路线相关

输出结构：

```text
1. 当前论文核心主题
2. 本地相关论文 Top-K
3. 每篇论文的关联原因
4. 共同研究问题
5. 方法差异
6. 推荐下一篇阅读论文
```

### 4.4 Compare：论文比较

新增命令：

```bash
argupaper compare <paper-a> <paper-b>
```

功能：

* 比较两篇论文的任务、方法、实验、数据集、baseline、贡献点
* 输出相同点、不同点和适合写入 related work 的总结
* 避免直接判断优劣，除非有明确证据支持

输出结构：

```text
1. 研究问题对比
2. 方法对比
3. 实验设置对比
4. 数据集与指标对比
5. 贡献差异
6. 适合写入综述的比较段落
```

### 4.5 Research Discussion：多 Agent 研究讨论

保留原有多 Agent Debate，但改造成研究讨论功能。

Agent 角色：

#### Supervisor Agent

负责理解用户意图、选择工具、组织多 Agent 协作流程。

#### Paper Reader Agent

负责解释当前论文的研究问题、方法、实验和结论。

#### Memory Retriever Agent

负责从本地论文库中检索相关论文。

#### Comparator Agent

负责比较当前论文与本地相关论文的相似点和差异点。

#### Skeptic Agent

负责提出需要谨慎理解或人工检查的问题，例如是否缺少 ablation、baseline 是否需要进一步确认。

#### Evidence Agent

负责检查回答是否能追溯到论文原文、本地论文库或检索结果。

#### Judge Agent

负责整合多 Agent 观点，输出共识、分歧和建议下一步。

### 4.6 Checkpoints：人工检查点提示

系统不直接给出“论文有缺陷”的结论，而是输出检查点：

```text
系统未在当前解析内容中发现明显的 ablation study，建议人工检查实验章节。
系统发现当前论文与本地论文 A/B 在方法设计上相似，建议进一步比较二者贡献差异。
系统未发现明显的 baseline 对比信息，建议确认实验表格是否完整解析。
```

该功能作为辅助阅读提示，不作为自动审稿判断。

## 5. 非目标

v0.3 暂不追求：

* 自动判断论文是否一定存在缺陷
* 自动预测论文是否应该被接收
* 构建复杂知识图谱可视化
* 完整替代人工审稿
* 大规模训练专用模型
* 复杂云端多用户系统

## 6. CLI 设计

保留已有命令：

```bash
argupaper convert <paper.pdf>
argupaper analyze <paper-name>
argupaper search <query>
argupaper papers
```

新增命令：

```bash
argupaper chat
argupaper relate <paper-name>
argupaper compare <paper-a> <paper-b>
argupaper discuss <paper-name>
```

命令含义：

* `chat`：进入多轮科研对话
* `relate`：从本地论文库中寻找相关论文
* `compare`：比较两篇论文
* `discuss`：触发多 Agent 研究讨论

## 7. Web 工作台设计

Web 工作台保留 Search、Analyze、Library 页面，新增：

### Chat 页面

用于多轮科研对话。

### Related 页面

展示当前论文与本地论文库的关联结果。

### Compare 页面

展示两篇论文的结构化对比。

### Discussion 页面

展示多 Agent 讨论过程，包括不同 Agent 的观点、证据和最终 Judge 总结。

## 8. 技术架构

```text
User CLI / Web Chat
        ↓
Research Supervisor Agent
        ↓
Intent Router
        ↓
Tool Planner
        ↓
Tool Executor
        ↓
PaperStore / Vector Search / Analyze / Relate / Compare
        ↓
Multi-Agent Discussion
        ↓
Answer Synthesizer
        ↓
Memory Writer
```

## 9. MVP 优先级

### P0：必须完成

* 本地论文库 embedding 检索
* `argupaper relate <paper-name>`
* `argupaper compare <paper-a> <paper-b>`
* 基础 `argupaper chat`
* 会话状态管理：current paper、last analysis、last retrieved papers
* 回答中区分“原文证据”“本地库推断”“需要人工确认”

### P1：建议完成

* Research Discussion 多 Agent 编排
* Supervisor Agent 调度多个专门 Agent
* Related Work Map 输出
* Web Chat 页面
* Web Related 页面
* 本地论文推荐下一读

### P2：后续扩展

* 研究路线图
* 引用关系图谱
* 基于公开数据集的自动评估
* 更强的 Evidence QA
* 多篇论文综述草稿生成

## 10. 输出格式

### Relate 输出

```text
1. 当前论文核心摘要
2. 本地相关论文 Top-K
3. 关联类型
4. 相似点
5. 差异点
6. 推荐阅读顺序
```

### Compare 输出

```text
1. 任务对比
2. 方法对比
3. 实验对比
4. 贡献对比
5. 适合写入 related work 的总结
```

### Discussion 输出

```text
1. Paper Reader 观点
2. Comparator 观点
3. Skeptic 检查点
4. Evidence 支撑情况
5. Judge 共识
6. 下一步建议
```

## 11. 验收标准

v0.3 MVP 完成后，系统应满足：

* 用户可以把多篇论文加入本地库
* 用户可以选择一篇论文并检索本地相关论文
* 用户可以比较两篇本地论文
* 用户可以围绕当前论文进行多轮对话
* Agent 能根据上下文自动调用 analyze、relate、compare、papers 等工具
* 多 Agent 讨论能输出不同视角，而不是单一总结
* 系统不会把“未找到证据”误写成“论文一定有缺陷”
* 所有推断性结论都应标注为“建议人工检查”或“需要进一步确认”

## 12. 一句话总结

ArguPaper v0.3 不再是一个试图自动审稿的论文批判系统，而是一个面向个人科研阅读的多 Agent 论文记忆与关联分析系统。它通过本地论文库、多轮对话、工具调用和多 Agent 研究讨论，帮助用户把读过的论文连接成可理解、可追问、可复用的研究脉络。

