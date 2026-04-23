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

# 运行测试
uv run pytest --basetemp=.pytest/tmp -o cache_dir=.pytest/cache

# 代码检查
uv run ruff check src/
uv run mypy src/
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
tests/             # 测试相关代码
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


### 测试

- 所有测试相关的缓存、临时目录、手工工作区统一放在 `.pytest/` 下
- pytest 缓存目录固定使用 `.pytest/cache`
- pytest 临时目录固定使用 `.pytest/tmp`
- 手工创建的测试工作区固定使用 `.pytest/workspace`
- 禁止在仓库根目录创建 `test_workspace`、`.test_workspace`、`.pytest_temp_run` 或其他散落的测试临时目录
- 运行 pytest 时，默认使用 `uv run pytest --basetemp=.pytest/tmp -o cache_dir=.pytest/cache`
- 编写测试时，优先使用 `tmp_path`；如果必须手动创建目录，必须显式放到 `.pytest/workspace` 下
