
# **ArguPaper — 产品需求文档（增强版 PRD v0.2）**

---

## 一、产品定位

**ArguPaper** 是一个基于多智能体（Multi-Agent）的科研认知系统，提供从**论文检索 → 理解 → 证据分析 → 对抗性批判 → 共识生成**的一站式服务，并通过动态检索与知识结构化实现接近真实科研过程的分析能力。

---

## 二、核心功能模块（按流程划分）

---

## 1. 论文检索模块（Paper Retrieval）

### 功能描述（升级）

系统根据用户需求自动生成多组语义关键词，并通过多轮检索 + 分析驱动检索（Search-in-the-loop）机制，实现**检索与推理耦合**。

> 现有系统普遍存在“分析脱离外部证据”的问题 ([arXiv][1])
> 本系统引入动态检索以弥补该缺陷

---

### 子功能设计（增强）

### 1️⃣ 关键词生成（Query Expansion）

* 语义扩展（同义词 / 上下位 / 方法 / 数据集）
* 研究问题拆解驱动关键词生成

---

### 2️⃣ 多轮搜索机制（Iterative Search）

* 多策略检索（exploration / exploitation）
* 支持动态调整搜索策略

---

### 3️⃣ 🔄 分析驱动检索（Search-in-the-loop）【新增核心】

在后续分析过程中，Agent可触发新的检索行为：

* 自动补充：

  * baseline论文
  * 对比方法
  * 冲突研究
* 支持“验证式检索”（verification search）

👉 对标 ScholarPeer 的 active verification 思路 ([arXiv][2])

---

### 4️⃣ 论文质量排序（Quality Ranking）

* 基于：

  * 期刊等级（CCF）
  * citation
  * 方法新颖性（可扩展）

---

### 5️⃣ 渐进式筛选机制（Progressive Filtering）

* 标题过滤 → 摘要过滤 → 初步结构理解
* 输出候选论文列表

---

## 2. 论文简读模块（Paper Skimming）

#### 功能描述

对论文进行快速理解，帮助用户在短时间内掌握核心内容，并支持基础问答。

#### 子功能设计

* **结构化摘要生成**

  * 研究问题（Problem）
  * 方法（Method）
  * 数据集与实验（Experiment）
  * 结论（Conclusion）

* **轻量问答系统**

  * 回答用户对论文的基础问题
  * 限制为“非深度推理”级别问题

---

## 3. 论文精讲模块（Deep Analysis & Critique）

#### 功能描述（核心差异点）

基于多智能体协作，对论文进行**深入解析 + 批判性分析**，形成具有研究价值的输出。


## Agent分层设计（增强版）

---

### （1）分析层（Analysis Layer）

* 提供系统性知识总结：

  * 方法原理拆解
  * 技术路线分析
  * 实验设计解析
* 输出结构化分析报告

---

### （2）证据层（Evidence Layer）【新增】

👉 用于解决“表层批判”问题

> 当前系统常停留在浅层总结，难以评估方法可靠性 ([arXiv][2])

---

#### 核心能力：

* 实验信息抽取：

  * 数据集
  * 样本量
  * 指标
* 方法条件分析：

  * 适用范围
  * 假设条件
* 结果可信度分析：

  * 是否有统计支撑
  * 是否存在过拟合风险

---

### （3）批判层（Critique Layer）【强化】

#### 新增能力：

* **证据一致性校验**

  * claim ↔ experiment 对齐检查
* **方法有效性分析**

  * 是否合理 / 是否过度简化
* **实验充分性分析**

  * 是否缺 baseline / ablation

---

### （4）⚔️ 对抗层（Debate Layer）【核心新增】

👉 解决“单路径推理”问题

---

#### Agent角色：

* **Support Agent（支持）**

  * 为论文辩护
* **Skeptic Agent（质疑）**

  * 挖掘漏洞
* **Comparator Agent**

  * 引入对比论文
* **Evidence Agent**

  * 提供证据支持

---

#### 机制：

```text
Round 1：提出观点
Round 2：互相反驳
Round 3：证据补充（触发检索）
Round N：收敛或继续争论
```

👉 实践表明，多Agent争论显著提升分析质量 ([Reddit][3])

---

### （5）裁决层（Judge Layer）【新增】

#### 功能：

* 汇总多Agent结论
* 输出：

```text
共识（Consensus）
分歧（Disagreement）
支持证据
```

---

## 🔄 迭代机制（升级）

```text
Analysis
  ↓
Evidence Extraction
  ↓
Debate（多轮）
  ↓
Search-in-loop（补充证据）
  ↓
Judge（裁决）
```

