import argparse
import os
import json
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qq", required=True)
    parser.add_argument("--student", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    
    student_dir = os.path.join(DATA_DIR, str(args.qq), args.student)
    if not os.path.exists(student_dir):
        print("未找到该学生的历史记录，无法提取薄弱点。")
        return
        
    wp_counts = defaultdict(int)
    for batch_id in os.listdir(student_dir):
        batch_dir = os.path.join(student_dir, batch_id)
        if not os.path.isdir(batch_dir): continue
        
        fname = f"result_{args.subject}.json"
        fpath = os.path.join(batch_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    for wp in data.get("weak_points", []):
                        wp_counts[wp] += 1
                except:
                    pass
                    
    if not wp_counts:
        print(f"该学生在 {args.subject} 科目上暂无明显的薄弱点记录，您可以自由出题。")
        return
        
    sorted_wp = sorted(wp_counts.items(), key=lambda x: x[1], reverse=True)
    top_wps = [k for k, v in sorted_wp[:3]]
    
    print(f"以下是学生 {args.student} 最需要提升的 {args.subject} 核心薄弱点：")
    for wp in top_wps:
        print(f"- {wp}")
    print(f"\n请根据上述薄弱点，为该学生生成 {args.count} 道针对性的辅导练习题。")

if __name__ == "__main__":
    main()
