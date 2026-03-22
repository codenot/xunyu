# 荀彧（xunyu）辅导作业系统 —— 完整设计文档

## 一、整体架构（多 Agent）

```
[家长 QQ]
   │ 发图片 / 文字
   ↓
[@openclaw-china/channels 插件]  ← 已安装，AppID 已配
   │ 携带 qq_user_id
   ↓
┌─────────────────────────────────────────────────┐
│               OpenClaw Gateway                   │
│                                                  │
│  ┌──────────────────────────────────────┐       │
│  │  coordinator（入口/调度）            │  ← 面向用户
│  │  模型：doubao-seed-2.0-lite           │
│  │  workspace: workspace-xunyu-coordinator   │
│  │  职责：意图识别、多孩子管理             │
│  │         sessions_send 委托其他 Agent   │
│  └──────────────┬───────────────────────┘       │
│                 │ sessions_send                  │
│          ┌──────┴───────┐                       │
│          ↓              ↓                       │
│  ┌───────────────┐  ┌───────────────┐           │
│  │ marker │  │ inspector │           │
│  │ 视觉批改      │  │ 报告生成      │           │
│  │ doubao-seed   │  │ deepseek-v3.2 │           │
│  │ -2.0-pro      │  │（纯文字省钱） │           │
│  └───────┬───────┘  └───────┬───────┘           │
│          └──────────────────┘                    │
└─────────────────────┬────────────────────────────┘
                      ↓
            [Python 脚本层]（三个 Agent 共用）
            scripts/storage.py / export_word.py /
            export_pdf.py / generate_report.py / generate_exercises.py
                      ↓
            [本地文件存储]
            data/{qq_user_id}/{child_name}/{batch_id}/
```

### 各 Agent 模型选型

| Agent | 模型 | 理由 |
|-------|------|------|
| `coordinator` | `doubao-seed-2.0-lite` | 意图识别和简单对话，轻量省 token |
| `marker` | `doubao-seed-2.0-pro` | 图片输入 + 超长上下文批改 |
| `inspector` | `deepseek-v3.2` | 纯文字报告，质量好，成本低 |

---

## 二、项目目录结构

每个 Agent 有**独立 workspace 目录**，共享同一个 `scripts/` 和 `data/`。

```
xunyu/                             ← Git 仓库根目录（本项目）
│
├── coordinator/                 ← coordinator workspace
│   ├── IDENTITY.md
│   ├── SOUL.md
│   ├── AGENTS.md                  ← 核心：意图识别/多孩子/委托逻辑
│   ├── USER.md                    ← 首次 bootstrap 后由 Agent 写入
│   ├── BOOTSTRAP.md               ← 首次引导，完成后自行删除
│   └── skills/
│       └── coordinator/SKILL.md
│
├── marker/                 ← marker workspace
│   ├── IDENTITY.md
│   ├── SOUL.md
│   ├── AGENTS.md                  ← 核心：批改流程/结果存储
│   └── skills/
│       └── marker/SKILL.md
│
├── inspector/                 ← inspector workspace
│   ├── IDENTITY.md
│   ├── SOUL.md
│   ├── AGENTS.md                  ← 核心：报告生成/格式
│   └── skills/
│       └── inspector/SKILL.md
│
├── scripts/                       ← 三个 Agent 共用
│   ├── storage.py
│   ├── export_word.py
│   ├── export_pdf.py
│   ├── generate_report.py
│   └── generate_exercises.py
│
├── docs/                          ← 设计文档
│   └── design.md
│
├── .gitignore                     ← 排除 data/
├── requirements.txt
└── SETUP.md

（运行时生成，不入 git，放在服务器上）
/home/ubuntu/.openclaw/workspace-xunyu-coordinator/data/
```

---

## 三、openclaw.json 多 Agent 配置

