# Inspector Study Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify inspector “错题总结 / 出类似题 / 两者皆有” into one `study` request with shared `student + subject + start + end` filters and a merged `both` document.

**Architecture:** Keep `scripts/generate_report.py` as the historical source of truth, extend `scripts/generate_exercises.py` to honor the same date filters, and update the coordinator/inspector prompt contracts to route everything through `task="study"` and `purpose`. The runtime behavior stays documentation-driven; only the exercise script gains new filtering logic and tests.

**Tech Stack:** Python 3, stdlib `unittest`, OpenClaw agent instruction files, Markdown/Docx export flow

---

## File Map

- Modify: `agents/coordinator/AGENTS.md`
  Purpose: Route “错题总结 / 出题 / 两者皆有” into the unified `study` protocol and tighten follow-up rules.
- Modify: `agents/inspector/AGENTS.md`
  Purpose: Replace split report/exercise orchestration with one `task="study"` workflow and a single merged-document response contract.
- Modify: `agents/inspector/skills/inspector/SKILL.md`
  Purpose: Teach the inspector skill how to structure `purpose=both` output so the prompt layer matches the new workflow.
- Modify: `scripts/generate_exercises.py`
  Purpose: Add `--start` and `--end`, filter result files by timestamp, and expose small helper functions for unit testing.
- Create: `tests/test_generate_exercises.py`
  Purpose: Lock the new date-filter behavior and weak-point aggregation before editing the script.

### Task 0: Preflight Workspace

**Files:**
- Modify: none
- Test: none

- [ ] **Step 1: Set up an isolated workspace**

Use `@superpowers/using-git-worktrees` and create a feature worktree such as `feat/inspector-study-workflow`.

- [ ] **Step 2: Install Python dependencies in the worktree**

Run: `python3 -m pip install -r requirements.txt`
Expected: `python-docx`, `reportlab`, and `Pillow` install without errors.

- [ ] **Step 3: Capture the current CLI baseline**

Run: `python3 scripts/generate_report.py --help`
Expected: help output already includes `--start` and `--end`

Run: `python3 scripts/generate_exercises.py --help`
Expected: help output does not yet include `--start` or `--end`

### Task 1: Add Failing Tests for Time-Scoped Exercise Filtering

**Files:**
- Create: `tests/test_generate_exercises.py`
- Modify: `scripts/generate_exercises.py`
- Test: `tests/test_generate_exercises.py`

- [ ] **Step 1: Write the failing tests**

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts import generate_exercises


