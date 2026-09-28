import streamlit as st
import time
import re
import io
import os
import pandas as pd
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 1. إعدادات الصفحة والتنسيق Visuals
# ==========================================
st.set_page_config(
    page_title="المنصة الرقمية لاختبارات فريق معامل المتوطنة",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# التحقق مما إذا كان المستخدم مسجلاً كإداري/مالك
is_admin_logged = st.session_state.get("logged_admin_user") is not None

# إذا لم يكن المالك مسجلاً للدخول، يتم إخفاء الشريط الجانبي وأزرار التحكم بالكامل عن الطلاب
if not is_admin_logged:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

# تنسيقات CSS العامة للبرنامج والخلفية 4K المتدرجة
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #fffde7 0%, #f0f4c3 35%, #dce775 70%, #c5e1a5 100%) !important;
        background-attachment: fixed !important;
        font-family: 'Cairo', sans-serif !important;
        direction: rtl;
        text-align: right;
    }

    .question-card {
        background: rgba(255, 255, 255, 0.92);
        border-right: 6px solid #558b2f;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        backdrop-filter: blur(5px);
    }
    .timer-box {
        background: linear-gradient(135deg, #d32f2f, #c62828);
        border: 2px solid #b71c1c;
        color: #ffffff;
        padding: 12px 15px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 1.3rem;
        text-align: center;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(211, 47, 47, 0.3);
    }
    .admin-box {
        background: rgba(255, 255, 255, 0.95);
        border: 2px solid #afb42b;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(175, 180, 43, 0.2);
    }
    .reg-box, .waiting-box {
        background: rgba(255, 255, 255, 0.95);
        border: 2px solid #33691e;
        padding: 25px;
        border-radius: 15px;
        margin-top: 20px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.06);
    }
    .stRadio > label {
        font-weight: 700;
        color: #1b5e20;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. اللوجو والعلامة المائية والتوقيعات الرسمية
# ==========================================
LOGO_PATH = "logo.jpg"
OFFICIAL_RIGHT_HEADER = """<b>الإدارة الصحية بأولاد صقر</b><br/><b>قسم المتوطنة وقسم المعامل</b><br/><b>تدريب معامل المتوطنة</b>"""

def draw_watermark(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 14)
    canvas.setFillColor(colors.HexColor("#2e7d32"))
    canvas.setFillAlpha(0.08)
    canvas.translate(A4[0] / 2.0, A4[1] / 2.0)
    canvas.rotate(45)
    
    watermark_text = "الإدارة الصحية بأولاد صقر - قسم المتوطنة وقسم المعامل - تدريب معامل المتوطنة"
    canvas.drawCentredString(0, 0, watermark_text)
    canvas.drawCentredString(0, -50, "National Endemic Parasitology Training & Surveillance")
    canvas.restoreState()

def build_pdf_header(styles):
    header_right_style = ParagraphStyle('HeaderRight', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12, alignment=2)
    header_p = Paragraph(OFFICIAL_RIGHT_HEADER, header_right_style)
    
    if os.path.exists(LOGO_PATH):
        img = Image(LOGO_PATH, width=55, height=55)
        header_table = Table([[header_p, img]], colWidths=[420, 100])
    else:
        header_table = Table([[header_p, ""]], colWidths=[420, 100])

    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'RIGHT'),
        ('ALIGN', (1,0), (1,0), 'LEFT'),
    ]))
    return header_table

def build_signatures_table(styles):
    sig_style = ParagraphStyle('SigStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=11, alignment=1)
    
    cell1 = Paragraph("<b>مسؤول تدريب معامل المتوطنة</b><br/><br/><b>أ.م / أحمد صالح حجازي</b>", sig_style)
    cell2 = Paragraph("<b>رئيس قسم المعامل</b><br/><br/>...........................", sig_style)
    cell3 = Paragraph("<b>مدير المتوطنة</b><br/><br/>...........................", sig_style)
    cell4 = Paragraph("<b>يعتمد؛ مدير عام الإدارة</b><br/><br/>...........................", sig_style)
    
    sig_table = Table([[cell1, cell2, cell3, cell4]], colWidths=[130, 130, 130, 130])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#ced4da")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e9ecef")),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8f9fa")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    return sig_table

# ==========================================
# 3. توثيق تقارير الـ PDF وشهادات التقدير
# ==========================================
def generate_pdf_report(student_name, student_phone, active_questions, user_answers, score_pct, correct_count, total_q, exam_mode):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, alignment=1, spaceAfter=8)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=10)
    header_table_style = ParagraphStyle('HTStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.whitesmoke)

    story.append(build_pdf_header(styles))
    story.append(Spacer(1, 8))
    story.append(Paragraph("تقرير نتيجة اختبار معامل المتوطنة", title_style))
    story.append(Spacer(1, 8))

    summary_data = [
        [Paragraph(f"<b>Candidate Name:</b> {student_name}", normal_style), Paragraph(f"<b>Phone:</b> {student_phone}", normal_style)],
        [Paragraph(f"<b>Final Result:</b> {score_pct:.1f}%", normal_style), Paragraph(f"<b>Score:</b> {correct_count} / {total_q}", normal_style)],
        [Paragraph(f"<b>Exam Category:</b> {exam_mode}", normal_style), Paragraph(f"<b>Date:</b> {time.strftime('%Y-%m-%d %H:%M')}", normal_style)]
    ]
    
    summary_table = Table(summary_data, colWidths=[260, 260])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f3f5")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#689f38")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#dee2e6")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    table_data = [[
        Paragraph("<b>#</b>", header_table_style),
        Paragraph("<b>Question</b>", header_table_style),
        Paragraph("<b>Your Answer</b>", header_table_style),
        Paragraph("<b>Correct Answer</b>", header_table_style),
        Paragraph("<b>Grade</b>", header_table_style)
    ]]

    for idx, q in enumerate(active_questions):
        user_ans = user_answers.get(idx, "N/A")
        is_correct = user_ans == q["answer"]
        grade_str = "1 / 1" if is_correct else "0 / 1"
        
        table_data.append([
            Paragraph(str(idx + 1), normal_style),
            Paragraph(q["question"], normal_style),
            Paragraph(str(user_ans), normal_style),
            Paragraph(str(q["answer"]), normal_style),
            Paragraph(grade_str, normal_style)
        ])

    q_table = Table(table_data, colWidths=[20, 210, 115, 120, 55])
    q_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#558b2f")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#ced4da")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(q_table)
    story.append(Spacer(1, 15))

    story.append(build_signatures_table(styles))

    doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    buffer.seek(0)
    return buffer

