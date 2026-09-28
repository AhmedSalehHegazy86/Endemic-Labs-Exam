import os
import io
import re
import time
import sqlite3
import html
from datetime import datetime

import streamlit as st

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import arabic_reshaper
from bidi.algorithm import get_display


# =========================================================
# 1. إعداد الصفحة
# =========================================================

st.set_page_config(
    page_title="المنصة الرقمية لاختبارات معامل المتوطنة",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# 2. المسارات
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(
    BASE_DIR,
    "endemic_labs_exam.db"
)

LOGO_PATH = os.path.join(
    BASE_DIR,
    "logo.jpg"
)

FONT_PATH = os.path.join(
    BASE_DIR,
    "DejaVuSans.ttf"
)

FONT_BOLD_PATH = os.path.join(
    BASE_DIR,
    "DejaVuSans-Bold.ttf"
)


# =========================================================
# 3. إعداد الخط العربي للـ PDF
# =========================================================

PDF_FONT_AVAILABLE = False

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

except Exception:
    PDF_FONT_AVAILABLE = False


# =========================================================
# 4. CSS
# =========================================================

st.markdown(
    """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
    }

    .stApp {
        background:
        linear-gradient(
            135deg,
            #064e3b 0%,
            #065f46 45%,
            #0f172a 100%
        );
    }

    .main-title {
        background:
        linear-gradient(
            90deg,
            #064e3b,
            #047857,
            #059669
        );
        padding: 20px;
        border-radius: 18px;
        color: white;
        text-align: center;
        font-size: 30px;
        font-weight: 800;
        margin-bottom: 20px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.25);
    }

    .section-title {
        background: white;
        padding: 14px 18px;
        border-radius: 14px;
        color: #064e3b;
        font-size: 22px;
        font-weight: 800;
        margin: 15px 0;
        border-right: 6px solid #facc15;
        box-shadow: 0 5px 18px rgba(0,0,0,0.15);
    }

    .card {
        background: white;
        padding: 20px;
        border-radius: 18px;
        margin-bottom: 18px;
        box-shadow: 0 7px 22px rgba(0,0,0,0.18);
        border-right: 5px solid #059669;
    }

    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 6px 18px rgba(0,0,0,0.18);
        border-top: 5px solid #059669;
    }

    .metric-title {
        color: #64748b;
        font-size: 15px;
        font-weight: 600;
    }

    .metric-value {
        color: #064e3b;
        font-size: 28px;
        font-weight: 800;
    }

    .success-box {
        background: #ecfdf5;
        border: 2px solid #10b981;
        color: #065f46;
        padding: 16px;
        border-radius: 14px;
        font-weight: 700;
        margin: 12px 0;
    }

    .warning-box {
        background: #fffbeb;
        border: 2px solid #f59e0b;
        color: #92400e;
        padding: 16px;
        border-radius: 14px;
        font-weight: 700;
        margin: 12px 0;
    }

    .danger-box {
        background: #fef2f2;
        border: 2px solid #ef4444;
        color: #991b1b;
        padding: 16px;
        border-radius: 14px;
        font-weight: 700;
        margin: 12px 0;
    }

    .info-box {
        background: #eff6ff;
        border: 2px solid #3b82f6;
        color: #1e3a8a;
        padding: 16px;
        border-radius: 14px;
        font-weight: 700;
        margin: 12px 0;
    }

    .question-box {
        background: white;
        padding: 22px;
        border-radius: 18px;
        margin-bottom: 20px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.18);
        border-right: 5px solid #047857;
    }

    .question-number {
        background: #064e3b;
        color: white;
        display: inline-block;
        padding: 6px 13px;
        border-radius: 20px;
        font-weight: 800;
        margin-bottom: 10px;
    }

    .question-text {
        color: #111827;
        font-size: 19px;
        font-weight: 700;
        line-height: 1.8;
    }

    .exam-header {
        background:
        linear-gradient(
            90deg,
            #064e3b,
            #047857
        );
        color: white;
        padding: 20px;
        border-radius: 18px;
        margin-bottom: 20px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.25);
    }

    .timer-box {
        background: #111827;
        color: #facc15;
        padding: 12px 18px;
        border-radius: 12px;
        font-size: 22px;
        font-weight: 800;
        text-align: center;
    }

    .rtl {
        direction: rtl;
        text-align: right;
    }

    div[data-testid="stForm"] {
        background: white;
        padding: 20px;
        border-radius: 18px;
        border: 2px solid #059669;
    }

    .stButton > button {
        width: 100%;
        border-radius: 12px;
        border: none;
        background: linear-gradient(
            90deg,
            #047857,
            #059669
        );
        color: white;
        font-weight: 800;
        min-height: 45px;
    }

    .stButton > button:hover {
        background: linear-gradient(
            90deg,
            #065f46,
            #047857
        );
        color: white;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 5. تحويل النص العربي للـ PDF
# =========================================================

def ar(text):
    if text is None:
        return ""

    text = str(text)

    try:
        reshaped = arabic_reshaper.reshape(text)
        displayed = get_display(reshaped)

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
    if text is None:
        return ""

    text = str(text)

    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)

    except Exception:
        return text


# =========================================================
# 6. بنك الأسئلة
# =========================================================

QUESTIONS_DB = [
    {
        "id": 1,
        "category": "البلهارسيا",
        "question": "ما هو الطور المعدي للإنسان في دورة حياة البلهارسيا؟",
        "options": [
            "البيضة",
            "الميراسيديوم",
            "السركاريا",
            "الطور البالغ",
        ],
        "answer": 2,
    },
    {
        "id": 2,
        "category": "البلهارسيا",
        "question": "ما هو العائل الوسيط للبلهارسيا المانسونية Schistosoma mansoni؟",
        "options": [
            "Biomphalaria",
            "Lymnaea",
            "Bulinus",
            "Planorbis",
        ],
        "answer": 0,
    },
    {
        "id": 3,
        "category": "الفاشيولا",
        "question": "أين تخرج الميتاسركاريا الخاصة بالفاشيولا من الكيس بعد ابتلاعها؟",
        "options": [
            "المعدة",
            "الاثنا عشر",
            "القولون",
            "المستقيم",
        ],
        "answer": 1,
    },
    {
        "id": 4,
        "category": "الفحص المدرسي",
        "question": "عند فحص 100 طالب بالمدرسة للكشف عن الطفيليات، ما الإجراء الصحيح؟",
        "options": [
            "جمع العينات وفق خطة الفحص المعتمدة",
            "جمع البول فقط لكل الطلاب",
            "جمع البراز فقط لكل الطلاب",
            "عدم تسجيل بيانات الطلاب",
        ],
        "answer": 0,
    },
    {
        "id": 5,
        "category": "التشخيص المعملي",
        "question": "ما الإجراء المناسب لتحضير عينة البول لفحص بويضات البلهارسيا البولية؟",
        "options": [
            "صبغ العينة مباشرة فقط",
            "ترسيب العينة بالطريقة المعتمدة ثم الفحص المجهري",
            "تسخين البول حتى الغليان",
            "تخفيف العينة بالماء فقط",
        ],
        "answer": 1,
    },
    {
        "id": 6,
        "category": "البلهارسيا",
        "question": "ما العلامة المميزة لبويضة Schistosoma haematobium؟",
        "options": [
            "شوكة طرفية",
            "شوكة جانبية",
            "غطاء قطبي",
            "لا تحتوي على شوكة",
        ],
        "answer": 0,
    },
    {
        "id": 7,
        "category": "المكافحة",
        "question": "عند الوصول إلى المستوى الذي يستدعي التدخل وفق الخطة المعتمدة، ما الإجراء؟",
        "options": [
            "إيقاف الترصد",
            "عدم اتخاذ أي إجراء",
            "تنفيذ التدخل والعلاج الجماعي وفق الخطة المعتمدة",
            "إلغاء الفحص",
        ],
        "answer": 2,
    },
    {
        "id": 8,
        "category": "الترصد",
        "question": "عند استكمال استمارة الترصد، ما الإجراء الصحيح؟",
        "options": [
            "إتلاف الاستمارة",
            "إرسال الأصل للجهة المسؤولة والاحتفاظ بصورة",
            "الاحتفاظ بها دون إرسال",
            "إرسال صورة فقط دون الأصل",
        ],
        "answer": 1,
    },
]


# =========================================================
# 7. قاعدة البيانات
# =========================================================

def get_db():
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS trainees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            approved_at TEXT,
            exam_started_at TEXT,
            exam_submitted_at TEXT,
            score INTEGER,
            max_score INTEGER,
            percentage REAL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS exam_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainee_id INTEGER NOT NULL,
            student_name TEXT NOT NULL,
            facility TEXT NOT NULL,
            phone TEXT NOT NULL,
            score INTEGER NOT NULL,
            max_score INTEGER NOT NULL,
            percentage REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (trainee_id)
            REFERENCES trainees(id)
        )
        """
    )

    defaults = {
        "exam_open": "0",
        "exam_timing": "بعد التدريب",
        "exam_mode": "فردي",
        "categories": "",
        "num_questions": "8",
        "exam_duration": "20",
        "pdf_pages": "2",
        "reexam": "1",
    }

    for key, value in defaults.items():
        cur.execute(
            """
            INSERT OR IGNORE INTO settings
            (key, value)
            VALUES (?, ?)
            """,
            (key, value),
        )

    conn.commit()
    conn.close()


init_db()


# =========================================================
# 8. وظائف الإعدادات
# =========================================================

def get_setting(key, default=None):
    conn = get_db()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT value
        FROM settings
        WHERE key = ?
        """,
        (key,),
    )

    row = cur.fetchone()

    conn.close()

    if row is None:
        return default

    return row["value"]


def set_setting(key, value):
    conn = get_db()

    conn.execute(
        """
        INSERT OR REPLACE INTO settings
        (key, value)
        VALUES (?, ?)
        """,
        (key, str(value)),
    )

    conn.commit()
    conn.close()


def get_bool_setting(key, default=False):
    value = get_setting(
        key,
        "1" if default else "0"
    )

    return str(value) == "1"


def get_int_setting(key, default=0):
    value = get_setting(
        key,
        str(default)
    )

    try:
        return int(value)
    except Exception:
        return default


def get_categories_setting():
    value = get_setting(
        "categories",
        ""
    )

    if not value:
        return []

    return [
        x.strip()
        for x in value.split(",")
        if x.strip()
    ]


def save_settings(
    exam_open,
    exam_timing,
    exam_mode,
    categories,
    num_questions,
    exam_duration,
    pdf_pages,
    reexam,
):
    set_setting(
        "exam_open",
        "1" if exam_open else "0"
    )

    set_setting(
        "exam_timing",
        exam_timing
    )

    set_setting(
        "exam_mode",
        exam_mode
    )

    set_setting(
        "categories",
        ",".join(categories)
    )

    set_setting(
        "num_questions",
        num_questions
    )

    set_setting(
        "exam_duration",
        exam_duration
    )

    set_setting(
        "pdf_pages",
        pdf_pages
    )

    set_setting(
        "reexam",
        "1" if reexam else "0"
    )


# =========================================================
# 9. وظائف المتدربين
# =========================================================

def create_trainee_request(
    facility,
    name,
    phone
):
    conn = get_db()

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO trainees
        (
            facility,
            name,
            phone,
            status,
            created_at
        )
        VALUES (?, ?, ?, 'pending', ?)
        """,
        (
            facility,
            name,
            phone,
            now,
        ),
    )

    trainee_id = cur.lastrowid

    conn.commit()
    conn.close()

    return trainee_id


