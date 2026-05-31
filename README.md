# ArguPaper

面向论文检索与分析的 CLI 工具。

当前 CLI 提供四个主命令：

- `argupaper search "<query>"`：检索论文
- `argupaper convert <local.pdf>`：将本地 PDF 转换为 Markdown 并写入缓存
- `argupaper analyze <paper-name>`：基于已缓存 Markdown 分析论文
- `argupaper papers`：查看本地已保存的论文分析记录

同时新增本地 React 工作台，可视化使用上述能力。

## 环境要求

- Python `>=3.11`

## 安装

推荐使用 `uv`：

```bash
uv sync
```

或使用 `pip`：

```bash
pip install -e .
```

## 配置

复制环境变量模板：

```bash
cp .env.example .env
```

### `convert` 前置配置

当前 PDF 转 Markdown 依赖远端 MinerU 服务。最少需要关注这些配置：

```env
# convert 必需
MINERU_API_KEY=your_api_key_here
MINERU_API_ENDPOINT=https://mineru.net/api/v4/extract/task

# 仅在使用非标准 URL 解析 endpoint 时需要
NGROK_URL_BASE=https://your-ngrok-url.ngrok-free.dev

# 本地存储
DATA_PATH=./data
CACHE_PATH=./data/cache
PAPER_STORAGE_PATH=./data/papers
LOG_PATH=./data/logs
```

说明：

- `MINERU_API_KEY`：运行 `argupaper convert` 或 legacy PDF analyze 时必需；按论文名分析已缓存 Markdown 时不需要。
- `MINERU_API_ENDPOINT`：建议使用 MinerU 官方精准解析 API：`https://mineru.net/api/v4/extract/task`。
- `NGROK_URL_BASE`：仅在使用非标准 URL 解析 endpoint 时需要；默认官方 endpoint 会走本地文件签名上传链路，不依赖 ngrok。
- `PAPER_STORAGE_PATH`：本地论文记录保存目录；未配置时默认为 `DATA_PATH/papers`。
- `LOG_PATH`：运行日志根目录；未配置时默认为 `DATA_PATH/logs`，内部按 `search`、`convert`、`web` 区分。

### `search` 可选配置

```env
# 配置后可提升 Semantic Scholar 检索能力
SEMANTIC_SCHOLAR_API_KEY=your_api_key_here

# 配置后可使用 SerpApi 的 Google Scholar 检索
SERPAPI_API_KEY=your_serpapi_key_here
```

### 常用可选项

```env
SEARCH_WORKFLOW_MAX_CANDIDATES=50
DEBATE_MAX_ROUNDS=3
SEARCH_DEFAULT_LIMIT=10
SEARCH_MAX_RESULTS=20
ANALYZE_ENABLE_RETRIEVAL_LOOP=true
```

### Analyze Debate

`argupaper analyze` 的 Support/Skeptic debate 已使用 LangChain `ChatPromptTemplate` + LCEL Runnable 编排，LLM 接入仍复用现有 `LLM_PROVIDER__DEFAULT__*` 配置，不需要新增 `langchain-openai` 或 OpenAI SDK。

如果默认 LLM provider 未配置、请求失败或返回空内容，debate 会自动降级到确定性规则输出，并在 analyze warnings 中说明降级原因；Search workflow 不受此变更影响。

## 启动

### 本地 Web 工作台

后端 API：

```bash
uv run uvicorn argupaper.web.app:app --reload --port 8000
```

后端文件日志会写入 `LOG_PATH/web/web-backend.log`，默认路径为 `data/logs/web/web-backend.log`。

前端开发服务：

```bash
cd frontend
npm install
npm run dev:log
```

前端开发服务的 stdout/stderr 会写入 `LOG_PATH/web/web-frontend.log`、`LOG_PATH/web/web-frontend.out.log` 与 `LOG_PATH/web/web-frontend.err.log`。

打开 `http://127.0.0.1:5173`。Vite 已将 `/api` 代理到 `http://127.0.0.1:8000`。

工作台当前包含：

- Search：调用现有 Search / Retrieval workflow，展示结果、warning 与 trace。
- Analyze：上传本地 PDF，创建后台分析任务，并轮询展示进度、warning 与 Markdown 报告。
- Library：读取 `PAPER_STORAGE_PATH` 下的本地 PaperStore 历史记录，展示结构化摘要、报告和论文 Markdown。

### CLI

查看帮助：

```bash
uv run argupaper --help
```

检索论文：

```bash
uv run argupaper search "retrieval augmented generation" --limit 10 --source both
```

说明：

- `--source both` 当前会聚合多个来源的结果并排序返回。
- `--source google_scholar` 或 `--source serpapi` 会通过 SerpApi 调用 Google Scholar。
- 配置 `SERPAPI_API_KEY` 后，`--source both` 会自动加入 Google Scholar；当 `--source semantic_scholar` 遇到 403/429 且已配置 SerpApi 时，会回退到 Google Scholar。
- 但当前去重逻辑仍存在已知限制：在同标题但实际不是同一篇论文的场景下，可能发生误合并。