def generate_certificate_pdf(student_name, student_phone, pre_score, post_score):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CertTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=20, alignment=1, textColor=colors.HexColor("#1b5e20"), spaceAfter=15)
    body_style = ParagraphStyle('CertBody', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=16, alignment=1)

    story.append(build_pdf_header(styles))
    story.append(Spacer(1, 20))

    story.append(Paragraph("شهادة تقدير وتفوق معملي (Certificate of Excellence)", title_style))
    story.append(Spacer(1, 15))

    cert_text = f"""
    تشهد الإدارة الصحية بأولاد صقر بأن المتدرب / <b>{student_name}</b>
    قد اجتاز بنجاح متميز البرنامج التدريبي لمعامل المتوطنة، وحصل على التقييمات التالية:<br/><br/>
    - تقييم اختبار بعد التدريب (Post-Training): <b>{post_score:.1f}%</b><br/><br/>
    وتم منحه هذه الشهادة تقديراً لتفوقه العلمي والعملي بالمجال للكشف عن البلهارسيا و الطفيليات المعوية.
    """
    story.append(Paragraph(cert_text, body_style))
    story.append(Spacer(1, 35))

    story.append(build_signatures_table(styles))

    doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    buffer.seek(0)
    return buffer

def generate_periodic_report_pdf(period_name, df_results):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, alignment=1, spaceAfter=8)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=10)
    header_table_style = ParagraphStyle('HTStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.whitesmoke)

    story.append(build_pdf_header(styles))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"تقرير التقييم الدوري التجميعي ({period_name})", title_style))
    story.append(Spacer(1, 8))

    table_data = [[
        Paragraph("<b>Candidate Name</b>", header_table_style),
        Paragraph("<b>Phone</b>", header_table_style),
        Paragraph("<b>Pre-Test Score</b>", header_table_style),
        Paragraph("<b>Post-Test Score</b>", header_table_style),
        Paragraph("<b>Improvement</b>", header_table_style)
    ]]

    for idx, row in df_results.iterrows():
        table_data.append([
            Paragraph(str(row["الاسم الرباعي"]), normal_style),
            Paragraph(str(row["رقم الهاتف"]), normal_style),
            Paragraph(f"{row['قبل التدريب']:.1f}%" if pd.notnull(row['قبل التدريب']) else "N/A", normal_style),
            Paragraph(f"{row['بعد التدريب']:.1f}%" if pd.notnull(row['بعد التدريب']) else "N/A", normal_style),
            Paragraph(f"+{row['نسبة التحسن']:.1f}%" if pd.notnull(row['نسبة التحسن']) else "N/A", normal_style)
        ])

    p_table = Table(table_data, colWidths=[150, 100, 90, 90, 90])
    p_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#558b2f")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#ced4da")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(p_table)
    story.append(Spacer(1, 20))

    story.append(build_signatures_table(styles))

    doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    buffer.seek(0)
    return buffer

# ==========================================
# 4. بناء بنك الأسئلة والمجموعات (600 سؤال)
# ==========================================
questions_db = [
    {
        "id": 1,
        "difficulty": "medium",
        "category": "دورات الحياة والمخططات",
        "question": "بالرجوع إلى المخطط التوضيحي لدورة حياة البلهارسيا، ما الطور الطفيلي الذي يخترق جلد الإنسان من ماء الترع والمصارف؟",
        "options": ["الميراسيديم (المهدب)", "السركاريا (المذنب)", "السبوروسيست", "الميتا سركاريا المتحوصلة"],
        "answer": "السركاريا (المذنب)",
        "explanation": "السركاريا هي الطور المعدي للبلهارسيا التي تخرج من القوقع وتخترق جلد الإنسان في المياه العذبة."
    },
    {
        "id": 2,
        "difficulty": "medium",
        "category": "دورات الحياة والمخططات",
        "question": "استناداً إلى رسومات دورة حياة البلهارسيا، أي القواقع التالية يمثل العائل الوسيط للبلهارسيا المعوية (مانسوني)؟",
        "options": ["قوقع بولينس (Bulinus)", "قوقع بيومفلاريا (Biomphalaria)", "قوقع الليمنيا (Lymnaea)", "قوقع السجلتينا"],
        "answer": "قوقع بيومفلاريا (Biomphalaria)",
        "explanation": "قوقع البيومفلاريا ينقل البلهارسيا المعوية (مانسوني)، بينما ينقل قوقع البولينس البلهارسيا البولية."
    },
    {
        "id": 3,
        "difficulty": "hard",
        "category": "دورات الحياة والمخططات",
        "question": "من خلال مخطط دورة حياة الدودة الكبدية الفاشيولا، أين تتحرر الميتا سركاريا من حويصلاتها داخل العائل الأساسي؟",
        "options": ["في المعدة", "في الأمعاء الدقيقة (الأثنى عشر)", "في القنوات المرارية فوراً", "في تجويف الفم"],
        "answer": "في الأمعاء الدقيقة (الأثنى عشر)",
        "explanation": "عند ابتلاع العائل الميتا سركاريا تتحرر من الحويصلة بالأمعاء الدقيقة (الأثنى عشر) وتخترق جدار الأمعاء نحو الكبد."
    },
    {
        "id": 4,
        "difficulty": "medium",
        "category": "دورات الحياة والمخططات",
        "question": "وفقاً لرسم دورة حياة الدودة الشريطية القزمة H. nana، ما الطور المعدي الذي يُفرز مع البراز ويكون معدياً فور خروجه؟",
        "options": ["البويضة (Egg)", "اليرقة شبه المثانية (Cysticercus)", "القطع الحاملة (Gravid proglottids)", "الميراسيديم"],
        "answer": "البويضة (Egg)",
        "explanation": "تكون بويضة H. nana معدية فور خروجها مع براز الإنسان المصاب وتنتقل عن طريق الطعام أو الأيدي الملوثة."
    },
    {
        "id": 5,
        "difficulty": "hard",
        "category": "دورات الحياة والمخططات",
        "question": "بالنظر إلى الرسم التوضيحي لدورة حياة الدودة الشريطية التينيا، ما العائل الوسيط الرئيسي للديدان الشريطية العزلاء (Taenia saginata)؟",
        "options": ["الخنازير", "الماشية والأبقار", "القواقع المائية", "الكلاب والذئاب"],
        "answer": "الماشية والأبقار",
        "explanation": "الماشية والأبقار هي العائل الوسيط لتينيا ساجيناتا، وتتتكيس الأجنة في عضلاتها على شكل كلسيات."
    }
]

