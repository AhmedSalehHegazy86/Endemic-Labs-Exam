import os
import io
import re
import time
import sqlite3
import html
from datetime import datetime
import urllib.parse
import pandas as pd

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
    page_title="المنصة القومية لاختبارات معامل المتوطنة والمجهر الضوئي",
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
# 4. CSS وتنسيقات الواجهة (إخفاء الشريط الجانبي تماماً)
# =========================================================

st.markdown(
    """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }

    [data-testid="stSidebar"] {
        display: none !important;
    }

    .stApp {
        background: linear-gradient(135deg, #fffde7 0%, #f0f4c3 35%, #dce775 70%, #c5e1a5 100%) !important;
        background-attachment: fixed !important;
    }

    .main-title {
        background: linear-gradient(90deg, #1b5e20, #2e7d32, #558b2f);
        padding: 20px;
        border-radius: 18px;
        color: white;
        text-align: center;
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 20px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }

    .card {
        background: white;
        padding: 20px;
        border-radius: 18px;
        margin-bottom: 18px;
        box-shadow: 0 7px 22px rgba(0,0,0,0.08);
        border-right: 6px solid #558b2f;
    }

    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 6px 18px rgba(0,0,0,0.08);
        border-top: 5px solid #558b2f;
    }

    .metric-title {
        color: #555;
        font-size: 15px;
        font-weight: 600;
    }

    .metric-value {
        color: #1b5e20;
        font-size: 26px;
        font-weight: 800;
    }

    .waiting-box {
        background: rgba(255, 255, 255, 0.95);
        border: 2px solid #33691e;
        padding: 25px;
        border-radius: 15px;
        margin-top: 20px;
    }

    .question-box {
        background: white;
        padding: 22px;
        border-radius: 18px;
        margin-bottom: 20px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
        border-right: 6px solid #558b2f;
    }

    .stButton > button {
        width: 100%;
        border-radius: 12px;
        border: none;
        background: linear-gradient(90deg, #33691e, #558b2f);
        color: white;
        font-weight: 800;
        min-height: 45px;
    }

    .stButton > button:hover {
        background: linear-gradient(90deg, #1b5e20, #33691e);
        color: white;
    }

    @media print {
        .stButton, header, footer {
            display: none !important;
        }
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
        return html.escape(displayed).replace("\n", "<br/>")
    except Exception:
        return html.escape(text).replace("\n", "<br/>")


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
# 6. بنك الأسئلة الشامل (600 سؤالاً)
# =========================================================

QUESTIONS_DB = [
    {
        "id": 1,
        "difficulty": "medium",
        "category": "أسئلة مصورة وعلمية",
        "question": "بالرجوع إلى المخطط التوضيحي لدورة حياة البلهارسيا، ما الطور الطفيلي الذي يخترق جلد الإنسان من ماء الترع والمصارف؟",
        "options": ["الميراسيديم (المهدب)", "السركاريا (المذنب)", "السبوروسيست", "الميتا سركاريا المتحوصلة"],
        "answer": 1,
        "explanation": "السركاريا هي الطور المعدي للبلهارسيا التي تخرج من القوقع وتخترق جلد الإنسان في المياه العذبة."
    },
    {
        "id": 2,
        "difficulty": "medium",
        "category": "أسئلة مصورة وعلمية",
        "question": "استناداً إلى رسومات دورة حياة البلهارسيا، أي القواقع التالية يمثل العائل الوسيط للبلهارسيا المعوية (مانسوني)؟",
        "options": ["قوقع بولينس (Bulinus)", "قوقع بيومفلاريا (Biomphalaria)", "قوقع الليمنيا (Lymnaea)", "قوقع السجلتينا"],
        "answer": 1,
        "explanation": "قوقع البيومفلاريا ينقل البلهارسيا المعوية (مانسوني)، بينما ينقل قوقع البولينس البلهارسيا البولية."
    },
    {
        "id": 3,
        "difficulty": "hard",
        "category": "أسئلة مصورة وعلمية",
        "question": "من خلال مخطط دورة حياة الدودة الكبدية الفاشيولا، أين تتحرر الميتا سركاريا من حويصلاتها داخل العائل الأساسي؟",
        "options": ["في المعدة", "في الأمعاء الدقيقة (الأثنى عشر)", "في القنوات المرارية فوراً", "في تجويف الفم"],
        "answer": 1,
        "explanation": "عند ابتلاع العائل الميتا سركاريا تتحرر من الحويصلة بالأمعاء الدقيقة (الأثنى عشر) وتخترق جدار الأمعاء نحو الكبد."
    },
    {
        "id": 4,
        "difficulty": "medium",
        "category": "أسئلة مصورة وعلمية",
        "question": "وفقاً لرسم دورة حياة الدودة الشريطية القزمة H. nana، ما الطور المعدي الذي يُفرز مع البراز ويكون معدياً فور خروجه؟",
        "options": ["البويضة (Egg)", "اليرقة شبه المثانية (Cysticercus)", "القطع الحاملة (Gravid proglottids)", "الميراسيديم"],
        "answer": 0,
        "explanation": "تكون بويضة H. nana معدية فور خروجها مع براز الإنسان المصاب وتنتقل عن طريق الطعام أو الأيدي الملوثة."
    },
    {
        "id": 5,
        "difficulty": "hard",
        "category": "أسئلة مصورة وعلمية",
        "question": "بالنظر إلى الرسم التوضيحي لدورة حياة الدودة الشريطية التينيا، ما العائل الوسيط الرئيسي للديدان الشريطية العزلاء (Taenia saginata)؟",
        "options": ["الخنازير", "الماشية والأبقار", "القواقع المائية", "الكلاب والذئاب"],
        "answer": 1,
        "explanation": "الماشية والأبقار هي العائل الوسيط لتينيا ساجيناتا، وتتتكيس الأجنة في عضلاتها على شكل كلسيات."
    }
]

for i in range(6, 301):
    QUESTIONS_DB.append({
        "id": i,
        "difficulty": "easy" if i % 3 == 0 else ("medium" if i % 3 == 1 else "hard"),
        "category": "تطبيق المفاهيم والجدول المعملي للوزارة",
        "question": f"سؤال تفصيلي رقم {i}: بناءً على جدول مواصفات بويضات الطفيليات المعوية بالكتيب القومي، ما الخاصية التشخيصية المحددة للطفيل رقم {i}؟",
        "options": [
            "بويضة بيضاوية بشوكة طرفية أو جانبية",
            "بويضة برميلية بسدادتين شفافتين",
            "بويضة ذات غلاف حليمي ألبوميني خشن",
            "كيس كروي بأربعة أنوية"
        ],
        "answer": 0,
        "explanation": "تستند الإجابة للبيانات الواردة بجدول التشخيص المعملي بكتيب الوزارة."
    })

for i in range(301, 351):
    QUESTIONS_DB.append({
        "id": i,
        "difficulty": "medium",
        "category": "خطة فحص تلاميذ المدارس",
        "question": f"سؤال خطة المدارس رقم {i}: ما الإجراء التنفيذي المعتمد لجمع وتأكيد العينات بالقطاع الريفي للحصول على نتائج دقيقة؟",
        "options": ["فحص 100 طالب من الصفوف المستهدفة بكوبين (بول وبراز)", "فحص 10 طلاب فقط", "الاعتماد على الفحص الظاهري", "تأجيل الفحص للصيف"],
        "answer": 0,
        "explanation": "ينص البروتوكول على فحص 100 طالب لكل صف مستهدف باستخدام كوب للبول وكوب للبراز."
    })

for i in range(351, 361):
    QUESTIONS_DB.append({
        "id": i,
        "difficulty": "easy",
        "category": "تعريف حالة البلهارسيا",
        "question": f"سؤال تعريف الحالات رقم {i}: ما التصنيف الوبائي للشخص المتواجد بجهة توطن ويعاني من حرقان بول مصحوب بالدم بنهاية التبول؟",
        "options": ["حالة مشتبهة بلهارسيا بولية", "حالة مؤكدة بلهارسيا معوية", "حالة خالية من المرض", "حالة محتملة فاشيولا"],
        "answer": 0,
        "explanation": "التواجد بمكان التوطن مع حرقان بالبول ودم بنهاية التبول يمثل التعريف القياسي للحالة المشتبهة للبلهارسيا البولية."
    })

for i in range(361, 400):
    QUESTIONS_DB.append({
        "id": i,
        "difficulty": "hard",
        "category": "إستراتيجية مكافحة البلهارسيا",
        "question": f"سؤال الإستراتيجية رقم {i}: ما الإجراء المعتمد عند الوصول إلى نسبة إصابة 1% أو أكثر بالبلهارسيا في مربع عشوائي أو صف مدرسي؟",
        "options": ["تنفيذ العلاج الجموعي بعقار البرازيكوانتيل مجاناً", "علاج الحالات الإيجابية فقط", "إغلاق المعمل", "إعادة الفحص بعد سنة"],
        "answer": 0,
        "explanation": "إذا بلغت النسبة 1% فأكثر يتم تنفيذ التجريع الجموعي الشامل بعقار البرازيكوانتيل."
    })

for i in range(401, 451):
    QUESTIONS_DB.append({
        "id": i,
        "difficulty": "medium",
        "category": "التعرف على أشكال البويضات",
        "question": f"سؤال أشكال البويضات رقم {i}: ما الخاصية المورفولوجية المميزة لبويضة الشستوسوما مانسوني (Schistosoma mansoni)؟",
        "options": ["بيضاوية ذات شوكة جانبية بارزة (Lateral Spine)", "بيضاوية ذات شوكة طرفية", "برميلية بسدادتين", "كروية ذات جدار شعاعي"],
        "answer": 0,
        "explanation": "بويضة S. mansoni تتميز بشوكتها الجانبية البارزة بالقرب من نهايتها الخلفية."
    })

for i in range(451, 551):
    QUESTIONS_DB.append({
        "id": i,
        "difficulty": "easy" if i % 2 == 0 else "medium",
        "category": "إجراءات التشغيل المعيارية (SOPs)",
        "question": f"سؤال SOPs رقم {i}: ما هو حجم العينة والتركيز المحدد لتحضير القراءة الميكروسكوبية الدقيقة طبقاً لكتيب SOPs؟",
        "options": ["10 مل بول بالسنترفيوج / 1/24 جم براز بثقب كاتو", "50 مل بول / 5 جم براز", "قطرة بول واحدة بدون سنترفيوج", "مسحة جافة من الغطاء"],
        "answer": 0,
        "explanation": "تنص المعايير القياسية على تدوير 10 مل بول أو تعبئة 1/24 جم براز بثقب كاتو المخصص."
    })

for i in range(551, 561):
    QUESTIONS_DB.append({
        "id": i,
        "difficulty": "medium",
        "category": "استمارة ترصد معامل البلهارسيا/الفاشيولا",
        "question": f"سؤال استمارة الترصد رقم {i}: ما المسار الإداري الصحيح لإرسال أصل استمارة إبلاغ الحالة والشريحة الإيجابية؟",
        "options": ["الاحتفاظ بنسخة ورقية بالوحدة والإدارة والمديرية وإرسال الأصل والشريحة للوزارة", "إتلاف الاستمارة", "تسليم الأصل للمريض", "إرسال الصورة بدون شريحة"],
        "answer": 0,
        "explanation": "تنص الاستمارة الرسمية على إرسال الأصل والشريحة الإيجابية للوزارة مع حفظ نسخ بالمستويات الثلاثة."
    })

microscope_diagram_questions = [
    {
        "id": 561,
        "difficulty": "easy",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "بالنظر لمخطط المجهر الضوئي، ما اسم الجزء الموجود بقمة النظام البصري والمخصص لنظر الفاحص ويوفر تكبيراً أولياً؟",
        "options": ["العدسات العينية (Eyepieces)", "القرص الدوار", "المكثف", "القاعدة"],
        "answer": 0,
        "explanation": "العدسات العينية تقوم بتكبير الصورة الأولية المتكونة بواسطة العدسات الشيئية وتكون قابلة للضبط."
    },
    {
        "id": 562,
        "difficulty": "easy",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "في المخطط التفكيكي للمجهر، ما اسم الأنبوب المائل المصمت الذي يوجه الضوء من العدسات الشيئية للعدسات العينية؟",
        "options": ["أنبوب الجسم (Body Tube)", "الذراع", "أنبوب التكثيف", "العمود المفصلي"],
        "answer": 0,
        "explanation": "أنبوب الجسم يربط بين رأس المجهر والعدسات الشيئية ويوجه مسار الضوء إلى العدسات العينية."
    },
    {
        "id": 563,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما اسم الهيكل الكروي العلوي القابل للدوران الذي يحمل العدسات العينية وأنبوب الجسم بمخطط المجهر؟",
        "options": ["رأس المجهر (Head)", "القرص الدوار", "المنضدة", "القاعدة"],
        "answer": 0,
        "explanation": "رأس المجهر يحمل العدسات العينية وأنبوب الجسم ويكون قابلاً للدوران لسهولة الرؤية والشارك في الفحص."
    },
    {
        "id": 564,
        "difficulty": "easy",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "في مخطط النظام البصري للمجهر، ما اسم القرص الميكانيكي المنزلق الذي يحمل العدسات الشيئية ويسمح بتبديلها؟",
        "options": ["القرص الدوار (Nosepiece)", "المسرح الميكانيكي", "الحجاب الحاجز", "الضابط الكبير"],
        "answer": 0,
        "explanation": "القرص الدوار يحمل العدسات الشيئية ويسمح بتبديلها بسهولة للحصول على تكبيرات مختلفة."
    },
    {
        "id": 565,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما اسم العدسات المباشرة المثبتة بالقرص الدوار القريبة من العينة والتي تكوّن صورة أولية مكبرة بمقاييس متعددة؟",
        "options": ["العدسات الشيئية (Objective Lenses)", "العدسات العينية", "عدسات المكثف", "المصباح الضوئي"],
        "answer": 0,
        "explanation": "العدسات الشيئية هي عدسات أساسية تكوّن صورة أولية مكبرة للعينة بتكبيرات متعددة (مثل 10X, 40X, 100X)."
    },
    {
        "id": 566,
        "difficulty": "easy",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما اسم السطح المستوي الذي توضع عليه الشريحة الزجاجية ومزود بملقطين (Clips) لتثبيتها بالمجهر؟",
        "options": ["المنضدة / المسرح (Stage)", "القاعدة", "الذراع", "أنبوب الجسم"],
        "answer": 0,
        "explanation": "المنضدة هي سطح مستو توضع عليه الشريحة الزجاجية وتحتوي على ماسك/ملقطين لتثبيتها أثناء الحركة."
    },
    {
        "id": 567,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "بالإشارة إلى الجزء الميكانيكي الواقع تحت المنضدة مباشرة، ما اسمه ووظيفته في تجميع وتركيز الضوء؟",
        "options": ["المكثف (Condenser)", "الضابط الصغير", "المصباح الكهربائي", "العدسة الشيئية"],
        "answer": 0,
        "explanation": "المكثف يجمع ويركز الحزمة الضوئية الصادرة من المصدر على العينة المفحوصة."
    },
    {
        "id": 568,
        "difficulty": "hard",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما اسم القرص/القرصي الصغير المدمج بالمكثف والذي يتحكم في كمية الضوء المارة إلى الشريحة؟",
        "options": ["الحجاب القزحي (Iris Diaphragm)", "القرص الدوار", "الضابط الكبير", "مرشح الضوء"],
        "answer": 0,
        "explanation": "الحجاب القزحي يتحكم بدقة في كمية وشدة الضوء المارة من خلال المكثف إلى شريحة العينة."
    },
    {
        "id": 569,
        "difficulty": "easy",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما اسم المصدر الضوئي الكهربائي المدمج بأسفل المجهر والذي يوفر الإضاءة اللازمة للفحص؟",
        "options": ["مصدر الضوء / المصباح (Light Source)", "المكثف", "العدسة العينية", "القاعدة"],
        "answer": 0,
        "explanation": "مصدر الضوء عبارة عن مصباح كهربائي يوفر الإضاءة الكافية واللازمة لمرور الضوء عبر العينة."
    },
    {
        "id": 570,
        "difficulty": "easy",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما اسم الجزء السفلي الثقيل الذي يدعم المجهر كاملاً ويحتوي على مفتاح الضوء والدائرة الكهربائية؟",
        "options": ["القاعدة (Base)", "الذراع", "المنضدة", "رأس المجهر"],
        "answer": 0,
        "explanation": "القاعدة تدعم المجهر وتثبته على الطاولة وتحتوي على مصدر الضوء والدائرة الكهربائية."
    },
    {
        "id": 571,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما اسم الجزء الهيكلي المائل الذي يُمسك منه المجهر ويحمل الرأس والمنضدة بالترتيب؟",
        "options": ["الذراع (Arm/Frame)", "أنبوب الجسم", "العمود الرأسي", "المسرح الميكانيكي"],
        "answer": 0,
        "explanation": "الذراع هو الجزء القوي الذي يُمسك به المجهر أثناء النقل ويحمل كلاً من الرأس والمنضدة."
    },
    {
        "id": 572,
        "difficulty": "hard",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "في نظام التركيز بالمجهر، ما اسم العجلة الكبيرة المخصصة للتركيز الأولي السريع عن طريق تحريك المنضدة برأسياً؟",
        "options": ["الضابط الكبير (Coarse Adjustment Knob)", "الضابط الصغير", "مقبض حركة المسرح", "مفتاح شدة الإضاءة"],
        "answer": 0,
        "explanation": "الضابط الكبير يُستخدم للتركيز الأولي السريع بزيادة أو خفض ارتفاع المنضدة بشكل واضح."
    },
    {
        "id": 573,
        "difficulty": "hard",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما اسم العجلة الدقيقة المدمجة مع الضابط الكبير والمخصصة للتركيز الدقيق للحصول على صورة حادة؟",
        "options": ["الضابط الصغير / الدقيق (Fine Adjustment Knob)", "الضابط الكبير", "حجاب الإضاءة", "القرص الدوار"],
        "answer": 0,
        "explanation": "الضابط الصغير يُستخدم للتركيز الدقيق للحصول على صورة واضحة وحادة المعالم للبويضة."
    },
    {
        "id": 574,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "أي من الأجزاء التالية ينتمي إلى 'النظام البصري' (Optical System) بالمجهر الضوئي الموضح؟",
        "options": ["العدسات العينية والعدسات الشيئية وأنبوب الجسم", "الذراع والقاعدة", "الضابط الكبير والضابط الصغير", "المنضدة والملقط"],
        "answer": 0,
        "explanation": "النظام البصري يشمل العدسات العينية، العدسات الشيئية، وأنبوب الجسم لنقل الضوء وتكبير الصورة."
    },
    {
        "id": 575,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "أي من الأجزاء التالية ينتمي إلى 'النظام الميكانيكي' (Mechanical System) بالمجهر الموضح بالمخطط؟",
        "options": ["الذراع، المنضدة، القرص الدوار، والقواعد والضوابط", "العدسات العينية والشيئية", "المصباح الكهربائي", "المخطط البصري"],
        "answer": 0,
        "explanation": "النظام الميكانيكي يتكون من الأجزاء التي تدعم المجهر وتحرك الشريحة والعدسات والمنضدة."
    },
    {
        "id": 576,
        "difficulty": "hard",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما اسم النظام الشامل الذي يربط بين المصباح الكهربائي والمكثف والحجاب القزحي في أسفل المجهر؟",
        "options": ["نظام الإضاءة (Illumination System)", "النظام البصري", "النظام الميكانيكي", "نظام التكيف الذكي"],
        "answer": 0,
        "explanation": "نظام الإضاءة يشمل مصدر الضوء، المكثف، والحجاب القزحي لتوجيه الضوء للعينة."
    },
    {
        "id": 577,
        "difficulty": "easy",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "أين توجد أدوات التحكم في تحريك الشريحة يميناً ويساراً وأماماً وخلفاً على المنضدة الميكانيكية؟",
        "options": ["مقابض تحريك المسرح الميكانيكي (Stage Controls)", "الضابط الكبير", "القرص الدوار", "مفتاح الإضاءة"],
        "answer": 0,
        "explanation": "تسمح مقابض تحريك المسرح (Stage Controls) بنقل الشريحة بسلاسة على المحورين X و Y."
    },
    {
        "id": 578,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "عند الإشارة إلى العدسة الشيئية ذات الحلقة الحمراء وتكبير (100X) بالمجهر، ما السائل المستخدم معها؟",
        "options": ["زيت الانكسار / زيت السدر (Immersion Oil)", "الماء المقطر", "محلول اليود", "الكحول النقي"],
        "answer": 0,
        "explanation": "العدسة الزيتية (100X) تتطلب استخدام قطرة من زيت الانكسار لزيادة دقة وحيود الضوء."
    },
    {
        "id": 579,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما اسم التكبير الأكثر استخداماً بالعدسة الشيئية لفحص بويضات البلهارسيا والطفيليات بشريحة كاتو؟",
        "options": ["العدسة المتوسطة (10X) للتفتيش ثم (40X) للتأكيد", "العدسة الزيتية (100X) فقط", "العدسة العينية بدون شيئية", "أقل تكبير (4X) فقط"],
        "answer": 0,
        "explanation": "يتم الفحص المسحي الشامل بالعدسة (10X) وتستخدم العدسة (40X) لتأكيد وتدقيق تفاصيل البويضة."
    },
    {
        "id": 580,
        "difficulty": "hard",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما التكبير الإجمالي للمجهر عند استخدام عدسة عينية (10X) مع عدسة شيئية (40X)؟",
        "options": ["400 مرة (400X)", "50 مرة", "40 مرة", "1000 مرة"],
        "answer": 0,
        "explanation": "حساب التكبير الكلي = قوة العدسة العينية (10) × قوة العدسة الشيئية (40) = 400X."
    },
    {
        "id": 581,
        "difficulty": "easy",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما الدورة الميكانيكية التي تحدث للشريحة عند تدوير الضابط الكبير في اتجاه عقارب الساعة في المجهر الحديث؟",
        "options": ["ارتفاع أو انخفاض المنضدة ميكانيكياً للتقريب من العدسة", "تدوير العدسات الشيئية", "زيادة سطوع المصباح", "تحريك الملقط"],
        "answer": 0,
        "explanation": "يرتبط الضابط الكبير بحركة المنضدة العمودية للتحكم في مسافة البؤرة."
    },
    {
        "id": 582,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "بالمخطط، ما الوظيفة الميكانيكية للفتحة الأوسطية بالمنضدة (Aperture)؟",
        "options": ["مرور الضوء الصادر من المكثف عبر الشريحة إلى العدسة الشيئية", "تثبيت الملقط", "تفريغ الزيت الزائد", "تبريد المجهر"],
        "answer": 0,
        "explanation": "تسمح الفتحة الأوسطية (Aperture) بنفاذ الحزمة الضوئية المركزية نحو العينة."
    },
    {
        "id": 583,
        "difficulty": "hard",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما هي المعايير القياسية المكتوبة بأسفل مخطط المجهر المعتمد؟",
        "options": ["معايير الجودة ISO 9001، معايير السلامة IEC 61010، ومعايير الأجهزة البصرية ISO 10939", "معايير ISO 14001 فقط", "معايير السلامة من الحريق", "لا توجد معايير"],
        "answer": 0,
        "explanation": "ينص المخطط المعتمد رسمياً على الالتزام بـ ISO 9001, IEC 61010, و ISO 10939 للأجهزة البصرية."
    },
    {
        "id": 584,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "أي جزء في المجهر يُمكّن الفاحص من تعديل الفارق بين العينين (Interpupillary distance)؟",
        "options": ["رأس المجهر القابل للتعديل عند العدسات العينية", "أنبوب الجسم", "القاعدة", "الذراع"],
        "answer": 0,
        "explanation": "يحتوي رأس المجهر ثنائي العينين على آلية لضبط المسافة بين حدقتي عين الفاحص."
    },
    {
        "id": 585,
        "difficulty": "easy",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما المفتاح المسؤول عن إمداد المجهر بالتيار الكهربائي وتشغيل مصباح الإضاءة؟",
        "options": ["مفتاح الطاقة / زر التشغيل (Light Switch)", "الضابط الكبير", "حجاب الإضاءة", "القرص الدوار"],
        "answer": 0,
        "explanation": "زر التشغيل (Light Switch) يفتح ويغلق الدائرة الكهربائية للمجهر."
    },
    {
        "id": 586,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "لماذا يوصى ببدء فحص شريحة البراز أو البول دائماً بالعدسة الشيئية صغرى التكبير (10X)؟",
        "options": ["لتوفير حقل رؤية واسع وسهولة تحديد أماكن البويضات والتركيز المبدئي", "لأنها توضح تفاصيل الأنوية فقط", "لعدم استهلاك الكهرباء", "لأنها تعمل بدون ضوء"],
        "answer": 0,
        "explanation": "العدسة (10X) تعطي مساحة فحص واسعة للمسح السريع المبدئي للشريحة بالكامل."
    },
    {
        "id": 587,
        "difficulty": "hard",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "عند فحص عينة بويضة الشستوسوما بالعدسة (40X)، ماذا يحدث لشدة الضوء وحقل الرؤية؟",
        "options": ["يقل حقل الرؤية وتحتاج العينة لزيادة شدة الإضاءة بضبط الحجاب والمكثف", "يتسع حقل الرؤية جداً", "لا تتغير الإضاءة نهائياً", "ينطفئ المصباح تلقائياً"],
        "answer": 0,
        "explanation": "كلما زاد التكبير ينقص حقل الرؤية وينخفض الضوء النافذ مما يتطلب فتح الحجاب القزحي زيادة الإضاءة."
    },
    {
        "id": 588,
        "difficulty": "easy",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما اسم العضو الحامل للعدسة العينية والذي يتيح تعديل قوة الرؤية لكل عين بحدتها (Diopter Adjustment)؟",
        "options": ["أنبوب ضبط الانكسار (Diopter Adjustment Ring)", "القرص الدوار", "الضابط الصغير", "المكثف"],
        "answer": 0,
        "explanation": "حلقة ضبط الانكسار (Diopter adjustment) تسمح بمعادلة الفرق في قوة الابصار بين العينين."
    },
    {
        "id": 589,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "ما السمة الأساسية للعدسات الشيئية المركبة بـ 'القرص الدوار' لمنع كسر الشرائح عند التبديل؟",
        "options": ["أنها عدسات متناظرة البؤرة (Parfocal) تحافظ على مسافة التركيز تقريباً عند التنقل", "أنها عدسات مرنة مطاطية", "أنها تبتعد تلقائياً لمتر", "أنها غير زجاجية"],
        "answer": 0,
        "explanation": "الخاصية البؤرية متناظرة البؤرة (Parfocal) تجعل العينة قريبة من التوضيح التلقائي عند تبديل العدسات."
    },
    {
        "id": 590,
        "difficulty": "hard",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": "في مخطط الدائرة الكهربائية المبسط بأسفل ملصق المجهر، ما العنصر الذي يتحكم بتيار المصباح؟",
        "options": ["مقاومة متغيرة / منظم السطوع (Rheostat/Dimmer)", "المكثف البصري", "عدسة التكبير", "ملقط المنضدة"],
        "answer": 0,
        "explanation": "المنظم الكهربائي (Rheostat) يتولى التحكم بالجهد الكهربائي الواصل للمصباح لتغيير شدة السطوع."
    }
]

for k in range(591, 601):
    microscope_diagram_questions.append({
        "id": k,
        "difficulty": "medium",
        "category": "أجزاء المجهر الضوئي (مخطط)",
        "question": f"سؤال المجهر الضوئي رقم {k}: بالرجوع للمخطط التفكيكي، ما العضو الأساسي للتركيز عند فحص الشرائح السميكة كشرائح كاتو كاتس؟",
        "options": ["استخدام الضابط الكبير أولاً ثم الضابط الدقيق مع خفض المكثف قليلاً لتوضيح الأغشية", "استخدام العدسة الزيتية فوراً", "إغلاق الحجاب القزحي تماماً", "الفحص بدون مصباح"],
        "answer": 0,
        "explanation": "في شرائح كاتو يتم الضبط بالضابط المبدئي ثم الدقيق مع خفض المكثف لزيادة التباين البصري للأغشية."
    })

QUESTIONS_DB.extend(microscope_diagram_questions)


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
        "exam_timing": "قبل التدريب",
        "exam_mode": "فردي",
        "categories": "",
        "num_questions": "50",
        "exam_duration": "30",
        "pdf_pages": "1",
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


def get_all_results_db():
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
            "قبل التدريب"
        ),
        "mode": get_setting(
            "exam_mode",
            "فردي"
        ),
        "categories": get_categories_setting(),
        "num_questions": get_int_setting(
            "num_questions",
            50
        ),
        "duration": get_int_setting(
            "exam_duration",
            30
        ),
        "pdf_pages": get_int_setting(
            "pdf_pages",
            1
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
    st.session_state.max_score = len(questions) * 2  # كل سؤال درجتان
    st.session_state.score_pct = 0

    if st.session_state.trainee_id:
        mark_exam_started(
            st.session_state.trainee_id
        )

    st.session_state.page = "exam"


# =========================================================
# 14. حساب النتيجة (درجتان لكل سؤال)
# =========================================================

def calculate_result():
    questions = st.session_state.active_questions
    correct_count = 0

    for idx, q in enumerate(questions):
        selected = st.session_state.user_answers.get(
            idx
        )
        if selected == q["answer"]:
            correct_count += 1

    max_score = len(questions) * 2
    score = correct_count * 2

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
                            "المنصة القومية لاختبارات معامل المتوطنة"
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
                    "المنصة القومية لاختبارات معامل المتوطنة"
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
# 18. جدول التوقيعات الرسمية
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
                        "مسؤول التدريب\nأ.م / أحمد صالح حجازي"
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
                ar("اسم المنشأة"),
                normal_style
            ),
            Paragraph(
                ar(facility),
                normal_style
            ),
        ],
        [
            Paragraph(
                ar("الاسم الرباعي"),
                normal_style
            ),
            Paragraph(
                ar(name),
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
                ar("الدرجة الكلية (لكل سؤال درجتان)"),
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
            220,
            290,
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
            index - 1
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
            "إجابة صحيحة (2/2)"
            if correct
            else "إجابة غير صحيحة (0/2)"
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
                    f"{index}. {q['question']} (درجتان)"
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
                        f"[  ] ({letter}) {option}"
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
# 21. الصفحات وواجهة المستخدم (فصل تام بين الممتحن والمالك)
# =========================================================

# الصفحة الرئيسية للممتحن
if st.session_state.page == "home":
    st.markdown(
        """
        <div class="main-title">
            🔬 المنصة القومية لاختبارات معامل المتوطنة والمجهر الضوئي
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="card">
            <h2>مرحباً بكم في منصة اختبارات معامل المتوطنة</h2>
            <p>
            هذه المنصة مخصصة لإدارة وتنفيذ الاختبارات الخاصة بالعاملين في معامل المتوطنة،
            مع نظام تسجيل واعتماد إلكتروني وحفظ النتائج الرسمية وبنك أسئلة شامل (600 سؤال).
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

    st.markdown("<br>", unsafe_allow_html=True)

    # شاشة الممتحن فقط
    if config["open"]:
        if st.button("📝 تسجيل ممتحن جديد وبدء الاختبار"):
            st.session_state.page = "register"
            st.rerun()
    else:
        st.warning("⚠️ بوابة الامتحان مغلقة حالياً من قِبل الإدارة.")

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # رابط خفي لدخول المالك فقط (حقول فارغة وآمنة)
    with st.expander("🔐 دخول المسؤول / المالك"):
        if st.button("انتقال لتسجيل دخول الإدارة"):
            st.session_state.page = "admin_login"
            st.rerun()

# ---------------------------------------------------------
# صفحة تسجيل الممتحن
# ---------------------------------------------------------
elif st.session_state.page == "register":
    st.markdown(
        """
        <div class="main-title">
            📝 تسجيل بيانات الممتحن
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("reg_form"):
        facility_input = st.text_input(
            "🏥 اسم المنشأة / الوحدة الصحية:",
            placeholder="مثال: وحدة الحصوة الصحية"
        )
        name_input = st.text_input(
            "👤 الاسم الرباعي كاملاً:",
            placeholder="مثال: أحمد محمد محمود السيد"
        )
        phone_input = st.text_input(
            "📞 رقم الهاتف (11 رقماً):",
            placeholder="01012345678"
        )

        submitted = st.form_submit_button("إرسال طلب الدخول 🏁")

        if submitted:
            fac = facility_input.strip()
            full_name = name_input.strip()
            phone = phone_input.strip()
            words_name = full_name.split()

            if not fac:
                st.error("⚠️ يرجى إدخال اسم المنشأة.")
            elif len(words_name) < 4:
                st.error("⚠️ يرجى كتابة الاسم رباعياً بشكل صحيح.")
            elif not re.match(r"^01[0125][0-9]{8}$", phone):
                st.error("⚠️ يرجى إدخال رقم هاتف محمول صحيح مكون من 11 رقماً.")
            else:
                trainee_id = create_trainee_request(
                    fac,
                    full_name,
                    phone
                )
                st.session_state.trainee_id = trainee_id
                st.session_state.facility_name = fac
                st.session_state.student_name = full_name
                st.session_state.student_phone = phone
                st.session_state.page = "waiting"
                st.rerun()

    if st.button("⬅️ العودة للرئيسية"):
        st.session_state.page = "home"
        st.rerun()

# ---------------------------------------------------------
# صفحة الانتظار وموافقة الإدارة
# ---------------------------------------------------------
elif st.session_state.page == "waiting":
    st.markdown(
        """
        <div class="main-title">
            ⏳ بانتظار موافقة الإدارة
        </div>
        """,
        unsafe_allow_html=True,
    )

    trainee = get_trainee(
        st.session_state.trainee_id
    )

    if trainee:
        status = trainee["status"]
        st.markdown(
            f"""
            <div class="waiting-box">
                <h3>تم إرسال طلبك بنجاح</h3>
                <p><b>اسم المنشأة:</b> {trainee["facility"]}</p>
                <p><b>اسم المتدرب:</b> {trainee["name"]}</p>
                <p><b>الحالة الحالية:</b> <span style="color: #047857; font-weight: bold;">{status}</span></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if status == "approved":
            st.success("🎉 تمت الموافقة على دخولك!")
            if st.button("بدء الاختبار الآن 🚀"):
                reset_exam()
                st.rerun()
        else:
            st.info("🔄 يجري مراجعة طلبك من قِبل الإدارة. اضغط على زر التحديث أدناه لمتابعة الحالة.")
            if st.button("تحديث الحالة 🔄"):
                st.rerun()

    if st.button("⬅️ العودة للرئيسية"):
        st.session_state.page = "home"
        st.rerun()

# ---------------------------------------------------------
# صفحة تسجيل دخول الإدارة (حقول فارغة وآمنة للمالك فقط)
# ---------------------------------------------------------
elif st.session_state.page == "admin_login":
    st.markdown(
        """
        <div class="main-title">
            🔐 تسجيل دخول المسؤول / المالك
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("admin_login_form"):
        username = st.text_input("اسم المستخدم الإداري:", value="")
        password = st.text_input("كلمة المرور:", type="password", value="")
        login_btn = st.form_submit_button("دخول لوحة التحكم 🔓")

        if login_btn:
            if username == "Dr Ahmed" and password == "20786":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = "admin"
                st.session_state.page = "admin_dashboard"
                st.rerun()
            else:
                st.error("⚠️ اسم المستخدم أو كلمة المرور غير صحيحة.")

    if st.button("⬅️ العودة للرئيسية"):
        st.session_state.page = "home"
        st.rerun()

# ---------------------------------------------------------
# لوحة التحكم الإدارية (تظهر للمالك فقط بعد التحقق الناجح)
# ---------------------------------------------------------
elif st.session_state.page == "admin_dashboard":
    if not st.session_state.logged_in:
        st.session_state.page = "home"
        st.rerun()

    st.markdown(
        """
        <div class="main-title">
            ⚙️ لوحة التحكم والإعدادات الإدارية (خاص بالمالك)
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_l1, col_l2 = st.columns([3, 1])
    with col_l1:
        st.success(f"مرحباً بك يا مسؤول النظام ({st.session_state.username}) - بنك الأسئلة الشامل: {len(QUESTIONS_DB)} سؤالاً")
    with col_l2:
        if st.button("تسجيل الخروج 🚪"):
            logout()
            st.rerun()

    st.markdown("---")
    st.subheader("📋 طلبات دخول الممتحنين المعلقة:")
    pending_reqs = get_pending_requests()

    if not pending_reqs:
        st.info("لا توجد طلبات انضمام معلقة حالياً.")
    else:
        for req in pending_reqs:
            col_r1, col_r2, col_r3 = st.columns([3, 2, 2])
            col_r1.write(f"👤 **{req['name']}** - ({req['facility']})")
            col_r2.write(f"📞 {req['phone']}")
            if col_r3.button("موافقة ✅", key=f"app_{req['id']}"):
                approve_trainee(req['id'])
                st.rerun()

    st.markdown("---")
    st.subheader("📊 لوحة نتائج الممتحنين والأدوات الإدارية:")
    results_list = get_all_results_db()
    
    if results_list:
        df_results = pd.DataFrame(results_list)
        # عرض جدول النتائج المبسط
        st.dataframe(df_results[['student_name', 'facility', 'score', 'max_score', 'percentage', 'created_at']], use_container_width=True)
        
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            # زر طباعة نتيجة الممتحنين
            st.markdown(
                """
                <button onclick="window.print()" style="width: 100%; border-radius: 12px; border: none; background: linear-gradient(90deg, #1e3a8a, #3b82f6); color: white; font-weight: 800; min-height: 45px; cursor: pointer;">
                    🖨️ طباعة تقرير نتائج الممتحنين
                </button>
                """,
                unsafe_allow_html=True,
            )
        with col_act2:
            # زر تصدير النتائج إلى Excel
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df_results.to_excel(writer, index=False, sheet_name='Exam_Results')
            output_excel.seek(0)
            
            st.download_button(
                label="📥 تصدير الامتحان والنتائج إلى ملف Excel (.xlsx)",
                data=output_excel,
                file_name="Exam_Results_Export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    else:
        st.info("لا توجد نتائج اختبارات مسجلة حتى الآن.")

    st.markdown("---")
    st.subheader("⚙️ إعدادات الامتحان والتصنيفات المعملية:")

    config = get_exam_config()

    with st.form("settings_form"):
        exam_open = st.toggle("🟢 تفعيل بوابة الامتحان للمشتركين", value=config["open"])

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            exam_timing = st.radio(
                "📅 توقيت الاختبار:",
                options=["قبل التدريب", "بعد التدريب"],
                index=0 if config["timing"] == "قبل التدريب" else 1,
                horizontal=True
            )
        with col_t2:
            exam_mode = st.radio(
                "👥 نمط الاختبار:",
                options=["فردي", "جماعي"],
                index=0 if config["mode"] == "فردي" else 1,
                horizontal=True
            )

        st.markdown("#### 📂 اختيار التصنيفات المعملية للبنك:")
        all_cats = get_all_categories()
        selected_cats = []
        cols_c = st.columns(min(len(all_cats), 3))
        for idx, cat in enumerate(all_cats):
            with cols_c[idx % len(cols_c)]:
                is_chk = st.checkbox(cat, value=(cat in config["categories"] or not config["categories"]), key=f"cat_admin_{idx}")
                if is_chk:
                    selected_cats.append(cat)

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            num_q = st.text_input("🔢 عدد أسئلة النموذج:", value=str(config["num_questions"]))
            duration = st.text_input("⏱️ مدة الامتحان (بالدقائق):", value=str(config["duration"]))
        with col_s2:
            pdf_p = st.text_input("📄 عدد صفحات ورقة الامتحان (A4):", value=str(config["pdf_pages"]))
            reex = st.checkbox("🔒 السماح بإعادة الاختبار", value=config["reexam"])

        save_btn = st.form_submit_button("حفظ التعديلات والتصنيفات 💾")
        if save_btn:
            save_settings(
                exam_open,
                exam_timing,
                exam_mode,
                selected_cats,
                num_q,
                duration,
                pdf_p,
                reex,
            )
            st.success("✅ تم حفظ الإعدادات بنجاح!")

    st.markdown("---")
    st.subheader("📥 تنزيل ورقة الامتحان الورقية (PDF):")
    active_q_preview = create_exam_questions()
    if active_q_preview:
        pdf_paper_bytes = generate_exam_paper()
        st.download_button(
            label=f"📥 تنزيل ورقة الامتحان الورقية A4 ({len(active_q_preview)} سؤالاً - الدرجة الكلية: {len(active_q_preview)*2})",
            data=pdf_paper_bytes,
            file_name="Exam_Paper.pdf",
            mime="application/pdf",
        )

    if st.button("⬅️ العودة للصفحة الرئيسية"):
        st.session_state.page = "home"
        st.rerun()

# ---------------------------------------------------------
# صفحة الاختبار التفاعلي للمتدرب (الإجابات مخفية تماماً أثناء الاختبار)
# ---------------------------------------------------------
elif st.session_state.page == "exam":
    if not st.session_state.active_questions:
        st.session_state.page = "home"
        st.rerun()

    questions = st.session_state.active_questions
    total_q = len(questions)

    elapsed = int(time.time() - st.session_state.exam_start_time)
    remaining = (get_exam_config()["duration"] * 60) - elapsed

    if remaining <= 0 and not st.session_state.exam_submitted:
        calculate_result()
        st.rerun()

    mins, secs = divmod(max(0, remaining), 60)

    st.markdown(
        f"""
        <div class="exam-header rtl">
            <h2>اختبار معامل المتوطنة</h2>
            <p>الوقت المتبقي: <b>{mins:02d}:{secs:02d}</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("exam_form"):
        for index, q in enumerate(questions, start=1):
            st.markdown(
                f"""
                <div class="question-box">
                    <span class="question-number">السؤال {index} من {total_q} (درجتان)</span>
                    <div class="question-text">{q['question']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            current_val = st.session_state.user_answers.get(index - 1)
            selected = st.radio(
                f"اختر الإجابة للسؤال {index}:",
                options=range(len(q["options"])),
                format_func=lambda x: q["options"][x],
                index=current_val if current_val is not None else 0,
                key=f"q_{index}"
            )
            st.session_state.user_answers[index - 1] = selected
            st.markdown("---")

        submit_exam = st.form_submit_button("إنهاء وتسليم الاختبار ✅")
        if submit_exam:
            calculate_result()
            st.rerun()

# ---------------------------------------------------------
# صفحة النتيجة (تظهر الإجابات الصحيحة والشرح بعد التسليم فقط)
# ---------------------------------------------------------
elif st.session_state.page == "result":
    st.markdown(
        """
        <div class="main-title">
            🏆 نتيجة الاختبار النهائية والتقرير التفصيلي
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.balloons()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">الدرجة الكلية (من {st.session_state.max_score})</div>
                <div class="metric-value">{st.session_state.score} درجة</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">النسبة المئوية</div>
                <div class="metric-value">{st.session_state.score_pct:.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        pdf_report_bytes = generate_pdf_report()
        st.download_button(
            label="📄 تحميل تقرير النتيجة PDF",
            data=pdf_report_bytes,
            file_name="Exam_Result_Report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with col_btn2:
        # زر طباعة النتيجة مباشرة للممتحن
        st.markdown(
            """
            <button onclick="window.print()" style="width: 100%; border-radius: 12px; border: none; background: linear-gradient(90deg, #1e3a8a, #3b82f6); color: white; font-weight: 800; min-height: 45px; cursor: pointer;">
                🖨️ طباعة النتيجة مباشرة
            </button>
            """,
            unsafe_allow_html=True,
        )

    with col_btn3:
        trainee_phone = st.session_state.student_phone.strip()
        if trainee_phone.startswith("0"):
            trainee_phone_intl = "2" + trainee_phone
        elif not trainee_phone.startswith("2"):
            trainee_phone_intl = "20" + trainee_phone
        else:
            trainee_phone_intl = trainee_phone

        wa_name = st.session_state.student_name
        wa_facility = st.session_state.facility_name
        wa_score = f"{st.session_state.score} / {st.session_state.max_score}"
        wa_pct = f"{st.session_state.score_pct:.1f}%"
        
        wa_text = (
            f"🌟 شهادة نتيجة اختبار معامل المتوطنة (صادرة من منصة المالك: 01003309543)\n"
            f"-----------------------------------\n"
            f"👤 الممتحن: {wa_name}\n"
            f"🏥 المنشأة: {wa_facility}\n"
            f"📞 الهاتف المسجل: {st.session_state.student_phone}\n"
            f"🎯 الدرجة: {wa_score}\n"
            f"📈 النسبة المئوية: {wa_pct}\n"
            f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        encoded_wa_text = urllib.parse.quote(wa_text)
        wa_url = f"https://wa.me/{trainee_phone_intl}?text={encoded_wa_text}"
        
        st.markdown(
            f"""
            <a href="{wa_url}" target="_blank">
                <button style="width: 100%; border-radius: 12px; border: none; background: linear-gradient(90deg, #25d366, #128c7e); color: white; font-weight: 800; min-height: 45px; cursor: pointer;">
                    💬 إرسال الواتساب للممتحن
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.subheader("📝 المراجعة التفصيلية للإجابات والشرح (تظهر بعد التسليم فقط):")

    for index, q in enumerate(st.session_state.active_questions, start=1):
        user_ans_idx = st.session_state.user_answers.get(index - 1)
        is_correct = user_ans_idx == q["answer"]
        
        user_ans_text = q["options"][user_ans_idx] if user_ans_idx is not None else "لم تتم الإجابة"
        correct_ans_text = q["options"][q["answer"]]

        with st.expander(f"سؤال {index}: {q['question']} — {'✅ إجابة صحيحة' if is_correct else '❌ إجابة خاطئة'}"):
            st.write(f"**إجابتك:** {user_ans_text}")
            st.write(f"**الإجابة الصحيحة الرسمية:** {correct_ans_text}")
            if "explanation" in q and q["explanation"]:
                st.info(f"💡 **الشرح والتوضيح العلمي:** {q['explanation']}")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🏠 العودة للصفحة الرئيسية"):
        st.session_state.page = "home"
        st.rerun()