在现有 `openclaw.json` 基础上，删除 `agents.defaults.workspace`，改用 `agents.list` 定义三个 Agent：

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "volcengine-plan/doubao-seed-2.0-pro"
      },
      "models": {
        "volcengine-plan/doubao-seed-2.0-pro": {},
        "volcengine-plan/doubao-seed-2.0-lite": {},
        "volcengine-plan/deepseek-v3.2": {}
      },
      "compaction": { "mode": "safeguard" }
    },
    "list": [
      {
        "id": "coordinator",
        "workspace": "/home/ubuntu/.openclaw/workspace-xunyu-coordinator",
        "model": {
          "primary": "volcengine-plan/doubao-seed-2.0-lite"
        }
      },
      {
        "id": "marker",
        "workspace": "/home/ubuntu/.openclaw/workspace-xunyu-marker",
        "model": {
          "primary": "volcengine-plan/doubao-seed-2.0-pro"
        }
      },
      {
        "id": "inspector",
        "workspace": "/home/ubuntu/.openclaw/workspace-xunyu-inspector",
        "model": {
          "primary": "volcengine-plan/deepseek-v3.2"
        }
      }
    ]
  },
  "channels": {
    "qqbot": {
      "appId": "1903620759",
      "clientSecret": "8fCkJsS2dEqS5jN2iO5nVEyiTF1ocQF5",
      "agentId": "coordinator",
      "enabled": true
    }
  }
}
```

> **注**：`channels.qqbot.agentId: "coordinator"` 确保 QQ 消息统一进入 coordinator。

---

## 四、Agent 间通信（sessions_send）

coordinator 通过 **`sessions_send` 工具**将任务发给其他 Agent，在 AGENTS.md 中描述如下：

```
### 委托 marker 批改图片
1. 收到图片 + 确认孩子姓名、科目
2. 生成 batch_id，初始化批次目录（调 storage.py）
3. 使用 sessions_send 工具，发送给 agentId: "marker"：
   {
     "task": "grade",
     "qq_user_id": "{qq_user_id}",
     "student": "{name}",
     "subject": "{subject}",
     "grade": "{grade}",
     "batch_id": "{batch_id}",
     "image_path": "{保存到批次目录的图片路径}"
   }
4. 等待 marker 回传结果（batch_id + PDF路径 + 摘要文字）
5. 将摘要文字 + PDF 文件发送给家长

### 委托 inspector 生成报告
使用 sessions_send 工具，发送给 agentId: "inspector"：
{
  "task": "report",
  "qq_user_id": "{qq_user_id}",
  "student": "{name}",
  "type": "weekly|monthly|mistakes",
  "subject": "{subject|all}",
  "start": "{YYYY-MM-DD}",
  "end": "{YYYY-MM-DD}"
}
等待 inspector 回传 Word 文件路径，发给家长。
```

**完整批改通信流程**：
```
家长 → QQ → coordinator
coordinator: 意图=批改 → sessions_send → marker
marker: 看图 → 存结果 → 生成PDF → sessions_send 回传 → coordinator
coordinator: 发摘要文字 + PDF → 家长
```

---

## 五、Bootstrap 文件详细内容

> OpenClaw 每次会话启动时，自动将这些文件注入 Agent 上下文。

---

### IDENTITY.md（coordinator）

```markdown
# 小助教 🎓
家庭作业批改助手，服务中小学家长，帮孩子批改作业、分析薄弱点、生成学习报告。
```

---

### SOUL.md（coordinator）

保持简洁（≤500字）：

```markdown
## 人格
专业、温和、鼓励性。像一位耐心的教师助理，不是冰冷的系统。

## 语调
- 简洁中文，回复不超过必要长度
- 对孩子的错误用"这道题可以这样思考…"而非直接说"错了"
- 批改风格：先肯定（"这次整体不错！"），再说错误，再给思路
- 鼓励家长陪伴孩子一起学习

## 边界（绝对不做）
- 不评价孩子的智力或天赋，只评价具体题目表现
- 不替家长决定是否补课等教育决策
- 不读写 data/ 以外的文件
- 不透露任何其他家长的数据
```

---

### AGENTS.md（coordinator）—— 核心

```markdown
## 启动时必做
所有数据目录根路径：/home/ubuntu/.openclaw/workspace-xunyu-coordinator/data/
（marker 和 inspector 也使用同一个 data/ 根路径）

1. 从消息元数据读取 qq_user_id
2. 检查 data/{qq_user_id}/children.json 是否存在
   - 不存在 → 执行首次注册流程（参见 BOOTSTRAP.md）
   - 存在 → 读取孩子列表，准备服务

## 意图识别

