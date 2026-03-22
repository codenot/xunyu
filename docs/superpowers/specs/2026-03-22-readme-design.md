# README 设计说明

## 目标
为仓库补一份**部署优先型** `README.md`，让第一次进入仓库的使用者可以快速理解项目用途，并直接完成 OpenClaw 场景下的安装、配置与联调。

## 读者
- 主要读者：部署者 / 运维使用者
- 次要读者：需要快速了解目录和文档入口的开发者

## 内容结构
1. 项目简介
2. 核心能力
3. 快速部署
4. 网关配置要点
5. 启动与联调
6. 目录结构
7. 补充文档

## 写法原则
- 首页不展开实现细节，不塞长篇设计背景
- 所有命令以当前仓库实际存在的文件为准：`install.sh`、`requirements.txt`、`openclaw.json`
- 强调这是一个基于 OpenClaw Gateway 的多 Agent 作业辅导系统
- 对 `coordinator`、`marker`、`inspector` 只做职责级说明，不重复 `docs/design.md` 的全部设计细节
- README 自身保持简洁，复杂说明引导到 `SETUP.md`、`docs/design.md`、`docs/plan.md`

## 预期结果
- 使用者克隆仓库后，可以从 README 中直接找到部署命令
- 使用者知道必须检查 `channels.qqbot.agentId`、`agents.list` 和 Agent 目录结构
- 使用者知道如何重启网关并通过“帮我批改作业”进行联调
