import streamlit as st
import time
import re
import io
import os
import math
import pandas as pd
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 1. إعدادات الصفحة وتنسيق الواجهة (RTL)
# ==========================================
st.set_page_config(
    page_title="المنصة الرقمية لاختبارات فريق معامل المتوطنة",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

is_admin_logged = st.session_state.get("logged_admin_user") is not None

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

    [data-testid="stSidebar"] {
        display: none !important;
    }

    .question-card {
        background: rgba(255, 255, 255, 0.95);
        border-right: 6px solid #558b2f;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
        margin-bottom: 20px;
    }
    .admin-box {
        background: rgba(255, 255, 255, 0.95);
        border: 2px solid #afb42b;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .waiting-box {
        background: rgba(255, 255, 255, 0.95);
        border: 2px solid #33691e;
        padding: 25px;
        border-radius: 15px;
        margin-top: 20px;
    }
    .stRadio > label, .stCheckbox > label {
        font-weight: 700 !important;
        color: #1b5e20 !important;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: bold;
    }
    p, span, div, label, h1, h2, h3, h4 {
        font-family: 'Cairo', sans-serif !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. الهيدر والعلامة المائية والتوقيعات (PDF)
# ==========================================
LOGO_PATH = "logo.jpg"

def draw_watermark(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 12)
    canvas.setFillColor(colors.HexColor("#2e7d32"))
    canvas.setFillAlpha(0.06)
    canvas.translate(A4[0] / 2.0, A4[1] / 2.0)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "Awlad Sakr Health Administration - Endemic Laboratories")
    canvas.restoreState()

def build_pdf_header(styles):
    header_text = "<b>Health Administration of Awlad Sakr</b><br/><b>Endemic & Laboratories Department</b><br/><b>Endemic Labs Training Unit</b>"
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, alignment=0)
    header_p = Paragraph(header_text, header_style)
    
    if os.path.exists(LOGO_PATH):
        img = Image(LOGO_PATH, width=45, height=45)
        header_table = Table([[header_p, img]], colWidths=[430, 90])
    else:
        header_table = Table([[header_p, ""]], colWidths=[430, 90])

    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    return header_table

def build_signatures_table(styles):
    sig_style = ParagraphStyle('SigStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=10, alignment=1)
    
    cell1 = Paragraph("<b>Training Supervisor</b><br/><br/><b>Dr. Ahmed Saleh</b>", sig_style)
    cell2 = Paragraph("<b>Lab Head</b><br/><br/>...........................", sig_style)
    cell3 = Paragraph("<b>Endemic Manager</b><br/><br/>...........................", sig_style)
    cell4 = Paragraph("<b>General Director</b><br/><br/>...........................", sig_style)
    
    sig_table = Table([[cell1, cell2, cell3, cell4]], colWidths=[130, 130, 130, 130])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#ced4da")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e9ecef")),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8f9fa")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    return sig_table

# ==========================================
# 3. دوال تصدير الـ PDF المعيارية المانعة للمربعات
# ==========================================
def generate_pdf_report(facility_name, student_name, student_phone, active_questions, user_answers, score_pct, total_score, max_score, exam_timing, exam_mode):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=12, alignment=1, spaceAfter=8)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10)
    header_table_style = ParagraphStyle('HTStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.whitesmoke)

    story.append(build_pdf_header(styles))
    story.append(Spacer(1, 6))
    story.append(Paragraph("ENDEMIC LABS EXAM EVALUATION REPORT", title_style))
    story.append(Spacer(1, 6))

    summary_data = [
        [Paragraph(f"<b>Facility:</b> {facility_name}", normal_style), Paragraph(f"<b>Candidate:</b> {student_name}", normal_style)],
        [Paragraph(f"<b>Phone:</b> {student_phone}", normal_style), Paragraph(f"<b>Final Percentage:</b> {score_pct:.1f}%", normal_style)],
        [Paragraph(f"<b>Total Score:</b> {total_score} / {max_score} Marks", normal_style), Paragraph(f"<b>Type:</b> {exam_timing} - {exam_mode}", normal_style)]
    ]
    
    summary_table = Table(summary_data, colWidths=[260, 260])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f3f5")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#689f38")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#dee2e6")),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))

    table_data = [[
        Paragraph("<b>#</b>", header_table_style),
        Paragraph("<b>Question Item</b>", header_table_style),
        Paragraph("<b>Your Answer</b>", header_table_style),
        Paragraph("<b>Correct Answer</b>", header_table_style),
        Paragraph("<b>Mark (2)</b>", header_table_style)
    ]]

    for idx, q in enumerate(active_questions):
        user_ans = user_answers.get(idx, "N/A")
        is_correct = user_ans == q["answer"]
        grade_str = "2 / 2" if is_correct else "0 / 2"
        
        table_data.append([
            Paragraph(str(idx + 1), normal_style),
            Paragraph(f"Question Item #{idx+1}", normal_style),
            Paragraph(str(user_ans)[:20], normal_style),
            Paragraph(str(q["answer"])[:20], normal_style),
            Paragraph(grade_str, normal_style)
        ])

    q_table = Table(table_data, colWidths=[20, 230, 110, 110, 50])
    q_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#558b2f")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#ced4da")),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(q_table)
    story.append(Spacer(1, 10))
    story.append(build_signatures_table(styles))

    doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    buffer.seek(0)
    return buffer