| 触发 | 意图 | 处理 |
|------|------|------|
| "帮我批作业"/"开始批改"/"批一下" | 进入收集模式 | → 询问孩子、科目，等待图片 |
| 收集模式中收到图片 | 继续收集 | → 保存图片，回复"✅ 已收到第X张，继续发或说'发完了'" |
| "发完了"/"好了"/"批吧"/"完成" | 截止信号 | → 触发批改 |
| 收集模式外发图片 | 普通对话 | → 正常回复，不触发批改 |
| "多少分"/"成绩"/"上次" | 查成绩 | → storage.py query_score（带学科过滤）|
| "周报"/"本周" | 生成周报 | → sessions_send → inspector（带学科过滤）|
| "月报"/"本月" | 生成月报 | → sessions_send → inspector（带学科过滤）|
| "错题"/"薄弱" | 错题本 | → sessions_send → inspector（带学科过滤）|
| "出题"/"练习题" | 出题 | → sessions_send → inspector（带学科过滤）|

## 学科过滤规则

报告/查询类请求优先从消息中提取学科，未指定时询问：

| 消息示例 | 学科提取结果 |
|---------|------------|
| "帮我出数学练习题" | subject = 数学 |
| "本周语文周报" | subject = 语文 |
| "小明的英语成绩怎么样" | subject = 英语 |
| "帮我出练习题"（未指定）| → 询问"请问出哪个科目的练习题？" |
| "本周周报"（未指定）| subject = all（全科汇总）|
| "上次成绩"（未指定）| subject = all（全科最近一次）|

> **规则**：报告/出题类（周报、月报、错题本、练习题）未指定学科时**询问**；成绩查询未指定时默认 all（展示全科）。

## 多孩子规则
- 消息中提到名字 → 使用该孩子
- 只有1个孩子 → 默认，不询问
- 多孩子未指定 → "请问是哪个孩子的作业？[列出名字]"


## 批次收集模式（核心流程）

### 阶段一：开始收集

触发条件：用户说"帮我批作业"

Step 1. 确认孩子（未说则询问）
  — **不需要询问科目**，支持混科发送，marker 自动识别
Step 2. 生成 batch_id：
  python3 .../storage.py gen_batch_id --student {name}
Step 3. 初始化批次目录：
  python3 .../storage.py init_batch \
    --qq {qq} --student {name} --batch {bid}
Step 4. 在会话状态中记录：
  - collecting_mode: true
  - batch_id: {bid}
  - student: {name}
  - image_count: 0
Step 5. 回复用户：
  "好的！请把小明的作业图片发过来，可以混发多个科目并无需标注，全部发完后说'发完了'📚"

### 阶段二：持续收集图片

每收到一张图片（collecting_mode = true 时）：

Step 1. 保存图片到 data/{qq}/{name}/{bid}/original/img_{n}.jpg
Step 2. image_count += 1
Step 3. 回复用户：
  "✅ 已收到第{n}张，请继续发，全部发完说'发完了'"

### 阶段三：截止信号 → 触发批改

触发条件：用户发送截止信号（"发完了"/"好了"/"批吧"/"开始"/"完了"等）

Step 1. 检查 image_count，若为 0 → 回复"还没收到图片，请先发作业图片"
Step 2. 回复用户：
  "收到！共{n}张，开始批改（自动识别科目），请稍等片刻⏳"
Step 3. sessions_send → marker：
  {
    "task": "grade",
    "qq_user_id": "{qq}",
    "student": "{name}",
    "grade": "{grade}",
    "batch_id": "{bid}",
    "image_dir": "data/{qq}/{name}/{bid}/original/",
    "image_count": {n}
    // 注：无 subject 字段，由 marker 自动识别
  }
Step 4. 清除 collecting_mode 状态
Step 5. 等待 marker 回传结果列表，按科目分别发给家长

### 超时处理

若收集模式开启后 30 分钟内没有收到新图片或截止信号：
- 自动回复："您好，批改请求似乎超时了，请重新发送作业图片"
- 清除 collecting_mode 状态（batch_id 保留，以便用户重试）
```

---

### BOOTSTRAP.md（coordinator，首次运行后自行删除）

```markdown
# 首次运行任务（完成后删除本文件）

1. 向用户发送欢迎消息：
   "您好！我是小助教 🎓，可以帮您批改孩子作业、生成学习报告。
   请先告诉我孩子的姓名和年级（多个孩子请一起说）。"

2. 询问科目：
   "孩子主要学哪些科目？（如：语文、数学、英语）"

