"""export_report.py — 将批改报告（Markdown 文本）生成漂亮的 PDF。

用法：
    python3 scripts/export_report.py \
        --qq <qq> --student <student> --batch <batch_id> --subject <subject> \
        --text 'Markdown 文本内容'

输出文件：data/<qq>/<student>/<batch>/report_<subject>.pdf
"""

import os
import argparse
import datetime
import logging

# 自动安装所需的依赖（如果缺少）
try:
    import markdown
    import weasyprint
except ImportError:
    import subprocess
    import sys
    print("Installing required packages (markdown, weasyprint)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown", "weasyprint"])
    import markdown
    import weasyprint

# 屏蔽 weasyprint 过多的排版警告日志
logging.getLogger('weasyprint').setLevel(logging.ERROR)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "NotoSansSC-Regular.ttf")

def ensure_font():
    """确保中文字体可用。"""
    if not os.path.exists(FONT_PATH):
        print(f"Warning: Local font missing at {FONT_PATH}")
    return FONT_PATH

def build_pdf(md_text: str, student: str, subject: str, batch_id: str, output_path: str, title: str = ""):
    """将 Markdown 评语渲染为 A4 PDF。"""
    font_path = ensure_font()
    
    # 默认使用科目+批改报告作为标题，除非指定了自定义标题
    display_title = title if title else f"{subject} 批改报告"
    
    # 将 Windows 路径里的反斜杠转为正斜杠，防止 CSS 解析错误
    font_path_css = font_path.replace("\\", "/")
    if not font_path_css.startswith('/'):
        font_path_css = '/' + font_path_css
    font_path_uri = f"file://{font_path_css}"
    
    # 转换 Markdown 到 HTML
    # extensions 开启表格、列表等加强支持
    html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'nl2br'])
    
    date_str = datetime.date.today().isoformat()
    
    # 构造完整的带有样式的 HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @font-face {{
                font-family: 'NotoSansSC';
                src: url('{font_path_uri}');
            }}
            @page {{
                size: A4;
                margin: 20mm;
                @bottom-right {{
                    content: counter(page) " / " counter(pages);
                    font-size: 10px;
                    color: #999;
                }}
                @top-center {{
                    content: string(doctitle);
                    font-size: 10px;
                    color: #999;
                }}
            }}
            body {{
                font-family: 'NotoSansSC', sans-serif;
                line-height: 1.6;
                color: #333;
                font-size: 14px;
            }}
            .header-meta {{
                text-align: center;
                color: #666;
                font-size: 12px;
                margin-bottom: 20px;
                border-bottom: 1px solid #ccc;
                padding-bottom: 10px;
            }}
            h1 {{ font-size: 26px; color: #2c3e50; text-align: center; margin-bottom: 5px; string-set: doctitle content(); }}
            h2 {{ font-size: 20px; color: #2980b9; border-bottom: 1px solid #eee; padding-bottom: 4px; margin-top: 15px; }}
            h3 {{ font-size: 16px; color: #34495e; }}
            p {{ margin-bottom: 10px; }}
            img {{ max-width: 100%; height: auto; margin: 10px 0; page-break-inside: avoid; }}
            ul, ol {{ margin-bottom: 12px; margin-left: 20px; }}
            table {{ page-break-inside: auto; border-collapse: collapse; width: 100%; margin-bottom: 15px; font-size: 12px; }}
            tr {{ page-break-inside: avoid; page-break-after: auto; }}
            thead {{ display: table-header-group; }}
            td, th {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f8f9fa; color: #2c3e50; font-weight: bold; }}
            pre {{
                white-space: pre-wrap;
                word-wrap: break-word;
                background-color: #f4f4f4;
                padding: 10px;
                border-radius: 4px;
                page-break-inside: avoid;
            }}
            code {{
                font-family: Consolas, monospace;
                background-color: #f4f4f4;
                padding: 2px 4px;
                border-radius: 4px;
            }}
            blockquote {{
                border-left: 4px solid #3498db;
                padding-left: 10px;
                margin-left: 0;
                color: #555;
                background-color: #fbfcfd;
                page-break-inside: avoid;
            }}
            strong {{ color: #e74c3c; }}
        </style>
    </head>
    <body>
        <h1>{display_title}</h1>
        <div class="header-meta">
            学生：{student} &nbsp;|&nbsp; 批次：{batch_id} &nbsp;|&nbsp; 日期：{date_str}
        </div>
        <div class="content">
            {html_body}
        </div>
    </body>
    </html>
    """
    
    # 使用 weasyprint 写入 PDF
    try:
        weasyprint.HTML(string=html_content).write_pdf(output_path)
        print(f"report saved: {output_path}")
    except Exception as e:
        print(f"Error generating PDF: {e}")

def main():
    parser = argparse.ArgumentParser(description="生成报告 PDF")
    parser.add_argument("--qq", required=True, help="QQ 用户 ID")
    parser.add_argument("--student", required=True, help="学生姓名")
    parser.add_argument("--batch", required=True, help="批次 ID")
    parser.add_argument("--subject", required=True, help="科目（数学/语文/英语）")
    parser.add_argument("--text", required=True, help="正文内容（Markdown 文本）")
    parser.add_argument("--title", help="PDF 顶部显示的标题")

    args = parser.parse_args()

    # 尝试将传递过来的文本中的换行符从 \\n 替换为真实的 \n
    text = args.text.replace("\\n", "\n")

    batch_dir = os.path.join(DATA_DIR, str(args.qq), args.student, args.batch)
    os.makedirs(batch_dir, exist_ok=True)

    output_path = os.path.join(batch_dir, f"report_{args.subject}.pdf")
    build_pdf(
        md_text=text,
        student=args.student,
        subject=args.subject,
        batch_id=args.batch,
        output_path=output_path,
        title=args.title
    )

if __name__ == "__main__":
    main()
