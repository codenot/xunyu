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
    """将批改结果写入 analysis_{subject}.json。

    接收的 JSON 只需包含：
      - weak_points: [str]   薄弱知识点列表
      - errors: [object]     错题列表（全对时传空数组）

    函数会自动附加 batch_id / qq_user_id / student / subject / timestamp 字段。
    """
    batch_dir = os.path.join(get_user_dir(args.qq), args.student, args.batch)
    os.makedirs(batch_dir, exist_ok=True)

    try:
        analysis = json.loads(args.json)
    except json.JSONDecodeError as e:
        print(f"Error: JSON 解析失败 — {e}")
        return

    # 校验必要字段
    if "weak_points" not in analysis or "errors" not in analysis:
        print("Error: JSON 必须包含 'weak_points' 和 'errors' 字段")
        return

    # 注入元数据
    analysis["batch_id"] = args.batch
    analysis["qq_user_id"] = str(args.qq)
    analysis["student"] = args.student
    analysis["subject"] = args.subject
    if "timestamp" not in analysis:
        analysis["timestamp"] = datetime.datetime.now().isoformat()

    # 写入 analysis_{subject}.json
    out_path = os.path.join(batch_dir, f"analysis_{args.subject}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    print(f"analysis saved: {out_path}")

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
        if not os.path.isdir(batch_dir):
            continue

        # 读 analysis_{subj}.json（新格式）
        for fname in os.listdir(batch_dir):
            if fname.startswith("analysis_") and fname.endswith(".json"):
                if args.subject and args.subject != "all":
                    subj_in_fname = fname[9:-5]  # "analysis_".len == 9
                    if subj_in_fname != args.subject:
                        continue

                with open(os.path.join(batch_dir, fname), "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        results.append({
                            "batch_id": batch_id,
                            "subject": data.get("subject"),
                            "weak_points": data.get("weak_points", []),
                            "error_count": len(data.get("errors", [])),
                            "timestamp": data.get("timestamp"),
                        })
                    except Exception:
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
        if not os.path.isdir(batch_dir):
            continue

        for fname in os.listdir(batch_dir):
            if fname.startswith("analysis_") and fname.endswith(".json"):
                if args.subject and args.subject != "all":
                    subj_in_fname = fname[9:-5]
                    if subj_in_fname != args.subject:
                        continue

                with open(os.path.join(batch_dir, fname), "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        # 按日期过滤
                        ts = data.get("timestamp", "").split("T")[0]
                        if args.start and ts < args.start:
                            continue
                        if args.end and ts > args.end:
                            continue
                        results.append(data)
                    except Exception:
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
