import streamlit as st
import time
import re
import io
import os
import math
import pandas as pd

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import arabic_reshaper
from bidi.algorithm import get_display


# ============================================================
# 1. إعداد الصفحة
# ============================================================

st.set_page_config(
    page_title="المنصة الرقمية لاختبارات معامل المتوطنة",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# 2. إعداد الخط العربي للـ PDF
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FONT_PATH = os.path.join(BASE_DIR, "DejaVuSans.ttf")
FONT_BOLD_PATH = os.path.join(BASE_DIR, "DejaVuSans-Bold.ttf")

PDF_FONT_AVAILABLE = False

try:
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(
            TTFont("Arabic", FONT_PATH)
        )

        if os.path.exists(FONT_BOLD_PATH):
            pdfmetrics.registerFont(
                TTFont("Arabic-Bold", FONT_BOLD_PATH)
            )
        else:
            pdfmetrics.registerFont(
                TTFont("Arabic-Bold", FONT_PATH)
            )

        PDF_FONT_AVAILABLE = True

except Exception:
    PDF_FONT_AVAILABLE = False


def ar(text):
    """
    تجهيز النص العربي للعرض الصحيح داخل ReportLab.
    """
    if text is None:
        return ""

    text = str(text)

    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


# ============================================================
# 3. CSS - RTL بالكامل
# ============================================================

st.markdown(
    """
<style>

@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');

html,
body,
.stApp,
[class*="css"] {
    font-family: 'Cairo', Arial, sans-serif !important;
}

.stApp {
    background:
        linear-gradient(
            135deg,
            #fffde7 0%,
            #f0f4c3 35%,
            #dce775 70%,
            #c5e1a5 100%
        ) !important;

    background-attachment: fixed !important;

    direction: rtl !important;

    text-align: right !important;
}


/* ==========================================
   الحاوية الرئيسية
   ========================================== */

.block-container {
    direction: rtl !important;
    text-align: right !important;
}


/* ==========================================
   Sidebar
   ========================================== */

[data-testid="stSidebar"] {
    display: none !important;
}


/* ==========================================
   العناوين
   ========================================== */

h1,
h2,
h3,
h4,
h5,
h6 {
    font-family: 'Cairo', sans-serif !important;
    direction: rtl !important;
    text-align: right !important;
}


/* ==========================================
   النصوص
   ========================================== */

p,
span,
label,
div {
    font-family: 'Cairo', sans-serif !important;
}


/* ==========================================
   بطاقات الأسئلة
   ========================================== */

.question-card {
    background: rgba(255,255,255,0.97);

    border-right: 6px solid #558b2f;
    border-left: none;

    padding: 25px;

    border-radius: 15px;

    box-shadow:
        0 10px 25px rgba(0,0,0,0.08);

    margin-bottom: 20px;

    direction: rtl;
    text-align: right;
}

.question-card h4,
.question-card p {
    direction: rtl;
    text-align: right;
}


/* ==========================================
   الإدارة
   ========================================== */

.admin-box {
    background: rgba(255,255,255,0.97);

    border: 2px solid #afb42b;

    padding: 20px;

    border-radius: 12px;

    margin-bottom: 20px;

    direction: rtl;
    text-align: right;
}


/* ==========================================
   الانتظار
   ========================================== */

.waiting-box {
    background: rgba(255,255,255,0.97);

    border: 2px solid #33691e;

    padding: 25px;

    border-radius: 15px;

    margin-top: 20px;

    direction: rtl;
    text-align: right;
}


/* ==========================================
   Radio
   ========================================== */

.stRadio {
    direction: rtl !important;
    text-align: right !important;
}

.stRadio > div {
    direction: rtl !important;
}

.stRadio label {
    direction: rtl !important;
    text-align: right !important;

    font-weight: 700 !important;

    color: #1b5e20 !important;
}


/* ==========================================
   Checkbox
   ========================================== */

.stCheckbox {
    direction: rtl !important;
    text-align: right !important;
}

.stCheckbox label {
    direction: rtl !important;
    text-align: right !important;
}


/* ==========================================
   Inputs
   ========================================== */

input,
textarea,
select {
    direction: rtl !important;
    text-align: right !important;

    font-family: 'Cairo', sans-serif !important;
}

input::placeholder,
textarea::placeholder {
    direction: rtl !important;
    text-align: right !important;
}


/* ==========================================
   Buttons
   ========================================== */

.stButton > button,
.stDownloadButton > button {
    font-family: 'Cairo', sans-serif !important;

    font-weight: 700 !important;

    border-radius: 10px;

    direction: rtl !important;

    text-align: center !important;
}


/* ==========================================
   Forms
   ========================================== */

[data-testid="stForm"] {
    direction: rtl !important;
    text-align: right !important;
}


/* ==========================================
   Expander
   ========================================== */

[data-testid="stExpander"] {
    direction: rtl !important;
    text-align: right !important;
}


/* ==========================================
   Alerts
   ========================================== */

[data-testid="stAlert"] {
    direction: rtl !important;
    text-align: right !important;
}


/* ==========================================
   Metrics
   ========================================== */

[data-testid="stMetric"] {
    direction: rtl !important;
    text-align: right !important;
}


/* ==========================================
   Progress
   ========================================== */

.stProgress {
    direction: rtl !important;
}


/* ==========================================
   Dataframe
   ========================================== */

[data-testid="stDataFrame"] {
    direction: rtl !important;
}


/* ==========================================
   Divider
   ========================================== */

hr {
    border-color: #689f38 !important;
}


/* ==========================================
   نتيجة الامتحان
   ========================================== */

.result-card {
    direction: rtl;

    text-align: center;

    background: white;

    border: 2px solid #558b2f;

    border-radius: 18px;

    padding: 25px;

    margin: 20px 0;

    box-shadow:
        0 8px 20px rgba(0,0,0,0.08);
}

.result-score {
    font-size: 36px;

    font-weight: 800;

    color: #1b5e20;
}

.result-percent {
    font-size: 24px;

    font-weight: 700;

    color: #558b2f;
}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# 4. اللوجو
# ============================================================

LOGO_PATH = os.path.join(BASE_DIR, "logo.jpg")


# ============================================================
# 5. العلامة المائية
# ============================================================

def draw_watermark(canvas, doc):

    canvas.saveState()

    if PDF_FONT_AVAILABLE:

        canvas.setFont(
            "Arabic-Bold",
            11
        )

        watermark = ar(
            "الإدارة الصحية بأولاد صقر - قسم المتوطنة والمعامل"
        )

    else:

        canvas.setFont(
            "Helvetica-Bold",
            10
        )

        watermark = (
            "Awlad Sakr Health Administration"
        )

    canvas.setFillColor(
        colors.HexColor("#2e7d32")
    )

    try:
        canvas.setFillAlpha(0.06)
    except Exception:
        pass

    canvas.translate(
        A4[0] / 2,
        A4[1] / 2
    )

    canvas.rotate(45)

    canvas.drawCentredString(
        0,
        0,
        watermark
    )

    canvas.restoreState()


# ============================================================
# 6. Header PDF
# ============================================================

def build_pdf_header(styles):

    if PDF_FONT_AVAILABLE:

        header_style = ParagraphStyle(
            "ArabicHeader",
            parent=styles["Normal"],
            fontName="Arabic-Bold",
            fontSize=8.5,
            leading=11,
            alignment=2
        )

        header_text = (
            f"<b>{ar('مديرية الشئون الصحية بالشرقية')}</b><br/>"
            f"<b>{ar('الإدارة الصحية بأولاد صقر')}</b><br/>"
            f"<b>{ar('قسم المتوطنة وقسم المعامل')}</b><br/>"
            f"<b>{ar('وحدة تدريب معامل المتوطنة')}</b>"
        )

    else:

        header_style = ParagraphStyle(
            "EnglishHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=2
        )

        header_text = (
            "Health Directorate - Sharqia<br/>"
            "Awlad Sakr Health Administration<br/>"
            "Endemic & Laboratories Department<br/>"
            "Endemic Labs Training Unit"
        )

    header_p = Paragraph(
        header_text,
        header_style
    )

    if os.path.exists(LOGO_PATH):

        img = Image(
            LOGO_PATH,
            width=45,
            height=45
        )

        header_table = Table(
            [[img, header_p]],
            colWidths=[90, 430]
        )

    else:

        header_table = Table(
            [["", header_p]],
            colWidths=[90, 430]
        )

    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

            ("ALIGN", (0,0), (0,0), "RIGHT"),

            ("ALIGN", (1,0), (1,0), "RIGHT"),

            ("LEFTPADDING", (0,0), (-1,-1), 4),

            ("RIGHTPADDING", (0,0), (-1,-1), 4),

            ("TOPPADDING", (0,0), (-1,-1), 2),

            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ])
    )

    return header_table


# ============================================================
# 7. التوقيعات
# ============================================================

def build_signatures_table(styles):

    if PDF_FONT_AVAILABLE:

        sig_style = ParagraphStyle(
            "ArabicSigStyle",
            parent=styles["Normal"],
            fontName="Arabic-Bold",
            fontSize=7.5,
            leading=10,
            alignment=1
        )

        cell1 = Paragraph(
            f"<b>{ar('مسؤول التدريب')}</b><br/><br/>"
            f"<b>{ar('د. أحمد صالح')}</b>",
            sig_style
        )

        cell2 = Paragraph(
            f"<b>{ar('رئيس قسم المعامل')}</b><br/><br/>"
            f"...........................",
            sig_style
        )

        cell3 = Paragraph(
            f"<b>{ar('مسؤول المتوطنة')}</b><br/><br/>"
            f"...........................",
            sig_style
        )

        cell4 = Paragraph(
            f"<b>{ar('مدير الإدارة الصحية')}</b><br/><br/>"
            f"...........................",
            sig_style
        )

    else:

        sig_style = ParagraphStyle(
            "EnglishSig",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            alignment=1
        )

        cell1 = Paragraph(
            "<b>Training Supervisor</b><br/><br/>"
            "Dr. Ahmed Saleh",
            sig_style
        )

        cell2 = Paragraph(
            "<b>Lab Head</b><br/><br/>"
            "...........................",
            sig_style
        )

        cell3 = Paragraph(
            "<b>Endemic Manager</b><br/><br/>"
            "...........................",
            sig_style
        )

        cell4 = Paragraph(
            "<b>General Director</b><br/><br/>"
            "...........................",
            sig_style
        )

    sig_table = Table(
        [[cell4, cell3, cell2, cell1]],
        colWidths=[130,130,130,130]
    )

    sig_table.setStyle(
        TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),

            ("ALIGN", (0,0), (-1,-1), "CENTER"),

            ("BOX", (0,0), (-1,-1),
             0.5,
             colors.HexColor("#ced4da")),

            ("INNERGRID", (0,0), (-1,-1),
             0.5,
             colors.HexColor("#e9ecef")),

            ("BACKGROUND", (0,0), (-1,-1),
             colors.HexColor("#f8f9fa")),

            ("PADDING", (0,0), (-1,-1), 5),
        ])
    )

    return sig_table


# ============================================================
# 8. تقرير النتيجة PDF
# ============================================================

def generate_pdf_report(
    facility_name,
    student_name,
    student_phone,
    active_questions,
    user_answers,
    score_pct,
    total_score,
    max_score,
    exam_timing,
    exam_mode
):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=25,
        leftMargin=25,
        topMargin=25,
        bottomMargin=30
    )

    story = []

    styles = getSampleStyleSheet()

    if PDF_FONT_AVAILABLE:

        title_style = ParagraphStyle(
            "ArabicTitle",
            parent=styles["Heading1"],
            fontName="Arabic-Bold",
            fontSize=13,
            leading=17,
            alignment=1,
            spaceAfter=8,
            textColor=colors.HexColor("#1b5e20")
        )

        normal_style = ParagraphStyle(
            "ArabicNormal",
            parent=styles["Normal"],
            fontName="Arabic",
            fontSize=8.5,
            leading=12,
            alignment=2
        )

        bold_style = ParagraphStyle(
            "ArabicBold",
            parent=styles["Normal"],
            fontName="Arabic-Bold",
            fontSize=8.5,
            leading=12,
            alignment=2
        )

        header_table_style = ParagraphStyle(
            "ArabicTableHeader",
            parent=styles["Normal"],
            fontName="Arabic-Bold",
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=colors.white
        )

    else:

        title_style = ParagraphStyle(
            "EnglishTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=12,
            alignment=1
        )

        normal_style = ParagraphStyle(
            "EnglishNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            alignment=1
        )

        bold_style = normal_style

        header_table_style = ParagraphStyle(
            "EnglishHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            alignment=1,
            textColor=colors.white
        )

    story.append(
        build_pdf_header(styles)
    )

    story.append(
        Spacer(1,8)
    )

    if PDF_FONT_AVAILABLE:

        story.append(
            Paragraph(
                ar("تقرير تقييم اختبار معامل المتوطنة"),
                title_style
            )
        )

    else:

        story.append(
            Paragraph(
                "ENDEMIC LABS EXAM EVALUATION REPORT",
                title_style
            )
        )

    story.append(
        Spacer(1,8)
    )

    # --------------------------------------------------------
    # بيانات المتدرب
    # --------------------------------------------------------

    if PDF_FONT_AVAILABLE:

        summary_data = [

            [
                Paragraph(
                    f"<b>{ar('اسم المنشأة')}:</b> "
                    f"{ar(facility_name)}",
                    normal_style
                ),

                Paragraph(
                    f"<b>{ar('اسم المتدرب')}:</b> "
                    f"{ar(student_name)}",
                    normal_style
                )
            ],

            [
                Paragraph(
                    f"<b>{ar('رقم الهاتف')}:</b> "
                    f"{ar(student_phone)}",
                    normal_style
                ),

                Paragraph(
                    f"<b>{ar('النسبة النهائية')}:</b> "
                    f"{score_pct:.1f}%",
                    normal_style
                )
            ],

            [
                Paragraph(
                    f"<b>{ar('الدرجة')}:</b> "
                    f"{total_score} / {max_score}",
                    normal_style
                ),

                Paragraph(
                    f"<b>{ar('نوع الاختبار')}:</b> "
                    f"{ar(exam_timing)} - "
                    f"{ar(exam_mode)}",
                    normal_style
                )
            ]
        ]

        summary_data = [
            [row[1], row[0]]
            for row in summary_data
        ]

    else:

        summary_data = [

            [
                Paragraph(
                    f"<b>Facility:</b> {facility_name}",
                    normal_style
                ),

                Paragraph(
                    f"<b>Candidate:</b> {student_name}",
                    normal_style
                )
            ],

            [
                Paragraph(
                    f"<b>Phone:</b> {student_phone}",
                    normal_style
                ),

                Paragraph(
                    f"<b>Final Percentage:</b> "
                    f"{score_pct:.1f}%",
                    normal_style
                )
            ],

            [
                Paragraph(
                    f"<b>Total Score:</b> "
                    f"{total_score}/{max_score}",
                    normal_style
                ),

                Paragraph(
                    f"<b>Type:</b> "
                    f"{exam_timing} - {exam_mode}",
                    normal_style
                )
            ]
       