# SMOKE

本文件是项目唯一的手工 smoke 验收入口。

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
- 前置条件：已配置 `MINERU_API_KEY`、`MINERU_API_ENDPOINT=https://mineru.net/api/v4/extract/task`；当前网络可访问 MinerU API 与其返回的签名上传 / 下载地址；准备一个本地 PDF 文件
- 执行命令：`uv run argupaper analyze ./paper.pdf --output 1.md --rounds 2`
- 预期结果：成功生成 Markdown 报告，裸文件名输出自动保存到 `output/1.md`；报告中应能看到与当前轮数一致的 debate 输出；若外部服务异常，应给出可见错误或 warning，而不是静默失败；`Disagreement` 不应出现明显正向结论
- 记录：____

### 4.1 Analyze 自动报告保存

- 功能名称：Analyze 自动报告保存
- 适用场景：验证未显式传入 `--output` 时，可按论文文件名自动保存报告
- 前置条件：已配置 `MINERU_API_KEY`、`MINERU_API_ENDPOINT=https://mineru.net/api/v4/extract/task`；准备一个本地 PDF 文件
- 执行命令：`uv run argupaper analyze ./paper.pdf --save-report`
- 预期结果：成功生成 Markdown 报告，并自动保存到 `output/paper.md`
- 记录：____

### 4.2 Claim-Evidence 对齐

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

### 6. CLI 错误处理

- 功能名称：用户可读错误面板
- 适用场景：验证 CLI 参数错误会显示明确错误类型与下一步提示
- 前置条件：已执行 `uv sync`
- 执行命令：

```powershell
$tmp = Join-Path $env:TEMP "argupaper-not-pdf.txt"
"not a pdf" | Set-Content -Encoding UTF8 $tmp
uv run argupaper analyze $tmp
if ($LASTEXITCODE -ne 1) { throw "Expected analyze to fail with exit code 1." }
Remove-Item -Force $tmp
```

- 预期结果：命令以退出码 `1` 失败；错误面板包含 `InputValidationError`、`Input must be a .pdf file.` 与 `Next step`
- 记录：____

### 7. 配置项读取

- 功能名称：环境变量模板与配置读取一致性
- 适用场景：验证 `PAPER_STORAGE_PATH` 与检索配置项会被 `load_config()` 读取
- 前置条件：已执行 `uv sync`
- 执行命令：

```powershell
$env:PAPER_STORAGE_PATH = Join-Path $env:TEMP "argupaper-config-paper-store"
$env:SEARCH_DEFAULT_LIMIT = "7"
$env:SEARCH_MAX_RESULTS = "13"
$env:ANALYZE_ENABLE_RETRIEVAL_LOOP = "false"
uv run python -c "from argupaper.config import load_config; c=load_config(require_pdf_api_key=False); print(c.paper_storage_path); print(c.retrieval.default_limit, c.retrieval.max_results); print(c.analyze_enable_retrieval_loop)"
Remove-Item -Recurse -Force $env:PAPER_STORAGE_PATH
Remove-Item Env:PAPER_STORAGE_PATH
Remove-Item Env:SEARCH_DEFAULT_LIMIT
Remove-Item Env:SEARCH_MAX_RESULTS
Remove-Item Env:ANALYZE_ENABLE_RETRIEVAL_LOOP
```

- 预期结果：输出的 paper storage 路径与 `$env:PAPER_STORAGE_PATH` 一致；第二行输出 `7 13`；第三行输出 `False`
- 记录：____

### 8. Debate 角色异常兜底

- 功能名称：Debate 单角色异常兜底
- 适用场景：验证 support 输出为空、skeptic 抛异常时，`DebateChain` 仍返回结构完整的 `DebateState`
- 前置条件：已执行 `uv sync`
- 执行命令：

```powershell
@'
import asyncio
from argupaper.agents.base import AgentBase, AgentConfig
from argupaper.chains.debate import DebateChain

class EmptySupport(AgentBase):
    async def think(self, context):
        return ""

class BrokenSkeptic(AgentBase):
    async def think(self, context):
        raise RuntimeError("boom")

async def main():
    chain = DebateChain(max_rounds=1)
    chain.support_agent = EmptySupport(AgentConfig(name="support", role="support"))
    chain.skeptic_agent = BrokenSkeptic(AgentConfig(name="skeptic", role="skeptic"))
    state = await chain.run({"analysis": {"overview": "demo"}, "evidence": {}})
    print(len(state.messages))
    print(state.messages[0].content)
    print(state.messages[1].content)

asyncio.run(main())
'@ | uv run python -
```

- 预期结果：第一行输出 `2`；后两行分别包含 `Support fallback` 与 `Skeptic fallback`
- 记录：____

### 9. Analyze 空 Markdown 降级

- 功能名称：Analyze 空内容与抽取缺失 warning
- 适用场景：验证 PDF 转换返回空 Markdown 时，workflow 仍返回最小报告并暴露降级原因
- 前置条件：已执行 `uv sync`
- 执行命令：