def generate_exam_paper_pdf(exam_timing, exam_mode, duration_min, questions_list, target_pages):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('ExamTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=12, alignment=1, spaceAfter=4, textColor=colors.HexColor("#1b5e20"))
    q_title_style = ParagraphStyle('QTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#2e7d32"))
    option_style = ParagraphStyle('OptStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9)
    info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10)

    total_q = len(questions_list)
    q_per_page = math.ceil(total_q / max(1, target_pages))

    for page_idx in range(target_pages):
        story.append(build_pdf_header(styles))
        story.append(Spacer(1, 3))

        if page_idx == 0:
            story.append(Paragraph(f"OFFICIAL EXAM PAPER: ({exam_timing} - {exam_mode})", title_style))
            story.append(Spacer(1, 3))

            info_data = [
                [Paragraph("<b>Facility:</b> .............................................................", info_style),
                 Paragraph(f"<b>Duration:</b> {duration_min} Min", info_style)],
                [Paragraph("<b>Candidate Name:</b> .............................................................", info_style),
                 Paragraph(f"<b>Total Q:</b> {total_q} (2 Marks/Q)", info_style)]
            ]
            info_table = Table(info_data, colWidths=[340, 195])
            info_table.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#558b2f")),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f8e9")),
                ('PADDING', (0,0), (-1,-1), 3),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 5))

        start_q_idx = page_idx * q_per_page
        end_q_idx = min(start_q_idx + q_per_page, total_q)
        page_questions = questions_list[start_q_idx:end_q_idx]

        for idx, q in enumerate(page_questions, start=start_q_idx + 1):
            q_text = f"<b>Q{idx}: {q['question']}</b> (2 Marks)"
            story.append(Paragraph(q_text, q_title_style))
            story.append(Spacer(1, 2))

            opts = q['options']
            opt_cells = []
            for i, opt in enumerate(opts):
                opt_cells.append(Paragraph(f"[  ] ({chr(65+i)}) {opt}", option_style))

            if len(opt_cells) >= 4:
                opt_matrix = [[opt_cells[0], opt_cells[1]], [opt_cells[2], opt_cells[3]]]
            else:
                opt_matrix = [[c] for c in opt_cells]

            opt_table = Table(opt_matrix, colWidths=[265, 270])
            opt_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('PADDING', (0,0), (-1,-1), 2),
            ]))
            story.append(opt_table)
            story.append(Spacer(1, 3))

        story.append(Spacer(1, 5))
        story.append(build_signatures_table(styles))

        if page_idx < target_pages - 1:
            story.append(PageBreak())

    doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    buffer.seek(0)
    return buffer

