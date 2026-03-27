# Marker 重设计实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 marker 的职责拆分为两条独立流水线：大模型自由输出评语→PDF，结构化 analysis JSON→存储；同时删除 export_pdf.py，重写 generate_report.py。

**Architecture:** marker SKILL.md 定义两段独立输出；`save_result` 只写 `analysis_{subject}.json`（含 errors 列表 + weak_points）；`export_report.py` 接收自由文本直接渲染 PDF；`generate_report.py` 读 analysis JSON 汇总。

**Tech Stack:** Python 3, reportlab (已有字体逻辑), argparse, unittest

---

## Task 1: 重写 `agents/marker/skills/marker/SKILL.md`

**Files:**
- Modify: `agents/marker/skills/marker/SKILL.md`

**Step 1: 确认新 JSON 格式**

新的 `analysis` JSON 只保留两组字段：

```json
{
  "weak_points": ["进位加法", "病句识别"],
  "errors": [
    {
      "question": "第3题",
      "student_answer": "40",
      "correct_answer": "42",
      "error_type": "计算错误",
      "error_reason": "7×6=42，学生错用40，口诀不熟",
      "thinking_guide": "7×6=42，可用7×5+7推导，注意不要和邻近口诀混淆"
    }
  ]
}
```

**Step 2: 修改 SKILL.md**

用以下内容完全替换 `agents/marker/skills/marker/SKILL.md` 中 "## JSON 输出格式要求" 之后的全部内容：

```markdown
## 输出要求

每次批改分两步输出，**顺序不可颠倒**：

### 第一步：写给家长的评语（直接输出，不含 JSON）

先用自然语言写一段适合家长阅读的评语，态度亲切。内容包含：
- 本次作业整体表现（先肯定优点）
- 主要错误和原因（简洁）
- 下一步建议

> 无格式要求，大模型自由发挥即可。评语写完后，输出以下分隔线：
> ```
> ---REPORT_END---
> ```

### 第二步：调用存储脚本保存结构化分析

紧接着执行 bash 命令，将结构化 JSON 写入存储（**JSON 不含评语文本**）：

```bash
python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/storage.py save_result \
  --qq {qq_user_id} --student {student} --batch {batch_id} --subject 数学 \
  --json '{"weak_points":["进位加法"],"errors":[{"question":"第3题","student_answer":"40","correct_answer":"42","error_type":"计算错误","error_reason":"口诀不熟","thinking_guide":"用7×5+7推导"}]}'
```

**analysis JSON 字段说明：**
- `weak_points`：概括出错题背后的薄弱知识点（字符串列表）
- `errors`：仅包含做错的题（is_correct=false），每条包含：
  - `question`：题号或题目摘要
  - `student_answer`：学生的答案
  - `correct_answer`：正确答案
  - `error_type`：粗粒度错误类型（见各学科标准）
  - `error_reason`：细粒度原因（自由描述）
  - `thinking_guide`：思路引导，像老师一样引导，不能只给答案

### 第三步：调用脚本生成 PDF

```bash
python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/export_report.py \
  --qq {qq_user_id} --student {student} --batch {batch_id} --subject 数学 \
  --text '（将第一步写的完整评语粘贴于此）'
```
```

**Step 3: Commit**

```bash
git add agents/marker/skills/marker/SKILL.md
git commit -m "feat: marker SKILL.md 拆分为评语+analysis两步输出"
```

---

## Task 2: 重写 `agents/marker/AGENTS.md`

**Files:**
- Modify: `agents/marker/AGENTS.md`

**Step 1: 更新工作流 Step 5**

将 AGENTS.md 中的 Step 5 替换为新的两步流程（评语先出，再存 JSON，再生成 PDF）。回传给 coordinator 的 JSON 中去掉 `score` 字段，改为 `pdf_path` + `summary`（取 weak_points 前3条拼接）。

完整替换 Step 5 内容为：