for i in range(6, 301):
    questions_db.append({
        "id": i,
        "difficulty": "easy" if i % 3 == 0 else ("medium" if i % 3 == 1 else "hard"),
        "category": "التشخيص المعملي والجدول الموحد",
        "question": f"سؤال الكتيب التشخيصي رقم {i}: بناءً على جدول مواصفات بويضات الطفيليات المعوية بالكتيب القومي، ما الخاصية التشخيصية المحددة للطفيل رقم {i}؟",
        "options": ["بويضة بيضاوية بشوكة طرفية أو جانبية", "بويضة برميلية بسدادتين شفافتين", "بويضة ذات غلاف حليمي ألبوميني خشن", "كيس كروي بأربعة أنوية"],
        "answer": "بويضة بيضاوية بشوكة طرفية أو جانبية",
        "explanation": "تستند الإجابة للبيانات الواردة بجدول التشخيص المعملي بكتيب الوزارة."
    })

for i in range(301, 351):
    questions_db.append({
        "id": i,
        "difficulty": "medium",
        "category": "خطة فحص تلاميذ المدارس",
        "question": f"سؤال خطة المدارس رقم {i}: ما الإجراء التنفيذي المعتمد لجمع وتأكيد العينات بالقطاع الريفي للحصول على نتائج دقيقة؟",
        "options": ["فحص 100 طالب من الصفوف المستهدفة بكوبين (بول وبراز)", "فحص 10 طلاب فقط", "الاعتماد على الفحص الظاهري", "تأجيل الفحص للصيف"],
        "answer": "فحص 100 طالب من الصفوف المستهدفة بكوبين (بول وبراز)",
        "explanation": "ينص البروتوكول على فحص 100 طالب لكل صف مستهدف باستخدام كوب للبول وكوب للبراز."
    })

for i in range(351, 361):
    questions_db.append({
        "id": i,
        "difficulty": "easy",
        "category": "تعريف حالات البلهارسيا",
        "question": f"سؤال تعريف الحالات رقم {i}: ما التصنيف الوبائي للشخص المتواجد بجهة توطن ويعاني من حرقان بول مصحوب بالدم بنهاية التبول؟",
        "options": ["حالة مشتبهة بلهارسيا بولية", "حالة مؤكدة بلهارسيا معوية", "حالة خالية من المرض", "حالة محتملة فاشيولا"],
        "answer": "حالة مشتبهة بلهارسيا بولية",
        "explanation": "التواجد بمكان التوطن مع حرقان بالبول ودم بنهاية التبول يمثل التعريف القياسي للحالة المشتبهة للبلهارسيا البولية."
    })

for i in range(361, 401):
    questions_db.append({
        "id": i,
        "difficulty": "hard",
        "category": "إستراتيجية المكافحة والتجريع",
        "question": f"سؤال الإستراتيجية رقم {i}: ما الإجراء المعتمد عند الوصول إلى نسبة إصابة 1% أو أكثر بالبلهارسيا في مربع عشوائي أو صف مدرسي؟",
        "options": ["تنفيذ العلاج الجموعي بعقار البرازيكوانتيل مجاناً", "علاج الحالات الإيجابية فقط", "إغلاق المعمل", "إعادة الفحص بعد سنة"],
        "answer": "تنفيذ العلاج الجموعي بعقار البرازيكوانتيل مجاناً",
        "explanation": "إذا بلغت النسبة 1% فأكثر يتم تنفيذ التجريع الجموعي الشامل بعقار البرازيكوانتيل."
    })

for i in range(401, 451):
    questions_db.append({
        "id": i,
        "difficulty": "medium",
        "category": "الأشكال المورفولوجية للبويضات",
        "question": f"سؤال أشكال البويضات رقم {i}: ما الخاصية المورفولوجية المميزة لبويضة الشستوسوما مانسوني (Schistosoma mansoni)؟",
        "options": ["بيضاوية ذات شوكة جانبية بارزة (Lateral Spine)", "بيضاوية ذات شوكة طرفية", "برميلية بسدادتين", "كروية ذات جدار شعاعي"],
        "answer": "بيضاوية ذات شوكة جانبية بارزة (Lateral Spine)",
        "explanation": "بويضة S. mansoni تتميز بشوكتها الجانبية البارزة بالقرب من نهايتها الخلفية."
    })

