# SMOKE

本文件是项目唯一的手工 smoke 验收入口。

规则：

- 新增功能、主链路变更或行为修复时，必须同步更新本文件
- smoke 表单统一写在这里，不要散落到 `AGENTS.md`、`README.md` 或其他文档
- 所有 Python 相关命令默认通过 `uv run` 执行

## 表单模板

每条 smoke 项按以下字段维护：

- 功能名称
- 适用场景
- 前置条件
- 执行命令
- 预期结果
- 记录

## 当前 Smoke 表单

### 1. CLI 基础可用性

- 功能名称：CLI 基础可用性
- 适用场景：确认命令入口安装正常，可在开发环境执行
- 前置条件：已执行 `uv sync`
- 执行命令：`uv run argupaper --version`
- 预期结果：终端输出当前版本号，不报导入错误或命令不存在
- 记录：____

### 2. 单源检索

- 功能名称：Semantic Scholar 单源检索
- 适用场景：验证基础检索链路可用
- 前置条件：网络可访问；如需更稳定结果，可配置 `SEMANTIC_SCHOLAR_API_KEY`
- 执行命令：`uv run argupaper search "retrieval augmented generation" --limit 5 --source semantic_scholar`
- 预期结果：返回非空论文列表，至少包含标题、年份、来源或 URL 等基础字段
- 记录：____

### 3. 双源聚合检索

- 功能名称：双源聚合检索
- 适用场景：验证多源聚合路径仍可执行
- 前置条件：网络可访问；如需更稳定结果，可配置 `SEMANTIC_SCHOLAR_API_KEY`
- 执行命令：`uv run argupaper search "retrieval augmented generation" --limit 5 --source both`
- 预期结果：命令成功返回聚合结果，不因单一来源失败直接崩溃
- 记录：____

### 3.1 相对时间解析

- 功能名称：相对时间解析
- 适用场景：验证搜索请求中的相对年份表达会按当前日期归一化
- 前置条件：当前本地日期可获取
- 执行命令：`uv run argupaper search "近一年 的 retrieval augmented generation 论文" --limit 5 --source both --verbose`
- 预期结果：解析结果中的年份范围应与当前年份一致；例如当前日期为 2026-04-25 时，`近一年` 应解析为 `year_from=2025`、`year_to=2026`
- 记录：____

### 4. 本地 PDF 分析主链路

- 功能名称：本地 PDF 分析
- 适用场景：验证 `analyze` 主链路可生成报告
- 前置条件：已配置 `MINERU_API_KEY`、`MINERU_API_ENDPOINT`；若分析未缓存 PDF，还需配置 `NGROK_URL_BASE` 或其他可公开访问本地 PDF 的地址；准备一个本地 PDF 文件
- 执行命令：`uv run argupaper analyze ./paper.pdf --output report.md --rounds 2`
- 预期结果：成功生成 Markdown 报告；报告中应能看到与当前轮数一致的 debate 输出；若外部服务异常，应给出可见错误或 warning，而不是静默失败；`Disagreement` 不应出现明显正向结论
- 记录：____

### 4.1 Claim-Evidence 对齐

- 功能名称：Claim-Evidence 对齐与证据充分性检查
- 适用场景：验证 evidence 链路可识别 claim 支撑、baseline、ablation 与缺失项
- 前置条件：已执行 `uv sync`
- 执行命令：

```powershell
@'
import asyncio
from argupaper.chains.evidence import EvidenceChain

markdown = """# Demo Paper

## Abstract
We propose a robust retrieval model that improves accuracy on benchmark tasks.

## Evaluation
We compare against a baseline on CIFAR-10 and report accuracy and f1.
Ablation variants remove the reranker component.
"""

async def main():
    result = await EvidenceChain().run(markdown)
    print(result["has_baseline"], result["has_ablation"])
    print(result["unsupported_claims"])
    print(result["missing_analyses"])

asyncio.run(main())
'@ | uv run python -
```

- 预期结果：第一行输出 `True True`；`unsupported_claims` 为空列表；`missing_analyses` 为空列表
- 记录：____

### 5. 本地论文历史记录读取

- 功能名称：PaperStore 历史记录读取
- 适用场景：验证 `argupaper papers` 可列出、搜索并按 paper id/hash 前缀读取本地记录
- 前置条件：已执行 `uv sync`
- 执行命令：

```powershell
$env:DATA_PATH = Join-Path $env:TEMP "argupaper-paper-store-smoke"
$paperDir = Join-Path $env:DATA_PATH "papers/demo-paper-123"
New-Item -ItemType Directory -Force $paperDir | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText((Join-Path $paperDir "metadata.json"), '{"paper_id":"demo-paper-123","title":"Demo Paper","source":"smoke","from_cache":false}', $utf8)
[System.IO.File]::WriteAllText((Join-Path $paperDir "abstract.json"), '{"problem":"Demo problem","method":"Demo method","experiment":"Demo experiment","conclusion":"Demo conclusion"}', $utf8)
[System.IO.File]::WriteAllText((Join-Path $paperDir "report.md"), "# Demo Report", $utf8)
[System.IO.File]::WriteAllText((Join-Path $paperDir "paper.md"), "# Demo Paper Markdown", $utf8)

uv run argupaper papers --query Demo
uv run argupaper papers demo-paper --report

Remove-Item -Recurse -Force $env:DATA_PATH
Remove-Item Env:DATA_PATH
```

- 预期结果：第一次命令显示包含 `demo-paper-123` 与 `Demo Paper` 的 Saved Papers 表格；第二次命令显示 Saved Paper 摘要与 `Demo Report`
- 记录：____
