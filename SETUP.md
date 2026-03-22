# 荀彧 (xunyu) 辅导系统自动化部署指南

本系统基于 OpenClaw Gateway 架构，目前支持通过一键软链接安装脚本快速挂载三大教务 Agent 到服务器后台。后续如果代码库有更新，您只需在此拉取 `git pull` 即可自动对后台生效！

## 一键自动部署

假设您已在您的服务器克隆或解压了本项目。

```bash
# 1. 登录到您的服务器，进入本项目根目录
cd /您放置代码的路径/xunyu/

# 2. 执行自动挂载脚本（包含自动部署 pip 依赖、并在 OpenClaw 目录下生成对应的角色工作区软链接）
./install.sh
```
*(注：安装脚本跑完后，它会自动把项目里的 `agents/coordinator`，`agents/marker`，`agents/inspector` 目录挂载投射到 `/home/ubuntu/.openclaw/` 目录下。)*

## 网关核心配置

安装完底层系统文件后，您需要将项目根目录自带的 `openclaw.json` 与您网关正在使用的配置字典进行合并或覆盖。

核心请检查以下三点必须包含在 `/home/ubuntu/.openclaw/openclaw.json` 中：
1. `channels.qqbot.agentId` 设定为 `"coordinator"`（唯一对外客服代表）。
2. 请确保直接拉取的 xunyu 工程配置目录结构如下：
   1. `agents/coordinator/`
   2. `agents/marker/`
   3. `agents/inspector/`
   4. `scripts/` (所有角色共用底座脚本体系)。
3. `agents.list` 为这三名教员配置了适合的模型能力（我们推荐在本项目配置文件中使用的 Doubao 及 Deepseek 模型组合以平衡多模态与性能）。

## 启动调试

所有部署与配置调整完毕后，请重启网关：
```bash
openclaw gateway restart
```

网关启动并连接到 QQ 机器人后，从绑定的账号给机器人发送“帮我批改作业”。
主控系统 `coordinator` 会开始引导您建立第一份家庭学生档案并存储至内部数据库。随后您可以任意发送试卷照片，体验智能批图。
