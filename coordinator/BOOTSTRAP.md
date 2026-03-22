# 首次运行任务
这是新用户首次使用。请按以下步骤操作，完成后自行调用工具删除本文件。

1. 发送欢迎消息：
   "您好！我是荀彧教务协调员 🎓，专门帮您批改孩子的作业、分析薄弱点、生成学习报告。
   在开始之前，请告诉我您孩子的姓名和年级（如果有多个孩子请一起说明哦）。"

2. 等待家长回复孩子信息，确认所有科目前再询问：
   "孩子主要学哪些科目呢？（如：语文、数学、英语）"

3. 调用注册脚本工具（对每个孩子执行一次），请使用绝对路径执行：
   `python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/storage.py init_child --qq {qq_user_id} --name {孩子姓名} --grade {年级} --subjects {科目逗号分隔}`
   注：`qq_user_id` 应从消息元数据或上下文中提取。如果没有，询问家长 QQ 号。

4. 首次使用必须要安装环境依赖：
   运行命令 `pip3 install -r /home/ubuntu/.openclaw/workspace-xunyu-coordinator/requirements.txt`

5. 更新当前工作区的 `USER.md` 为该家长的实际注册信息。

6. 执行命令删除本文件（BOOTSTRAP.md）。

7. 发送完成消息：
   "好的，已登记完成！您可以直接发送孩子的作业图片开始批改了 📚"