def get_pending_requests():
    conn = get_db()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM trainees
        WHERE status = 'pending'
        ORDER BY id DESC
        """
    )

    rows = cur.fetchall()

    conn.close()

    return rows


def get_trainee(trainee_id):
    conn = get_db()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM trainees
        WHERE id = ?
        """,
        (trainee_id,),
    )

    row = cur.fetchone()

    conn.close()

    return row


def approve_trainee(trainee_id):
    conn = get_db()

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn.execute(
        """
        UPDATE trainees
        SET status = 'approved',
            approved_at = ?
        WHERE id = ?
        """,
        (
            now,
            trainee_id,
        ),
    )

    conn.commit()
    conn.close()


def reject_trainee(trainee_id):
    conn = get_db()

    conn.execute(
        """
        UPDATE trainees
        SET status = 'rejected'
        WHERE id = ?
        """,
        (trainee_id,),
    )

    conn.commit()
    conn.close()


def mark_exam_started(trainee_id):
    conn = get_db()

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn.execute(
        """
        UPDATE trainees
        SET exam_started_at = ?,
            status = 'exam'
        WHERE id = ?
        """,
        (
            now,
            trainee_id,
        ),
    )

    conn.commit()
    conn.close()


# =========================================================
# 10. حفظ النتائج
# =========================================================