# ==========================================
# 4. بنك الأسئلة والمجموعات المعملية المتوطنة
# ==========================================
questions_db = [
    {
        "id": 1,
        "difficulty": "medium",
        "category": "دورات الحياة والمخططات",
        "question": "ما الطور الطفيلي الذي يخترق جلد الإنسان من ماء الترع والمصارف حسب مخطط البلهارسيا؟",
        "options": ["الميراسيديم (المهدب)", "السركاريا (المذنب)", "السبوروسيست", "الميتا سركاريا المتحوصلة"],
        "answer": "السركاريا (المذنب)",
        "explanation": "السركاريا هي الطور المعدي للبلهارسيا التي تخرج من القوقع وتخترق جلد الإنسان في المياه العذبة."
    },
    {
        "id": 2,
        "difficulty": "medium",
        "category": "دورات الحياة والمخططات",
        "question": "أي القواقع التالية يمثل العائل الوسيط للبلهارسيا المعوية (مانسوني)؟",
        "options": ["قوقع بولينس (Bulinus)", "قوقع بيومفلاريا (Biomphalaria)", "قوقع الليمنيا (Lymnaea)", "قوقع السجلتينا"],
        "answer": "قوقع بيومفلاريا (Biomphalaria)",
        "explanation": "قوقع البيومفلاريا ينقل البلهارسيا المعوية (مانسوني)، بينما ينقل قوقع البولينس البلهارسيا البولية."
    },
    {
        "id": 3,
        "difficulty": "hard",
        "category": "دورات الحياة والمخططات",
        "question": "أين تتحرر الميتا سركاريا من حويصلاتها داخل العائل الأساسي لدورة حياة الفاشيولا؟",
        "options": ["في المعدة", "في الأمعاء الدقيقة (الأثنى عشر)", "في القنوات المرارية فوراً", "في تجويف الفم"],
        "answer": "في الأمعاء الدقيقة (الأثنى عشر)",
        "explanation": "عند ابتلاع العائل الميتا سركاريا تتحرر من الحويصلة بالأمعاء الدقيقة (الأثنى عشر) وتخترق جدار الأمعاء نحو الكبد."
    },
    {
        "id": 4,
        "difficulty": "medium",
        "category": "خطة فحص تلاميذ المدارس",
        "question": "ما الإجراء التنفيذي المعتمد لجمع وتأكيد العينات بالقطاع الريفي للحصول على نتائج دقيقة بفحص المدارس؟",
        "options": ["فحص 100 طالب من الصفوف المستهدفة بكوبين (بول وبراز)", "فحص 10 طلاب فقط", "الاعتماد على الفحص الظاهري", "تأجيل الفحص للصيف"],
        "answer": "فحص 100 طالب من الصفوف المستهدفة بكوبين (بول وبراز)",
        "explanation": "ينص البروتوكول على فحص 100 طالب لكل صف مستهدف باستخدام كوب للبول وكوب للبراز."
    },
    {
        "id": 5,
        "difficulty": "medium",
        "category": "إجراءات التشغيل المعيارية (SOPs)",
        "question": "ما هو حجم العينة والتركيز المحدد لتحضير القراءة الميكروسكوبية الدقيقة طبقاً لكتيب SOPs؟",
        "options": ["10 مل بول بالسنترفيوج / 1/24 جم براز بثقب كاتو", "50 مل بول / 5 جم براز", "قطرة بول واحدة بدون سنترفيوج", "مسحة جافة من الغطاء"],
        "answer": "10 مل بول بالسنترفيوج / 1/24 جم براز بثقب كاتو",
        "explanation": "تنص المعايير القياسية على تدوير 10 مل بول أو تعبئة 1/24 جم براز بثقب كاتو المخصص."
    },
    {
        "id": 6,
        "difficulty": "medium",
        "category": "التشخيص المعملي والجدول الموحد",
        "question": "ما الخاصية التشخيصية لبويضة الشستوسوما هيماتوبيام (Schistosoma haematobium) تحت المجهر؟",
        "options": ["بيضاوية ذات شوكة طرفية (Terminal Spine)", "بيضاوية ذات شوكة جانبية", "برميلية بسدادتين", "كروية جدارها ألبوميني"],
        "answer": "بيضاوية ذات شوكة طرفية (Terminal Spine)",
        "explanation": "تتميز بويضة S. haematobium بوجود شوكة طرفية واضحة في نهايتها."
    },
    {
        "id": 7,
        "difficulty": "hard",
        "category": "إستراتيجية المكافحة والتجريع",
        "question": "متى يتم تنفيذ العلاج الجموعي الشامل بعقار البرازيكوانتيل في قرية أو مدرسة مستهدفة حسب الإستراتيجية القومية؟",
        "options": ["إذا بلغت نسبة الإصابة 1% فأكثر", "إذا لم تُوجد أي اصابة", "عند ظهور حالات ملاريا", "في فصل الشتاء فقط"],
        "answer": "إذا بلغت نسبة الإصابة 1% فأكثر",
        "explanation": "وفقاً لتعليمات البرنامج القومي للمكافحة، يُطبق العلاج الجموعي عند وصول معدل الإيجابية إلى 1% فأكثر."
    },
    {
        "id": 8,
        "difficulty": "medium",
        "category": "استمارة ترصد معامل البلهارسيا والفاشيولا",
        "question": "ما المسار الإداري الصحيح لإرسال أصل استمارة إبلاغ الحالة الإيجابية والشريحة المعملية ببرنامج الترصد؟",
        "options": ["إرسال الأصل والشريحة للوزارة مع حفظ نسخ ورقية بالوحدة والإدارة والمديرية", "إتلاف الاستمارة بعد التسجيل", "تسليم الأصل للمريض شخصياً", "الاحتفاظ بها بالوحدة فقط دون إرسال"],
        "answer": "إرسال الأصل والشريحة للوزارة مع حفظ نسخ ورقية بالوحدة والإدارة والمديرية",
        "explanation": "تنص تعليمات الترصد المعملي على إرسال الأصل والشريحة للتأكيد بالوزارة وحفظ النسخ بالمستويات المختلفة."
    }
]

