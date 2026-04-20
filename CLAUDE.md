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
uv run pytest

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
```

## 编码规范

- Python >= 3.11
- 类型提示：所有函数必须有类型注解
- 异步：IO密集用 `async/await`
- 异常：使用自定义异常类（`src/argupaper/pdf/exceptions.py`）
- 缓存：计算结果使用缓存键（SHA256）

## 注意事项

- **必须使用 uv 虚拟环境**
- 所有 python 相关 shell 命令通过 `uv run` 执行
- 使用 `uv` 管理依赖，不使用 pip 直接安装
- 不要读取 .env 文件，仅需通过 .env.example 查看修改项目环境变量
