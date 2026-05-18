## Why

`argupaper analyze` 目前把 PDF 转 Markdown、结构化分析、证据检查、debate、judge 与报告生成串在同一条主链路中，导致每次分析都容易被 MinerU 网络、上传或解析问题阻断。先把 PDF 转换从 analyze 中拆出，可以显著降低主链路失败面，并让用户复用已转换 Markdown 反复调试分析逻辑；这比继续扩展 4-Agent、知识图谱等后续能力更优先，因为它直接提升当前核心路径的稳定性和可验收性。

## What Changes

- 新增 `argupaper convert <pdf> [--force] [--output <path>]`，专门负责本地 PDF 到 Markdown 的转换与缓存。
- 修改 `argupaper analyze <paper>`，当输入不是 PDF 路径时，按现有 cache metadata 的原始文件名或 stem 查找已转换 Markdown 并直接分析。
- 保留 `argupaper analyze ./paper.pdf` 作为兼容路径，但输出 warning，引导用户使用 `convert -> analyze <论文名>`。
- 增强 `MarkdownCache`，支持按原始文件名、stem 或 cache key 查找唯一 Markdown 记录，并在未命中或多命中时提供可读错误。
- 更新 README 与 `docs/SMOKE.md`，补充 convert/analyze 解耦后的手工验收步骤。

## Capabilities

### New Capabilities

- `analyze-input-decoupling`: 定义 PDF 转 Markdown 与 analyze Markdown 分析解耦后的 CLI 输入、缓存查找、兼容路径和错误处理行为。

### Modified Capabilities

- None.

## Impact

- 影响范围：
  - CLI：新增 `convert` 命令，调整 `analyze` 输入语义与 warning。
  - Workflow：`AnalyzeWorkflow` 需要支持从 cached Markdown 直接分析，也保留 legacy PDF 路径。
  - Cache：`MarkdownCache` 增加按 metadata 查询记录能力。
  - Web：上传 PDF 的 analyze 入口继续通过 legacy PDF path 调用，不新增 Web 转换页面。
  - 文档：README、`docs/SMOKE.md` 和完成记录需要同步。
- 回滚策略：
  - 删除 `convert` 命令及相关文档。
  - 将 `AnalyzeOptions.paper_path` 恢复为必填，并恢复 `AnalyzeWorkflow` 内部始终先调用 `PDFPipeline.process()` 的逻辑。
  - 保留已有 cache 文件与 metadata，不需要迁移或清理。
