# ArguPaper

面向论文检索与分析的 CLI 工具。

当前 CLI 提供四个主命令：

- `argupaper search "<query>"`：检索论文
- `argupaper convert <local.pdf>`：将本地 PDF 转换为 Markdown 并写入缓存
- `argupaper debate <paper-name>`：基于已缓存 Markdown 运行多 Agent 辩论式论文分析
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

- `MINERU_API_KEY`：运行 `argupaper convert` 或 legacy PDF debate 时必需；按论文名辩论分析已缓存 Markdown 时不需要。
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

### Debate Analysis

`argupaper debate` 的 Support/Skeptic 多 Agent 辩论已使用 LangChain `ChatPromptTemplate` + LCEL Runnable 编排，LLM 接入仍复用现有 `LLM_PROVIDER__DEFAULT__*` 配置，不需要新增 `langchain-openai` 或 OpenAI SDK。

如果默认 LLM provider 未配置、请求失败或返回空内容，debate 会自动降级到确定性规则输出，并在 warnings 中说明降级原因；Search workflow 不受此变更影响。

## 启动与命令速览

### CLI 常用命令

```bash
# 帮助与版本
uv run argupaper --help
uv run argupaper --version

# 外部论文检索
uv run argupaper search "retrieval augmented generation" --limit 10 --source both

# 本地 PDF 转 Markdown，并写入缓存与 PaperStore
uv run argupaper convert ./paper.pdf
uv run argupaper convert --folder ./papers --force

# 查看本地论文库
uv run argupaper papers
uv run argupaper papers --query "retrieval"
uv run argupaper papers <paper_id_or_hash_prefix> --report

# 多 Agent 辩论式论文分析
uv run argupaper debate <paper_id_or_name> --rounds 2 --save-report

# claim 级对抗式论文审查
uv run argupaper court <paper_id> --max-rounds 2

# 本地 RAG
uv run argupaper rag status
uv run argupaper rag index <paper_id>
uv run argupaper rag search "query" --paper-id <paper_id>
uv run argupaper rag delete <paper_id>

# 多轮科研阅读 Chat Agent
uv run argupaper chat
```

简要说明：

- `search`：检索外部学术来源，支持 Semantic Scholar、arXiv 与配置 SerpApi 后的 Google Scholar。
- `convert`：只支持本地 PDF；目录模式只扫描目录直属 PDF，不递归进入子目录。
- `papers`：读取本地 `PAPER_STORAGE_PATH` 中的 PaperStore 记录。
- `debate`：基于已转换或已入库论文运行 Support/Skeptic 多 Agent 分析。
- `court`：抽取论文 claim，绑定证据并生成 challenge、defense、verdict 与人工检查点。
- `rag`：管理本地论文向量索引，依赖 `RAG_ENABLED=true`、Ollama embedding 与 Milvus。
- `chat`：进入 LangGraph Chat Agent，支持 `/papers`、`/use <paper>`、`/debate`、`/court` 和自然语言问答。

### 本地 Web 工作台

启动后端 API：

```bash
uv run uvicorn argupaper.web.app:app --reload --port 8000
```

启动前端开发服务：

```bash
cd frontend
npm install
npm run dev:log
```

打开 `http://127.0.0.1:5173`。Vite 会将 `/api` 代理到 `http://127.0.0.1:8000`。

Web 工作台包含 Search、Convert、Debate、Court、RAG、Chat、Library 页面。默认日志路径：

- 后端：`data/logs/web/web-backend.log`
- 前端：`data/logs/web/web-frontend.log`
- 前端 stdout/stderr：`data/logs/web/web-frontend.out.log`、`data/logs/web/web-frontend.err.log`

## 说明

- `convert` 当前只支持本地 PDF，不支持直接传 URL
- `convert --folder <dir>` 支持目录批量转换，目录短参数为 `-d`；`-f` 仍表示 `--force`
- `debate` 推荐传入已转换论文的原始文件名、文件名 stem 或 cache key；传入本地 PDF 路径仍兼容，但会提示迁移到 `convert -> debate <paper-name>`
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

`argupaper chat` 是面向本地科研阅读的会话型 Agent 入口。它的主体逻辑位于 `argupaper.agents.chat`，使用 LangGraph 构建 Planner + ReAct Tool Loop + Agent State；`debate`、`search`、`papers` 等现有 workflows 只作为可调用 tools 被封装，不承载 chat 主体逻辑。

启动：

```bash
uv run argupaper chat
```

支持命令：

- `/papers`：通过 `PapersWorkflow` tool 列出本地 PaperStore。
- `/use <paper-id-or-name>`：选择当前论文，后续自然语言问题会使用该 selected paper。
- `/debate`：对当前 selected paper 调用多 Agent 辩论式论文分析 tool。
- `/exit`：退出当前 chat 进程。

LLM provider 可用时，自然语言请求会进入 LangGraph Planner + ReAct 工具循环，例如搜索论文、读取当前论文上下文、读取本地 `paper.md` 全文并回答问题。工具返回上下文后，`respond` 节点会基于 observations 生成最终回答；如果 responder LLM 调用失败，则回退为工具摘要。LLM 不可用时，自然语言会降级提示；slash commands 仍可使用。

`debate` / `/debate` 只用于明确的多 Agent 辩论式论文分析请求，例如“使用多 agent 辩论分析此论文”“正反方分析这篇论文”。普通论文解读、摘要、全文解释和问答由 chat 的阅读工具与 `respond` 节点处理。

当用户明确要求“全文 / 完整 / 详细 / 逐节 / 具体内容”时，chat Agent 可调用 `read_paper_fulltext` 读取本地论文全文。CLI 默认不会直接打印完整 markdown，而是返回读取状态、字符数、hash 与本地 `paper.md` 路径。

运行日志写入：

```env
CHAT_LOG_PATH=./data/logs/chat
```

### Chat Tool Extension

`argupaper chat` now builds its LangGraph tool loop from the shared `argupaper.tools` registry. To add future Agent-callable tools, implement and register them under `src/argupaper/tools/`, then include them in `build_default_tool_registry()`. The chat graph keeps conversation state and selected-paper argument injection, while existing workflows remain wrapped as tools.

未配置 `CHAT_LOG_PATH` 时默认写入 `LOG_PATH/chat`。日志为 JSONL 审计记录，包含 state transition、planner decision、tool call、observation、warning、interrupt 和 final response 摘要；`read_paper_fulltext` 的日志会脱敏，不保存原始 `markdown` / `report` 全文；当前不支持从日志恢复对话。
