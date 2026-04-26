# ArguPaper

面向论文检索与分析的 CLI 工具。

当前提供三个主命令：

- `argupaper search "<query>"`：检索论文
- `argupaper analyze <local.pdf>`：分析本地 PDF
- `argupaper papers`：查看本地已保存的论文分析记录

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

### `analyze` 前置配置

当前 `analyze` 依赖远端 MinerU 服务处理 PDF。最少需要关注这些配置：

```env
# analyze 必需
MINERU_API_KEY=your_api_key_here
MINERU_API_ENDPOINT=https://mineru.net/api/v4/extract/task

# 仅在使用非标准 URL 解析 endpoint 时需要
NGROK_URL_BASE=https://your-ngrok-url.ngrok-free.dev

# 本地存储
DATA_PATH=./data
CACHE_PATH=./data/cache
PAPER_STORAGE_PATH=./data/papers
```

说明：

- `MINERU_API_KEY`：必需。
- `MINERU_API_ENDPOINT`：建议使用 MinerU 官方精准解析 API：`https://mineru.net/api/v4/extract/task`。
- `NGROK_URL_BASE`：仅在使用非标准 URL 解析 endpoint 时需要；默认官方 endpoint 会走本地文件签名上传链路，不依赖 ngrok。
- `PAPER_STORAGE_PATH`：本地论文记录保存目录；未配置时默认为 `DATA_PATH/papers`。

### `search` 可选配置

```env
# 配置后可提升 Semantic Scholar 检索能力
SEMANTIC_SCHOLAR_API_KEY=your_api_key_here

# 配置后可使用 SerpApi 的 Google Scholar 检索
SERPAPI_API_KEY=your_serpapi_key_here
```

### 常用可选项

```env
SEARCH_AGENT_TRACE_PATH=./data/agent_runs/search
SEARCH_AGENT_MAX_CANDIDATES=50
DEBATE_MAX_ROUNDS=3
SEARCH_DEFAULT_LIMIT=10
SEARCH_MAX_RESULTS=20
ANALYZE_ENABLE_RETRIEVAL_LOOP=true
```

## 启动

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

分析本地 PDF：

```bash
uv run argupaper analyze ./paper.pdf --output report.md --rounds 2
```

运行前请确认：

- 已配置 `MINERU_API_KEY`
- 已配置 `MINERU_API_ENDPOINT`
- 当前网络可访问 MinerU API 与其返回的签名上传 URL

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

- `analyze` 当前只支持本地 PDF，不支持直接传 URL
- 输出报告会写到 `--output` 指定路径；同时分析结果会落到 `data/` 目录下
- 已保存记录可通过 `argupaper papers` 读取和搜索
- 手工验收入口统一维护在 [docs/SMOKE.md](/E:/Code/Project/ArguPaper/docs/SMOKE.md)

## 已知限制

- 默认 MinerU 官方 endpoint 使用本地文件签名上传；只有切换到非标准 URL 解析 endpoint 时才需要 `NGROK_URL_BASE`。
- `search --source both` 当前支持多源聚合，但去重仍不是严格正确的，在同标题不同论文场景下可能误合并结果。
- `strict_journal` 和 `authoritative_publication` 当前基于 venue 名称做启发式过滤，不保证完整覆盖真实期刊。
- 像 `Nature`、`Science`、`Cell`、`PNAS` 这类不含通用期刊关键词的 venue，当前可能被错误过滤掉。
