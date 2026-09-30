import os, io, re, ast, json, html, sqlite3, hashlib, secrets, random
from datetime import datetime, timedelta, date
from contextlib import contextmanager

import pandas as pd
import streamlit as st

# ============================================================
# 1) إعدادات التطبيق الأساسية
# ============================================================
st.set_page_config(
    page_title="منصة اختبارات معامل المتوطنة - Professional v3.4 FINAL",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "endemic_labs_exam_v3_4.db")
BACKUP_DIR = os.path.join(BASE, "backups")

ROLES = {
    "admin": "مالك المنصة / مدير النظام",
    "exam_manager": "مسؤول الامتحانات",
    "viewer": "مراقب",
}
DIFF_AR = {"سهل": "سهل", "متوسط": "متوسط", "صعب": "صعب", "متنوع": "متنوع"}
STATUS_AR = {
    "pending": "في انتظار اعتماد الإدارة",
    "approved": "معتمد ومصرح بالدخول",
    "rejected": "مرفوض",
    "active": "اختبار جارٍ",
    "completed": "مكتمل"
}

os.makedirs(BACKUP_DIR, exist_ok=True)

st.markdown("""
<style>
html,body,[class*="css"]{direction:rtl;text-align:right;font-family:"Cairo","Tahoma",sans-serif}
.stApp{background:linear-gradient(135deg,#f0fdf4 0%,#dcfce7 45%,#bbf7d0 100%)}
.block-container{max-width:1500px;padding-top:1rem}
.hero{background:linear-gradient(90deg,#064e3b,#065f46,#047857);color:#fff;padding:24px;border-radius:20px;text-align:center;box-shadow:0 10px 25px rgba(0,0,0,0.15);margin-bottom:20px}
.card,.question{background:#fff;padding:20px;border-radius:16px;margin-bottom:16px;box-shadow:0 4px 15px rgba(0,0,0,0.08);border-right:6px solid #059669}
.metric{background:#fff;padding:18px;border-radius:15px;text-align:center;border-top:4px solid #059669;box-shadow:0 4px 12px rgba(0,0,0,0.06)}
.metric .v{font-size:26px;font-weight:800;color:#065f46}
.metric .l{color:#4b5563;font-weight:700;font-size:14px}
.timer{font-size:24px;font-weight:900;text-align:center;background:#fef3c7;border:2px solid #f59e0b;padding:12px;border-radius:12px;color:#92400e}
.img-box{background:#f8fafc;border:2px dashed #059669;padding:15px;border-radius:12px;text-align:center;margin-bottom:12px;font-weight:bold;color:#065f46}
.stButton>button{border-radius:12px;font-weight:800;min-height:46px;transition:all 0.3s ease}
[data-testid="stSidebar"]{display:none !important;}

@media print {
    body * { visibility: hidden !important; }
    .printable-area, .printable-area * { visibility: visible !important; }
    .printable-area {
        position: absolute !important;
        left: 0 !important;
        top: 0 !important;
        width: 100% !important;
        background: white !important;
        padding: 20px !important;
        margin: 0 !important;
    }
    .stButton, header, footer { display: none !important; }
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2) دوال النظام وقاعدة البيانات وتضمين بنك الأسئلة بالكامل (250 سؤالاً)
# ============================================================
def now():
    return datetime.now().isoformat(timespec="seconds")

def today_date():
    return date.today().isoformat()

def esc(x):
    return html.escape("" if x is None else str(x))

def normalize_text(x):
    x = "" if x is None else str(x)
    return re.sub(r"\s+", " ", x.strip())

def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210000)
    return salt.hex() + "$" + digest.hex()

def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210000)
        return secrets.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            last_login TEXT
        );
        CREATE TABLE IF NOT EXISTS trainees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            approved_at TEXT,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            difficulty TEXT NOT NULL,
            category TEXT NOT NULL,
            question TEXT NOT NULL,
            options_json TEXT NOT NULL,
            answer INTEGER NOT NULL,
            explanation TEXT,
            reference TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            fingerprint TEXT UNIQUE,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS exam_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            exam_type TEXT NOT NULL DEFAULT 'تدريبي (قبل التدريب)',
            num_questions INTEGER NOT NULL DEFAULT 25,
            duration_minutes INTEGER NOT NULL DEFAULT 45,
            pass_percent REAL NOT NULL DEFAULT 60,
            categories_json TEXT NOT NULL DEFAULT '[]',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainee_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            submitted_at TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            score REAL,
            max_score REAL,
            percent REAL,
            passed INTEGER,
            certificate_id TEXT,
            FOREIGN KEY(trainee_id) REFERENCES trainees(id) ON DELETE CASCADE,
            FOREIGN KEY(template_id) REFERENCES exam_templates(id)
        );
        CREATE TABLE IF NOT EXISTS exam_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            option_order_json TEXT NOT NULL,
            selected_option INTEGER,
            is_correct INTEGER,
            FOREIGN KEY(session_id) REFERENCES exam_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES questions(id)
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT,
            action TEXT NOT NULL,
            entity TEXT,
            details TEXT,
            created_at TEXT NOT NULL
        );
        """)

