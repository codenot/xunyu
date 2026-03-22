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
    parser.add_argument("--type", required=True, choices=["weekly", "monthly", "mistakes"])
    parser.add_argument("--subject", default="all")
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    args = parser.parse_args()
    
    student_dir = os.path.join(DATA_DIR, str(args.qq), args.student)
    if not os.path.exists(student_dir):
        print(json.dumps({"error": "No records found"}, ensure_ascii=False))
        return
        
    results = []
    
    # Iterate over batch dirs
    for batch_id in sorted(os.listdir(student_dir)):
        batch_dir = os.path.join(student_dir, batch_id)
        if not os.path.isdir(batch_dir): continue
        
        for fname in os.listdir(batch_dir):
            if fname.startswith("result_") and fname.endswith(".json"):
                if args.subject != "all":
                    subj_in_fname = fname[7:-5]
                    if subj_in_fname != args.subject:
                        continue
                        
                with open(os.path.join(batch_dir, fname), "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        ts = data.get("timestamp", "").split("T")[0]
                        if args.start and ts < args.start:
                            continue
                        if args.end and ts > args.end:
                            continue
                        results.append(data)
                    except:
                        pass
                        
    if not results:
        print(json.dumps({"error": "No records in this time range"}, ensure_ascii=False))
        return

    # Aggregate data
    subj_scores = defaultdict(list)
    mistake_counts = defaultdict(int)
    weak_points_all = set()
    all_mistakes = []
    
    for r in results:
        subj = r.get("subject", "Unk")
        score = r.get("score", 0)
        subj_scores[subj].append(score)
        
        for wp in r.get("weak_points", []):
            weak_points_all.add(wp)
            
        for c in r.get("corrections", []):
            if not c.get("is_correct", True):
                etype = c.get("error_type", "未知")
                mistake_counts[etype] += 1
                all_mistakes.append({
                    "date": r.get("timestamp", "").split("T")[0],
                    "subject": subj,
                    "question": c.get("question", ""),
                    "student_answer": c.get("student_answer", ""),
                    "correct_answer": c.get("correct_answer", ""),
                    "error_type": etype,
                    "error_reason": c.get("error_reason", ""),
                    "thinking_guide": c.get("thinking_guide", "")
                })

    report_data = {
        "student": args.student,
        "type": args.type,
        "total_batches": len(results),
        "subjects_stats": {},
        "top_mistakes": [],
        "weak_points": list(weak_points_all)
    }
    
    for subj, scores in subj_scores.items():
        report_data["subjects_stats"][subj] = {
            "count": len(scores),
            "avg_score": round(sum(scores)/len(scores), 1)
        }
        
    sorted_mistakes = sorted(mistake_counts.items(), key=lambda x: x[1], reverse=True)
    report_data["top_mistakes"] = [{"type": k, "count": v} for k, v in sorted_mistakes[:5]]
    
    if args.type == "mistakes":
        report_data["mistakes_list"] = all_mistakes
        
    print(json.dumps(report_data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
