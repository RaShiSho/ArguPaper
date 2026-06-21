## Context

`AnalyzeWorkflow` 当前从 `AnalyzeOptions.paper_path` 开始，先调用 `PDFPipeline.process()`，再执行结构抽取、证据检查、debate、judge 和 report。`MarkdownCache` 已保存 `{hash}.md` 与 `{hash}.meta.json`，其中 metadata 包含 `original_filename`，因此可以复用现有缓存作为“论文名字 -> Markdown”的轻量索引。

## Goals / Non-Goals

**Goals:**

- 将 PDF 转 Markdown 独立为 `argupaper convert`。
- 让 `argupaper analyze <paper-name>` 可直接读取已缓存 Markdown 并运行分析。
- 保留 `argupaper analyze ./paper.pdf` 兼容路径，并给出迁移 warning。
- 在未命中或多命中 cache 时输出可读错误，避免静默重新调用 MinerU。

**Non-Goals:**

- 不新增独立 Markdown Library 或数据库。
- 不新增 Web 转换页面。
- 不改变 `ConsensusDetector` 与 `ReportGenerator` 的职责；它们仍只消费 analyze 上游产物并生成 judge/report 结果。
- 不支持 URL PDF analyze。

## Decisions

- **使用现有 MarkdownCache 作为索引来源。** 备选方案是新建 PaperLibrary 或复用 PaperStore；前者迁移成本更高，后者只能覆盖已分析论文。现有 cache metadata 已有原始文件名，能用最小改动支持论文名查询。
- **AnalyzeWorkflow 拆成输入加载与 Markdown 分析两个阶段。** 输入加载负责 PDF legacy 路径、cache 查询和 warning；Markdown 分析阶段继续负责 structured/evidence/debate/judge/report。`ConsensusDetector` 和 `ReportGenerator` 边界不变，不感知输入来自 PDF 还是 cache。
- **CLI 保持薄层。** `convert` 只组装 config、pipeline 和输出参数；cache 查询、PDF 兼容和 Markdown 分析逻辑放在 workflow/cache 层。
- **失败降级与 warning 策略。** cache 未命中或多命中属于用户输入错误，直接失败并给出下一步；legacy PDF 输入属于兼容 warning；PDF 转换失败仍按现有 ConversionError 暴露；下游 debate/judge/report 继续沿用现有 warning 降级行为。

## Risks / Trade-offs

- **同名 PDF 可能匹配多个 cache 记录。** → 拒绝自动选择，列出候选 cache key 与 original filename。
- **cache metadata 缺失会导致旧缓存不可按名称发现。** → 支持 cache key 精确输入；缺失 metadata 的旧缓存不参与 filename/stem 匹配。
- **用户仍可用 PDF 路径触发网络转换。** → 保留兼容但提示推荐新流程，避免破坏现有 Web 上传和 CLI 用法。
- **按文件名而非论文标题匹配可能不符合部分用户直觉。** → 文档明确“论文名字”指原始 PDF 文件名或 stem。
