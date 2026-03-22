#!/bin/bash

set -e

# 获取当前脚本所在目录的绝对路径
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCLAW_DIR="/home/ubuntu/.openclaw"

echo "======================================"
echo "开始安装与配置 荀彧(Xunyu) 辅导系统..."
echo "探测到项目路径: $PROJECT_DIR"
echo "======================================"

echo "1. 安装 Python 相关依赖..."
pip3 install -r "$PROJECT_DIR/requirements.txt"

echo "2. 配置目录软链接环境..."
# 确保在 coordinator 目录下能够向上访问到公用的 scripts 与数据 data
cd "$PROJECT_DIR/agents/coordinator"
rm -f scripts
ln -s ../../scripts scripts
mkdir -p data

# 在 OpenClaw 平台的主配置目录下创建指向本项目的软链接
mkdir -p "$OPENCLAW_DIR"
cd "$OPENCLAW_DIR"

# 清理可能残留的旧文件夹或链接
rm -rf workspace-xunyu-coordinator workspace-xunyu-marker workspace-xunyu-inspector

echo "创建三大 Agent 工作区到 OpenClaw 的投射软链接..."
ln -s "$PROJECT_DIR/agents/coordinator" workspace-xunyu-coordinator
ln -s "$PROJECT_DIR/agents/marker" workspace-xunyu-marker
ln -s "$PROJECT_DIR/agents/inspector" workspace-xunyu-inspector

echo "======================================"
echo "✅ 环境部署与文件软链接创建成功！"
echo "以后拉取 git 更新后，代码将自动在 OpenClaw 中生效，无需再做移动。"
echo ""
echo "待办最后一步："
echo "1. 请将项目根目录 $PROJECT_DIR/openclaw.json 的内容覆盖或合并到 $OPENCLAW_DIR/openclaw.json 中。"
echo "2. 运行 openclaw gateway restart 即可启动所有 Agent！"
echo "======================================"
