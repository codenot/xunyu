import os
import json
import argparse
import datetime
from collections import defaultdict

# Base data directory relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

def get_user_dir(qq):
    return os.path.join(DATA_DIR, str(qq))

def get_children_file(qq):
    return os.path.join(get_user_dir(qq), "children.json")

def init_child(args):
    user_dir = get_user_dir(args.qq)
    os.makedirs(user_dir, exist_ok=True)
    
    children_file = get_children_file(args.qq)
    data = {"qq_user_id": str(args.qq), "children": []}
    
    if os.path.exists(children_file):
        with open(children_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                pass
                
    # Check if child already exists
    child_found = False
    subjects_list = [s.strip() for s in args.subjects.split(",") if s.strip()]
    
    for child in data["children"]:
        if child["name"] == args.name:
            child["grade"] = args.grade
            child["subjects"] = subjects_list
            child_found = True
            break
            
    if not child_found:
        data["children"].append({
            "name": args.name,
            "grade": args.grade,
            "subjects": subjects_list
        })
        
    with open(children_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"Child {args.name} registered successfully.")

def list_children(args):
    children_file = get_children_file(args.qq)
    if not os.path.exists(children_file):
        print(json.dumps({"error": "No children found for this QQ"}, ensure_ascii=False))
        return
        
    with open(children_file, "r", encoding="utf-8") as f:
        print(f.read())

def gen_batch_id(args):
    now = datetime.datetime.now()
    import random
    import string
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    batch_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{random_str}"
    print(batch_id)

def init_batch(args):
    batch_dir = os.path.join(get_user_dir(args.qq), args.student, args.batch)
    original_dir = os.path.join(batch_dir, "original")
    os.makedirs(original_dir, exist_ok=True)
    print(original_dir)

def save_result(args):
    batch_dir = os.path.join(get_user_dir(args.qq), args.student, args.batch)
    os.makedirs(batch_dir, exist_ok=True)
    
    try:
        result_data = json.loads(args.json)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return

    # Add metadata
    result_data["batch_id"] = args.batch
    result_data["qq_user_id"] = args.qq
    result_data["student"] = args.student
    result_data["subject"] = args.subject
    
    if "timestamp" not in result_data:
        result_data["timestamp"] = datetime.datetime.now().isoformat()

    # Save result_{subject}.json
    json_path = os.path.join(batch_dir, f"result_{args.subject}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
        
    # Generate and save analysis_{subject}.md
    analysis_path = os.path.join(batch_dir, f"analysis_{args.subject}.md")
    generate_analysis_md(result_data, analysis_path)
    
    # Generate and append to summary.txt
    summary_path = os.path.join(batch_dir, "summary.txt")
    generate_summary_txt(result_data, summary_path)
    
    print(f"Results saved to {batch_dir}")

def generate_analysis_md(data, output_path):
    student = data.get("student", "")
    subject = data.get("subject", "")
    batch_id = data.get("batch_id", "")
    
    # Try to extract date from timestamp (format: 2026-03-22T14:30:00)
    date_str = batch_id.split('_')[0] if batch_id else "未知日期"
    if "timestamp" in data:
        try:
            date_str = data["timestamp"].split("T")[0]
        except:
            pass

    score = data.get("score", 0)
    total = data.get("total", 100)
    corr_list = data.get("corrections", [])
    
    md_lines = []
    md_lines.append(f"# 批次分析 | {student} | {subject} | {date_str}")
    md_lines.append("")
    md_lines.append("## 得分")
    md_lines.append(f"{score}/{total}")
    md_lines.append("")
    md_lines.append("## 错误记录")
    
    # Aggregate errors
    error_stats = defaultdict(lambda: {"count": 0, "reasons": set()})
    for corr in corr_list:
        if not corr.get("is_correct", True):
            etype = corr.get("error_type", "未知错误")
            ereason = corr.get("error_reason", "无详细原因")
            error_stats[etype]["count"] += 1
            error_stats[etype]["reasons"].add(ereason)
            
    if error_stats:
        md_lines.append("| 错误类型 | 错误原因示例 | 出现次数 |")
        md_lines.append("|---------|---------|--------|")
        for etype, stats in error_stats.items():
            reasons_str = "；".join(list(stats["reasons"])[:2]) # max 2 examples
            md_lines.append(f"| {etype} | {reasons_str} | {stats['count']} |")
    else:
        md_lines.append("全部正确，无错误记录。")
        
    md_lines.append("")
    md_lines.append("## 薄弱知识点")
    weak_points = data.get("weak_points", [])
    if weak_points:
        for wp in weak_points:
            md_lines.append(f"- {wp}")
    else:
        md_lines.append("- 无明显薄弱点")
        
    md_lines.append("")
    md_lines.append("## 出题建议")
    suggestions = data.get("exercise_suggestions", [])
    if suggestions:
        for sug in suggestions:
            md_lines.append(f"- {sug}")
    else:
        md_lines.append("- 根据薄弱点针对性出题。")
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

def generate_summary_txt(data, output_path):
    student = data.get("student", "")
    subject = data.get("subject", "")
    batch_id = data.get("batch_id", "")
    timestamp = data.get("timestamp", "").replace("T", " ")[:16]
    score = data.get("score", 0)
    total = data.get("total", 100)
    
    error_types = defaultdict(int)
    for corr in data.get("corrections", []):
        if not corr.get("is_correct", True):
            error_types[corr.get("error_type", "未知")] += 1
            
    # sort by count descending
    sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
    top_errors_str = "、".join([f"{k}×{v}" for k, v in sorted_errors[:3]])
    if not top_errors_str:
        top_errors_str = "无"
        
    weak_str = "、".join(data.get("weak_points", [])) if data.get("weak_points") else "无"
    
    summary_line = f"批次：{batch_id} | {student} | {subject}\n"
    summary_line += f"时间：{timestamp} | 得分：{score}/{total}\n"
    summary_line += f"主要错误：{top_errors_str}\n"
    summary_line += f"薄弱点：{weak_str}\n"
    summary_line += f"总评：{data.get('overall', '')}\n\n"
    
    # Append to summary.txt to support multi-subject appending
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(summary_line)

def query_score(args):
    # Print recent N scores
    student_dir = os.path.join(get_user_dir(args.qq), args.student)
    if not os.path.exists(student_dir):
        print(json.dumps({"error": "Student not found"}, ensure_ascii=False))
        return
        
    results = []
    # Batch dirs
    for batch_id in sorted(os.listdir(student_dir), reverse=True):
        batch_dir = os.path.join(student_dir, batch_id)
        if not os.path.isdir(batch_dir): continue
        
        # files like result_{subj}.json
        for fname in os.listdir(batch_dir):
            if fname.startswith("result_") and fname.endswith(".json"):
                if args.subject and args.subject != "all":
                    subj_in_fname = fname[7:-5]
                    if subj_in_fname != args.subject:
                        continue
                
                with open(os.path.join(batch_dir, fname), "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        results.append({
                            "batch_id": batch_id,
                            "subject": data.get("subject"),
                            "score": f"{data.get('score', 0)}/{data.get('total', 100)}",
                            "timestamp": data.get("timestamp"),
                            "overall": data.get("overall")
                        })
                    except:
                        pass
        
        if args.limit and len(results) >= args.limit:
            results = results[:args.limit]
            break
            
    print(json.dumps(results, ensure_ascii=False, indent=2))

def get_results(args):
    # Filter by date range
    student_dir = os.path.join(get_user_dir(args.qq), args.student)
    if not os.path.exists(student_dir):
        print(json.dumps([], ensure_ascii=False))
        return
        
    results = []
    for batch_id in sorted(os.listdir(student_dir), reverse=True):
        batch_dir = os.path.join(student_dir, batch_id)
        if not os.path.isdir(batch_dir): continue
        
        for fname in os.listdir(batch_dir):
            if fname.startswith("result_") and fname.endswith(".json"):
                if args.subject and args.subject != "all":
                    subj_in_fname = fname[7:-5]
                    if subj_in_fname != args.subject:
                        continue
                        
                with open(os.path.join(batch_dir, fname), "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        # Filter by start/end
                        ts = data.get("timestamp", "").split("T")[0]
                        if args.start and ts < args.start:
                            continue
                        if args.end and ts > args.end:
                            continue
                        results.append(data)
                    except:
                        pass
                        
    print(json.dumps(results, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Storage script for Xunyu Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    p_init_child = subparsers.add_parser("init_child")
    p_init_child.add_argument("--qq", required=True)
    p_init_child.add_argument("--name", required=True)
    p_init_child.add_argument("--grade", required=True)
    p_init_child.add_argument("--subjects", required=True)
    
    p_list_children = subparsers.add_parser("list_children")
    p_list_children.add_argument("--qq", required=True)
    
    p_gen_batch_id = subparsers.add_parser("gen_batch_id")
    p_gen_batch_id.add_argument("--student", required=True)
    
    p_init_batch = subparsers.add_parser("init_batch")
    p_init_batch.add_argument("--qq", required=True)
    p_init_batch.add_argument("--student", required=True)
    p_init_batch.add_argument("--batch", required=True)
    
    p_save_result = subparsers.add_parser("save_result")
    p_save_result.add_argument("--qq", required=True)
    p_save_result.add_argument("--student", required=True)
    p_save_result.add_argument("--batch", required=True)
    p_save_result.add_argument("--subject", required=True)
    p_save_result.add_argument("--json", required=True)
    
    p_query_score = subparsers.add_parser("query_score")
    p_query_score.add_argument("--qq", required=True)
    p_query_score.add_argument("--student", required=True)
    p_query_score.add_argument("--subject", default=None)
    p_query_score.add_argument("--limit", type=int, default=5)
    
    p_get_results = subparsers.add_parser("get_results")
    p_get_results.add_argument("--qq", required=True)
    p_get_results.add_argument("--student", required=True)
    p_get_results.add_argument("--subject", default=None)
    p_get_results.add_argument("--start", default=None)
    p_get_results.add_argument("--end", default=None)
    
    args = parser.parse_args()
    
    if args.command == "init_child":
        init_child(args)
    elif args.command == "list_children":
        list_children(args)
    elif args.command == "gen_batch_id":
        gen_batch_id(args)
    elif args.command == "init_batch":
        init_batch(args)
    elif args.command == "save_result":
        save_result(args)
    elif args.command == "query_score":
        query_score(args)
    elif args.command == "get_results":
        get_results(args)

if __name__ == "__main__":
    main()