def write_result(base, qq, student, batch, subject, timestamp, weak_points):
    batch_dir = Path(base) / str(qq) / student / batch
    batch_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": timestamp,
        "subject": subject,
        "weak_points": weak_points,
    }
    (batch_dir / f"result_{subject}.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


class GenerateExercisesTests(unittest.TestCase):
    def test_collect_top_weak_points_filters_by_date_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_result(tmp, 10001, "小明", "b1", "数学", "2026-03-05T09:00:00", ["计算错误"])
            write_result(tmp, 10001, "小明", "b2", "数学", "2026-03-15T09:00:00", ["计算错误", "单位换算"])

            result = generate_exercises.collect_top_weak_points(
                data_dir=tmp,
                qq="10001",
                student="小明",
                subject="数学",
                start="2026-03-10",
                end="2026-03-20",
            )

            self.assertEqual(result, ["计算错误", "单位换算"])

    def test_collect_top_weak_points_uses_full_history_without_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_result(tmp, 10001, "小明", "b1", "数学", "2026-03-05T09:00:00", ["计算错误"])
            write_result(tmp, 10001, "小明", "b2", "数学", "2026-03-15T09:00:00", ["单位换算"])

            result = generate_exercises.collect_top_weak_points(
                data_dir=tmp,
                qq="10001",
                student="小明",
                subject="数学",
            )

            self.assertEqual(result, ["计算错误", "单位换算"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest discover -s tests -p 'test_generate_exercises.py' -v`
Expected: FAIL because `collect_top_weak_points` does not exist and the script has no date-filter helpers yet.

- [ ] **Step 3: Write the minimal implementation**

Add pure helpers to `scripts/generate_exercises.py` so the CLI can stay thin and testable:

```python
def iter_subject_results(data_dir, qq, student, subject, start="", end=""):
    student_dir = os.path.join(data_dir, str(qq), student)
    if not os.path.exists(student_dir):
        return

    for batch_id in os.listdir(student_dir):
        batch_dir = os.path.join(student_dir, batch_id)
        if not os.path.isdir(batch_dir):
            continue
        fpath = os.path.join(batch_dir, f"result_{subject}.json")
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        ts = data.get("timestamp", "").split("T")[0]
        if start and ts < start:
            continue
        if end and ts > end:
            continue
        yield data


def collect_top_weak_points(data_dir, qq, student, subject, start="", end="", limit=3):
    wp_counts = defaultdict(int)
    for data in iter_subject_results(data_dir, qq, student, subject, start, end):
        for wp in data.get("weak_points", []):
            wp_counts[wp] += 1
    return [k for k, _ in sorted(wp_counts.items(), key=lambda item: item[1], reverse=True)[:limit]]
```

Also extend `argparse`:

```python
parser.add_argument("--start", default="")
parser.add_argument("--end", default="")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -p 'test_generate_exercises.py' -v`
Expected: PASS

- [ ] **Step 5: Commit the code and tests**

```bash
git add tests/test_generate_exercises.py scripts/generate_exercises.py
git commit -m "feat: add time-scoped exercise filtering"
```

### Task 2: Update the Inspector Protocol and Skill Guidance

**Files:**
- Modify: `agents/inspector/AGENTS.md`
- Modify: `agents/inspector/skills/inspector/SKILL.md`
- Test: none

- [ ] **Step 1: Rewrite the inspector trigger contract**

Update `agents/inspector/AGENTS.md` so it accepts:

```json
{
  "task": "study",
  "purpose": "mistakes|exercises|both",
  "qq_user_id": "...",
  "student": "...",
  "subject": "...",
  "start": "...",
  "end": "...",
  "count": 5
}
```

and returns:

```json
{
  "status": "study_done",
  "summary": "...",
  "word_path": "..."
}
```

- [ ] **Step 2: Document the merged `both` output structure**

Add a dedicated section to `agents/inspector/skills/inspector/SKILL.md` stating that `purpose=both` must produce one document in this order:
1. `## 一、错题总结与解析`
2. `## 二、同类巩固练习`
3. `# 答案与解析`

- [ ] **Step 3: Verify the new contract is discoverable**

Run: `rg -n 'task\": \"study\"|purpose|study_done|学习巩固包|答案与解析' agents/inspector/AGENTS.md agents/inspector/skills/inspector/SKILL.md`
Expected: all new protocol terms and the merged-document headings appear in the two files.

- [ ] **Step 4: Commit the inspector documentation changes**

```bash
git add agents/inspector/AGENTS.md agents/inspector/skills/inspector/SKILL.md
git commit -m "feat: unify inspector study workflow"
```

### Task 3: Update Coordinator Routing and Follow-Up Rules

**Files:**
- Modify: `agents/coordinator/AGENTS.md`
- Test: none

- [ ] **Step 1: Replace the old split routing entries**

Update the intent table so:
- “错题本 / 错题总结” routes to `purpose=mistakes`
- “出题 / 类似题 / 练习题” routes to `purpose=exercises`
- “总结并出题 / 错题+练习 / 两者都要” routes to `purpose=both`

- [ ] **Step 2: Tighten the query rules**

Document that all three study requests:
- require `subject`
- default `start/end` to full history when omitted
- reject `subject=all`
- keep the existing multi-child disambiguation behavior

- [ ] **Step 3: Verify the route table and guardrails**

Run: `rg -n 'purpose=mistakes|purpose=exercises|purpose=both|未指定学科|全历史|subject = all' agents/coordinator/AGENTS.md`
Expected: the new purpose mapping and the required-subject rule both appear.

- [ ] **Step 4: Commit the coordinator changes**

```bash
git add agents/coordinator/AGENTS.md
git commit -m "feat: route study requests through purpose"
```

### Task 4: Run Manual End-to-End Verification

**Files:**
- Modify: none
- Test: `tests/test_generate_exercises.py`

- [ ] **Step 1: Re-run the automated test**

Run: `python3 -m unittest discover -s tests -p 'test_generate_exercises.py' -v`
Expected: PASS

- [ ] **Step 2: Seed manual sample data with two dates**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path

records = [
    ("20260305_a", "2026-03-05T09:00:00", ["计算错误"], "粗心"),
    ("20260315_b", "2026-03-15T09:00:00", ["单位换算"], "审题"),
]

for batch_id, ts, weak_points, error_type in records:
    batch_dir = Path("data/99999/测试学生") / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": ts,
        "subject": "数学",
        "score": 80,
        "total": 100,
        "weak_points": weak_points,
        "corrections": [
            {
                "is_correct": False,
                "question": "示例题",
                "student_answer": "1",
                "correct_answer": "2",
                "error_type": error_type,
                "error_reason": "示例原因",
                "thinking_guide": "示例讲解"
            }
        ]
    }
    (batch_dir / "result_数学.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
PY
```

Expected: fixture files appear under `data/99999/测试学生/`.

- [ ] **Step 3: Verify the shared time filter through both CLIs**

Run: `python3 scripts/generate_report.py --qq 99999 --student 测试学生 --type mistakes --subject 数学 --start 2026-03-10 --end 2026-03-20`
Expected: JSON contains only the `2026-03-15` record in `mistakes_list`

Run: `python3 scripts/generate_exercises.py --qq 99999 --student 测试学生 --subject 数学 --count 5 --start 2026-03-10 --end 2026-03-20`
Expected: output mentions `单位换算` and does not mention `计算错误`

- [ ] **Step 4: Do a prompt-contract sanity pass**

Read `agents/coordinator/AGENTS.md`, `agents/inspector/AGENTS.md`, and `agents/inspector/skills/inspector/SKILL.md` together and verify:
- all three files use the same `task="study"` and `purpose` language
- `purpose=both` is explicitly described as one merged document
- no stale instruction still tells inspector to return separate docs for the combined path

- [ ] **Step 5: Remove temporary verification data and confirm a clean diff**

Run: `rm -rf data/99999 && git status --short`
Expected: the temporary fixture directory is gone, and only intentional tracked-file changes remain.
