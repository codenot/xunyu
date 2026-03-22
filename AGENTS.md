# Repository Guidelines

## 项目结构与模块组织
- `scripts/` 存放共享 Python CLI 脚本，如 `storage.py`、`generate_report.py`、`export_pdf.py`。
- `coordinator/`、`marker/`、`inspector/` 是三个 OpenClaw Agent 工作区，目录内的 `AGENTS.md`、`IDENTITY.md`、`SOUL.md` 和 `skills/` 共同定义行为。
- `data/` 为运行期数据目录，结构为 `data/<qq>/<student>/<batch>/`；`docs/` 保存设计与计划，`openclaw.json` 保存网关配置。

## 构建、测试与开发命令
- `python3 -m pip install -r requirements.txt`：安装 `python-docx`、`reportlab`、`Pillow`。
- `python3 scripts/storage.py gen_batch_id --student 张三`：生成批次 ID。
- `python3 scripts/generate_report.py --qq 12345 --student 张三 --type weekly --subject all`：汇总历史结果。
- `python3 scripts/export_pdf.py --qq 12345 --student 张三 --batch 20260322_abcd --subject math`：生成 PDF 报告。
- 修改 `openclaw.json` 或 Agent 指令文件后，使用 `openclaw gateway restart` 重启网关。

## 代码风格与命名规范
- Python 统一使用 4 空格缩进，函数、变量、CLI 子命令采用 `snake_case`，模块级常量采用全大写。
- 新增逻辑优先放在 `scripts/`，用 `argparse` 暴露参数，保持单一职责。
- 输出文件沿用现有命名：`result_<subject>.json`、`analysis_<subject>.md`、`report_<subject>.pdf`。
- 仓库当前未配置 `ruff`、`black` 或 `pytest`；提交前至少整理 imports，并保证 UTF-8 中文输出正常。

## 测试指南
- 当前没有 `tests/` 目录，默认采用脚本级手工验证。
- 修改存储或聚合逻辑时，在 `data/` 下构造样例并检查输出 JSON/Markdown。
- 修改导出逻辑时，务必打开 PDF/Docx，确认中文字体、表格和路径正常。

## 提交与 Pull Request 规范
- 提交信息遵循 Conventional Commits，当前历史已使用 `feat: ...`；后续保持 `feat:`、`fix:`、`docs:` 这类前缀。
- PR 描述应写清影响的 Agent 或脚本、验证命令，以及是否改动 `openclaw.json`、依赖或文档。
- 涉及报告导出或提示词变更时，附上示例输出或截图；不要提交密钥、真实学生数据或临时批次文件。
