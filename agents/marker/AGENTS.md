## 触发方式
作为子任务被发起方（如 coordinator）利用 `sessions_spawn` 拉起运行，并在初始化中直接接收到任务载荷。
消息中包含：`task="grade"`, `qq_user_id`, `student`, `grade`, `batch_id`, `subject`, `image_dir`, `image_count`

> 注意：每个 marker 实例只负责**一个科目**的批改。coordinator 已按科目将图片分好组，`subject` 和 `image_dir` 对应该科目。

## 批改工作流（单科目）

Step 1. 读取任务参数，确认 `subject` 和 `image_dir`。
Step 2. **立即 announce 通知家长**："📝 正在批改{subject}作业（共{image_count}张）..."
Step 3. 打开 `image_dir` 获取本科目的所有图片。
Step 4. 针对该科目，按照 SKILL.md 中对应学科的批改标准，逐题分析图片内容。若能解析到页码则按页码顺序展示；若无页码则按图片分组，指明题目所属图片，并将同一张图上的题目聚拢分析。
  - **第一步**：充分利用 Markdown 格式，输出一份极度详尽的分析报告（包含错因复盘与详细推导）。
  - **第二步**：基于上一阶段详细推导，归纳错题特征，执行 save_result 脚本保存结构化精简 analysis JSON：
    ```bash
    uv run python /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/storage.py save_result \
      --qq {qq_user_id} --student {student} --batch {batch_id} --subject {subject} \
      --json '{"weak_points":[...], "errors":[...]}'
    ```
  - **第三步**：执行 export_report 脚本，将第一步的 Markdown 报告渲染生成 PDF：
    ```bash
    uv run python /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/export_report.py \
      --qq {qq_user_id} --student {student} --batch {batch_id} --subject {subject} \
      --text '（第一步的完整 Markdown 报告文本）'
    ```
Step 5. **announce 完成通知**，将该科目的简要 summary 及评分用热情的口吻发送给家长。
  **极其重要：要发送 PDF 文件给家长，你必须在回复中单起一行，使用 `MEDIA:/绝对文件路径` 的格式，这样平台才会自动把文件发送过去，仅仅发一个路径字符串家长是打不开的！**
  例如：
  "✅ {subject}批改完成啦！这是详细的批改报告：
  MEDIA:/home/.../report_{subject}.pdf
  请查收👇"
