## 触发方式
负责接收从 coordinator 传来的各种非图片批改类的分析任务。
收到通过 sessions_send 传来的 JSON 消息：
- `task="report"`：周报 / 月报
- `task="study"`：错题总结 / 同类练习 / 合并输出

`study` 请求结构包含：
```json
{
  "task": "study",
  "purpose": "mistakes|exercises|both",
  "qq_user_id": "...",
  "student": "...",
  "subject": "...",
  "start": "...",
  "end": "...",
  "count": 5
}
```
其中 `subject` 必须是单一学科，不能传 `all`；`count` 默认 5，主要对 `exercises` 和 `both` 生效。

## 核心工作流

### 1. 周报 / 月报 工作流
Step 1: 处理请求，调用数据生成脚本，直接将返回作为上下文。
```bash
python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/generate_report.py --qq {qq} --student {student} --type {weekly/monthly} --subject {subject} --start '{start}' --end '{end}'
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

### 2. 学习巩固 工作流 (Study)
Step 1: 根据 `purpose` 选择对应的上游分析方式，确保使用同一组 `subject` / `start` / `end` 过滤条件：
- `mistakes`：调用错题总结数据脚本，获取报告级的错题与薄弱点信息
```bash
python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/generate_report.py --qq {qq} --student {student} --type mistakes --subject {subject} --start '{start}' --end '{end}'
```
- `exercises`：调用题目生成依据脚本，获取同类练习所需的核心薄弱点
```bash
python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/generate_exercises.py --qq {qq} --student {student} --subject {subject} --start '{start}' --end '{end}' --count X
```
- `both`：先调用 `generate_report.py --type mistakes` 获取错题总结与解析所需的上下文，再调用 `generate_exercises.py` 获取同类练习所需的上下文；两者使用同一组 `subject` / `start` / `end` 过滤条件，最后合并为一个文档，输出错题总结与同类练习
Step 2: 仔细分析上游脚本返回的"核心薄弱点"信息。
Step 3: 按 `purpose` 生成对应内容：
- `mistakes`：输出错题总结与解析
- `exercises`：输出同类巩固练习
- `both`：先输出错题总结，再输出同类巩固练习，最后统一输出答案与解析
Step 4: 将 Markdown 文本保存至 `/tmp/exercises.md`。
Step 5: 调用导出脚本排版为 Word 文件：
```bash
python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/export_word.py --type exercises --input /tmp/exercises.md --output /home/ubuntu/.openclaw/workspace-xunyu-coordinator/data/{qq}/{student}/学习巩固包_{purpose}_{subject}.docx
```
Step 6: 发送结束信息给 coordinator：
```json
{
  "status": "study_done",
  "summary": "根据小明的薄弱点，我出了一套专项训练题！",
  "word_path": "..."
}
```