```powershell
@'
import asyncio
import shutil
import tempfile
from pathlib import Path

from argupaper.config import Config, PDFConfig
from argupaper.pdf.types import ConversionResult, TaskStatus
from argupaper.workflows import AnalyzeOptions, AnalyzeWorkflow

class EmptyPipeline:
    async def process(self, paper_path, force_reconvert=False):
        return ConversionResult(
            status=TaskStatus.SUCCESS,
            markdown="",
            cache_key="empty-smoke",
            from_cache=False,
        )

    async def close(self):
        return None

async def main():
    data_dir = Path(tempfile.mkdtemp(prefix="argupaper-empty-md-"))
    try:
        config = Config(
            pdf=PDFConfig(api_key="fake"),
            data_path=str(data_dir),
            paper_storage_path=str(data_dir / "papers"),
        )
        workflow = AnalyzeWorkflow(config, pipeline_factory=lambda: EmptyPipeline())
        result = await workflow.run(AnalyzeOptions(paper_path=Path("empty.pdf"), rounds=1))
        print(result.paper_id)
        for warning in result.warnings:
            print(warning)
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)

asyncio.run(main())
'@ | uv run python -
```

- 预期结果：输出 `empty-smoke`；warning 中包含 `PDF conversion returned empty Markdown`、`Structured extraction missing fields` 和 `Supplementary retrieval skipped`
- 记录：____

### 10. SerpApi Google Scholar 检索

- 功能名称：SerpApi Google Scholar 检索源
- 适用场景：验证配置 `SERPAPI_API_KEY` 后可通过 Google Scholar 获取论文候选，并可作为 Semantic Scholar 403/429 的回退
- 前置条件：网络可访问；已配置有效的 `SERPAPI_API_KEY`
- 执行命令：

```powershell
uv run argupaper search "给我10篇有关多智能体的论文，要求近一年的" --source google_scholar --verbose
uv run argupaper search "给我10篇有关多智能体的论文，要求近一年的" --source semantic_scholar --verbose
```

- 预期结果：第一条命令返回 `source=google_scholar` 的论文列表；第二条命令若 Semantic Scholar 返回 403/429，应出现 `Fell back to Google Scholar via SerpApi` warning 且仍返回论文结果
- 记录：____

### 11. 本地 Web 工作台后端启动

- 功能名称：Workbench API 启动与配置状态
- 适用场景：验证本地 FastAPI 入口可启动，且不会暴露 API key 明文
- 前置条件：已执行 `uv sync`
- 执行命令：

```powershell
uv run uvicorn argupaper.web.app:app --port 8000
# 另开终端
Invoke-RestMethod http://127.0.0.1:8000/api/config/status
```

- 预期结果：接口返回 `mineru_api_configured`、`semantic_scholar_configured`、`serpapi_configured`、`paper_storage_path`、`cache_path` 等字段；不返回任何 API key 明文
- 记录：____

### 12. 本地 Web 工作台前端启动

- 功能名称：React Workbench 启动
- 适用场景：验证 Vite 前端可访问，并能通过 `/api` 代理访问后端
- 前置条件：后端已运行在 `127.0.0.1:8000`；已在 `frontend/` 执行 `npm install`
- 执行命令：

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

- 预期结果：浏览器打开 `http://127.0.0.1:5173` 后可看到 Search、Analyze、Library 三个工作台视图；侧栏配置状态可正常显示或显示可读错误
- 记录：____

### 13. Workbench Search 视图

- 功能名称：Workbench 检索可视化
- 适用场景：验证 React Search 页面复用现有 Search Agent workflow
- 前置条件：后端与前端均已启动；网络可访问所选检索源
- 执行步骤：
  1. 打开 Search 视图
  2. 输入 `retrieval augmented generation`
  3. 选择 `All configured`，limit 设为 `5`
  4. 点击 Search
- 预期结果：页面展示结果表格、Retrieved / Filtered / Parser 指标、warning 列表和 trace 路径；无需解析 CLI Rich 输出
- 记录：____

### 14. Workbench Analyze 视图

- 功能名称：Workbench PDF 分析后台任务
- 适用场景：验证 PDF 上传后会创建后台任务，并可轮询进度和报告
- 前置条件：后端与前端均已启动；已配置 `MINERU_API_KEY`；准备一个本地 PDF
- 执行步骤：
  1. 打开 Analyze 视图
  2. 上传 PDF
  3. 设置 rounds 为 `2`
  4. 点击 Start
- 预期结果：页面显示 job 状态从 queued/running 到 succeeded 或 failed；running 阶段展示 progress timeline；成功时展示 Paper ID、cache、supplementary retrieval 和 Markdown 报告；失败时展示可读错误
- 记录：____

### 15. Workbench Library 视图

- 功能名称：Workbench PaperStore 历史记录浏览
- 适用场景：验证 React Library 页面读取本地保存记录
- 前置条件：`PAPER_STORAGE_PATH` 下已有 analyze 保存的记录，或先执行一次 Analyze smoke
- 执行步骤：
  1. 打开 Library 视图
  2. 查看记录列表或输入 query 过滤
  3. 点击一条记录
  4. 在 Report 与 Paper Markdown 标签间切换
- 预期结果：页面显示元数据、Problem / Method / Experiment / Conclusion 结构化摘要，并能渲染保存的报告和论文 Markdown
- 记录：____

### 16. Workbench 错误处理

- 功能名称：Workbench 用户可读错误
- 适用场景：验证 Web API 和 UI 对常见错误给出明确反馈
- 前置条件：后端与前端均已启动
- 执行步骤：
  1. 在 Analyze 视图上传非 PDF 文件并点击 Start
  2. 在 Search 视图提交空 query 或会触发歧义澄清的请求
- 预期结果：页面显示可读错误；非 PDF 返回 `Only .pdf uploads are supported.`；歧义搜索返回需要 clarification 的错误，而不是静默失败
- 记录：____
