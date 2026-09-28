# ============================================================
# منصة اختبارات معامل المتوطنة
# نسخة كاملة - Arabic RTL + Arabic PDF
# ============================================================

import streamlit as st
import time
import re
import io
import os
import math
import html
import pandas as pd

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    KeepTogether
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
# 2. المسارات
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOGO_PATH = os.path.join(BASE_DIR, "logo.jpg")

FONT_PATH = os.path.join(
    BASE_DIR,
    "DejaVuSans.ttf"
)

FONT_BOLD_PATH = os.path.join(
    BASE_DIR,
    "DejaVuSans-Bold.ttf"
)


# ============================================================
# 3. تسجيل الخط العربي للـ PDF
# ============================================================

PDF_FONT_AVAILABLE = False
PDF_FONT_ERROR = ""

try:

    if os.path.exists(FONT_PATH):

        pdfmetrics.registerFont(
            TTFont(
                "Arabic",
                FONT_PATH
            )
        )

        if os.path.exists(FONT_BOLD_PATH):

            pdfmetrics.registerFont(
                TTFont(
                    "Arabic-Bold",
                    FONT_BOLD_PATH
                )
            )

        else:

            pdfmetrics.registerFont(
                TTFont(
                    "Arabic-Bold",
                    FONT_PATH
                )
            )

        PDF_FONT_AVAILABLE = True

    else:

        PDF_FONT_ERROR = (
            "لم يتم العثور على ملف DejaVuSans.ttf "
            "بجوار ملف app.py"
        )

except Exception as e:

    PDF_FONT_AVAILABLE = False

    PDF_FONT_ERROR = str(e)


# ============================================================
# 4. دوال معالجة العربية
# ============================================================

def ar(text):
    """
    تشكيل العربية وترتيبها بصرياً لعرضها داخل ReportLab.
    """

    if text is None:
        return ""

    text = str(text)

    try:

        reshaped = arabic_reshaper.reshape(
            text
        )

        displayed = get_display(
            reshaped
        )

        return html.escape(
            displayed
        ).replace(
            "\n",
            "<br/>"
        )

    except Exception:

        return html.escape(
            text
        ).replace(
            "\n",
            "<br/>"
        )


def ar_plain(text):
    """
    نفس ar ولكن بدون HTML escaping.
    يستخدم مع canvas.
    """

    if text is None:
        return ""

    text = str(text)

    try:

        reshaped = arabic_reshaper.reshape(
            text
        )

        return get_display(
            reshaped
        )

    except Exception:

        return text


def P(
    text,
    style,
    bold=False
):
    """
    إنشاء Paragraph عربي بسهولة.
    """

    content = ar(text)

    if bold:

        content = (
            "<b>"
            + content
            + "</b>"
        )

    return Paragraph(
        content,
        style
    )


# ============================================================
# 5. CSS
# ============================================================