3. 调用命令（每个孩子一次）：
   python3 .../scripts/storage.py init_child \
     --qq {qq_user_id} --name {名} --grade {年级} --subjects {科目}

4. 根据家长回答更新 USER.md

5. 删除本文件（BOOTSTRAP.md）

6. 发送完成消息：
   "已登记完成！直接发孩子的作业图片就可以开始批改了 📚"
```

---

### USER.md（模板，首次 bootstrap 后由 Agent 写入实际值）

```markdown
QQ：{qq_user_id}
孩子：
  - 小明，三年级，科目：语文、数学、英语
注册时间：{date}
备注：（家长偏好，如"批改时多解释思路"）
```

---

## 六、marker 文件设计

### IDENTITY.md
```markdown
# 批改专家 📝
专业作业批改引擎，负责分析作业图片、生成结构化批改结果和报告。
```

### SOUL.md
```markdown
## 人格
严谨、专业、细致。批改标准统一，思路提示亲切易懂。

## 核心原则
- 每道错题必须给出思路引导，不只给答案
- 批注语言适合小学/初中生理解
- 图片不清晰时如实说明，不猜测
```

### AGENTS.md（marker）——核心

```markdown
## 触发方式
收到 sessions_send 来的 JSON 消息，task="grade"
消息字段：qq_user_id / student / grade / batch_id / image_dir / image_count
**注：无 subject 字段，需自动识别每张图的科目**

## 批改流程（支持混科）

Step 1. 解析任务参数
Step 2. 遍历 image_dir 下所有图片，**对每张图**：
  2a. 用视觉能力判断该图片的科目（数学/语文/英语/其他）
  2b. 若无法判断（图片模糊/非作业）→ 记录为"待确认"
Step 3. 按识别出的科目将图片分组：
  数学组: [img_1.jpg, img_3.jpg]
  语文组: [img_2.jpg]
  待确认: [img_4.jpg]
Step 4. 若有"待确认"图片 → sessions_send 回 coordinator：
  {"status": "need_confirm", "uncertain_images": ["img_4.jpg 无法识别科目，请告知"]}
  coordinator 询问家长后再 sessions_send 回来补充科目信息
Step 5. 对**每个科目组**独立批改：
  5a. 按批改标准逐题分析（见 SKILL.md）
  5b. 生成该科目的 result_{科目}.json
  5c. 生成该科目的 analysis_{科目}.md
  5d. 生成该科目的 report_{科目}.pdf
  5e. 存储：
      python3 .../storage.py save_result \
        --qq {qq} --student {name} --batch {bid} \
        --subject {科目} --json '{结果JSON}'
Step 6. 所有科目批改完成后，sessions_send 回传 coordinator：
  {
    "status": "done",
    "batch_id": "...",
    "results": [
      {"subject": "数学", "score": "85/100", "pdf_path": "...", "summary": "..."},
      {"subject": "语文", "score": "92/100", "pdf_path": "...", "summary": "..."}
    ]
  }


## 批改标准
### 数学
- 识别题号、内容、学生答案，核对，检查过程
- 错误类型：计算错误 / 概念混淆 / 审题不清 / 粗心漏题

### 语文  
- 字词（字典标准）、标点、阅读理解（关键词完整性）
- 作文：结构/内容/语言三维度

### 英语
- 拼写（完全一致）、语法（时态/主谓一致）、大小写

## 结果 JSON 格式
{
  "score": 85, "total": 100,
  "overall": "整体不错！计算需细心。",
  "weak_points": ["两位数乘法"],
  "corrections": [
    {
      "question": "第3题",
      "student_answer": "40", "correct_answer": "42",
      "is_correct": false,
      "error_type": "计算错误",
      "thinking_guide": "7×6=42，用7×5=35再加7"
    }
  ]
}

## 向用户展示格式（由 coordinator 展示）
整体：这次整体不错！计算部分要细心。
得分：85/100
✅ 第1题：正确
❌ 第3题：答"40"，正确"42"
   类型：计算错误
   思路：7×6=42，用7×5=35再加7来计算
薄弱点：两位数乘法
建议：每天练5道乘法口算。
```

---

## 七、inspector 文件设计

### IDENTITY.md
```markdown
# 学习分析师 📊
根据历史批改数据，生成周报、月报、错题本和练习题。
```

### AGENTS.md（inspector）

```markdown
## 触发方式
收到 sessions_send 来的 JSON 消息，task="report"

