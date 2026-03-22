import os
import json
import argparse
import urllib.request
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "NotoSansSC-Regular.ttf")
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC-Regular.ttf"

def ensure_font():
    if not os.path.exists(FONT_PATH):
        print("Downloading Chinese font (NotoSansSC) for PDF generation...")
        try:
            urllib.request.urlretrieve(FONT_URL, FONT_PATH)
        except Exception as e:
            print(f"Warning: Failed to download font: {e}")
            pass
    
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont('NotoSans', FONT_PATH))
    else:
        # Fallback to default, might not render Chinese
        print("Warning: NotoSans font not available, using Helvetica.")

def build_pdf(json_data, output_path):
    ensure_font()
    font_name = 'NotoSans' if os.path.exists(FONT_PATH) else 'Helvetica'
    
    doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleChinese', fontName=font_name, fontSize=18, alignment=1, spaceAfter=20))
    styles.add(ParagraphStyle(name='Heading2Chinese', fontName=font_name, fontSize=14, spaceAfter=10, spaceBefore=10))
    styles.add(ParagraphStyle(name='NormalChinese', fontName=font_name, fontSize=11, spaceAfter=6))
    
    elements = []
    
    student = json_data.get("student", "学生")
    subject = json_data.get("subject", "学科")
    batch_id = json_data.get("batch_id", "")
    date_str = json_data.get("timestamp", "").split("T")[0] if "timestamp" in json_data else "Unknown"
    
    elements.append(Paragraph(f"批改报告 - {subject}", styles['TitleChinese']))
    elements.append(Paragraph(f"学生: {student}    |    日期: {date_str}    |    批次: {batch_id}", styles['NormalChinese']))
    elements.append(Spacer(1, 10))
    
    score = json_data.get("score", 0)
    total = json_data.get("total", 100)
    elements.append(Paragraph(f"<b>得分：{score} / {total}</b>", styles['NormalChinese']))
    elements.append(Paragraph(f"总体评价：{json_data.get('overall', '')}", styles['NormalChinese']))
    elements.append(Spacer(1, 10))
    
    wp = json_data.get("weak_points", [])
    if wp:
        elements.append(Paragraph("<b>薄弱知识点：</b>", styles['NormalChinese']))
        elements.append(Paragraph("、".join(wp), styles['NormalChinese']))
        elements.append(Spacer(1, 10))
        
    corrections = json_data.get("corrections", [])
    if corrections:
        elements.append(Paragraph("<b>错题明细：</b>", styles['Heading2Chinese']))
        
        table_data = [["题号", "学生答案", "正确答案", "错误类型", "思路提示"]]
        for c in corrections:
            if not c.get("is_correct", True):
                table_data.append([
                    Paragraph(str(c.get("question", "")), styles['NormalChinese']),
                    Paragraph(str(c.get("student_answer", "")), styles['NormalChinese']),
                    Paragraph(str(c.get("correct_answer", "")), styles['NormalChinese']),
                    Paragraph(str(c.get("error_type", "")), styles['NormalChinese']),
                    Paragraph(str(c.get("thinking_guide", "")), styles['NormalChinese'])
                ])
                
        if len(table_data) > 1:
            t = Table(table_data, colWidths=[50, 80, 80, 80, 240])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('FONTNAME', (0,0), (-1,-1), font_name),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("全部正确！", styles['NormalChinese']))
            
    sugg = json_data.get("exercise_suggestions", [])
    if sugg:
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("<b>下一步建议：</b>", styles['Heading2Chinese']))
        for s in sugg:
            elements.append(Paragraph(f"• {s}", styles['NormalChinese']))
            
    doc.build(elements)
    print(f"PDF generated: {output_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qq", required=True)
    parser.add_argument("--student", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--subject", required=True)
    args = parser.parse_args()
    
    batch_dir = os.path.join(DATA_DIR, str(args.qq), args.student, args.batch)
    json_path = os.path.join(batch_dir, f"result_{args.subject}.json")
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    pdf_path = os.path.join(batch_dir, f"report_{args.subject}.pdf")
    build_pdf(data, pdf_path)

if __name__ == "__main__":
    main()