st.markdown(
    """
<style>

@import url(
'https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap'
);

html,
body,
.stApp,
[class*="css"] {

    font-family:
        'Cairo',
        Arial,
        sans-serif !important;
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

.block-container {

    direction: rtl !important;

    text-align: right !important;

    max-width: 1200px !important;
}

[data-testid="stSidebar"] {

    display: none !important;
}

h1,
h2,
h3,
h4,
h5,
h6 {

    direction: rtl !important;

    text-align: right !important;

    font-family:
        'Cairo',
        Arial,
        sans-serif !important;
}

p,
span,
label {

    font-family:
        'Cairo',
        Arial,
        sans-serif !important;
}


/* الأسئلة */

.question-card {

    background:
        rgba(255,255,255,0.98);

    border-right:
        6px solid #558b2f;

    padding:
        25px;

    border-radius:
        15px;

    box-shadow:
        0 10px 25px rgba(0,0,0,0.08);

    margin-bottom:
        20px;

    direction:
        rtl;

    text-align:
        right;
}

.question-card h4,
.question-card p {

    direction:
        rtl;

    text-align:
        right;
}


/* الإدارة */

.admin-box {

    background:
        rgba(255,255,255,0.97);

    border:
        2px solid #afb42b;

    padding:
        20px;

    border-radius:
        12px;

    margin-bottom:
        20px;

    direction:
        rtl;

    text-align:
        right;
}


/* الانتظار */

.waiting-box {

    background:
        rgba(255,255,255,0.97);

    border:
        2px solid #33691e;

    padding:
        25px;

    border-radius:
        15px;

    margin-top:
        20px;

    direction:
        rtl;

    text-align:
        right;
}


/* Radio */

.stRadio,
.stRadio > div,
[role="radiogroup"] {

    direction:
        rtl !important;

    text-align:
        right !important;
}

.stRadio label {

    direction:
        rtl !important;

    text-align:
        right !important;

    font-weight:
        700 !important;

    color:
        #1b5e20 !important;
}


/* Checkbox */

.stCheckbox,
.stCheckbox label {

    direction:
        rtl !important;

    text-align:
        right !important;
}


/* Inputs */

input,
textarea,
select {

    direction:
        rtl !important;

    text-align:
        right !important;

    font-family:
        'Cairo',
        Arial,
        sans-serif !important;
}

input::placeholder,
textarea::placeholder {

    direction:
        rtl !important;

    text-align:
        right !important;
}


/* Buttons */

.stButton > button,
.stDownloadButton > button {

    font-family:
        'Cairo',
        Arial,
        sans-serif !important;

    font-weight:
        700 !important;

    border-radius:
        10px !important;

    direction:
        rtl !important;

    text-align:
        center !important;
}


/* Forms */

[data-testid="stForm"] {

    direction:
        rtl !important;

    text-align:
        right !important;
}


/* Expander */

[data-testid="stExpander"] {

    direction:
        rtl !important;

    text-align:
        right !important;
}


/* Alerts */

[data-testid="stAlert"] {

    direction:
        rtl !important;

    text-align:
        right !important;
}


/* Metrics */

[data-testid="stMetric"] {

    direction:
        rtl !important;

    text-align:
        right !important;
}


/* Tables */

[data-testid="stDataFrame"] {

    direction:
        rtl !important;
}


/* النتيجة */

.result-card {

    direction:
        rtl;

    text-align:
        center;

    background:
        white;

    border:
        2px solid #558b2f;

    border-radius:
        18px;

    padding:
        25px;

    margin:
        20px 0;

    box-shadow:
        0 8px 20px rgba(0,0,0,0.08);
}

.result-score {

    font-size:
        36px;

    font-weight:
        800;

    color:
        #1b5e20;
}

.result-percent {

    font-size:
        24px;

    font-weight:
        700;

    color:
        #558b2f;
}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# 6. البيانات الأساسية
# ============================================================

questions_db = [

    {
        "id": 1,
        "category": "دورات الحياة والمخططات",
        "question":
            "ما هو الطور المعدي للإنسان في دورة حياة Schistosoma haematobium؟",
        "options": [
            "الميراسيديوم Miracidium",
            "السركاريا Cercaria",
            "الميتاسركاريا Metacercaria",
            "البيضة Egg"
        ],
        "answer": 1,
        "explanation":
            "السركاريا هي الطور المعدي للإنسان وتخترق الجلد أثناء التعرض للمياه الملوثة."
    },

    {
        "id": 2,
        "category": "دورات الحياة والمخططات",
        "question":
            "ما هو العائل الوسيط الرئيسي المرتبط بدورة حياة Schistosoma mansoni؟",
        "options": [
            "Biomphalaria",
            "Lymnaea",
            "Planorbis",
            "Bulinus"
        ],
        "answer": 0,
        "explanation":
            "حلزون Biomphalaria هو العائل الوسيط الأساسي لـ Schistosoma mansoni."
    },

    {
        "id": 3,
        "category": "دورات الحياة والمخططات",
        "question":
            "أين تخرج Metacercaria الخاصة بـ Fasciola hepatica بعد دخولها جسم الإنسان؟",
        "options": [
            "المعدة",
            "الاثنا عشر",
            "القولون",
            "المستقيم"
        ],
        "answer": 1,
        "explanation":
            "تخرج الميتاسركاريا في منطقة الاثنا عشر ثم تبدأ الأطوار اللاحقة في الهجرة."
    },

    {
        "id": 4,
        "category": "خطة فحص تلاميذ المدارس",
        "question":
            "تم فحص 100 طالب، وتم توزيع عبوات لجمع عينات البول والبراز. ما الإجراء الصحيح؟",
        "options": [
            "جمع عينة بول فقط",
            "جمع عينة براز فقط",
            "جمع العينتين حسب خطة الفحص",
            "عدم جمع أي عينة"
        ],
        "answer": 2,
        "explanation":
            "يتم الالتزام بخطة الفحص المعتمدة وجمع العينات المطلوبة وفق الفئة المستهدفة."
    },

    {
        "id": 5,
        "category": "إجراءات التشغيل المعيارية SOPs",
        "question":
            "في فحص البول للكشف عن بويضات البلهارسيا، ما الإجراء المعملي المناسب للعينة؟",
        "options": [
            "استخدام العينة مباشرة دون تجهيز",
            "ترسيب العينة بالطريقة المعتمدة ثم الفحص",
            "تسخين العينة",
            "إضافة صبغة جرام"
        ],
        "answer": 1,
        "explanation":
            "يتم تجهيز عينة البول وفق الطريقة القياسية المعتمدة قبل الفحص المجهري."
    },

    {
        "id": 6,
        "category": "التشخيص المعملي والجدول الموحد",
        "question":
            "ما الصفة المميزة لبيضة Schistosoma haematobium؟",
        "options": [
            "شوكة جانبية",
            "شوكة طرفية",
            "لا تحتوي على شوكة",
            "غطاء قطبي"
        ],
        "answer": 1,
        "explanation":
            "تتميز بيضة S. haematobium بوجود شوكة طرفية واضحة."
    },

    {
        "id": 7,
        "category": "إستراتيجية المكافحة والتجريع",
        "question":
            "عند وصول معدل الإصابة في المجتمع إلى المستوى الذي يستدعي التدخل الجماعي، ما الإجراء الأساسي؟",
        "options": [
            "إيقاف الفحص",
            "العلاج الجماعي وفق الخطة المعتمدة",
            "عدم اتخاذ أي إجراء",
            "الاكتفاء بتطهير المعمل"
        ],
        "answer": 1,
        "explanation":
            "يتم تنفيذ التدخل العلاجي الجماعي وفق السياسة والعتبة المعتمدة للبرنامج."
    },

    {
        "id": 8,
        "category": "استمارة ترصد معامل البلهارسيا والفاشيولا",
        "question":
            "ما الإجراء الصحيح بالنسبة لاستمارة ترصد معامل البلهارسيا والفاشيولا؟",
        "options": [
            "إرسال الأصل للجهة المختصة والاحتفاظ بصورة",
            "إتلاف الأصل",
            "الاحتفاظ بالأصل فقط",
            "عدم تسجيل البيانات"
        ],
        "answer": 0,
        "explanation":
            "يتم استكمال الاستمارة وفق الدورة المستندية المعتمدة وإرسالها للجهة المختصة مع الاحتفاظ بالسجلات المطلوبة."
    }
]


# ============================================================
# 7. Session State
# ============================================================

defaults = {

    "logged_in": False,

    "username": "",

    "role": "",

    "page": "home",

    "admin_exam_open": False,

    "admin_exam_timing": "بعد التدريب",

    "admin_exam_mode": "فردي",

    "admin_categories": [],

    "admin_num_questions": 8,

    "admin_pdf_pages": 2,

    "admin_exam_duration": 20,

    "admin_reexam": True,

    "approval_requests": [],

    "trainee_approved": False,

    "facility_name": "",

    "student_name": "",

    "student_phone": "",

    "active_questions": [],

    "user_answers": {},

    "exam_start_time": None,

    "exam_submitted": False,

    "score": 0,

    "max_score": 0,

    "score_pct": 0,

    "exam_result": None
}


for key, value in defaults.items():

    if key not in st.session_state:

        st.session_state[key] = value


# ============================================================
# 8. دوال مساعدة
# ============================================================

def reset_exam():

    st.session_state.user_answers = {}

    st.session_state.exam_start_time = time.time()

    st.session_state.exam_submitted = False

    st.session_state.score = 0

    st.session_state.max_score = 0

    st.session_state.score_pct = 0

    st.session_state.page = "exam"


def logout():

    st.session_state.logged_in = False

    st.session_state.username = ""

    st.session_state.role = ""

    st.session_state.page = "home"


def get_categories():

    return list(
        dict.fromkeys(
            q["category"]
            for q in questions_db
        )
    )


def create_exam_questions():

    selected = st.session_state.admin_categories

    if not selected:

        pool = questions_db.copy()

    else:

        pool = [
            q
            for q in questions_db
            if q["category"] in selected
        ]

    if not pool:

        return []

    number = min(
        st.session_state.admin_num_questions,
        len(pool)
    )

    # نحافظ على ترتيب الأسئلة
    return pool[:number]


def calculate_result():

    questions = st.session_state.active_questions

    total = len(questions)

    score = 0

    for index, question in enumerate(questions):

        selected = st.session_state.user_answers.get(
            index
        )

        if selected == question["answer"]:

            score += 1

    st.session_state.score = score

    st.session_state.max_score = total

    if total > 0:

        st.session_state.score_pct = (
            score / total
        ) * 100

    else:

        st.session_state.score_pct = 0

    st.session_state.exam_submitted = True

    st.session_state.page = "result"


# ============================================================
# 9. PDF - العلامة المائية
# ============================================================

def draw_watermark(canvas, doc):

    canvas.saveState()

    if PDF_FONT_AVAILABLE:

        canvas.setFont(
            "Arabic-Bold",
            10
        )

        watermark = ar_plain(
            "الإدارة الصحية بأولاد صقر - قسم المتوطنة والمعامل"
        )

    else:

        canvas.setFont(
            "Helvetica-Bold",
            9
        )

        watermark = (
            "Aw