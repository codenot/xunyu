# Inspector (大模型督学) 重设计方案 (Approach A)

## 目标与背景
将 `inspector` 从一个简单的 "JSON 到 Markdown 格式化工具" 升级为具有教育洞察力的 "AI 督学教师"。
它将利用 `marker` 生成的结构化分析数据，进行跨周期的深度诊断，给出针对性建议，并通过对话形式引导后续的巩固练习。

## 核心变更点

### 1. 数据获取层 (scripts/collect_history.py)
`collect_history.py` 将增加一个 `--format json` 模式：
- **旧行为**：直接打印格式化好的 Markdown。
- **新行为**：将选定时间段内的所有 `analysis_{subject}.json` 聚合成一个大的 JSON 结构输出。这为 `inspector` 提供了原始的“原始诊断素材”，而非处理済的结论。

### 2. 督学大脑层 (agents/inspector/skills/inspector/SKILL.md)
重写 `SKILL.md`，从“排版规范”转向“分析指南”：
- **诊断逻辑**：要求模型分析 `errors` 中的 `error_reason`。不再只是统计次数，而是要归纳出“底层的认知缺陷”（例如：不是计算错误，而是退位减法逻辑不清）。
- **建议质量**：要求提供具体的“提分小锦囊”或“学习方法建议”，而非泛虚。
- **引导话术**：在生成完周报后，必须以引导语气询问家长是否需要针对该薄弱点由系统自动出 5-10 道题。

### 3. 工作流 (AGENTS.md)
更新 `inspector` 的流程为两个阶段的响应触发：
- **阶段 1：深度学情诊断 (由 Coordinator 的汇总结数指令触发)**
  - 命令：`scripts/collect_history.py --qq {qq} --student {student} --format json`
  - 行为：模型阅读 JSON，输出长篇周/月报，并**必须**在结尾提问：“*我为您整理了针对以上薄弱点的练习题，您现在需要下发给孩子吗？*”
- **阶段 2：针对性出题 (由用户反馈触发)**
  - 触发条件：当用户表达肯定意图时。
  - 行为：Coordinator 提供历史诊断 JSON。Inspector 充分发挥自主性，生成包含丰富题型（如：填空、应用、图形分析）的 Markdown。
  - **图文并茂支持**：模型可根据需要调用绘图工具（如有）生成示意图，或通过 Markdown 语法引用图片。
  - **文档导出**：复用并升级 `scripts/export_report.py`，支持动态标题（如“学情报告”或“巩固练习”），将结果渲染为 PDF。
  - **备注**：练习必须包含“题目”与“答案解析”，解析应深入浅出，体现“督学”的水平。

## 详细设计 (Section 3: Script & Export Enhancements)

### 1. 脚本升级 (scripts/export_pdf.py)
- **参数扩展**：增加 `--title` 参数，允许自定义 PDF 顶部的标题。
- **CSS 增强**：增加对 `<img>` 标签的基础样式支持（如 `max-width: 100%`），确保图文排版整齐。

### 2. 提示词增强 (SKILL.md)
- 明确要求模型在出题时，不仅要覆盖薄弱点，还要根据年级特点设计趣味性题型。
- 鼓励模型在解析中使用形象的比喻。

## 详细设计 (Section 1: Data Protocol)
... (保持不变)

### 聚合 JSON 输出格式
```json
{
  "student": "张三",
  "subject": "数学",
  "period": "2026-03-01 to 2026-03-07",
  "summary": {
    "total_batches": 5,
    "total_errors": 12
  },
  "raw_data": [
    {
      "batch_id": "...",
      "timestamp": "...",
      "weak_points": ["进位加法"],
      "errors": [...]
    }
  ]
}
```

## 详细设计 (Section 2: Inspector Persona & Output)

### 生成报告模板 (不再强行规定 Markdown 层级，改为人设驱动)
- **开场**：亲切的问候，基于 `total_batches` 的参与度评价。
- **深度分析**：
  - “根据本周的错题记录，我发现...”
  - 对 `error_reason` 的聚合分析，跨越多个 batch 寻找模式。
- **具体提分策略**：给家长的实操性建议（如“建议本周每天进行 5 分钟的口算闪示卡练习”）。
- **结语与邀约**：
  - “老师已经为您准备好了相关考点的针对性习题，您现在需要我出题给孩子练一练吗？”

---
## 下一步计划
1. 修改 `scripts/generate_report.py` 增加 JSON 输出支持。
2. 重写 `agents/inspector/skills/inspector/SKILL.md`。
3. 调整 `agents/inspector/AGENTS.md` 工作流。