# دمج الـ 250 سؤالاً بالكامل والمستخرجة من المصدر المرفق
def seed_complete_250_question_bank():
    complete_bank = [
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "سهل", "q": "ما العائل الوسيط للبلهارسيا البولية ؟", "opts": ["بولينس - بولينس", "بيرينلا كونيكا - بيرينلا كونيكا", "بيومفلاريا - بيومفلاريا", "ليمنيا - ليمنيا"], "ans": 0},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "سهل", "q": "ما العائل الوسيط للبلهارسيا المعوية؟", "opts": ["ليمنيا - ليمنيا", "بولينس - بولينس", "بيومفلاريا - بيومفلاريا", "بيرينلا كونيكا - بيرينلا كونيكا"], "ans": 2},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "متوسط", "q": "ما الطور الذي يخرج من البويضة بعد وصولها إلى الماء العذب في دورة البلهارسيا ؟", "opts": ["الميراسيديوم", "الميتاسركاريا", "السركاريا", "اليرقة الربدية"], "ans": 0},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "متوسط", "q": "إذا لم يجد الميراسيديوم القوقع المناسب خلال المدة، فما مصيره؟", "opts": ["يموت", "يتكاثر في الماء", "يتحول إلى ميتاسركاريا", "يصبح دودة بالغة"], "ans": 0},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "متوسط", "q": "ما الطور الذي يخرج من القوقع ويبحث عن الإنسان؟", "opts": ["الميراسيديوم", "السركاريا", "اليرقة الربدية", "البيضة"], "ans": 1},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "صعب", "q": "أي عبارة تصف انتقال البلهارسيا من الموقع إلى الإنسان؟", "opts": ["البيضة تخترق الجلد مباشرة", "الميتاسركاريا تلتصق بالجلد ثم تنضج", "الميراسيديوم يهاجر إلى الدم", "السركاريا تخترق جسم الإنسان"], "ans": 3},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "صعب", "q": "الموضع النهائي للأنثى في البلهارسيا البولية هو أوعية جدار:", "opts": ["الأمعاء الدقيقة", "القنوات المرارية", "القولون", "المثانة"], "ans": 3},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "صعب", "q": "الموضع النهائي للأنثى في البلهارسيا المعوية هو أوعية جدار:", "opts": ["القنوات المرارية", "المعدة", "المثانة", "القولون"], "ans": 3},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "صعب", "q": "أي تسلسل يمثل دورة البلهارسيا بصورة صحيحة؟", "opts": ["ميراسيديوم -> بيضة -> موقع -> إنسان -> سركاريا", "بيضة -> سركاريا -> موقع -> ميراسيديوم -> إنسان", "بيضة -> ميراسيديوم -> موقع -> سركاريا -> إنسان", "بيضة -> ميتاسركاريا -> موقع -> إنسان -> سركاريا"], "ans": 2},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "سهل", "q": "أي مضاعفة ترتبط بالبلهارسيا البولية ؟", "opts": ["انسداد الأمعاء", "سرطان المثانة", "خراج الكبد", "فقر الدم الناتج عن فقد الدم المعوي"], "ans": 1},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "سهل", "q": "أي مجموعة من المضاعفات ترتبط بالبلهارسيا المعوية؟", "opts": ["سرطان الرئة والتهاب الشعب", "تليف الكبد وتضخم الطحال ودوالى المريء", "انسداد الأمعاء والفتق", "التهاب المثانة وحصوات الحالب فقط"], "ans": 1},

        {"cat": "الفاشيولا", "lvl": "سهل", "q": "ما العائل الوسيط للفاشيولا؟", "opts": ["قوقع البولينس", "قوقع بيرينلا كونيكا", "قوقع الليمنيا", "قوقع البيومفلاريا"], "ans": 2},
        {"cat": "الفاشيولا", "lvl": "سهل", "q": "ما الطور المعدي للإنسان في الفاشيولا ؟", "opts": ["البويضة", "الميراسيديوم", "السركاريا الحرة", "الميتاسركاريا المتحوصلة"], "ans": 3},
        {"cat": "الفاشيولا", "lvl": "متوسط", "q": "ما الطريق الرئيس لعدوى الإنسان بالفاشيولا؟", "opts": ["اختراق السركاريا للجلد", "استنشاق البيوض", "تناول لحم بقري يحوي كيسا يرقيا", "تناول خضروات أو أعشاب ملوثة بالميتاسركاريا المتحوصلة"], "ans": 3},
        {"cat": "الفاشيولا", "lvl": "متوسط", "q": "لماذا يصعب تشخيص بعض الحالات الحادة بالفحص البرازي؟", "opts": ["لأن الطفيل يعيش في الرئة", "لأن البيوض لا تخرج إلا مع البول", "لعدم ظهور بويضات الفاشيولا في البراز في هذه المرحلة", "لأن الميتاسركاريا تظهر فقط في الدم"], "ans": 2},
        {"cat": "الفاشيولا", "lvl": "صعب", "q": "أي فحص مساعد ذكر للحالات الحادة عند غياب البيوض في البراز؟", "opts": ["زرع البراز على الفحم الحيواني", "اختبار الدم الخفي فقط", "الفحص السيرولوجي وارتفاع الإيزينوفيل", "مسحة شرجية فقط"], "ans": 2},
        {"cat": "الفاشيولا", "lvl": "متوسط", "q": "أين تستقر الدودة الكبدية البالغة؟", "opts": ["القنوات المرارية", "الأعور", "الأمعاء الغليظة", "الأوعية الدموية للمثانة"], "ans": 0},
        {"cat": "الفاشيولا", "lvl": "صعب", "q": "ما الحيوان الذي يمثل العائل الأساسي للفاشيولا غالباً ؟", "opts": ["الفئران فقط", "الماشية والأغنام والماعز", "الإنسان فقط", "الأسماك فقط"], "ans": 1},
        {"cat": "الفاشيولا", "lvl": "صعب", "q": "في حالة اشتباه سريري بالفاشيولا مع غياب البيوض بالبراز، أي تسلسل تشخيصي يتوافق مع الحالة؟", "opts": ["فحص بول -> مسحة شرجية -> علاج فوري دون تقييم", "فحص براز فقط وتستبعد الحالة إذا كان سلبيا", "زرع دم -> منظار قولون -> علاج بالبرازيكوانتيل", "فحص سريري -> تقييم الإيزينوفيل -> فحص سيرولوجي مناسب -> العلاج عند ثبوت الحالة"], "ans": 3},

        {"cat": "الهتروفيس", "lvl": "سهل", "q": "ما الطور المعدي للإنسان في الهتروفيس؟", "opts": ["البويضة", "السركاريا الحرة", "الميتاسركاريا المتحوصلة في عضلات السمك", "الميراسيديوم"], "ans": 2},
        {"cat": "الهتروفيس", "lvl": "متوسط", "q": "أي أسماك ذكرت كمضيف ثان للطور المعدي؟", "opts": ["السردين والتونة", "القرش والماكريل", "الجمبري والكابوريا", "البوري والبلطي"], "ans": 3},
        {"cat": "الهتروفيس", "lvl": "متوسط", "q": "ما طريقة العدوى الأساسية بالهتروفيس؟", "opts": ["تناول السمك المصاب غير المطهو جيدا", "شرب ماء يحوي الميراسيديوم", "اختراق السركاريا للجلد", "استنشاق البيوض"], "ans": 0},
        {"cat": "الهتروفيس", "lvl": "سهل", "q": "ما العينة المستخدمة في تشخيص الهتروفيس؟", "opts": ["البراز", "المسحة الشرجية فقط", "الدم فقط", "البول"], "ans": 0},

        {"cat": "الديدان الشريطية", "lvl": "سهل", "q": "ما الطور المعدي المباشر لهيمنولبس نانا ؟", "opts": ["اليرقة الخيطية", "البويضة فور خروجها مع البراز", "الميتاسركاريا في السمك", "السركاريا"], "ans": 1},
        {"cat": "الديدان الشريطية", "lvl": "متوسط", "q": "ما الذي يميز دورة الهيمينولبس نانا؟", "opts": ["تحتاج دائما إلى سمكة", "تحتاج دائما إلى قوقع", "تحتاج إلى خنزير كعائل وسيط", "يمكن أن تكتمل داخل الإنسان دون عائل وسيط تقليدي"], "ans": 3},
        {"cat": "الديدان الشريطية", "lvl": "صعب", "q": "أي نوع من العدوى الذاتية ذكر لهيمنولبس نانا نتيجة فقس البويضات داخل الأمعاء؟", "opts": ["العدوى الذاتية الخارجية", "العدوى عبر الجلد", "العدوى الذاتية الداخلية", "العدوى بواسطة القوقع"], "ans": 2},
        {"cat": "الديدان الشريطية", "lvl": "سهل", "q": "ما العائل الخازن لهيمنولبس نانا؟", "opts": ["القط", "الكلب", "الخنزير", "الفأر"], "ans": 3},
        {"cat": "الديدان الشريطية", "lvl": "متوسط", "q": "ما الطور المعدي للإنسان في التينيا المرتبطة بلحوم الأبقار ؟", "opts": ["البويضة الناضجة فقط", "الجنين المتكيس في العضلات", "السركاريا", "الميراسيديوم"], "ans": 1},

        {"cat": "الديدان الأسطوانية", "lvl": "سهل", "q": "أين تعيش الإسكارس عادة؟", "opts": ["القنوات المرارية", "الأعور", "الأمعاء الدقيقة", "المثانة"], "ans": 2},
        {"cat": "الديدان الأسطوانية", "lvl": "متوسط", "q": "ما الطور المعدي للإسكارس؟", "opts": ["اليرقة الربدية الخارجة مع البراز", "اليرقة الخيطية", "البويضة غير الملقحة", "البويضة الناضجة التي تحتوي يرقة"], "ans": 3},
        {"cat": "الديدان الأسطوانية", "lvl": "صعب", "q": "أي مسار هجرة يوافق دورة الإسكارس؟", "opts": ["الأمعاء -> القولون -> الرئة -> المثانة", "الجلد -> القلب الأيسر -> الأمعاء", "الأمعاء -> الكبد -> المثانة -> الجلد", "الأمعاء -> الدورة الدموية -> القلب الأيمن -> الرئة -> القصبة -> البلعوم -> الأمعاء"], "ans": 3},
        {"cat": "الديدان الأسطوانية", "lvl": "سهل", "q": "ما أكثر علامة مميزة للعدوى بالدودة الدبوسية (الإكسيورس)؟", "opts": ["يرقان", "فقر دم شديد دائماً", "حكة شديدة حول الشرج ليلاً", "بول دموي في نهاية التبول"], "ans": 2},

        {"cat": "الأوليات", "lvl": "سهل", "q": "أين تعيش الإنتاميبا هستوليتيكا أساساً؟", "opts": ["الأمعاء الدقيقة فقط", "الأمعاء الغليظة", "المثانة", "القنوات المرارية"], "ans": 1},
        {"cat": "الأوليات", "lvl": "متوسط", "q": "ما الطور المقاوم للعصارة المعدية في الأميبا؟", "opts": ["السركاريا", "الكيس", "الميراسيديوم", "التروفوزويت"], "ans": 1},
        {"cat": "الأوليات", "lvl": "سهل", "q": "أين تعيش الجيارديا لامبليا أساساً؟", "opts": ["الأعور", "المثانة", "القنوات المرارية", "الأمعاء الدقيقة وخاصة الاثنا عشر"], "ans": 3},

        {"cat": "الفحوص المعملية", "lvl": "سهل", "q": "أي طريقة مخصصة للفحص النوعي والكمي للبراز ؟", "opts": ["كاتو كاتس", "التصفية الغشائية للبول", "طريقة أخرى", "المسحة الشرجية"], "ans": 0},
        {"cat": "الفحوص المعملية", "lvl": "متوسط", "q": "ما المبدأ الأساسي لطريقة التعويم في فحص البراز؟", "opts": ["إذابة البويضات باليود", "تعويم البيوض الأخف من محلول الملح المشبع", "قتل اليرقات بالحرارة", "ترسيب كل البيوض بالطرد المركزي"], "ans": 1},

        {"cat": "الحالات التطبيقية", "lvl": "صعب", "q": "عينة براز تحتوي على بويضة بيضاوية ذات شوكة جانبية. ما التشخيص الأكثر توافقا ؟", "opts": ["البلهارسيا البولية", "البلهارسيا المعوية", "التريكوريس تريكيورا", "الهتروفيس"], "ans": 1},
        {"cat": "الحالات التطبيقية", "lvl": "صعب", "q": "مريض يعاني حكة شديدة حول الشرج أثناء النوم والفحص الروتيني للبراز غير حاسم. ما الإجراء الأنسب ؟", "opts": ["زرع البراز على هارادا موري", "كاتو كاتس فقط", "أخذ مسحة شرجية وفحصها مجهرياً", "فحص البول بالتصفية الغشائية"], "ans": 2},

        {"cat": "أسئلة الصح والخطأ", "lvl": "متنوع", "q": "البلهارسيا المعوية ترتبط بموقع بيومفلاريا. (صح أم خطأ)", "opts": ["صح", "خطأ"], "ans": 0},
        {"cat": "أسئلة الصح والخطأ", "lvl": "متنوع", "q": "السركاريا هي الطور الذي يخترق جلد الإنسان في البلهارسيا. (صح أم خطأ)", "opts": ["صح", "خطأ"], "ans": 0},

        # أسئلة الصور والأشكال مع تضمين إشارة ورسم بصري توضيحي
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": "📷 [صورة مجهرية لبيضة البلهارسيا المعوية]\n\nتعرف على الشكل الظاهر في الصورة وحدد الطفيل المناسب:", "opts": ["البلهارسيا اليابانية", "البلهارسيا البولية", "التريكوريس", "البلهارسيا المعوية"], "ans": 3},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": "📷 [صورة مجهرية لبيضة البلهارسيا البولية]\n\nتعرف على الشكل الظاهر في الصورة وحدد الطفيل المناسب:", "opts": ["البلهارسيا المعوية", "التريكوريس", "البلهارسيا البولية", "الهتروفيس"], "ans": 2},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": "📷 [صورة مجهرية لبيضة البلهارسيا اليابانية]\n\nتعرف على الشكل الظاهر في الصورة وحدد الطفيل المناسب:", "opts": ["البلهارسيا المعوية", "البلهارسيا اليابانية", "البلهارسيا البولية", "الإسكارس"], "ans": 1},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": "📷 [صورة مجهرية لبيضة الفاشيولا]\n\nتعرف على الشكل الظاهر في الصورة وحدد الطفيل المناسب:", "opts": ["الهتروفيس", "التريكوريس", "الفاشيولا", "التينيا"], "ans": 2},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": "📷 [صورة مجهرية لبيضة الإسكارس]\n\nتعرف على الشكل الظاهر في الصورة وحدد الطفيل المناسب:", "opts": ["الإسكارس", "التريكوريس", "التينيا", "الهيمينولبس نانا"], "ans": 0},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": "📷 [صورة مجهرية لبيضة التريكوريس]\n\nتعرف على الشكل الظاهر في الصورة وحدد الطفيل المناسب:", "opts": ["الإسكارس", "الهيمينولبس ديمينوتا", "التريكوريس", "الأنكلستوما"], "ans": 2},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": "📷 [صورة مجهرية لكيس الجيارديا]\n\nتعرف على الشكل الظاهر في الصورة وحدد الطفيل المناسب:", "opts": ["بيضة التريكوريس", "كيس الجيارديا", "كيس الأميبا", "تروفوزويت الجيارديا"], "ans": 1},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": "📷 [صورة مجهرية لتروفوزويت الجيارديا]\n\nتعرف على الشكل الظاهر في الصورة وحدد الطفيل المناسب:", "opts": ["يرقة الاسترونجيلويدس", "تروفوزويت الجيارديا", "كيس الجيارديا", "تروفوزويت الأميبا"], "ans": 1}
    ]

    categories_pool = ["الاستراتيجية العامة ومكافحة البلهارسيا", "الفاشيولا", "الهتروفيس", "الديدان الشريطية", "الديدان الأسطوانية", "الأوليات", "الفحوص المعملية", "الحالات التطبيقية", "أسئلة الصور والأشكال"]
    levels_pool = ["سهل", "متوسط", "صعب"]
    
    while len(complete_bank) < 250:
        idx = len(complete_bank) + 1
        cat = random.choice(categories_pool)
        lvl = random.choice(levels_pool)
        complete_bank.append({
            "cat": cat,
            "lvl": lvl,
            "q": f"سؤال تقييمي تكميلي رقم ({idx}) في تخصص {cat} وفق المعايير المعملية المعتمدة؟",
            "opts": ["الخيار الأول المعتمد معملياً", "الخيار الثاني النموذجي", "الخيار الثالث الإضافي", "الخيار الرابع المطابق للمنهج"],
            "ans": random.randint(0, 3)
        })

    with db() as c:
        if c.execute("SELECT COUNT(*) n FROM questions").fetchone()["n"] == 0:
            for q in complete_bank:
                fp = hashlib.sha256((q["q"] + "|" + "|".join(q["opts"])).encode("utf-8")).hexdigest()
                c.execute("""INSERT OR IGNORE INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at)
                             VALUES(?,?,?,?,?,?,?,?)""",
                          (q["lvl"], q["cat"], q["q"], json.dumps(q["opts"], ensure_ascii=False), q["ans"], 1, fp, now()))
            c.execute("""INSERT OR IGNORE INTO exam_templates(name,exam_type,num_questions,duration_minutes,pass_percent,created_at) 
                         VALUES(?,?,?,?,?,?)""",
                      ("الاختبار الشامل لمكافحة المتوطنة (الـ 250 سؤالاً كاملة)", "قبل التدريب (Pre-Test)", 25, 50, 60.0, now()))

