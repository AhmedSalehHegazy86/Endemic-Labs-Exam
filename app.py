import os, io, re, ast, json, sqlite3, hashlib, secrets, random, time, html, urllib.request, socket
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from contextlib import contextmanager
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import qrcode
from PIL import Image

# ============================================================
# 1) إعدادات التطبيق الأساسية (الإصدار V1.0)
# ============================================================
st.set_page_config(
    page_title="نظام تقييم واختبار العاملين بالأمراض المتوطنة 🪱🔬🐌💊 - System V1.0",
    page_icon="🪱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "endemic_labs_exam_v1_0.db")
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
os.makedirs(os.path.join(BASE, "assets"), exist_ok=True)

DEFAULT_LOGO = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="

# ============================================================
# 2) دوال التوقيت المحدث أونلاين لمصر (Online Cairo Timezone - Live Sync)
# ============================================================
CAIRO_TZ = ZoneInfo("Africa/Cairo")

def get_online_network_time():
    try:
        req = urllib.request.Request("http://worldtimeapi.org/api/timezone/Africa/Cairo", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=1.5) as response:
            data = json.loads(response.read().decode())
            if "datetime" in data:
                return datetime.fromisoformat(data["datetime"])
    except Exception:
        pass
    return datetime.now(CAIRO_TZ)

def now_cairo():
    return get_online_network_time()

def now():
    return now_cairo().isoformat(timespec="seconds")

def today_date():
    return now_cairo().date().isoformat()

# ============================================================
# 3) حقن التنسيقات (CSS) وتدرج الألوان
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: 'Cairo', 'Tahoma', sans-serif !important;
    font-size: 16px;
    color-scheme: light !important;
    -webkit-user-select: none !important;
    -moz-user-select: none !important;
    -ms-user-select: none !important;
    user-select: none !important;
    -webkit-touch-callout: none !important;
}
.stApp {
    background: linear-gradient(135deg, #f0fdf4 0%, #ccfbcc 40%, #a7f3d0 70%, #d1fae5 100%) !important;
    background-attachment: fixed !important;
}
body::after {
    content: "";
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 999998;
    background: radial-gradient(circle, rgba(255,255,255,0) 70%, rgba(5,150,105,0.03) 100%);
}
.stApp, .stApp p, .stApp label, .stApp [data-testid="stMarkdownContainer"] {
    font-size: 16px;
}
.stApp h1 { font-size: 1.8rem !important; }
.stApp h2 { font-size: 1.55rem !important; }
.stApp h3 { font-size: 1.3rem !important; }
.stApp input, .stApp textarea, .stApp select, .stApp button {
    font-size: 15px !important;
}
.block-container {
    max-width: 1150px !important;
    margin: auto !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-top: 3.5rem !important;
    padding-bottom: 7rem !important;
}
.card, .question, [data-testid="stForm"], [data-testid="stVerticalBlock"] > div {
    box-sizing: border-box !important;
}
.card, .question {
    background: #ffffff !important;
    color: #111827 !important;
    padding: 18px 24px;
    border-radius: 10px;
    margin-bottom: 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    border-right: 6px solid #059669 !important;
    width: 100% !important;
}
.metric {
    background: #ffffff !important;
    padding: 16px;
    border-radius: 10px;
    text-align: center;
    border-top: 4px solid #059669 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.metric .v {
    font-size: 24px;
    font-weight: 800;
    color: #065f46 !important;
}
.metric .l {
    color: #4b5563 !important;
    font-weight: 700;
    font-size: 13px;
}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {
    display: none !important;
}
.stButton>button {
    background-color: #059669 !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    font-weight: 800 !important;
    min-height: 42px !important;
    padding: 6px 14px;
    border: none !important;
    width: 100% !important;
    transition: all 0.2s ease;
}
.stButton>button:hover {
    background-color: #047857 !important;
    color: #ffffff !important;
}
input, select, textarea {
    background-color: #ffffff !important;
    color: #111827 !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
}
.ownership-watermark {
    position: fixed;
    bottom: 0;
    right: 0;
    left: 0;
    background: rgba(6, 78, 59, 0.95);
    color: #ffffff;
    text-align: center;
    padding: 8px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
    z-index: 99999;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    border-top: 2px solid #059669;
}
</style>
<script>
document.addEventListener("contextmenu", function(e) {
    e.preventDefault();
});
document.addEventListener("copy", function(e) {
    e.preventDefault();
    alert("⚠ عذراً، نسخ النصوص محظور حفاظاً على سرية الأسئلة والبيانات!");
});
document.addEventListener("keydown", function(e) {
    if (
        e.key === "PrintScreen" ||
        (e.ctrlKey && e.shiftKey && (e.key === "I" || e.key === "i" || e.key === "C" || e.key === "c" || e.key === "J" || e.key === "j")) ||
        (e.ctrlKey && (e.key === "u" || e.key === "U" || e.key === "s" || e.key === "S" || e.key === "p" || e.key === "P")) ||
        e.keyCode === 44
    ) {
        e.preventDefault();
        alert("⚠ تنبيه أمني: محاولة التقاط الشاشة أو نسخ محتوى النظام محظورة تماماً!");
        document.body.style.filter = "blur(15px)";
        setTimeout(function() {
            document.body.style.filter = "none";
        }, 3000);
        return false;
    }
});
window.addEventListener("blur", function() {
    document.body.style.filter = "blur(8px)";
});
window.addEventListener("focus", function() {
    document.body.style.filter = "none";
});
</script>
""", unsafe_allow_html=True)

st.markdown("""
<div class="ownership-watermark">
    جميع الحقوق محفوظة © 2026 | تصميم وتطوير: Dr/Ahmed.S.Hegazy
</div>
""", unsafe_allow_html=True)

# ============================================================
# 4) دوال النظام وقاعدة البيانات وإعادة الترتيب التلقائي للـ ID
# ============================================================
def esc(x):
    return html.escape("" if x is None else str(x))

def clean_question_text(q_text):
    if q_text is None:
        return ""
    cleaned = str(q_text).strip()
    patterns = [
        r"\(\s*نموذج\s*[^)]*\)",
        r"\[\s*نموذج\s*[^]]*\]",
        r"\(\s*النموذج\s*[^)]*\)",
        r"\[\s*النموذج\s*[^]]*\]",
        r"\(\s*مجموعة\s*[^)]*\)",
        r"\[\s*مجموعة\s*[^]]*\]",
        r"\(\s*سؤال\s*[^)]*\)",
        r"\[\s*سؤال\s*[^]]*\]",
        r"\(\s*رقم\s*\d+\s*[^)]*\)",
        r"\[\s*رقم\s*\d+\s*[^]]*\]",
        r"\(\s*رقم[^)]*\)",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*(?:سؤال\s*(?:رقم|#)?\s*)?\d+\s*[\)\].:-]+\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\s+([،,:؛.)])", r"\1", cleaned)
    return cleaned.strip()

def normalize_text(x):
    x = "" if x is None else str(x)
    return re.sub(r"\s+", " ", x.strip()).lower()

_DIGIT_TRANSLATION = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_EGYPT_PHONE_RE = re.compile(r"^01[0125]\d{8}$")
_VALID_NID_GOV_CODES = {"01", "02", "03", "04", "11", "12", "13", "14", "15", "16", "17", "18", "19", "21", "22", "23", "24", "25", "26", "27", "28", "29", "31", "32", "33", "34", "35", "88"}

def normalize_digits(value):
    """Translate Arabic/Persian digits to ASCII and keep digits only."""
    return re.sub(r"\D", "", str(value or "").translate(_DIGIT_TRANSLATION))

def normalize_national_id(value):
    return normalize_digits(value)

def normalize_egyptian_phone(value):
    """Canonicalize common Egyptian mobile formats to 01xxxxxxxxx."""
    raw = str(value or "").translate(_DIGIT_TRANSLATION).strip()
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0020"):
        digits = digits[4:]
    elif digits.startswith("20") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("1"):
        digits = "0" + digits
    return digits

def is_valid_egyptian_mobile(value):
    return bool(_EGYPT_PHONE_RE.fullmatch(normalize_egyptian_phone(value)))

def is_valid_egyptian_national_id(value):
    nid = normalize_national_id(value)
    if len(nid) != 14 or nid[0] not in {"2", "3"}:
        return False
    try:
        century = 1900 if nid[0] == "2" else 2000
        year = century + int(nid[1:3])
        month = int(nid[3:5])
        day = int(nid[5:7])
        datetime(year, month, day)
    except (ValueError, OverflowError):
        return False
    return nid[7:9] in _VALID_NID_GOV_CODES and nid[9:].isdigit()

def trainee_matches_hierarchy(facility_value, hierarchy_row):
    """Match both legacy facility-only values and the full hierarchy string."""
    value = str(facility_value or "").strip()
    h = dict(hierarchy_row)
    if value == str(h.get("facility_name") or "").strip():
        return True
    new_path = " - ".join(str(h.get(k) or "").strip() for k in ("authority", "administration", "facility_name") if str(h.get(k) or "").strip())
    legacy_path = " - ".join(str(h.get(k) or "").strip() for k in ("governorate", "authority", "center", "administration", "facility_name") if str(h.get(k) or "").strip())
    return any(path and value.endswith(path) for path in (new_path, legacy_path))

def hierarchy_filter_for_trainees(scope, trainee_alias="t"):
    """SQL predicate for trainee records stored with a full administrative path."""
    keys = ("scope_governorate", "scope_authority", "scope_center", "scope_administration", "scope_facility")
    if not any(str(scope.get(k) or "").strip() for k in keys):
        return "1=1", []
    scope_sql, args = hierarchy_scope_sql("h", scope)
    pred = (f"EXISTS (SELECT 1 FROM hierarchical_facilities h WHERE ({scope_sql}) AND "
            f"({trainee_alias}.facility=h.facility_name OR "
            f"{trainee_alias}.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR "
            f"{trainee_alias}.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || "
            f"h.center || ' - ' || h.administration || ' - ' || h.facility_name))")
    return pred, args

def reindex_hierarchical_facilities():
    with db() as c:
        rows = c.execute("SELECT governorate, authority, center, administration, facility_name, created_at, hidden FROM hierarchical_facilities ORDER BY id ASC").fetchall()
        c.execute("DELETE FROM hierarchical_facilities")
        c.execute("DELETE FROM sqlite_sequence WHERE name='hierarchical_facilities'")
        for r in rows:
            c.execute("INSERT INTO hierarchical_facilities(governorate, authority, center, administration, facility_name, created_at, hidden) VALUES(?,?,?,?,?,?,?)",
                      (r["governorate"], r["authority"], r["center"], r["administration"], r["facility_name"], r["created_at"], r["hidden"] if r["hidden"] is not None else 0))

def reindex_trainees():
    with db() as c:
        c.execute("PRAGMA foreign_keys=OFF;")
        rows = c.execute("SELECT id, facility, name, phone, national_id, profession, work_start_date, status, assigned_template_id, created_at, approved_at, updated_at, hidden FROM trainees ORDER BY id ASC").fetchall()
        c.execute("DELETE FROM trainees")
        c.execute("DELETE FROM sqlite_sequence WHERE name='trainees'")
        id_mapping = {}
        for new_id, r in enumerate(rows, start=1):
            old_id = r["id"]
            c.execute("INSERT INTO trainees(id, facility, name, phone, national_id, profession, work_start_date, status, assigned_template_id, created_at, approved_at, updated_at, hidden) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (new_id, r["facility"], r["name"], r["phone"], r["national_id"] if r["national_id"] is not None else "", r["profession"] if r["profession"] is not None else "", r["work_start_date"] if r["work_start_date"] is not None else "", r["status"], r["assigned_template_id"], r["created_at"], r["approved_at"], r["updated_at"], r["hidden"] if r["hidden"] is not None else 0))
            id_mapping[old_id] = new_id
        for old_id, new_id in id_mapping.items():
            c.execute("UPDATE exam_sessions SET trainee_id=? WHERE trainee_id=?", (new_id, old_id))
        c.execute("PRAGMA foreign_keys=ON;")

def reindex_questions():
    with db() as c:
        c.execute("PRAGMA foreign_keys=OFF;")
        rows = c.execute("SELECT id, difficulty, category, question, options_json, answer, explanation, reference, active, fingerprint, created_at FROM questions ORDER BY id ASC").fetchall()
        c.execute("DELETE FROM questions")
        c.execute("DELETE FROM sqlite_sequence WHERE name='questions'")
        q_mapping = {}
        for new_id, r in enumerate(rows, start=1):
            old_id = r["id"]
            c.execute("INSERT INTO questions(id, difficulty, category, question, options_json, answer, explanation, reference, active, fingerprint, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (new_id, r["difficulty"], r["category"], r["question"], r["options_json"], r["answer"], r["explanation"], r["reference"], r["active"], r["fingerprint"], r["created_at"]))
            q_mapping[old_id] = new_id
        for old_id, new_id in q_mapping.items():
            c.execute("UPDATE exam_questions SET question_id=? WHERE question_id=?", (new_id, old_id))
        c.execute("PRAGMA foreign_keys=ON;")

def reindex_templates():
    with db() as c:
        c.execute("PRAGMA foreign_keys=OFF;")
        rows = c.execute("SELECT id, name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, start_time, end_time, active, created_at, scope_governorate, scope_authority, scope_center, scope_administration, scope_facility, profession FROM exam_templates ORDER BY id ASC").fetchall()
        c.execute("DELETE FROM exam_templates")
        c.execute("DELETE FROM sqlite_sequence WHERE name='exam_templates'")
        t_mapping = {}
        for new_id, r in enumerate(rows, start=1):
            old_id = r["id"]
            c.execute("INSERT INTO exam_templates(id, name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, start_time, end_time, active, created_at, scope_governorate, scope_authority, scope_center, scope_administration, scope_facility, profession) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (new_id, r["name"], r["exam_type"], r["num_questions"], r["duration_minutes"], r["pass_percent"], r["categories_json"], r["start_time"], r["end_time"], r["active"], r["created_at"], r["scope_governorate"] or "", r["scope_authority"] or "", r["scope_center"] or "", r["scope_administration"] or "", r["scope_facility"] or "", r["profession"] or ""))
            t_mapping[old_id] = new_id
        for old_id, new_id in t_mapping.items():
            c.execute("UPDATE exam_sessions SET template_id=? WHERE template_id=?", (new_id, old_id))
            c.execute("UPDATE trainees SET assigned_template_id=? WHERE assigned_template_id=?", (new_id, old_id))
        c.execute("PRAGMA foreign_keys=ON;")

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

ALL_MENU_MODULES = {
    "📊 لوحة التحكم": "لوحة المؤشرات العامة",
    "🏥 الهيكل الإداري": "الهيكل الإداري والمنشآت ورفع البيانات",
    "👥 إدارة المهن والوظائف": "تقسيم وإدارة المهن والوظائف بالأمراض المتوطنة",
    "⚙ إدارة الأسئلة": "إدارة الأسئلة الفردية وبنك الأسئلة الشامل للأمراض المتوطنة",
    "🧑‍🔬 المتدربين والنماذج": "اعتماد المتدربين والنماذج وطباعة النتائج",
    "📚 قاعدة بيانات المتدربين": "عرض وتعديل وطباعة وتصدير جميع بيانات المتدربين",
    "🧩 مواعيد الاختبارات و طباعة النماذج": "نماذج التدريب والمواعيد",
    "✍ تسجيل نتيجة يدوي": "التسجيل اليدوي للنتائج",
    "🖨 ضبط اعدادات الطباعة و الهوامش": "إعدادات هوامش وترويسات التقارير العامة",
    "🎨 إعدادات الشهادات المخصصة": "صفحة مخصصة لضبط الشهادات بالكامل وطباعتها",
    "📊 التقارير": "التقارير وتحليل الأداء للأمراض المتوطنة",
    "📈 خطط العمل": "خطط العمل التدريبية للأمراض المتوطنة",
    "💾 النسخ الاحتياطي": "النسخ الاحتياطي لقاعدة البيانات",
    "👥 إدارة المستخدمين": "إدارة المستخدمين والصلاحيات",
    "🧾 سجل التدقيق": "سجل التدقيق والأحداث"
}

def init_db():
    with db() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                permissions_json TEXT NOT NULL DEFAULT '[]',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT
            );
            CREATE TABLE IF NOT EXISTS hierarchical_facilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                governorate TEXT NOT NULL,
                authority TEXT NOT NULL,
                center TEXT NOT NULL,
                administration TEXT NOT NULL,
                facility_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                hidden INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS exam_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                exam_type TEXT NOT NULL DEFAULT 'قبل التدريب',
                num_questions INTEGER NOT NULL DEFAULT 999999,
                duration_minutes INTEGER NOT NULL DEFAULT 60,
                pass_percent REAL NOT NULL DEFAULT 60,
                categories_json TEXT NOT NULL DEFAULT '[]',
                start_time TEXT,
                end_time TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                scope_governorate TEXT NOT NULL DEFAULT '',
                scope_authority TEXT NOT NULL DEFAULT '',
                scope_center TEXT NOT NULL DEFAULT '',
                scope_administration TEXT NOT NULL DEFAULT '',
                scope_facility TEXT NOT NULL DEFAULT '',
                profession TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS trainees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                facility TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                national_id TEXT NOT NULL DEFAULT '',
                profession TEXT NOT NULL DEFAULT 'أخصائي الأمراض المتوطنة',
                work_start_date TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                assigned_template_id INTEGER,
                created_at TEXT NOT NULL,
                approved_at TEXT,
                updated_at TEXT NOT NULL,
                hidden INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(assigned_template_id) REFERENCES exam_templates(id) ON DELETE SET NULL
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
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trainee_id INTEGER NOT NULL,
                template_id INTEGER,
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
                FOREIGN KEY(template_id) REFERENCES exam_templates(id) ON DELETE SET NULL
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
                FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS action_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                target_name TEXT NOT NULL,
                weakness_areas TEXT NOT NULL,
                action_steps TEXT NOT NULL,
                time_frame_type TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                created_at TEXT NOT NULL,
                scope_governorate TEXT NOT NULL DEFAULT '',
                scope_authority TEXT NOT NULL DEFAULT '',
                scope_center TEXT NOT NULL DEFAULT '',
                scope_administration TEXT NOT NULL DEFAULT '',
                scope_facility TEXT NOT NULL DEFAULT '',
                template_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS print_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                header_text TEXT NOT NULL,
                margin_top TEXT NOT NULL,
                margin_bottom TEXT NOT NULL,
                margin_right TEXT NOT NULL,
                margin_left TEXT NOT NULL,
                line_spacing REAL NOT NULL DEFAULT 1.25,
                logo_base64 TEXT NOT NULL,
                logo2_base64 TEXT NOT NULL DEFAULT '',
                logo3_base64 TEXT NOT NULL DEFAULT '',
                bg_base64 TEXT NOT NULL DEFAULT '',
                frame_base64 TEXT NOT NULL DEFAULT '',
                default_cert_title TEXT NOT NULL DEFAULT 'شهادة',
                default_cert_notes TEXT NOT NULL DEFAULT 'تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد',
                trainee_prefix TEXT NOT NULL DEFAULT '',
                trainee_title TEXT NOT NULL DEFAULT '',
                trainee_profession TEXT NOT NULL DEFAULT '',
                professions_list_json TEXT NOT NULL DEFAULT '[]',
                cert_box_inset TEXT NOT NULL DEFAULT '13mm'
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT,
                action TEXT NOT NULL,
                entity TEXT,
                details TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS training_minutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER UNIQUE,
                minutes_text TEXT NOT NULL,
                training_items TEXT NOT NULL DEFAULT '',
                training_goals TEXT NOT NULL DEFAULT '',
                training_date TEXT NOT NULL DEFAULT '',
                facility_name TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
        """)

    for col_table, col_name, col_type in [
        ("trainees", "hidden", "INTEGER NOT NULL DEFAULT 0"),
        ("trainees", "profession", "TEXT NOT NULL DEFAULT 'أخصائي الأمراض المتوطنة'"),
        ("trainees", "work_start_date", "TEXT NOT NULL DEFAULT ''"),
        ("trainees", "phone", "TEXT NOT NULL DEFAULT ''"),
        ("trainees", "national_id", "TEXT NOT NULL DEFAULT ''"),
        ("hierarchical_facilities", "hidden", "INTEGER NOT NULL DEFAULT 0"),
        ("users", "permissions_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("exam_templates", "exam_type", "TEXT NOT NULL DEFAULT 'قبل التدريب'"),
        ("exam_templates", "start_time", "TEXT"),
        ("exam_templates", "end_time", "TEXT"),
        ("exam_templates", "scope_governorate", "TEXT NOT NULL DEFAULT ''"),
        ("exam_templates", "scope_authority", "TEXT NOT NULL DEFAULT ''"),
        ("exam_templates", "scope_center", "TEXT NOT NULL DEFAULT ''"),
        ("exam_templates", "scope_administration", "TEXT NOT NULL DEFAULT ''"),
        ("exam_templates", "scope_facility", "TEXT NOT NULL DEFAULT ''"),
        ("exam_templates", "profession", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "scope_governorate", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "scope_authority", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "scope_center", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "scope_administration", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "scope_facility", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "template_id", "INTEGER"),
        ("action_plans", "start_date", "TEXT"),
        ("action_plans", "end_date", "TEXT"),
        ("print_settings", "line_spacing", "REAL NOT NULL DEFAULT 1.25"),
        ("print_settings", "logo2_base64", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "logo3_base64", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "bg_base64", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "frame_base64", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "default_cert_title", "TEXT NOT NULL DEFAULT 'شهادة'"),
        ("print_settings", "default_cert_notes", "TEXT NOT NULL DEFAULT 'تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد'"),
        ("print_settings", "trainee_prefix", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "trainee_title", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "trainee_profession", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "professions_list_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("print_settings", "cert_box_inset", "TEXT NOT NULL DEFAULT '13mm'"),
        ("print_settings", "cert_trainee_extra", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "cert_facility_extra", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "cert_facility_section", "TEXT NOT NULL DEFAULT ''"),
        ("training_minutes", "training_items", "TEXT NOT NULL DEFAULT ''"),
        ("training_minutes", "training_goals", "TEXT NOT NULL DEFAULT ''"),
        ("training_minutes", "training_date", "TEXT NOT NULL DEFAULT ''"),
        ("training_minutes", "facility_name", "TEXT NOT NULL DEFAULT ''")
    ]:
        try:
            with db() as c:
                c.execute(f"ALTER TABLE {col_table} ADD COLUMN {col_name} {col_type}")
        except:
            pass

    # إلغاء مستويات المحافظة والمركز من نطاقات الصلاحيات المحفوظة، مع الإبقاء على المديرية والإدارة والمنشأة.
    with db() as c:
        c.execute("UPDATE exam_templates SET scope_governorate='', scope_center='' WHERE COALESCE(scope_governorate,'')<>'' OR COALESCE(scope_center,'')<>''")
        c.execute("UPDATE action_plans SET scope_governorate='', scope_center='' WHERE COALESCE(scope_governorate,'')<>'' OR COALESCE(scope_center,'')<>''")

    # منع تكرار الممتحن على مستوى قاعدة البيانات: الهاتف هو المعرف الرئيسي، والرقم القومي معرف فريد أيضاً.
    # استخدمنا Triggers بالإضافة إلى فحوصات الواجهة حتى يتم منع التكرار حتى عند التعديل المباشر أو أي مسار آخر.
    with db() as c:
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_trainees_unique_phone_insert
            BEFORE INSERT ON trainees
            WHEN TRIM(COALESCE(NEW.phone,'')) <> '' AND EXISTS (SELECT 1 FROM trainees WHERE TRIM(phone)=TRIM(NEW.phone))
            BEGIN SELECT RAISE(ABORT, 'DUPLICATE_TRAINEE_PHONE'); END;
        """)
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_trainees_unique_phone_update
            BEFORE UPDATE OF phone ON trainees
            WHEN TRIM(COALESCE(NEW.phone,'')) <> '' AND EXISTS (SELECT 1 FROM trainees WHERE TRIM(phone)=TRIM(NEW.phone) AND id<>NEW.id)
            BEGIN SELECT RAISE(ABORT, 'DUPLICATE_TRAINEE_PHONE'); END;
        """)
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_trainees_unique_national_id_insert
            BEFORE INSERT ON trainees
            WHEN TRIM(COALESCE(NEW.national_id,'')) <> '' AND EXISTS (SELECT 1 FROM trainees WHERE TRIM(national_id)=TRIM(NEW.national_id))
            BEGIN SELECT RAISE(ABORT, 'DUPLICATE_TRAINEE_NATIONAL_ID'); END;
        """)
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_trainees_unique_national_id_update
            BEFORE UPDATE OF national_id ON trainees
            WHEN TRIM(COALESCE(NEW.national_id,'')) <> '' AND EXISTS (SELECT 1 FROM trainees WHERE TRIM(national_id)=TRIM(NEW.national_id) AND id<>NEW.id)
            BEGIN SELECT RAISE(ABORT, 'DUPLICATE_TRAINEE_NATIONAL_ID'); END;
        """)

    with db() as c:
        cnt = c.execute("SELECT COUNT(*) FROM print_settings").fetchone()[0]
        if cnt == 0:
            default_header = "جمهورية مصر العربية<br>وزارة الصحة والسكان<br>مديرية الشئون الصحية بالشرقية<br>الإدارة الصحية بأولاد صقر"
            default_professions = [
                "أخصائي الأمراض المتوطنة",
                "طبيب بيطري",
                "أخصائي ميكروبيولوجي",
                "فني صحي متوطنة",
                "فني تمريض",
                "مسؤول وحدة متوطنة",
                "مراقب صحي",
                "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"
            ]
            c.execute("""INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, line_spacing, logo_base64, logo2_base64, logo3_base64, bg_base64, frame_base64, default_cert_title, default_cert_notes, trainee_prefix, trainee_title, trainee_profession, professions_list_json, cert_box_inset) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (default_header, "12mm", "auto", "8mm", "8mm", 1.10, DEFAULT_LOGO, "", "", "", "", "شهادة", "تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد", "", "دكتور", "أخصائي الأمراض المتوطنة", json.dumps(default_professions, ensure_ascii=False), "13mm"))

        cnt_tpl = c.execute("SELECT COUNT(*) FROM exam_templates").fetchone()[0]
        if cnt_tpl == 0:
            default_start = now_cairo().isoformat(timespec="seconds")
            default_end = (now_cairo() + timedelta(days=365)).isoformat(timespec="seconds")
            c.execute("""INSERT INTO exam_templates(name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, start_time, end_time, active, created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                      ("النموذج التقييمي العام للاستجابة والتدريب للأمراض المتوطنة", "قبل التدريب", 999999, 60, 60.0, '[]', default_start, default_end, 1, now()))

init_db()

def get_print_settings():
    with db() as c:
        row = c.execute("SELECT * FROM print_settings ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            res = dict(row)
            try:
                res["professions_list"] = json.loads(res.get("professions_list_json", "[]"))
            except:
                res["professions_list"] = ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"]
            if "line_spacing" not in res or res["line_spacing"] is None:
                res["line_spacing"] = 1.10
            return res
    return {
        "header_text": "جمهورية مصر العربية<br>وزارة الصحة والسكان<br>مديرية الشئون الصحية بالشرقية<br>الإدارة الصحية بأولاد صقر",
        "margin_top": "12mm",
        "margin_bottom": "auto",
        "margin_right": "8mm",
        "margin_left": "8mm",
        "line_spacing": 1.10,
        "logo_base64": DEFAULT_LOGO,
        "logo2_base64": "",
        "logo3_base64": "",
        "bg_base64": "",
        "frame_base64": "",
        "default_cert_title": "شهادة",
        "default_cert_notes": "تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد",
        "trainee_prefix": "",
        "trainee_title": "دكتور",
        "trainee_profession": "أخصائي الأمراض المتوطنة",
        "professions_list": ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"]
    }

def save_print_settings(h_text, m_top, m_bot, m_right, m_left, line_spacing, logo_data, logo2_data, logo3_data, bg_data, frame_data, def_title, def_notes, trainee_prefix, trainee_title, trainee_profession, professions_list, cert_box_inset="13mm", cert_trainee_extra=None, cert_facility_extra=None, cert_facility_section=None):
    with db() as c:
        old_cert = c.execute("SELECT cert_trainee_extra, cert_facility_extra, cert_facility_section FROM print_settings ORDER BY id DESC LIMIT 1").fetchone()
        if cert_trainee_extra is None:
            cert_trainee_extra = old_cert["cert_trainee_extra"] if old_cert and "cert_trainee_extra" in old_cert.keys() else ""
        if cert_facility_extra is None:
            cert_facility_extra = old_cert["cert_facility_extra"] if old_cert and "cert_facility_extra" in old_cert.keys() else ""
        if cert_facility_section is None:
            cert_facility_section = old_cert["cert_facility_section"] if old_cert and "cert_facility_section" in old_cert.keys() else ""
        c.execute("DELETE FROM print_settings")
        c.execute("INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, line_spacing, logo_base64, logo2_base64, logo3_base64, bg_base64, frame_base64, default_cert_title, default_cert_notes, trainee_prefix, trainee_title, trainee_profession, professions_list_json, cert_box_inset) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (h_text, m_top, "auto", m_right, m_left, float(line_spacing), logo_data, logo2_data, logo3_data, bg_data, frame_data, def_title, def_notes, trainee_prefix, trainee_title, trainee_profession, json.dumps(professions_list, ensure_ascii=False), cert_box_inset))
        c.execute("UPDATE print_settings SET cert_trainee_extra=?, cert_facility_extra=?, cert_facility_section=? WHERE id=(SELECT MAX(id) FROM print_settings)", (cert_trainee_extra or "", cert_facility_extra or "", cert_facility_section or ""))

def get_hierarchical_data(include_hidden=False):
    with db() as c:
        q = "SELECT * FROM hierarchical_facilities"
        if not include_hidden:
            q += " WHERE hidden = 0"
        q += " ORDER BY id ASC"
        rows = c.execute(q).fetchall()
        return [dict(r) for r in rows] if rows else []

def hierarchy_scope_widget(label="الهيكل الإداري المستهدف:", key="hier_scope"):
    """Choose a scope from the current hierarchy: authority -> administration -> facility."""
    rows = get_hierarchical_data(include_hidden=False)
    levels = [
        ("كل الهيكل الإداري", ""),
        ("المديرية / الجهة", "authority"),
        ("الإدارة", "administration"),
        ("المنشأة", "facility_name"),
    ]
    level_label = st.selectbox(label, [x[0] for x in levels], key=f"{key}_level")
    level_field = dict(levels)[level_label]
    scope = {"scope_governorate":"", "scope_authority":"", "scope_center":"", "scope_administration":"", "scope_facility":""}
    if not level_field:
        st.session_state["_last_hierarchy_scope"] = scope
        return scope
    current = rows
    field_map = [
        ("authority", "scope_authority", "المديرية / الجهة"),
        ("administration", "scope_administration", "الإدارة"),
        ("facility_name", "scope_facility", "المنشأة / وحدة الأمراض المتوطنة"),
    ]
    for src, dst, title in field_map:
        vals = sorted({str(r.get(src) or "").strip() for r in current if str(r.get(src) or "").strip()})
        if not vals:
            st.warning(f"لا توجد بيانات متاحة لمستوى {title} في الهيكل الإداري.")
            return scope
        chosen = st.selectbox(title, vals, key=f"{key}_{src}")
        scope[dst] = chosen
        current = [r for r in current if str(r.get(src) or "").strip() == chosen]
        if src == level_field:
            break
    st.session_state["_last_hierarchy_scope"] = dict(scope)
    return scope

def hierarchy_scope_sql(alias, scope):
    conditions, args = [], []
    mapping = [("scope_governorate","governorate"),("scope_authority","authority"),("scope_center","center"),("scope_administration","administration"),("scope_facility","facility_name")]
    scoped = False
    for scope_key, col in mapping:
        val = str(scope.get(scope_key) or "").strip()
        if val:
            scoped = True
            conditions.append(f"{alias}.{col}=?")
            args.append(val)
    if scoped:
        conditions.insert(0, f"COALESCE({alias}.hidden,0)=0")
    return (" AND ".join(conditions) if conditions else "1=1"), args

def template_scope_text(row):
    parts = [row.get("scope_authority"), row.get("scope_administration"), row.get("scope_facility")]
    parts = [str(x).strip() for x in parts if str(x or "").strip()]
    return "كل الهيكل الإداري" if not parts else " ← ".join(parts)

def hierarchy_header_html(scope=None, facility_value=None):
    # Build a print header reflecting exactly the selected hierarchy level.
    scope = dict(scope or {})
    rows = get_hierarchical_data(include_hidden=True)
    selected = None
    if facility_value:
        raw = str(facility_value or "").strip()
        for item in rows:
            paths = [
                str(item.get("facility_name") or "").strip(),
                " - ".join(str(item.get(k) or "").strip() for k in ("authority", "administration", "facility_name") if str(item.get(k) or "").strip()),
                " - ".join(str(item.get(k) or "").strip() for k in ("governorate", "authority", "center", "administration", "facility_name") if str(item.get(k) or "").strip()),
                "جمهورية مصر العربية - وزارة الصحة والسكان - " + " - ".join(str(item.get(k) or "").strip() for k in ("authority", "administration", "facility_name") if str(item.get(k) or "").strip()),
            ]
            if raw in paths or raw.endswith(" - " + str(item.get("facility_name") or "").strip()):
                selected = item
                break
        parts = [selected.get("authority"), selected.get("administration"), selected.get("facility_name")] if selected else [raw]
    else:
        auth = str(scope.get("scope_authority") or scope.get("authority") or "").strip()
        admin = str(scope.get("scope_administration") or scope.get("administration") or "").strip()
        fac = str(scope.get("scope_facility") or scope.get("facility_name") or "").strip()
        for item in rows:
            if auth and str(item.get("authority") or "").strip() != auth:
                continue
            if admin and str(item.get("administration") or "").strip() != admin:
                continue
            if fac and str(item.get("facility_name") or "").strip() != fac:
                continue
            if auth or admin or fac:
                selected = item
                break
        if selected:
            parts = []
            if auth or admin or fac:
                parts.append(auth or str(selected.get("authority") or "").strip())
            if admin or fac:
                parts.append(admin or str(selected.get("administration") or "").strip())
            if fac:
                parts.append(fac)
        else:
            parts = [auth, admin, fac]
    parts = [esc(str(x).strip()) for x in parts if str(x or "").strip()]
    if not parts:
        return "جمهورية مصر العربية<br>وزارة الصحة والسكان<br>كل الهيكل الإداري"
    return "<br>".join(parts)

def current_hierarchy_header():
    scope = st.session_state.get("_last_hierarchy_scope")
    if isinstance(scope, dict):
        return hierarchy_header_html(scope)
    return get_print_settings().get("header_text", "جمهورية مصر العربية<br>وزارة الصحة والسكان")

def template_matches_scope(template_row, scope):
    """True when an exam template applies to at least one facility inside the chosen plan scope."""
    t = dict(template_row) if not isinstance(template_row, dict) else template_row
    t_scope = {"scope_authority": t.get("scope_authority") or "", "scope_administration": t.get("scope_administration") or "", "scope_facility": t.get("scope_facility") or ""}
    if not any(str(v).strip() for v in t_scope.values()):
        return True
    scope = dict(scope or {})
    rows = get_hierarchical_data(include_hidden=False)
    for item in rows:
        if scope.get("scope_authority") and item.get("authority") != scope.get("scope_authority"):
            continue
        if scope.get("scope_administration") and item.get("administration") != scope.get("scope_administration"):
            continue
        if scope.get("scope_facility") and item.get("facility_name") != scope.get("scope_facility"):
            continue
        if t_scope["scope_authority"] and item.get("authority") != t_scope["scope_authority"]:
            continue
        if t_scope["scope_administration"] and item.get("administration") != t_scope["scope_administration"]:
            continue
        if t_scope["scope_facility"] and item.get("facility_name") != t_scope["scope_facility"]:
            continue
        return True
    return False

def template_matches_profession(template_row, trainee_profession):
    """Legacy/blank profession means all professions; otherwise require an exact normalized match."""
    t = dict(template_row) if not isinstance(template_row, dict) else template_row
    required = normalize_text(t.get("profession") or "")
    actual = normalize_text(trainee_profession or "")
    return not required or required in {normalize_text("كل الوظائف"), normalize_text("جميع الوظائف")} or required == actual

def template_matches_facility(template_row, facility_name):
    """Check whether a template scope contains the trainee facility."""
    t = dict(template_row) if not isinstance(template_row, dict) else template_row
    vals = {
        "authority": t.get("scope_authority") or "",
        "administration": t.get("scope_administration") or "",
        "facility_name": t.get("scope_facility") or "",
    }
    if not any(vals.values()):
        return True
    with db() as c:
        h = c.execute("SELECT * FROM hierarchical_facilities WHERE facility_name=? AND hidden=0 LIMIT 1", (facility_name,)).fetchone()
    if not h:
        return False
    return all((not v) or str(h[k] or "").strip() == str(v).strip() for k, v in vals.items())

def ensure_admin():
    with db() as c:
        u = c.execute("SELECT * FROM users WHERE role='admin'").fetchone()
        all_modules = list(ALL_MENU_MODULES.keys())
        if not u:
            c.execute("INSERT OR REPLACE INTO users(username,password_hash,role,permissions_json,active,created_at) VALUES(?,?,?,?,?,?)",
                      ("admin", hash_password("admin"), "admin", json.dumps(all_modules, ensure_ascii=False), 1, now()))
        else:
            # أي حساب يحمل دور admin هو مالك المنصة، وتُعاد له جميع الصلاحيات تلقائياً.
            c.execute("UPDATE users SET permissions_json=?, active=1 WHERE role='admin'", (json.dumps(all_modules, ensure_ascii=False),))

ensure_admin()

def login_user(u, p):
    with db() as c:
        user = c.execute("SELECT * FROM users WHERE username=? AND active=1", (u.strip(),)).fetchone()
        if user and verify_password(p, user["password_hash"]):
            c.execute("UPDATE users SET last_login=? WHERE id=?", (now(), user["id"]))
            return dict(user)
    return None

def _find_duplicate_trainee_value(c, field, normalized_value, exclude_id=None):
    if field not in {"phone", "national_id"} or not normalized_value:
        return False
    rows = c.execute(f"SELECT id, {field} FROM trainees WHERE COALESCE({field},'')<>''").fetchall()
    normalizer = normalize_egyptian_phone if field == "phone" else normalize_national_id
    for row in rows:
        if exclude_id is not None and int(row["id"]) == int(exclude_id):
            continue
        if normalizer(row[field]) == normalized_value:
            return True
    return False

def create_trainee(facility, name, phone, national_id, profession, assigned_template_id=None, work_start_date=""):
    phone_norm = normalize_egyptian_phone(phone)
    nid_norm = normalize_national_id(national_id)
    if not is_valid_egyptian_mobile(phone_norm):
        raise ValueError("INVALID_TRAINEE_PHONE")
    if not is_valid_egyptian_national_id(nid_norm):
        raise ValueError("INVALID_TRAINEE_NATIONAL_ID")
    with db() as c:
        if _find_duplicate_trainee_value(c, "phone", phone_norm):
            raise ValueError("DUPLICATE_TRAINEE_PHONE")
        if _find_duplicate_trainee_value(c, "national_id", nid_norm):
            raise ValueError("DUPLICATE_TRAINEE_NATIONAL_ID")
        cur = c.execute("INSERT INTO trainees(facility,name,phone,national_id,profession,work_start_date,status,assigned_template_id,created_at,updated_at,hidden) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (facility.strip(), normalize_text(name), phone_norm, nid_norm, profession, str(work_start_date or ""), "pending", assigned_template_id, now(), now(), 0))
        return cur.lastrowid

def update_trainee_data(tid, facility, name, phone, national_id, profession, work_start_date=None):
    phone_norm = normalize_egyptian_phone(phone)
    nid_norm = normalize_national_id(national_id)
    if not is_valid_egyptian_mobile(phone_norm):
        raise ValueError("INVALID_TRAINEE_PHONE")
    if not is_valid_egyptian_national_id(nid_norm):
        raise ValueError("INVALID_TRAINEE_NATIONAL_ID")
    with db() as c:
        if _find_duplicate_trainee_value(c, "phone", phone_norm, exclude_id=tid):
            raise ValueError("DUPLICATE_TRAINEE_PHONE")
        if _find_duplicate_trainee_value(c, "national_id", nid_norm, exclude_id=tid):
            raise ValueError("DUPLICATE_TRAINEE_NATIONAL_ID")
        if work_start_date is None:
            c.execute("UPDATE trainees SET facility=?, name=?, phone=?, national_id=?, profession=?, updated_at=? WHERE id=?",
                      (facility.strip(), normalize_text(name), phone_norm, nid_norm, profession, now(), int(tid)))
        else:
            c.execute("UPDATE trainees SET facility=?, name=?, phone=?, national_id=?, profession=?, work_start_date=?, updated_at=? WHERE id=?",
                      (facility.strip(), normalize_text(name), phone_norm, nid_norm, profession, str(work_start_date or ""), now(), int(tid)))

def trainee_by_credentials(name, facility):
    with db() as c:
        r = c.execute("SELECT * FROM trainees WHERE name=? AND facility=? AND status IN ('approved','active') AND hidden=0", (normalize_text(name), facility)).fetchone()
        return dict(r) if r else None

def trainee_by_phone_and_national_id(phone, national_id):
    phone_norm = normalize_egyptian_phone(phone)
    nid_norm = normalize_national_id(national_id)
    if not phone_norm or not nid_norm:
        return None
    with db() as c:
        rows = c.execute("SELECT * FROM trainees WHERE status IN ('approved','active') AND hidden=0 ORDER BY id DESC").fetchall()
        matches = [dict(r) for r in rows if normalize_egyptian_phone(r["phone"]) == phone_norm and normalize_national_id(r["national_id"]) == nid_norm]
        return matches[0] if len(matches) == 1 else None

def trainee_by_phone(phone):
    phone_norm = normalize_egyptian_phone(phone)
    if not phone_norm:
        return None
    with db() as c:
        rows = c.execute("SELECT * FROM trainees WHERE status IN ('approved','active') AND hidden=0 ORDER BY id DESC").fetchall()
        matches = [dict(r) for r in rows if normalize_egyptian_phone(r["phone"]) == phone_norm]
        return matches[0] if len(matches) == 1 else None

def phone_exists(phone):
    phone_norm = normalize_egyptian_phone(phone)
    if not phone_norm:
        return False
    with db() as c:
        return _find_duplicate_trainee_value(c, "phone", phone_norm)

def set_trainee_status_and_template(tid, status, assigned_template_id):
    with db() as c:
        c.execute("""UPDATE trainees SET status=?, assigned_template_id=?, updated_at=?, approved_at=CASE WHEN ?='approved' THEN ? ELSE approved_at END WHERE id=?""",
                  (status, assigned_template_id, now(), status, now(), tid))

def set_bulk_template_for_all(assigned_template_id):
    with db() as c:
        c.execute("""UPDATE trainees SET assigned_template_id=?, status=CASE WHEN status='pending' THEN 'approved' ELSE status END, approved_at=CASE WHEN status='pending' THEN ? ELSE approved_at END, updated_at=? WHERE hidden=0""",
                  (assigned_template_id, now(), now()))

def trainees_df(status=None, include_hidden=False):
    with db() as c:
        q = "SELECT id, facility, name, phone, national_id, profession, status, assigned_template_id, created_at, approved_at, hidden FROM trainees"
        conditions = []
        args = []
        if status:
            conditions.append("status=?")
            args.append(status)
        if not include_hidden:
            conditions.append("hidden=0")
        if conditions:
            q += " WHERE " + " AND ".join(conditions)
        q += " ORDER BY id DESC"
        return pd.read_sql_query(q, c, params=args)

def choose_questions(t):
    if not t:
        return []
    t_dict = dict(t)
    cats_raw = t_dict.get("categories_json", "[]")
    try:
        cats = json.loads(cats_raw) if cats_raw else []
    except:
        cats = []
    limit_count = int(t_dict.get("num_questions", 999999))
    with db() as c:
        if cats:
            placeholders = ','.join(['?'] * len(cats))
            all_db_questions = [dict(r) for r in c.execute(f"SELECT * FROM questions WHERE active=1 AND category IN ({placeholders}) ORDER BY RANDOM()", cats).fetchall()]
            if not all_db_questions:
                all_db_questions = [dict(r) for r in c.execute("SELECT * FROM questions WHERE active=1 ORDER BY RANDOM()").fetchall()]
        else:
            all_db_questions = [dict(r) for r in c.execute("SELECT * FROM questions WHERE active=1 ORDER BY RANDOM()").fetchall()]
        if limit_count >= 999900:
            return all_db_questions
        return all_db_questions[:limit_count]

def start_session(trainee_id, template_id):
    with db() as c:
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        if not t:
            raise ValueError("نموذج الاختبار غير موجود.")
        t_dict = dict(t)
        trainee_row = c.execute("SELECT facility, profession FROM trainees WHERE id=? AND hidden=0", (trainee_id,)).fetchone()
        if not trainee_row:
            raise ValueError("المتدرب غير موجود أو غير متاح حالياً.")
        if not template_matches_profession(t_dict, trainee_row["profession"]):
            raise ValueError("هذا النموذج مخصص لمهنة أخرى، ولا يمكن استخدامه لهذه الوظيفة.")
        scope_values = {
            "governorate": t_dict.get("scope_governorate") or "",
            "authority": t_dict.get("scope_authority") or "",
            "center": t_dict.get("scope_center") or "",
            "administration": t_dict.get("scope_administration") or "",
            "facility_name": t_dict.get("scope_facility") or "",
        }
        if any(scope_values.values()):
            h_row = c.execute("SELECT * FROM hierarchical_facilities WHERE facility_name=? AND hidden=0 LIMIT 1", (trainee_row["facility"],)).fetchone()
            if not h_row or not all((not v) or str(h_row[k] or "").strip() == str(v).strip() for k, v in scope_values.items()):
                raise ValueError("هذا النموذج غير مخصص للجهة الإدارية التابعة لك.")
        start_t_str = t_dict.get("start_time")
        end_t_str = t_dict.get("end_time")
        if start_t_str and end_t_str:
            dt_now = now_cairo()
            dt_start = datetime.fromisoformat(start_t_str)
            dt_end = datetime.fromisoformat(end_t_str)
            if dt_now < dt_start:
                raise ValueError(f"عذراً، لم يحن موعد الاختبار بعد. موعد البدء المحدد: {start_t_str.replace('T', ' الساعة ')}")
            if dt_now > dt_end:
                raise ValueError("عذراً، انتهى موعد هذا الاختبار ولم يعد متاحاً.")
        else:
            raise ValueError("عذراً، لم تقم الإدارة بتحديد موعد ساري لبدء ونهاية هذا الاختبار بعد.")

        today_start = today_date() + "T00:00:00"
        completed_today = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND template_id=? AND status='submitted' AND started_at>=?", (trainee_id, template_id, today_start)).fetchone()
        if completed_today:
            raise ValueError("عذراً، لا يمكنك أداء هذا الاختبار أكثر من مرة في نفس اليوم.")

        active = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND status='active'", (trainee_id,)).fetchone()
        if active:
            raise ValueError("لديك اختبار نشط بالفعل.")

        qs = choose_questions(t)
        started = now_cairo()
        expires = started + timedelta(minutes=int(t_dict.get("duration_minutes", 60)))
        with db() as c:
            cur = c.execute("INSERT INTO exam_sessions(trainee_id,template_id,started_at,expires_at,status) VALUES(?,?,?,?,?)",
                            (trainee_id, template_id, started.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds"), "active"))
            sid = cur.lastrowid
            for pos, q in enumerate(qs):
                try:
                    opts_parsed = json.loads(q["options_json"])
                except:
                    opts_parsed = ["نعم", "لا"]
                order = list(range(len(opts_parsed)))
                random.shuffle(order)
                c.execute("INSERT INTO exam_questions(session_id,question_id,position,option_order_json) VALUES(?,?,?,?)",
                          (sid, q["id"], pos, json.dumps(order)))
            c.execute("UPDATE trainees SET status='active', updated_at=? WHERE id=?", (now(), trainee_id))
            return sid

def submit_session(sid):
    with db() as c:
        s = c.execute("SELECT * FROM exam_sessions WHERE id=?", (sid,)).fetchone()
        if not s or s["status"] != "active":
            return None
        rows = c.execute("SELECT eq.*, q.answer FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=?", (sid,)).fetchall()
        correct = sum(1 for r in rows if r["selected_option"] is not None and int(r["selected_option"]) == int(r["answer"]))
        max_score = len(rows)
        percent = (correct / max_score * 100) if max_score else 0
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (s["template_id"],)).fetchone()
        t_dict = dict(t) if t else {}
        pass_pct = float(t_dict.get("pass_percent", 60.0))
        passed = 1 if percent >= pass_pct else 0
        cert = f"ELX-{sid:06d}"
        c.execute("UPDATE exam_sessions SET status='submitted', submitted_at=?, score=?, max_score=?, percent=?, passed=?, certificate_id=? WHERE id=?",
                  (now(), correct, max_score, percent, passed, cert, sid))
        c.execute("UPDATE trainees SET status='completed', updated_at=? WHERE id=?", (now(), s["trainee_id"]))
        return {"score": correct, "max_score": max_score, "percent": percent, "passed": passed, "certificate_id": cert}

def render_logos_html():
    sett = get_print_settings()
    logo1 = sett.get("logo_base64", DEFAULT_LOGO) or DEFAULT_LOGO
    logo2 = sett.get("logo2_base64", "") or ""
    logo3 = sett.get("logo3_base64", "") or ""
    logos = [logo1, logo2, logo3]
    logos_list_html = ""
    for i, logo in enumerate(logos, start=1):
        if logo:
            logos_list_html += f'<img src="{logo}" style="width:45px; height:45px; object-fit:contain; display:block;" alt="Logo {i}">'
    return f"""
    <div style="display:flex; flex-direction:row; gap:8px; align-items:center; justify-content:flex-start; direction:ltr;">
        {logos_list_html}
    </div>
    """

def generate_qr_code_base64(data_text):
    qr = qrcode.QRCode(version=1, box_size=5, border=1)
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return "data:image/png;base64," + __import__("base64").b64encode(buffered.getvalue()).decode("utf-8")

def _certificate_background_css(sett):
    """Return the certificate page background. Background image is the only frame source."""
    bg_data = sett.get("bg_base64", "") or ""
    if bg_data:
        return f"background-image:url('{bg_data}'); background-repeat:no-repeat; background-position:center center; background-size:100% 100%;"
    return "background:#ffffff; border:1.2mm solid #059669;"


def _certificate_inner_box_css(sett):
    """Return the adjustable inner content box used for every certificate element."""
    raw = sett.get("cert_box_inset", "13mm") or "13mm"
    try:
        value = float(str(raw).replace("mm", "").strip())
    except Exception:
        value = 13.0
    value = max(4.0, min(35.0, value))
    return f"top:{value:g}mm;right:{value:g}mm;bottom:{value:g}mm;left:{value:g}mm;"


def _certificate_common_html(inner_content, sett):
    bg_css = _certificate_background_css(sett)
    box_css = _certificate_inner_box_css(sett)
    return f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@500;700;800;900&family=Reem+Kufi:wght@700&display=swap');
@page {{ size:A4 landscape; margin:0 !important; }}
html,body {{ margin:0 !important; padding:0 !important; width:297mm; height:210mm; }}
body {{ font-family:'Cairo','Tahoma',sans-serif; direction:rtl; overflow:hidden; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }}
.cert-page {{ width:297mm; height:210mm; position:relative; overflow:hidden; margin:0; padding:0; box-sizing:border-box; {bg_css} }}
.cert-inner-box {{ position:absolute; {box_css} box-sizing:border-box; display:flex; flex-direction:column; justify-content:flex-start; overflow:hidden; text-align:center; padding:4mm 7mm 3mm 7mm; }}
.cert-header {{ flex:0 0 auto; width:100%; display:flex; justify-content:space-between; align-items:flex-start; direction:rtl; min-height:18mm; margin-bottom:0; }}
.header-right {{ text-align:right; font-size:11pt; line-height:1.3; font-weight:900; color:#064e3b; max-width:72%; }}
.cert-logos {{ text-align:left; flex:0 0 auto; }}
.cert-body {{ flex:0 0 auto; min-height:0; width:100%; display:flex; flex-direction:column; justify-content:flex-start; align-items:center; overflow:hidden; }}
h1.cert-main-title {{ font-family:'Reem Kufi','Amiri','Cairo',serif; color:#047857; font-size:32pt; line-height:1.05; margin:0 0 2mm 0; font-weight:700; }}
.cert-prefix-line {{ font-size:18pt; line-height:1.2; color:#374151; font-weight:800; margin:1mm 0 2mm; min-height:7mm; }}
.cert-person-line {{ font-size:25pt; line-height:1.15; color:#064e3b; font-weight:900; margin:1mm 0 3mm; white-space:nowrap; }}
.cert-facility-line {{ font-size:20pt; line-height:1.2; color:#047857; font-weight:900; margin:1mm 0 3mm; white-space:nowrap; }}
.cert-profession-line {{ font-size:16pt; line-height:1.2; color:#374151; font-weight:800; margin:0.5mm 0 1.5mm; white-space:nowrap; min-height:0; }}
.cert-result-row {{ width:94%; display:flex; align-items:center; justify-content:center; gap:10mm; margin-top:2mm; margin-bottom:0; }}
.cert-result {{ font-size:15pt; line-height:1.35; color:#1f2937; font-weight:900; white-space:nowrap; }}
.cert-number {{ font-size:12pt; line-height:1.2; color:#064e3b; font-weight:900; white-space:nowrap; }}
.cert-qr {{ display:flex; align-items:center; gap:2mm; direction:ltr; flex:0 0 auto; }}
.cert-qr img {{ width:18mm; height:18mm; display:block; }}
.cert-code {{ font-size:8pt; font-weight:900; color:#064e3b; white-space:nowrap; }}
.cert-footer {{ flex:0 0 auto; width:100%; margin-top:4mm; }}
.credits-footer-row {{ width:100%; display:flex; justify-content:space-between; align-items:flex-end; direction:rtl; font-size:9.5pt; font-weight:900; color:#065f46; margin-top:2mm; line-height:1.2; }}
.ownership-footer-row {{ width:100%; text-align:center; font-size:8pt; font-weight:800; color:#047857; padding:1.5mm 0; margin-top:1mm; line-height:1.2; border-top:1.2px solid #047857; border-bottom:1.2px solid #047857; box-sizing:border-box; }}
</style>
</head>
<body>
<div class="cert-page">
  <div class="cert-inner-box">
    {inner_content}
  </div>
</div>
</body>
</html>
"""


def _certificate_footer_html():
    return """
<div class="cert-footer">
  <div class="ownership-footer-row">جميع الحقوق محفوظة © 2026 | تطوير Dr/Ahmed.S.Hegazy</div>
  <div class="credits-footer-row">
    <span>مسؤول التدريب</span><span>رئيس القسم</span><span>مدير المتوطنة</span><span>يعتمد: مدير عام الإدارة</span>
  </div>
</div>
"""


def generate_customizable_certificate_html(sid, custom_title=None, custom_notes=None):
    """Generate one individual A4-landscape certificate."""
    sett = get_print_settings()
    title_val = "شَهَادَةُ حُضُورِ دَوْرَةٍ تَدْرِيبِيَّةٍ"
    prefix_val = (sett.get("trainee_prefix", "") or "").strip()
    title_role_val = (sett.get("trainee_title", "") or "").strip()

    with db() as c:
        r = c.execute("""SELECT s.*, t.name trainee_name, t.facility, t.profession trainee_profession,
                        e.name template_name, e.exam_type
                        FROM exam_sessions s
                        JOIN trainees t ON t.id=s.trainee_id
                        LEFT JOIN exam_templates e ON e.id=s.template_id
                        WHERE s.id=?""", (sid,)).fetchone()
    if not r:
        return ""

    name = str(r["trainee_name"] or "").strip()
    prof = str(r["trainee_profession"] or sett.get("trainee_profession", "أخصائي الأمراض المتوطنة") or "").strip()
    facility = str(r["facility"] or "").strip()
    score = r["score"] or 0
    max_score = r["max_score"] or 0
    percent = float(r["percent"] or 0)
    status_text = "اجتاز الاختبار بنجاح" if r["passed"] else "لم يجتز الاختبار"
    cert_no = str(r["certificate_id"] or f"ELX-{sid:06d}")
    qr = generate_qr_code_base64(cert_no)

    # Prefix is a dedicated line; title + name are a separate line.
    prefix_html = f"<div class='cert-prefix-line'>{esc(prefix_val)}</div>" if prefix_val else ""
    person_label = " ".join(x for x in [title_role_val, name] if x)

    inner = f"""
<div class="cert-header">
  <div class="header-right">{hierarchy_header_html(facility_value=facility)}</div>
  <div class="cert-logos">{render_logos_html()}</div>
</div>
<div class="cert-body">
  <h1 class="cert-main-title">{esc(title_val)}</h1>
  {prefix_html}
  <div class="cert-person-line" style="color:#b91c1c;">{esc(person_label)}</div>
  <div class="cert-profession-line">الوظيفة: {esc(prof)} &nbsp;&nbsp; | &nbsp;&nbsp; المنشأة: {esc(facility)}</div>
  <div class="cert-profession-line">{esc(str(sett.get("cert_trainee_extra", "") or "").strip())}</div>
  <div class="cert-result-row">
    <div class="cert-result">النتيجة: {score} / {max_score} ({percent:.1f}%) — {status_text}</div>
    <div class="cert-number">رقم الشهادة: {esc(cert_no)}</div>
    <div class="cert-qr"><img src="{qr}" alt="QR"><span class="cert-code">QR</span></div>
  </div>
</div>
{_certificate_footer_html()}
"""
    return _certificate_common_html(inner, sett)


def generate_facility_certificate_html(facility_name, session_ids, custom_title=None):
    """Generate one A4-landscape certificate evaluating an entire facility from submitted reports."""
    sett = get_print_settings()
    title_val = (custom_title or "شهادة تقييم منشأة") or "شهادة تقييم منشأة"
    prefix_val = (sett.get("trainee_prefix", "") or "").strip()

    rows = []
    with db() as c:
        for sid in session_ids:
            row = c.execute("SELECT percent FROM exam_sessions WHERE id=? AND status='submitted'", (sid,)).fetchone()
            if row:
                rows.append(float(row["percent"] or 0))
    if not rows:
        return ""

    avg = sum(rows) / len(rows)
    facility_digest = hashlib.sha256(str(facility_name).encode("utf-8")).hexdigest()[:6].upper()
    facility_code = "FAC-" + facility_digest
    qr = generate_qr_code_base64(facility_code)
    prefix_html = f"<div class='cert-prefix-line'>{esc(prefix_val)}</div>" if prefix_val else ""

    inner = f"""
<div class="cert-header">
  <div class="header-right">{hierarchy_header_html(facility_value=facility_name)}</div>
  <div class="cert-logos">{render_logos_html()}</div>
</div>
<div class="cert-body">
  <h1 class="cert-main-title">{esc(title_val)}</h1>
  {prefix_html}
  <div class="cert-profession-line" style="color:#b91c1c; font-size:18pt;">{esc(str(sett.get("cert_facility_section", "") or "").strip())}</div>
  <div class="cert-facility-line" style="color:#b91c1c;">{esc(facility_name)}</div>
  <div class="cert-profession-line">{esc(str(sett.get("cert_facility_extra", "") or "").strip())}</div>
  <div class="cert-result-row">
    <div class="cert-result">نتيجة تقييم المنشأة: {avg:.1f}%</div>
    <div class="cert-number">رقم الشهادة: {esc(facility_code)}</div>
    <div class="cert-qr"><img src="{qr}" alt="QR"><span class="cert-code">QR</span></div>
  </div>
</div>
{_certificate_footer_html()}
"""
    return _certificate_common_html(inner, sett)


def generate_certificates_batch_html(session_ids, custom_title=None, custom_notes=None):
    """Create one print document containing one individual certificate per A4 page."""
    pages = []
    for sid in session_ids:
        one = generate_customizable_certificate_html(sid, custom_title, custom_notes)
        if not one:
            continue
        body_start = one.find('<body>')
        body_end = one.rfind('</body>')
        if body_start >= 0 and body_end >= 0:
            pages.append(one[body_start + len('<body>'):body_end])
    if not pages:
        return ""
    return f"""
<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8">
<style>@page {{ size:A4 landscape; margin:0 !important; }} html,body {{margin:0!important;padding:0!important;width:297mm;}} body {{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;}} .cert-page {{page-break-after:always!important;break-after:page!important;}} .cert-page:last-child {{page-break-after:avoid!important;break-after:avoid-page!important;}}</style></head><body>{''.join(pages)}</body></html>"""

def generate_trainee_exam_sheet_html(sid):
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    header_right_text = ''
    with db() as c:
        s = c.execute("""SELECT s.*, t.name trainee_name, t.facility, t.profession trainee_profession, e.name template_name, e.exam_type FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?""", (sid,)).fetchone()
        if not s:
            return ""
        rows = c.execute("""SELECT eq.*, q.question, q.options_json, q.answer FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=? ORDER BY eq.position""", (sid,)).fetchall()
    header_right_text = hierarchy_header_html(facility_value=s["facility"])
    q_html_content = ""
    for idx, r in enumerate(rows, start=1):
        try:
            opts = json.loads(r["options_json"])
        except:
            opts = ["نعم", "لا"]
        try:
            order = json.loads(r["option_order_json"])
        except:
            order = list(range(len(opts)))
        disp_opts = [opts[i] for i in order]
        selected_opt_idx = r["selected_option"]
        correct_ans_idx = r["answer"]
        is_correct = r["is_correct"]
        raw_q_text = r["question"]
        
        opts_html = ""
        for o_idx, opt_text in enumerate(disp_opts):
            orig_opt_index = order[o_idx]
            is_selected = (selected_opt_idx is not None and orig_opt_index == int(selected_opt_idx))
            is_true_ans = (orig_opt_index == int(correct_ans_idx))
            style_bg = "#f8fafc"
            border_color = "#e2e8f0"
            icon_str = "🔲"
            if is_true_ans:
                style_bg = "#dcfce7"
                border_color = "#059669"
                icon_str = "✅"
            elif is_selected and not is_true_ans:
                style_bg = "#fee2e2"
                border_color = "#dc2626"
                icon_str = "❌"
            opts_html += f'<div style="padding: 0.1mm 1mm; margin: 0 0 0.1mm 0; background: {style_bg}; border: 1px solid {border_color}; border-radius: 2px; font-size: 8pt; line-height: 1.0;">{icon_str} {esc(opt_text)}</div>'

        if "IMAGE:" in raw_q_text:
            parts = raw_q_text.split("\n\n")
            img_uri = parts[0].replace("IMAGE:", "").strip()
            q_text_clean = parts[1] if len(parts) > 1 else ""
            if img_uri:
                content_inner_html = f'''
                <div style="display: flex; flex-direction: row; gap: 4mm; align-items: flex-start; width: 100%;">
                    <div style="flex: 1; min-width: 0;">{opts_html}</div>
                    <div style="width: 32mm; flex-shrink: 0; text-align: center;">
                        <img src="{img_uri}" style="max-height: 18mm; max-width: 32mm; object-fit: contain; border-radius: 2px; border: 1px solid #cbd5e1; display: block; margin: auto;">
                    </div>
                </div>
                '''
            else:
                content_inner_html = opts_html
        else:
            q_text_clean = raw_q_text
            content_inner_html = opts_html

        q_text_clean = clean_question_text(q_text_clean)
        status_badge = '<span style="color: green; font-weight: bold;">صحيح</span>' if is_correct else '<span style="color: red; font-weight: bold;">خاطئ</span>'
        q_html_content += f"""
        <div style="margin: 0; padding: 0.6mm 1.2mm; background:#ffffff; border:1px solid #059669; border-radius:4px; box-sizing:border-box; width:100%; height:30mm; min-height:30mm; max-height:30mm; overflow:hidden; display:flex; flex-direction:column; justify-content:flex-start; page-break-inside:avoid; break-inside:avoid;">
            <div style="font-weight: bold; color: #065f46; margin-bottom: 0.3px; font-size: 8pt; line-height: 1.0; height: 7.5mm; overflow: hidden;">({idx}) {esc(q_text_clean)} | النتيجة: {status_badge}</div>
            <div style="margin-top: 0px; padding-right: 0px; flex-grow: 1;">{content_inner_html}</div>
        </div>
        """
    score_val, max_score_val, percent_val = s["score"] or 0, s["max_score"] or 0, s["percent"] or 0.0
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
    <meta charset="UTF-8">
    <style>
    @page {{ size: A4 portrait; margin: 12mm 8mm 18mm 8mm !important; }}
    body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0 !important; padding: 0 !important; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
    .report-wrapper {{ width: 194mm; max-width: 194mm; margin: 0 auto !important; padding: 0 !important; position: relative; }}
    .first-page-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #059669; padding-bottom: 2mm; margin-bottom: 2mm; }}
    h2 {{ text-align: center; color: #047857; font-size: 11pt; margin: 0 0 2px 0 !important; padding-top: 0 !important; line-height: {line_sp}; }}
    .tpl-info {{ background: #f0fdf4; border: 1px dashed #059669; padding: 2mm 6px; border-radius: 4px; margin-top: 2mm !important; margin-bottom: 2mm; font-size: 7.5pt; font-weight: bold; color: #065f46; text-align: center; line-height: {line_sp}; }}
    .questions-grid {{ display: grid; grid-template-columns: 1fr 1fr; grid-auto-rows: 30mm; gap: 2mm; width: 100%; }}
    </style>
    </head>
    <body>
    <div class="report-wrapper">
        <div class="first-page-header">
            <div style="font-size: 8pt; font-weight: bold; color: #065f46; line-height: 1.15;">{header_right_text}</div>
            <div>{render_logos_html()}</div>
        </div>
        <h2>نموذج إجابة واختبار المتدرب: {esc(s['trainee_name'])}</h2>
        <div class="tpl-info">
            جهة العمل: {esc(s['facility'])} | الوظيفة: {esc(s['trainee_profession'] if s['trainee_profession'] is not None else '')} | الاختبار: {esc(s['template_name'] or 'اختبار معتمد')} ({esc(s['exam_type'] or 'قبل التدريب')}) | النتيجة: {score_val} / {max_score_val} ({percent_val:.1f}%)
        </div>
        <div class="questions-grid">
            {q_html_content}
        </div>
    </div>
    </body>
    </html>
    """

def generate_staff_signature_table_html(scope=None, title="كشف العاملين والتوقيع"):
    """Build a printable staff roster matching the selected administrative hierarchy."""
    scope = dict(scope or {})
    selected_keys = (
        ("scope_governorate", "governorate"),
        ("scope_authority", "authority"),
        ("scope_center", "center"),
        ("scope_administration", "administration"),
        ("scope_facility", "facility_name"),
    )
    with db() as c:
        staff_rows = [dict(r) for r in c.execute(
            "SELECT id, name, profession, facility FROM trainees "
            "WHERE COALESCE(hidden,0)=0 ORDER BY name COLLATE NOCASE"
        ).fetchall()]

    active_hierarchy = get_hierarchical_data(include_hidden=False)
    if any(str(scope.get(k) or "").strip() for k, _ in selected_keys):
        scoped_hierarchy = [
            h for h in active_hierarchy
            if all(
                not str(scope.get(scope_key) or "").strip()
                or str(h.get(hierarchy_key) or "").strip() == str(scope.get(scope_key) or "").strip()
                for scope_key, hierarchy_key in selected_keys
            )
        ]
        staff_rows = [
            person for person in staff_rows
            if any(trainee_matches_hierarchy(person.get("facility"), h) for h in scoped_hierarchy)
        ]

    body_rows = []
    for idx, person in enumerate(staff_rows, start=1):
        body_rows.append(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td style='text-align:right'>{esc(person.get('name') or '')}</td>"
            f"<td>{esc(person.get('profession') or '')}</td>"
            "<td style='height:9mm'>&nbsp;</td>"
            "</tr>"
        )
    if not body_rows:
        body_rows.append(
            "<tr><td>1</td><td style='text-align:right;height:9mm'>&nbsp;</td>"
            "<td>&nbsp;</td><td style='height:9mm'>&nbsp;</td></tr>"
        )

    return f"""
    <section class="staff-signature-roster" style="margin-top:7mm; page-break-inside:auto; break-inside:auto;">
      <h3 style="text-align:center; margin:0 0 3mm; font-size:12pt; color:#047857;">{esc(title)}</h3>
      <table style="width:100%; border-collapse:collapse; font-size:10pt;">
        <thead><tr>
          <th style="border:1px solid #64748b; padding:5px; width:8%;">م</th>
          <th style="border:1px solid #64748b; padding:5px; width:38%;">اسم العامل</th>
          <th style="border:1px solid #64748b; padding:5px; width:29%;">الوظيفة</th>
          <th style="border:1px solid #64748b; padding:5px; width:25%;">التوقيع</th>
        </tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </section>
    """


def generate_general_report_html(title, content_html, target_pages=1, header_text=None):
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    header_right_text = header_text or current_hierarchy_header()
    roster_html = generate_staff_signature_table_html(st.session_state.get("_last_hierarchy_scope", {}))
    printable_content = content_html + roster_html
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
    <meta charset="UTF-8">
    <style>
    @page {{ size: A4 portrait; margin: 12mm 8mm 18mm 8mm !important; }}
    body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0 !important; padding: 0 !important; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
    .report-wrapper {{ width: 194mm; max-width: 194mm; margin: 0 auto !important; padding: 0 !important; position: relative; }}
    .first-page-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #059669; padding-bottom: 2mm; margin-bottom: 2mm; }}
    h2 {{ text-align: center; color: #047857; font-size: 12pt; margin: 0 0 2px 0 !important; padding-top: 0 !important; line-height: {line_sp}; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 2px; font-size: 8pt; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 3px 5px; text-align: center; line-height: {line_sp}; page-break-inside: avoid; break-inside: avoid; }}
    th {{ background-color: #059669; color: white; font-weight: bold; }}
    tr {{ page-break-inside: avoid; break-inside: avoid; }}
    tr:nth-child(even) {{ background-color: #f0fdf4; }}
    </style>
    </head>
    <body>
    <div class="report-wrapper">
        <div class="first-page-header">
            <div style="font-size: 8pt; font-weight: bold; color: #065f46; line-height: 1.15;">{header_right_text}</div>
            <div>{render_logos_html()}</div>
        </div>
        <h2>{esc(title)}</h2>
        <div style="text-align: left; font-size: 7.5pt; color: #6b7280; margin-bottom: 2px;">تاريخ الإصدار: {now_cairo().strftime('%Y-%m-%d %I:%M %p')}</div>
        {printable_content}
    </div>
    </body>
    </html>
    """

def generate_action_plan_report_html(title, content_html, target_pages=1, header_text=None, hierarchy_scope=None):
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    header_right_text = header_text or current_hierarchy_header()
    roster_html = generate_staff_signature_table_html(hierarchy_scope or {})
    printable_content = content_html + roster_html
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
    <meta charset="UTF-8">
    <style>
    @page {{ size: A4 portrait; margin: 12mm 8mm 18mm 8mm !important; }}
    body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0 !important; padding: 0 !important; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
    .report-wrapper {{ width: 194mm; max-width: 194mm; margin: 0 auto !important; padding: 0 !important; position: relative; }}
    .first-page-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #059669; padding-bottom: 2mm; margin-bottom: 2mm; }}
    h2 {{ text-align: center; color: #047857; font-size: 12pt; margin: 0 0 2px 0 !important; padding-top: 0 !important; line-height: {line_sp}; }}
    </style>
    </head>
    <body>
    <div class="report-wrapper">
        <div class="first-page-header">
            <div style="font-size: 8pt; font-weight: bold; color: #065f46; line-height: 1.15;">{header_right_text}</div>
            <div>{render_logos_html()}</div>
        </div>
        <h2>{esc(title)}</h2>
        <div style="text-align: left; font-size: 7.5pt; color: #6b7280; margin-bottom: 2px;">تاريخ الإصدار: {now_cairo().strftime('%Y-%m-%d %I:%M %p')}</div>
        {printable_content}
    </div>
    </body>
    </html>
    """

def generate_exam_template_print_html(template_id):
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    header_right_text = sett.get('header_text', '')
    with db() as c:
        tpl = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        if not tpl:
            return ""
        t_dict = dict(tpl)
    header_right_text = hierarchy_header_html(t_dict)
    questions_list = choose_questions(t_dict)
    q_html_content = ""
    for idx, q in enumerate(questions_list, start=1):
        try:
            opts = json.loads(q["options_json"])
        except:
            opts = ["نعم", "لا"]
        raw_q_text = q["question"]
        
        opts_html = "".join([f'<div style="padding: 0.1mm 1mm; margin: 0 0 0.1mm 0; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 2px; font-size: 8pt; line-height: 1.0;">🔲 {esc(opt)}</div>' for opt in opts])
        
        if "IMAGE:" in raw_q_text:
            parts = raw_q_text.split("\n\n")
            img_uri = parts[0].replace("IMAGE:", "").strip()
            q_text_clean = parts[1] if len(parts) > 1 else ""
            if img_uri:
                content_inner_html = f'''
                <div style="display: flex; flex-direction: row; gap: 4mm; align-items: flex-start; width: 100%;">
                    <div style="flex: 1; min-width: 0;">{opts_html}</div>
                    <div style="width: 32mm; flex-shrink: 0; text-align: center;">
                        <img src="{img_uri}" style="max-height: 18mm; max-width: 32mm; object-fit: contain; border-radius: 2mm; border: 1px solid #cbd5e1; display: block; margin: auto;">
                    </div>
                </div>
                '''
            else:
                content_inner_html = opts_html
        else:
            q_text_clean = raw_q_text
            content_inner_html = opts_html

        q_text_clean = clean_question_text(q_text_clean)
        q_html_content += f"""
        <div style="margin: 0; padding: 0.6mm 1.2mm; background:#ffffff; border:1px solid #059669; border-radius:4px; box-sizing:border-box; width:100%; height:30mm; min-height:30mm; max-height:30mm; overflow:hidden; display:flex; flex-direction:column; justify-content:flex-start; page-break-inside:avoid; break-inside:avoid;">
            <div style="font-weight: bold; color: #065f46; margin-bottom: 0.3px; font-size: 8pt; line-height: 1.0; height: 7.5mm; overflow: hidden;">({idx}) {esc(q_text_clean)}</div>
            <div style="margin-top: 0px; padding-right: 0px; flex-grow: 1;">{content_inner_html}</div>
        </div>
        """
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
    <meta charset="UTF-8">
    <style>
    @page {{ size: A4 portrait; margin: 12mm 8mm 18mm 8mm !important; }}
    body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0 !important; padding: 0 !important; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
    .report-wrapper {{ width: 194mm; max-width: 194mm; margin: 0 auto !important; padding: 0 !important; position: relative; }}
    .first-page-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #059669; padding-bottom: 2mm; margin-bottom: 2mm; }}
    h2 {{ text-align: center; color: #047857; font-size: 11pt; margin: 0 0 2px 0 !important; padding-top: 0 !important; line-height: {line_sp}; }}
    .tpl-info {{ background: #f0fdf4; border: 1px dashed #059669; padding: 2mm 6px; border-radius: 4px; margin-top: 2mm !important; margin-bottom: 2mm; font-size: 7.5pt; font-weight: bold; color: #065f46; text-align: center; line-height: {line_sp}; }}
    .questions-grid {{ display: grid; grid-template-columns: 1fr 1fr; grid-auto-rows: 30mm; gap: 2mm; width: 100%; }}
    </style>
    </head>
    <body>
    <div class="report-wrapper">
        <div class="first-page-header">
            <div style="font-size: 8pt; font-weight: bold; color: #065f46; line-height: 1.15;">{header_right_text}</div>
            <div>{render_logos_html()}</div>
        </div>
        <h2>نموذج امتحان: {esc(t_dict['name'])} ({esc(t_dict.get('exam_type', 'قبل التدريب'))})</h2>
        <div class="tpl-info">
            التصنيف: {esc(t_dict.get('exam_type', 'قبل التدريب'))} | مدة الاختبار: {t_dict['duration_minutes']} د | نسبة النجاح: {t_dict['pass_percent']}% | إجمالي الأسئلة: {len(questions_list)}
        </div>
        <div class="questions-grid">
            {q_html_content}
        </div>
    </div>
    </body>
    </html>
    """

def render_print_button_only(html_content, label_prefix=""):
    print_sett = get_print_settings()
    is_cert = ("شهاد" in label_prefix) or ("certificate" in label_prefix.lower())
    
    if is_cert:
        repeated_print_css = """
        <style>
        @page {
            size: A4 landscape;
            margin: 0 !important;
        }
        @media print {
            html, body {
                margin: 0 !important;
                padding: 0 !important;
                width: 297mm !important;
                height: 210mm !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            .cert-page {
                page-break-after: always !important;
                break-after: page !important;
            }
            .cert-page:last-child {
                page-break-after: avoid !important;
                break-after: avoid-page !important;
            }
        }
        </style>
        """
    else:
        m_top = "12mm"
        m_right = "8mm"
        m_left = "8mm"
        # Apply Arabic Naskh typography to every non-certificate printout only.
        # Certificate HTML is intentionally left untouched to preserve its existing design.
        repeated_print_css = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Naskh+Arabic:wght@400;500;600;700&display=swap');
        html, body, body * {{
            font-family: 'Noto Naskh Arabic', 'Amiri', 'Traditional Arabic', serif !important;
        }}
        html, body {{ font-size: 11pt; }}
        body {{ line-height: 1.35; }}
        p, li {{ font-size: 10.5pt; }}
        table {{ font-size: 9.5pt; }}
        th, td {{ line-height: 1.25; }}
        @page {{
            size: A4 portrait;
            margin: {m_top} {m_right} 16mm {m_left} !important;
        }}
        @media print {{
            html, body {{
                margin: 0 !important;
                padding: 0 !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            @page {{
                @bottom-center {{
                    content: "صفحة " counter(page) " من " counter(pages);
                }}
            }}
            body {{
                counter-reset: page;
            }}
            .print-footer-dynamic {{
                position: fixed !important;
                bottom: 0 !important;
                left: 0 !important;
                right: 0 !important;
                width: 100% !important;
                background: #ffffff !important;
                border-top: 2px solid #059669;
                padding: 4px 4px !important;
                font-family: 'Cairo', Tahoma, sans-serif;
                font-size: 10pt;
                font-weight: 900;
                color: #065f46;
                box-sizing: border-box;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}
            .print-footer-container {{
                display: block;
                page-break-inside: avoid;
            }}
            .report-wrapper {{
                margin-bottom: 0 !important;
                padding-bottom: 15mm !important;
                overflow: visible !important;
            }}
            .print-footer-dynamic:last-of-type {{
                position: relative !important;
                bottom: auto !important;
                margin-top: 10px !important;
                page-break-inside: avoid !important;
            }}
            .page-number-box {{
                counter-increment: page;
            }}
            .page-number-box::after {{
                content: "صفحة " counter(page);
            }}
            .print-footer-top-row {{
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                width: 100% !important;
                direction: rtl !important;
                font-size: 9.5pt;
                font-weight: 800;
                color: #047857;
                border-bottom: 1px dotted #059669;
                padding-bottom: 2px;
                margin-bottom: 2px;
            }}
            .print-footer-bottom-row {{
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                width: 100% !important;
                direction: rtl !important;
                font-size: 10pt;
                font-weight: 900;
                color: #065f46;
            }}
        }}
        .print-footer-dynamic {{
            width: 100% !important;
            background: #ffffff !important;
            border-top: 2px solid #059669;
            margin-top: 6mm;
            padding: 6px 4px;
            font-family: 'Cairo', Tahoma, sans-serif;
            font-size: 10pt;
            font-weight: 900;
            color: #065f46;
            box-sizing: border-box;
        }}
        .print-footer-top-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            direction: rtl;
            font-size: 9.5pt;
            font-weight: 800;
            color: #047857;
            border-bottom: 1px dotted #059669;
            padding-bottom: 2px;
            margin-bottom: 2px;
        }}
        .print-footer-bottom-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            direction: rtl;
            font-size: 10pt;
            font-weight: 900;
            color: #065f46;
        }}
        </style>
        """
        footer_bar_html = f"""
        <div class="print-footer-container">
            <div class="print-footer-dynamic">
                <div class="print-footer-top-row">
                    <div style="text-align: center; width: 100%;">جميع الحقوق محفوظة © 2026 | تطوير Dr/Ahmed.S.Hegazy</div>
                    <div class="page-number-box" style="position: absolute; left: 4px;"></div>
                </div>
                <div class="print-footer-bottom-row">
                    <span>مسؤول التدريب</span>
                    <span>رئيس القسم</span>
                    <span>مدير المتوطنة</span>
                    <span>يعتمد: مدير عام الإدارة</span>
                </div>
            </div>
        </div>
        """
        if "</body>" in html_content:
            html_content = html_content.replace("</body>", footer_bar_html + "</body>")
        else:
            html_content += footer_bar_html

    if "</head>" in html_content:
        html_content = html_content.replace("</head>", repeated_print_css + "</head>", 1)
    else:
        html_content = repeated_print_css + html_content

    encoded_html = json.dumps(html_content)
    
    if is_cert:
        chosen_orient = "أفقي (Landscape)"
    else:
        orient_key = f"orient_{hash(label_prefix) & 0xffffffff}"
        chosen_orient = st.selectbox("اتجاه الورق للطباعة (مقاس A4):", ["أفقي (Landscape)", "رأسي (Portrait)"], key=orient_key)

    js_code = """
    <div style="margin: 4px 0;">
        <button onclick="printDoc()" style="width: 100%; background-color: #059669; color: white; padding: 8px 12px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-family: 'Cairo', sans-serif; font-size: 13pt;">
            🖨 طباعة / حفظ المستند (A4 """ + chosen_orient + """ - """ + label_prefix + """)
        </button>
    </div>
    <script>
    function printDoc() {
        var win = window.open('', '_blank');
        var styledHtml = """ + encoded_html + """;
        win.document.write(styledHtml);
        win.document.close();
        
        // عدد الصفحات يُحدد تلقائياً بواسطة محرك الطباعة حسب طول المحتوى.
        // لا يوجد أي حد ثابت لعدد الصفحات أو قص للمحتوى.

        win.focus();
        setTimeout(function(){
            win.print();
        }, 600);
    }
    </script>
    """
    components.html(js_code, height=100)

# ============================================================
# 5) واجهات النظام وتوجيه الشاشات
# ============================================================
for k, v in {"logged_in": False, "username": "", "role": "", "permissions": [], "trainee_id": "", "trainee_name": "", "exam_session_id": None, "last_result_id": None, "form_key": 0, "add_success_msg": "", "active_admin_tab": "📊 لوحة التحكم", "scanned_cert_code": ""}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def header():
    header_html = f"""
    <style>
    @keyframes electricMultiGlow {{
        0% {{ box-shadow: 0 0 15px rgba(16, 185, 129, 0.4), 0 0 30px rgba(5, 150, 105, 0.3), inset 0 0 15px rgba(255, 255, 255, 0.2); border-color: #34d399; }}
        14.28% {{ box-shadow: 0 0 20px rgba(20, 184, 166, 0.5), 0 0 35px rgba(13, 148, 136, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.3); border-color: #2dd4bf; }}
        28.56% {{ box-shadow: 0 0 20px rgba(14, 165, 233, 0.5), 0 0 35px rgba(2, 132, 199, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.3); border-color: #38bdf8; }}
        42.84% {{ box-shadow: 0 0 20px rgba(139, 92, 246, 0.5), 0 0 35px rgba(109, 40, 217, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.3); border-color: #a78bfa; }}
        57.12% {{ box-shadow: 0 0 20px rgba(245, 158, 11, 0.5), 0 0 35px rgba(217, 119, 6, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.3); border-color: #fbbf24; }}
        71.40% {{ box-shadow: 0 0 20px rgba(251, 146, 60, 0.5), 0 0 35px rgba(234, 88, 12, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.3); border-color: #fb923c; }}
        85.68% {{ box-shadow: 0 0 20px rgba(248, 113, 113, 0.5), 0 0 35px rgba(239, 68, 68, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.3); border-color: #f87171; }}
        100% {{ box-shadow: 0 0 15px rgba(16, 185, 129, 0.4), 0 0 30px rgba(5, 150, 105, 0.3), inset 0 0 15px rgba(255, 255, 255, 0.2); border-color: #34d399; }}
    }}
    .electric-box {{
        background: linear-gradient(135deg, #064e3b 0%, #065f46 50%, #0f766e 100%);
        color: #ffffff;
        width: 100%;
        max-width: 100%;
        padding: 14px 40px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 20px;
        font-family: 'Cairo', sans-serif;
        box-sizing: border-box;
        border: 2px solid #34d399;
        animation: electricMultiGlow 8s infinite ease-in-out;
    }}
    </style>
    <div class="electric-box">
        <div style="display: flex; justify-content: center; align-items: center; gap: 8px; margin-bottom: 2px;">
            <span style="font-size: 24px;">🪱🔬🐌💊</span>
        </div>
        <div style="font-size: 19px; color: #ffffff; font-weight: 900; line-height: 1.3; margin-bottom: 4px; word-wrap: break-word;">مرحباً بك في بوابة تقييم واختبار العاملين بالأمراض المتوطنة</div>
        <div style="display: flex; justify-content: center; align-items: center; gap: 12px; flex-wrap: wrap;">
            <span style="font-size: 12px; font-weight: bold; background: rgba(255,255,255,0.2); color: #ffffff; padding: 2px 10px; border-radius: 12px;">System V1.0</span>
            <span id="live-clock-display" style="font-size: 13px; font-weight: bold; color: #e2e8f0;">جاري تحميل الوقت...</span>
        </div>
    </div>
    <script>
    function updateLiveClock() {{
        const options = {{ timeZone: 'Africa/Cairo', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }};
        const formatter = new Intl.DateTimeFormat('ar-EG', options);
        try {{
            document.getElementById('live-clock-display').innerHTML = "" + formatter.format(new Date()) + "";
        }} catch(e) {{
            document.getElementById('live-clock-display').innerHTML = "" + new Date().toLocaleString() + "";
        }}
    }}
    updateLiveClock();
    setInterval(updateLiveClock, 1000);
    </script>
    """
    components.html(header_html, height=155, scrolling=False)

def verification_portal_view():
    header()
    st.markdown("### 🔍 صفحة التحقق الرقمي من صحة الشهادات والبيانات الواردة")
    st.info("يمكنك إدخال رقم الشهادة أو كود التحقق يدوياً، أو رفع صورة QR Code للشهادة للتحقق الفوري منها.")
    uploaded_qr_img = st.file_uploader("📥 رفع صورة QR Code للشهادة:", type=["png", "jpg", "jpeg"])
    if uploaded_qr_img is not None:
        try:
            from PIL import Image as PILImage
            img_pil = PILImage.open(uploaded_qr_img)
            st.image(img_pil, caption="صورة QR Code المرفوعة", width=200)
            st.success("✅ تم استلام صورة الرمز بنجاح. إذا لم يتم التعرف عليه تلقائياً، يرجى كتابة كود الشهادة في الحقل أدناه.")
        except Exception as e:
            st.error(f"عذراً، لم نتمكن من قراءة صورة الرمز: {e}")
    search_cert_code = st.text_input("أدخل رقم الشهادة أو كود التحقق (مثل: ELX-000001):", value=st.session_state.get("scanned_cert_code", ""))
    cert_to_verify = None
    if search_cert_code.strip():
        cert_code_clean = search_cert_code.strip().upper()
        with db() as c:
            cert_to_verify = c.execute("""SELECT s.*, t.name trainee_name, t.facility, t.profession trainee_profession, e.name template_name, e.exam_type FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE (s.certificate_id LIKE ? OR s.id=?) AND t.hidden=0""", (f"%{cert_code_clean}%", cert_code_clean.replace("ELX-", "").lstrip("0") or "0")).fetchone()
        if cert_to_verify:
            r = cert_to_verify
            status_str = "معتمدة وصحيحة بنسبة 100%" if r["passed"] else "غير اجتياز / غير معتمدة"
            score_val, max_score_val, percent_val = r["score"] or 0, r["max_score"] or 0, r["percent"] or 0.0
            st.markdown(f"""
            <div style="background: #f0fdf4; border: 2px solid #059669; padding: 20px; border-radius: 12px; margin-top: 15px;">
                <h3 style="color: #065f46; margin-top: 0;">✅ نتيجة التحقق وصحة البيانات الواردة:</h3>
                <p style="font-size: 11pt; color: #111827; line-height: 1.6;">
                    👤 <b>اسم المتدرب:</b> {esc(r['trainee_name'])}<br>
                    🩺 <b>الوظيفة / التخصص:</b> {esc(r['trainee_profession'] if r['trainee_profession'] is not None else '')}<br>
                    🏥 <b>جهة العمل والمنشأة:</b> {esc(r['facility'])}<br>
                    📋 <b>اسم الاختبار:</b> {esc(r['template_name'] or 'اختبار معتمد')} ({esc(r['exam_type'] or 'قبل التدريب')})<br>
                    📊 <b>الدرجة والنسبة المئوية:</b> {score_val} / {max_score_val} ({percent_val:.1f}%)<br>
                    🏷 <b>حالة الاعتماد:</b> <b style="color: {'green' if r['passed'] else 'red'};">{status_str}</b><br>
                    🔖 <b>رقم الشهادة الرسمي:</b> <span style="font-weight: bold; color: #065f46;">{r['certificate_id']}</span><br>
                    ⏰ <b>تاريخ إصدار الاعتماد:</b> {r['submitted_at'] or r['started_at']}
                </p>
            </div>
            """, unsafe_allow_html=True)
            verification_doc_html = f"""
            <!DOCTYPE html>
            <html lang="ar" dir="rtl">
            <head>
            <meta charset="UTF-8">
            <style>
            @page {{ size: A4 auto; margin: 15mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0; padding: 10mm; direction: rtl; -webkit-print-color-adjust: exact; }}
            .doc-wrapper {{ max-width: 200mm; margin: auto; border: 3px double #059669; padding: 15mm; border-radius: 10mm; position: relative; }}
            h2 {{ text-align: center; color: #047857; margin-bottom: 5px; }}
            .meta-table {{ width: 100%; border-collapse: collapse; margin-top: 15mm; font-size: 11pt; }}
            .meta-table th, .meta-table td {{ border: 1px solid #cbd5e1; padding: 8px 12px; text-align: right; }}
            .meta-table th {{ background-color: #059669; color: white; }}
            </style>
            </head>
            <body>
            <div class="doc-wrapper">
                <h2>وثيقة إثبات صحة البيانات والاعتماد الرسمي</h2>
                <div style="text-align: center; font-size: 9pt; color: #6b7280; margin-bottom: 15mm;">صادر عن نظام تقييم واختبار العاملين بالأمراض المتوطنة</div>
                <table class="meta-table">
                    <tr><th>اسم المتدرب</th><td>{esc(r['trainee_name'])}</td></tr>
                    <tr><th>الوظيفة / التخصص</th><td>{esc(r['trainee_profession'] if r['trainee_profession'] is not None else '')}</td></tr>
                    <tr><th>جهة العمل</th><td>{esc(r['facility'])}</td></tr>
                    <tr><th>اسم الاختبار</th><td>{esc(r['template_name'] or 'اختبار معتمد')} ({esc(r['exam_type'] or 'قبل التدريب')})</td></tr>
                    <tr><th>النتيجة والنسبة</th><td>{score_val} / {max_score_val} ({percent_val:.1f}%)</td></tr>
                    <tr><th>حالة التحقق</th><td style="color: green; font-weight: bold;">{status_str}</td></tr>
                    <tr><th>رقم الشهادة</th><td><span style="font-weight: bold; color: #065f46;">{r['certificate_id']}</span></td></tr>
                    <tr><th>تاريخ الاعتماد</th><td>{r['submitted_at'] or r['started_at']}</td></tr>
                </table>
            </div>
            </body>
            </html>
            """
            st.markdown("<br>", unsafe_allow_html=True)
            render_print_button_only(verification_doc_html, f"توثيق صحة شهادة {r['certificate_id']}")
        elif search_cert_code.strip():
            st.warning("⚠ عذراً، لم نتمكن من العثور على شهادة بهذا الكود. تأكد من صحة رقم الشهادة.")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("العودة لتسجيل الدخول / الرئيسية"):
        st.session_state.show_verification_portal = False
        st.rerun()

def _reset_reg_admin_and_facility():
    st.session_state["reg_administration"] = "-- اختر الإدارة --"
    st.session_state["reg_facility"] = "-- اختر المنشأة --"

def _reset_reg_facility():
    st.session_state["reg_facility"] = "-- اختر المنشأة --"

def _reset_hier_admin_and_facility():
    st.session_state["hier_manage_administration"] = "-- اختر الإدارة --"
    st.session_state["hier_manage_facility"] = "-- اختر المنشأة --"

def _reset_hier_facility():
    st.session_state["hier_manage_facility"] = "-- اختر المنشأة --"

def login_portal():
    header()
    col_v_btn1, col_v_btn2 = st.columns([3, 1])
    with col_v_btn2:
        if st.button("🔍 التحقق من شهادة (QR)", use_container_width=True):
            st.session_state.show_verification_portal = True
            st.rerun()

    hier_data = get_hierarchical_data(include_hidden=False)
    print_st = get_print_settings()
    professions_list = print_st.get("professions_list", ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"])

    reg_tab, exam_tab = st.tabs(["📝 تسجيل لأول مرة", "🔐 التسجيل ودخول الامتحان"])

    with reg_tab:
        st.markdown("### 📝 تسجيل الممتحن لأول مرة")
        st.info("أدخل بياناتك مرة واحدة. بعد إرسال الطلب سيظهر للإدارة في قسم **قبول تسجيل الجدد**، ولا يمكن دخول الامتحان قبل اعتماد التسجيل.")
        st.markdown("##### 📍 الجهة الإدارية التابع لها:")
        st.text_input("جمهورية مصر العربية", value="جمهورية مصر العربية", disabled=True, key="reg_country_fixed")
        st.text_input("وزارة الصحة والسكان", value="وزارة الصحة والسكان", disabled=True, key="reg_ministry_fixed")
        if not hier_data:
            st.warning("⚠ لا توجد بيانات مسجلة في الهيكل الإداري حالياً. يرجى إضافتها من لوحة التحكم أولاً.")
            facility_final_str = ""
        else:
            auths_list = sorted({str(item.get("authority") or "").strip() for item in hier_data if str(item.get("authority") or "").strip()})
            sel_auth = st.selectbox("المديرية / الجهة:", ["-- اختر المديرية / الجهة --"] + auths_list, key="reg_authority", on_change=_reset_reg_admin_and_facility)
            rows_auth = [item for item in hier_data if sel_auth != "-- اختر المديرية / الجهة --" and str(item.get("authority") or "").strip() == sel_auth]
            admins_list = sorted({str(item.get("administration") or "").strip() for item in rows_auth if str(item.get("administration") or "").strip()})
            sel_admin = st.selectbox("الإدارة:", ["-- اختر الإدارة --"] + admins_list, key="reg_administration", disabled=not bool(rows_auth), on_change=_reset_reg_facility)
            rows_admin = [item for item in rows_auth if sel_admin != "-- اختر الإدارة --" and str(item.get("administration") or "").strip() == sel_admin]
            facilities_list = sorted({str(item.get("facility_name") or "").strip() for item in rows_admin if str(item.get("facility_name") or "").strip()})
            sel_fac = st.selectbox("المنشأة / وحدة الأمراض المتوطنة:", ["-- اختر المنشأة --"] + facilities_list, key="reg_facility", disabled=not bool(rows_admin))
            facility_final_str = f"جمهورية مصر العربية - وزارة الصحة والسكان - {sel_auth} - {sel_admin} - {sel_fac}" if sel_auth != "-- اختر المديرية / الجهة --" and sel_admin != "-- اختر الإدارة --" and sel_fac != "-- اختر المنشأة --" else ""
        with st.form("trainee_first_registration"):
            name = st.text_input("الاسم الرباعي:")
            national_id = st.text_input("الرقم القومي:", max_chars=14, help="يجب أن يكون 14 رقماً.")
            phone = st.text_input("رقم الهاتف:", help="رقم الهاتف هو المعرف الرئيسي والفريد بعد اعتماد التسجيل.")
            selected_profession = st.selectbox("الوظيفة / التخصص:", professions_list)
            work_start_date = st.date_input(
                "📅 تاريخ استلام العمل:",
                value=now_cairo().date(),
                max_value=now_cairo().date(),
                format="DD/MM/YYYY",
                help="اختر تاريخ استلام العمل الفعلي."
            )
            if st.form_submit_button("📨 إرسال طلب التسجيل", use_container_width=True):
                digits_nid = normalize_national_id(national_id)
                phone_norm = normalize_egyptian_phone(phone)
                if not facility_final_str:
                    st.warning("⚠ يرجى استكمال اختيار الهيكل الإداري بالكامل.")
                elif not name.strip() or not phone_norm or not digits_nid:
                    st.warning("⚠ يرجى إدخال الاسم والرقم القومي ورقم الهاتف.")
                elif not is_valid_egyptian_national_id(digits_nid):
                    st.warning("⚠ الرقم القومي غير صحيح. تأكد من 14 رقماً وتاريخ الميلاد وكود المحافظة.")
                elif not is_valid_egyptian_mobile(phone_norm):
                    st.warning("⚠ أدخل رقم موبايل مصري صحيحاً مثل 01012345678 أو +201012345678.")
                elif phone_exists(phone_norm):
                    st.error("❌ رقم الهاتف مستخدم بالفعل لممتحن مسجل. رقم الهاتف يجب أن يكون فريداً.")
                else:
                    with db() as c:
                        nid_exists = c.execute("SELECT 1 FROM trainees WHERE national_id=? LIMIT 1", (digits_nid,)).fetchone()
                    if nid_exists:
                        st.error("❌ الرقم القومي مستخدم بالفعل في تسجيل سابق.")
                    else:
                        try:
                            tid = create_trainee(
                                facility_final_str, name, phone_norm, digits_nid,
                                selected_profession, None, work_start_date.isoformat()
                            )
                            st.success(f"✅ تم إرسال طلب التسجيل بنجاح. رقم الطلب: {tid}. انتظر اعتماد الإدارة.")
                        except ValueError as e:
                            msg = {"DUPLICATE_TRAINEE_PHONE": "رقم الهاتف مستخدم بالفعل.", "DUPLICATE_TRAINEE_NATIONAL_ID": "الرقم القومي مستخدم بالفعل.", "INVALID_TRAINEE_PHONE": "رقم الموبايل المصري غير صحيح.", "INVALID_TRAINEE_NATIONAL_ID": "الرقم القومي غير صحيح."}.get(str(e), str(e))
                            st.error("❌ " + msg)

    with exam_tab:
        st.markdown("### 🔐 التسجيل ودخول الامتحان")
        st.info("بعد اعتماد تسجيلك من الإدارة، أدخل **رقم الهاتف والرقم القومي** المسجلين لطلب دخول الامتحان.")
        with st.form("trainee_phone_login"):
            phone_login = st.text_input("رقم الهاتف:", placeholder="مثال: 01012345678 أو +201012345678")
            nid_login = st.text_input("الرقم القومي:", max_chars=14, placeholder="أدخل الرقم القومي المسجل")
            if st.form_submit_button("🚪 التحقق وطلب دخول الامتحان", use_container_width=True):
                tr = trainee_by_phone_and_national_id(phone_login, nid_login)
                if not tr:
                    st.error("❌ بيانات الدخول غير متطابقة مع تسجيل معتمد. راجع رقم الهاتف والرقم القومي.")
                elif not tr.get("assigned_template_id"):
                    st.warning("⏳ تم اعتماد التسجيل، لكن لم يتم تخصيص نموذج امتحان لك بعد.")
                else:
                    with db() as c:
                        login_tpl = c.execute("SELECT * FROM exam_templates WHERE id=? AND active=1", (tr["assigned_template_id"],)).fetchone()
                    if not login_tpl:
                        st.warning("⏳ نموذج الاختبار المخصص لك غير متاح حالياً. يرجى مراجعة الإدارة.")
                    elif not template_matches_profession(dict(login_tpl), tr.get("profession", "")):
                        st.error(f"❌ نموذج الاختبار المحدد غير مخصص لمهنتك ({tr.get('profession') or 'غير محددة'}). يرجى مراجعة الإدارة لتخصيص النموذج الصحيح.")
                    else:
                        st.session_state.trainee_id = tr["id"]
                        st.session_state.trainee_name = tr["name"]
                        st.success("✅ تم التحقق من رقم الهاتف والرقم القومي بنجاح. جاري الانتقال إلى الامتحان...")
                        st.rerun()

    with st.expander("🔐 تسجيل دخول الإدارة"):
        with st.form("admin_login_form_hidden"):
            u = st.text_input("اسم المستخدم", value="")
            p = st.text_input("كلمة المرور", type="password", value="")
            if st.form_submit_button("دخول لوحة التحكم", use_container_width=True):
                user = login_user(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.role = user["role"]
                    try:
                        stored_permissions = json.loads(user["permissions_json"]) if user["permissions_json"] else []
                    except:
                        stored_permissions = []
                    # المالك لا يعتمد على permissions_json للوصول؛ جميع الوحدات متاحة له دائماً.
                    st.session_state.permissions = list(ALL_MENU_MODULES.keys()) if user["role"] == "admin" else stored_permissions
                    st.rerun()
                else:
                    st.error("بيانات الدخول غير صحيحة.")

def is_owner():
    """المالك/مدير النظام يمتلك صلاحية عليا على جميع أجزاء البرنامج."""
    return str(st.session_state.get("role", "")).strip().lower() == "admin"

def has_permission(module_key):
    """فحص مركزي للصلاحيات: المالك يتجاوز أي قائمة صلاحيات محفوظة."""
    if is_owner():
        return True
    perms = st.session_state.get("permissions") or []
    return module_key in perms

def require_permission(module_key):
    """منع الوصول المباشر لأي قسم عند عدم امتلاك الصلاحية."""
    if has_permission(module_key):
        return True
    st.error("⛔ ليس لديك صلاحية للوصول إلى هذا القسم.")
    return False

def admin_dashboard():
    header()
    c_info, c_btn = st.columns([4, 1])
    with c_info:
        st.write(f"**المستخدم:** {st.session_state.username} | **الصلاحية:** {ROLES.get(st.session_state.role, '')}")
    with c_btn:
        if st.button("تسجيل الخروج", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.session_state.permissions = []
            st.rerun()
    all_modules_list = list(ALL_MENU_MODULES.keys())
    # المالك يرى كل أجزاء النظام دائماً، حتى لو كانت permissions_json قديمة أو ناقصة.
    if is_owner():
        available_menus = all_modules_list
    else:
        available_menus = [m for m in all_modules_list if has_permission(m)]
    if not available_menus:
        st.warning("⚠ لا توجد صلاحيات مصرحة.")
        return
    st.markdown("### 📌 لوحة المؤشرات وأقسام الإدارة:")
    cols_per_row = 3
    menu_keys = available_menus
    for i in range(0, len(menu_keys), cols_per_row):
        row_cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(menu_keys):
                m_key = menu_keys[i + j]
                is_active = (st.session_state.active_admin_tab == m_key)
                button_label = f"📍 {m_key}" if is_active else m_key
                with row_cols[j]:
                    if st.button(button_label, use_container_width=True, key=f"btn_menu_{i+j}"):
                        st.session_state.active_admin_tab = m_key
                        st.rerun()
    selected_menu = st.session_state.active_admin_tab
    st.markdown("---")
    


    if selected_menu == "📊 لوحة التحكم":
        st.subheader("📊 لوحة المؤشرات العامة والتحليلات الشاملة للأمراض المتوطنة")
        with db() as c:
            cnts = c.execute("""SELECT 
                (SELECT COUNT(*) FROM trainees WHERE hidden=0) tr,
                (SELECT COUNT(*) FROM trainees WHERE status='pending' AND hidden=0) pend,
                (SELECT COUNT(*) FROM trainees WHERE status='approved' AND hidden=0) appr,
                (SELECT COUNT(*) FROM trainees WHERE status='completed' AND hidden=0) comp,
                (SELECT COUNT(*) FROM questions WHERE active=1) qs,
                (SELECT COUNT(*) FROM exam_templates WHERE active=1) tpls,
                (SELECT COUNT(*) FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.status='submitted' AND t.hidden=0) ex,
                (SELECT COALESCE(AVG(s.percent),0) FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.status='submitted' AND t.hidden=0) avgp,
                (SELECT COUNT(*) FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.status='submitted' AND s.passed=1 AND t.hidden=0) passed_cnt,
                (SELECT COUNT(*) FROM hierarchical_facilities WHERE hidden=0) facs_cnt
            """).fetchone()
        total_tr = cnts["tr"] or 1
        passed_cnt = cnts["passed_cnt"] or 0
        pass_ratio = (passed_cnt / total_tr) * 100
        st.markdown("##### 🚀 المؤشرات الرئيسية (KPIs):")
        cols = st.columns(5)
        metrics_data = [
            ("إجمالي المتدربين", cnts["tr"]),
            ("الطلبات المعلقة", cnts["pend"]),
            ("المتدربين المعتمدين", cnts["appr"]),
            ("الاختبارات المكتملة", cnts["comp"]),
            ("بنك الأسئلة الشامل", cnts["qs"])
        ]
        for box, (l, v) in zip(cols, metrics_data):
            box.markdown(f'<div class="metric"><div class="v">{v}</div><div class="l">{l}</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        cols_sub = st.columns(4)
        sub_metrics = [
            ("النماذج المتاحة", cnts["tpls"]),
            ("الوحدات الصحية", cnts["facs_cnt"]),
            ("متوسط النسبة العام", f"{cnts['avgp']:.1f}%"),
            ("نسبة النجاح العامة", f"{pass_ratio:.1f}%")
        ]
        for box, (l, v) in zip(cols_sub, sub_metrics):
            box.markdown(f'<div class="metric"><div class="v">{v}</div><div class="l">{l}</div></div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("### 📈 تحليلات إضافية وتفصيلية:")
        tab_db_1, tab_db_2, tab_db_3 = st.tabs(["👥 تحليل التخصصات والوظائف", "🏥 توزيع وحدات الأمراض المتوطنة", "📚 تفاصيل بنك الأسئلة والصعوبة"])
        with tab_db_1:
            with db() as c:
                df_prof_analysis = pd.read_sql_query("""
                    SELECT profession AS 'الوظيفة / التخصص', COUNT(id) AS 'إجمالي العاملين',
                           SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS 'المكتملين للاختبار',
                           SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS 'قيد الانتظار'
                    FROM trainees WHERE hidden=0 GROUP BY profession ORDER BY COUNT(id) DESC
                """, c)
            if df_prof_analysis.empty:
                st.info("لا توجد بيانات متدربين مسجلة لتحليلها.")
            else:
                st.dataframe(df_prof_analysis, use_container_width=True, hide_index=True)
        with tab_db_2:
            with db() as c:
                df_fac_analysis = pd.read_sql_query("""
                    SELECT t.facility AS 'وحدة الأمراض المتوطنة / المنشأة', COUNT(t.id) AS 'عدد العاملين',
                           SUM(CASE WHEN s.passed=1 THEN 1 ELSE 0 END) AS 'عدد المجتازين',
                           COALESCE(AVG(s.percent), 0) AS 'متوسط نسبة النجاح %'
                    FROM trainees t LEFT JOIN exam_sessions s ON s.trainee_id=t.id AND s.status='submitted'
                    WHERE t.hidden=0 GROUP BY t.facility ORDER BY COUNT(t.id) DESC
                """, c)
            if df_fac_analysis.empty:
                st.info("لا توجد بيانات منشآت مسجلة.")
            else:
                st.dataframe(df_fac_analysis, use_container_width=True, hide_index=True)
        with tab_db_3:
            with db() as c:
                df_q_analysis = pd.read_sql_query("""
                    SELECT difficulty AS 'مستوى الصعوبة', category AS 'المجال / القسم', COUNT(id) AS 'عدد الأسئلة'
                    FROM questions WHERE active=1 GROUP BY difficulty, category ORDER BY COUNT(id) DESC
                """, c)
                df_q_category = pd.read_sql_query("""
                    SELECT COALESCE(NULLIF(TRIM(category), ''), 'غير مصنف') AS 'التصنيف / القسم',
                           COUNT(id) AS 'عدد الأسئلة'
                    FROM questions
                    WHERE active=1
                    GROUP BY COALESCE(NULLIF(TRIM(category), ''), 'غير مصنف')
                    ORDER BY COUNT(id) DESC, 'التصنيف / القسم' ASC
                """, c)
            if df_q_analysis.empty:
                st.info("بنك الأسئلة فارغ حالياً.")
            else:
                st.markdown("#### 📚 توزيع بنك الأسئلة حسب مستوى الصعوبة والتصنيف:")
                st.dataframe(df_q_analysis, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("#### 🗂️ عدد الأسئلة في كل تصنيف داخل بنك الأسئلة:")
                st.caption("يتم الحساب من الأسئلة النشطة فقط، مع تجميع كل الأسئلة التي تحمل نفس اسم التصنيف.")

                total_category_questions = int(df_q_category['عدد الأسئلة'].sum())
                category_count = len(df_q_category)
                c1, c2 = st.columns(2)
                c1.metric("إجمالي الأسئلة المصنفة", total_category_questions)
                c2.metric("عدد التصنيفات", category_count)

                st.dataframe(df_q_category, use_container_width=True, hide_index=True)


    elif selected_menu == "👥 إدارة المهن والوظائف":
        st.subheader("👥 إدارة الوظائف والتخصصات بالأمراض المتوطنة (مع إمكانية الحذف)")
        st.info("💡 يمكنك من هنا إضافة وظيفة أو تخصص جديد أو حذف تخصص موجود، واستعراض توزيع العاملين حسب وظائفهم.")
        curr_p_set = get_print_settings()
        current_prof_list = curr_p_set.get("professions_list", [])
        col_add_prof, col_list_prof = st.columns(2)
        with col_add_prof:
            with st.form("add_new_profession_form"):
                st.markdown("#### ➕ إضافة وظيفة أو تخصص جديد:")
                new_prof_input = st.text_input("اسم الوظيفة أو التخصص:", value="")
                if st.form_submit_button("💾 حفظ وإضافة الوظيفة", use_container_width=True):
                    clean_p = new_prof_input.strip()
                    if clean_p:
                        if clean_p not in current_prof_list:
                            current_prof_list.append(clean_p)
                            save_print_settings(
                                curr_p_set["header_text"], curr_p_set["margin_top"], curr_p_set["margin_bottom"],
                                curr_p_set["margin_right"], curr_p_set["margin_left"], curr_p_set.get("line_spacing", 1.25),
                                curr_p_set["logo_base64"], curr_p_set.get("logo2_base64", ""), curr_p_set.get("logo3_base64", ""),
                                curr_p_set.get("bg_base64", ""), curr_p_set.get("frame_base64", ""),
                                curr_p_set["default_cert_title"], curr_p_set["default_cert_notes"],
                                curr_p_set["trainee_prefix"], curr_p_set["trainee_title"], curr_p_set["trainee_profession"], current_prof_list
                            )
                            st.success(f"✅ تمت إضافة الوظيفة ({clean_p}) بنجاح للقائمة المنسدلة!")
                            st.rerun()
                        else:
                            st.warning("⚠ هذه الوظيفة موجودة مسبقاً في القائمة.")
                    else:
                        st.warning("الرجاء إدخال اسم الوظيفة.")
        with col_list_prof:
            with st.form("delete_profession_form"):
                st.markdown("#### 🗑 حذف وظيفة من القائمة:")
                sel_del_prof = st.selectbox("اختر الوظيفة للحذف:", ["-- اختر الوظيفة --"] + current_prof_list)
                if st.form_submit_button("حذف الوظيفة المحددة", use_container_width=True):
                    if sel_del_prof != "-- اختر الوظيفة --":
                        if sel_del_prof in current_prof_list:
                            current_prof_list.remove(sel_del_prof)
                            save_print_settings(
                                curr_p_set["header_text"], curr_p_set["margin_top"], curr_p_set["margin_bottom"],
                                curr_p_set["margin_right"], curr_p_set["margin_left"], curr_p_set.get("line_spacing", 1.25),
                                curr_p_set["logo_base64"], curr_p_set.get("logo2_base64", ""), curr_p_set.get("logo3_base64", ""),
                                curr_p_set.get("bg_base64", ""), curr_p_set.get("frame_base64", ""),
                                curr_p_set["default_cert_title"], curr_p_set["default_cert_notes"],
                                curr_p_set["trainee_prefix"], curr_p_set["trainee_title"], curr_p_set["trainee_profession"], current_prof_list
                            )
                            st.success(f"✅ تم حذف الوظيفة ({sel_del_prof}) بنجاح!")
                            st.rerun()
                    else:
                        st.warning("الرجاء اختيار وظيفة صحيحة للحذف.")
            st.markdown("#### 📋 القائمة الحالية للوظائف المتاحة:")
            for idx, p_name in enumerate(current_prof_list, start=1):
                st.write(f"{idx}. {p_name}")
        st.markdown("---")
        st.markdown("#### 📊 تقسيم وإحصائيات العاملين والممتحنين حسب التخصصات:")
        with db() as c:
            df_prof_stats = pd.read_sql_query("""
                SELECT profession AS 'الوظيفة / التخصص', COUNT(id) AS 'إجمالي العاملين',
                       SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS 'المكتملين للاختبار'
                FROM trainees WHERE hidden=0 GROUP BY profession ORDER BY COUNT(id) DESC
            """, c)
        if df_prof_stats.empty:
            st.info("لا توجد بيانات متدربين مسجلة حتى الآن.")
        else:
            df_prof_stats.columns = ["الوظيفة / التخصص", "إجمالي العاملين", "المكتملين للاختبار"]
            st.dataframe(df_prof_stats, use_container_width=True, hide_index=True)
            out_prof_bytes = io.BytesIO()
            with pd.ExcelWriter(out_prof_bytes, engine='openpyxl') as writer:
                df_prof_stats.to_excel(writer, index=False, sheet_name='ProfessionsBreakdown')
            st.download_button("📥 تحميل تقرير وتوزيع التخصصات (.xlsx)", data=out_prof_bytes.getvalue(), file_name="professions_breakdown.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    elif selected_menu == "🖨 ضبط اعدادات الطباعة و الهوامش":
        st.subheader("🖨 ضبط إعدادات الطباعة للتقارير العامة (الهوامش تلقائية)")
        current_set = get_print_settings()
        with st.form("print_settings_form"):
            header_text_val = st.text_area("نص ترويسة الجهة العامة (أعلى يمين التقارير):", value=current_set.get("header_text", "جمهورية مصر العربية"))
            st.info("📐 تم ضبط هوامش الطباعة تلقائياً حسب مقاس A4، ولا تحتاج إلى تعديل يدوي.")
            line_spacing_val = st.number_input("المسافة بين الأسطر:", min_value=0.8, max_value=3.0, value=float(current_set.get("line_spacing", 1.25)), step=0.05)
            st.markdown("#### 🖼 رفع الصور والشعارات لترويسة التقارير:")
            col_logo1, col_logo2, col_logo3 = st.columns(3)
            with col_logo1:
                uploaded_logo1 = st.file_uploader("الشعار الأول (أعلى يمين - 1):", type=["png", "jpg", "jpeg"], key="rep_logo1")
                remove_logo1 = st.checkbox("حذف الشعار الأول", key="rep_rem1")
            with col_logo2:
                uploaded_logo2 = st.file_uploader("الشعار الثاني (أعلى يمين - 2):", type=["png", "jpg", "jpeg"], key="rep_logo2")
                remove_logo2 = st.checkbox("حذف الشعار الثاني", key="rep_rem2")
            with col_logo3:
                uploaded_logo3 = st.file_uploader("الشعار الثالث (أعلى يسار التقرير):", type=["png", "jpg", "jpeg"], key="rep_logo3")
                remove_logo3 = st.checkbox("حذف الشعار الثالث", key="rep_rem3")
            
            current_logo1_val = current_set["logo_base64"]
            if remove_logo1:
                current_logo1_val = DEFAULT_LOGO
            elif uploaded_logo1 is not None:
                current_logo1_val = f"data:image/{uploaded_logo1.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo1.read()).decode("utf-8")
            
            current_logo2_val = current_set.get("logo2_base64", "")
            if remove_logo2:
                current_logo2_val = ""
            elif uploaded_logo2 is not None:
                current_logo2_val = f"data:image/{uploaded_logo2.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo2.read()).decode("utf-8")
            
            current_logo3_val = current_set.get("logo3_base64", "")
            if remove_logo3:
                current_logo3_val = ""
            elif uploaded_logo3 is not None:
                current_logo3_val = f"data:image/{uploaded_logo3.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo3.read()).decode("utf-8")
            
            if st.form_submit_button("💾 حفظ ضبط اعدادات الطباعة و الهوامش", use_container_width=True):
                save_print_settings(
                    header_text_val, "12mm", "auto", "8mm", "8mm", line_spacing_val,
                    current_logo1_val, current_logo2_val, current_logo3_val,
                    current_set.get("bg_base64", ""), current_set.get("frame_base64", ""),
                    current_set["default_cert_title"], current_set["default_cert_notes"],
                    current_set["trainee_prefix"], current_set["trainee_title"], current_set["trainee_profession"],
                    current_set.get("professions_list", [])
                )
                st.success("✅ تم حفظ ضبط اعدادات الطباعة و الهوامش بنجاح!")
                st.rerun()

    elif selected_menu == "🎨 إعدادات الشهادات المخصصة":
        st.subheader("🎨 صفحة إدارة وضبط الشهادات المخصصة وطباعتها")
        cert_sub_tab1, cert_sub_tab2 = st.tabs([
            "⚙ إعدادات وتصميم الشهادة",
            "🖨 طباعة الشهادات بناءً على التقارير (فرد / منشأة)"
        ])
        with cert_sub_tab1:
            st.info("💡 هذه الصفحة مخصصة بالكامل لضبط تصميم الشهادة، الألقاب، المسافات، الخلفية، والشعارات بمعزل عن باقي التقارير.")
            current_set = get_print_settings()
            professions_options_list = current_set.get("professions_list", [
                "أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"
            ])
            with st.form("dedicated_certificate_settings_form"):
                st.markdown("#### 🏷️ إعدادات الألقاب والوظيفة في الشهادة:")
                col_p1, col_p2, col_p3 = st.columns(3)
                with col_p1:
                    trainee_prefix_val = st.text_input("1. البادئة قبل الاسم (مثل: الزميل / الأستاذ):", value=current_set.get("trainee_prefix", ""))
                with col_p2:
                    trainee_title_val = st.text_input("2. اللقب (يظهر أمام الاسم مباشرة):", value=current_set.get("trainee_title", "دكتور"))
                with col_p3:
                    curr_prof = current_set.get("trainee_profession", "أخصائي الأمراض المتوطنة")
                    prof_idx = professions_options_list.index(curr_prof) if curr_prof in professions_options_list else 0
                    trainee_profession_val = st.selectbox("3. اختيار الوظيفة الافتراضية للشهادات:", professions_options_list, index=prof_idx)
                cert_trainee_extra_val = st.text_input(
                    "4. نص إضافي لشهادة المتدرب (يظهر بعد سطر الوظيفة والمنشأة):",
                    value=current_set.get("cert_trainee_extra", ""),
                    placeholder="مثال: أتم حضور الدورة التدريبية بنجاح"
                )
                cert_facility_extra_val = st.text_input(
                    "5. نص إضافي لشهادة المنشأة (يظهر بعد سطر اسم المنشأة):",
                    value=current_set.get("cert_facility_extra", ""),
                    placeholder="مثال: اجتازت المنشأة متطلبات التقييم"
                )
                cert_facility_section_val = st.text_input(
                    "6. تصنيف القسم في شهادة المنشأة (يظهر قبل اسم المنشأة):",
                    value=current_set.get("cert_facility_section", ""),
                    placeholder="مثال: قسم المتوطنة"
                )
                st.markdown("#### 📐 التحكم بالمسافات بين الأسطر وتخطيط الشهادة:")
                line_spacing_val = st.number_input("المسافة بين الأسطر داخل الشهادة:", min_value=0.8, max_value=3.0, value=float(current_set.get("line_spacing", 1.25)), step=0.05)
                cert_box_inset_val = st.number_input(
                    "📐 حجم مربع محتوى الشهادة داخل صورة الخلفية (المسافة من الإطار):",
                    min_value=4.0, max_value=35.0,
                    value=float(str(current_set.get("cert_box_inset", "13mm")).replace("mm", "").strip() or 13),
                    step=0.5,
                    help="كلما زادت القيمة صغر مربع المحتوى وابتعد عن إطار الصورة. كلما قلت كبر مربع المحتوى واقترب من الإطار."
                )
                cert_box_inset_css = f"{cert_box_inset_val:g}mm"
                
                st.markdown("#### 🖼 شعارات الشهادات المخصصة:")
                col_logo1, col_logo2, col_logo3 = st.columns(3)
                with col_logo1:
                    uploaded_logo1 = st.file_uploader("الشعار الأول (أعلى يمين - 1):", type=["png", "jpg", "jpeg"], key="cert_logo1")
                    remove_logo1 = st.checkbox("حذف الشعار الأول", key="c_rem1")
                with col_logo2:
                    uploaded_logo2 = st.file_uploader("الشعار الثاني (أعلى يمين - 2):", type=["png", "jpg", "jpeg"], key="cert_logo2")
                    remove_logo2 = st.checkbox("حذف الشعار الثاني", key="c_rem2")
                with col_logo3:
                    uploaded_logo3 = st.file_uploader("الشعار الثالث (أعلى يسار الشهادة):", type=["png", "jpg", "jpeg"], key="cert_logo3")
                    remove_logo3 = st.checkbox("حذف الشعار الثالث", key="c_rem3")
                
                st.markdown("#### 🖼 خلفية الشهادة:")
                uploaded_bg = st.file_uploader("رفع خلفية الشهادة (صورة):", type=["png", "jpg", "jpeg"], key="cert_bg")
                remove_bg = st.checkbox("حذف الخلفية الحالية", key="c_rem_bg")
                
                current_logo1_val = current_set["logo_base64"]
                if remove_logo1:
                    current_logo1_val = DEFAULT_LOGO
                elif uploaded_logo1 is not None:
                    current_logo1_val = f"data:image/{uploaded_logo1.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo1.read()).decode("utf-8")
                
                current_logo2_val = current_set.get("logo2_base64", "")
                if remove_logo2:
                    current_logo2_val = ""
                elif uploaded_logo2 is not None:
                    current_logo2_val = f"data:image/{uploaded_logo2.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo2.read()).decode("utf-8")
                
                current_logo3_val = current_set.get("logo3_base64", "")
                if remove_logo3:
                    current_logo3_val = ""
                elif uploaded_logo3 is not None:
                    current_logo3_val = f"data:image/{uploaded_logo3.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo3.read()).decode("utf-8")
                
                current_bg_val = current_set.get("bg_base64", "")
                if remove_bg:
                    current_bg_val = ""
                elif uploaded_bg is not None:
                    current_bg_val = f"data:image/{uploaded_bg.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_bg.read()).decode("utf-8")
                
                current_frame_val = current_set.get("frame_base64", "")
                
                if st.form_submit_button("💾 حفظ إعدادات الشهادة المخصصة", use_container_width=True):
                    save_print_settings(
                        current_set["header_text"], current_set["margin_top"], "auto",
                        current_set["margin_right"], current_set["margin_left"], line_spacing_val,
                        current_logo1_val, current_logo2_val, current_logo3_val,
                        current_bg_val, current_frame_val,
                        current_set["default_cert_title"], current_set["default_cert_notes"],
                        trainee_prefix_val, trainee_title_val, trainee_profession_val, professions_options_list,
                        cert_box_inset_css, cert_trainee_extra_val, cert_facility_extra_val, cert_facility_section_val
                    )
                    st.success("✅ تم تحديث وحفظ ضبط الشهادات المخصصة بنجاح!")
                    st.rerun()

        with cert_sub_tab2:
            st.markdown("#### 🖨 طباعة الشهادات بناءً على التقارير")
            st.info("اختر طباعة شهادة فردية لمتدرب، أو شهادة تقييم للمنشأة بناءً على نتائج التقارير المعتمدة.")
            st.markdown("#### 🏥 تحديد نطاق الشهادات حسب الهيكل الإداري")
            cert_scope = hierarchy_scope_widget("نطاق الشهادات:", "cert_scope_v12")
            cert_scope_sql, cert_scope_args = hierarchy_scope_sql("h", cert_scope)
            with db() as c:
                all_facilities_list = [row[0] for row in c.execute(
                    f"SELECT DISTINCT t.facility FROM trainees t LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name) WHERE t.facility IS NOT NULL AND t.facility != '' AND t.hidden=0 AND {cert_scope_sql} ORDER BY t.facility",
                    tuple(cert_scope_args)
                ).fetchall()]
                sessions_full_list = c.execute("""SELECT s.id, t.name trainee_name, t.facility, t.profession trainee_profession,
                    s.score, s.max_score, s.percent, s.passed, e.name as tpl_name, e.exam_type
                    FROM exam_sessions s
                    JOIN trainees t ON t.id=s.trainee_id
                    LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name)
                    LEFT JOIN exam_templates e ON e.id=s.template_id
                    WHERE s.status='submitted' AND t.hidden=0 AND {cert_scope_sql} ORDER BY s.id DESC""".format(cert_scope_sql=cert_scope_sql), tuple(cert_scope_args)).fetchall()

            if not sessions_full_list:
                st.info("لا توجد اختبارات مكتملة أو معتمدة للمتدربين الظاهرين حتى الآن.")
            else:
                cert_print_type = st.radio(
                    "اختر نوع الشهادة:",
                    ["شهادة فردية (لمتدرب محدد)", "شهادة تقييم منشأة"],
                    horizontal=True
                )
                curr_sett = get_print_settings()

                if cert_print_type == "شهادة فردية (لمتدرب محدد)":
                    sess_choices = {
                        f"متدرب: {s['trainee_name']} | الوظيفة: {s['trainee_profession']} | الجهة: {s['facility']} | النتيجة: {s['percent']}%": s['id']
                        for s in sessions_full_list
                    }
                    sel_sess_lbl = st.selectbox("اختر المتدرب للطباعة الفردية:", list(sess_choices.keys()))
                    chosen_sid_val = sess_choices[sel_sess_lbl]
                    cert_html_ind = generate_customizable_certificate_html(
                        chosen_sid_val,
                        curr_sett.get("default_cert_title"),
                        None
                    )
                    render_print_button_only(cert_html_ind, f"شهادة متدرب رقم {chosen_sid_val}")

                else:
                    if not all_facilities_list:
                        st.info("لا توجد منشآت مسجلة.")
                    else:
                        sel_fac_print = st.selectbox("اختر المنشأة لإصدار شهادة تقييم لها:", all_facilities_list)
                        fac_filtered_sessions = [s for s in sessions_full_list if s['facility'] == sel_fac_print]
                        st.write(f"📊 عدد النتائج المعتمدة للمنشأة: **{len(fac_filtered_sessions)}**")
                        if fac_filtered_sessions:
                            facility_html = generate_facility_certificate_html(
                                sel_fac_print,
                                [s['id'] for s in fac_filtered_sessions],
                                "شهادة تقييم منشأة"
                            )
                            render_print_button_only(facility_html, f"شهادة تقييم منشأة {sel_fac_print}")
                        else:
                            st.warning("⚠ لا توجد نتائج معتمدة لهذه المنشأة.")

    elif selected_menu == "🏥 الهيكل الإداري":
        st.subheader("🏥 إدارة الهيكل الإداري لوحدات الأمراض المتوطنة (مديرية / جهة ⬅ إدارة ⬅ منشأة)")
        tab_h1, tab_h2, tab_h3 = st.tabs(["✍ إضافة يدوية", "📥 رفع الملفات", "📋 استعراض وإخفاء/إظهار/حذف"])
        with tab_h1:
            with st.form("manual_hierarchical_form"):
                st.markdown("##### 📌 الحقول الثابتة التابعة للجمهورية:")
                st.text_input("جمهورية مصر العربية", value="جمهورية مصر العربية", disabled=True, key="hier_country_fixed")
                st.text_input("وزارة الصحة والسكان", value="وزارة الصحة والسكان", disabled=True, key="hier_ministry_fixed")
                m_auth = st.text_input("المديرية / الجهة:", value="")
                m_admin = st.text_input("الإدارة:", value="")
                m_fac = st.text_input("المنشأة / وحدة الأمراض المتوطنة:", value="")
                if st.form_submit_button("💾 حفظ", use_container_width=True):
                    if m_auth.strip() and m_admin.strip() and m_fac.strip():
                        with db() as c:
                            exists = c.execute("SELECT 1 FROM hierarchical_facilities WHERE authority=? AND administration=? AND facility_name=? LIMIT 1", (m_auth.strip(), m_admin.strip(), m_fac.strip())).fetchone()
                            if not exists:
                                c.execute("INSERT INTO hierarchical_facilities(governorate,authority,center,administration,facility_name,created_at,hidden) VALUES(?,?,?,?,?,?,?)",
                                          ("", m_auth.strip(), "", m_admin.strip(), m_fac.strip(), now(), 0))
                        if exists:
                            st.warning("هذه المنشأة مسجلة بالفعل تحت الإدارة والمديرية المحددتين.")
                        else:
                            reindex_hierarchical_facilities()
                            st.success("✅ تمت الإضافة بنجاح وإعادة الترتيب!")
                            st.rerun()
                    else:
                        st.warning("أدخل المديرية / الجهة والإدارة واسم المنشأة.")
        with tab_h2:
            up_file = st.file_uploader("اختر ملف إكسيل أو CSV:", type=["xlsx", "xls", "csv"], key="hier_file_upload_v1_0")
            if up_file is not None:
                try:
                    df_up = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
                    if st.button("🚀 دمج وتحديث البيانات", use_container_width=True):
                        added_cnt = 0
                        with db() as c:
                            for _, r in df_up.iterrows():
                                auth = str(r.get("authority", r.get("المديرية / الجهة", r.get("الهيئة", "")))).strip()
                                adm = str(r.get("administration", r.get("الإدارة", ""))).strip()
                                fac = str(r.get("facility_name", r.get("المنشأة / وحدة الأمراض المتوطنة", r.get("المنشأة", r.get("وحدة الأمراض المتوطنة", ""))))).strip()
                                if auth and adm and fac:
                                    exists = c.execute("SELECT 1 FROM hierarchical_facilities WHERE authority=? AND administration=? AND facility_name=? LIMIT 1", (auth, adm, fac)).fetchone()
                                    if not exists:
                                        c.execute("INSERT INTO hierarchical_facilities(governorate,authority,center,administration,facility_name,created_at,hidden) VALUES(?,?,?,?,?,?,?)",
                                                  ("", auth, "", adm, fac, now(), 0))
                                        added_cnt += 1
                        reindex_hierarchical_facilities()
                        st.success(f"🎉 تم إضافة ({added_cnt}) سجل وإعادة الترتيب بنجاح!")
                        st.balloons()
                except Exception as e:
                    st.error(f"خطأ: {e}")
            st.markdown("---")
            st.markdown("##### 📥 تحميل شيت إكسيل الهيكل الإداري الحالي:")
            hier_all_data = get_hierarchical_data(include_hidden=True)
            if hier_all_data:
                df_hier_download = pd.DataFrame(hier_all_data)
                df_hier_download = df_hier_download[["id", "authority", "administration", "facility_name", "created_at", "hidden"]]
                df_hier_download.columns = ["ID", "المديرية / الجهة", "الإدارة", "المنشأة / وحدة الأمراض المتوطنة", "تاريخ الإنشاء", "حالة الإخفاء"]
                output_hier = io.BytesIO()
                with pd.ExcelWriter(output_hier, engine='openpyxl') as writer:
                    df_hier_download.to_excel(writer, index=False, sheet_name='HierarchicalFacilities')
                st.download_button("📥 تحميل شيت الهيكل الإداري (.xlsx)", data=output_hier.getvalue(), file_name="hierarchical_facilities.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            else:
                st.info("لا توجد بيانات مسجلة في الهيكل الإداري للتحميل حالياً.")
        with tab_h3:
            hier_rows_all = get_hierarchical_data(include_hidden=True)
            if not hier_rows_all:
                st.info("لا توجد بيانات مسجلة.")
            else:
                st.markdown("##### اختر المديرية ثم الإدارة ثم المنشأة التابعة لها:")
                manage_auths = sorted({str(r.get("authority") or "").strip() for r in hier_rows_all if str(r.get("authority") or "").strip()})
                sel_manage_auth = st.selectbox("المديرية / الجهة:", manage_auths, key="hier_manage_authority", on_change=_reset_hier_admin_and_facility)
                manage_auth_rows = [r for r in hier_rows_all if str(r.get("authority") or "").strip() == sel_manage_auth]
                manage_admins = sorted({str(r.get("administration") or "").strip() for r in manage_auth_rows if str(r.get("administration") or "").strip()})
                sel_manage_admin = st.selectbox("الإدارة:", ["-- اختر الإدارة --"] + manage_admins, key="hier_manage_administration", on_change=_reset_hier_facility)
                manage_admin_rows = [r for r in manage_auth_rows if sel_manage_admin != "-- اختر الإدارة --" and str(r.get("administration") or "").strip() == sel_manage_admin]
                manage_facilities = sorted(manage_admin_rows, key=lambda r: str(r.get("facility_name") or ""))
                manage_facility_map = {f"{r['facility_name']} (ID {r['id']}) — {'مخفي' if r['hidden'] else 'ظاهر'}": r['id'] for r in manage_facilities}
                if not manage_facility_map:
                    st.info("اختر الإدارة لعرض المنشآت التابعة لها فقط.")
                else:
                    selected_manage_facility = st.selectbox("المنشأة:", ["-- اختر المنشأة --"] + list(manage_facility_map.keys()), key="hier_manage_facility")
                    if selected_manage_facility != "-- اختر المنشأة --":
                        target_id = manage_facility_map[selected_manage_facility]
                        with st.form("manage_single_hier_form"):
                            c_hide_btn, c_show_btn, c_del_btn = st.columns(3)
                            with c_hide_btn:
                                hide_fac_submit = st.form_submit_button("👁🗨️ إخفاء المنشأة", use_container_width=True)
                            with c_show_btn:
                                show_fac_submit = st.form_submit_button("✅ إظهار المنشأة", use_container_width=True)
                            with c_del_btn:
                                single_del = st.form_submit_button("🗑 حذف نهائي", use_container_width=True)
                        if hide_fac_submit:
                            with db() as c:
                                c.execute("UPDATE hierarchical_facilities SET hidden=1 WHERE id=?", (target_id,))
                            st.success("✅ تم إخفاء المنشأة من التقارير بنجاح!")
                            st.rerun()
                        if show_fac_submit:
                            with db() as c:
                                c.execute("UPDATE hierarchical_facilities SET hidden=0 WHERE id=?", (target_id,))
                            st.success("✅ تم إظهار المنشأة في التقارير بنجاح!")
                            st.rerun()
                        if single_del:
                            with db() as c:
                                c.execute("DELETE FROM hierarchical_facilities WHERE id=?", (target_id,))
                            reindex_hierarchical_facilities()
                            st.success("✅ تم حذف المنشأة وإعادة الترتيب التسلسلي للـ ID بنجاح!")
                            st.rerun()
                df_hier = pd.DataFrame(hier_rows_all)
                df_hier["hidden"] = df_hier["hidden"].apply(lambda x: "مخفي 👁‍🗨" if x==1 else "ظاهر ✅")
                df_hier = df_hier[["id", "authority", "administration", "facility_name", "created_at", "hidden"]]
                df_hier.columns = ["ID", "المديرية / الجهة", "الإدارة", "المنشأة / وحدة الأمراض المتوطنة", "تاريخ الإنشاء", "حالة الإخفاء"]
                st.dataframe(df_hier, use_container_width=True, hide_index=True)

    elif selected_menu == "⚙ إدارة الأسئلة":
        st.subheader("⚙ إدارة الأسئلة وبنك الأسئلة الشامل للأمراض المتوطنة (مع إمكانية الحذف الفردي والنهائي والتفريغ)")
        sub_q_manage_tabs = st.tabs(["➕ إضافة وتعديل وحذف فردي", "🧠 بنك الأسئلة الشامل (استيراد وتصدير وحذف البنك)"])
        categories_list_opts = [
            "الاستراتيجية العامة ومكافحة البلهارسيا", "البلهارسيا", "علاج البلهارسيا", "الفاشيولا", "علاج الفاشيولا", "الهتروفيس", "التينيا", "هيمنولبس نانا", "الإسكارس", "الأنكلستوما", "الأكسيورس", "تركيورس تركيورا", "Strongyloides stercoralis", "Entamoeba histolytica", "Giardia lamblia", "الفحوصات الطفيلية والتشخيصية", "فحص البول (بلهارسيا المجاري البولية)", "فحص البراز (طفيليات المعوية)", "ط طرق فحص البراز المعتمدة", "الترسيب", "التعويم", "اللطخة المباشرة", "التصفية الغشائية", "Kato-Katz", "تحضير وعزل العينات", "أسئلة الصور والأشكال المجهرية"
        ]
        with sub_q_manage_tabs[0]:
            sub_img_tabs = st.tabs(["➕ إضافة", "✏ تعديل", "🗑 حذف"])
            with sub_img_tabs[0]:
                if st.session_state.add_success_msg:
                    st.success(st.session_state.add_success_msg)
                    st.session_state.add_success_msg = ""
                with st.form(key=f"add_q_form_{st.session_state.form_key}"):
                    selected_cat = st.selectbox("المجال / القسم:", categories_list_opts)
                    c_text = st.text_area("نص السؤال:", value="")
                    c_diff = st.selectbox("الصعوبة:", ["سهل", "متوسط", "صعب"])
                    uploaded_img = st.file_uploader("رفع صورة مجهرية / توضيحية (اختياري):", type=["png", "jpg", "jpeg"])
                    opt1, opt2 = st.text_input("خيار 1:", value=""), st.text_input("خيار 2:", value="")
                    opt3, opt4 = st.text_input("خيار 3:", value=""), st.text_input("خيار 4:", value="")
                    correct_ans_text = st.text_input("الإجابة الصحيحة:", value="")
                    if st.form_submit_button("حفظ", use_container_width=True):
                        if c_text and correct_ans_text:
                            img_uri_final = f"data:image/{uploaded_img.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_img.read()).decode("utf-8") if uploaded_img else ""
                            full_q_str = f"IMAGE:{img_uri_final}\n\n{c_text}" if img_uri_final else c_text
                            opts_list = [o for o in [opt1, opt2, opt3, opt4] if o.strip() != ""]
                            if correct_ans_text not in opts_list:
                                opts_list.append(correct_ans_text)
                            ans_idx = opts_list.index(correct_ans_text)
                            fp = hashlib.sha256((full_q_str + "|" + "|".join(opts_list)).encode("utf-8")).hexdigest()
                            with db() as c:
                                c.execute("INSERT INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                          (c_diff, selected_cat, full_q_str, json.dumps(opts_list, ensure_ascii=False), ans_idx, 1, fp, now()))
                            st.session_state.add_success_msg = "✅ تم الإضافة!"
                            st.session_state.form_key += 1
                            st.rerun()
            with sub_img_tabs[1]:
                with db() as c:
                    all_questions = c.execute("SELECT id, question, category FROM questions ORDER BY id ASC").fetchall()
                if all_questions:
                    q_options_map = {f"سؤال ({q['id']}) - {q['question'][:40]}...": q['id'] for q in all_questions}
                    selected_q_label = st.selectbox("اختر السؤال:", list(q_options_map.keys()))
                    selected_q_id = q_options_map[selected_q_label]
                    with db() as c:
                        q_data = c.execute("SELECT * FROM questions WHERE id=?", (selected_q_id,)).fetchone()
                    if q_data:
                        current_opts = json.loads(q_data["options_json"])
                        while len(current_opts) < 4:
                            current_opts.append("")
                        with st.form(f"edit_q_{selected_q_id}"):
                            e_cat = st.selectbox("المجال / القسم:", categories_list_opts, index=categories_list_opts.index(q_data["category"]) if q_data["category"] in categories_list_opts else 0)
                            e_diff = st.selectbox("الصعوبة:", ["سهل", "متوسط", "صعب"], index=["سهل", "متوسط", "صعب"].index(q_data["difficulty"]) if q_data["difficulty"] in ["سهل", "متوسط", "صعب"] else 0)
                            raw_q_db = q_data["question"]
                            actual_text_editable = raw_q_db.replace("IMAGE:", "").split("\n\n")[-1] if "IMAGE:" in raw_q_db else raw_q_db
                            e_text = st.text_area("نص السؤال:", value=actual_text_editable)
                            e_o1, e_o2 = st.text_input("خيار 1:", value=str(current_opts[0])), st.text_input("خيار 2:", value=str(current_opts[1]))
                            e_o3, e_o4 = st.text_input("خيار 3:", value=str(current_opts[2])), st.text_input("خيار 4:", value=str(current_opts[3]))
                            e_correct = st.text_input("الإجابة الصحيحة:", value=current_opts[q_data["answer"]] if 0 <= q_data["answer"] < len(current_opts) else "")
                            if st.form_submit_button("💾 حفظ", use_container_width=True):
                                updated_opts = [o for o in [e_o1, e_o2, e_o3, e_o4] if o.strip() != ""]
                                if e_correct not in updated_opts:
                                    updated_opts.append(e_correct)
                                new_ans_idx = updated_opts.index(e_correct)
                                prefix_img = raw_q_db.split("\n\n")[0] + "\n\n" if "IMAGE:" in raw_q_db else ""
                                final_str = prefix_img + e_text
                                new_fp = hashlib.sha256((final_str + "|" + "|".join(updated_opts)).encode("utf-8")).hexdigest()
                                with db() as c:
                                    c.execute("UPDATE questions SET difficulty=?, category=?, question=?, options_json=?, answer=?, fingerprint=? WHERE id=?",
                                              (e_diff, e_cat, final_str, json.dumps(updated_opts, ensure_ascii=False), new_ans_idx, new_fp, selected_q_id))
                                st.success("✅ تم التعديل!")
                                st.rerun()
            with sub_img_tabs[2]:
                with db() as c:
                    all_questions_del = c.execute("SELECT id, question FROM questions ORDER BY id ASC").fetchall()
                if all_questions_del:
                    q_del_map = {f"سؤال رقم {q['id']} - {q['question'][:40]}": q['id'] for q in all_questions_del}
                    with st.form("delete_single_question_form"):
                        selected_del_label = st.selectbox("اختر السؤال للحذف:", list(q_del_map.keys()))
                        if st.form_submit_button("🗑 حذف السؤال المحدد وإعادة الترتيب", use_container_width=True):
                            with db() as c:
                                c.execute("DELETE FROM questions WHERE id=?", (q_del_map[selected_del_label],))
                            reindex_questions()
                            st.success("✅ تم الحذف وإعادة ترقيم بنك الأسئلة بنجاح!")
                            st.rerun()
        with sub_q_manage_tabs[1]:
            st.markdown("#### 🧠 بنك الأسئلة الشامل (استيراد، دمج، تصدير، وتفريغ/حذف البنك بالكامل)")
            tab_ex_1, tab_ex_2 = st.tabs(["📥 رفع شيت إكسيل ودمج الأسئلة", "📤 تصدير وحذف بنك الأسئلة"])
            with tab_ex_1:
                st.info("💡 يمكنك من هنا رفع شيت إكسيل (أو CSV) لدمج وإضافة مجموعة جديدة من الأسئلة إلى بنك الأسئلة الحالي دون مسح الأسئلة الموجودة مسبقاً.")
                uploaded_excel = st.file_uploader("اختر ملف إكسيل الأسئلة:", type=["xlsx", "xls", "csv"], key="excel_uploader_v1_0")
                if uploaded_excel is not None:
                    try:
                        df_import = pd.read_csv(uploaded_excel) if uploaded_excel.name.endswith('.csv') else pd.read_excel(uploaded_excel)
                        st.write(f"📊 معاينة الملف المرفوع (عدد الصفوف: {len(df_import)}):")
                        st.dataframe(df_import.head(5), use_container_width=True, hide_index=True)
                        if st.button("🚀 تأكيد ودمج الأسئلة الجديدة في بنك الأسئلة", use_container_width=True):
                            imported_count = 0
                            skipped_count = 0
                            with db() as c:
                                for _, row in df_import.iterrows():
                                    diff = str(row.get("difficulty", row.get("الصعوبة", "متوسط"))).strip()
                                    cat = str(row.get("category", row.get("المجال", "الفحوصات الطفيلية والتشخيصية"))).strip()
                                    q_text = str(row.get("question", row.get("السؤال", ""))).strip()
                                    raw_opts = row.get("options_json", row.get("الخيارات", '["نعم", "لا"]'))
                                    try:
                                        if isinstance(raw_opts, str) and raw_opts.startswith("["):
                                            opts_list = json.loads(raw_opts)
                                        else:
                                            opts_list = [o.strip() for o in str(raw_opts).split(",") if o.strip()]
                                    except:
                                        opts_list = ["نعم", "لا"]
                                    try:
                                        ans_idx = int(row.get("answer", row.get("رقم الإجابة الصحيحة", 0)))
                                    except:
                                        ans_idx = 0
                                    if ans_idx < 0 or ans_idx >= len(opts_list):
                                        ans_idx = 0
                                    if q_text and opts_list:
                                        fp = hashlib.sha256((q_text + "|" + "|".join(str(o) for o in opts_list)).encode("utf-8")).hexdigest()
                                        try:
                                            c.execute("INSERT INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                                      (diff, cat, q_text, json.dumps(opts_list, ensure_ascii=False), ans_idx, 1, fp, now()))
                                            imported_count += 1
                                        except sqlite3.IntegrityError:
                                            skipped_count += 1
                                        except:
                                            pass
                            reindex_questions()
                            st.success(f"🎉 تم بنجاح دمج وإضافة ({imported_count}) سؤالاً جديداً للبنك! (تم تخطي {skipped_count} سؤالاً مكرراً لتجنب الازدواج).")
                            st.balloons()
                    except Exception as e:
                        st.error(f"خطأ أثناء قراءة أو دمج الملف: {e}")
            with tab_ex_2:
                with db() as c:
                    df_bank = pd.read_sql_query("SELECT id, difficulty, category, question, options_json, answer FROM questions ORDER BY id ASC", c)
                if df_bank.empty:
                    st.info("بنك الأسئلة فارغ حالياً.")
                else:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_bank.to_excel(writer, index=False, sheet_name='QuestionBank')
                    st.download_button("📥 تحميل بنك الأسئلة إكسيل (.xlsx)", data=output.getvalue(), file_name="question_bank.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                    st.dataframe(df_bank, use_container_width=True, hide_index=True)
                st.markdown("---")
                st.markdown("##### ⚠ منطقة الخطر - إدارة البنك الشامل:")
                with st.form("delete_entire_question_bank_form"):
                    confirm_text_del = st.text_input("اكتب كلمة (حذف البنك) للتأكيد نهائياً:", value="")
                    if st.form_submit_button("🗑 تفريغ وحذف بنك الأسئلة بالكامل", use_container_width=True):
                        if confirm_text_del.strip() == "حذف البنك":
                            with db() as c:
                                c.execute("DELETE FROM questions")
                                c.execute("DELETE FROM sqlite_sequence WHERE name='questions'")
                            st.success("✅ تم حذف وتفريغ بنك الأسئلة بالكامل بنجاح!")
                            st.rerun()
                        else:
                            st.warning("⚠ يرجى كتابة كلمة (حذف البنك) بشكل صحيح في حقل التأكيد لإتمام الحذف.")

    elif selected_menu == "🧑‍🔬 المتدربين والنماذج":
        st.subheader("🧑🔬 إدارة واعتماد المتدربين والنماذج المرتبطة بهم")
        with db() as c:
            all_tpls_records = c.execute("SELECT * FROM exam_templates WHERE active=1 ORDER BY name ASC").fetchall()
        if all_tpls_records:
            tpl_names_list = [f"{row['name']} ({row['exam_type'] or 'قبل التدريب'}) | المهنة: {row['profession'] or 'كل الوظائف'} | {template_scope_text(dict(row))}" for row in all_tpls_records]
            tpl_map_dict = {f"{row['name']} ({row['exam_type'] or 'قبل التدريب'}) | المهنة: {row['profession'] or 'كل الوظائف'} | {template_scope_text(dict(row))}": row["id"] for row in all_tpls_records}
        else:
            tpl_names_list = ["لا توجد نماذج اختبارات مسجلة"]
            tpl_map_dict = {}
        with st.container(border=True):
            st.markdown("##### 🚀 التعميم الجماعي لنموذج على كافة المتدربين:")
            with st.form("bulk_assign_form_fixed"):
                global_tpl_labels = [f"{t['name']} ({t['exam_type'] or 'قبل التدريب'}) | {template_scope_text(dict(t))}" for t in all_tpls_records if not any((t[k] or "").strip() for k in ["scope_governorate", "scope_authority", "scope_center", "scope_administration", "scope_facility"])]
                global_tpl_map = {f"{t['name']} ({t['exam_type'] or 'قبل التدريب'}) | {template_scope_text(dict(t))}": t['id'] for t in all_tpls_records if not any((t[k] or "").strip() for k in ["scope_governorate", "scope_authority", "scope_center", "scope_administration", "scope_facility"])}
                bulk_tpl_sel = st.selectbox("اختر نموذج الاختبار لتعميمه على الجميع (النماذج العامة فقط):", global_tpl_labels or ["لا يوجد نموذج عام"] )
                if st.form_submit_button("تعميم الاختبار واعتماد الجميع", use_container_width=True):
                    if global_tpl_map and bulk_tpl_sel in global_tpl_map:
                        set_bulk_template_for_all(global_tpl_map[bulk_tpl_sel])
                        st.success("✅ تم التعميم والاعتماد بنجاح لكافة المتدربين!")
                        st.rerun()
                    else:
                        st.warning("⚠ يرجى اختيار نموذج صالح.")
        sub_tabs = st.tabs(["🆕 قبول المسجلين الجدد", "جميع المتدربين (إدارة وإخفاء/إظهار/حذف)", "📝 طباعة نموذج امتحان الممتحن"])
        with sub_tabs[0]:
            st.markdown("#### 🆕 قبول المسجلين الجدد وتعديل بياناتهم")
            st.caption("يمكن البحث بالرقم القومي، تعديل بيانات الطلب قبل الاعتماد، ثم اختيار نموذج الاختبار وفق الهيكل الإداري.")
            search_nid = st.text_input("🔎 بحث عن متدرب بالرقم القومي:", value="", max_chars=14, key="pending_nid_search")
            search_digits = normalize_national_id(search_nid)
            if search_digits:
                with db() as c:
                    search_rows = c.execute("SELECT * FROM trainees WHERE national_id=? ORDER BY id DESC", (search_digits,)).fetchall()
                if search_rows:
                    st.success(f"تم العثور على {len(search_rows)} سجل مطابق للرقم القومي.")
                    for sr in search_rows:
                        st.info(f"ID: {sr['id']} | الاسم: {sr['name']} | الهاتف: {sr['phone']} | الحالة: {sr['status']} | الجهة: {sr['facility']}")
                elif len(search_digits) == 14:
                    st.warning("لا يوجد متدرب مسجل بهذا الرقم القومي.")

            df_pend = trainees_df("pending", include_hidden=False)
            if df_pend.empty:
                st.info("لا توجد طلبات تسجيل جديدة معلقة حالياً.")
            else:
                for _, r in df_pend.iterrows():
                    with st.container(border=True):
                        st.markdown(f"### 👤 طلب تسجيل رقم {int(r['id'])}")
                        with st.form(f"approve_edit_form_{int(r['id'])}"):
                            edit_name = st.text_input("اسم المتدرب:", value=str(r.get('name') or ''), key=f"pend_name_{int(r['id'])}")
                            ec1, ec2 = st.columns(2)
                            with ec1:
                                edit_nid = st.text_input("الرقم القومي:", value=str(r.get('national_id') or ''), max_chars=14, key=f"pend_nid_{int(r['id'])}")
                            with ec2:
                                edit_phone = st.text_input("رقم الهاتف / المعرف الرئيسي:", value=str(r.get('phone') or ''), key=f"pend_phone_{int(r['id'])}")
                            ec3, ec4 = st.columns(2)
                            with ec3:
                                edit_prof = st.text_input("الوظيفة:", value=str(r.get('profession') or 'أخصائي الأمراض المتوطنة'), key=f"pend_prof_{int(r['id'])}")
                            with ec4:
                                edit_facility = st.text_input("جهة العمل / المنشأة:", value=str(r.get('facility') or ''), key=f"pend_fac_{int(r['id'])}")
                            applicable_tpls = [t for t in all_tpls_records if template_matches_facility(t, edit_facility)]
                            applicable_labels = [f"{t['name']} ({t['exam_type'] or 'قبل التدريب'}) | {template_scope_text(dict(t))}" for t in applicable_tpls] or ["لا يوجد نموذج ضمن نطاق هذه الجهة"]
                            applicable_map = {f"{t['name']} ({t['exam_type'] or 'قبل التدريب'}) | {template_scope_text(dict(t))}": t['id'] for t in applicable_tpls}
                            chosen_tpl = st.selectbox("نموذج الاختبار المخصص حسب الهيكل الإداري:", applicable_labels, key=f"app_tpl_{int(r['id'])}")
                            bc1, bc2, bc3 = st.columns(3)
                            with bc1:
                                save_data_btn = st.form_submit_button("💾 حفظ تعديل البيانات", use_container_width=True)
                            with bc2:
                                app_btn = st.form_submit_button("✅ اعتماد", use_container_width=True)
                            with bc3:
                                rej_btn = st.form_submit_button("❌ رفض", use_container_width=True)
                            if save_data_btn or app_btn:
                                digits_nid = normalize_national_id(edit_nid)
                                phone_norm = normalize_egyptian_phone(edit_phone)
                                if not edit_name.strip() or not phone_norm or not edit_facility.strip():
                                    st.error("⚠ يجب استكمال الاسم والهاتف وجهة العمل.")
                                elif not is_valid_egyptian_national_id(digits_nid):
                                    st.error("⚠ الرقم القومي غير صحيح؛ راجع 14 رقماً وتاريخ الميلاد وكود المحافظة.")
                                elif not is_valid_egyptian_mobile(phone_norm):
                                    st.error("⚠ رقم الموبايل المصري غير صحيح.")
                                else:
                                    try:
                                        update_trainee_data(int(r['id']), edit_facility.strip(), edit_name.strip(), phone_norm, digits_nid, edit_prof.strip())
                                        if app_btn:
                                            if applicable_map and chosen_tpl in applicable_map:
                                                set_trainee_status_and_template(int(r['id']), "approved", applicable_map[chosen_tpl])
                                                st.success("✅ تم حفظ البيانات واعتماد المتدرب بنجاح.")
                                                st.rerun()
                                            else:
                                                st.warning("⚠ تم حفظ البيانات، لكن يجب تحديد نموذج اختبار صحيح للاعتماد.")
                                        else:
                                            st.success("✅ تم حفظ تعديلات بيانات المتدرب بنجاح.")
                                            st.rerun()
                                    except ValueError as e:
                                        if str(e) == "DUPLICATE_TRAINEE_PHONE":
                                            st.error("❌ رقم الهاتف مستخدم بالفعل لمتدرب آخر، ولا يمكن تكراره.")
                                        elif str(e) == "DUPLICATE_TRAINEE_NATIONAL_ID":
                                            st.error("❌ الرقم القومي مستخدم بالفعل لمتدرب آخر، ولا يمكن تكراره.")
                                        elif str(e) == "INVALID_TRAINEE_PHONE":
                                            st.error("❌ رقم الموبايل المصري غير صحيح.")
                                        elif str(e) == "INVALID_TRAINEE_NATIONAL_ID":
                                            st.error("❌ الرقم القومي غير صحيح.")
                                        else:
                                            st.error(f"تعذر حفظ البيانات: {e}")
                            if rej_btn:
                                set_trainee_status_and_template(int(r['id']), "rejected", r.get('assigned_template_id'))
                                st.warning("تم رفض طلب التسجيل.")
                                st.rerun()
        with sub_tabs[1]:
            st.markdown("#### 🏥 فلترة المتدربين حسب الهيكل الإداري")
            tr_scope_manage = hierarchy_scope_widget("نطاق المتدربين:", "trainees_manage_scope_v1")
            tr_scope_pred, tr_scope_args = hierarchy_filter_for_trainees(tr_scope_manage, "t")
            with db() as c:
                scoped_ids = [r[0] for r in c.execute(f"SELECT t.id FROM trainees t WHERE {tr_scope_pred}", tuple(tr_scope_args)).fetchall()]
            df_all_tr = trainees_df(include_hidden=True)
            if not df_all_tr.empty and any(str(tr_scope_manage.get(k) or "").strip() for k in ("scope_governorate", "scope_authority", "scope_center", "scope_administration", "scope_facility")):
                df_all_tr = df_all_tr[df_all_tr["id"].isin(scoped_ids)]
            if df_all_tr.empty:
                st.info("لا توجد بيانات متدربين مسجلة.")
            else:
                st.dataframe(df_all_tr[['id', 'name', 'profession', 'facility', 'status']], use_container_width=True, hide_index=True)
                with st.form("manage_trainee_action_form"):
                    tr_map_options = {f"ID ({row['id']}) - {row['name']} [{row['status']}]": row['id'] for _, row in df_all_tr.iterrows()}
                    selected_tr_label = st.selectbox("اختر المتدرب للإدارة والتعديل:", list(tr_map_options.keys()))
                    target_tr_id = tr_map_options[selected_tr_label]
                    target_chosen_tpl = st.selectbox("تعديل نموذج الاختبار للمتدرب:", tpl_names_list, key="mod_tr_tpl_sel")
                    col_u1, col_u2, col_u3, col_u4 = st.columns(4)
                    with col_u1:
                        upd_t_btn = st.form_submit_button("💾 تحديث", use_container_width=True)
                    with col_u2:
                        hide_t_btn = st.form_submit_button("👁🗨 إخفاء", use_container_width=True)
                    with col_u3:
                        show_t_btn = st.form_submit_button("✅ إظهار", use_container_width=True)
                    with col_u4:
                        del_t_btn = st.form_submit_button("🗑 حذف", use_container_width=True)
                    if upd_t_btn:
                        if tpl_map_dict and target_chosen_tpl in tpl_map_dict:
                            set_trainee_status_and_template(int(target_tr_id), "approved", tpl_map_dict[target_chosen_tpl])
                            st.success("✅ تم تحديث نموذج المتدرب بنجاح!")
                            st.rerun()
                    if hide_t_btn:
                        with db() as c:
                            c.execute("UPDATE trainees SET hidden=1 WHERE id=?", (int(target_tr_id),))
                        st.success("✅ تم إخفاء المتدرب بنجاح!")
                        st.rerun()
                    if show_t_btn:
                        with db() as c:
                            c.execute("UPDATE trainees SET hidden=0 WHERE id=?", (int(target_tr_id),))
                        st.success("✅ تم إظهار المتدرب بنجاح!")
                        st.rerun()
                    if del_t_btn:
                        with db() as c:
                            c.execute("PRAGMA foreign_keys=OFF;")
                            c.execute("DELETE FROM trainees WHERE id=?", (int(target_tr_id),))
                            c.execute("DELETE FROM exam_sessions WHERE trainee_id=?", (int(target_tr_id),))
                            c.execute("PRAGMA foreign_keys=ON;")
                        reindex_trainees()
                        st.success("✅ تم الحذف وإعادة الترتيب بنجاح!")
                        st.rerun()
        with sub_tabs[2]:
            st.markdown("#### 📝 طباعة نموذج امتحان الإجابة والأسئلة لممتحن أدى الامتحان على البرنامج:")
            exam_print_scope = hierarchy_scope_widget("نطاق طباعة نماذج الإجابة:", "exam_print_scope_v1")
            exam_scope_pred, exam_scope_args = hierarchy_filter_for_trainees(exam_print_scope, "t")
            with db() as c:
                completed_sessions = c.execute(f"""
                    SELECT s.id, t.name trainee_name, t.facility, t.profession trainee_profession, s.submitted_at, s.started_at, e.name template_name, e.exam_type
                    FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id
                    WHERE s.status='submitted' AND t.hidden=0 AND {exam_scope_pred} ORDER BY s.id DESC
                """, tuple(exam_scope_args)).fetchall()
            if not completed_sessions:
                st.info("لا توجد اختبارات مكتملة مسجلة للممتحنين الظاهرين حتى الآن.")
            else:
                exam_records_map = {f"المتدرب: {r['trainee_name']} | الوظيفة: {r['trainee_profession']} | الجهة: {r['facility']} | الاختبار: {r['template_name'] or 'موافق'} ({r['exam_type'] or 'قبل التدريب'}) | التاريخ: {r['submitted_at'] or r['started_at']} (ID: {r['id']})": r['id'] for r in completed_sessions}
                sel_exam_rec_label = st.selectbox("اختر الممتحن وتاريخ الامتحان:", list(exam_records_map.keys()))
                chosen_exam_session_id = exam_records_map[sel_exam_rec_label]
                trainee_exam_sheet_html = generate_trainee_exam_sheet_html(chosen_exam_session_id)
                st.markdown("<br>", unsafe_allow_html=True)
                render_print_button_only(trainee_exam_sheet_html, f"نموذج إجابة الامتحان للممتحن رقم {chosen_exam_session_id}")

    elif selected_menu == "🧩 مواعيد الاختبارات و طباعة النماذج":
        st.subheader("🧩 مواعيد الاختبارات ونماذج الأسئلة (مع إمكانية الحذف وإعادة الترتيب التلقائي للـ ID)")
        sub_tpl_mode = st.radio("القسم:", ["📋 عرض النماذج وطباعة الأسئلة", "➕ إنشاء نموذج جديد", "⚙ تعديل موعد وتصنيف", "🗑 حذف نموذج"], horizontal=True)
        if sub_tpl_mode == "📋 عرض النماذج وطباعة الأسئلة":
            st.markdown("#### 🏥 فلترة طباعة النماذج حسب الهيكل الإداري")
            tpl_print_scope = hierarchy_scope_widget("نطاق طباعة نماذج الاختبار:", "template_print_scope_v1")
            scope_keys = ("scope_governorate", "scope_authority", "scope_center", "scope_administration", "scope_facility")
            scope_values = [str(tpl_print_scope.get(k) or "").strip() for k in scope_keys]
            with db() as c:
                all_tpl_rows = [dict(r) for r in c.execute("SELECT * FROM exam_templates ORDER BY name ASC, id ASC").fetchall()]
            def _template_in_print_scope(template_row):
                if not any(scope_values):
                    return True
                template_scope_values = [str(template_row.get(k) or "").strip() for k in ("scope_governorate", "scope_authority", "scope_center", "scope_administration", "scope_facility")]
                # A global template is available in every selected administrative scope.
                if not any(template_scope_values):
                    return True
                return all(not template_scope_values[i] or template_scope_values[i] == scope_values[i] for i in range(len(scope_values))) and all(not scope_values[i] or not template_scope_values[i] or template_scope_values[i] == scope_values[i] for i in range(len(scope_values)))
            tpls = [t for t in all_tpl_rows if _template_in_print_scope(t)]
            if not tpls:
                st.info("لا توجد نماذج اختبارات مسجلة حتى الآن.")
            else:
                tpl_dropdown_map = {f"نموذج ({t['id']}) - {t['name']} [{t['exam_type']}] | {template_scope_text(dict(t))}": t for t in tpls}
                selected_dropdown_label = st.selectbox("🔍 اختر نموذج الاختبار من القائمة المنسدلة لعرضه وطباعته:", list(tpl_dropdown_map.keys()))
                if selected_dropdown_label:
                    t_dict = dict(tpl_dropdown_map[selected_dropdown_label])
                    num_q_display = "مفتوح" if int(t_dict.get('num_questions', 999999)) >= 999900 else t_dict.get('num_questions')
                    s_t = t_dict.get('start_time') or "غير محدد"
                    e_t = t_dict.get('end_time') or "غير محدد"
                    exam_type_badge = t_dict.get('exam_type', 'قبل التدريب')
                    def format_12h(iso_str):
                        if not iso_str or "T" not in iso_str:
                            return iso_str
                        try:
                            dt = datetime.fromisoformat(iso_str)
                            return dt.strftime("%Y-%m-%d %I:%M %p").replace("AM", "صباحاً").replace("PM", "مساءً")
                        except:
                            return iso_str
                    with st.container(border=True):
                        st.markdown(f"#### 🏷 نموذج ({t_dict.get('id')}): {t_dict.get('name')} &nbsp;|&nbsp; <span style='color: #059669; font-size: 14px;'>[{exam_type_badge}]</span>", unsafe_allow_html=True)
                        st.write(f"🔹 البدء: `{format_12h(s_t)}` | 🔸 النهاية: `{format_12h(e_t)}` | 📝 الأسئلة: {num_q_display}")
                        st.info(f"👷 المهنة المخصصة: **{t_dict.get('profession') or 'كل الوظائف'}**  \n\n🏥 نطاق الهيكل الإداري للنموذج: **{template_scope_text(t_dict)}**")
                        exam_template_html_out = generate_exam_template_print_html(t_dict.get('id'))
                        render_print_button_only(exam_template_html_out, f"نموذج امتحان رقم {t_dict.get('id')}")
        elif sub_tpl_mode == "➕ إنشاء نموذج جديد":
            categories_pool_opts = [
                "الاستراتيجية العامة ومكافحة البلهارسيا", "البلهارسيا", "علاج البلهارسيا", "الفاشيولا", "علاج الفاشيولا", "الهتروفيس", "التينيا", "هيمنولبس نانا", "الإسكارس", "الأنكلستوما", "الأكسيورس", "تركيورس تركيورا", "Strongyloides stercoralis", "Entamoeba histolytica", "Giardia lamblia", "الفحوصات الطفيلية والتشخيصية", "فحص البول (بلهارسيا المجاري البولية)", "فحص البراز (طفيليات المعوية)", "طرق فحص البراز المعتمدة", "الترسيب", "التعويم", "اللطخة المباشرة", "التصفية الغشائية", "Kato-Katz", "تحضير وعزل العينات", "أسئلة الصور والأشكال المجهرية"
            ]
            tpl_profession_options = ["كل الوظائف"] + list(get_print_settings().get("professions_list", ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"]))
            with st.form("create_template_schedule_form"):
                new_tpl_name = st.text_input("اسم النموذج:", value="")
                new_tpl_profession = st.selectbox("المهنة المسموح لها بأداء هذا الاختبار:", tpl_profession_options, help="لن يتمكن من دخول هذا النموذج إلا المتدرب المسجل بنفس المهنة. اختر كل الوظائف لإتاحته للجميع.")
                st.markdown("#### 🎯 تحديد تصنيف نموذج الاختبار:")
                new_exam_type = st.radio("نوع النموذج:", ["قبل التدريب", "بعد التدريب", "تقييم شامل"], horizontal=True)
                is_open_questions = st.checkbox("عدد أسئلة مفتوح (كامل البنك)", value=True)
                new_tpl_num_q = st.number_input("عدد الأسئلة:", min_value=1, max_value=5000, value=50)
                new_tpl_duration = st.number_input("المدة (بالدقائق):", min_value=5, max_value=300, value=60)
                new_tpl_pass = st.slider("نسبة النجاح %:", min_value=30.0, max_value=95.0, value=60.0)
                st.markdown("---")
                st.markdown("#### ⏰ تحديد توقيت البدء والنهاية بالتوقيت المحدث أونلاين (نظام 12 ساعة):")
                current_online_dt = now_cairo()
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    start_d = st.date_input("تاريخ البدء:", current_online_dt.date())
                    st.markdown("##### وقت البدء:")
                    sh_col1, sh_col2, sh_col3 = st.columns(3)
                    with sh_col1:
                        start_h = st.number_input("الساعة (1-12):", min_value=1, max_value=12, value=current_online_dt.hour % 12 or 12, key="sh_in")
                    with sh_col2:
                        start_m = st.number_input("الدقيقة (0-59):", min_value=0, max_value=59, value=current_online_dt.minute, key="sm_in")
                    with sh_col3:
                        start_ampm = st.selectbox("الفترة:", ["صباحاً", "مساءً"], index=0 if current_online_dt.hour < 12 else 1, key="sap_in")
                with col_d2:
                    end_d = st.date_input("تاريخ النهاية:", current_online_dt.date() + timedelta(days=1))
                    st.markdown("##### وقت النهاية:")
                    eh_col1, eh_col2, eh_col3 = st.columns(3)
                    with eh_col1:
                        end_h = st.number_input("الساعة (1-12):", min_value=1, max_value=12, value=5, key="eh_in")
                    with eh_col2:
                        end_m = st.number_input("الدقيقة (0-59):", min_value=0, max_value=59, value=0, key="em_in")
                    with eh_col3:
                        end_ampm = st.selectbox("الفترة:", ["صباحاً", "مساءً"], index=1, key="eap_in")
                st.markdown("#### 🏥 ربط النموذج بالهيكل الإداري")
                new_tpl_scope = hierarchy_scope_widget("نطاق النموذج داخل الهيكل الإداري:", "new_tpl_scope_v12")
                st.caption("إذا اخترت (كل الهيكل الإداري) يصبح النموذج متاحاً لجميع الجهات. وإلا سيظهر ويُستخدم داخل النطاق المحدد فقط.")
                new_tpl_cats = st.multiselect("المجالات / الأقسام:", categories_pool_opts)
                if st.form_submit_button("💾 حفظ النموذج والمواعيد", use_container_width=True):
                    if new_tpl_name.strip():
                        with db() as c:
                            if new_tpl_cats:
                                placeholders = ','.join(['?'] * len(new_tpl_cats))
                                img_q_cnt = c.execute(f"SELECT COUNT(*) FROM questions WHERE active=1 AND category IN ({placeholders}) AND question LIKE '%IMAGE:%'", new_tpl_cats).fetchone()[0]
                            else:
                                img_q_cnt = c.execute("SELECT COUNT(*) FROM questions WHERE active=1 AND question LIKE '%IMAGE:%'").fetchone()[0]
                        
                        if "أسئلة الصور والأشكال المجهرية" in new_tpl_cats and img_q_cnt < 4:
                            st.warning(f"⚠ عذراً، عدد الأسئلة المصورة المتاحة في النطاق المحدد هو ({img_q_cnt}), ويجب ألا يقل عن 4 أسئلة مصورة عند اختيار تصنيف الأشكال والصور.")
                        else:
                            def convert_to_24h(h, m, ampm):
                                h_24 = h % 12
                                if "مساءً" in ampm:
                                    h_24 += 12
                                return h_24, m
                            s_h24, s_m24 = convert_to_24h(start_h, start_m, start_ampm)
                            e_h24, e_m24 = convert_to_24h(end_h, end_m, end_ampm)
                            start_dt_str = datetime.combine(start_d, datetime.min.time().replace(hour=s_h24, minute=s_m24), tzinfo=CAIRO_TZ).isoformat(timespec="seconds")
                            end_dt_str = datetime.combine(end_d, datetime.min.time().replace(hour=e_h24, minute=e_m24), tzinfo=CAIRO_TZ).isoformat(timespec="seconds")
                            final_num_q = 999999 if is_open_questions else int(new_tpl_num_q)
                            with db() as c:
                                c.execute("""INSERT INTO exam_templates(
                                    name, exam_type, num_questions, duration_minutes, pass_percent, categories_json,
                                    start_time, end_time, created_at, scope_governorate, scope_authority, scope_center,
                                    scope_administration, scope_facility, profession
                                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                          (new_tpl_name.strip(), new_exam_type, final_num_q, int(new_tpl_duration), float(new_tpl_pass),
                                           json.dumps(new_tpl_cats, ensure_ascii=False), start_dt_str, end_dt_str, now(),
                                           new_tpl_scope["scope_governorate"], new_tpl_scope["scope_authority"], new_tpl_scope["scope_center"],
                                           new_tpl_scope["scope_administration"], new_tpl_scope["scope_facility"],
                                           "" if new_tpl_profession == "كل الوظائف" else new_tpl_profession))
                            st.success("✅ تم إنشاء وتحديد موعد وتصنيف النموذج بنجاح!")
                            st.rerun()
        elif sub_tpl_mode == "⚙ تعديل موعد وتصنيف":
            st.markdown("#### 👷 تعديل المهنة المخصصة لنموذج اختبار موجود")
            with db() as c:
                editable_tpls = c.execute("SELECT * FROM exam_templates ORDER BY name ASC, id ASC").fetchall()
            if not editable_tpls:
                st.info("لا توجد نماذج اختبارات لتعديلها.")
            else:
                editable_map = {f"{t['name']} ({t['exam_type'] or 'قبل التدريب'}) — المهنة الحالية: {t['profession'] or 'كل الوظائف'}": dict(t) for t in editable_tpls}
                edit_professions = ["كل الوظائف"] + list(get_print_settings().get("professions_list", ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"]))
                with st.form("edit_template_profession_form"):
                    edit_tpl_label = st.selectbox("اختر نموذج الاختبار:", list(editable_map.keys()))
                    edit_tpl_profession = st.selectbox("المهنة المسموح لها بأداء الاختبار:", edit_professions, help="اختيار كل الوظائف يجعل النموذج متاحاً لجميع المهن.")
                    if st.form_submit_button("💾 حفظ المهنة للنموذج", use_container_width=True):
                        edit_tpl_id = editable_map[edit_tpl_label]["id"]
                        profession_to_save = "" if edit_tpl_profession == "كل الوظائف" else edit_tpl_profession
                        with db() as c:
                            c.execute("UPDATE exam_templates SET profession=? WHERE id=?", (profession_to_save, edit_tpl_id))
                        st.success("✅ تم تحديث المهنة المخصصة لنموذج الاختبار.")
                        st.rerun()
        else:
            with db() as c:
                tpls_del = c.execute("SELECT id, name, exam_type FROM exam_templates ORDER BY name ASC, id ASC").fetchall()
            if tpls_del:
                tpl_map = {f"نموذج رقم {t['id']} - {t['name']} [{t['exam_type']}] | {template_scope_text(dict(t))}": t['id'] for t in tpls_del}
                with st.form("delete_template_form"):
                    selected_tpl_label = st.selectbox("اختر النموذج للحذف:", list(tpl_map.keys()))
                    if st.form_submit_button("🗑 حذف نموذج الاختبار وإعادة الترتيب", use_container_width=True):
                        with db() as c:
                            c.execute("PRAGMA foreign_keys=OFF;")
                            c.execute("DELETE FROM exam_templates WHERE id=?", (tpl_map[selected_tpl_label],))
                            c.execute("PRAGMA foreign_keys=ON;")
                        reindex_templates()
                        st.success("✅ تم الحذف وإعادة الترتيب التلقائي بنجاح!")
                        st.rerun()

    elif selected_menu == "✍ تسجيل نتيجة يدوي":
        st.subheader("✍ تسجيل نتيجة يدوي (مع اختيار الأسئلة الخاطئة لضمان الدقة)")
        hier_data = get_hierarchical_data(include_hidden=False)
        default_fac_str = hier_data[0]["facility_name"] if hier_data else ""
        print_st_m = get_print_settings()
        prof_manual_list = print_st_m.get("professions_list", ["أخصائي الأمراض المتوطنة", "طبيب بيطري"])
        with db() as c:
            all_tpls_records = c.execute("SELECT id, name, exam_type FROM exam_templates ORDER BY name ASC").fetchall()
        manual_tpl_choices = {f"{row['name']} ({row['exam_type']})": row["id"] for row in all_tpls_records} if all_tpls_records else {}
        manual_tpl_keys = list(manual_tpl_choices.keys()) if manual_tpl_choices else ["لا توجد نماذج اختبارات مسجلة"]
        with st.form("manual_score_form_enhanced"):
            m_trainee_name = st.text_input("اسم المتدرب:", value="")
            m_facility_name = st.text_input("وحدة الأمراض المتوطنة / جهة العمل:", value=default_fac_str)
            m_profession = st.selectbox("الوظيفة / التخصص:", prof_manual_list)
            selected_manual_tpl_name = st.selectbox("اختر قالب/نموذج الاختبار:", manual_tpl_keys)
            c1, c2 = st.columns(2)
            with c1:
                manual_score = st.number_input("الدرجة الحاصل عليها:", min_value=0, max_value=9999, value=45)
            with c2:
                manual_max = st.number_input("الدرجة الكلية:", min_value=1, max_value=9999, value=50)
            manual_passed = st.radio("الحالة:", ["اجتزت بنجاح", "لم تجتز الاختبار"])
            calc_pct = (manual_score / manual_max) * 100 if manual_max > 0 else 0
            st.info(f"📊 النسبة المئوية المحسوبة: **{calc_pct:.1f}%**")
            with db() as c:
                all_questions_db = c.execute("SELECT id, question, category FROM questions WHERE active=1").fetchall()
            selected_wrong_q_ids = []
            if calc_pct < 100.0 and all_questions_db:
                st.markdown("---")
                st.markdown("#### ❌ حدد الأسئلة التي أخطأ فيها المتدرب (لضمان دقة خطط العمل وتقارير الضعف):")
                q_options_dict = {f"سؤال ({q['id']}) - [{q['category']}] {q['question'][:50]}...": q['id'] for q in all_questions_db}
                selected_wrong_labels = st.multiselect("اختر الأسئلة الخاطئة من القائمة:", list(q_options_dict.keys()))
                selected_wrong_q_ids = [q_options_dict[lbl] for lbl in selected_wrong_labels]
            if st.form_submit_button("💾 حفظ النتيجة وتسجيل تفاصيل الأخطاء بدقة", use_container_width=True):
                if not m_trainee_name.strip():
                    st.warning("⚠ يرجى إدخال اسم المتدرب.")
                elif not manual_tpl_choices:
                    st.warning("⚠ يرجى إنشاء نماذج اختبارات أولاً.")
                else:
                    with db() as c:
                        tpl_id_val = manual_tpl_choices.get(selected_manual_tpl_name)
                        cur_tr = c.execute("INSERT INTO trainees(facility,name,phone,profession,status,assigned_template_id,created_at,updated_at,hidden) VALUES(?,?,?,?,?,?,?,?,?)",
                                           (m_facility_name, normalize_text(m_trainee_name), "0000000000", m_profession, "completed", tpl_id_val, now(), now(), 0))
                        new_tid = cur_tr.lastrowid
                        passed_flag = 1 if manual_passed == "اجتزت بنجاح" else 0
                        cur_sess = c.execute("INSERT INTO exam_sessions(trainee_id,template_id,started_at,expires_at,submitted_at,status,score,max_score,percent,passed) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                             (new_tid, tpl_id_val, now(), now(), now(), "submitted", manual_score, manual_max, calc_pct, passed_flag))
                        new_sid = cur_sess.lastrowid
                        cert_code = f"ELX-{new_sid:06d}"
                        c.execute("UPDATE exam_sessions SET certificate_id=? WHERE id=?", (cert_code, new_sid))
                        all_bank_qs = c.execute("SELECT id, answer FROM questions WHERE active=1").fetchall()
                        for pos, q_item in enumerate(all_bank_qs):
                            q_id = q_item["id"]
                            correct_ans = q_item["answer"]
                            if q_id in selected_wrong_q_ids:
                                wrong_opt = (correct_ans + 1) % 4
                                c.execute("INSERT INTO exam_questions(session_id, question_id, position, option_order_json, selected_option, is_correct) VALUES(?,?,?,?,?,?)",
                                          (new_sid, q_id, pos, json.dumps([0,1,2,3]), wrong_opt, 0))
                            else:
                                c.execute("INSERT INTO exam_questions(session_id, question_id, position, option_order_json, selected_option, is_correct) VALUES(?,?,?,?,?,?)",
                                          (new_sid, q_id, pos, json.dumps([0,1,2,3]), correct_ans, 1))
                    st.success(f"✅ تم تسجيل المتدرب والنتيجة وتحديد الأسئلة الخاطئة بنجاح برقم الشهادة: **{cert_code}**")


    elif selected_menu == "📊 التقارير":
        st.subheader("📊 تقارير أداء وحدات الأمراض المتوطنة وتحليل النتائج (تستبعد المخفيين تلقائياً)")

        st.markdown("#### 🏥 تحديد نطاق التقارير حسب الهيكل الإداري")
        rep_scope = hierarchy_scope_widget("نطاق التقارير:", "reports_scope_v12")
        rep_scope_sql, rep_scope_args = hierarchy_scope_sql("h", rep_scope)
        st.caption("جميع التقارير والرسوم البيانية والنتائج أسفل الصفحة ستلتزم بهذا النطاق الإداري.")

        rep_tab1, rep_tab2, rep_tab3, rep_tab4, rep_tab5 = st.tabs([
            "👤 تقرير فردي (لمتدرب مع فلترة ومقارنة فترات)",
            "🏢 تقرير جماعي (لوحدة متوطنة مع فلترة ومقارنة فترات)",
            "📋 تقرير النتائج الشامل",
            "📈 تقرير أداء الجهات",
            "🏆 عرض النتائج والفلترة والأعلى تقييماً"
        ])

        # أدوات داخلية آمنة للتقارير
        def _report_date_ok(d1, d2):
            if d1 > d2:
                st.warning("⚠️ تاريخ البداية يجب أن يكون قبل أو مساوياً لتاريخ النهاية.")
                return False
            return True

        def _pct(v):
            try:
                return float(v or 0.0)
            except Exception:
                return 0.0

        def _status(v):
            return "اجتزت بنجاح" if v == 1 else ("لم تجتز" if v is not None else "لا توجد نتيجة")

        def _excel_download(df, label, filename, key):
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Report")
            st.download_button(
                label, data=out.getvalue(), file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=key
            )

        with rep_tab1:
            st.markdown("#### 👤 التقرير الفردي للمتدرب (مع تحديد المدى الزمني ومقارنة فترتين)")
            with db() as c:
                tr_list_rep = c.execute(
                    f"SELECT DISTINCT t.id, t.name, t.facility, t.profession FROM trainees t "
                    f"LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name) "
                    f"WHERE COALESCE(t.hidden,0)=0 AND {rep_scope_sql} ORDER BY t.id DESC",
                    tuple(rep_scope_args)
                ).fetchall()

            if not tr_list_rep:
                st.info("لا توجد بيانات متدربين ظاهرة متاحة.")
            else:
                tr_choices_rep = {
                    f"متدرب: {t['name'] or ''} - الوظيفة: {t['profession'] or ''} - "
                    f"الجهة: {t['facility'] or ''} (ID: {t['id']})": t['id']
                    for t in tr_list_rep
                }
                sel_tr_rep_label = st.selectbox(
                    "اختر المتدرب لاستعراض تقريره الفردي:",
                    list(tr_choices_rep.keys()), key="sel_ind_tr_rep_v7"
                )
                chosen_tr_id = tr_choices_rep[sel_tr_rep_label]
                today = now_cairo().date()

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("##### 📅 الفترة الأولى (التقرير الأساسي)")
                    d_start_1 = st.date_input("من تاريخ الفترة الأولى", today-timedelta(days=30), key="rep_ds1_v7")
                    d_end_1 = st.date_input("إلى تاريخ الفترة الأولى", today, key="rep_de1_v7")
                with c2:
                    st.markdown("##### 📅 الفترة الثانية (للمقارنة)")
                    d_start_2 = st.date_input("من تاريخ الفترة الثانية", today-timedelta(days=60), key="rep_ds2_v7")
                    d_end_2 = st.date_input("إلى تاريخ الفترة الثانية", today-timedelta(days=31), key="rep_de2_v7")

                if _report_date_ok(d_start_1, d_end_1) and _report_date_ok(d_start_2, d_end_2):
                    with db() as c:
                        ind_tr_data = c.execute(
                            "SELECT id,name,facility,profession FROM trainees WHERE id=? AND COALESCE(hidden,0)=0",
                            (chosen_tr_id,)
                        ).fetchone()
                        q = """
                            SELECT s.id,s.score,s.max_score,s.percent,s.passed,s.submitted_at,
                                   e.name AS tpl_name,e.exam_type
                            FROM exam_sessions s
                            LEFT JOIN exam_templates e ON e.id=s.template_id
                            WHERE s.trainee_id=? AND s.status='submitted'
                              AND date(s.submitted_at)>=date(?) AND date(s.submitted_at)<=date(?)
                            ORDER BY s.id DESC LIMIT 1
                        """
                        s_q1 = c.execute(q, (chosen_tr_id,d_start_1.isoformat(),d_end_1.isoformat())).fetchone()
                        s_q2 = c.execute(q, (chosen_tr_id,d_start_2.isoformat(),d_end_2.isoformat())).fetchone()

                    if ind_tr_data:
                        def _score_text(row):
                            if not row or row["score"] is None:
                                return "لا توجد نتيجة في هذه الفترة"
                            return (
                                f"{row['score'] or 0}/{row['max_score'] or 0} "
                                f"({_pct(row['percent']):.1f}%) — "
                                f"{row['tpl_name'] or 'اختبار معتمد'} "
                                f"({row['exam_type'] or 'قبل التدريب'})"
                            )

                        p1_score = _score_text(s_q1)
                        p2_score = _score_text(s_q2)
                        p1_status = _status(s_q1["passed"] if s_q1 else None)
                        p2_status = _status(s_q2["passed"] if s_q2 else None)
                        p1_pct = _pct(s_q1["percent"] if s_q1 else 0)
                        p2_pct = _pct(s_q2["percent"] if s_q2 else 0)
                        individual_delta = p2_pct - p1_pct
                        individual_delta_text = f"{individual_delta:+.1f} نقطة مئوية (الفترة الثانية − الأولى)"

                        individual_report_html = f"""
                        <div style="font-family:'Cairo',sans-serif;direction:rtl;padding:10px;">
                            <h3 style="color:#047857;text-align:center;">تقرير أداء ونتيجة متدرب (مع مقارنة الفترات)</h3>
                            <hr style="border:1px solid #059669;">
                            <p><b>اسم المتدرب:</b> {esc(ind_tr_data['name'] or '')} |
                               <b>الوظيفة:</b> {esc(ind_tr_data['profession'] or '')} |
                               <b>جهة العمل:</b> {esc(ind_tr_data['facility'] or '')}</p>
                            <table style="width:100%;border-collapse:collapse;margin-top:15px;font-size:10pt;">
                                <tr><th style="border:1px solid #cbd5e1;padding:8px;background:#059669;color:white;">فترة المقارنة</th>
                                    <th style="border:1px solid #cbd5e1;padding:8px;background:#059669;color:white;">النتيجة والنسبة والتصنيف</th>
                                    <th style="border:1px solid #cbd5e1;padding:8px;background:#059669;color:white;">حالة الاجتياز</th></tr>
                                <tr><td style="border:1px solid #cbd5e1;padding:8px;font-weight:bold;">الفترة الأولى ({d_start_1} إلى {d_end_1})</td>
                                    <td style="border:1px solid #cbd5e1;padding:8px;">{p1_score}</td>
                                    <td style="border:1px solid #cbd5e1;padding:8px;">{p1_status}</td></tr>
                                <tr><td style="border:1px solid #cbd5e1;padding:8px;font-weight:bold;">الفترة الثانية ({d_start_2} إلى {d_end_2})</td>
                                    <td style="border:1px solid #cbd5e1;padding:8px;">{p2_score}</td>
                                    <td style="border:1px solid #cbd5e1;padding:8px;">{p2_status}</td></tr>
                                <tr><td colspan="3" style="border:1px solid #059669;padding:8px;background:#ecfdf5;font-weight:900;color:#065f46;text-align:center;">الفارق بين الفترتين: {individual_delta_text}</td></tr>
                            </table>
                        </div>"""
                        st.markdown(individual_report_html, unsafe_allow_html=True)
                        st.markdown("##### 📊 الرسم البياني لمقارنة الفترتين")
                        chart_ind = pd.DataFrame({"الفترة": ["الفترة الأولى", "الفترة الثانية"], "النسبة %": [_pct(s_q1["percent"] if s_q1 else 0), _pct(s_q2["percent"] if s_q2 else 0)]}).set_index("الفترة")
                        st.bar_chart(chart_ind, use_container_width=True)
                        chart_ind_html = report_chart_html("الرسم البياني — مقارنة الفترتين", ["الفترة الأولى", "الفترة الثانية"], [p1_pct, p2_pct], "%")
                        render_print_button_only(generate_general_report_html("الرسم البياني لمقارنة أداء المتدرب", chart_ind_html), f"طباعة رسم مقارنة المتدرب {chosen_tr_id}")

                        df_ind = pd.DataFrame([{
                            "اسم المتدرب": ind_tr_data["name"] or "",
                            "الوظيفة": ind_tr_data["profession"] or "",
                            "جهة العمل": ind_tr_data["facility"] or "",
                            "الفترة الأولى": f"{d_start_1} إلى {d_end_1}",
                            "نتيجة الفترة الأولى": p1_score,
                            "حالة الفترة الأولى": p1_status,
                            "الفترة الثانية": f"{d_start_2} إلى {d_end_2}",
                            "نتيجة الفترة الثانية": p2_score,
                            "حالة الفترة الثانية": p2_status,
                            "الفارق بين الفترتين (الثانية - الأولى)": f"{individual_delta:+.1f} نقطة مئوية"
                        }])
                        _excel_download(df_ind,"📥 تحميل التقرير الفردي (.xlsx)",f"individual_report_{chosen_tr_id}.xlsx","dl_ind_report_v7")
                        render_print_button_only(
                            generate_general_report_html(f"مقارنة أداء المتدرب: {ind_tr_data['name'] or ''}", individual_report_html),
                            f"مقارنة فترات المتدرب {chosen_tr_id}"
                        )

        with rep_tab2:
            st.markdown("#### 🏢 التقرير الجماعي لوحدة الأمراض المتوطنة (مقارنة فترتين)")
            with db() as c:
                facs_list_rep = [
                    r[0] for r in c.execute(
                        f"SELECT DISTINCT t.facility FROM trainees t "
                        f"LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name) "
                        f"WHERE t.facility IS NOT NULL AND TRIM(t.facility)<>'' AND COALESCE(t.hidden,0)=0 AND {rep_scope_sql} ORDER BY t.facility",
                        tuple(rep_scope_args)
                    ).fetchall()
                ]
            if not facs_list_rep:
                st.info("لا توجد وحدات أو جهات ظاهرة مسجلة.")
            else:
                sel_fac_rep = st.selectbox("اختر الوحدة الصحية / جهة العمل:", facs_list_rep, key="sel_group_fac_rep_v7")
                today = now_cairo().date()
                g1,g2=st.columns(2)
                with g1:
                    gf_start_1=st.date_input("من تاريخ الفترة الأولى",today-timedelta(days=30),key="gfs1_v7")
                    gf_end_1=st.date_input("إلى تاريخ الفترة الأولى",today,key="gfe1_v7")
                with g2:
                    gf_start_2=st.date_input("من تاريخ الفترة الثانية",today-timedelta(days=60),key="gfs2_v7")
                    gf_end_2=st.date_input("إلى تاريخ الفترة الثانية",today-timedelta(days=31),key="gfe2_v7")

                if _report_date_ok(gf_start_1,gf_end_1) and _report_date_ok(gf_start_2,gf_end_2):
                    with db() as c:
                        sql="""
                        SELECT COUNT(DISTINCT t.id) AS total_tr,
                               COUNT(s.id) AS exams,
                               COALESCE(AVG(s.percent),0) AS avg_pct,
                               COALESCE(SUM(CASE WHEN s.passed=1 THEN 1 ELSE 0 END),0) AS passed_cnt
                        FROM trainees t JOIN exam_sessions s ON s.trainee_id=t.id
                        LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name)
                        WHERE s.status='submitted' AND COALESCE(t.hidden,0)=0 AND t.facility=?
                          AND {rep_scope_sql}
                          AND date(s.submitted_at)>=date(?) AND date(s.submitted_at)<=date(?)
                        """
                        p1=c.execute(sql.format(rep_scope_sql=rep_scope_sql), tuple([sel_fac_rep] + rep_scope_args + [gf_start_1.isoformat(),gf_end_1.isoformat()])).fetchone()
                        p2=c.execute(sql.format(rep_scope_sql=rep_scope_sql), tuple([sel_fac_rep] + rep_scope_args + [gf_start_2.isoformat(),gf_end_2.isoformat()])).fetchone()

                    def _stat(row):
                        return (int(row["total_tr"] or 0),int(row["exams"] or 0),int(row["passed_cnt"] or 0),_pct(row["avg_pct"]))
                    a=_stat(p1); b=_stat(p2)
                    group_delta_pct = b[3] - a[3]
                    group_delta_tr = b[0] - a[0]
                    group_delta_exams = b[1] - a[1]
                    group_delta_passed = b[2] - a[2]
                    group_compare_html=f"""
                    <div style="font-family:'Cairo',sans-serif;direction:rtl;padding:10px;">
                    <h3 style="color:#047857;text-align:center;">تقرير مقارنة أداء وحدة الأمراض المتوطنة: {esc(sel_fac_rep)}</h3>
                    <table style="width:100%;border-collapse:collapse;font-size:10pt;">
                    <tr><th>الفترة</th><th>إجمالي المتدربين</th><th>الاختبارات</th><th>المجتازون</th><th>متوسط النسبة %</th></tr>
                    <tr><td>{gf_start_1} إلى {gf_end_1}</td><td>{a[0]}</td><td>{a[1]}</td><td>{a[2]}</td><td>{a[3]:.1f}%</td></tr>
                    <tr><td>{gf_start_2} إلى {gf_end_2}</td><td>{b[0]}</td><td>{b[1]}</td><td>{b[2]}</td><td>{b[3]:.1f}%</td></tr>
                    <tr><td colspan="5" style="border:1px solid #059669;padding:7px;background:#ecfdf5;font-weight:900;color:#065f46;text-align:center;">الفارق (الثانية − الأولى): المتدربون {group_delta_tr:+d} | الاختبارات {group_delta_exams:+d} | المجتازون {group_delta_passed:+d} | متوسط النسبة {group_delta_pct:+.1f} نقطة مئوية</td></tr>
                    </table></div>"""
                    st.markdown(group_compare_html,unsafe_allow_html=True)
                    st.markdown("##### 📊 الرسم البياني لمقارنة أداء الوحدة")
                    chart_group = pd.DataFrame({"الفترة": ["الفترة الأولى", "الفترة الثانية"], "متوسط النسبة %": [a[3], b[3]]}).set_index("الفترة")
                    st.bar_chart(chart_group, use_container_width=True)
                    chart_group_html = report_chart_html("الرسم البياني — مقارنة أداء الوحدة", ["الفترة الأولى", "الفترة الثانية"], [a[3], b[3]], "%")
                    render_print_button_only(generate_general_report_html("الرسم البياني لمقارنة أداء الوحدة", chart_group_html), f"طباعة رسم مقارنة الوحدة {sel_fac_rep}")
                    df_group=pd.DataFrame([
                        {"وحدة الأمراض المتوطنة":sel_fac_rep,"الفترة":f"{gf_start_1} إلى {gf_end_1}","إجمالي المتدربين":a[0],"الاختبارات":a[1],"المجتازون":a[2],"متوسط النسبة %":f"{a[3]:.1f}%"},
                        {"وحدة الأمراض المتوطنة":sel_fac_rep,"الفترة":f"{gf_start_2} إلى {gf_end_2}","إجمالي المتدربين":b[0],"الاختبارات":b[1],"المجتازون":b[2],"متوسط النسبة %":f"{b[3]:.1f}%","الفارق (الثانية - الأولى)":f"{group_delta_pct:+.1f} نقطة مئوية"}
                    ])
                    _excel_download(df_group,"📥 تحميل التقرير الجماعي للوحدة (.xlsx)",f"facility_report_{sel_fac_rep}.xlsx","dl_group_report_v7")
                    render_print_button_only(generate_general_report_html(f"مقارنة أداء وحدة الأمراض المتوطنة: {sel_fac_rep}",group_compare_html),f"مقارنة فترات وحدة {sel_fac_rep}")

        with rep_tab3:
            st.markdown("#### 📋 التقرير الشامل لجميع نتائج المتدربين الظاهرين")
            with db() as c:
                rows=c.execute("""
                    SELECT t.id,t.name,t.profession,t.facility,
                           s.score,s.max_score,s.percent,s.passed,s.submitted_at,
                           e.exam_type,e.name AS template_name
                    FROM trainees t
                    LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name)
                    LEFT JOIN exam_sessions s ON s.trainee_id=t.id AND s.status='submitted'
                    LEFT JOIN exam_templates e ON e.id=s.template_id
                    WHERE COALESCE(t.hidden,0)=0 AND {rep_scope_sql}
                    ORDER BY t.id DESC,s.id DESC
                """.format(rep_scope_sql=rep_scope_sql), tuple(rep_scope_args)).fetchall()
                # رقم الشهادة اختياري حتى لا يتعطل التقرير مع قاعدة قديمة.
                cols=[r[1] for r in c.execute("PRAGMA table_info(exam_sessions)").fetchall()]
                has_cert="certificate_id" in cols
                if has_cert:
                    rows=c.execute("""
                        SELECT t.id,t.name,t.profession,t.facility,s.score,s.max_score,s.percent,s.passed,
                               s.certificate_id,s.submitted_at,e.exam_type,e.name AS template_name
                        FROM trainees t
                        LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name)
                        LEFT JOIN exam_sessions s ON s.trainee_id=t.id AND s.status='submitted'
                        LEFT JOIN exam_templates e ON e.id=s.template_id
                        WHERE COALESCE(t.hidden,0)=0 AND {rep_scope_sql} ORDER BY t.id DESC,s.id DESC
                    """.format(rep_scope_sql=rep_scope_sql), tuple(rep_scope_args)).fetchall()

            data=[]
            for r in rows:
                data.append({
                    "مسلسل":r["id"],"اسم المتدرب":r["name"] or "","الوظيفة":r["profession"] or "",
                    "وحدة الأمراض المتوطنة":r["facility"] or "","تصنيف الاختبار":r["exam_type"] or "-",
                    "الدرجة":f"{r['score'] or 0}/{r['max_score'] or 0}" if r["score"] is not None else "-",
                    "النسبة المئوية %":f"{_pct(r['percent']):.1f}%" if r["percent"] is not None else "-",
                    "الحالة":_status(r["passed"]),"رقم الشهادة":(r["certificate_id"] or "-") if has_cert else "-",
                    "التاريخ":r["submitted_at"] or "-"
                })
            df_rep=pd.DataFrame(data)
            if df_rep.empty: st.info("لا توجد بيانات متدربين ظاهرة لعرضها في التقرير.")
            else:
                st.dataframe(df_rep,use_container_width=True,hide_index=True)
                st.markdown("##### 📊 الرسم البياني لحالة النتائج")
                pass_count = int(sum(1 for r in data if r["الحالة"] == "اجتزت بنجاح"))
                fail_count = int(sum(1 for r in data if r["الحالة"] == "لم تجتز"))
                no_result_count = int(sum(1 for r in data if r["الحالة"] == "لا توجد نتيجة"))
                chart_all = pd.DataFrame({"الحالة": ["اجتزت بنجاح", "لم تجتز", "لا توجد نتيجة"], "العدد": [pass_count, fail_count, no_result_count]}).set_index("الحالة")
                st.bar_chart(chart_all, use_container_width=True)
                chart_all_html = report_chart_html("الرسم البياني — حالة النتائج", ["اجتاز بنجاح", "لم يجتز", "لا توجد نتيجة"], [pass_count, fail_count, no_result_count], "")
                render_print_button_only(generate_general_report_html("الرسم البياني لحالة النتائج", chart_all_html), "طباعة رسم حالة النتائج")
                _excel_download(df_rep,"📥 تحميل تقرير النتائج الشامل (.xlsx)","all_trainees_results.xlsx","dl_all_results_v7")
                table_html=df_rep.to_html(index=False,border=0,classes="table")
                render_print_button_only(generate_general_report_html("تقرير نتائج المتدربين الشامل",f"<div>{table_html}</div>"),"تقرير النتائج الشامل")

        with rep_tab4:
            st.markdown("#### 📈 تحليل أداء جميع الجهات والوحدات")
            with db() as c:
                rows=c.execute("""
                    SELECT t.facility AS facility,
                           COUNT(DISTINCT t.id) AS trainees_count,
                           COUNT(s.id) AS exams_count,
                           COALESCE(SUM(CASE WHEN s.passed=1 THEN 1 ELSE 0 END),0) AS passed_count,
                           COALESCE(AVG(s.percent),0) AS avg_pct
                    FROM trainees t
                    LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name)
                    LEFT JOIN exam_sessions s ON s.trainee_id=t.id AND s.status='submitted'
                    WHERE COALESCE(t.hidden,0)=0 AND t.facility IS NOT NULL AND TRIM(t.facility)<>'' AND {rep_scope_sql}
                    GROUP BY t.facility ORDER BY avg_pct DESC,t.facility
                """.format(rep_scope_sql=rep_scope_sql), tuple(rep_scope_args)).fetchall()
            df_fac=pd.DataFrame([{
                "وحدة الأمراض المتوطنة / الجهة":r["facility"] or "",
                "إجمالي المتدربين":int(r["trainees_count"] or 0),
                "إجمالي الاختبارات":int(r["exams_count"] or 0),
                "المجتازون":int(r["passed_count"] or 0),
                "متوسط النسبة %":round(_pct(r["avg_pct"]),1)
            } for r in rows])
            if df_fac.empty: st.info("لا توجد بيانات جهات أو وحدات لتحليلها.")
            else:
                st.dataframe(df_fac,use_container_width=True,hide_index=True)
                st.markdown("##### 📊 الرسم البياني لمتوسط أداء الجهات")
                chart_fac = df_fac[["وحدة الأمراض المتوطنة / الجهة", "متوسط النسبة %"]].set_index("وحدة الأمراض المتوطنة / الجهة")
                st.bar_chart(chart_fac, use_container_width=True)
                chart_fac_html = report_chart_html("الرسم البياني — متوسط أداء الجهات", df_fac["وحدة الأمراض المتوطنة / الجهة"].tolist(), df_fac["متوسط النسبة %"].tolist(), "%")
                render_print_button_only(generate_general_report_html("الرسم البياني لمتوسط أداء الجهات", chart_fac_html), "طباعة رسم أداء الجهات")
                _excel_download(df_fac,"📥 تحميل تقرير أداء الجهات ووحدات المتوطنة (.xlsx)","facilities_performance_report.xlsx","dl_fac_report_v7")
                table_fac_html=df_fac.to_html(index=False,border=0,classes="table")
                render_print_button_only(generate_general_report_html("تقرير أداء وحدات الأمراض المتوطنة والجهات",f"<div>{table_fac_html}</div>"),"تقرير أداء الجهات")

        with rep_tab5:
            st.markdown("#### 🏆 عرض نتائج الاختبارات مع الفلترة والطباعة الفردية والجماعية")
            with db() as c:
                all_sessions_results=c.execute("""
                    SELECT s.id AS session_id,t.name AS trainee_name,t.facility,t.profession AS trainee_profession,
                           s.score,s.max_score,s.percent,s.passed,e.name AS template_name,e.exam_type,s.submitted_at
                    FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id
                    LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name)
                    LEFT JOIN exam_templates e ON e.id=s.template_id
                    WHERE s.status='submitted' AND COALESCE(t.hidden,0)=0 AND {rep_scope_sql}
                    ORDER BY COALESCE(s.percent,0) DESC,s.id DESC
                """.format(rep_scope_sql=rep_scope_sql), tuple(rep_scope_args)).fetchall()
            if not all_sessions_results:
                st.info("لا توجد اختبارات مكتملة أو نتائج مسجلة حتى الآن.")
            else:
                st.markdown("##### 📊 الرسم البياني العام للنتائج")
                chart_results_base = pd.DataFrame([{
                    "الفئة": "مجتازون",
                    "العدد": int(sum(1 for r in all_sessions_results if r["passed"] == 1))
                }, {
                    "الفئة": "غير مجتازين",
                    "العدد": int(sum(1 for r in all_sessions_results if r["passed"] == 0))
                }]).set_index("الفئة")
                st.bar_chart(chart_results_base, use_container_width=True)
                chart_results_html = report_chart_html("الرسم البياني — النتائج العامة", ["مجتازون", "غير مجتازين"], [int(sum(1 for r in all_sessions_results if r["passed"] == 1)), int(sum(1 for r in all_sessions_results if r["passed"] == 0))], "")
                render_print_button_only(generate_general_report_html("الرسم البياني العام للنتائج", chart_results_html), "طباعة الرسم البياني العام")
                filter_mode=st.radio("فلترة النتائج:",["عرض الكل (مرتبة تنازلياً)","فقط الأعلى تقييماً (النسبة >= 85%)","فقط المجتازين بنجاح"],horizontal=True,key="rep_filter_mode_v7")
                filtered_sessions=[]
                for r in all_sessions_results:
                    pct=_pct(r["percent"]); passed=(r["passed"]==1)
                    if "الأعلى تقييماً" in filter_mode and pct<85: continue
                    if "المجتازين بنجاح" in filter_mode and not passed: continue
                    filtered_sessions.append(r)
                st.write(f"📊 عدد النتائج المعروضة بعد الفلترة: **{len(filtered_sessions)}** نتيجة.")
                if filtered_sessions:
                    df_res=pd.DataFrame([{
                        "رقم الاختبار":r["session_id"],"المتدرب":r["trainee_name"] or "","الوظيفة":r["trainee_profession"] or "",
                        "وحدة الأمراض المتوطنة":r["facility"] or "","الاختبار":f"{r['template_name'] or 'اختبار معتمد'} ({r['exam_type'] or 'قبل التدريب'})",
                        "الدرجة":f"{r['score'] or 0}/{r['max_score'] or 0}","النسبة %":f"{_pct(r['percent']):.1f}%",
                        "الحالة":_status(r["passed"]),"التاريخ":r["submitted_at"] or "-"
                    } for r in filtered_sessions])
                    st.dataframe(df_res,use_container_width=True,hide_index=True)
                    _excel_download(df_res,"📥 تحميل النتائج المفلترة (.xlsx)","filtered_results.xlsx","dl_filtered_results_v7")

                    st.markdown("---")
                    print_choice_mode=st.radio("اختر نوع طباعة النتائج:",["طباعة نتيجة ممتحن فردي محدد","طباعة نتائج جميع الممتحنين الظاهرين (القائمة المعروضة)"],horizontal=True,key="rep_print_mode_v7")
                    if "فردي محدد" in print_choice_mode:
                        single_map={f"المتدرب: {r['trainee_name'] or ''} | النسبة: {_pct(r['percent']):.1f}% | الجهة: {r['facility'] or ''} (ID: {r['session_id']})":r["session_id"] for r in filtered_sessions}
                        sel_single=st.selectbox("اختر الممتحن لطباعة تقرير نتيجته المفصلة:",list(single_map.keys()),key="rep_print_session_v7")
                        render_print_button_only(generate_trainee_exam_sheet_html(single_map[sel_single]),f"تقرير نتيجة الممتحن رقم {single_map[sel_single]}")
                    else:
                        combined="".join(generate_trainee_exam_sheet_html(r["session_id"])+"<div style='page-break-after:always;'></div>" for r in filtered_sessions)
                        render_print_button_only(combined,"طباعة نتائج جميع الممتحنين")
                else:
                    st.warning("⚠️ لا توجد نتائج تطابق شروط الفلترة المحددة.")

    elif selected_menu == "📈 خطط العمل":
        st.subheader("📈 خطط العمل التدريبية ومعالجة نقاط الضعف بالأمراض المتوطنة (مع إمكانية الحذف)")
        plan_tabs = st.tabs(["➕ إنشاء وتحديث خطة عمل ذكية", "📋 استعراض وإدارة خطط العمل المسجلة", "📄 محاضر التدريب"])
        with plan_tabs[0]:
            st.markdown("#### 🏥 تحديد نطاق خطة العمل حسب الهيكل الإداري")
            plan_scope = hierarchy_scope_widget("نطاق خطة العمل:", "plan_scope_v12")
            plan_scope_sql, plan_scope_args = hierarchy_scope_sql("h", plan_scope)
            with db() as c:
                all_tr_list = c.execute(
                    f"SELECT DISTINCT t.id, t.name, t.facility, t.profession FROM trainees t LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name) WHERE t.hidden=0 AND {plan_scope_sql} ORDER BY t.id ASC",
                    tuple(plan_scope_args)
                ).fetchall()
                all_fac_list = [row[0] for row in c.execute(
                    f"SELECT DISTINCT t.facility FROM trainees t LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name) WHERE t.facility IS NOT NULL AND t.facility != '' AND t.hidden=0 AND {plan_scope_sql} ORDER BY t.facility",
                    tuple(plan_scope_args)
                ).fetchall()]
            with st.form("create_action_plan_form"):
                target_category = st.radio("نطاق الخطة:", ["فرد (متدرب محدد)", "جماعة (وحدة الأمراض المتوطنة بالكامل)"], horizontal=True)
                auto_weakness_text = ""
                auto_steps_text = ""
                if "فرد" in target_category:
                    if not all_tr_list:
                        st.warning("⚠ لا توجد بيانات متدربين ظاهرة مسجلة بعد.")
                        target_name = ""
                    else:
                        tr_choices = {f"{t['name']} - الوظيفة: {t['profession']} - الجهة: {t['facility']} (ID: {t['id']})": t for t in all_tr_list}
                        sel_tr_label = st.selectbox("اختر المتدرب لاستخراج نقاط ضعفه تلقائياً:", list(tr_choices.keys()))
                        chosen_tr_obj = tr_choices[sel_tr_label]
                        target_name = chosen_tr_obj['name']
                        with db() as c:
                            incorrect_qs = c.execute("""
                                SELECT q.category, q.question, eq.selected_option, q.answer
                                FROM exam_questions eq JOIN questions q ON q.id=eq.question_id
                                JOIN exam_sessions s ON s.id=eq.session_id
                                WHERE s.trainee_id=? AND eq.is_correct=0
                            """, (chosen_tr_obj['id'],)).fetchall()
                        if incorrect_qs:
                            failed_cats = list(set([r['category'] for r in incorrect_qs]))
                            auto_weakness_text = f"تم رصد إخفاقات للمتدرب {target_name} في الأقسام التالية بناءً على نتائج الاختبارات الأخيرة:\n- " + "\n- ".join(failed_cats)
                            auto_steps_text = f"1. عقد جلسة تدريب مركزة ومكثفة للأقسام التالية: {', '.join(failed_cats)}.\n2. إعادة الاختبار العملي والنظري بعد استكمال البرنامج العلاجي.\n3. متابعة أداء المتدرب الميداني داخل الوحدة."
                        else:
                            auto_weakness_text = "لم يتم رصد إخفاقات واضحة أو اجتاز المتدرب كافة الأسئلة بنجاح."
                            auto_steps_text = "1. استمرار المتابعة الدورية وتحفيز المتدرب.\n2. إدراج المتدرب في دورات تنشيطية متقدمة للأمراض المتوطنة."
                else:
                    if not all_fac_list:
                        st.warning("⚠ لا توجد وحدات أو جهات ظاهرة مسجلة بعد.")
                        target_name = ""
                    else:
                        target_name = st.selectbox("اختر وحدة الأمراض المتوطنة المستهدفة:", all_fac_list)
                        with db() as c:
                            fac_incorrect = c.execute("""
                                SELECT q.category FROM exam_questions eq
                                JOIN questions q ON q.id=eq.question_id
                                JOIN exam_sessions s ON s.id=eq.session_id
                                JOIN trainees t ON t.id=s.trainee_id
                                WHERE t.facility=? AND t.hidden=0 AND eq.is_correct=0
                            """, (target_name,)).fetchall()
                        if fac_incorrect:
                            fac_cats = list(set([r['category'] for r in fac_incorrect]))
                            auto_weakness_text = f"تم رصد نقاط ضعف متكررة لكوادر وحدة ({target_name}) في الأقسام التالية:\n- " + "\n- ".join(fac_cats)
                            auto_steps_text = f"1. تنفيذ برنامج تدريبي جماعي للعاملين بالوحدة يركز على: {', '.join(fac_cats)}.\n2. توفير الأدلة الإرشادية والمواد التعليمية داخل وحدة الأمراض المتوطنة.\n3. تقييم العاملين بعد أسبوعين من تاريخ الخطة."
                        else:
                            auto_weakness_text = "مستوى العاملين بالوحدة مستقر وتجتاز الاختبارات بكفاءة."
                            auto_steps_text = "1. الحفاظ على مستوى الأداء المتميز.\n2. إجراء تقييم فصلي دوري."
                st.markdown("---")
                st.markdown("#### 🎯 نقاط الضعف (تم استنتاجها وتحليلها تلقائياً):")
                weak_areas = st.text_area("أبرز نقاط الضعف والأقسام المرصودة:", value=auto_weakness_text)
                st.markdown("#### 🛠 الخطوات الإجرائية والبرنامج التدريبي المقترح:")
                action_steps = st.text_area("الخطوات العلاجية:", value=auto_steps_text)
                st.markdown("---")
                current_online_dt = now_cairo().date()
                st.markdown("#### 📅 تحديد الإطار الزمني للخطة (من تاريخ إلى تاريخ):")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    plan_start_date = st.date_input("من تاريخ البدء:", current_online_dt)
                with col_d2:
                    plan_end_date = st.date_input("إلى تاريخ النهاية:", current_online_dt + timedelta(days=30))
                with db() as c:
                    all_plan_templates = [dict(r) for r in c.execute("SELECT * FROM exam_templates WHERE active=1 ORDER BY name ASC").fetchall()]
                applicable_plan_templates = [t for t in all_plan_templates if template_matches_scope(t, plan_scope)]
                plan_template_options = {"بدون نموذج اختبار محدد": None}
                for t in applicable_plan_templates:
                    plan_template_options[f"{t['name']} ({t.get('exam_type') or 'اختبار'}) — {template_scope_text(t)} | رقم {t['id']}"] = int(t['id'])
                selected_plan_template_label = st.selectbox("نموذج الاختبار المرتبط بخطة العمل:", list(plan_template_options.keys()), key="action_plan_template_choice")
                selected_plan_template_id = plan_template_options[selected_plan_template_label]
                if st.form_submit_button("💾 حفظ وإنشاء خطة العمل الذكية", use_container_width=True):
                    if not target_name.strip() or not weak_areas.strip():
                        st.warning("⚠ يرجى استكمال البيانات.")
                    else:
                        with db() as c:
                            c.execute("""INSERT INTO action_plans(
                                target_type, target_name, weakness_areas, action_steps, time_frame_type, start_date, end_date, created_at,
                                scope_governorate, scope_authority, scope_center, scope_administration, scope_facility, template_id
                            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                      (target_category, target_name, weak_areas.strip(), action_steps.strip(), "من تاريخ إلى تاريخ",
                                       plan_start_date.isoformat(), plan_end_date.isoformat(), now(),
                                       plan_scope["scope_governorate"], plan_scope["scope_authority"], plan_scope["scope_center"],
                                       plan_scope["scope_administration"], plan_scope["scope_facility"], selected_plan_template_id))
                        st.success("✅ تم حفظ خطة العمل بناءً على التحليل التلقائي بنجاح!")
                        st.rerun()
        with plan_tabs[1]:
            with db() as c:
                plans_list = c.execute(
                    f"SELECT * FROM action_plans WHERE " + " AND ".join([f"{k}=?" for k in ["scope_governorate","scope_authority","scope_center","scope_administration","scope_facility"] if str(plan_scope.get(k) or "").strip()]) + " ORDER BY id DESC",
                    tuple(str(plan_scope.get(k) or "").strip() for k in ["scope_governorate","scope_authority","scope_center","scope_administration","scope_facility"] if str(plan_scope.get(k) or "").strip())
                ).fetchall() if any(str(plan_scope.get(k) or "").strip() for k in ["scope_governorate","scope_authority","scope_center","scope_administration","scope_facility"]) else c.execute("SELECT * FROM action_plans ORDER BY id DESC").fetchall()
            if not plans_list:
                st.info("لا توجد خطط عمل مسجلة حتى الآن.")
            else:
                plan_map = {f"خطة رقم ({p['id']}) - [{p['target_type']}] المستهدف: {p['target_name']} | الهيكل: {template_scope_text(dict(p))} (من {p['start_date']} إلى {p['end_date']})": p['id'] for p in plans_list}
                sel_plan_label = st.selectbox("اختر خطة العمل للمعاينة والطباعة الذكية:", list(plan_map.keys()))
                chosen_plan_id = plan_map[sel_plan_label]
                with db() as c:
                    p_data = dict(c.execute("SELECT * FROM action_plans WHERE id=?", (chosen_plan_id,)).fetchone())
                plan_tpl_name = "بدون نموذج اختبار محدد"
                if p_data.get("template_id"):
                    with db() as c:
                        plan_tpl_row = c.execute("SELECT name, exam_type FROM exam_templates WHERE id=?", (p_data["template_id"],)).fetchone()
                    if plan_tpl_row:
                        plan_tpl_name = f"{plan_tpl_row['name']} ({plan_tpl_row['exam_type'] or 'اختبار'})"
                plan_detail_html = f"""
                <div style="font-family: 'Cairo', sans-serif; direction: rtl; padding: 5px; page-break-inside: avoid; break-inside: avoid;">
                    <h3 style="color: #047857; text-align: center; font-size: 14pt; margin: 5px 0;">خطة عمل لعلاج نقاط الضعف وتحسين الأداء بوحدات الأمراض المتوطنة</h3>
                    <hr style="border: 1px solid #059669; margin: 8px 0;">
                    <p style="font-size: 9.5pt; margin: 4px 0;"><b>نوع النطاق:</b> {esc(p_data['target_type'])} | <b>المستهدف:</b> {esc(p_data['target_name'])} | <b>الهيكل الإداري:</b> {esc(template_scope_text(p_data))} | <b>نموذج الاختبار:</b> {esc(plan_tpl_name)} | <b>الفترة الزمنية:</b> من {esc(p_data['start_date'])} إلى {esc(p_data['end_date'])}</p>
                    <div style="background: #f0fdf4; border: 1px solid #059669; padding: 8px; border-radius: 6px; margin: 10px 0; page-break-inside: avoid; break-inside: avoid;">
                        <h4 style="color: #065f46; margin-top: 0; font-size: 10.5pt;">🎯 نقاط الضعف المرصودة (بناءً على التقييم الآلي):</h4>
                        <p style="white-space: pre-wrap; margin-bottom: 0; font-size: 9.5pt;">{esc(p_data['weakness_areas'])}</p>
                    </div>
                    <div style="background: #ffffff; border: 1px solid #cbd5e1; padding: 8px; border-radius: 6px; margin: 10px 0; page-break-inside: avoid; break-inside: avoid;">
                        <h4 style="color: #065f46; margin-top: 0; font-size: 10.5pt;">🛠 الخطوات الإجرائية والبرنامج العلاجي والتدريبي:</h4>
                        <p style="white-space: pre-wrap; margin-bottom: 0; font-size: 9.5pt;">{esc(p_data['action_steps'])}</p>
                    </div>
                </div>
                """
                st.markdown(plan_detail_html, unsafe_allow_html=True)
                full_plan_print_html = generate_action_plan_report_html(f"خطة عمل - {p_data['target_name']}", plan_detail_html, header_text=hierarchy_header_html(p_data), hierarchy_scope=p_data)
                render_print_button_only(full_plan_print_html, f"خطة عمل رقم {chosen_plan_id}")
                if st.button("🗑 حذف خططة العمل المحددة", use_container_width=True):
                    with db() as c:
                        c.execute("DELETE FROM action_plans WHERE id=?", (chosen_plan_id,))
                    st.success("✅ تم حذف خطة العمل بنجاح!")
                    st.rerun()

        with plan_tabs[2]:
            st.markdown("#### 📄 طباعة وتعديل محضر التدريب:")
            # قائمة الهيكل الإداري داخل محاضر التدريب نفسها، وليست في تبويب آخر.
            minutes_scope = hierarchy_scope_widget("الهيكل الإداري لمحضر التدريب:", "training_minutes_scope_v1")
            with db() as c:
                all_tpls_for_minutes = [dict(r) for r in c.execute("SELECT * FROM exam_templates ORDER BY name ASC").fetchall()]
            all_tpls_for_minutes = [t for t in all_tpls_for_minutes if template_matches_scope(t, minutes_scope)]
            if not all_tpls_for_minutes:
                st.info("لا توجد نماذج اختبارات مسجلة تطابق الهيكل الإداري المحدد.")
            else:
                minutes_tpl_map = {f"نموذج ({t['id']}) - {t['name']} [{t['exam_type']}] | {template_scope_text(t)}": t['id'] for t in all_tpls_for_minutes}
                sel_min_tpl_label = st.selectbox("اختر نموذج الاختبار لإنشاء أو تعديل محضر التدريب الخاص به:", list(minutes_tpl_map.keys()), key="sel_min_tpl")
                chosen_min_tpl_id = minutes_tpl_map[sel_min_tpl_label]

                with db() as c:
                    existing_min = c.execute("SELECT * FROM training_minutes WHERE template_id=?", (chosen_min_tpl_id,)).fetchone()
                    tpl_rec = c.execute("SELECT * FROM exam_templates WHERE id=?", (chosen_min_tpl_id,)).fetchone()

                # توليد بيانات محضر التدريب تلقائياً من نموذج الاختبار ونطاقه الإداري.
                tpl_dict_for_minutes = dict(tpl_rec) if tpl_rec else {}
                minute_scope_parts = [str(tpl_dict_for_minutes.get(k) or '').strip() for k in ('scope_authority', 'scope_administration', 'scope_facility')]
                minute_scope_parts = [x for x in minute_scope_parts if x]
                default_facility_val = " - ".join(minute_scope_parts) if minute_scope_parts else "كل الهيكل الإداري"
                default_min_text = (
                    f"إيماءً إلى خطة التدريب والإشراف الفني بوحدات الأمراض المتوطنة، "
                    f"وبناءً على نموذج الاختبار ({tpl_rec['name'] if tpl_rec else ''})، "
                    f"تم عقد التدريب للعاملين ضمن النطاق الإداري: {default_facility_val}. "
                    f"ويستهدف التدريب رفع الكفاءة الفنية وتحسين جودة الأداء وفق متطلبات النموذج."
                )
                default_items_text = (
                    f"1. التعريف بأهداف ومتطلبات نموذج الاختبار ({tpl_rec['name'] if tpl_rec else ''}).\n"
                    f"2. مراجعة المهارات والمعايير الفنية المرتبطة بالمهنة: {tpl_rec['profession'] if tpl_rec and tpl_rec['profession'] else 'جميع الوظائف المستهدفة'}.\n"
                    "3. مناقشة إجراءات الفحص والتشخيص ومكافحة الأمراض المتوطنة.\n"
                    "4. مراجعة السجلات والتقارير والتدابير الوقائية ومعايير الجودة."
                )
                default_goals_text = (
                    f"1. رفع كفاءة العاملين في نطاق {default_facility_val}.\n"
                    "2. تحسين جودة الفحوصات والإجراءات الفنية المرتبطة بنموذج الاختبار.\n"
                    "3. توحيد تطبيق المعايير القياسية والتدابير الوقائية.\n"
                    "4. تحديد احتياجات المتابعة وقياس التحسن بعد التدريب."
                )
                default_date_val = now_cairo().strftime('%Y-%m-%d')

                cur_min_text = existing_min["minutes_text"] if existing_min and existing_min["minutes_text"] else default_min_text
                cur_items_text = existing_min["training_items"] if existing_min and existing_min["training_items"] else default_items_text
                cur_goals_text = existing_min["training_goals"] if existing_min and existing_min["training_goals"] else default_goals_text
                cur_date_val = existing_min["training_date"] if existing_min and existing_min["training_date"] else default_date_val
                cur_facility_val = existing_min["facility_name"] if existing_min and existing_min["facility_name"] else default_facility_val

                with st.form(f"edit_training_minutes_form_{chosen_min_tpl_id}"):
                    st.markdown("##### ✏ تعديل محضر التدريب والبنود والأهداف:")
                    edited_facility_input = st.text_input("اسم المنشأة / جهة العمل:", value=cur_facility_val)
                    edited_date_input = st.text_input("تاريخ محضر التدريب:", value=cur_date_val)
                    edited_minutes_input = st.text_area("1. محضر التدريب:", value=cur_min_text, height=120)
                    edited_items_input = st.text_area("2. بنود التدريب:", value=cur_items_text, height=140)
                    edited_goals_input = st.text_area("3. الأهداف من التدريب:", value=cur_goals_text, height=140)

                    if st.form_submit_button("💾 حفظ التعديلات على محضر التدريب", use_container_width=True):
                        with db() as c:
                            c.execute("""INSERT INTO training_minutes(template_id, minutes_text, training_items, training_goals, training_date, facility_name, updated_at) VALUES(?,?,?,?,?,?,?)
                                       ON CONFLICT(template_id) DO UPDATE SET minutes_text=excluded.minutes_text, training_items=excluded.training_items, training_goals=excluded.training_goals, training_date=excluded.training_date, facility_name=excluded.facility_name, updated_at=excluded.updated_at""",
                                      (chosen_min_tpl_id, edited_minutes_input.strip(), edited_items_input.strip(), edited_goals_input.strip(), edited_date_input.strip(), edited_facility_input.strip(), now()))
                        st.success("✅ تم حفظ وتعديل محضر التدريب بنجاح!")
                        st.rerun()

                st.markdown("---")
                st.markdown("##### 🖨 معاينة وطباعة محضر التدريب:")
                print_sett_m = get_print_settings()
                # ترويسة المحضر تتبع الهيكل الإداري المرتبط بنموذج الاختبار المختار.
                header_right_txt = hierarchy_header_html(minutes_scope) if any(str(minutes_scope.get(k) or '').strip() for k in ('scope_authority','scope_administration','scope_facility')) else hierarchy_header_html(tpl_dict_for_minutes)
                line_sp_m = print_sett_m.get('line_spacing', 1.25)

                # أسماء المتدربين تتعبأ تلقائياً وفق نطاق النموذج والمهنة والتخصيص الحالي.
                with db() as c:
                    all_minutes_trainees = [dict(r) for r in c.execute(
                        "SELECT id, name, profession, facility, assigned_template_id FROM trainees WHERE COALESCE(hidden,0)=0 ORDER BY name COLLATE NOCASE"
                    ).fetchall()]
                hierarchy_rows_minutes = get_hierarchical_data(include_hidden=False)
                matching_minutes_trainees = []
                minutes_has_scope = any(str(minutes_scope.get(k) or '').strip() for k in ('scope_authority', 'scope_administration', 'scope_facility'))
                template_has_scope = any(str(tpl_dict_for_minutes.get(k) or '').strip() for k in ('scope_authority', 'scope_administration', 'scope_facility'))
                for trainee_row in all_minutes_trainees:
                    if not template_matches_profession(tpl_dict_for_minutes, trainee_row.get('profession')):
                        continue
                    assigned_id = trainee_row.get('assigned_template_id')
                    if assigned_id not in (None, 0, chosen_min_tpl_id):
                        continue
                    if trainee_row.get('assigned_template_id') not in (None, 0, chosen_min_tpl_id):
                        continue
                    if not minutes_has_scope and not template_has_scope:
                        # النموذج العام يشمل المتدربين غير المخصصين لنموذج آخر.
                        matching_minutes_trainees.append(trainee_row)
                        continue
                    matching_scope_rows = [hrow for hrow in hierarchy_rows_minutes
                        if (not minutes_scope.get('scope_authority') or hrow.get('authority') == minutes_scope.get('scope_authority'))
                        and (not minutes_scope.get('scope_administration') or hrow.get('administration') == minutes_scope.get('scope_administration'))
                        and (not minutes_scope.get('scope_facility') or hrow.get('facility_name') == minutes_scope.get('scope_facility'))
                        and (not tpl_dict_for_minutes.get('scope_authority') or hrow.get('authority') == tpl_dict_for_minutes.get('scope_authority'))
                        and (not tpl_dict_for_minutes.get('scope_administration') or hrow.get('administration') == tpl_dict_for_minutes.get('scope_administration'))
                        and (not tpl_dict_for_minutes.get('scope_facility') or hrow.get('facility_name') == tpl_dict_for_minutes.get('scope_facility'))]
                    if any(trainee_matches_hierarchy(trainee_row.get('facility'), hrow) for hrow in matching_scope_rows):
                        matching_minutes_trainees.append(trainee_row)

                final_min_t = edited_minutes_input if 'edited_minutes_input' in locals() else cur_min_text
                final_items_t = edited_items_input if 'edited_items_input' in locals() else cur_items_text
                final_goals_t = edited_goals_input if 'edited_goals_input' in locals() else cur_goals_text
                final_date_t = edited_date_input if 'edited_date_input' in locals() else cur_date_val
                final_fac_t = edited_facility_input if 'edited_facility_input' in locals() else cur_facility_val

                days_ar = {
                    'Monday': 'الإثنين', 'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء',
                    'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت', 'Sunday': 'الأحد'
                }
                day_name_str = ""
                try:
                    parsed_dt = datetime.strptime(final_date_t.strip(), "%Y-%m-%d")
                    eng_day = parsed_dt.strftime("%A")
                    day_name_str = days_ar.get(eng_day, "")
                except:
                    pass
                
                date_display_block = (f"<b>اليوم:</b> {day_name_str}<br>" if day_name_str else "") + f"<b>التاريخ:</b> {final_date_t}"

                def build_minutes_signature_rows(trainee_slice, start_index):
                    rows_html = ""
                    for offset in range(6):
                        trainee_row = trainee_slice[offset] if offset < len(trainee_slice) else None
                        row_num = start_index + offset
                        trainee_name = esc(trainee_row.get('name') or '') if trainee_row else '&nbsp;'
                        trainee_prof = esc(trainee_row.get('profession') or '') if trainee_row else '&nbsp;'
                        rows_html += f"""
                        <tr>
                            <td style="border: 1px solid #059669; padding: 3px; text-align: center; font-size: 10pt; width: 12%;">{row_num}</td>
                            <td style="border: 1px solid #059669; padding: 3px; text-align: right; font-size: 10pt; width: 50%;">{trainee_name}</td>
                            <td style="border: 1px solid #059669; padding: 3px; text-align: right; font-size: 10pt; width: 38%;">{trainee_prof}</td>
                        </tr>
                        """
                    return rows_html

                signatures_rows_html = build_minutes_signature_rows(matching_minutes_trainees[:6], 1)
                signatures_rows_b_html = build_minutes_signature_rows(matching_minutes_trainees[6:12], 7)
                if matching_minutes_trainees:
                    st.caption(f"تم العثور على {len(matching_minutes_trainees)} متدرب مطابق للهيكل الإداري والمهنة ونموذج الاختبار. سيظهر أول 12 اسمًا في كشف التوقيع.")
                else:
                    st.info("لا توجد أسماء متدربين مطابقة لنطاق هذا النموذج ومهنته؛ سيظل كشف التوقيع فارغًا ويمكن تعبئته يدويًا.")

                side_by_side_tables_html = f"""
                <div style="display: flex; flex-direction: row; gap: 4mm; width: 100%; margin-top: 3mm; margin-bottom: 3mm; page-break-inside: avoid; break-inside: avoid;">
                    <div style="flex: 1;">
                        <div style="font-weight: bold; color: #047857; font-size: 10.5pt; margin-bottom: 1mm; text-align: center;">كشف توقيع المتدربين (أ)</div>
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background-color: #059669; color: white;">
                                    <th style="border: 1px solid #059669; padding: 5px; font-size: 10pt; text-align: center;">م</th>
                                    <th style="border: 1px solid #059669; padding: 5px; font-size: 10pt; text-align: center;">اسم المتدرب</th>
                                    <th style="border: 1px solid #059669; padding: 5px; font-size: 10pt; text-align: center;">الوظيفة</th>
                                </tr>
                            </thead>
                            <tbody>
                                {signatures_rows_html}
                            </tbody>
                        </table>
                    </div>
                    <div style="flex: 1;">
                        <div style="font-weight: bold; color: #047857; font-size: 10.5pt; margin-bottom: 1mm; text-align: center;">كشف توقيع المتدربين (ب)</div>
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background-color: #059669; color: white;">
                                    <th style="border: 1px solid #059669; padding: 5px; font-size: 10pt; text-align: center;">م</th>
                                    <th style="border: 1px solid #059669; padding: 5px; font-size: 10pt; text-align: center;">اسم المتدرب</th>
                                    <th style="border: 1px solid #059669; padding: 5px; font-size: 10pt; text-align: center;">الوظيفة</th>
                                </tr>
                            </thead>
                            <tbody>
                                {signatures_rows_b_html}
                            </tbody>
                        </table>
                    </div>
                </div>
                """

                minutes_print_html = f"""
                <!DOCTYPE html>
                <html lang="ar" dir="rtl">
                <head>
                <meta charset="UTF-8">
                <style>
                @page {{ size: A4 portrait; margin: 12mm 8mm 18mm 8mm !important; }}
                body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0 !important; padding: 0 !important; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp_m}; }}
                .report-wrapper {{ width: 194mm; max-width: 194mm; margin: 0 auto !important; padding: 0 !important; position: relative; box-sizing: border-box; }}
                .first-page-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #059669; padding-bottom: 2mm; margin-bottom: 3mm; }}
                h2 {{ text-align: center; color: #047857; font-size: 16pt; margin: 0 0 2mm 0 !important; }}
                .meta-info {{ display: flex; justify-content: space-between; font-size: 11.5pt; font-weight: bold; color: #065f46; background: #f0fdf4; border: 1px solid #059669; padding: 2.5mm 5mm; border-radius: 4px; margin-bottom: 3mm; }}
                .section-box {{ background: #f8fafc; border: 1px solid #059669; padding: 4mm; border-radius: 5px; font-size: 12pt; white-space: pre-wrap; line-height: 1.5; margin-bottom: 3mm; }}
                .section-title {{ font-weight: bold; color: #047857; font-size: 13pt; margin-bottom: 1mm; border-bottom: 1px dashed #059669; padding-bottom: 1mm; }}
                </style>
                </head>
                <body>
                <div class="report-wrapper">
                    <div class="first-page-header">
                        <div style="font-size: 10.5pt; font-weight: bold; color: #065f46; line-height: 1.15;">{header_right_txt}</div>
                        <div>{render_logos_html()}</div>
                    </div>
                    <h2>محضر تدريب</h2>
                    <div class="meta-info">
                        <div>المنشأة / الجهة: {esc(final_fac_t)}</div>
                        <div style="text-align: left;">{date_display_block}</div>
                    </div>
                    
                    <div class="section-title">1. محضر التدريب</div>
                    <div class="section-box">{esc(final_min_t)}</div>

                    <div class="section-title">2. بنود التدريب</div>
                    <div class="section-box">{esc(final_items_t)}</div>

                    <div class="section-title">3. الأهداف من التدريب</div>
                    <div class="section-box">{esc(final_goals_t)}</div>

                    {side_by_side_tables_html}
                </div>
                </body>
                </html>
                """
                render_print_button_only(minutes_print_html, f"محضر تدريب نموذج رقم {chosen_min_tpl_id}")

    elif selected_menu == "📚 قاعدة بيانات المتدربين":
        st.subheader("📚 قاعدة بيانات المتدربين — عرض وتعديل وطباعة وتصدير")
        st.warning("تحتوي هذه الصفحة على بيانات شخصية حساسة. استخدمها للمخولين فقط، وتأكد من مراجعة البيانات قبل تصديرها أو طباعتها.")
        all_scope = hierarchy_scope_widget("فلترة البيانات حسب الهيكل الإداري:", "trainee_db_scope_v1")
        all_scope_pred, all_scope_args = hierarchy_filter_for_trainees(all_scope, "t")
        with db() as c:
            rows = c.execute(f"SELECT t.* FROM trainees t WHERE {all_scope_pred} ORDER BY t.id DESC", tuple(all_scope_args)).fetchall()
            templates_db = c.execute("SELECT id, name, exam_type FROM exam_templates ORDER BY name").fetchall()
        df_db = pd.DataFrame([dict(r) for r in rows])
        if df_db.empty:
            st.info("لا توجد بيانات متدربين ضمن النطاق المحدد.")
        else:
            search_db = st.text_input("🔎 بحث بالاسم أو الرقم القومي أو الهاتف أو رقم السجل:", key="trainee_db_search_v1")
            status_options = ["الكل"] + sorted({str(x) for x in df_db.get("status", pd.Series(dtype=str)).dropna().tolist()})
            status_db = st.selectbox("حالة التسجيل:", status_options, key="trainee_db_status_v1")
            if status_db != "الكل":
                df_db = df_db[df_db["status"].astype(str) == status_db]
            if search_db.strip():
                q_norm = normalize_text(search_db)
                q_digits = normalize_digits(search_db)
                mask = df_db.apply(lambda row: (
                    q_norm in normalize_text(row.get("name", ""))
                    or (bool(q_digits) and q_digits in normalize_national_id(row.get("national_id", "")))
                    or (bool(q_digits) and q_digits in normalize_egyptian_phone(row.get("phone", "")))
                    or q_norm == str(row.get("id", ""))
                ), axis=1)
                df_db = df_db[mask]
            status_labels = {"pending":"في انتظار اعتماد الإدارة", "approved":"معتمد ومصرح بالدخول", "active":"اختبار جارٍ", "completed":"مكتمل", "rejected":"مرفوض"}
            display_columns = [
                ("id", "رقم السجل"), ("name", "الاسم"), ("national_id", "الرقم القومي"), ("phone", "رقم الهاتف"),
                ("profession", "الوظيفة / التخصص"), ("facility", "الجهة الإدارية / المنشأة"),
                ("work_start_date", "تاريخ استلام العمل"), ("status", "حالة التسجيل"),
                ("assigned_template_id", "رقم نموذج الاختبار"), ("created_at", "تاريخ التسجيل"),
                ("approved_at", "تاريخ الاعتماد"), ("updated_at", "آخر تحديث"), ("hidden", "مخفي")
            ]
            export_df = df_db.copy()
            for col, label in display_columns:
                if col not in export_df.columns:
                    export_df[col] = ""
            export_df = export_df[[c for c, _ in display_columns]].rename(columns={c: label for c, label in display_columns})
            if "حالة التسجيل" in export_df.columns:
                export_df["حالة التسجيل"] = export_df["حالة التسجيل"].map(lambda x: status_labels.get(str(x), x))
            st.caption(f"عدد السجلات المطابقة: {len(export_df)}")
            st.dataframe(export_df, use_container_width=True, hide_index=True)
            dl1, dl2 = st.columns(2)
            with dl1:
                csv_data = export_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button("📥 تصدير CSV", data=csv_data, file_name="trainees_database.csv", mime="text/csv", use_container_width=True, key="trainees_db_csv_v1")
            with dl2:
                xlsx_out = io.BytesIO()
                with pd.ExcelWriter(xlsx_out, engine="openpyxl") as writer:
                    export_df.to_excel(writer, index=False, sheet_name="Trainees")
                st.download_button("📥 تصدير Excel", data=xlsx_out.getvalue(), file_name="trainees_database.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="trainees_db_xlsx_v1")
            printable_rows = "".join("<tr>" + "".join(f"<td style='border:1px solid #bbb;padding:5px'>{esc('' if pd.isna(v) else str(v))}</td>" for v in row) + "</tr>" for row in export_df.fillna("").itertuples(index=False, name=None))
            printable_headers = "".join(f"<th style='border:1px solid #bbb;padding:6px;background:#e5e7eb'>{esc(str(col))}</th>" for col in export_df.columns)
            printable_html = generate_general_report_html("قاعدة بيانات المتدربين", f"<table style='border-collapse:collapse;width:100%;font-size:8pt'><thead><tr>{printable_headers}</tr></thead><tbody>{printable_rows}</tbody></table>", target_pages=0)
            render_print_button_only(printable_html, "طباعة قاعدة بيانات المتدربين")

            st.markdown("---")
            st.markdown("#### ✏️ تعديل بيانات متدرب")
            row_choices = {f"سجل {int(r['id'])} — {r.get('name','')} — {r.get('phone','')}": int(r["id"]) for _, r in df_db.iterrows()}
            if row_choices:
                selected_record_label = st.selectbox("اختر المتدرب للتعديل:", list(row_choices.keys()), key="trainee_db_edit_pick_v1")
                selected_record_id = row_choices[selected_record_label]
                selected_record = df_db[df_db["id"].astype(int) == selected_record_id].iloc[0].to_dict()
                try:
                    current_work_date = date.fromisoformat(str(selected_record.get("work_start_date") or ""))
                except Exception:
                    current_work_date = now_cairo().date()
                current_status = str(selected_record.get("status") or "pending")
                current_template = selected_record.get("assigned_template_id")
                template_labels = ["بدون نموذج"] + [f"{t['name']} ({t['exam_type'] or 'قبل التدريب'}) — ID {t['id']}" for t in templates_db]
                template_ids = [None] + [int(t["id"]) for t in templates_db]
                current_template_index = template_ids.index(int(current_template)) if current_template is not None and int(current_template) in template_ids else 0
                with st.form("trainee_db_edit_form_v1"):
                    ed_name = st.text_input("الاسم:", value=str(selected_record.get("name") or ""))
                    ed_nid = st.text_input("الرقم القومي:", value=str(selected_record.get("national_id") or ""), max_chars=14)
                    ed_phone = st.text_input("رقم الهاتف:", value=str(selected_record.get("phone") or ""))
                    ed_prof = st.text_input("الوظيفة / التخصص:", value=str(selected_record.get("profession") or ""))
                    ed_facility = st.text_input("الجهة الإدارية / المنشأة:", value=str(selected_record.get("facility") or ""))
                    ed_work_date = st.date_input("تاريخ استلام العمل:", value=current_work_date, max_value=now_cairo().date(), format="DD/MM/YYYY")
                    status_values = ["pending", "approved", "active", "completed", "rejected"]
                    status_labels_list = [status_labels[x] for x in status_values]
                    status_index = status_values.index(current_status) if current_status in status_values else 0
                    ed_status_label = st.selectbox("حالة التسجيل:", status_labels_list, index=status_index)
                    ed_template_label = st.selectbox("نموذج الاختبار المخصص:", template_labels, index=current_template_index)
                    ed_hidden = st.checkbox("إخفاء السجل من القوائم العامة", value=bool(selected_record.get("hidden", 0)))
                    save_trainee_db = st.form_submit_button("💾 حفظ جميع التعديلات", use_container_width=True)
                if save_trainee_db:
                    ed_nid_norm = normalize_national_id(ed_nid)
                    ed_phone_norm = normalize_egyptian_phone(ed_phone)
                    if not ed_name.strip() or not ed_facility.strip():
                        st.error("أدخل الاسم وجهة العمل.")
                    elif not is_valid_egyptian_national_id(ed_nid_norm):
                        st.error("الرقم القومي غير صحيح؛ راجع 14 رقماً وتاريخ الميلاد وكود المحافظة.")
                    elif not is_valid_egyptian_mobile(ed_phone_norm):
                        st.error("رقم الموبايل المصري غير صحيح.")
                    else:
                        try:
                            update_trainee_data(selected_record_id, ed_facility, ed_name, ed_phone_norm, ed_nid_norm, ed_prof, ed_work_date.isoformat())
                            chosen_status = status_values[status_labels_list.index(ed_status_label)]
                            chosen_tpl_id = template_ids[template_labels.index(ed_template_label)]
                            with db() as c:
                                c.execute("UPDATE trainees SET status=?, assigned_template_id=?, hidden=?, updated_at=? WHERE id=?", (chosen_status, chosen_tpl_id, int(ed_hidden), now(), selected_record_id))
                            st.success("تم حفظ بيانات المتدرب بنجاح.")
                            st.rerun()
                        except ValueError as e:
                            errors = {"DUPLICATE_TRAINEE_PHONE":"رقم الهاتف مستخدم في سجل آخر.", "DUPLICATE_TRAINEE_NATIONAL_ID":"الرقم القومي مستخدم في سجل آخر.", "INVALID_TRAINEE_PHONE":"رقم الهاتف غير صحيح.", "INVALID_TRAINEE_NATIONAL_ID":"الرقم القومي غير صحيح."}
                            st.error(errors.get(str(e), f"تعذر حفظ البيانات: {e}"))

    elif selected_menu == "💾 النسخ الاحتياطي":
        st.subheader("💾 النسخ الاحتياطي واستعادة قاعدة البيانات والدمج")
        if st.button("🗑 تفرغ جميع بيانات النظام (تصفير قاعدة البيانات)", use_container_width=True):
            with db() as c:
                c.execute("DELETE FROM exam_questions")
                c.execute("DELETE FROM exam_sessions")
                c.execute("DELETE FROM trainees")
                c.execute("DELETE FROM questions")
                c.execute("DELETE FROM exam_templates")
                c.execute("DELETE FROM action_plans")
                c.execute("DELETE FROM hierarchical_facilities")
                c.execute("DELETE FROM audit_logs")
            st.success("✨ تمت تصفية قاعدة البيانات بالكامل وأصبحت نظيفة وخالية من أي بيانات!")
            st.rerun()
        col_bk1, col_bk2 = st.columns(2)
        with col_bk1:
            with open(DB_PATH, "rb") as f:
                db_bytes = f.read()
            st.download_button("📥 تحميل النسخة (.db)", data=db_bytes, file_name="endemic_labs_exam_v1_0.db", mime="application/octet-stream", use_container_width=True)
        with col_bk2:
            uploaded_db_file = st.file_uploader("رفع ملف قاعدة بيانات (.db):", type=["db"], key="restore_db_uploader")
            if uploaded_db_file is not None:
                c_btn_res, c_btn_merge = st.columns(2)
                with c_btn_res:
                    if st.button("⚠ استبدال القاعدة الحالية بالكامل", use_container_width=True):
                        try:
                            with open(DB_PATH, "wb") as f_out:
                                f_out.write(uploaded_db_file.getbuffer())
                            st.success("✅ تمت الاستعادة بنجاح!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"خطأ: {e}")
                with c_btn_merge:
                    if st.button("🔄 دمج البيانات المرفوعة بالبرنامج", use_container_width=True):
                        try:
                            temp_db_path = os.path.join(BASE, "temp_merge.db")
                            with open(temp_db_path, "wb") as f_out:
                                f_out.write(uploaded_db_file.getbuffer())
                            src_conn = sqlite3.connect(temp_db_path)
                            src_conn.row_factory = sqlite3.Row
                            with db() as dest_conn:
                                src_qs = src_conn.execute("SELECT * FROM questions").fetchall()
                                merged_q_count = 0
                                for q in src_qs:
                                    try:
                                        dest_conn.execute("INSERT INTO questions(difficulty, category, question, options_json, answer, explanation, reference, active, fingerprint, created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                                          (q["difficulty"], q["category"], q["question"], q["options_json"], q["answer"], q["explanation"], q["reference"], q["active"], q["fingerprint"], q["created_at"]))
                                        merged_q_count += 1
                                    except sqlite3.IntegrityError:
                                        pass
                                src_hier = src_conn.execute("SELECT * FROM hierarchical_facilities").fetchall()
                                merged_h_count = 0
                                for h in src_hier:
                                    exists = dest_conn.execute("SELECT 1 FROM hierarchical_facilities WHERE governorate=? AND authority=? AND center=? AND administration=? AND facility_name=?",
                                                               (h["governorate"], h["authority"], h["center"], h["administration"], h["facility_name"])).fetchone()
                                    if not exists:
                                        dest_conn.execute("INSERT INTO hierarchical_facilities(governorate, authority, center, administration, facility_name, created_at, hidden) VALUES(?,?,?,?,?,?,?)",
                                                          (h["governorate"], h["authority"], h["center"], h["administration"], h["facility_name"], h["created_at"], h["hidden"] if h["hidden"] is not None else 0))
                                        merged_h_count += 1
                            src_conn.close()
                            if os.path.exists(temp_db_path):
                                os.remove(temp_db_path)
                            reindex_hierarchical_facilities()
                            st.success(f"🎉 تم الدمج بنجاح! (تم إضافة {merged_q_count} سؤالاً، و {merged_h_count} وحدة متوطنة جديدة دون فقدان البيانات السابقة).")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"خطأ أثناء الدمج: {e}")

    elif selected_menu == "👥 إدارة المستخدمين":
        st.subheader("👥 إدارة المستخدمين وصلاحياتهم وتعديل بيانات الاعتماد (مع إمكانية الحذف)")
        tab_u1, tab_u2, tab_u3 = st.tabs(["➕ إضافة مستخدم", "⚙ الصلاحيات والحذف", "🔑 تعديل اسم وكلمة المرور"])
        with tab_u1:
            with st.form("add_user_form_v1_0"):
                new_u_name = st.text_input("اسم المستخدم:", value="")
                new_u_pass = st.text_input("كلمة المرور:", type="password", value="")
                new_u_role = st.selectbox("المسمى الوظيفي:", ["exam_manager", "viewer"], format_func=lambda x: ROLES[x])
                selected_modules_checkboxes = {}
                for mod_key, mod_desc in ALL_MENU_MODULES.items():
                    selected_modules_checkboxes[mod_key] = st.checkbox(f"{mod_key} ({mod_desc})", value=True)
                if st.form_submit_button("💾 حفظ", use_container_width=True):
                    if new_u_name.strip() and new_u_pass.strip():
                        assigned_perms = [k for k, v in selected_modules_checkboxes.items() if v]
                        with db() as c:
                            try:
                                c.execute("INSERT INTO users(username, password_hash, role, permissions_json, active, created_at) VALUES(?,?,?,?,?,?)",
                                          (new_u_name.strip(), hash_password(new_u_pass), new_u_role, json.dumps(assigned_perms, ensure_ascii=False), 1, now()))
                                st.success("✅ تم الإضافة!")
                            except sqlite3.IntegrityError:
                                st.error("مستخدم مسبقاً.")
                    else:
                        st.warning("أدخل البيانات.")
        with tab_u2:
            with db() as c:
                all_users = c.execute("SELECT id, username, role, permissions_json FROM users WHERE role != 'admin'").fetchall()
            if not all_users:
                st.info("لا توجد مستخدمين.")
            else:
                user_map = {f"مستخدم: {u['username']}": u for u in all_users}
                sel_user_label = st.selectbox("اختر المستخدم:", list(user_map.keys()))
                target_user = user_map[sel_user_label]
                try:
                    curr_user_perms = json.loads(target_user["permissions_json"]) if target_user["permissions_json"] else []
                except:
                    curr_user_perms = []
                with st.form(f"edit_user_perms_{target_user['id']}"):
                    edit_checkboxes = {}
                    for mod_key, mod_desc in ALL_MENU_MODULES.items():
                        is_checked = mod_key in curr_user_perms
                        edit_checkboxes[mod_key] = st.checkbox(f"{mod_key}", value=is_checked, key=f"mod_chk_{target_user['id']}_{mod_key}")
                    c_save, c_del = st.columns(2)
                    with c_save:
                        save_btn = st.form_submit_button("💾 حفظ", use_container_width=True)
                    with c_del:
                        del_btn = st.form_submit_button("🗑 حذف المستخدم", use_container_width=True)
                    if save_btn:
                        new_assigned = [k for k, v in edit_checkboxes.items() if v]
                        with db() as c:
                            c.execute("UPDATE users SET permissions_json=? WHERE id=?", (json.dumps(new_assigned, ensure_ascii=False), target_user["id"]))
                        st.success("✅ تم التحديث!")
                        st.rerun()
                    if del_btn:
                        with db() as c:
                            c.execute("DELETE FROM users WHERE id=?", (target_user["id"],))
                        st.success("✅ تم الحذف بنجاح!")
                        st.rerun()
        with tab_u3:
            st.markdown("#### 🔑 تعديل اسم المستخدم وكلمة المرور للمالك أو المستخدمين")
            st.info("📌 **شروط التعديل:** يجب إدخال كلمة المرور الحالية بشكل صحيح (وإلا كلمة مرور المالك الأساسية في حال تعديل حساب آخر) لضمان الأمان.")
            with db() as c:
                all_sys_users = c.execute("SELECT id, username, role FROM users").fetchall()
            sys_user_choices = {f"{u['username']} ({ROLES.get(u['role'], u['role'])})": u for u in all_sys_users}
            with st.form("edit_credentials_form"):
                sel_target_user_label = st.selectbox("اختر الحساب المراد تعديله:", list(sys_user_choices.keys()))
                chosen_target = sys_user_choices[sel_target_user_label]
                new_username_input = st.text_input("اسم المستخدم الجديد:", value=chosen_target["username"])
                current_password_input = st.text_input("كلمة المرور الحالية (للتأكيد):", type="password", value="")
                new_password_input = st.text_input("كلمة المرور الجديدة (اتركها فارغة إن لم ترد تغييرها):", type="password", value="")
                if st.form_submit_button("🔒 تحديث بيانات الدخول", use_container_width=True):
                    if not current_password_input.strip():
                        st.warning("⚠ يرجى إدخال كلمة المرور الحالية للتأكيد.")
                    else:
                        with db() as c:
                            actor_user = c.execute("SELECT * FROM users WHERE username=?", (st.session_state.username,)).fetchone()
                            target_db_rec = c.execute("SELECT * FROM users WHERE id=?", (chosen_target["id"],)).fetchone()
                        is_admin_actor = actor_user and actor_user["role"] == "admin"
                        verified_actor = actor_user and verify_password(current_password_input, actor_user["password_hash"])
                        verified_target = target_db_rec and verify_password(current_password_input, target_db_rec["password_hash"])
                        if verified_actor or verified_target or (is_admin_actor and st.session_state.username == "admin" and current_password_input == "admin"):
                            new_uname_clean = new_username_input.strip()
                            if not new_uname_clean:
                                st.error("❌ اسم المستخدم لا يمكن أن يكون فارغاً.")
                            else:
                                with db() as c:
                                    try:
                                        if new_password_input.strip():
                                            new_hash = hash_password(new_password_input.strip())
                                            c.execute("UPDATE users SET username=?, password_hash=? WHERE id=?", (new_uname_clean, new_hash, chosen_target["id"]))
                                        else:
                                            c.execute("UPDATE users SET username=? WHERE id=?", (new_uname_clean, chosen_target["id"]))
                                        st.success("✅ تم تحديث بيانات الدخول بنجاح! يرجى إعادة تسجيل الدخول.")
                                        time.sleep(1.5)
                                        st.session_state.logged_in = False
                                        st.session_state.username = ""
                                        st.session_state.role = ""
                                        st.rerun()
                                    except sqlite3.IntegrityError:
                                        st.error("❌ اسم المستخدم الجديد مستخدم مسبقاً، اختر اسمًا آخر.")
                        else:
                            st.error("❌ كلمة المرور الحالية غير صحيحة.")

    elif selected_menu == "🧾 سجل التدقيق":
        st.subheader("🧾 سجل التدقيق")
        with db() as c:
            df_audit = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100", c)
        st.dataframe(df_audit, use_container_width=True, hide_index=True)

def trainee_portal():
    with db() as c:
        tr = c.execute("SELECT * FROM trainees WHERE id=? AND hidden=0", (st.session_state.trainee_id,)).fetchone()
    if not tr:
        st.session_state.trainee_id = ""
        st.rerun()
    header()
    if tr["status"] == "pending":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #064e3b, #047857); color: #ffffff; padding: 35px; border-radius: 16px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-top: 40px; font-family: 'Cairo', sans-serif;">
            <div style="font-size: 26px; font-weight: 900; margin-bottom: 10px;">⏳ حسابك في انتظار اعتماد الإدارة</div>
            <p style="font-size: 15px; color: #d1fae5;">جاري تحديث الصفحة تلقائياً حتى يتم اعتمادك وتفعيل الاختبار...</p>
        </div>
        """, unsafe_allow_html=True)
        components.html("""
        <script>
        setTimeout(function(){
            window.location.reload();
        }, 5000);
        </script>
        """, height=0)
        if st.button("🔄 تحديث الصفحة يدوياً", use_container_width=True):
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state.trainee_id = ""
            st.rerun()
        return

    assigned_tpl_id = tr["assigned_template_id"]
    with db() as c:
        matching_template = c.execute("SELECT * FROM exam_templates WHERE id=?", (assigned_tpl_id,)).fetchone() if assigned_tpl_id else None

    is_exam_open = False
    if matching_template:
        t_dict = dict(matching_template)
        if not template_matches_profession(t_dict, tr["profession"]):
            st.error(f"❌ نموذج الاختبار المخصص لك غير مناسب لمهنتك ({tr['profession'] or 'غير محددة'}). يرجى التواصل مع الإدارة لتعديل التخصيص.")
            if st.button("🚪 تسجيل الخروج", use_container_width=True):
                st.session_state.trainee_id = ""
                st.rerun()
            return
        start_t = t_dict.get("start_time")
        end_t = t_dict.get("end_time")
        if start_t and end_t:
            try:
                dt_now = now_cairo()
                dt_start = datetime.fromisoformat(start_t)
                dt_end = datetime.fromisoformat(end_t)
                if dt_start <= dt_now <= dt_end:
                    is_exam_open = True
            except:
                pass

    if not is_exam_open:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #064e3b, #047857); color: #ffffff; padding: 45px; border-radius: 16px; text-align: center; box-shadow: 0 6px 20px rgba(0,0,0,0.15); border: 3px solid #059669; margin-top: 50px; margin-bottom: 30px; font-family: 'Cairo', sans-serif;">
            <div style="font-size: 34px; font-weight: 900; letter-spacing: 1px;">🚫 لا يوجد امتحانات متوفرة الان</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        t_dict = dict(matching_template)
        tpl_name_str = t_dict.get("name", "اختبار معتمد")
        exam_type_str = t_dict.get("exam_type", "قبل التدريب")
        start_t = t_dict.get("start_time")
        end_t = t_dict.get("end_time")
        def format_12h(iso_str):
            if not iso_str or "T" not in iso_str:
                return iso_str
            try:
                dt = datetime.fromisoformat(iso_str)
                return dt.strftime("%Y-%m-%d %I:%M %p").replace("AM", "صباحاً").replace("PM", "مساءً")
            except:
                return iso_str
        st.markdown(f"""
        <div style="background-color: #059669; color: #ffffff; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin: 15px auto; max-width: 900px; border: 2px solid #34d399;">
            <h2 style="margin: 0 0 6px 0; font-size: 20px; font-weight: 900; color: #ffffff;">نظام تقييم واختبار العاملين بالأمراض المتوطنة</h2>
            <p style="margin: 0; font-size: 14px; color: #d1fae5;">المتدرب: <b>{esc(tr["name"])}</b> &nbsp;|&nbsp; الوظيفة: <b>{esc(tr['profession'] if tr['profession'] is not None else '')}</b> &nbsp;|&nbsp; الاختبار المخصص: <b>{esc(tpl_name_str)}</b> [{esc(exam_type_str)}]</p>
        </div>
        """, unsafe_allow_html=True)
        with st.container(border=True):
            format_s = format_12h(start_t)
            format_e = format_12h(end_t)
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.markdown(f"🟢 **وقت البدء:**\n`{format_s}`")
            with col_s2:
                st.markdown(f"🔴 **و وقت النهاية:**\n`{format_e}`")
        st.success("🟢 **الاختبار مفتوح ومتاح الآن للتنفيذ!**")
        try:
            sid = start_session(tr["id"], matching_template["id"])
            st.session_state.exam_session_id = sid
            st.rerun()
        except Exception as e:
            if "لديك اختبار نشط بالفعل" in str(e):
                with db() as c:
                    active_s = c.execute("SELECT id FROM exam_sessions WHERE trainee_id=? AND status='active' LIMIT 1", (tr["id"],)).fetchone()
                if active_s:
                    st.session_state.exam_session_id = active_s["id"]
                    st.rerun()
            else:
                st.error(str(e))
    st.markdown("<br>", unsafe_allow_html=True)
    col_space1, col_btn, col_space2 = st.columns([1, 2, 1])
    with col_btn:
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state.trainee_id = ""
            st.rerun()

def exam_interface(session_id):
    header()
    with db() as c:
        session = c.execute("SELECT s.*, t.facility FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.id=? AND t.hidden=0", (session_id,)).fetchone()
        rows = c.execute("""SELECT eq.*, q.question, q.options_json FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=? ORDER BY eq.position""", (session_id,)).fetchall()
    answered = 0
    for idx, row in enumerate(rows, start=1):
        try:
            opts = json.loads(row["options_json"])
        except:
            opts = ["نعم", "لا"]
        order = json.loads(row["option_order_json"])
        disp_opts = [opts[i] for i in order]
        curr_idx = None
        if row["selected_option"] is not None:
            try:
                curr_idx = disp_opts.index(opts[row["selected_option"]])
            except:
                pass
        question_text = esc(clean_question_text(row["question"]))
        st.markdown(f'<div class="question"><strong style="color:#065f46;">({idx})</strong> {question_text}</div>', unsafe_allow_html=True)
        choice = st.radio("اختر الإجابة:", disp_opts, index=curr_idx, key=f"q_{row['id']}", label_visibility="collapsed")
        if choice:
            sel = order[disp_opts.index(choice)]
            with db() as c:
                c.execute("UPDATE exam_questions SET selected_option=?, is_correct=CASE WHEN ?=(SELECT answer FROM questions WHERE id=question_id) THEN 1 ELSE 0 END WHERE id=?",
                          (sel, sel, row["id"]))
            answered += 1
    st.progress(answered / len(rows) if rows else 0)
    if st.button("تسليم الاختبار نهائياً", use_container_width=True):
        res = submit_session(session_id)
        if res:
            st.session_state.last_result_id = session_id
            st.session_state.exam_session_id = None
            st.success("🎉 تم تسليم الاختبار بنجاح!")
            st.rerun()

# ============================================================
# 6) التوجيه الأساسي الشامل للشاشات
# ============================================================
if st.session_state.get("show_verification_portal", False):
    verification_portal_view()
    if st.button("🔙 العودة للبوابة الرئيسية"):
        st.session_state.show_verification_portal = False
        st.rerun()
elif st.session_state.get("exam_session_id"):
    exam_interface(st.session_state.exam_session_id)
elif st.session_state.trainee_id and not st.session_state.logged_in:
    if st.session_state.get("last_result_id"):
        sid = st.session_state.last_result_id
        header()
        st.success("تم تسليم الاختبار بنجاح ونتيجتك جاهزة!")
        curr_sett = get_print_settings()
        cert_html = generate_customizable_certificate_html(sid, curr_sett.get("default_cert_title"), curr_sett.get("default_cert_notes"))
        render_print_button_only(cert_html, f"الشهادة المعتمدة {sid}")
        if st.button("العودة للرئيسية"):
            st.session_state.trainee_id = ""
            st.session_state.last_result_id = None
            st.rerun()
    else:
        trainee_portal()
elif not st.session_state.logged_in:
    login_portal()
else:
    admin_dashboard()