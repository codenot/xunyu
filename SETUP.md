# 荀彧 (xunyu) 辅导系统部署包

## 环境准备
1. 确保您的服务器支持 python 3 和 pip3。
2. 安装所需第三方依赖：
   ```bash
   pip3 install -r requirements.txt
   ```
   注：该项目中用于生成精确中文 PDF 批改长图报告的 `export_pdf.py` 内部会自动安装内置的开源 NotoSans 字体文件供渲染所需。

## Core 部署及网络调通
系统核心基于 OpenClaw Gateway。
请确保直接拉取的 xunyu 工程配置目录结构正确：
1. `coordinator/` 
2. `marker/`
3. `inspector/`
4. `scripts/` (所有角色共用底座脚本体系)。

在您 Gateway 运行目录下的 `openclaw.json` 中配置这三名教员的信息（本项目内已有参考样板），同时确保 QQ 机器人入口 `channels.qqbot.agentId` 指向了 `coordinator`。

重启网关：
```bash
openclaw gateway restart
```

## 测试与联调
1. 启动后，您可以向绑定的家长端测试 QQ 号发送“帮我批改作业”。
2. coordinator 收到信息后会触发 `BOOTSTRAP.md` 上的引导机制进行档案录入，生成 `/data/您的QQ/您的孩子/...` 本地目录。
3. 您可以开始往里面传入模拟的混合语文、数学作业照片，并结束传输，系统会自动按照 marker -> inspector 分布式运转工作流。

一切完毕。