## 时间范围计算
- weekly：本周一 00:00 ~ 今天
- monthly：本月 1 日 00:00 ~ 今天
- mistakes：全部历史（或指定 start/end）

## 报告生成流程
Step 1. 解析任务参数（type/student/subject/start/end）
Step 2. python3 ...generate_report.py \
         --qq {qq} --student {name} --type {type} \
         --subject {subj} --start {start} --end {end}
         → 返回汇总JSON + Word文件路径
Step 3. sessions_send 回传给 coordinator：
        {"word_path": "...", "summary": "本周批改X次，平均XX分..."}

## 无数据时
sessions_send 回传：{"error": "该时间段内暂无批改记录"}
coordinator 向家长说明。

## 练习题流程（task="exercises"）
Step 1. python3 ...generate_exercises.py \
         --qq {qq} --student {name} --subject {subj} --count {n}
         → 返回薄弱知识点
Step 2. 用内置能力生成题目
Step 3. python3 ...export_word.py --type exercises --qq {qq} --student {name}
Step 4. 回传 Word 路径给 coordinator
```

---

## 八、Python 脚本 API

所有脚本路径前缀：`/home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/`

### storage.py

| 子命令 | 参数 | 功能 |
|--------|------|------|
| `init_child` | `--qq --name --grade --subjects` | 注册孩子 |
| `list_children` | `--qq` | 列出孩子（JSON） |
| `gen_batch_id` | `--student` | 生成批次ID |
| `init_batch` | `--qq --student --batch --subject` | 创建批次目录 |
| `save_result` | `--qq --student --batch --json '{}'` | 保存结果+生成 summary.txt |
| `query_score` | `--qq --student [--subject] [--limit]` | 查近N次成绩 |
| `get_results` | `--qq --student [--subject] [--start] [--end]` | 按时段获取所有结果 |

### export_word.py / export_pdf.py

```
python3 export_word.py
  --type  grade_report | weekly | monthly | mistakes | exercises
  --qq    {qq_user_id}
  --student {name}
  [--batch {batch_id}]
  [--start {YYYY-MM-DD}]  [--end {YYYY-MM-DD}]
  [--output {path}]
```

**grade_report Word 文档结构**：封面（学生/科目/日期/得分）→ 逐题批改表格（题号|✅❌|学生答案|正确答案|思路提示）→ 薄弱点总结 → 鼓励语

### generate_report.py

```
python3 generate_report.py
  --qq {qq}  --student {name}
  --type weekly|monthly|mistakes
  [--subject {科目|all}]  [--start]  [--end]
```

逻辑：读取时段内所有 result.json → 汇总（均分/高频错误类型/薄弱点）→ 输出 JSON 到 stdout + 调 export_word.py 生成 Word → 返回 Word 路径

### generate_exercises.py

```
python3 generate_exercises.py
  --qq {qq}  --student {name}  --subject {科目}
  [--count 5]  [--difficulty 简单|中等|困难]
```

逻辑：读取错题历史 → 输出薄弱点 JSON（供 Agent 生成题目）→ Agent 生成后调 export_word.py

---

## 九、数据格式

### children.json
```json
{
  "qq_user_id": "123456789",
  "children": [
    {"name": "小明", "grade": "三年级", "subjects": ["语文","数学","英语"]},
    {"name": "小红", "grade": "一年级", "subjects": ["语文","数学"]}
  ]
}
```

### 每批次目录结构

```
data/{qq}/{student}/{batch_id}/
├── original/           ← 原始图片（img_1.jpg, img_2.jpg...）
├── result.json         ← 完整批改结果（用于生成PDF/Word，含题目详情）
├── analysis.md         ← 分析文档（仅错误类型/原因，用于事后出题分析）
├── summary.txt         ← 一行摘要（给 inspector 快速读）
├── report.pdf          ← 发给家长的批改报告
└── report.docx         ← 可选 Word 版本
```

### result.json（完整批改结果，用于生成 PDF/Word）
```json
{
  "batch_id": "20260322_143000_a3f1",
  "qq_user_id": "123456789",
  "student": "小明", "subject": "数学", "grade": "三年级",
  "timestamp": "2026-03-22T14:30:00",
  "score": 85, "total": 100,
  "overall": "整体不错，计算细心度需加强",
  "weak_points": ["两位数乘法", "进位计算"],
  "corrections": [
    {
      "question": "第3题",
      "student_answer": "40", "correct_answer": "42",
      "is_correct": false,
      "error_type": "计算错误",
      "thinking_guide": "7×6=42，用7×5=35再加7"
    }
  ]
}
```

### analysis.md（分析文档，不含具体题目，用于事后出题）

各科有独立的错误维度，但格式统一。marker Agent 根据科目选用对应的错误类型分类。

---

**数学 analysis.md**
```markdown
# 批次分析 | 小明 | 数学 | 三年级 | 2026-03-22