def save_result(
    trainee_id,
    score,
    max_score
):
    conn = get_db()

    trainee = get_trainee(
        trainee_id
    )

    if trainee is None:
        conn.close()
        return

    percentage = 0

    if max_score > 0:
        percentage = (
            score / max_score
        ) * 100

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn.execute(
        """
        UPDATE trainees
        SET status = 'completed',
            exam_submitted_at = ?,
            score = ?,
            max_score = ?,
            percentage = ?
        WHERE id = ?
        """,
        (
            now,
            score,
            max_score,
            percentage,
            trainee_id,
        ),
    )

    conn.execute(
        """
        INSERT INTO exam_results
        (
            trainee_id,
            student_name,
            facility,
            phone,
            score,
            max_score,
            percentage,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trainee_id,
            trainee["name"],
            trainee["facility"],
            trainee["phone"],
            score,
            max_score,
            percentage,
            now,
        ),
    )

    conn.commit()
    conn.close()


def get_results():
    conn = get_db()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM exam_results
        ORDER BY id DESC
        """
    )

    rows = cur.fetchall()

    conn.close()

    return rows


# =========================================================
# 11. إعدادات الاختبار
# =========================================================

def get_all_categories():
    return sorted(
        list(
            set(
                q["category"]
                for q in QUESTIONS_DB
            )
        )
    )


