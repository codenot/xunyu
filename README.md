# 荀彧（xunyu）辅导作业系统

## 项目简介
荀彧（xunyu）是一个基于 OpenClaw Gateway 的作业辅导系统，面向 QQ 机器人渠道部署。仓库提供三类 Agent 工作区、共享脚本和网关配置，部署后可完成批改、报告和学习巩固相关流程。

## 核心能力
- `coordinator`：负责 QQ 入口、意图识别、批次收集和任务分发。
- `marker`：负责图片批改、学科识别和批改结果落盘。
- `inspector`：负责周报、月报、错题总结和练习题生成。
- `scripts/`：提供共享的存储、导出和报表脚本。

## 快速部署
1. 克隆仓库并进入目录。
   ```bash
   git clone git@github.com:codenot/xunyu.git
   cd xunyu
   ```
2. 执行安装脚本。
   ```bash
   ./install.sh
   ```
3. 将仓库根目录的 `openclaw.json` 复制或合并到 `/home/ubuntu/.openclaw/openclaw.json`。
4. 重启网关。
   ```bash
   openclaw gateway restart
   ```
5. 注意：`install.sh` 里的 OpenClaw 目录是硬编码的 `/home/ubuntu/.openclaw`，部署前请确保你的 OpenClaw 实际使用这个路径，或者先修改脚本再部署。

## 网关配置要点
- `channels.qqbot.agentId` 必须指向 `coordinator`。
- `agents.list` 必须注册三个 Agent：`coordinator`、`marker`、`inspector`。
- 网关使用前，请确认 `/home/ubuntu/.openclaw/openclaw.json` 已包含仓库中的 Agent 配置。
- `coordinator`、`marker`、`inspector` 的 `workspace` 必须分别指向 `install.sh` 创建的软链接路径：
  - `/home/ubuntu/.openclaw/workspace-xunyu-coordinator`
  - `/home/ubuntu/.openclaw/workspace-xunyu-marker`
  - `/home/ubuntu/.openclaw/workspace-xunyu-inspector`
- 依赖由 `requirements.txt` 提供，当前包含 `python-docx`、`reportlab`、`Pillow`。

## 启动与联调
启动完成后，向绑定的 QQ 账号发送“帮我批改作业”进行联调。若配置和网关都正常，`coordinator` 应先返回收集/登记引导，再继续进入孩子或批次收集流程。

## 目录结构
仓库部署时，重点关注以下本地目录：

```text
xunyu/
├── agents/
│   ├── coordinator/
│   ├── marker/
│   └── inspector/
├── scripts/
├── openclaw.json
├── requirements.txt
├── SETUP.md
├── docs/
│   ├── design.md
│   └── plan.md
└── install.sh
```

## 补充文档
- [SETUP.md](SETUP.md)
- [docs/design.md](docs/design.md)
- [docs/plan.md](docs/plan.md)