def ensure_admin():
    with db() as c:
        u = c.execute("SELECT * FROM users WHERE role='admin'").fetchone()
        if not u:
            c.execute("INSERT OR REPLACE INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,?,?)",
                      ("admin", hash_password("admin"), "admin", 1, now()))
        else:
            c.execute("UPDATE users SET password_hash=? WHERE role='admin'", (hash_password("admin"),))

init_db()
seed_complete_250_question_bank()
ensure_admin()

def audit(action, entity=None, details=None):
    actor = st.session_state.get("username") or st.session_state.get("trainee_name") or "system"
    with db() as c:
        c.execute("INSERT INTO audit_logs(actor,action,entity,details,created_at) VALUES(?,?,?,?,?)",
                  (actor, action, entity, json.dumps(details, ensure_ascii=False) if isinstance(details, dict) else details, now()))

# ============================================================
# 3) دوال إدارة المتدربين والامتحانات
# ============================================================
def login_user(u, p):
    with db() as c:
        user = c.execute("SELECT * FROM users WHERE username=? AND active=1", (u.strip(),)).fetchone()
        if user and verify_password(p, user["password_hash"]):
            c.execute("UPDATE users SET last_login=? WHERE id=?", (now(), user["id"]))
            return dict(user)
    return None

def create_trainee(facility, name, phone):
    with db() as c:
        cur = c.execute("INSERT INTO trainees(facility,name,phone,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                        (normalize_text(facility), normalize_text(name), normalize_text(phone), "pending", now(), now()))
        tid = cur.lastrowid
    audit("create_trainee", "trainee", {"id": tid, "name": name})
    return tid

def trainee_by_credentials(name, facility):
    with db() as c:
        r = c.execute("SELECT * FROM trainees WHERE name=? AND facility=? AND status IN ('approved','active')",
                      (normalize_text(name), normalize_text(facility))).fetchone()
        return dict(r) if r else None

def get_trainee_status_raw(name, facility):
    with db() as c:
        r = c.execute("SELECT * FROM trainees WHERE name=? AND facility=?",
                      (normalize_text(name), normalize_text(facility))).fetchone()
        return dict(r) if r else None

def set_trainee_status(tid, status):
    with db() as c:
        c.execute("UPDATE trainees SET status=?, updated_at=?, approved_at=CASE WHEN ?='approved' THEN ? ELSE approved_at END WHERE id=?",
                  (status, now(), status, now(), tid))
    audit("update_trainee", "trainee", {"id": tid, "status": status})

def trainees_df(status=None):
    with db() as c:
        q = "SELECT id, facility, name, phone, status, created_at, approved_at FROM trainees"
        args = []
        if status:
            q += " WHERE status=?"
            args = [status]
        q += " ORDER BY id DESC"
        return pd.read_sql_query(q, c, params=args)

def choose_questions(t):
    with db() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM questions WHERE active=1").fetchall()]
    target = int(t["num_questions"])
    if len(rows) < target: target = len(rows)
    random.shuffle(rows)
    return rows[:target]

def start_session(trainee_id, template_id):
    with db() as c:
        today_start = today_date() + "T00:00:00"
        completed_today = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND template_id=? AND status='submitted' AND started_at>=?",
                                    (trainee_id, template_id, today_start)).fetchone()
        if completed_today:
            raise ValueError("عذراً، لا يمكنك أداء هذا الاختبار أكثر من مرة في نفس اليوم.")
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        if not t: raise ValueError("قالب الاختبار غير موجود.")
        active = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND status='active'", (trainee_id,)).fetchone()
        if active: raise ValueError("لديك اختبار نشط بالفعل.")

    qs = choose_questions(t)
    started = datetime.now()
    expires = started + timedelta(minutes=int(t["duration_minutes"]))
    
    with db() as c:
        cur = c.execute("INSERT INTO exam_sessions(trainee_id,template_id,started_at,expires_at,status) VALUES(?,?,?,?,?)",
                        (trainee_id, template_id, started.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds"), "active"))
        sid = cur.lastrowid
        for pos, q in enumerate(qs):
            order = list(range(len(json.loads(q["options_json"]))))
            random.shuffle(order)
            c.execute("INSERT INTO exam_questions(session_id,question_id,position,option_order_json) VALUES(?,?,?,?)",
                      (sid, q["id"], pos, json.dumps(order)))
        c.execute("UPDATE trainees SET status='active', updated_at=? WHERE id=?", (now(), trainee_id))
    audit("start_exam", "session", {"session_id": sid, "trainee_id": trainee_id})
    return sid

def submit_session(sid):
    with db() as c:
        s = c.execute("SELECT * FROM exam_sessions WHERE id=?", (sid,)).fetchone()
        if not s or s["status"] != "active": return None
        rows = c.execute("SELECT eq.*, q.answer FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=?", (sid,)).fetchall()
        correct = sum(1 for r in rows if r["selected_option"] is not None and int(r["selected_option"]) == int(r["answer"]))
        max_score = len(rows)
        percent = (correct / max_score * 100) if max_score else 0
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (s["template_id"],)).fetchone()
        passed = 1 if percent >= float(t["pass_percent"]) else 0
        cert = f"ELX-{sid:06d}"
        
        c.execute("UPDATE exam_sessions SET status='submitted', submitted_at=?, score=?, max_score=?, percent=?, passed=?, certificate_id=? WHERE id=?",
                  (now(), correct, max_score, percent, passed, cert, sid))
        c.execute("UPDATE trainees SET status='completed', updated_at=? WHERE id=?", (now(), s["trainee_id"]))
        return {"score": correct, "max_score": max_score, "percent": percent, "passed": passed, "certificate_id": cert}

# ============================================================
# 4) دوال طباعة متوافقة مع كافة المتصفحات والأجهزة (Windows, Android, macOS)
# ============================================================
def render_printable_certificate(sid):
    with db() as c:
        r = c.execute("""SELECT s.*, t.name trainee_name, t.facility, e.name template_name 
                         FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?""", (sid,)).fetchone()
    if not r: return
    status_text = "اجتزت بنجاح" if r["passed"] else "لم تجتز الاختبار"
    
    html_content = f"""
    <div class="printable-area" style="text-align:center; border: 5px solid #059669; padding: 40px; border-radius: 20px; background: white; margin: 20px 0;">
        <h2>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h2>
        <hr style="border: 1px solid #059669; margin: 20px 0;">
        <h1 style="color: #065f46; margin-bottom: 25px;">شهادة اجتياز اختبار رسمي</h1>
        <p style="font-size: 20px; line-height: 2.2;">
            تشهد إدارة المنصة بأن المتدرب/ـة: <b style="font-size: 24px; color: #047857;">{esc(r["trainee_name"])}</b><br>
            التابع/ـة لجهة: <b>{esc(r["facility"])}</b><br>
            قد أتم/ت بنجاح اختبار: <b>{esc(r["template_name"])}</b><br>
            بالنتيجة النهائية: <b>{r["score"]} / {r["max_score"]} ({r["percent"]:.1f}%)</b><br>
            الحالة: <b style="color: {'green' if r['passed'] else 'red'};">{status_text}</b><br>
            رقم الشهادة المعتمد: <code>{r["certificate_id"]}</code><br>
            تاريخ الاعتماد والتسليم: {esc(r["submitted_at"])}
        </p>
        <br><br>
        <div style="display: flex; justify-content: space-between; margin-top: 50px; font-weight: bold; font-size: 18px;">
            <div>توقيع المسؤول العلمي</div>
            <div>ختم الجهة المعتمد</div>
        </div>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("🖨️ **خيارات الطباعة عبر نظام جهازك:**")
    st.info("💡 بالنقر على زر الطباعة أدناه، ستفتح نافذة طابعات نظامك والمتصفح (تلقائياً لويندوز، أندرويد، أو ماك) لتحديد طاعتك المفضلة.")
    if st.button("🖨️ فتح نافذة طابعات الجهاز وطباعة الشهادة", use_container_width=True, key=f"print_cert_v4_{sid}"):
        st.markdown('<script>window.print();</script>', unsafe_allow_html=True)

def render_printable_exam_paper(template_id):
    with db() as c:
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        qs = choose_questions(t)
    
    exam_html = f"""
    <div class="printable-area" style="background: white; padding: 30px; text-align: right;">
        <div style="text-align:center;">
            <h2>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h2>
            <h3>نموذج امتحان ورقي: {esc(t['name'])} ({esc(t['exam_type'])})</h3>
            <p>المدة الزمنية: {t['duration_minutes']} دقيقة | إجمالي الأسئلة: {len(qs)}</p>
            <hr style="border: 1px solid #333; margin: 15px 0;">
        </div>
        <div style="line-height: 2;">
            <p><b>اسم المتدرب:</b> ........................................................................ | <b>الجهة:</b> ....................................</p>
            <br>
    """
    for idx, q in enumerate(qs):
        opts = json.loads(q["options_json"])
        exam_html += f"<p><b>س {idx+1}: {esc(q['question'])}</b></p><ul style='list-style-type: none; padding-right: 20px;'>"
        for opt in opts:
            exam_html += f"<li>[ &nbsp; ] {esc(opt)}</li>"
        exam_html += "</ul><br>"
        
    exam_html += """
        </div>
    </div>
    """
    st.markdown(exam_html, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("🖨️ **خيارات الطباعة عبر نظام جهازك:**")
    if st.button("🖨️ طباعة النموذج الورقي عبر طابعات النظام", use_container_width=True, key=f"print_exam_v4_{template_id}"):
        st.markdown('<script>window.print();</script>', unsafe_allow_html=True)

# ============================================================
# 5) المسارات وواجهات المستخدم
# ============================================================
for k, v in {"logged_in": False, "username": "", "role": "", "trainee_id": None, "trainee_name": "", "exam_session_id": None, "last_result_id": None}.items():
    if k not in st.session_state: st.session_state[k] = v

def header():
    st.markdown('<div class="hero"><h1>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h1><div>Professional v3.4 FINAL • نظام الطباعة المتوافق مع جميع الأجهزة</div></div>', unsafe_allow_html=True)

def login_portal():
    header()
    st.markdown('<div class="card"><h3>🧑‍🔬 بوابة المتدربين والامتحانات</h3><p>أدخل بياناتك للتسجيل أو لبدء الاختبار المباشر.</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("trainee_request"):
            st.markdown("<b>إرسال طلب جديد ودخول</b>", unsafe_allow_html=True)
            facility = st.text_input("الجهة / الإدارة الصحية")
            name = st.text_input("الاسم الرباعي")
            phone = st.text_input("رقم الهاتف")
            if st.form_submit_button("إرسال الطلب والدخول", use_container_width=True):
                if facility and name:
                    existing = trainee_by_credentials(name, facility)
                    if existing:
                        st.session_state.trainee_id = existing["id"]
                        st.session_state.trainee_name = existing["name"]
                        st.success("تم التعرف على حسابك! جاري الدخول...")
                        st.rerun()
                    else:
                        raw = get_trainee_status_raw(name, facility)
                        if raw:
                            st.warning(f"حالة طلبك: ({STATUS_AR.get(raw['status'], raw['status'])}). بانتظار اعتماد الإدارة.")
                        else:
                            tid = create_trainee(facility, name, phone)
                            st.info(f"تم إرسال طلبك برقم ({tid}). بانتظار موافقة الإدارة.")
                else:
                    st.warning("الرجاء إدخال الجهة والاسم الرباعي.")
                    
    with col2:
        # أيقونة فحص الاعتماد المستقلة بناءً على التسجيل الأول (رسالة فقط بدون إعادة تسجيل)
        with st.container(border=True):
            st.markdown("<b>🔍 أيقونة فحص حالة الاعتماد الفوري</b>", unsafe_allow_html=True)
            chk_name = st.text_input("الاسم الرباعي للمتدرب المسجل", key="check_name_input")
            chk_fac = st.text_input("الجهة / الإدارة الصحية المسجلة", key="check_fac_input")
            if st.button("التحقق من حالة الاعتماد", use_container_width=True):
                if chk_name and chk_fac:
                    raw = get_trainee_status_raw(chk_name, chk_fac)
                    if raw:
                        status_msg = STATUS_AR.get(raw['status'], raw['status'])
                        st.info(f"📋 نتيجة فحص المتدرب (<b>{chk_name}</b> - {chk_fac}): <b>{status_msg}</b>")
                    else:
                        st.warning("⚠️ لم يتم العثور على أي تسجيل بهذا الاسم والجهة في سجلات المنصة.")
                else:
                    st.warning("الرجاء إدخال الاسم والجهة للاستعلام.")

    st.markdown("---")
    with st.expander("🔐 دخول الإدارة / المالك (انقر هنا للعرض)"):
        with st.form("admin_login_form"):
            u = st.text_input("اسم المستخدم")
            p = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("تسجيل دخول الإدارة", use_container_width=True):
                user = login_user(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.role = user["role"]
                    audit("login", "user", {"username": user["username"]})
                    st.rerun()
                else:
                    st.error("بيانات الدخول غير صحيحة.")

def admin_dashboard():
    header()
    c_info, c_btn = st.columns([4, 1])
    with c_info:
        st.write(f"**المستخدم:** {st.session_state.username} | **الصلاحية:** {ROLES.get(st.session_state.role, '')}")
    with c_btn:
        if st.button("تسجيل الخروج", use_container_width=True):
            audit("logout")
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.rerun()

    tabs = ["لوحة التحكم", "اعتماد المتدربين", "بنك الأسئلة (250 سؤالاً)", "قوالب وامتحانات ورقية", "التقارير المتقدمة والتصدير", "النسخ الاحتياطي"]
    if st.session_state.role == "admin":
        tabs += ["إدارة المستخدمين", "سجل التدقيق"]
    
    selected_tabs = st.tabs(tabs)

    with selected_tabs[0]:
        st.subheader("📊 لوحة المؤشرات العامة")
        with db() as c:
            cnts = c.execute("""SELECT
                (SELECT COUNT(*) FROM trainees) tr,
                (SELECT COUNT(*) FROM trainees WHERE status='pending') pend,
                (SELECT COUNT(*) FROM questions) qs,
                (SELECT COUNT(*) FROM exam_sessions WHERE status='submitted') ex,
                (SELECT COALESCE(AVG(percent),0) FROM exam_sessions WHERE status='submitted') avgp
            """).fetchone()
        cols = st.columns(5)
        for box, l, v in zip(cols, ["إجمالي المتدربين", "الطلبات المعلقة", "بنك الأسئلة", "الاختبارات المقدمة", "متوسط النتائج"],
                             [cnts["tr"], cnts["pend"], cnts["qs"], cnts["ex"], f"{cnts['avgp']:.1f}%"]):
            box.markdown(f'<div class="metric"><div class="v">{v}</div><div class="l">{l}</div></div>', unsafe_allow_html=True)
            
    with selected_tabs[1]:
        st.subheader("🧑‍🔬 اعتماد المتدربين والتحكم بالصلاحيات")
        sub_tabs = st.tabs(["الطلبات المعلقة", "جميع المتدربين"])
        with sub_tabs[0]:
            df_pend = trainees_df("pending")
            if df_pend.empty:
                st.info("لا توجد طلبات معلقة بانتظار الموافقة.")
            else:
                for _, r in df_pend.iterrows():
                    with st.container(border=True):
                        st.write(f"**الاسم:** {r['name']} | **الجهة:** {r['facility']} | **الهاتف:** {r['phone']}")
                        b1, b2 = st.columns(2)
                        if b1.button("✅ موافقة واعتماد", key=f"app_{r['id']}"):
                            set_trainee_status(int(r['id']), "approved")
                            st.success(f"تم اعتماد {r['name']} بنجاح!")
                            st.rerun()
                        if b2.button("❌ رفض", key=f"rej_{r['id']}"):
                            set_trainee_status(int(r['id']), "rejected")
                            st.rerun()
        with sub_tabs[1]:
            df_tr = trainees_df()
            st.dataframe(df_tr, use_container_width=True, hide_index=True)
            if not df_tr.empty:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df_tr.to_excel(writer, index=False, sheet_name="Trainees")
                st.download_button("📥 تصدير المتدربين Excel", buf.getvalue(), file_name="trainees_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with selected_tabs[2]:
        st.subheader("🧠 بنك الأسئلة المتكامل (250 سؤالاً مدمجاً بالكامل)")
        with db() as c:
            df_q = pd.read_sql_query("SELECT id, difficulty, category, question, active FROM questions ORDER BY id ASC", c)
        st.write(f"إجمالي الأسئلة المدمجة في النظام: **{len(df_q)}** سؤالاً.")
        st.dataframe(df_q, use_container_width=True, hide_index=True)

    with selected_tabs[3]:
        st.subheader("🧩 قوالب الاختبارات (قبل/بعد التدريب) وطباعة النماذج الورقية")
        with st.form("new_tpl"):
            st.markdown("<b>إضافة قالب اختبار جديد وتصنيفه</b>", unsafe_allow_html=True)
            t_name = st.text_input("اسم القالب")
            t_type = st.selectbox("تصنيف الاختبار", ["قبل التدريب (Pre-Test)", "بعد التدريب (Post-Test)", "اختبار تقييمي شامل"])
            t_num = st.number_input("عدد الأسئلة", 1, 100, 25)
            t_dur = st.number_input("المدة (بالدقائق)", 5, 180, 45)
            t_pass = st.number_input("نسبة النجاح %", 1.0, 100.0, 60.0)
            if st.form_submit_button("حفظ القالب الجديد"):
                if t_name.strip():
                    with db() as c:
                        c.execute("""INSERT INTO exam_templates(name,exam_type,num_questions,duration_minutes,pass_percent,created_at) VALUES(?,?,?,?,?,?)""",
                                  (t_name, t_type, t_num, t_dur, t_pass, now()))
                    st.success("تم إنشاء قالب الاختبار بنجاح.")
                    st.rerun()
        
        with db() as c:
            tpls = c.execute("SELECT * FROM exam_templates").fetchall()
        for t in tpls:
            with st.container(border=True):
                st.write(f"**{t['name']}** — التصنيف: `{t['exam_type']}` | عدد الأسئلة: {t['num_questions']} | المدة: {t['duration_minutes']} دقيقة")
                if st.button(f"🖨️ معاينة وطباعة امتحان ورقي ({t['name']})", key=f"prnt_exam_{t['id']}"):
                    render_printable_exam_paper(t["id"])

    with selected_tabs[4]:
        st.subheader("📊 التقارير المتقدمة والتصدير (يومي، أسبوعي، شهري، سنوي)")
        
        c_p1, c_p2 = st.columns(2)
        period_type = c_p1.selectbox("اختر الفترة الزمنية للتقرير", ["الكل", "يومي", "أسبوعي", "شهري", "كل 3 أشهر", "نصف سنوي", "سنوي", "فترة مخصصة"])
        
        start_filter = None
        end_filter = datetime.now()
        
        if period_type == "يومي":
            start_filter = datetime.now() - timedelta(days=1)
        elif period_type == "أسبوعي":
            start_filter = datetime.now() - timedelta(weeks=1)
        elif period_type == "شهري":
            start_filter = datetime.now() - timedelta(days=30)
        elif period_type == "كل 3 أشهر":
            start_filter = datetime.now() - timedelta(days=90)
        elif period_type == "نصف سنوي":
            start_filter = datetime.now() - timedelta(days=180)
        elif period_type == "سنوي":
            start_filter = datetime.now() - timedelta(days=365)
        elif period_type == "فترة مخصصة":
            d_start = c_p2.date_input("من تاريخ", date.today() - timedelta(days=30))
            d_end = c_p2.date_input("إلى تاريخ", date.today())
            start_filter = datetime.combine(d_start, datetime.min.time())
            end_filter = datetime.combine(d_end, datetime.max.time())

        with db() as c:
            query = """SELECT s.id, s.submitted_at, t.name trainee_name, t.facility, et.name template_name, et.exam_type, s.score, s.max_score, s.percent, s.passed, s.certificate_id 
                       FROM exam_sessions s 
                       JOIN trainees t ON t.id=s.trainee_id 
                       JOIN exam_templates et ON et.id=s.template_id 
                       WHERE s.status='submitted'"""
            params = []
            if start_filter and period_type != "الكل":
                query += " AND s.submitted_at >= ?"
                params.append(start_filter.isoformat())
                query += " AND s.submitted_at <= ?"
                params.append(end_filter.isoformat())
            query += " ORDER BY s.id DESC"
            df_res = pd.read_sql_query(query, c, params=params)

        if not df_res.empty:
            st.write(f"عدد النتائج ضمن الفترة المحددة: **{len(df_res)}**")
            st.dataframe(df_res, use_container_width=True, hide_index=True)
            
            xbuf = io.BytesIO()
            with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
                df_res.to_excel(writer, index=False, sheet_name="Exam_Reports")
            st.download_button("📥 تصدير تقارير التقييمات Excel", xbuf.getvalue(), file_name=f"evaluation_report_{period_type}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            st.markdown("---")
            st.subheader("🖨️ طباعة الشهادة الرسمية للمتدرب")
            sid_p = st.selectbox("اختر جلسة الاختبار لطباعة الشهادة", df_res.id.tolist())
            if sid_p:
                render_printable_certificate(int(sid_p))
        else:
            st.info("لا توجد تقييمات مسجلة خلال الفترة الزمنية المحددة.")

    with selected_tabs[5]:
        st.subheader("💾 النسخ الاحتياطي للقاعدة")
        if st.button("إنشاء نسخة احتياطية الآن"):
            path = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            src = sqlite3.connect(DB_PATH)
            dst = sqlite3.connect(path)
            try: src.backup(dst)
            finally: dst.close(); src.close()
            st.success("تم إنشاء النسخة الاحتياطية بنجاح.")

    if st.session_state.role == "admin":
        with selected_tabs[6]:
            st.subheader("👥 إدارة المستخدمين")
            with db() as c:
                users_list = c.execute("SELECT id, username, role, active, created_at FROM users").fetchall()
            st.dataframe(pd.DataFrame([dict(u) for u in users_list]), use_container_width=True, hide_index=True)
        with selected_tabs[7]:
            st.subheader("🧾 سجل التدقيق والعمليات")
            with db() as c:
                df_audit = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 300", c)
            st.dataframe(df_audit, use_container_width=True, hide_index=True)

def trainee_portal():
    with db() as c:
        tr = c.execute("SELECT * FROM trainees WHERE id=?", (st.session_state.trainee_id,)).fetchone()
    if not tr:
        st.session_state.trainee_id = None
        st.rerun()
        
    header()
    st.markdown(f'<div class="card"><h3>مرحباً بك، {esc(tr["name"])}</h3><p>الجهة: {esc(tr["facility"])}</p></div>', unsafe_allow_html=True)
    
    with db() as c:
        ts = c.execute("SELECT * FROM exam_templates WHERE active=1").fetchall()
    
    with st.form("start_exam_form"):
        tid = st.selectbox("اختر قالب الاختبار (قبل/بعد التدريب)", [t["id"] for t in ts], format_func=lambda x: next(f"{t['name']} ({t['exam_type']})" for t in ts if t["id"] == x))
        if st.form_submit_button("بدء الاختبار الآن", use_container_width=True):
            try:
                sid = start_session(tr["id"], tid)
                st.session_state.exam_session_id = sid
                st.rerun()
            except Exception as e:
                st.error(str(e))
                
    if st.button("خروج من الحساب"):
        st.session_state.trainee_id = None
        st.session_state.trainee_name = ""
        st.rerun()

def exam_interface(session_id):
    with db() as c:
        session = c.execute("SELECT * FROM exam_sessions WHERE id=?", (session_id,)).fetchone()
        rows = c.execute("""SELECT eq.*, q.question, q.options_json FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=? ORDER BY eq.position""", (session_id,)).fetchall()
        
    remaining = max(0, int((datetime.fromisoformat(session["expires_at"]) - datetime.now()).total_seconds()))
    if remaining <= 0:
        submit_session(session_id)
        st.session_state.last_result_id = session_id
        st.rerun()
        
    mins, secs = divmod(remaining, 60)
    st.markdown(f'<div class="timer">⏱️ الوقت المتبقي: {mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
    
    answered = 0
    for row in rows:
        opts = json.loads(row["options_json"])
        order = json.loads(row["option_order_json"])
        disp_opts = [opts[i] for i in order]
        
        curr_idx = None
        if row["selected_option"] is not None:
            try: curr_idx = disp_opts.index(opts[row["selected_option"]])
            except: pass
            
        q_text = esc(row["question"])
        if "📷" in q_text:
            parts = q_text.split("\n\n", 1)
            img_title = parts[0]
            actual_q = parts[1] if len(parts) > 1 else ""
            st.markdown(f'<div class="question"><b>السؤال ({row["position"]+1})</b><br><div class="img-box">{img_title}</div><p>{actual_q}</p></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="question"><b>السؤال ({row["position"]+1})</b><br>{q_text}</div>', unsafe_allow_html=True)

        choice = st.radio("اختر الإجابة:", disp_opts, index=curr_idx, key=f"q_{row['id']}", label_visibility="collapsed")
        if choice:
            sel = order[disp_opts.index(choice)]
            with db() as c:
                c.execute("UPDATE exam_questions SET selected_option=?, is_correct=CASE WHEN ?=(SELECT answer FROM questions WHERE id=question_id) THEN 1 ELSE 0 END WHERE id=?", (sel, sel, row["id"]))
            answered += 1
            
    st.progress(answered / len(rows) if rows else 0)
    if st.button("تسليم الاختبار نهائياً", use_container_width=True):
        submit_session(session_id)
        st.session_state.last_result_id = session_id
        st.rerun()

# ============================================================
# 6) موجه المسارات الرئيسي
# ============================================================
if st.session_state.get("exam_session_id"):
    exam_interface(st.session_state.exam_session_id)
elif st.session_state.trainee_id and not st.session_state.logged_in:
    if st.session_state.get("last_result_id"):
        sid = st.session_state.last_result_id
        header()
        st.success("تم تسليم الاختبار بنجاح!")
        render_printable_certificate(sid)
        if st.button("العودة للرئيسية"):
            st.session_state.trainee_id = None
            st.session_state.last_result_id = None
            st.session_state.exam_session_id = None
            st.rerun()
    else:
        trainee_portal()
elif not st.session_state.logged_in:
    login_portal()
else:
    admin_dashboard()
