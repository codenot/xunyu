# 荀彧（xunyu）辅导作业系统 - 实施计划

本项目基于 OpenClaw 平台，旨在打造一个多 Agent 协同的作业辅导系统。

## 项目目标
建立支持多学科混发的作业批改、错题本生成、周月报总结和自动出题的 AI 系统，主要面向 QQ 渠道交互。

## 一、 系统架构

系统包含三个独立的 Agent：
1. **`coordinator`**: 教务协调员。负责与用户在 QQ 上交互，意图识别，图片批次收集，以及将任务分发。
   - **模型**：`doubao-seed-2.0-lite`
   - **Workspace**：`workspace-xunyu-coordinator`
2. **`marker`**: 阅卷老师。负责接收批改任务，利用视觉大模型自动按学科识别作业图片，进行多学科混批。
   - **模型**：`doubao-seed-2.0-pro`
   - **Workspace**：`workspace-xunyu-marker`
3. **`inspector`**: 督学/教研组长。负责根据历史批改数据（`analysis.md`），生成周报、月报、错题本以及练习题。
   - **模型**：`deepseek-v3.2`
   - **Workspace**：`workspace-xunyu-inspector`

## 二、 技术难点解决方案 (PDF & Word 生成)

根据用户需求和设计文档：
1. **Word 生成 (`export_word.py`)**: 将使用 `python-docx` 库。这是生成 `.docx` 文件的业界标准，非常适合生成结构化的周报、月报、以及包含错题和练习题的文档。能够完美支持中文和表格排版。
2. **PDF 生成 (`export_pdf.py`)**: 将使用 `reportlab` 库。用于生成单次作业的批改报告给家长看。**重要注意点**：原生 ReportLab 不支持中文，我们需要在脚本内注册开源的中文字体（如基于系统自带字体或动态下载开源的霞鹜文楷/黑体），以确保生成的 PDF 报告中文不会显示为黑框或乱码。

## 三、 实施步骤

我们将分阶段实现，使得底层依赖先行，Agent 逻辑在上层搭建。

### 阶段 1：底层环境与基础脚本开发层 (Python)
所有的 Python 脚本放在项目根目录 `scripts/` 下，所有的 Agent 将通过软链接共享这些脚本。
- [NEW] `scripts/storage.py`：负责用户数据的初始化、批次目录生成、结果保存和读取。
- [NEW] `scripts/export_word.py`：根据 JSON 数据生成精美的 Word 报告。
- [NEW] `scripts/export_pdf.py`：注册中文字体并使用 `reportlab` 将单次作业批改结果转换为 PDF 返回。
- [NEW] `scripts/generate_report.py`：统计多批次的 `analysis.md` 和 `result.json` 生成结构化的报告数据源。
- [NEW] `scripts/generate_exercises.py`：分析薄弱点数据源供大模型生成复习题。
- [NEW] `requirements.txt`：记录依赖。

### 阶段 2：Agent Workspace 配置层
为每个 Agent 创建独立的 workspace，并编写其元数据文件。
- **Coordinator Agent** (`/coordinator/`):
  - [NEW] `IDENTITY.md` & `SOUL.md`: 设定人设。
  - [NEW] `AGENTS.md`: 实现批次收集模式交互逻辑、使用 `sessions_send` 将任务传递给 marker 和 inspector。
  - [NEW] `BOOTSTRAP.md` / `USER.md`: 包含首次启动时的登记及依赖环境的自动安装命令(`pip install`)。
  - [NEW] `skills/coordinator/SKILL.md`: 意图识别的补充说明。
- **Marker Agent** (`/marker/`):
  - [NEW] `IDENTITY.md` & `SOUL.md` & `AGENTS.md`: 定义严格的批改行为，实现自动识别图片学科并生成两层颗粒度结果（`result_{subj}.json` & `analysis_{subj}.md`）。
  - [NEW] `skills/marker/SKILL.md`: 包含最新的语文、数学、英语两层颗粒度错误分类清单。
- **Inspector Agent** (`/inspector/`):
  - [NEW] `IDENTITY.md` & `SOUL.md` & `AGENTS.md`: 报告生成和下发逻辑。
  - [NEW] `skills/inspector/SKILL.md`: 文本报告编写指南。

### 阶段 3：网关配置及安装清单
- [MODIFY] `openclaw.json`: 注册三个 agent 的 list 和模型，配置 `channels.qqbot` 的入口至 `coordinator`。
- [NEW] `SETUP.md`: 编写给最终用户的统一部署与软链接安装文档。

## 四、 验证计划

1. **底层测试**：模拟产生一份包括中文字符的 `result.json`，在本地运行 Python 脚本，确认 `export_pdf.py` 成功加载中文字体，生成的 PDF 无乱码，且 `export_word.py` 工作正常。
2. **多轮收集机制测试**：测试 coordinator 能否正确响应"开始批改"，进入批次模式并等待"发完了"。
3. **通信测试**：确认 coordinator 的 `sessions_send` 成功将任务送达 marker。
4. **端到端测试**：给系统发多张跨学科（语文、数学混合）图片，测试自动分发、按学科独立建立结果文件并返回最终报告的全流程。