---

## 三、系统级能力设计（SPECIAL）

---

### 1. 全局论文记忆库（升级）

#### 设计特点

区别于传统对话记忆，该模块为**结构化长期知识存储系统**

#### 分层存储机制（渐进式披露）

* Level 1：论文标题
* Level 2：摘要（Abstract）
* Level 3：全文（Markdown格式）

#### 功能能力

* 支持跨任务复用
* 支持语义检索
* 支持知识关联（为图谱提供基础）

## 🔥 新增：结构化知识层

不仅存储文本，还存储：

* Claim（结论）
* Method（方法）
* Evidence（证据）

---

### 支持能力：

* 跨论文推理
* 冲突检测
* 证据复用

---

### 2. PDF → Markdown 转换（保持）

* 使用专用API将论文PDF转为Markdown
* PDF本地存储（用于溯源）
* Markdown用于Agent解析与上下文输入

---

### 3. 异步分析机制（保持）

#### 设计目标

提升用户体验与系统吞吐效率

#### 实现方式

* 优先返回：
  * 分析层结果（快速）
* 延迟返回：
  * 批判层结果（较慢）
* UI层分区展示结果

---

### 4. 原文优先机制（保持）

* 在Agent上下文中提升论文原文权重
* 降低幻觉风险
* 强化基于证据的分析

---

## 🔄 5. 动态检索引擎（新增）

与所有Agent耦合：

* Analysis阶段 → 检索baseline
* Debate阶段 → 检索反例
* Critique阶段 → 检索证据

---

## 四、输出设计（升级）

---

## 🚨 从“文本输出” → “科研决策输出”

---

### 输出结构：

```text
1. Research Overview
2. Method Comparison
3. Evidence Table
4. Debate Summary（新增）
5. Contradictions
6. Weakness Analysis
7. Consensus vs Disagreement（新增）
8. Confidence Score（新增）
```

---

### 🧠 置信度建模（新增）

```text
结论A：支持度 78%
结论B：支持度 42%
冲突强度：高
```

👉 多Agent评估优于单Agent评估 ([arXiv][4])

---

## 五、扩展功能（BONUS）

### 1. 知识图谱（Knowledge Graph）

* 构建论文之间的引用与语义关联
* 可视化用户研究路径
* 支持论文推荐与关联发现

---

### 2. 引用论文跟踪

* 自动提取论文中的关键引用
* 存入记忆库“临时分区”
* 支持快速扩展阅读

---

### 3. 无关请求过滤（成本控制）

* 使用轻量模型进行意图分类
* 对非学术请求拒绝调用高成本模型

---

### 4. 多轮自优化机制

* 分析层与批判层循环优化结果
* 提升最终输出质量

---

## 六、功能优先级排序（更新）

---

### 🔴 P0（MVP必须）

* 检索模块 + Search-in-loop
* 简读模块
* Analysis + Evidence Layer
* 简单Debate（2 Agent）
* PDF解析
* 基础记忆库

---

### 🟡 P1

* 完整Debate系统（多Agent）
* Judge层
* 置信度系统
* 动态检索引擎

---

### 🟢 P2

* 知识图谱推理
* 多轮优化
* 引用扩展

---

## 七、关键差异总结（增强版）

---

### 与现有系统的本质差异：

| 维度   | 传统系统 | ArguPaper              |
| ---- | ---- | ---------------------- |
| 批判能力 | 表层总结 | **证据驱动批判**             |
| 推理方式 | 单路径  | **多Agent对抗推理**         |
| 检索机制 | 静态   | **Search-in-the-loop** |
| 输出   | 文本   | **决策+置信度**             |

---

### 一句话总结：

👉 不是“论文总结工具”
👉 而是：**模拟科研团队思考过程的认知系统**

[1]: https://arxiv.org/abs/2603.14629?utm_source=chatgpt.com "ResearchPilot: A Local-First Multi-Agent System for Literature Synthesis and Related Work Drafting"
[2]: https://arxiv.org/abs/2601.22638?utm_source=chatgpt.com "ScholarPeer: A Context-Aware Multi-Agent Framework for Automated Peer Review"
[3]: https://www.reddit.com/r/OpenAI/comments/1scf91j/i_used_a_structured_multiagent_workflow_to/?utm_source=chatgpt.com "I used a structured multi-agent workflow to generate a 50+ page research critique"
[4]: https://arxiv.org/abs/2410.15287?utm_source=chatgpt.com "Training Language Models to Critique With Multi-agent Feedback"