```markdown
Step 5. 对**每个有图片的科目组**分别独立批改：
  - 根据该科目的批改标准（详见 SKILL.md）仔细逐题分析图片内容。
  - **第一步**：用自然语言写给家长的评语，输出 `---REPORT_END---` 做结尾。
  - **第二步**：执行 save_result 脚本保存 analysis JSON（只含 weak_points + errors）：
    ```bash
    python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/storage.py save_result \
      --qq {qq_user_id} --student {student} --batch {batch_id} --subject 数学 \
      --json '{"weak_points":[...],"errors":[...]}'
    ```
  - **第三步**：执行 export_report 脚本生成 PDF：
    ```bash
    python3 /home/ubuntu/.openclaw/workspace-xunyu-coordinator/scripts/export_report.py \
      --qq {qq_user_id} --student {student} --batch {batch_id} --subject 数学 \
      --text '（评语全文）'
    ```
```

**Step 2: Commit**

```bash
git add agents/marker/AGENTS.md
git commit -m "feat: AGENTS.md 更新批改工作流为三步"
```

---

## Task 3: 重写 `scripts/storage.py` 中的 `save_result`

**Files:**
- Modify: `scripts/storage.py:77-109`（`save_result` 函数）
- Modify: `scripts/storage.py:111-173`（删除 `generate_analysis_md` 函数）
- Modify: `scripts/storage.py:175-204`（删除 `generate_summary_txt` 函数）
- Test: `tests/test_storage.py`（新建）

**Step 1: 写测试（失败）**

新建 `tests/test_storage.py`：

```python
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import datetime

from scripts import storage


class SaveResultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_dir = Path(self.tmp.name)

    def _run_save_result(self, subject, json_str):
        """Helper: patch DATA_DIR and call save_result via argparse simulation."""
        import argparse
        args = argparse.Namespace(
            qq="12345",
            student="张三",
            batch="20260323_test",
            subject=subject,
            json=json_str,
        )
        with patch.object(storage, "DATA_DIR", str(self.data_dir)):
            storage.save_result(args)

    def test_saves_analysis_json(self):
        payload = {
            "weak_points": ["进位加法"],
            "errors": [
                {
                    "question": "第3题",
                    "student_answer": "40",
                    "correct_answer": "42",
                    "error_type": "计算错误",
                    "error_reason": "口诀不熟",
                    "thinking_guide": "用7×5+7推导"
                }
            ]
        }
        self._run_save_result("数学", json.dumps(payload, ensure_ascii=False))

        out = self.data_dir / "12345" / "张三" / "20260323_test" / "analysis_数学.json"
        self.assertTrue(out.exists(), "analysis_数学.json 应该存在")
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertIn("weak_points", data)
        self.assertIn("errors", data)
        self.assertEqual(data["student"], "张三")
        self.assertEqual(data["subject"], "数学")

    def test_does_not_save_result_json(self):
        payload = {"weak_points": [], "errors": []}
        self._run_save_result("语文", json.dumps(payload, ensure_ascii=False))

        old_file = self.data_dir / "12345" / "张三" / "20260323_test" / "result_语文.json"
        self.assertFalse(old_file.exists(), "旧的 result_{subject}.json 不应该生成")

    def test_does_not_save_analysis_md(self):
        payload = {"weak_points": [], "errors": []}
        self._run_save_result("英语", json.dumps(payload, ensure_ascii=False))

        md_file = self.data_dir / "12345" / "张三" / "20260323_test" / "analysis_英语.md"
        self.assertFalse(md_file.exists(), "analysis_{subject}.md 不应该生成")

    def test_invalid_json_prints_error(self):
        import io, sys
        with patch.object(storage, "DATA_DIR", str(self.data_dir)):
            import argparse
            args = argparse.Namespace(
                qq="12345", student="张三", batch="20260323_test",
                subject="数学", json="not-valid-json"
            )
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                storage.save_result(args)
        self.assertIn("Error", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
```

**Step 2: 运行测试确认失败**

```bash
cd d:\devel\test\xunyu
python -m pytest tests/test_storage.py -v
```

期望：FAIL（`saves_analysis_json` 失败，当前写的是 `result_*.json` 而非 `analysis_*.json`）

**Step 3: 重写 `save_result` 及删除辅助函数**

替换 `scripts/storage.py` 第 77-204 行（`save_result`、`generate_analysis_md`、`generate_summary_txt` 三个函数）为：

