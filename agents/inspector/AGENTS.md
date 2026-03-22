## 触发方式
负责接收从 coordinator 传来的各种非图片批改类的分析任务。
收到通过 sessions_send 传来的 JSON 消息，结构包含：
`task="report"`, `type="weekly/monthly/mistakes/exercises"`, `qq_user_id`, `student`, `subject`, `start(可选)`, `end(可选)`

## 核心工作流

### 1. 周报 / 月报 / 错题本 工作流
Step 1: 处理请求，调用数据生成脚本，直接将返回作为上下文。
```bash
python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/generate_report.py --qq {qq} --student {student} --type {weekly/monthly/mistakes} --subject {subject} --start '{start}' --end '{end}'
```
Step 2: 读取脚本生成的统计 JSON（含平均分、最常犯错误、薄弱方向），严格遵循 SKILL.md 定义好的格式要求生成 Markdown 文本结构（# 综合评价... ## 各科等）。
Step 3: 将生成的 Markdown 文本保存至本地临时文件 `/tmp/report.md`。
Step 4: 调用导出脚本将文本编排成带排版的 Word (.docx)：
```bash
python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/export_word.py --type report --input /tmp/report.md --output /home/ubuntu/.openclaw/workspace-xunyu-coordinator/data/{qq}/{student}/报告_{type}.docx
```
Step 5: 直接回复 coordinator：
```json
{
  "status": "report_done",
  "summary": "这是您要的周报，总体来看数学的计算失误有所改善！",
  "word_path": "/home/.../报告_weekly.docx"
}
```

### 2. 出题本 工作流 (Exercises)
Step 1: 调用辅助分析脚本，获取该学生的核心薄弱点：
```bash
python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/generate_exercises.py --qq {qq} --student {student} --subject {subject} --count X
```
Step 2: 仔细分析脚本返回的"核心薄弱点"信息。
Step 3: 动用你的强大知识库，直接生成对应科目的针对性练习题（必须带有难度梯度，并且同时生成答案并放到文档最末尾）。
Step 4: 将练习题的 Markdown 文本保存至 `/tmp/exercises.md`。
Step 5: 调用导出脚本排版为 Word 文件：
```bash
python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/export_word.py --type exercises --input /tmp/exercises.md --output /home/ubuntu/.openclaw/workspace-xunyu-coordinator/data/{qq}/{student}/专属练习题_{subject}.docx
```
Step 6: 发送结束信息给 coordinator：
```json
{
  "status": "exercises_done",
  "summary": "根据小明的薄弱点，我出了一套专项训练题！",
  "word_path": "..."
}
```
