# Inspector 学习巩固请求统一化设计

## 背景
当前 `inspector` 的“错题本”和“出题本”是两条独立流程：
- 错题本依赖 `scripts/generate_report.py --type mistakes`，支持 `subject/start/end`
- 出题本依赖 `scripts/generate_exercises.py`，仅支持 `subject/count`

这导致两类能力的筛选口径不一致，无法稳定支持“按时间 + 按学科 + 目标可选”的统一请求，也无法自然表达“先总结错题，再出类似题”的合并产物。

## 目标
- 将“错题总结”“出类似题”“两者皆有”统一为一类 `study` 请求。
- 三种目的共享同一套查询条件：`student + subject + start + end`。
- 当 `purpose=both` 时输出单个合并 Word 文档，而不是两个分离文件。

## 非目标
- 不改动周报、月报流程。
- 不重写整套数据层；优先复用现有脚本。
- 不支持 `subject=all` 的跨学科出题。

## 请求协议
`coordinator -> inspector` 的消息改为：

```json
{
  "task": "study",
  "purpose": "mistakes|exercises|both",
  "qq_user_id": "12345",
  "student": "小明",
  "subject": "数学",
  "start": "2026-03-01",
  "end": "2026-03-22",
  "count": 5
}
```

字段约束：
- `purpose` 必填，可选值为 `mistakes`、`exercises`、`both`
- `student`、`subject` 必填
- `start`、`end` 可选；缺省表示全历史
- `count` 对 `exercises` 和 `both` 生效，默认值为 `5`
- `subject` 对该请求不得为 `all`

## Coordinator 编排变更
`agents/coordinator/AGENTS.md` 需要改为统一入口识别：
- “错题本 / 错题总结” -> `purpose=mistakes`
- “出题 / 类似题 / 练习题” -> `purpose=exercises`
- “总结并出题 / 错题+练习 / 两者都要” -> `purpose=both`

追问规则：
- 未指定孩子：按现有多孩子规则追问
- 未指定学科：必须追问，不能默认 `all`
- 未指定时间：默认全历史
- 提供了非法区间（`start > end`）：要求用户重新确认

## Inspector 编排变更
`agents/inspector/AGENTS.md` 中新增统一工作流：

1. 校验 `task="study"` 和请求字段。
2. 使用统一的历史数据筛选作为事实来源：

```bash
python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/generate_report.py \
  --qq {qq} \
  --student {student} \
  --type mistakes \
  --subject {subject} \
  --start '{start}' \
  --end '{end}'
```

3. 基于返回 JSON 生成 Markdown：
   - `mistakes`：只输出错题总结与解析
   - `exercises`：只输出同类巩固练习
   - `both`：同一文档先输出错题总结，再输出练习题，最后统一输出答案与解析
4. 将 Markdown 保存到临时文件。
5. 调用 `scripts/export_word.py` 生成单个 `.docx`。
6. 回传 `status="study_done"`、`summary`、`word_path`。

## 文档结构
当 `purpose=both` 时，建议 Word 内容采用以下结构：

```markdown
# [学生姓名][学科]学习巩固包

## 一、错题总结与解析
### 错题 1：[日期]
- 题目：
- 原答：
- 正确：
- 错因：
- 督导拆解思路：

## 二、同类巩固练习
### 练习 1
...

# 答案与解析
## 练习 1
...
```

命名建议：
- `错题总结_{subject}.docx`
- `专项练习_{subject}.docx`
- `学习巩固包_{subject}_{start}_{end}.docx`

## 脚本边界
### `scripts/generate_report.py`
- 继续作为统一历史查询入口
- `--type mistakes` 时返回 `mistakes_list`、`top_mistakes`、`weak_points`
- `inspector` 的三种 `purpose` 均基于该结果生成文案

### `scripts/generate_exercises.py`
- 补充 `--start`、`--end`
- 过滤逻辑与 `generate_report.py` 保持一致
- 角色收敛为“给出薄弱点摘要提示”，而不是定义单独的数据筛选规则

## 异常处理
- 无历史记录：直接返回“该时间范围内暂无该学科记录，暂不能生成总结或练习”
- `purpose=both` 但薄弱点不足：仍生成合并文档，练习题退化为基于高频错因的基础巩固题
- `subject=all`：拒绝执行并要求指定单科
- `start > end`：拒绝执行并要求用户重填时间

## 实施顺序
1. 更新 `agents/coordinator/AGENTS.md` 的意图和追问规则
2. 更新 `agents/inspector/AGENTS.md` 的任务协议与统一流程
3. 扩展 `scripts/generate_exercises.py` 的时间过滤能力
4. 根据统一协议补充手工验证样例

## 验证建议
- 指定单科 + 时间范围，验证 `mistakes`
- 指定单科 + 时间范围，验证 `exercises`
- 指定单科 + 时间范围，验证 `both` 输出单个合并文档
- 验证 `subject=all`、空数据、非法时间区间的回退行为
