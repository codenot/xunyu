"""generate_report.py — 汇总多批次 analysis JSON，生成结构化报告。

用法：
    python3 scripts/generate_report.py \
        --qq <qq> --student <student> \
        --type weekly|monthly|mistakes \
        --subject all|数学|语文|英语 \
        --start 2026-01-01 --end 2026-01-31

读取 data/<qq>/<student>/<batch>/analysis_<subject>.json，
输出 JSON 到 stdout。

字段说明（analysis JSON 格式）：
  - weak_points: [str]
  - errors: [{"question": str, "description": str, ...}]  （结构由 marker 决定）
"""

import argparse
import os
import json
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def load_analyses(student_dir: str, subject_filter: str, start: str, end: str) -> list:
    """从各批次目录读取 analysis_*.json，按日期过滤后返回列表。"""
    records = []
    if not os.path.isdir(student_dir):
        return records

    for batch_id in sorted(os.listdir(student_dir)):
        batch_dir = os.path.join(student_dir, batch_id)
        if not os.path.isdir(batch_dir):
            continue

        for fname in os.listdir(batch_dir):
            if not (fname.startswith("analysis_") and fname.endswith(".json")):
                continue

            # 科目过滤
            subj = fname.replace("analysis_", "").replace(".json", "")
            if subject_filter != "all" and subj != subject_filter:
                continue

            fpath = os.path.join(batch_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            # 日期过滤
            ts_date = data.get("timestamp", "").split("T")[0]
            if start and ts_date < start:
                continue
            if end and ts_date > end:
                continue

            records.append(data)

    return records


def aggregate(records: list) -> dict:
    """汇总所有记录，返回统计数据。"""
    weak_counter = Counter()
    error_list = []
    subj_batch_count = {}

    for r in records:
        subj = r.get("subject", "未知")
        subj_batch_count[subj] = subj_batch_count.get(subj, 0) + 1

        for wp in r.get("weak_points", []):
            weak_counter[wp] += 1

        for err in r.get("errors", []):
            # 保留原始错题信息，附加来源字段
            entry = dict(err)
            entry.setdefault("batch_id", r.get("batch_id", ""))
            entry.setdefault("subject", subj)
            entry.setdefault("date", r.get("timestamp", "").split("T")[0])
            error_list.append(entry)

    return {
        "batch_count": len(records),
        "subjects_summary": dict(subj_batch_count),
        # 按出现频次降序排列薄弱点
        "weak_points_ranked": [{"point": p, "count": c} for p, c in weak_counter.most_common()],
        "error_count": len(error_list),
    }


def main():
    parser = argparse.ArgumentParser(description="生成学习报告汇总")
    parser.add_argument("--qq", required=True)
    parser.add_argument("--student", required=True)
    parser.add_argument("--type", required=True, choices=["weekly", "monthly", "mistakes"])
    parser.add_argument("--subject", default="all")
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    args = parser.parse_args()

    student_dir = os.path.join(DATA_DIR, str(args.qq), args.student)
    records = load_analyses(student_dir, args.subject, args.start, args.end)

    if not records:
        print(json.dumps({"error": "No records in this time range"}, ensure_ascii=False))
        return

    stats = aggregate(records)

    report = {
        "student": args.student,
        "type": args.type,
        "subject": args.subject,
        "date_range": {"start": args.start, "end": args.end},
        **stats,
        "raw_data": records
    }

    # mistakes 类型额外输出完整错题列表
    if args.type == "mistakes":
        errors_detail = []
        for r in records:
            for err in r.get("errors", []):
                entry = dict(err)
                entry.setdefault("batch_id", r.get("batch_id", ""))
                entry.setdefault("subject", r.get("subject", "未知"))
                entry.setdefault("date", r.get("timestamp", "").split("T")[0])
                errors_detail.append(entry)
        report["errors_detail"] = errors_detail

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
