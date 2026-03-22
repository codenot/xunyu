import argparse
import json
import os
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

def iter_subject_results(data_dir, qq, student, subject, start="", end=""):
    student_dir = os.path.join(os.fspath(data_dir), str(qq), student)
    if not os.path.exists(student_dir):
        return

    for batch_id in sorted(os.listdir(student_dir)):
        batch_dir = os.path.join(student_dir, batch_id)
        if not os.path.isdir(batch_dir):
            continue

        fpath = os.path.join(batch_dir, f"result_{subject}.json")
        if not os.path.exists(fpath):
            continue

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue

        ts = data.get("timestamp", "").split("T")[0]
        if start and ts < start:
            continue
        if end and ts > end:
            continue
        yield data

def collect_top_weak_points(data_dir, qq, student, subject, start="", end="", limit=3):
    wp_counts = defaultdict(int)
    for result in iter_subject_results(data_dir, qq, student, subject, start=start, end=end):
        for wp in result.get("weak_points", []):
            wp_counts[wp] += 1

    if not wp_counts:
        return []

    sorted_wp = sorted(wp_counts.items(), key=lambda x: x[1], reverse=True)
    return [wp for wp, _ in sorted_wp[:limit]]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qq", required=True)
    parser.add_argument("--student", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    args = parser.parse_args()

    student_dir = os.path.join(DATA_DIR, str(args.qq), args.student)
    if not os.path.exists(student_dir):
        print("未找到该学生的历史记录，无法提取薄弱点。")
        return

    top_wps = collect_top_weak_points(
        DATA_DIR,
        args.qq,
        args.student,
        args.subject,
        start=args.start,
        end=args.end,
        limit=3,
    )

    if not top_wps:
        print(f"该学生在 {args.subject} 科目上暂无明显的薄弱点记录，您可以自由出题。")
        return

    print(f"以下是学生 {args.student} 最需要提升的 {args.subject} 核心薄弱点：")
    for wp in top_wps:
        print(f"- {wp}")
    print(f"\n请根据上述薄弱点，为该学生生成 {args.count} 道针对性的辅导练习题。")

if __name__ == "__main__":
    main()