## 得分
85/100（共批改2张图片）

## 错误记录
| 错误类型 | 错误原因 | 次数 |
|---------|---------|------|
| 计算错误 | 两位数乘法进位混淆（7×5与7×6） | 2 |
| 审题不清 | 忽略"至少"条件词，计算方向错误 | 1 |

## 薄弱知识点
- 两位数乘法（连续出错）
- 含条件词的应用题审题

## 出题建议
- 两位数乘法3-5道，覆盖7×6~9×9
- 含"至少""最多"条件词应用题1-2道
```

**数学错误类型标准（两层设计）**

**第一层：粗粒度维度**（写入 analysis.md 统计字段，基于国内数学课标）

| 错误维度 | 说明 |
|---------|------|
| 计算错误 | 四则运算出错、进退位错误、小数点位置错 |
| 概念混淆 | 对定义/定理/公式理解有偏差（如面积与周长混淆）|
| 公式记错 | 公式本身记忆错误或写错 |
| 审题不清 | 忽略条件词（"至少""整数""正数"）或误读题意 |
| 单位换算错误 | 长度/面积/时间/人民币等单位换算出错 |
| 粗心漏题 | 题目存在、学生未作答 |
| 逻辑推理错误 | 解题步骤跳步、推导方向错误（多见于应用题）|

**第二层：细粒度原因**（写入"错误原因"字段，自由描述）

> 示例：错误维度"计算错误"，错误原因"7×6=42 写成 7×6=40，乘法口诀记忆不牢"


---

**语文 analysis.md**
```markdown
# 批次分析 | 小红 | 语文 | 二年级 | 2026-03-22

## 得分
88/100（共批改1张图片）

## 错误记录
| 错误维度 | 错误类型 | 错误原因 | 次数 |
|---------|---------|---------|------|
| 字词书写 | 形近字混淆 | "己"与"已"混用，偏旁记忆不牢 | 2 |
| 阅读理解 | 要点缺失 | 答题遗漏"心情"维度，只答了"事件" | 1 |
| 标点符号 | 误用 | 句末用逗号代替句号 | 1 |

## 薄弱知识点
- 形近字辨析（己/已/巳）
- 阅读理解多维度答题方法

## 出题建议
- 形近字填空3组，含己/已/巳辨析
- 短文阅读1篇，要求从"事件+心情+原因"三维回答
```

**语文错误类型标准（两层设计）**

**第一层：粗粒度维度**（写入 analysis.md 统计字段，基于教育部课标）

| 错误维度 | 细化说明 |
|---------|---------|
| 字词书写 | 别字、多字、漏字、笔画错误（形近字 / 同音字）|
| 标点符号 | 误用、漏用、句末标点、引号书名号 |
| 病句·搭配不当 | 主谓搭配 / 动宾搭配 / 修饰语搭配错误 |
| 病句·成分残缺 | 缺主语、缺谓语、缺宾语 |
| 病句·成分赘余 | 重复累赘（"大家都普遍认为"）|
| 病句·语序不当 | 定/状语位置错、分句顺序乱 |
| 病句·结构混乱 | 句式杂糅（两种说法混用）|
| 病句·不合逻辑 | 自相矛盾、因果错误、概念混用 |
| 阅读理解 | 要点缺失 / 答非所问 / 概括不准 |
| 作文·结构 | 缺开头/结尾 / 段落混乱 |
| 作文·内容 | 偏题 / 内容空洞 / 举例不当 |
| 作文·语言 | 语句不通顺 / 用词重复 / 缺少描写 |

**第二层：细粒度原因**（写入"错误原因"字段，自由描述）

> 示例：错误维度"病句（搭配不当）"，错误原因""提高水平"误用为"改善水平"，动宾搭配错误"

---

**英语 analysis.md**
```markdown
# 批次分析 | 小明 | 英语 | 五年级 | 2026-03-22