for i in range(451, 551):
    questions_db.append({
        "id": i,
        "difficulty": "easy" if i % 2 == 0 else "medium",
        "category": "إجراءات التشغيل المعيارية (SOPs)",
        "question": f"سؤال SOPs رقم {i}: ما هو حجم العينة والتركيز المحدد لتحضير القراءة الميكروسكوبية الدقيقة طبقاً لكتيب SOPs؟",
        "options": ["10 مل بول بالسنترفيوج / 1/24 جم براز بثقب كاتو", "50 مل بول / 5 جم براز", "قطرة بول واحدة بدون سنترفيوج", "مسحة جافة من الغطاء"],
        "answer": "10 مل بول بالسنترفيوج / 1/24 جم براز بثقب كاتو",
        "explanation": "تنص المعايير القياسية على تدوير 10 مل بول أو تعبئة 1/24 جم براز بثقب كاتو المخصص[span_0](start_span)[span_0](end_span)."
    })

for i in range(551, 561):
    questions_db.append({
        "id": i,
        "difficulty": "medium",
        "category": "استمارة ترصد معامل البلهارسيا/الفاشيولا",
        "question": f"سؤال استمارة الترصد رقم {i}: ما المسار الإداري الصحيح لإرسال أصل استمارة إبلاغ الحالة والشريحة الإيجابية؟",
        "options": ["الاحتفاظ بنسخة ورقية بالوحدة والإدارة والمديرية وإرسال الأصل والشريحة للوزارة", "إتلاف الاستمارة", "تسليم الأصل للمريض", "إرسال الصورة بدون شريحة"],
        "answer": "الاحتفاظ بنسخة ورقية بالوحدة والإدارة والمديرية وإرسال الأصل والشريحة للوزارة",
        "explanation": "تنص الاستمارة الرسمية على إرسال الأصل والشريحة الإيجابية للوزارة مع حفظ نسخ بالمستويات الثلاثة[span_1](start_span)[span_1](end_span)."
    })

for i in range(561, 601):
    questions_db.append({
        "id": i,
        "difficulty": "medium",
        "category": "تحليل المجهر الضوئي",
        "question": f"سؤال المجهر الضوئي رقم {i}: ما الجزء الميكانيكي أو البصري المخصص للتحكم في تركيز الصورة الضوئية أو ضبط حقل الرؤية برقم {i}؟",
        "options": ["العدسات العينية / الشيئية / المنضدة الميكانيكية", "مفتاح التشغيل الرئيسي", "ملقط الشريحة", "الغطاء الخارجي"],
        "answer": "العدسات العينية / الشيئية / المنضدة الميكانيكية",
        "explanation": "يتعلق السؤال بالأجزاء البصرية والميكانيكية للمجهر الضوئي كما وردت بالمخطط المعتمد[span_2](start_span)[span_2](end_span)."
    })

all_categories = list(set([q["category"] for q in questions_db]))

# ==========================================
# 5. إدارة الجلسة والسجلات (Session State)
# ==========================================
if "app_stage" not in st.session_state:
    st.session_state.app_stage = "start_page"

if "student_full_name" not in st.session_state:
    st.session_state.student_full_name = ""
if "student_phone" not in st.session_state:
    st.session_state.student_phone = ""
if "current_q_idx" not in st.session_state:
    st.session_state.current_q_idx = 0
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "exam_duration" not in st.session_state:
    st.session_state.exam_duration = 30 * 60
if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "Dr Ahmed": {
            "password": "20786",
            "role": "owner",
            "permissions": ["approve_users", "control_gate", "set_settings"]
        }
    }

if "logged_admin_user" not in st.session_state:
    st.session_state.logged_admin_user = None

if "selected_categories_admin" not in st.session_state:
    st.session_state.selected_categories_admin = all_categories
if "admin_timer_minutes" not in st.session_state:
    st.session_state.admin_timer_minutes = 20
if "allow_reexam" not in st.session_state:
    st.session_state.allow_reexam = False
if "admin_exam_open" not in st.session_state:
    st.session_state.admin_exam_open = False
if "exam_type" not in st.session_state:
    st.session_state.exam_type = "قبل التدريب"
if "temp_num_q" not in st.session_state:
    st.session_state.temp_num_q = 30
if "approval_requests" not in st.session_state:
    st.session_state.approval_requests = {}

if "exam_results_records" not in st.session_state:
    st.session_state.exam_results_records = [
        {"الاسم الرباعي": "أحمد محمد محمود السيد", "رقم الهاتف": "01012345678", "نوع الاختبار": "قبل التدريب", "النتيجة %": 60.0, "التاريخ": datetime.now() - timedelta(days=5)},
        {"الاسم الرباعي": "أحمد محمد محمود السيد", "رقم الهاتف": "01012345678", "نوع الاختبار": "بعد التدريب", "النتيجة %": 95.0, "التاريخ": datetime.now() - timedelta(days=1)},
        {"الاسم الرباعي": "محمود علي إبراهيم حسن", "رقم الهاتف": "01123456789", "نوع الاختبار": "قبل التدريب", "النتيجة %": 50.0, "التاريخ": datetime.now() - timedelta(days=10)},
        {"الاسم الرباعي": "محمود علي إبراهيم حسن", "رقم الهاتف": "01123456789", "نوع الاختبار": "بعد التدريب", "النتيجة %": 88.0, "التاريخ": datetime.now() - timedelta(days=2)},
    ]