```python
def save_result(args):
    """保存批改分析结果到 analysis_{subject}.json。
    
    期望 args.json 为包含 weak_points 和 errors 的 JSON 字符串。
    """
    batch_dir = os.path.join(get_user_dir(args.qq), args.student, args.batch)
    os.makedirs(batch_dir, exist_ok=True)

    try:
        result_data = json.loads(args.json)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return

    # 注入元数据
    result_data["batch_id"] = args.batch
    result_data["qq_user_id"] = args.qq
    result_data["student"] = args.student
    result_data["subject"] = args.subject
    if "timestamp" not in result_data:
        result_data["timestamp"] = datetime.datetime.now().isoformat()

    # 只写 analysis_{subject}.json，不再写 result_*.json / analysis_*.md / summary.txt
    analysis_path = os.path.join(batch_dir, f"analysis_{args.subject}.json")
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"Analysis saved to {analysis_path}")
```

**Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_storage.py -v
```

期望：4 个测试全部 PASS

**Step 5: 确认现有测试不受影响**

```bash
python -m pytest tests/test_generate_exercises.py -v
```

期望：全部 PASS（`generate_exercises` 读的仍是 `result_{subject}.json`，需在 Task 6 中更新）

**Step 6: Commit**

```bash
git add scripts/storage.py tests/test_storage.py
git commit -m "feat: save_result 重写，只写 analysis JSON，删除 generate_analysis_md/summary_txt"
```

---

## Task 4: 新建 `scripts/export_report.py`（取代 export_pdf.py）

**Files:**
- Create: `scripts/export_report.py`
- 复用 `export_pdf.py` 中的字体加载逻辑（`ensure_font`）

**Step 1: 创建文件**

```python
"""export_report.py — 将自由文本（大模型评语）渲染为 PDF。

用法：
    python3 scripts/export_report.py \
        --qq 12345 --student 张三 --batch 20260323_abcd --subject 数学 \
        --text '这次数学表现不错，继续努力！'

输出：data/{qq}/{student}/{batch}/report_{subject}.pdf
"""
import os
import argparse
import urllib.request
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "NotoSansSC-Regular.ttf")
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC-Regular.ttf"


def ensure_font():
    """下载并注册中文字体（如未存在）。"""
    if not os.path.exists(FONT_PATH):
        print("Downloading Chinese font (NotoSansSC) for PDF generation...")
        try:
            urllib.request.urlretrieve(FONT_URL, FONT_PATH)
        except Exception as e:
            print(f"Warning: Failed to download font: {e}")
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont("NotoSans", FONT_PATH))