def create_exam_questions():
    categories = get_categories_setting()

    if categories:
        questions = [
            q
            for q in QUESTIONS_DB
            if q["category"] in categories
        ]
    else:
        questions = QUESTIONS_DB.copy()

    number = get_int_setting(
        "num_questions",
        len(questions)
    )

    if number <= 0:
        number = len(questions)

    return questions[:number]


def get_exam_config():
    return {
        "open": get_bool_setting(
            "exam_open"
        ),
        "timing": get_setting(
            "exam_timing",
            "بعد التدريب"
        ),
        "mode": get_setting(
            "exam_mode",
            "فردي"
        ),
        "categories": get_categories_setting(),
        "num_questions": get_int_setting(
            "num_questions",
            8
        ),
        "duration": get_int_setting(
            "exam_duration",
            20
        ),
        "pdf_pages": get_int_setting(
            "pdf_pages",
            2
        ),
        "reexam": get_bool_setting(
            "reexam",
            True
        ),
    }


# =========================================================
# 12. Session State
# =========================================================

defaults = {
    "page": "home",
    "logged_in": False,
    "username": "",
    "role": "",
    "trainee_id": None,
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
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# 13. بدء الاختبار
# =========================================================

def reset_exam():
    questions = create_exam_questions()

    st.session_state.active_questions = questions

    st.session_state.user_answers = {}

    st.session_state.exam_start_time = time.time()

    st.session_state.exam_submitted = False

    st.session_state.score = 0

    st.session_state.max_score = len(
        questions
    )

    st.session_state.score_pct = 0

    if st.session_state.trainee_id:
        mark_exam_started(
            st.session_state.trainee_id
        )

    st.session_state.page = "exam"


# =========================================================
# 14. حساب النتيجة
# =========================================================

def calculate_result():
    questions = st.session_state.active_questions

    score = 0

    for q in questions:
        selected = st.session_state.user_answers.get(
            q["id"]
        )

        if selected == q["answer"]:
            score += 1

    max_score = len(questions)

    percentage = 0

    if max_score > 0:
        percentage = (
            score / max_score
        ) * 100

    st.session_state.score = score
    st.session_state.max_score = max_score
    st.session_state.score_pct = percentage
    st.session_state.exam_submitted = True

    if st.session_state.trainee_id:
        save_result(
            st.session_state.trainee_id,
            score,
            max_score
        )

    st.session_state.page = "result"


# =========================================================
# 15. تسجيل الخروج
# =========================================================

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.page = "home"


# =========================================================
# 16. PDF Watermark
# =========================================================

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

        watermark = "Endemic Laboratories"

    canvas.setFillColor(
        colors.HexColor("#90a4ae")
    )

    canvas.drawCentredString(
        A4[0] / 2,
        18,
        watermark
    )

    canvas.restoreState()


# =========================================================
# 17. رأس PDF
# =========================================================

def build_pdf_header():
    elements = []

    if os.path.exists(LOGO_PATH):
        try:
            logo = Image(
                LOGO_PATH,
                width=70,
                height=70
            )

            table = Table(
                [[
                    logo,
                    Paragraph(
                        ar(
                            "المنصة الرقمية لاختبارات معامل المتوطنة"
                        ),
                        ParagraphStyle(
                            "title",
                            fontName=(
                                "Arabic-Bold"
                                if PDF_FONT_AVAILABLE
                                else "Helvetica-Bold"
                            ),
                            fontSize=18,
                            leading=24,
                            alignment=2,
                            textColor=colors.HexColor(
                                "#064e3b"
                            ),
                        ),
                    ),
                ]],
                colWidths=[
                    80,
                    430
                ],
            )

            table.setStyle(
                TableStyle(
                    [
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE",
                        ),
                        (
                            "ALIGN",
                            (1, 0),
                            (1, 0),
                            "RIGHT",
                        ),
                    ]
                )
            )

            elements.append(table)

        except Exception:
            pass

    else:
        elements.append(
            Paragraph(
                ar(
                    "المنصة الرقمية لاختبارات معامل المتوطنة"
                ),
                ParagraphStyle(
                    "title2",
                    fontName=(
                        "Arabic-Bold"
                        if PDF_FONT_AVAILABLE
                        else "Helvetica-Bold"
                    ),
                    fontSize=18,
                    leading=24,
                    alignment=2,
                    textColor=colors.HexColor(
                        "#064e3b"
                    ),
                ),
            )
        )

    elements.append(
        Spacer(1, 15)
    )

    return elements