all_categories = list(set([q["category"] for q in questions_db]))

# ==========================================
# 5. إدارة الجلسة (Session State)
# ==========================================
if "app_stage" not in st.session_state:
    st.session_state.app_stage = "start_page"
if "facility_name" not in st.session_state:
    st.session_state.facility_name = ""
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
            "role": "owner"
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
if "exam_timing" not in st.session_state:
    st.session_state.exam_timing = "قبل التدريب"
if "exam_mode" not in st.session_state:
    st.session_state.exam_mode = "فردي"
if "temp_num_q" not in st.session_state:
    st.session_state.temp_num_q = 4
if "target_pdf_pages" not in st.session_state:
    st.session_state.target_pdf_pages = 1
if "approval_requests" not in st.session_state:
    st.session_state.approval_requests = {}

# ==========================================
# 6. الهيكلة الرئيسية وتفصيل واجهة المالك مقابل المتدرب
# ==========================================
if st.session_state.app_stage == "start_page":
    st.title("🔬 المنصة الرقمية لاختبارات وتقييم معامل المتوطنة")
    st.subheader("الإدارة الصحية بأولاد صقر - قسم المتوطنة وقسم المعامل")
    st.write("---")

    # لوحة تسجيل دخول المالك (تظهر فقط إذا لم يكن مسجلاً، ولا يراها الممتحن العادي)
    if not is_admin_logged:
        with st.expander("🔐 لوحة التحكم الإدارية (تسجيل دخول المالك فقط)", expanded=True):
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                input_user = st.text_input("اسم المستخدم الإداري:", value="Dr Ahmed")
            with col_l2:
                input_pass = st.text_input("كلمة المرور:", type="password", value="20786")

            if st.button("تسجيل الدخول للإدارة 🔓", type="primary"):
                if input_user in st.session_state.users_db and st.session_state.users_db[input_user]["password"] == input_pass:
                    st.session_state.logged_admin_user = input_user
                    st.success(f"مرحباً بك {input_user}! تم تسجيل الدخول بنجاح.")
                    st.rerun()
                else:
                    st.error("⚠️ بيانات الدخول غير صحيحة.")
    else:
        # واجهة المالك الكاملة بعد تسجيل الدخول
        st.success(f"👑 المسؤول الحالي مسجل: **{st.session_state.logged_admin_user}**")
        if st.button("تسجيل الخروج من الإدارة 🚪"):
            st.session_state.logged_admin_user = None
            st.rerun()

        st.write("---")
        st.subheader("⚙️ لوحة إعدادات الامتحان وتصنيفاته:")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.session_state.exam_timing = st.radio(
                "📅 توقيت الاختبار:",
                options=["قبل التدريب", "بعد التدريب"],
                index=["قبل التدريب", "بعد التدريب"].index(st.session_state.exam_timing) if st.session_state.exam_timing in ["قبل التدريب", "بعد التدريب"] else 0,
                horizontal=True
            )
        with col_t2:
            st.session_state.exam_mode = st.radio(
                "👥 نمط الاختبار:",
                options=["فردي", "جماعي"],
                index=["فردي", "جماعي"].index(st.session_state.exam_mode) if st.session_state.exam_mode in ["فردي", "جماعي"] else 0,
                horizontal=True
            )

        st.session_state.admin_exam_open = st.toggle("🟢 تفعيل بوابة الامتحان للمشتركين", value=st.session_state.admin_exam_open)

        st.write("---")
        st.markdown("#### 📂 اختيار التصنيفات والمجموعات المعملية:")
        
        selected_cats = []
        cols_c = st.columns(min(len(all_categories), 3))
        for idx, cat in enumerate(all_categories):
            with cols_c[idx % len(cols_c)]:
                is_checked = st.checkbox(cat, value=(cat in st.session_state.selected_categories_admin), key=f"cat_chk_{idx}")
                if is_checked:
                    selected_cats.append(cat)
        
        if selected_cats:
            st.session_state.selected_categories_admin = selected_cats

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.session_state.admin_timer_minutes = st.number_input("⏱️ مدة الامتحان (دقائق):", min_value=1, max_value=180, value=st.session_state.admin_timer_minutes)
        with col_s2:
            st.session_state.allow_reexam = st.checkbox("🔒 السماح بإعادة الاختبار", value=st.session_state.allow_reexam)

        st.write("---")
        st.markdown("#### 🎯 تخصيص عدد الأسئلة وتصدير الـ PDF:")
        filtered_db_for_export = [q for q in questions_db if q["category"] in st.session_state.selected_categories_admin]
        max_q = max(len(filtered_db_for_export), 1)

        col_cfg1, col_cfg2 = st.columns(2)
        with col_cfg1:
            st.session_state.temp_num_q = st.number_input("🔢 عدد أسئلة النموذج:", min_value=1, max_value=max_q, value=min(st.session_state.temp_num_q, max_q))
        with col_cfg2:
            st.session_state.target_pdf_pages = st.number_input("📄 عدد الأوراق (A4):", min_value=1, max_value=10, value=st.session_state.target_pdf_pages)

        if filtered_db_for_export:
            selected_export_q = filtered_db_for_export[:st.session_state.temp_num_q]
            exam_pdf_paper = generate_exam_paper_pdf(
                st.session_state.exam_timing,
                st.session_state.exam_mode,
                st.session_state.admin_timer_minutes,
                selected_export_q,
                st.session_state.target_pdf_pages
            )
            st.download_button(
                label=f"📥 تنزيل ورقة الامتحان الورقية A4 ({len(selected_export_q)} سؤالاً - الدرجة الكلية: {len(selected_export_q)*2})",
                data=exam_pdf_paper,
                file_name=f"Exam_Paper_{st.session_state.exam_timing}_{st.session_state.exam_mode}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        else:
            st.warning("⚠️ يرجى اختيار تصنيف واحد على الأقل.")

        st.write("---")
        st.subheader("👥 طلبات دخول الممتحنين للموافقة:")
        if not st.session_state.approval_requests:
            st.info("لا توجد طلبات انضمام حالياً.")
        else:
            for phone_key, req_data in list(st.session_state.approval_requests.items()):
                rc1, rc2, rc3 = st.columns([3, 2, 2])
                rc1.write(f"👤 **{req_data['name']}** - المنشأة: ({req_data['facility']})")
                rc2.write(f"الحالة: **{req_data['status']}**")
                if req_data['status'] == "pending":
                    if rc3.button("موافقة ✅", key=f"app_{phone_key}"):
                        st.session_state.approval_requests[phone_key]['status'] = "approved"
                        st.rerun()

    st.write("---")
    filtered_db = [q for q in questions_db if q["category"] in st.session_state.selected_categories_admin]
    
    st.markdown(f"""
    ### تعليمات الامتحان للمتدربين:
    - **نوع الاختبار الحالي:** <span style="color:#2e7d32; font-weight:bold;">{st.session_state.exam_timing} ({st.session_state.exam_mode})</span>.
    - **عدد الأسئلة:** <span style="color:#1b5e20; font-weight:bold;">{st.session_state.temp_num_q} سؤالاً</span> (لكل سؤال درجتان | الإجمالي: {st.session_state.temp_num_q * 2} درجة).
    - **المدة الزمنية:** {st.session_state.admin_timer_minutes} دقيقة.
    """, unsafe_allow_html=True)

    if st.session_state.admin_exam_open:
        if st.button(f"الانتقال لصفحة تسجيل البيانات 🚀", type="primary", use_container_width=True):
            if not filtered_db:
                st.error("⚠️ لا توجد أسئلة متاحة بناءً على التصنيفات المختارة.")
            else:
                st.session_state.app_stage = "registration_page"
                st.rerun()
    else:
        st.warning("⚠️ بوابة الامتحان مغلقة حالياً من قِبل الإدارة.")

elif st.session_state.app_stage == "registration_page":
    st.title(f"📝 تسجيل بيانات المتدرب - ({st.session_state.exam_timing} / {st.session_state.exam_mode})")
    st.write("---")

    with st.form("student_reg_form"):
        facility_input = st.text_input("🏥 اسم المنشأة / الوحدة الصحية:", placeholder="مثال: وحدة الحصوة الصحية / مستشفى أولاد صقر")
        full_name_input = st.text_input("👤 الاسم الرباعي كاملاً:", placeholder="مثال: أحمد محمد علي حسن")
        phone_input = st.text_input("📞 رقم الهاتف (11 رقماً):", placeholder="01012345678")
        submit_reg = st.form_submit_button("إرسال طلب الدخول 🏁", type="primary", use_container_width=True)

        if submit_reg:
            facility_clean = facility_input.strip()
            words_name = full_name_input.strip().split()
            phone_clean = phone_input.strip()

            if not facility_clean:
                st.error("⚠️ يرجى إدخال اسم المنشأة.")
            elif len(words_name) < 4:
                st.error("⚠️ يرجى كتابة الاسم رباعياً بشكل صحيح.")
            elif not re.match(r"^01[0125][0-9]{8}$", phone_clean):
                st.error("⚠️ يرجى إدخال رقم هاتف محمول صحيح مكون من 11 رقماً.")
            else:
                st.session_state.facility_name = facility_clean
                st.session_state.student_full_name = full_name_input.strip()
                st.session_state.student_phone = phone_clean
                st.session_state.approval_requests[phone_clean] = {
                    "facility": facility_clean,
                    "name": full_name_input.strip(),
                    "status": "pending"
                }
                st.session_state.app_stage = "waiting_approval"
                st.rerun()

    if st.button("⬅️ العودة"):
        st.session_state.app_stage = "start_page"
        st.rerun()

elif st.session_state.app_stage == "waiting_approval":
    st.title("⏳ بانتظار موافقة الإدارة")
    st.write("---")
    phone_key = st.session_state.student_phone
    req_status = st.session_state.approval_requests.get(phone_key, {}).get("status", "pending")

    st.markdown(f"""
    <div class="waiting-box">
        <h4>تم إرسال الطلب بنجاح</h4>
        <p><b>اسم المنشأة:</b> {st.session_state.facility_name}</p>
        <p><b>اسم المتدرب:</b> {st.session_state.student_full_name}</p>
        <p><b>الحالة:</b> <span style="color: #558b2f; font-weight: bold;">{req_status}</span></p>
    </div>
    """, unsafe_allow_html=True)

    if req_status == "approved":
        st.success("🎉 تمت الموافقة!")
        if st.button("بدء الاختبار الآن 🚀", type="primary", use_container_width=True):
            filtered_db = [q for q in questions_db if q["category"] in st.session_state.selected_categories_admin]
            st.session_state.active_questions = filtered_db[:st.session_state.temp_num_q]
            st.session_state.exam_duration = st.session_state.admin_timer_minutes * 60
            st.session_state.start_time = time.time()
            st.session_state.current_q_idx = 0
            st.session_state.user_answers = {}
            st.session_state.submitted = False
            st.session_state.app_stage = "exam_page"
            st.rerun()
    else:
        if st.button("تحديث الحالة 🔄"):
            st.rerun()

elif st.session_state.app_stage == "exam_page":
    active_questions = st.session_state.active_questions
    total_q = len(active_questions)
    elapsed = int(time.time() - st.session_state.start_time)
    remaining = st.session_state.exam_duration - elapsed

    if remaining <= 0 and not st.session_state.submitted:
        st.session_state.submitted = True
        st.error("⏰ انتهى الوقت المحدد للامتحان!")

    if not st.session_state.submitted:
        mins, secs = divmod(max(0, remaining), 60)
        st.warning(f"⏳ المتبقي: {mins:02d}:{secs:02d}")

        curr_idx = st.session_state.current_q_idx
        q_data = active_questions[curr_idx]

        st.progress((curr_idx + 1) / total_q)
        st.markdown(f"""
        <div class="question-card">
            <h4>السؤال {curr_idx + 1} من {total_q} (درجتان)</h4>
            <p><b>{q_data['question']}</b></p>
        </div>
        """, unsafe_allow_html=True)

        current_ans = st.session_state.user_answers.get(curr_idx, None)
        selected_option = st.radio("اختر الإجابة الصحيحة:", q_data["options"], index=q_data["options"].index(current_ans) if current_ans in q_data["options"] else None, key=f"radio_{curr_idx}")

        if selected_option is not None:
            st.session_state.user_answers[curr_idx] = selected_option

        col_prev, col_next = st.columns(2)
        if curr_idx > 0 and col_prev.button("⬅️ السابق"):
            st.session_state.current_q_idx -= 1
            st.rerun()
        if curr_idx < total_q - 1 and col_next.button("التالي ➡️"):
            st.session_state.current_q_idx += 1
            st.rerun()
        if curr_idx == total_q - 1 and st.button("إنهاء وتسليم الاختبار ✅", type="primary"):
            st.session_state.submitted = True
            st.rerun()

    else:
        st.balloons()
        st.title("🏆 النتيجة النهائية")
        correct_count = sum(1 for idx, q in enumerate(active_questions) if st.session_state.user_answers.get(idx) == q["answer"])
        max_score = total_q * 2
        total_score = correct_count * 2
        score_pct = (correct_count / total_q) * 100 if total_q > 0 else 0

        st.metric("الدرجة الكلية", f"{total_score} / {max_score} ({score_pct:.1f}%)")

        pdf_bytes = generate_pdf_report(
            st.session_state.facility_name,
            st.session_state.student_full_name,
            st.session_state.student_phone,
            active_questions,
            st.session_state.user_answers,
            score_pct,
            total_score,
            max_score,
            st.session_state.exam_timing,
            st.session_state.exam_mode
        )
        st.download_button(
            label="📄 تحميل تقرير النتيجة الرسمي PDF",
            data=pdf_bytes,
            file_name=f"Report_{st.session_state.student_phone}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

        if st.session_state.allow_reexam and st.button("إعادة الاختبار 🔄"):
            st.session_state.app_stage = "start_page"
            st.rerun()
