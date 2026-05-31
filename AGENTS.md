# CLAUDE.md

## 项目简介

ArguPaper 是一个面向个人科研阅读的 Paper Memory & Related Work Agent。

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
├── app/           # 全局配置、依赖构造、异常导出
├── cli/           # Typer CLI 入口、命令模块、Rich/Markdown 输出格式化
├── web/           # FastAPI 本地 Web 工作台入口与 API 路由
├── agents/        # 真正 Agent 与多 Agent 讨论角色（roles/runtime/supervisor）
├── tools/         # 未来 Agent 可调用的工具注册与结构化包装层
├── workflows/     # 固定任务流（analyze/search/convert/papers）
├── pipelines/     # workflow 内部复用阶段（analysis/evidence/debate/report）
├── domain/        # 论文、claim、evidence、related work、verdict 领域逻辑
├── services/      # 底层服务能力（PDF、retrieval、LLM、reporting）
├── memory/        # 记忆库与持久化（PaperStore, ConversationMemory）
└── prompts/       # Prompt 模板与加载器

data/              # 本地运行数据、缓存、转换记录、论文记忆库等持久化数据
docs/              # 项目文档、已完成记录与手工 smoke 验收说明
frontend/          # 本地 Web 工作台前端工程与构建产物
output/            # 报告输出目录；所有 reports 默认输出到此处
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
- 不要随意创建新分支；只有用户明确要求、任务需要隔离大型变更或存在合并风险时，才创建分支，并在完成后及时合并和清理
- 对于已经实现的功能，请编写简短的介绍文档，存放到 docs/DONE.md 中

### Smoke 验收

- 不再维护 pytest、ruff、mypy 等自动验证体系
- 新增功能、主链路变更或行为修复时，必须同步更新 `docs/SMOKE.md`
- 手工验收步骤统一记录在 `docs/SMOKE.md`，不要把 smoke 表单散落到其他文档