## 得分
78/100（共批改2张图片）

## 错误记录
| 错误维度 | 错误类型 | 错误原因 | 次数 |
|---------|---------|---------|------|
| 拼写 | 元音字母遗漏 | "friend"写成"freind"，ei/ie规则未掌握 | 3 |
| 语法·时态 | 一般过去时错误 | 用现在时描述过去事件，动词未变形 | 2 |
| 语法·主谓一致 | 第三人称单数遗漏 | "He go"未加s | 1 |
| 大小写 | 句首未大写 | 句子开头字母小写 | 2 |

## 薄弱知识点
- ei/ie拼写规则
- 一般过去时动词变形
- 句首大写习惯

## 出题建议
- ei/ie单词填空5道（believe/receive/friend/field等）
- 改正句子时态练习3道（现在时改过去时）
- 大小写纠错练习一段短文
```

**英语错误类型清单**（marker 从这里选）：

**英语错误类型标准（两层设计）**

**第一层：粗粒度维度**（写入 analysis.md 统计字段，基于 James 错误分类法 + 国内中考五维）

| 错误维度 | 说明 |
|---------|------|
| 拼写 | 字母遗漏/顺序错/同音词混淆/规则错（如 ei/ie、双写辅音）|
| 时态/语态 | 一般现/过/将来时、现在完成时、被动语态 |
| 词形变化 | 第三人称单数 s、过去式变形、形容词比较级最高级、名词复数 |
| 句子结构 | 缺主语、缺谓语、疑问句语序（如 "What you want?"）、定语从句错误 |
| 词汇/搭配 | 近义词误用、词性错误（名词/动词混用）、介词搭配、冠词 a/an/the |
| 大小写标点 | 句首未大写、专有名词未大写、句末标点误用 |

**第二层：细粒度原因**（写入"错误原因"字段，自由描述）

> 示例：错误维度"词形变化"，错误原因"'He go to school'缺第三人称单数 s，应为 'goes'"

---

### summary.txt（各科通用，给 inspector 快速读）

格式固定，科目字段自动适配：

```
批次：{batch_id} | {student} | {subject} | {grade}
时间：{datetime} | 得分：{score}/{total}
主要错误：{错误类型1}×{次数}、{错误类型2}×{次数}（最多列3种）
薄弱点：{weak_point_1}、{weak_point_2}
批改图片数：{n}张
总评：{overall_one_line}
```

示例（语文）：
```
批次：20260322_160000_b2c3 | 小红 | 语文 | 二年级
时间：2026-03-22 16:00 | 得分：88/100
主要错误：形近字混淆×2、阅读要点缺失×1
薄弱点：己/已/巳辨析、多维度答题
批改图片数：1张
总评：字词书写需加强，阅读理解答题方法待训练
```


---

## 十、服务器部署（SETUP.md 内容）

### 1. 克隆代码

```bash
cd /tmp
git clone <你的私有仓库> xunyu
```

### 2. 分别建立各 Agent workspace（软链接脚本目录）

```bash
# 创建 coordinator workspace
cp -r xunyu/coordinator /home/ubuntu/.openclaw/workspace-xunyu-coordinator
# 在 workspace 中软链接公共脚本（避免重复）
ln -s /tmp/xunyu/scripts /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts
# 创建 data 目录
mkdir -p /home/ubuntu/.openclaw/workspace-xunyu-coordinator/data

# 创建 marker workspace
cp -r xunyu/marker /home/ubuntu/.openclaw/workspace-xunyu-marker
ln -s /tmp/xunyu/scripts /home/ubuntu/.openclaw/workspace-xunyu-marker/scripts
# marker 共享同一个 data 目录（软链接）
ln -s /home/ubuntu/.openclaw/workspace-xunyu-coordinator/data \
      /home/ubuntu/.openclaw/workspace-xunyu-marker/data

# 创建 inspector workspace
cp -r xunyu/inspector /home/ubuntu/.openclaw/workspace-xunyu-inspector
ln -s /tmp/xunyu/scripts /home/ubuntu/.openclaw/workspace-xunyu-inspector/scripts
ln -s /home/ubuntu/.openclaw/workspace-xunyu-coordinator/data \
      /home/ubuntu/.openclaw/workspace-xunyu-inspector/data
