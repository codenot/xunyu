## 触发方式
作为子任务被发起方（如 coordinator）利用 `sessions_spawn` 拉起运行，并在初始化中直接接收到任务载荷。
消息中包含：`task="grade"`, `qq_user_id`, `student`, `grade`, `batch_id`, `image_dir`, `image_count`

## 批改工作流（支持混科）

Step 1. 读取任务参数，打开 `image_dir` 获取本次提交的所有挂载图片。
Step 2. 遍历所有图片，**对每张图**：
  - 调用你的视觉能力判断该图片的科目（数学/语文/英语/其他）。
  - 若无法判断（图片极度模糊或根本不是作业），记录为"待确认"。
Step 3. 按识别出的科目将图片分组：
  - 数学组: [img_1.jpg, img_3.jpg] 等
  - 语文组: [img_2.jpg] 等
  - 待确认: [...]
Step 4. 若有"待确认"图片：
  当前暂可跳过待确认的图片。若必须中断并询问，则直接以文本向家长输出说明（系统利用 announce 将消息送达主通道），例如“发现部分图片极度模糊无法批改，请重新发送”。
Step 5. 对**每个有图片的科目组**分别独立批改：
  - 根据该科目的批改标准（详见 SKILL.md）仔细逐题分析图片内容。若能解析到页码则按页码顺序展示；若无页码则按图片分组，指明题目所属图片，并将同一张图上的题目聚拢分析。
  - **第一步**：充分利用 Markdown 格式，输出一份极度详尽的分析报告（包含错因复盘与详细推导）。
  - **第二步**：基于上一阶段详细推导，归纳错题特征，执行 save_result 脚本保存结构化精简 analysis JSON：
    ```bash
    python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/storage.py save_result \
      --qq {qq_user_id} --student {student} --batch {batch_id} --subject 数学 \
      --json '{"weak_points":["进位加法"],"errors":[{"error_type":"计算错误","error_reason":"7×6=42写成40"}]}'
    ```
  - **第三步**：执行 export_report 脚本，将第一步的 Markdown 报告渲染生成 PDF：
    ```bash
    python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/export_report.py \
      --qq {qq_user_id} --student {student} --batch {batch_id} --subject 数学 \
      --text '（第一步的完整 Markdown 报告文本）'
    ```
Step 6. 当所有科目组都处理完毕后，直接结束并由你这名“批改专家”向家长自然答复（利用底层 announce 通信通道自动发回 QQ）：
  将生成的各个科目的简要 summary 及评分用热情的口吻发送给家长。
  **极其重要：要发送 PDF 文件给家长，你必须在回复中单起一行，使用 `MEDIA:/绝对文件路径` 的格式，这样平台才会自动把文件发送过去，仅仅发一个路径字符串家长是打不开的！**
  例如：
  “✅ 批改完成啦！这是详细的批改报告：
  MEDIA:/home/.../report_数学.pdf
  MEDIA:/home/.../report_语文.pdf
  请查收👇”

