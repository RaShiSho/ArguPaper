# CLAUDE.md

## 项目简介

ArguPaper 是一个多智能体科研认知系统，实现论文检索 → 理解 → 证据分析 → 对抗性批判 → 共识生成的全流程。

## 常用命令

```bash
# 虚拟环境（必须激活）
uv venv .venv && source .venv/Scripts/activate  # Windows
uv venv .venv && source .venv/bin/activate       # Linux/Mac

# 安装依赖
uv pip install -e .

# 查看帮助
uv run argupaper --help
```

## 项目结构

```
src/argupaper/
├── agents/        # Agent定义（Support, Skeptic, Comparator, Evidence）
├── chains/        # LangChain Chain（Analysis, Evidence, Critique, Debate）
├── retrieval/     # 检索模块（Semantic Scholar, ArXiv）
├── memory/        # 记忆库（PaperStore, ConversationMemory）
├── pdf/           # PDF处理（MinerUClient, MarkdownCache, Pipeline）
├── extraction/    # 内容提取（结构化提取, Claim对齐检查）
├── judge/         # 裁决层（共识检测）
└── output/        # 输出报告生成
docs/              # 文档
```

## 编码规范

- Python >= 3.11
- 类型提示：所有函数必须有类型注解

## 注意事项

### 虚拟环境

- **必须使用 uv 虚拟环境**
- 所有 python 相关 shell 命令通过 `uv run` 执行
- 使用 `uv` 管理依赖，不使用 pip 直接安装
- 不要读取 .env 文件，仅需通过 .env.example 查看修改项目环境变量

### 版本管理

- 每次进行大型文件更改或功能实现后，自动使用git管理新版本
- git提交记录需要符合规范，采用 `<type>(<scope>): <subject>` 的格式，其中 `<subject>` 用中文编写
- 对于已经实现的功能，请编写简短的介绍文档，存放到 docs/DONE.md 中

### Smoke 验收

- 不再维护 pytest、ruff、mypy 等自动验证体系
- 新增功能、主链路变更或行为修复时，必须同步更新 `docs/SMOKE.md`
- 手工验收步骤统一记录在 `docs/SMOKE.md`，不要把 smoke 表单散落到其他文档