```

### 3. 安装依赖

```bash
pip3 install python-docx reportlab Pillow
```

### 4. 更新 openclaw.json

将 `agents.list` 和对应 workspace 路径填入（见第三节配置）。

### 5. 重启 Gateway

```bash
openclaw gateway restart
```

---

## 十一、初始化与依赖安装

### OpenClaw 的依赖机制（官方文档结论）

OpenClaw 对 Skill 依赖的处理分两层：

| 机制 | 作用 | 是否自动安装 |
|------|------|-------------|
| `SKILL.md metadata.requires.bins` | 声明需要哪些可执行文件在 PATH 上，**加载时检查**，不满足则 skill 不生效 | ❌ 只检查，不安装 |
| `agents.defaults.sandbox.docker.setupCommand` | 沙箱容器启动后执行一次安装命令 | ✅ 但仅限沙箱模式 |
| `BOOTSTRAP.md` | 首次会话时 Agent 执行任务，可以包含 pip install | ✅ 推荐用于非沙箱 |

**我们的方案：非沙箱模式 + BOOTSTRAP.md 安装依赖**

---

### SKILL.md metadata 写法

在三个 skill 的 `SKILL.md` 中声明对 `python3` 的依赖（加载时检查），确保 Python3 必须已安装：

```yaml
---
name: marker
description: 负责作业图片的视觉批改，生成结构化批改结果和PDF报告
metadata: {"openclaw": {"requires": {"bins": ["python3"]}, "os": ["linux", "darwin"]}}
---
```

> `bins: ["python3"]` 只做存在性检查，不自动安装。Python3 在 Ubuntu 服务器上默认已有。

---

### BOOTSTRAP.md 中执行依赖安装（coordinator）

将 `pip install` 加入 BOOTSTRAP.md 的第 0 步（其他步骤照旧）：

```markdown
# 首次运行任务（完成后删除本文件）

## Step 0：安装 Python 依赖
首先检查并安装必要的 Python 库：
```bash
pip3 install python-docx reportlab Pillow --quiet
```
若安装失败，向用户告知："系统依赖安装失败，请联系管理员运行：pip3 install python-docx reportlab Pillow"，并停止后续步骤。

## Step 1：欢迎新用户
向用户发送欢迎消息...
（其余步骤不变：询问孩子信息 → 注册 → 更新USER.md → 删除本文件）
```

---

### 为什么用 BOOTSTRAP 而不是手动 pip install

| 方案 | 优缺点 |
|------|--------|
| 手动 `pip3 install`（SETUP.md 第3步） | 简单直接，但需要人工操作，可能漏掉 |
| BOOTSTRAP.md 自动安装 | 第一个家长触发时自动安装，无需记住 |
| SKILL.md setupCommand（沙箱） | 不用沙箱，不适用 |

**最终方案：两者结合**
- `SETUP.md` 里写 `pip3 install`（部署时手动运行一次，确保环境正确）
- `BOOTSTRAP.md` 里也写 `pip3 install --quiet`（防漏，幂等，反复运行无害）

这样无论是否记得手动安装，第一次使用时都会自动补装。

---



| 文件 | 说明 |
|------|------|
| `coordinator/IDENTITY.md` | ✅ 见上方 |
| `coordinator/SOUL.md` | ✅ 见上方 |
| `coordinator/AGENTS.md` | ✅ 见上方 |
| `coordinator/USER.md` | ✅ 见上方（模板）|
| `coordinator/BOOTSTRAP.md` | ✅ 见上方 |
| `coordinator/skills/coordinator/SKILL.md` | 待写 |
| `marker/IDENTITY.md` | ✅ 见上方 |
| `marker/SOUL.md` | ✅ 见上方 |
| `marker/AGENTS.md` | ✅ 见上方 |
| `marker/skills/marker/SKILL.md` | 待写 |
| `inspector/IDENTITY.md` | ✅ 见上方 |
| `inspector/AGENTS.md` | ✅ 见上方 |
| `inspector/skills/inspector/SKILL.md` | 待写 |
| `scripts/storage.py` | 待写 |
| `scripts/export_word.py` | 待写 |
| `scripts/export_pdf.py` | 待写 |
| `scripts/generate_report.py` | 待写 |
| `scripts/generate_exercises.py` | 待写 |
| `SETUP.md` | ✅ 见上方 |
| `.gitignore` | 待写 |
| `requirements.txt` | 待写 |