转换本地 PDF：

```bash
uv run argupaper convert ./paper.pdf
uv run argupaper convert ./paper.pdf --output ./paper.md
```

批量转换目录中的 PDF：

```bash
uv run argupaper convert --folder ./papers
uv run argupaper convert -d ./papers --force
```

说明：

- `--folder/-d` 只扫描目录直属条目，不递归进入子目录。
- 目录模式会跳过非 PDF 文件、子目录或不可读条目，并继续处理后续 PDF。
- 目录模式不支持 `--output`；转换结果默认写入现有 `data/cache` Markdown 缓存。
- 每次目录转换会在 `data/logs/convert/<run-id>.jsonl` 写入执行日志，记录成功、缓存命中、失败、跳过和最终汇总。

基于已转换 Markdown 分析论文：

```bash
uv run argupaper analyze "paper" --output 1.md --rounds 2
```

自动按论文文件名保存报告：

```bash
uv run argupaper analyze "paper" --save-report
```

运行前请确认：

- 先执行过 `argupaper convert ./paper.pdf`，使 `data/cache` 中存在对应 Markdown 与 metadata
- 只有执行 `convert` 或 legacy PDF analyze 时才需要配置 `MINERU_API_KEY` 与 `MINERU_API_ENDPOINT`
- 执行 `convert` 时当前网络可访问 MinerU API 与其返回的签名上传 URL

查看本地历史记录：

```bash
uv run argupaper papers
uv run argupaper papers --query "retrieval"
uv run argupaper papers <paper_id_or_hash_prefix> --report
```

说明：

- `papers` 默认读取 `PAPER_STORAGE_PATH` 下的本地记录。
- `paper_id` 支持完整 ID 或唯一 hash 前缀。
- `--report` 会渲染保存的 Markdown 报告；`--markdown` 会渲染缓存的论文 Markdown。

查看版本：

```bash
uv run argupaper --version
```

## 说明

- `convert` 当前只支持本地 PDF，不支持直接传 URL
- `convert --folder <dir>` 支持目录批量转换，目录短参数为 `-d`；`-f` 仍表示 `--force`
- `analyze` 推荐传入已转换论文的原始文件名、文件名 stem 或 cache key；传入本地 PDF 路径仍兼容，但会提示迁移到 `convert -> analyze <paper-name>`
- Web 工作台同样只支持上传本地 PDF，不支持 URL PDF
- `--output 1.md` 这类裸文件名会自动保存到 `output/1.md`；显式目录或绝对路径会按用户传入路径保存
- `--save-report` 会在未指定 `--output` 时自动保存到 `output/<论文文件名>.md`
- 分析结果会同时落到 `data/` 目录下
- 已保存记录可通过 `argupaper papers` 读取和搜索
- 手工验收入口统一维护在 [docs/SMOKE.md](/E:/Code/Project/ArguPaper/docs/SMOKE.md)

## 已知限制

- 默认 MinerU 官方 endpoint 使用本地文件签名上传；只有切换到非标准 URL 解析 endpoint 时才需要 `NGROK_URL_BASE`。
- `search --source both` 当前支持多源聚合，但去重仍不是严格正确的，在同标题不同论文场景下可能误合并结果。
- `strict_journal` 和 `authoritative_publication` 当前基于 venue 名称做启发式过滤，不保证完整覆盖真实期刊。
- 像 `Nature`、`Science`、`Cell`、`PNAS` 这类不含通用期刊关键词的 venue，当前可能被错误过滤掉。

## Chat Agent Runtime

`argupaper chat` 是面向本地科研阅读的会话型 Agent 入口。它的主体逻辑位于 `argupaper.agents.chat`，使用 LangGraph 构建 Planner + ReAct Tool Loop + Agent State；`analyze`、`search`、`papers` 等现有 workflows 只作为可调用 tools 被封装，不承载 chat 主体逻辑。

启动：

```bash
uv run argupaper chat
```

支持命令：

- `/papers`：通过 `PapersWorkflow` tool 列出本地 PaperStore。
- `/use <paper-id-or-name>`：选择当前论文，后续自然语言问题会使用该 selected paper。
- `/analyze`：对当前 selected paper 调用 `AnalyzeWorkflow` tool。
- `/exit`：退出当前 chat 进程。

LLM provider 可用时，自然语言请求会进入 LangGraph Planner + ReAct 工具循环，例如搜索论文、读取当前论文上下文并回答问题。LLM 不可用时，自然语言会降级提示；slash commands 仍可使用。

运行日志写入：

```env
CHAT_LOG_PATH=./data/logs/chat
```

未配置 `CHAT_LOG_PATH` 时默认写入 `LOG_PATH/chat`。日志为 JSONL 审计记录，包含 state transition、planner decision、tool call、observation、warning、interrupt 和 final response 摘要；当前不支持从日志恢复对话。