# =========================================================
# 18. جدول التوقيعات
# =========================================================

def build_signatures_table():
    font = (
        "Arabic"
        if PDF_FONT_AVAILABLE
        else "Helvetica"
    )

    table = Table(
        [
            [
                Paragraph(
                    ar(
                        "توقيع المتدرب"
                    ),
                    ParagraphStyle(
                        "sig1",
                        fontName=font,
                        fontSize=10,
                        alignment=1,
                    ),
                ),
                Paragraph(
                    ar(
                        "مسؤول التدريب"
                    ),
                    ParagraphStyle(
                        "sig2",
                        fontName=font,
                        fontSize=10,
                        alignment=1,
                    ),
                ),
                Paragraph(
                    ar(
                        "رئيس القسم"
                    ),
                    ParagraphStyle(
                        "sig3",
                        fontName=font,
                        fontSize=10,
                        alignment=1,
                    ),
                ),
            ],
            [
                "\n\n",
                "\n\n",
                "\n\n",
            ],
        ],
        colWidths=[
            170,
            170,
            170,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    return table


# =========================================================
# 19. إنشاء PDF النتيجة
# =========================================================

def generate_pdf_report():
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=35,
        title="نتيجة اختبار معامل المتوطنة",
    )

    styles = getSampleStyleSheet()

    font_normal = (
        "Arabic"
        if PDF_FONT_AVAILABLE
        else "Helvetica"
    )

    font_bold = (
        "Arabic-Bold"
        if PDF_FONT_AVAILABLE
        else "Helvetica-Bold"
    )

    normal_style = ParagraphStyle(
        "ArabicNormal",
        parent=styles["Normal"],
        fontName=font_normal,
        fontSize=11,
        leading=18,
        alignment=2,
        textColor=colors.HexColor(
            "#111827"
        ),
    )

    title_style = ParagraphStyle(
        "ArabicTitle",
        parent=styles["Title"],
        fontName=font_bold,
        fontSize=20,
        leading=26,
        alignment=1,
        textColor=colors.HexColor(
            "#064e3b"
        ),
    )

    elements = []

    elements.extend(
        build_pdf_header()
    )

    elements.append(
        Paragraph(
            ar(
                "تقرير نتيجة الاختبار"
            ),
            title_style,
        )
    )

    elements.append(
        Spacer(1, 15)
    )

    trainee = None

    if st.session_state.trainee_id:
        trainee = get_trainee(
            st.session_state.trainee_id
        )

    facility = (
        trainee["facility"]
        if trainee
        else st.session_state.facility_name
    )

    name = (
        trainee["name"]
        if trainee
        else st.session_state.student_name
    )

    phone = (
        trainee["phone"]
        if trainee
        else st.session_state.student_phone
    )

    info_data = [
        [
            Paragraph(
                ar("الاسم"),
                normal_style
            ),
            Paragraph(
                ar(name),
                normal_style
            ),
        ],
        [
            Paragraph(
                ar("جهة العمل"),
                normal_style
            ),
            Paragraph(
                ar(facility),
                normal_style
            ),
        ],
        [
            Paragraph(
                ar("رقم الهاتف"),
                normal_style
            ),
            Paragraph(
                ar(phone),
                normal_style
            ),
        ],
        [
            Paragraph(
                ar("التاريخ"),
                normal_style
            ),
            Paragraph(
                ar(
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M"
                    )
                ),
                normal_style
            ),
        ],
    ]

    info_table = Table(
        info_data,
        colWidths=[
            130,
            380,
        ],
    )

    info_table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.grey,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor(
                        "#ecfdf5"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    elements.append(
        info_table
    )

    elements.append(
        Spacer(1, 20)
    )

    result_data = [
        [
            Paragraph(
                ar("الدرجة"),
                normal_style
            ),
            Paragraph(
                ar(
                    f"{st.session_state.score} / "
                    f"{st.session_state.max_score}"
                ),
                normal_style
            ),
        ],
        [
            Paragraph(
                ar("النسبة المئوية"),
                normal_style
            ),
            Paragraph(
                ar(
                    f"{st.session_state.score_pct:.1f}%"
                ),
                normal_style
            ),
        ],
    ]

    result_table = Table(
        result_data,
        colWidths=[
            180,
            330,
        ],
    )

    result_table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.HexColor(
                        "#059669"
                    ),
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor(
                        "#f0fdf4"
                    ),
                ),
            ]
        )
    )

    elements.append(
        result_table
    )

    elements.append(
        Spacer(1, 25)
    )

    elements.append(
        Paragraph(
            ar(
                "تفاصيل الإجابات"
            ),
            ParagraphStyle(
                "details",
                fontName=font_bold,
                fontSize=15,
                leading=20,
                alignment=2,
                textColor=colors.HexColor(
                    "#064e3b"
                ),
            ),
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    for index, q in enumerate(
        st.session_state.active_questions,
        start=1
    ):
        selected = st.session_state.user_answers.get(
            q["id"]
        )

        correct = (
            selected == q["answer"]
        )

        if selected is None:
            answer_text = "لم تتم الإجابة"

        else:
            answer_text = q["options"][
                selected
            ]

        correct_text = q["options"][
            q["answer"]
        ]

        status = (
            "إجابة صحيحة"
            if correct
            else "إجابة غير صحيحة"
        )

        elements.append(
            Paragraph(
                ar(
                    f"{index}. {q['question']}"
                ),
                normal_style,
            )
        )

        elements.append(
            Paragraph(
                ar(
                    f"الإجابة المختارة: {answer_text}"
                ),
                normal_style,
            )
        )

        elements.append(
            Paragraph(
                ar(
                    f"الإجابة الصحيحة: {correct_text}"
                ),
                normal_style,
            )
        )

        elements.append(
            Paragraph(
                ar(status),
                ParagraphStyle(
                    "status",
                    fontName=font_bold,
                    fontSize=10,
                    leading=16,
                    alignment=2,
                    textColor=(
                        colors.green
                        if correct
                        else colors.red
                    ),
                ),
            )
        )

        elements.append(
            Spacer(1, 8)
        )

    elements.append(
        Spacer(1, 15)
    )

    elements.append(
        build_signatures_table()
    )

    doc.build(
        elements,
        onFirstPage=draw_watermark,
        onLaterPages=draw_watermark,
    )

    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# 20. إنشاء ورقة الاختبار PDF
# =========================================================

def generate_exam_paper():
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=35,
        title="ورقة اختبار معامل المتوطنة",
    )

    styles = getSampleStyleSheet()

    font_normal = (
        "Arabic"
        if PDF_FONT_AVAILABLE
        else "Helvetica"
    )

    font_bold = (
        "Arabic-Bold"
        if PDF_FONT_AVAILABLE
        else "Helvetica-Bold"
    )

    normal = ParagraphStyle(
        "exam_normal",
        fontName=font_normal,
        fontSize=11,
        leading=18,
        alignment=2,
    )

    title = ParagraphStyle(
        "exam_title",
        fontName=font_bold,
        fontSize=18,
        leading=24,
        alignment=1,
        textColor=colors.HexColor(
            "#064e3b"
        ),
    )

    elements = []

    elements.extend(
        build_pdf_header()
    )

    elements.append(
        Paragraph(
            ar(
                "ورقة اختبار معامل المتوطنة"
            ),
            title,
        )
    )

    elements.append(
        Spacer(1, 15)
    )

    for index, q in enumerate(
        st.session_state.active_questions,
        start=1
    ):
        elements.append(
            Paragraph(
                ar(
                    f"{index}. {q['question']}"
                ),
                ParagraphStyle(
                    "q",
                    fontName=font_bold,
                    fontSize=12,
                    leading=20,
                    alignment=2,
                ),
            )
        )

        elements.append(
            Spacer(1, 4)
        )

        for option_index, option in enumerate(
            q["options"]
        ):
            letter = chr(
                65 + option_index
            )

            elements.append(
                Paragraph(
                    ar(
                        f"{letter}) {option}"
                    ),
                    normal,
                )
            )

        elements.append(
            Spacer(1, 12)
        )

    doc.build(
        elements,
        onFirstPage=draw_watermark,
        onLaterPages=draw_watermark,
    )

    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# 21. الصفحة الرئيسية
# =========================================================

def show_home():

    st.markdown(
        """
        <div class="main-title">
            🔬 المنصة الرقمية لاختبارات معامل المتوطنة
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="card rtl">
            <h2>مرحباً بكم</h2>
            <p>
            هذه المنصة مخصصة لإدارة وتنفيذ الاختبارات
            الخاصة بالعاملين في معامل المتوطنة،
            مع نظام تسجيل واعتماد إلكتروني وحفظ النتائج.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    config = get_exam_config()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">حالة الاختبار</div>
                <div class="metric-value">
                    {"مفتوح" if config["open"] else "مغلق"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">عدد الأسئلة</div>
                <div class="metric-value">
                    {config["num_questions"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">مدة الاختبار</div>
                <div class="metric-value">
                    {config["duration"]} دقيقة
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<br>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "👨‍💼 دخول الإدارة",
            key="home_admin"
        ):
            st.session_state.page = "admin_login"
            st.rerun()

    with col2:
        if st.button(
            "👨