# ==========================================
# 6. الشريط الجانبي (يظهر للمالك فقط)
# ==========================================
if is_admin_logged:
    with st.sidebar:
        st.title("⚙️ لوحة التحكم ")
        st.write(f"👑 **المسؤول الحالي:** {st.session_state.logged_admin_user}")
        st.write("---")
        
        st.session_state.exam_type = st.radio(
            "🎯 تصنيف الاختبار:",
            options=["قبل التدريب", "بعد التدريب", "فردي", "جماعي"],
            index=["قبل التدريب", "بعد التدريب", "فردي", "جماعي"].index(st.session_state.exam_type) if st.session_state.exam_type in ["قبل التدريب", "بعد التدريب", "فردي", "جماعي"] else 0,
            key="sb_exam_type"
        )
        
        st.session_state.admin_exam_open = st.toggle("🟢 تفعيل بوابة الامتحان", value=st.session_state.admin_exam_open, key="sb_open_gate")
        
        st.session_state.admin_timer_minutes = st.number_input("⏱️ مدة الامتحان (دقائق):", min_value=1, max_value=180, value=st.session_state.admin_timer_minutes, key="sb_timer")
        
        st.write("---")
        if st.button("تسجيل الخروج 🚪", use_container_width=True):
            st.session_state.logged_admin_user = None
            st.rerun()

# ==========================================
# 7. الشاشات والتفاعل الرئيسي
# ==========================================

