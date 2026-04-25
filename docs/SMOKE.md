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
