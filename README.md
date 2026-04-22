# ArguPaper

面向论文检索与分析的 CLI 工具。

当前提供两个主命令：

- `argupaper search "<query>"`：检索论文
- `argupaper analyze <local.pdf>`：分析本地 PDF

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

最少需要关注这些配置：

```env
# analyze 必需
MINERU_API_KEY=your_api_key_here

# search 可选；配置后可提升 Semantic Scholar 检索能力
SEMANTIC_SCHOLAR_API_KEY=your_api_key_here

# 本地存储
DATA_PATH=./data
CACHE_PATH=./data/cache

# 可选：当 MinerU 需要回调本地 PDF 服务时使用
NGROK_URL_BASE=https://your-ngrok-url.ngrok-free.dev
```

常用可选项：

```env
DEBATE_MAX_ROUNDS=3
SEARCH_DEFAULT_LIMIT=10
SEARCH_MAX_RESULTS=20
ANALYZE_ENABLE_RETRIEVAL_LOOP=true
```

## 启动

查看帮助：

```bash
argupaper --help
```

检索论文：

```bash
argupaper search "retrieval augmented generation" --limit 10 --source both
```

分析本地 PDF：

```bash
argupaper analyze ./paper.pdf --output report.md --rounds 2
```

查看版本：

```bash
argupaper --version
```

## 说明

- `analyze` 当前只支持本地 PDF，不支持直接传 URL
- 输出报告会写到 `--output` 指定路径；同时分析结果会落到 `data/` 目录下