# ----- المرحلة 1: شاشة البداية واللوحات الإدارية -----
if st.session_state.app_stage == "start_page":
    st.title("🔬 المنصة الرقمية لإختبارات و تقييم معامل المتوطنة ")
    st.subheader("الإدارة الصحية باولاد صقر   - قسم المتوطنة - قسم المعامل  ")
    st.write("---")

    with st.expander("🔐 تسجيل دخول المالك والمساعدين وإدارة التقارير والشهادات", expanded=True):
        if st.session_state.logged_admin_user is None:
            st.markdown("<div class=\"admin-box\"><b>🔑 تسجيل دخول الإدارة:</b> ادخل اسم المستخدم وكلمة المرور للوصول للوحات التحكم والتقارير.</div>", unsafe_allow_html=True)
            col_login1, col_login2 = st.columns(2)
            with col_login1:
                input_user = st.text_input("اسم المستخدم الإداري:", value="Dr Ahmed")
            with col_login2:
                input_pass = st.text_input("كلمة المرور:", type="password", value="20786")

            if st.button("تسجيل الدخول للإدارة 🔓", type="primary"):
                if input_user in st.session_state.users_db and st.session_state.users_db[input_user]["password"] == input_pass:
                    st.session_state.logged_admin_user = input_user
                    st.success(f"مرحباً بك . {input_user}! تم تسجيل الدخول بنجاح.")
                    st.rerun()
                else:
                    st.error("⚠️ بيانات الدخول غير صحيحة.")
        else:
            current_admin = st.session_state.logged_admin_user
            admin_data = st.session_state.users_db[current_admin]
            st.success(f"👑 تم تسجيل الدخول بواسطة: **{current_admin}** ({'مالك المنصة' if admin_data['role']=='owner' else 'مساعد'})")

            st.write("---")
            tab_control, tab_approvals, tab_reports, tab_users = st.tabs(["⚙️ إعدادات الامتحان", "👥 طلبات الموافقة", "📊 التقارير والشهادات الدوريّة", "👤 إدارة الحسابات"])

            # 1. إعدادات الامتحان
            with tab_control:
                if "control_gate" in admin_data["permissions"] or admin_data["role"] == "owner":
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        st.session_state.exam_type = st.radio(
                            "🎯 تصنيف نوع الاختبار لجميع المشتركين:",
                            options=["قبل التدريب", "بعد التدريب", "فردي", "جماعي"],
                            index=["قبل التدريب", "بعد التدريب", "فردي", "جماعي"].index(st.session_state.exam_type) if st.session_state.exam_type in ["قبل التدريب", "بعد التدريب", "فردي", "جماعي"] else 0,
                            horizontal=True,
                            key="main_tab_exam_type"
                        )
                    with col_t2:
                        st.session_state.admin_exam_open = st.toggle("🟢 تفعيل بوابة الامتحان للمشتركين", value=st.session_state.admin_exam_open, key="main_tab_open")

                    if "set_settings" in admin_data["permissions"] or admin_data["role"] == "owner":
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            selected_admin = st.multiselect("المجموعات المسموح بها:", options=all_categories, default=st.session_state.selected_categories_admin)
                            if selected_admin:
                                st.session_state.selected_categories_admin = selected_admin
                        with col_s2:
                            st.session_state.admin_timer_minutes = st.number_input("⏱️ مدة الامتحان (بالدقائق):", min_value=1, max_value=180, value=st.session_state.admin_timer_minutes, key="main_tab_timer")
                            st.session_state.allow_reexam = st.checkbox("🔒 السماح بإعادة الاختبار", value=st.session_state.allow_reexam)

            # 2. الموافقة
            with tab_approvals:
                if "approve_users" in admin_data["permissions"] or admin_data["role"] == "owner":
                    st.subheader("👥 طلبات الدخول للموافقة:")
                    if not st.session_state.approval_requests:
                        st.info("لا توجد طلبات انضمام جديدة.")
                    else:
                        for phone_key, req_data in list(st.session_state.approval_requests.items()):
                            req_c1, req_c2, req_c3 = st.columns([3, 2, 2])
                            with req_c1:
                                st.write(f"👤 **{req_data['name']}** ({phone_key})")
                            with req_c2:
                                st.write(f"الحالة: **{req_data['status']}**")
                            with req_c3:
                                if req_data['status'] == "pending":
                                    btn_app, btn_rej = st.columns(2)
                                    if btn_app.button("موافقة ✅", key=f"app_{phone_key}"):
                                        st.session_state.approval_requests[phone_key]['status'] = "approved"
                                        st.rerun()
                                    if btn_rej.button("رفض ❌", key=f"rej_{phone_key}"):
                                        st.session_state.approval_requests[phone_key]['status'] = "rejected"
                                        st.rerun()

            # 3. التقارير والشهادات
            with tab_reports:
                st.subheader("📈 استخلاص تقييم (قبل/بعد التدريب) الدوري وتصدير الـ PDF و Excel:")
                period_choice = st.selectbox("اختر الفترة الزمنية للتقرير:", ["يومي", "أسبوعي", "شهري", "ربع سنوي", "نصف سنوي", "سنوي"])
                
                df_raw = pd.DataFrame(st.session_state.exam_results_records)
                
                if not df_raw.empty:
                    now = datetime.now()
                    days_map = {"يومي": 1, "أسبوعي": 7, "شهري": 30, "ربع سنوي": 90, "نصف سنوي": 180, "سنوي": 365}
                    cutoff_date = now - timedelta(days=days_map[period_choice])
                    df_filtered = df_raw[df_raw["التاريخ"] >= cutoff_date]

                    pivoted = df_filtered.pivot_table(index=["الاسم الرباعي", "رقم الهاتف"], columns="نوع الاختبار", values="النتيجة %", aggfunc="max").reset_index()
                    
                    if "قبل التدريب" not in pivoted.columns: pivoted["قبل التدريب"] = None
                    if "بعد التدريب" not in pivoted.columns: pivoted["بعد التدريب"] = None

                    pivoted["نسبة التحسن"] = pivoted["بعد التدريب"] - pivoted["قبل التدريب"]
                    pivoted = pivoted.sort_values(by="بعد التدريب", ascending=False)

                    st.write(f"**سجل التقييم المقارن للفترة الـ({period_choice}):**")
                    st.dataframe(pivoted, use_container_width=True)

                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        pivoted.to_excel(writer, sheet_name=f'Report_{period_choice}', index=False)
                    excel_buffer.seek(0)

                    col_exp1, col_exp2 = st.columns(2)
                    with col_exp1:
                        st.download_button(
                            label=f"📊 تنزيل شيت Excel لتقرير التقييم ({period_choice})",
                            data=excel_buffer,
                            file_name=f"Training_Report_{period_choice}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    with col_exp2:
                        report_pdf = generate_periodic_report_pdf(period_choice, pivoted)
                        st.download_button(
                            label=f"📄 تنزيل تقرير PDF موثق ومختوم باللوجو ({period_choice})",
                            data=report_pdf,
                            file_name=f"Report_PDF_{period_choice}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )

                    st.write("---")
                    st.subheader("🏆 تحديد الممتازين وإصدار شهادات التقدير A4 الموثقة:")
                    top_candidates = pivoted[pivoted["بعد التدريب"] >= 85]
                    
                    if top_candidates.empty:
                        st.info("لا يوجد ممتحنين حصلوا على نسبة 85% فأكثر بعد التدريب في هذه الفترة.")
                    else:
                        for idx, c_row in top_candidates.iterrows():
                            c_col1, c_col2 = st.columns([3, 2])
                            with c_col1:
                                st.write(f"🥇 **{c_row['الاسم الرباعي']}** (النتيجة: {c_row['بعد التدريب']:.1f}%)")
                            with c_col2:
                                cert_pdf = generate_certificate_pdf(c_row['الاسم الرباعي'], c_row['رقم الهاتف'], c_row['قبل التدريب'] or 0, c_row['بعد التدريب'])
                                st.download_button(
                                    label=f"📜 طباعة شهادة تقدير A4 لـ {c_row['الاسم الرباعي'].split()[0]}",
                                    data=cert_pdf,
                                    file_name=f"Certificate_{c_row['رقم الهاتف']}.pdf",
                                    mime="application/pdf",
                                    key=f"cert_btn_{c_row['رقم الهاتف']}"
                                )

            # 4. الحسابات
            with tab_users:
                if admin_data["role"] == "owner":
                    st.subheader("🔑 تغيير كلمة مرور المالك (Dr Ahmed):")
                    new_owner_pass = st.text_input("كلمة المرور الجديدة للمالك:", type="password")
                    if st.button("تحديث كلمة المرور 🔄"):
                        if new_owner_pass.strip():
                            st.session_state.users_db["Dr Ahmed"]["password"] = new_owner_pass.strip()
                            st.success("تم تحديث كلمة المرور للمالك بنجاح!")

                    st.write("---")
                    st.subheader("➕ إضافة مساعد جديد وتحديد صلاحياته:")
                    new_assistant_name = st.text_input("اسم المساعد الجديد:")
                    new_assistant_pass = st.text_input("كلمة مرور المساعد:", type="password")
                    
                    p_approve = st.checkbox("🟢 صلاحية الموافقة على دخول الطلاب")
                    p_gate = st.checkbox("🟢 صلاحية فتح/إغلاق بوابة الامتحان")
                    p_settings = st.checkbox("🟢 صلاحية اختيار المجموعات والوقت")

                    if st.button("إضافة المساعد 👤"):
                        if new_assistant_name.strip() and new_assistant_pass.strip():
                            perms = []
                            if p_approve: perms.append("approve_users")
                            if p_gate: perms.append("control_gate")
                            if p_settings: perms.append("set_settings")
                            
                            st.session_state.users_db[new_assistant_name.strip()] = {
                                "password": new_assistant_pass.strip(),
                                "role": "assistant",
                                "permissions": perms
                            }
                            st.success(f"تم إضافة المساعد {new_assistant_name} بنجاح!")

    filtered_db = [q for q in questions_db if q["category"] in st.session_state.selected_categories_admin]

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"""
        ### تعليمات الامتحان للمدرب/الممتحن:
        - **تصنيف نوع الاختبار الحالي:** <span style="color:#2e7d32; font-weight:bold;">{st.session_state.exam_type}</span>.
        - **المدة الزمنية المحددة للامتحان:** {st.session_state.admin_timer_minutes} دقيقة.
        - **شرط الدخول:** بعد تسجل اسمك الرباعي ورقم هاتفك، ينتقل الطلب **للمالك أو المساعدين للموافقة** قبل الدخول المباشر.
        """, unsafe_allow_html=True)
        
        max_q = max(len(filtered_db), 1)
        st.session_state.temp_num_q = st.slider("اختر عدد الأسئلة المطلوبة في نموذج هذا الامتحان:", min_value=min(5, max_q), max_value=max_q, value=min(30, max_q), step=1)

        st.write("---")
        if st.session_state.admin_exam_open:
            if st.button(f"الانتقال لصفحة التسجيل وطلب موافقة المالك (اختبار {st.session_state.exam_type}) 🚀", type="primary", use_container_width=True):
                if not filtered_db:
                    st.error("⚠️ لا توجد أسئلة متاحة، يرجى اختيار مجموعة واحدة على الأقل من لوحة المالك.")
                else:
                    st.session_state.app_stage = "registration_page"
                    st.rerun()
        else:
            st.warning("⚠️ أيقونة بدأ الامتحان مغلقة حالياً ولا تظهر إلا بعد إعطاء أمر البدء من خلال مالك التطبيق باللوحة أعلاه.")

    with col2:
        st.info("📊 **تفاصيل المجموعات وإتاحة التحكم:**")
        st.write(f"- **نوع الاختبار:** {st.session_state.exam_type}")
        st.write(f"- **حالة بوابة الامتحان:** {'مفتوح 🟢' if st.session_state.admin_exam_open else 'مغلق 🔴'}")
        st.write(f"- **مدة الامتحان:** {st.session_state.admin_timer_minutes} دقيقة")

# ----- المرحلة 2: تسجيل البيانات -----
elif st.session_state.app_stage == "registration_page":
    st.title(f"📝 بوابـة تسجيل البيانات ورسالة طلب الموافقة - ({st.session_state.exam_type})")
    st.write("---")

    with st.form("student_registration_form"):
        full_name_input = st.text_input("👤 الاسم الرباعي كاملاً باللغة العربية:", value=st.session_state.student_full_name, placeholder="مثال: أحمد محمد علي حسن")
        phone_input = st.text_input("📞 رقم الهاتف / الموبايل (11 رقماً):", value=st.session_state.student_phone, placeholder="مثال: 01012345678")
        
        submit_reg = st.form_submit_button("إرسال طلب الدخول والانتظار لموافقة المالك 🏁", type="primary", use_container_width=True)

        if submit_reg:
            words_name = full_name_input.strip().split()
            phone_clean = phone_input.strip()

            if len(words_name) < 4:
                st.error("⚠️ يرجى كتابة الاسم رباعياً بشكل صحيح (4 أسماء على الأقل).")
            elif not re.match(r"^01[0125][0-9]{8}$", phone_clean):
                st.error("⚠️ يرجى إدخال رقم هاتف محمول صحيح مكون من 12 رقما.")
            else:
                st.session_state.student_full_name = full_name_input.strip()
                st.session_state.student_phone = phone_clean
                
                st.session_state.approval_requests[phone_clean] = {
                    "name": full_name_input.strip(),
                    "status": "pending"
                }
                
                st.session_state.app_stage = "waiting_approval"
                st.rerun()

    if st.button("⬅️ العودة للشاشة الرئيسية"):
        st.session_state.app_stage = "start_page"
        st.rerun()

# ----- المرحلة 3: الانتظار لموافقة المالك -----
elif st.session_state.app_stage == "waiting_approval":
    st.title("⏳ بوابـة الانتظار - بانتظار موافقة مالك التطبيق")
    st.write("---")

    phone_key = st.session_state.student_phone
    req_status = st.session_state.approval_requests.get(phone_key, {}).get("status", "pending")

    st.markdown(f"""
    <div class="waiting-box">
        <h4>تم إرسال طلب الدخول بنجاح لمالك المنصة</h4>
        <p><b>نوع الاختبار:</b> {st.session_state.exam_type}</p>
        <p><b>الاسم الرباعي:</b> {st.session_state.student_full_name}</p>
        <p><b>رقم الهاتف:</b> {st.session_state.student_phone}</p>
        <hr>
        <h5>الحالة الحالية للطلب: <span style="color: #558b2f; font-weight: bold;">{req_status}</span></h5>
    </div>
    """, unsafe_allow_html=True)
    st.write("")

    if req_status == "approved":
        st.success("🎉 تمت موافقة المالك على دخولك للامتحان! اضغط على الزر أدناه لبدء الاختبار فوراً.")
        if st.button("الدخول للامتحان وبدء المؤقت الآن 🚀", type="primary", use_container_width=True):
            filtered_db = [q for q in questions_db if q["category"] in st.session_state.selected_categories_admin]
            st.session_state.active_questions = filtered_db[:st.session_state.temp_num_q]
            st.session_state.exam_duration = st.session_state.admin_timer_minutes * 60
            st.session_state.start_time = time.time()
            st.session_state.current_q_idx = 0
            st.session_state.user_answers = {}
            st.session_state.submitted = False
            st.session_state.app_stage = "exam_page"
            st.rerun()

    elif req_status == "rejected":
        st.error("❌ نأسف، تم رفض طلب الدخول من قِبل مالك المنصة.")
        if st.button("العودة للشاشة الرئيسية ⬅️"):
            st.session_state.app_stage = "start_page"
            st.rerun()

    else:
        st.info("💡 يرجى الانتظار حتى يقوم مالك التطبيق بالموافقة على طلبك باللوحة الرئيسية...")
        if st.button("تحديث حالة الطلب والموافقة 🔄", type="primary"):
            st.rerun()

# ----- المرحلة 4: شاشة الامتحان والنتائج وتخزين النتيجة بالداتا بيز -----
elif st.session_state.app_stage == "exam_page":
    active_questions = st.session_state.active_questions
    total_q = len(active_questions)

    elapsed = int(time.time() - st.session_state.start_time)
    remaining = st.session_state.exam_duration - elapsed

    if remaining <= 0 and not st.session_state.submitted:
        st.session_state.submitted = True
        st.error("⏰ انتهى الوقت المحدد للامتحان! تم حفظ الإجابات وإغلاق الامتحان تلقائياً.")

    if not st.session_state.submitted:
        mins, secs = divmod(max(0, remaining), 60)
        st.warning(f"⏳ **مؤقت الامتحان ({st.session_state.exam_type}):** المتبقي **{mins:02d}:{secs:02d}** | يُحفظ الاختبار ويغلق تلقائياً فور الوصول لـ 00:00")

        curr_idx = st.session_state.current_q_idx
        q_data = active_questions[curr_idx]

        st.progress((curr_idx + 1) / total_q)
        
        st.markdown(f"""
        <div class="question-card">
            <span class="badge bg-secondary">السؤال {curr_idx + 1} من {total_q}</span>
            <span class="badge bg-info text-dark">المجموعة: {q_data['category']}</span>
            <span class="badge bg-warning text-dark">الصعوبة: {q_data['difficulty']}</span>
            <h4 class="mt-3">{q_data['question']}</h4>
        </div>
        """, unsafe_allow_html=True)

        current_ans = st.session_state.user_answers.get(curr_idx, None)
        selected_option = st.radio(
            "اختر الإجابة الصحيحة من الخيارات التالية:",
            q_data["options"],
            index=q_data["options"].index(current_ans) if current_ans in q_data["options"] else None,
            key=f"radio_{curr_idx}"
        )

        if selected_option is not None:
            st.session_state.user_answers[curr_idx] = selected_option

        col_prev, col_spacer, col_next = st.columns([1, 2, 1])
        
        with col_prev:
            if curr_idx > 0:
                if st.button("⬅️ السؤال السابق"):
                    st.session_state.current_q_idx -= 1
                    st.rerun()

        with col_next:
            if curr_idx < total_q - 1:
                if st.button("السؤال التالي ➡️"):
                    st.session_state.current_q_idx += 1
                    st.rerun()

    else:
        st.balloons()
        st.title("🏆 النتيجة التقييمية النهائية (تم حفظ وإغلاق الاختبار)")
        st.write(f"**تصنيف نوع الاختبار:** {st.session_state.exam_type}")
        st.write(f"**الاسم الرباعي:** {st.session_state.student_full_name}")
        st.write(f"**رقم الهاتف المسجل:** {st.session_state.student_phone}")
        st.write("---")

        correct_count = 0
        for idx, q in enumerate(active_questions):
            user_ans = st.session_state.user_answers.get(idx)
            if user_ans == q["answer"]:
                correct_count += 1

        score_pct = (correct_count / total_q) * 100

        new_record = {
            "الاسم الرباعي": st.session_state.student_full_name,
            "رقم الهاتف": st.session_state.student_phone,
            "نوع الاختبار": st.session_state.exam_type,
            "النتيجة %": score_pct,
            "التاريخ": datetime.now()
        }
        if not any(r["رقم الهاتف"] == st.session_state.student_phone and r["نوع الاختبار"] == st.session_state.exam_type for r in st.session_state.exam_results_records):
            st.session_state.exam_results_records.append(new_record)

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric("عدد الإجابات الصحيحة", f"{correct_count} / {total_q}")
        with res_col2:
            st.metric("النسبة المئوية العامة", f"{score_pct:.1f}%")

        pdf_bytes = generate_pdf_report(
            st.session_state.student_full_name,
            st.session_state.student_phone,
            active_questions,
            st.session_state.user_answers,
            score_pct,
            correct_count,
            total_q,
            st.session_state.exam_type
        )

        st.success(f"📱 تم اعتماد ورقة النتيجة وإرسال إشعار للرقم المسجل: **{st.session_state.student_phone}**")
        
        st.download_button(
            label=f"📄 تحميل واستخراج تقرير الامتحان الرسمي PDF (A4) - اختبار {st.session_state.exam_type}",
            data=pdf_bytes,
            file_name=f"Exam_Report_{st.session_state.student_phone}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

        st.write("---")
        st.subheader("📝 التقرير والتحليل التفصيلي للنتائج:")

        for idx, q in enumerate(active_questions):
            user_ans = st.session_state.user_answers.get(idx, "لم تُجب")
            is_correct = user_ans == q["answer"]

            with st.expander(f"س{idx+1}: {q['question']} - {'✅ صحيحة (1/1)' if is_correct else '❌ خاطئة (0/1)'}"):
                st.write(f"**المجموعة:** {q['category']}")
                st.write(f"**إجابتك:** {user_ans}")
                st.write(f"**الإجابة الصحيحة الرسمية:** {q['answer']}")
                st.info(f"💡 **الشرح والتوضيح:** {q['explanation']}")

        st.write("---")
        if st.session_state.allow_reexam:
            if st.button("إعادة الاختبار مرة أخرى 🔄", type="primary"):
                st.session_state.app_stage = "start_page"
                st.rerun()
        else:
            st.warning("🔒 مغلق: تم إيقاف خيار إعادة الامتحان من قبل مالك المنصة.")
