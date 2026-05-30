# SMOKE

本文件是项目唯一的手工 smoke 验收入口。

## 表单模板

每条 smoke 项按以下字段维护：

- 功能名称
- 适用场景
- 前置条件
- 执行命令或步骤
- 预期结果
- 记录

## 维护原则

- Smoke 条目应面向人工快速验收，优先覆盖 CLI、Web 与主工作流。
- 不再放置需要粘贴大段 PowerShell / Python 脚本的内部实现检查。
- 若某项只能通过构造临时文件、临时环境变量或 mock 类验证，应优先下沉到代码级测试或开发调试记录，不作为手工 smoke 条目维护。

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

### 4. 相对时间解析

- 功能名称：相对时间解析
- 适用场景：验证搜索请求中的相对年份表达会按当前日期归一化
- 前置条件：当前本地日期可获取
- 执行命令：`uv run argupaper search "近一年 的 retrieval augmented generation 论文" --limit 5 --source both --verbose`
- 预期结果：解析结果中的年份范围应与当前年份一致；例如当前日期为 2026-04-25 时，`近一年` 应解析为 `year_from=2025`、`year_to=2026`
- 记录：____

### 5. PDF 转 Markdown 缓存

- 功能名称：PDF 转 Markdown 缓存
- 适用场景：验证 `convert` 可将本地 PDF 转换为 Markdown 并写入 cache
- 前置条件：已配置 `MINERU_API_KEY`、`MINERU_API_ENDPOINT=https://mineru.net/api/v4/extract/task`；当前网络可访问 MinerU API 与其返回的签名上传 / 下载地址；准备一个本地 PDF 文件
- 执行命令：`uv run argupaper convert ./paper.pdf`
- 预期结果：成功输出 cache key、cache path 与是否来自缓存；`data/cache` 下存在对应 `.md` 与 `.meta.json`
- 记录：____

### 6. PDF 目录批量转换

- 功能名称：PDF 目录批量转换
- 适用场景：验证 `convert --folder` 可批量处理目录直属 PDF，并跳过非 PDF 或子目录
- 前置条件：已配置 `MINERU_API_KEY`、`MINERU_API_ENDPOINT=https://mineru.net/api/v4/extract/task`；当前网络可访问 MinerU API 与其返回的签名上传 / 下载地址；准备一个目录，包含至少两个 PDF、一个非 PDF 文件和一个子目录
- 执行命令：`uv run argupaper convert --folder ./papers`
- 预期结果：命令显示逐文件处理进度；PDF 被转换或命中缓存；非 PDF 文件与子目录被跳过；最终汇总包含 total、processed、succeeded、cache、failed、skipped；`data/logs/convert/` 下生成对应 JSONL 日志
- 记录：____

### 7. 本地 Markdown 分析主链路

- 功能名称：本地 Markdown 分析
- 适用场景：验证 `analyze` 可按已转换论文名读取缓存 Markdown 并生成报告
- 前置条件：已先执行 `uv run argupaper convert ./paper.pdf`
- 执行命令：`uv run argupaper analyze "paper" --output 1.md --rounds 2`
- 预期结果：不重新提交 MinerU 转换任务；成功生成 Markdown 报告，裸文件名输出自动保存到 `output/1.md`；报告中应能看到与当前轮数一致的 debate 输出；若下游阶段异常，应给出可见错误或 warning，而不是静默失败
- 记录：____

### 8. Analyze 自动报告保存

- 功能名称：Analyze 自动报告保存
- 适用场景：验证未显式传入 `--output` 时，可按论文文件名自动保存报告
- 前置条件：已先执行 `uv run argupaper convert ./paper.pdf`
- 执行命令：`uv run argupaper analyze "paper" --save-report`
- 预期结果：成功生成 Markdown 报告，并自动保存到 `output/paper.md`
- 记录：____

### 9. Analyze 缓存未命中提示

- 功能名称：Analyze 缓存未命中提示
- 适用场景：验证按论文名分析未转换论文时不会静默调用 MinerU
- 前置条件：确认 cache 中不存在名为 `unknown-paper` 的记录
- 执行命令：`uv run argupaper analyze "unknown-paper"`
- 预期结果：命令失败并提示未找到已转换 Markdown，要求先运行 `argupaper convert <pdf>`
- 记录：____

### 10. Analyze 缓存歧义提示

- 功能名称：Analyze 缓存歧义提示
- 适用场景：验证多个缓存记录匹配同一论文名时不会自动选择
- 前置条件：本地 cache 中已存在两个文件名相近、都能匹配同一查询词的转换记录
- 执行命令：`uv run argupaper analyze "paper"`
- 预期结果：命令失败并列出候选 original filename 与 cache key，要求输入更精确名称或 cache key
- 记录：____

### 11. Legacy PDF Analyze 兼容

- 功能名称：Legacy PDF Analyze 兼容
- 适用场景：验证旧的 PDF 输入仍可运行但会提示迁移
- 前置条件：已配置 `MINERU_API_KEY`、`MINERU_API_ENDPOINT=https://mineru.net/api/v4/extract/task`；准备一个本地 PDF 文件
- 执行命令：`uv run argupaper analyze ./paper.pdf --rounds 2`
- 预期结果：命令仍可生成报告；warning 中包含推荐先运行 `argupaper convert` 再运行 `argupaper analyze <paper-name>` 的提示
- 记录：____