def build_pdf(text: str, output_path: str, title: str = "批改报告"):
    """将自由文本按段落渲染为 PDF，不解析 Markdown 格式。"""
    ensure_font()
    font_name = "NotoSans" if os.path.exists(FONT_PATH) else "Helvetica"

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=30
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="Title_CN", fontName=font_name, fontSize=16,
        alignment=1, spaceAfter=16
    ))
    styles.add(ParagraphStyle(
        name="Body_CN", fontName=font_name, fontSize=11,
        leading=18, spaceAfter=6
    ))

    elements = [Paragraph(title, styles["Title_CN"])]
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            elements.append(Paragraph(stripped, styles["Body_CN"]))
        else:
            elements.append(Spacer(1, 8))

    doc.build(elements)
    print(f"PDF generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="将评语文本渲染为 PDF")
    parser.add_argument("--qq", required=True)
    parser.add_argument("--student", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--text", required=True, help="大模型输出的评语文本（自由格式）")
    args = parser.parse_args()

    batch_dir = os.path.join(DATA_DIR, str(args.qq), args.student, args.batch)
    os.makedirs(batch_dir, exist_ok=True)

    pdf_path = os.path.join(batch_dir, f"report_{args.subject}.pdf")
    title = f"批改报告 — {args.student} · {args.subject}"
    build_pdf(args.text, pdf_path, title=title)


if __name__ == "__main__":
    main()
```

**Step 2: 手工验证 PDF 生成**

```bash
cd d:\devel\test\xunyu
python scripts/export_report.py \
  --qq 99999 --student 测试 --batch 20260323_test --subject 数学 \
  --text "这次数学整体表现不错！计算部分有几处粗心错误，建议多练习进位加法。加油！"
```

期望：
- 输出 `PDF generated: data/99999/测试/20260323_test/report_数学.pdf`
- 打开 PDF，中文正常显示，内容为评语文本

**Step 3: Commit**

```bash
git add scripts/export_report.py
git commit -m "feat: 新建 export_report.py，接收自由文本渲染 PDF"
```

---

## Task 5: 删除 `scripts/export_pdf.py`

**Files:**
- Delete: `scripts/export_pdf.py`

**Step 1: 删除文件**

```bash
git rm scripts/export_pdf.py
```

**Step 2: Commit**

```bash
git commit -m "chore: 删除 export_pdf.py，由 export_report.py 取代"
```

---

## Task 6: 重写 `scripts/generate_report.py`

**Files:**
- Modify: `scripts/generate_report.py`（完全重写）
- Test: `tests/test_generate_report.py`（新建）

**Step 1: 写测试（失败）**

新建 `tests/test_generate_report.py`：

```python
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import sys

from scripts import generate_report


class GenerateReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_dir = Path(self.tmp.name)
        self.qq = "12345"
        self.student = "张三"

    def _write_analysis(self, batch_id, timestamp, subject, weak_points, errors=None):
        batch_dir = self.data_dir / self.qq / self.student / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "subject": subject,
            "timestamp": timestamp,
            "weak_points": weak_points,
            "errors": errors or [],
            "student": self.student,
            "batch_id": batch_id,
        }
        (batch_dir / f"analysis_{subject}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    def test_collect_reads_analysis_json(self):
        self._write_analysis("20260310_a", "2026-03-10T08:00:00", "数学",
                             ["进位加法", "乘法口诀"])
        result = generate_report.collect_analyses(
            self.data_dir, self.qq, self.student, subject="数学"
        )
        self.assertEqual(len(result), 1)
        self.assertIn("weak_points", result[0])

    def test_collect_filters_by_date(self):
        self._write_analysis("20260301_a", "2026-03-01T00:00:00", "数学", ["old"])
        self._write_analysis("20260315_b", "2026-03-15T00:00:00", "数学", ["mid"])
        self._write_analysis("20260325_c", "2026-03-25T00:00:00", "数学", ["late"])

        result = generate_report.collect_analyses(
            self.data_dir, self.qq, self.student,
            subject="数学", start="2026-03-10", end="2026-03-20"
        )
        self.assertEqual(len(result), 1)
        self.assertIn("mid", result[0]["weak_points"])

    def test_main_outputs_markdown(self):
        self._write_analysis("20260315_b", "2026-03-15T08:00:00", "数学",
                             ["进位加法"],
                             [{"error_type": "计算错误", "question": "第1题",
                               "student_answer": "40", "correct_answer": "42",
                               "error_reason": "口诀不熟", "thinking_guide": "用7×5+7"}])
        argv = [
            "generate_report.py",
            "--qq", self.qq,
            "--student", self.student,
            "--subject", "数学",
        ]
        with patch.object(generate_report, "DATA_DIR", str(self.data_dir)):
            with patch("sys.argv", argv):
                import io
                captured = io.StringIO()
                with patch("sys.stdout", captured):
                    generate_report.main()

        output = captured.getvalue()
        self.assertIn("张三", output)
        self.assertIn("进位加法", output)
        self.assertIn("计算错误", output)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_generate_report.py -v
```

期望：FAIL（`generate_report` 当前读 `result_*.json` 非 `analysis_*.json`）

**Step 3: 完全重写 `scripts/generate_report.py`**

```python
"""generate_report.py — 汇总历次 analysis JSON，输出 Markdown 格式报告。

用法：
    python3 scripts/generate_report.py \
        --qq 12345 --student 张三 --subject 数学 \
        [--start 2026-03-01] [--end 2026-03-31]
"""
import argparse
import os
import json
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def collect_analyses(data_dir, qq, student, subject="all", start="", end=""):
    """遍历所有批次，读取 analysis_{subject}.json，按日期过滤后返回列表。"""
    student_dir = os.path.join(str(data_dir), str(qq), student)
    if not os.path.exists(student_dir):
        return []

    results = []
    for batch_id in sorted(os.listdir(student_dir)):
        batch_dir = os.path.join(student_dir, batch_id)
        if not os.path.isdir(batch_dir):
            continue
        for fname in os.listdir(batch_dir):
            if not (fname.startswith("analysis_") and fname.endswith(".json")):
                continue
            subj_in_fname = fname[len("analysis_"):-len(".json")]
            if subject != "all" and subj_in_fname != subject:
                continue
            fpath = os.path.join(batch_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    continue
            ts = data.get("timestamp", "").split("T")[0]
            if start and ts < start:
                continue
            if end and ts > end:
                continue
            results.append(data)
    return results


def build_markdown(student, analyses):
    """将多批次 analysis 数据汇总成 Markdown 报告文本。"""
    if not analyses:
        return f"# {student} 学习报告\n\n暂无分析数据。\n"

    # 汇总薄弱知识点频次
    wp_count = defaultdict(int)
    error_type_count = defaultdict(int)
    total_errors = 0

    for a in analyses:
        for wp in a.get("weak_points", []):
            wp_count[wp] += 1
        for e in a.get("errors", []):
            error_type_count[e.get("error_type", "未知")] += 1
            total_errors += 1

    lines = [f"# {student} 学习分析报告", ""]
    lines.append(f"共分析 **{len(analyses)}** 批次，累计错题 **{total_errors}** 道。")
    lines.append("")

    if wp_count:
        lines.append("## 薄弱知识点（按出现频次）")
        for wp, cnt in sorted(wp_count.items(), key=lambda x: -x[1]):
            lines.append(f"- {wp}（出现 {cnt} 次）")
        lines.append("")

    if error_type_count:
        lines.append("## 错误类型分布")
        for etype, cnt in sorted(error_type_count.items(), key=lambda x: -x[1]):
            lines.append(f"- {etype}：{cnt} 次")
        lines.append("")

    lines.append("## 各批次明细")
    for a in analyses:
        batch = a.get("batch_id", "")
        subj = a.get("subject", "")
        ts = a.get("timestamp", "").split("T")[0]
        errors = a.get("errors", [])
        lines.append(f"### {ts} · {subj}（{batch}）")
        if errors:
            for e in errors:
                lines.append(
                    f"- 【{e.get('error_type', '')}】{e.get('question', '')}："
                    f"{e.get('error_reason', '')}"
                )
        else:
            lines.append("- 全部正确")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="汇总 analysis JSON 生成 Markdown 报告")
    parser.add_argument("--qq", required=True)
    parser.add_argument("--student", required=True)
    parser.add_argument("--subject", default="all")
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    args = parser.parse_args()

    analyses = collect_analyses(
        DATA_DIR, args.qq, args.student,
        subject=args.subject, start=args.start, end=args.end
    )
    print(build_markdown(args.student, analyses))


if __name__ == "__main__":
    main()
```

**Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_generate_report.py -v
```

期望：3 个测试全部 PASS

**Step 5: 确认其他测试不受影响**

```bash
python -m pytest tests/ -v
```

期望：全部 PASS（`test_generate_exercises` 仍读 `result_{subject}.json`，暂不修改）

**Step 6: Commit**

```bash
git add scripts/generate_report.py tests/test_generate_report.py
git commit -m "feat: generate_report.py 完全重写，读 analysis JSON 汇总输出 Markdown"
```

---

## 验证计划

### 自动化测试

```bash
# 运行所有新增测试
python -m pytest tests/test_storage.py tests/test_generate_report.py -v

# 确认现有测试不受影响
python -m pytest tests/ -v
```

### 手工验证

1. **验证 save_result 写的是 analysis JSON**

```bash
cd d:\devel\test\xunyu
python scripts/storage.py save_result \
  --qq 99999 --student 测试 --batch 20260323_demo \
  --subject 数学 \
  --json '{"weak_points":["进位加法"],"errors":[{"question":"第1题","student_answer":"40","correct_answer":"42","error_type":"计算错误","error_reason":"口诀不熟","thinking_guide":"7x5+7"}]}'
```

检查：`data/99999/测试/20260323_demo/analysis_数学.json` 存在，`result_数学.json` 不存在。

2. **验证 export_report 生成 PDF**

```bash
python scripts/export_report.py \
  --qq 99999 --student 测试 --batch 20260323_demo --subject 数学 \
  --text "这次数学表现很棒！有几处进位加法需要加强，建议多练习。"
```

检查：`data/99999/测试/20260323_demo/report_数学.pdf` 存在，打开 PDF 中文正常。

3. **验证 generate_report 读 analysis JSON**

```bash
python scripts/generate_report.py --qq 99999 --student 测试 --subject 数学
```

检查：输出包含"# 测试 学习分析报告"、"进位加法"、"计算错误"。
