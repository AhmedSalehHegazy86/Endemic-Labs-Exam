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
# 1. إعدادات الصفحة والتنسيق Visuals
# ==========================================
st.set_page_config(
    page_title="المنصة الرقمية لاختبارات فريق معامل المتوطنة",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

is_admin_logged = st.session_state.get("logged_admin_user") is not None

# تنسيقات CSS متقدمة: تثبيت الشريط الجانبي في أقصى اليسار وتعديل الاتجاهات
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

    /* تثبيت الشريط الجانبي في جهة اليسار تماماً وتنسيقه */
    [data-testid="stSidebar"] {
        right: auto !important;
        left: 0 !important;
        direction: rtl !important;
        background-color: rgba(255, 255, 255, 0.98) !important;
        box-shadow: 5px 0px 25px rgba(0,0,0,0.15) !important;
    }
    
    [data-testid="stSidebar"] * {
        text-align: right !important;
        direction: rtl !important;
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
    .admin-box {
        background: rgba(255, 255, 255, 0.95);
        border: 2px solid #afb42b;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(175, 180, 43, 0.2);
    }
    .waiting-box {
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
OFFICIAL_RIGHT_HEADER = """<b>Health Administration of Awlad Sakr</b><br/><b>Endemic & Laboratories Department</b><br/><b>Endemic Labs Training Unit</b>"""

def draw_watermark(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 12)
    canvas.setFillColor(colors.HexColor("#2e7d32"))
    canvas.setFillAlpha(0.06)
    canvas.translate(A4[0] / 2.0, A4[1] / 2.0)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "Awlad Sakr Health Administration - Endemic Laboratories Training")
    canvas.restoreState()

def build_pdf_header(styles):
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, alignment=0)
    header_p = Paragraph(OFFICIAL_RIGHT_HEADER, header_style)
    
    if os.path.exists(LOGO_PATH):
        img = Image(LOGO_PATH, width=50, height=50)
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
# 3. دوال تصدير الـ PDF المعيارية (بدون مربعات)
# ==========================================
def generate_pdf_report(student_name, student_phone, active_questions, user_answers, score_pct, correct_count, total_q, exam_mode):
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
        [Paragraph(f"<b>Candidate Name:</b> {student_name}", normal_style), Paragraph(f"<b>Phone:</b> {student_phone}", normal_style)],
        [Paragraph(f"<b>Final Percentage:</b> {score_pct:.1f}%", normal_style), Paragraph(f"<b>Score:</b> {correct_count} / {total_q}", normal_style)],
        [Paragraph(f"<b>Exam Type:</b> {exam_mode}", normal_style), Paragraph(f"<b>Date:</b> {time.strftime('%Y-%m-%d %H:%M')}", normal_style)]
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
        Paragraph("<b>Grade</b>", header_table_style)
    ]]

    for idx, q in enumerate(active_questions):
        user_ans = user_answers.get(idx, "N/A")
        is_correct = user_ans == q["answer"]
        grade_str = "1 / 1" if is_correct else "0 / 1"
        
        table_data.append([
            Paragraph(str(idx + 1), normal_style),
            Paragraph(f"Q{idx+1} Item", normal_style),
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

def generate_exam_paper_pdf(exam_type_name, duration_min, questions_list, target_pages):
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
            story.append(Paragraph(f"OFFICIAL EXAM PAPER: ({exam_type_name})", title_style))
            story.append(Spacer(1, 3))

            info_data = [
                [Paragraph("<b>Candidate Name:</b> .............................................................", info_style),
                 Paragraph(f"<b>Duration:</b> {duration_min} Min", info_style)],
                [Paragraph("<b>Unit / Department:</b> .............................................................", info_style),
                 Paragraph(f"<b>Total Q:</b> {total_q} | <b>Page:</b> {page_idx+1}/{target_pages}", info_style)]
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
            q_text = f"<b>Q{idx}: {q['question']}</b>"
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
# 4. بنك الأسئلة والمجموعات
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
        "question": "ما الإجراء التنفيذي المعتمد لجمع وتأكيد العينات بالقطاع الريفي للحصول على نتائج دقيقة؟",
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
    }
]

for i in range(6, 101):
    questions_db.append({
        "id": i,
        "difficulty": "medium",
        "category": "التشخيص المعملي والجدول الموحد",
        "question": f"سؤال التشخيص المعملي رقم {i}: ما الخاصية التشخيصية لبويضات الطفيليات المعوية بالكتيب القومي؟",
        "options": ["بويضة بيضاوية بشوكة طرفية أو جانبية", "بويضة برميلية بسدادتين شفافتين", "بويضة ذات غلاف حليمي خشن", "كيس كروي بأربعة أنوية"],
        "answer": "بويضة بيضاوية بشوكة طرفية أو جانبية",
        "explanation": "تستند الإجابة للبيانات الواردة بجدول التشخيص المعملي بكتيب الوزارة."
    })

all_categories = list(set([q["category"] for q in questions_db]))

# ==========================================
# 5. إدارة الجلسة (Session State)
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
    st.session_state.temp_num_q = 5
if "target_pdf_pages" not in st.session_state:
    st.session_state.target_pdf_pages = 1
if "approval_requests" not in st.session_state:
    st.session_state.approval_requests = {}

if "exam_results_records" not in st.session_state:
    st.session_state.exam_results_records = [
        {"الاسم الرباعي": "أحمد محمد محمود السيد", "رقم الهاتف": "01012345678", "نوع الاختبار": "قبل التدريب", "النتيجة %": 60.0, "التاريخ": datetime.now() - timedelta(days=5)},
    ]

# ==========================================
# 6. الشريط الجانبي (في أيسر الصفحة)
# ==========================================
if is_admin_logged:
    with st.sidebar:
        st.title("⚙️ لوحة التحكم")
        st.write(f"👑 **المسؤول:** {st.session_state.logged_admin_user}")
        st.write("---")
        
        st.session_state.exam_type = st.radio(
            "🎯 تصنيف الاختبار:",
            options=["قبل التدريب", "بعد التدريب", "فردي", "جماعي"],
            index=["قبل التدريب", "بعد التدريب", "فردي", "جماعي"].index(st.session_state.exam_type) if st.session_state.exam_type in ["قبل التدريب", "بعد التدريب", "فردي", "جماعي"] else 0,
            key="sb_exam_type"
        )
        
        st.session_state.admin_exam_open = st.toggle("🟢 تفعيل بوابة الامتحان", value=st.session_state.admin_exam_open, key="sb_open_gate")
        st.session_state.admin_timer_minutes = st.number_input("⏱️ مدة الامتحان (دقائق):", min_value=1, max_value=180, value=st.session_state.admin_timer_minutes, key="sb_timer")
        
        filtered_db_sb = [q for q in questions_db if q["category"] in st.session_state.selected_categories_admin]
        max_q_sb = max(len(filtered_db_sb), 1)
        st.session_state.temp_num_q = st.number_input("🔢 عدد أسئلة النموذج:", min_value=1, max_value=max_q_sb, value=min(st.session_state.temp_num_q, max_q_sb), key="sb_num_q")
        st.session_state.target_pdf_pages = st.number_input("📄 صفحات الـ PDF الورقي:", min_value=1, max_value=10, value=st.session_state.target_pdf_pages, key="sb_num_pages")

        st.write("---")
        if st.button("تسجيل الخروج 🚪", use_container_width=True):
            st.session_state.logged_admin_user = None
            st.rerun()

# ==========================================
# 7. الشاشات الرئيسية
# ==========================================
if st.session_state.app_stage == "start_page":
    st.title("🔬 المنصة الرقمية لاختبارات وتقييم معامل المتوطنة")
    st.subheader("الإدارة الصحية بأولاد صقر - قسم المتوطنة وقسم المعامل")
    st.write("---")

    with st.expander("🔐 تسجيل دخول المالك وإدارة المنصة", expanded=True):
        if st.session_state.logged_admin_user is None:
            st.markdown("<div class=\"admin-box\"><b>🔑 تسجيل دخول الإدارة:</b> أدخل بيانات الاعتماد للوصول للصلاحيات الكاملة.</div>", unsafe_allow_html=True)
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
            current_admin = st.session_state.logged_admin_user
            admin_data = st.session_state.users_db[current_admin]
            st.success(f"👑 تم تسجيل الدخول بواسطة: **{current_admin}**")

            st.write("---")
            tab_control, tab_approvals, tab_reports = st.tabs(["⚙️ إعدادات وتصنيفات الامتحان", "👥 طلبات الموافقة", "📊 التقارير"])

            with tab_control:
                if "control_gate" in admin_data["permissions"] or admin_data["role"] == "owner":
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        st.session_state.exam_type = st.radio(
                            "🎯 تصنيف نوع الاختبار للمشتركين:",
                            options=["قبل التدريب", "بعد التدريب", "فردي", "جماعي"],
                            index=["قبل التدريب", "بعد التدريب", "فردي", "جماعي"].index(st.session_state.exam_type) if st.session_state.exam_type in ["قبل التدريب", "بعد التدريب", "فردي", "جماعي"] else 0,
                            horizontal=True,
                            key="main_tab_exam_type"
                        )
                    with col_t2:
                        st.session_state.admin_exam_open = st.toggle("🟢 تفعيل بوابة الامتحان للمشتركين", value=st.session_state.admin_exam_open, key="main_tab_open")

                    if "set_settings" in admin_data["permissions"] or admin_data["role"] == "owner":
                        st.write("---")
                        st.markdown("#### 📂 قائمة منسدلة متعددة الاختيارات للمجموعات والتصنيفات:")
                        selected_admin = st.multiselect(
                            "اختر التصنيفات والمجموعات المطلوبة للامتحان:",
                            options=all_categories,
                            default=st.session_state.selected_categories_admin,
                            key="categories_multiselect_box"
                        )
                        if selected_admin:
                            st.session_state.selected_categories_admin = selected_admin

                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            st.session_state.admin_timer_minutes = st.number_input("⏱️ مدة الامتحان (دقائق):", min_value=1, max_value=180, value=st.session_state.admin_timer_minutes, key="main_tab_timer")
                        with col_s2:
                            st.session_state.allow_reexam = st.checkbox("🔒 السماح بإعادة الاختبار", value=st.session_state.allow_reexam)

                        st.write("---")
                        st.markdown("#### 🎯 تخصيص عدد الأسئلة وعدد الأوراق المطبوعة:")
                        filtered_db_for_export = [q for q in questions_db if q["category"] in st.session_state.selected_categories_admin]
                        max_q = max(len(filtered_db_for_export), 1)

                        col_cfg1, col_cfg2 = st.columns(2)
                        with col_cfg1:
                            st.session_state.temp_num_q = st.number_input("🔢 عدد أسئلة النموذج:", min_value=1, max_value=max_q, value=min(st.session_state.temp_num_q, max_q), key="owner_q_number")
                        with col_cfg2:
                            st.session_state.target_pdf_pages = st.number_input("📄 عدد الأوراق (A4):", min_value=1, max_value=10, value=st.session_state.target_pdf_pages, key="owner_page_number")

                        st.write("---")
                        if filtered_db_for_export:
                            selected_export_q = filtered_db_for_export[:st.session_state.temp_num_q]
                            exam_pdf_paper = generate_exam_paper_pdf(
                                st.session_state.exam_type,
                                st.session_state.admin_timer_minutes,
                                selected_export_q,
                                st.session_state.target_pdf_pages
                            )
                            st.download_button(
                                label=f"📥 تنزيل ورقة الامتحان الورقية A4 ({len(selected_export_q)} سؤالاً - {st.session_state.target_pdf_pages} صفحات)",
                                data=exam_pdf_paper,
                                file_name=f"Exam_Paper_{st.session_state.exam_type}.pdf",
                                mime="application/pdf",
                                type="primary",
                                use_container_width=True
                            )
                        else:
                            st.warning("⚠️ يرجى اختيار مجموعة واحدة على الأقل لتصدير ورقة الامتحان.")

            with tab_approvals:
                st.subheader("👥 طلبات الدخول:")
                if not st.session_state.approval_requests:
                    st.info("لا توجد طلبات انضمام حالياً.")
                else:
                    for phone_key, req_data in list(st.session_state.approval_requests.items()):
                        rc1, rc2, rc3 = st.columns([3, 2, 2])
                        rc1.write(f"👤 **{req_data['name']}** ({phone_key})")
                        rc2.write(f"الحالة: **{req_data['status']}**")
                        if req_data['status'] == "pending":
                            if rc3.button("موافقة ✅", key=f"app_{phone_key}"):
                                st.session_state.approval_requests[phone_key]['status'] = "approved"
                                st.rerun()

            with tab_reports:
                st.subheader("📊 التقارير:")
                df_raw = pd.DataFrame(st.session_state.exam_results_records)
                if not df_raw.empty:
                    st.dataframe(df_raw, use_container_width=True)

    filtered_db = [q for q in questions_db if q["category"] in st.session_state.selected_categories_admin]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""
        ### تعليمات الامتحان للمتدربين:
        - **نوع الاختبار الحالي:** <span style="color:#2e7d32; font-weight:bold;">{st.session_state.exam_type}</span>.
        - **عدد الأسئلة:** <span style="color:#1b5e20; font-weight:bold;">{st.session_state.temp_num_q} سؤالاً</span>.
        - **المدة:** {st.session_state.admin_timer_minutes} دقيقة.
        """, unsafe_allow_html=True)

        st.write("---")
        if st.session_state.admin_exam_open:
            if st.button(f"الانتقال لصفحة التسجيل (اختبار {st.session_state.exam_type}) 🚀", type="primary", use_container_width=True):
                if not filtered_db:
                    st.error("⚠️ لا توجد أسئلة متاحة بناءً على التصنيفات المختارة.")
                else:
                    st.session_state.app_stage = "registration_page"
                    st.rerun()
        else:
            st.warning("⚠️ بوابة الامتحان مغلقة حالياً من قِبل الإدارة.")

    with col2:
        st.info("📊 **ملخص الحالة:**")
        st.write(f"- **البوابة:** {'مفتوح 🟢' if st.session_state.admin_exam_open else 'مغلق 🔴'}")
        st.write(f"- **التصنيفات المتاحة:** {len(st.session_state.selected_categories_admin)}")

elif st.session_state.app_stage == "registration_page":
    st.title(f"📝 تسجيل البيانات - ({st.session_state.exam_type})")
    st.write("---")

    with st.form("student_reg_form"):
        full_name_input = st.text_input("👤 الاسم الرباعي كاملاً:", placeholder="مثال: أحمد محمد علي حسن")
        phone_input = st.text_input("📞 رقم الهاتف (11 رقماً):", placeholder="01012345678")
        submit_reg = st.form_submit_button("إرسال طلب الدخول 🏁", type="primary", use_container_width=True)

        if submit_reg:
            words_name = full_name_input.strip().split()
            phone_clean = phone_input.strip()
            if len(words_name) < 4:
                st.error("⚠️ يرجى كتابة الاسم رباعياً.")
            elif not re.match(r"^01[0125][0-9]{8}$", phone_clean):
                st.error("⚠️ يرجى إدخال رقم هاتف صحيح مكون من 11 رقماً.")
            else:
                st.session_state.student_full_name = full_name_input.strip()
                st.session_state.student_phone = phone_clean
                st.session_state.approval_requests[phone_clean] = {"name": full_name_input.strip(), "status": "pending"}
                st.session_state.app_stage = "waiting_approval"
                st.rerun()

    if st.button("⬅️ العودة"):
        st.session_state.app_stage = "start_page"
        st.rerun()

elif st.session_state.app_stage == "waiting_approval":
    st.title("⏳ بانتظار موافقة مالك المنصة")
    st.write("---")
    phone_key = st.session_state.student_phone
    req_status = st.session_state.approval_requests.get(phone_key, {}).get("status", "pending")

    st.markdown(f"""
    <div class="waiting-box">
        <h4>تم إرسال الطلب بنجاح</h4>
        <p><b>الاسم:</b> {st.session_state.student_full_name}</p>
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
            <h4>السؤال {curr_idx + 1} من {total_q}</h4>
            <p><b>{q_data['question']}</b></p>
        </div>
        """, unsafe_allow_html=True)

        current_ans = st.session_state.user_answers.get(curr_idx, None)
        selected_option = st.radio("اختر الإجابة:", q_data["options"], index=q_data["options"].index(current_ans) if current_ans in q_data["options"] else None, key=f"radio_{curr_idx}")

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
        score_pct = (correct_count / total_q) * 100

        st.metric("النسبة المئوية", f"{score_pct:.1f}%")

        pdf_bytes = generate_pdf_report(st.session_state.student_full_name, st.session_state.student_phone, active_questions, st.session_state.user_answers, score_pct, correct_count, total_q, st.session_state.exam_type)
        st.download_button(label="📄 تحميل تقرير النتيجة PDF", data=pdf_bytes, file_name=f"Report_{st.session_state.student_phone}.pdf", mime="application/pdf", type="primary", use_container_width=True)

        if st.session_state.allow_reexam and st.button("إعادة الاختبار 🔄"):
            st.session_state.app_stage = "start_page"
            st.rerun()