### 12. 本地论文历史记录读取

- 功能名称：PaperStore 历史记录读取
- 适用场景：验证 `argupaper papers` 可列出、搜索并读取本地记录
- 前置条件：已完成至少一次成功的 analyze，并已保存报告
- 执行命令：

```powershell
uv run argupaper papers
uv run argupaper papers --query paper
```

- 预期结果：第一条命令显示 Saved Papers 表格；第二条命令可按 query 过滤出匹配论文记录
- 记录：____

### 13. CLI 错误处理

- 功能名称：用户可读错误面板
- 适用场景：验证 CLI 参数错误会显示明确错误类型与下一步提示
- 前置条件：已执行 `uv sync`；准备一个非 PDF 文件，例如 `not-pdf.txt`
- 执行命令：`uv run argupaper analyze ./not-pdf.txt`
- 预期结果：命令失败；错误面板包含错误类型、错误原因和下一步提示，不出现 Python traceback
- 记录：____

### 14. SerpApi Google Scholar 检索

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

### 15. 本地 Web 工作台后端启动

- 功能名称：Workbench API 启动与配置状态
- 适用场景：验证本地 FastAPI 入口可启动，且不会暴露 API key 明文
- 前置条件：已执行 `uv sync`
- 执行命令：

```powershell
uv run uvicorn argupaper.web.app:app --port 8000
# 另开终端
Invoke-RestMethod http://127.0.0.1:8000/api/config/status
```

- 预期结果：接口返回 `mineru_api_configured`、`semantic_scholar_configured`、`serpapi_configured`、`paper_storage_path`、`cache_path`、`log_path`、`search_log_path`、`convert_log_path`、`web_log_path` 等字段；不返回任何 API key 明文；`data/logs/web/web-backend.log` 存在并记录后端启动或请求日志
- 记录：____

### 16. 本地 Web 工作台前端启动

- 功能名称：React Workbench 启动
- 适用场景：验证 Vite 前端可访问，并能通过 `/api` 代理访问后端
- 前置条件：后端已运行在 `127.0.0.1:8000`；已在 `frontend/` 执行 `npm install`
- 执行命令：

```powershell
cd frontend
npm run dev:log
```

- 预期结果：浏览器打开 `http://127.0.0.1:5173` 后可看到 Search、Analyze、Library 三个工作台视图；侧栏配置状态可正常显示或显示可读错误；`data/logs/web/web-frontend.log`、`data/logs/web/web-frontend.out.log`、`data/logs/web/web-frontend.err.log` 写入前端开发服务日志
- 记录：____

### 17. Workbench Search 视图

- 功能名称：Workbench 检索可视化
- 适用场景：验证 React Search 页面复用现有 Search workflow
- 前置条件：后端与前端均已启动；网络可访问所选检索源
- 执行步骤：
  1. 打开 Search 视图
  2. 输入 `retrieval augmented generation`
  3. 选择 `All configured`，limit 设为 `5`
  4. 点击 Search
- 预期结果：页面展示结果表格、Retrieved / Filtered / Parser 指标、warning 列表和 trace 路径；无需解析 CLI Rich 输出
- 记录：____

### 18. Workbench Analyze 视图

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

### 19. Workbench Library 视图

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

### 20. Workbench 错误处理

- 功能名称：Workbench 用户可读错误
- 适用场景：验证 Web API 和 UI 对常见错误给出明确反馈
- 前置条件：后端与前端均已启动
- 执行步骤：
  1. 在 Analyze 视图上传非 PDF 文件并点击 Start
  2. 在 Search 视图提交空 query 或会触发歧义澄清的请求
- 预期结果：页面显示可读错误；非 PDF 返回 `Only .pdf uploads are supported.`；歧义搜索返回需要 clarification 的错误，而不是静默失败
- 记录：____

### 21. v0.3 架构边界重构

- 功能名称：v0.3 架构边界重构
- 适用场景：验证新结构外部入口未破坏
- 前置条件：已执行 `uv sync`
- 执行命令：

```powershell
uv run argupaper --help
uv run argupaper convert --help
uv run argupaper analyze --help
uv run argupaper search --help
uv run argupaper papers --help
```

- 预期结果：所有 CLI help 命令正常显示；不出现导入错误或命令缺失
- 记录：____

### 22. Convert 结果进入 PaperStore

- 功能名称：Convert-only 论文进入本地论文库
- 适用场景：验证 `argupaper convert` 成功后，尚未 analyze 的论文也能通过 PaperStore 浏览，并用 `library_status` 与 analyzed 记录区分
- 前置条件：已执行 `uv sync`；已配置 `MINERU_API_KEY`；准备一个本地 PDF
- 执行命令：
```powershell
uv run argupaper convert .\sample.pdf
uv run argupaper papers
uv run argupaper papers <paper_id> --markdown
uv run argupaper convert .\sample.pdf
uv run argupaper analyze sample
uv run argupaper papers
```

- 预期结果：首次 convert 后 `argupaper papers` 出现同一 cache key 的记录，Status 为 `converted`；`--markdown` 可显示保存的 Markdown；第二次 convert 使用 cache 时记录仍存在；analyze 后同一记录 Status 升级为 `analyzed`，并包含结构化摘要和报告
- Web 验收：启动后端和前端，打开 Library 视图，确认列表和详情都显示 converted/analyzed 状态，converted 记录可查看 Paper Markdown
- 记录：____
