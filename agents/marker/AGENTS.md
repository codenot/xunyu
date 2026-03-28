## 触发方式
收到通过 sessions_send 传来的 JSON 消息（由 coordinator 发送），且 `task="grade"`。
消息中包含：`qq_user_id`, `student`, `grade`, `batch_id`, `image_dir`, `image_count`

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
  立即中断批改，通过 sessions_send 回传消息给 coordinator，让家长处理（当前暂可跳过待确认的图片）。
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
Step 6. 当所有科目组都处理完毕后，通过 sessions_send 回传给 coordinator 汇总信息：
  ```json
  {
    "status": "done",
    "batch_id": "...",
    "results": [
      {"subject": "数学", "pdf_path": "/home/.../report_数学.pdf", "summary": "薄弱点：进位加法、乘法口诀"},
      {"subject": "语文", "pdf_path": "/home/.../report_语文.pdf", "summary": "整体优秀"}
    ]
  }
  ```

