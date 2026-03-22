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
  - 根据该科目的批改标准（详见 SKILL.md）仔细逐题分析图片内容。
  - 生成针对本学科的最终评改结论 JSON。
  - 利用系统脚本执行保存动作，例如对于数学组：
    ```bash
    python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/storage.py save_result --qq {qq_user_id} --student {student} --batch {batch_id} --subject 数学 --json '{结果JSON}'
    ```
    *(注：替换命令中的参数为实际值，{结果JSON} 为你生成的标准 JSON 字符串，务必使用单引号包裹)*
  - 利用脚本生成 PDF 报告，例如：
    ```bash
    python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/export_pdf.py --qq {qq_user_id} --student {student} --batch {batch_id} --subject 数学
    ```
Step 6. 当所有科目组都处理完毕后，通过 sessions_send 回传给 coordinator 汇总信息：
  ```json
  {
    "status": "done",
    "batch_id": "...",
    "results": [
      {"subject": "数学", "score": 85, "pdf_path": "/home/.../report_数学.pdf", "summary": "整体不错！..."},
      {"subject": "语文", "score": 92, "pdf_path": "/home/.../report_语文.pdf", "summary": "优秀"}
    ]
  }
  ```
