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
        r"\(\s*نموذج\s+متوطنة[^)]*\)",
        r"\(\s*مجموعة\s+متوطنة[^)]*\)",
        r"\(\s*نموذج\s+تقييم(?:\s*(?:رقم\vert{}#)?\s*\d+)?[^)]*\)",
        r"\[\s*نموذج\s+تقييم(?:\s*(?:رقم\vert{}#)?\s*\d+)?[^]]*\]",
        r"\(\s*سؤال\s*(?:رقم\vert{}#)?\s*\d+\s*\)",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*(?:سؤال\s*(?:رقم|#)?\s*)?\d+\s*[\)\].:-]+\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*سؤال\s*(?:رقم|#)?\s*\d+\s*[:.)-]+\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\s+([،,:؛؟.)])", r"\1", cleaned)
    return cleaned.strip()

def normalize_text(x):
    x = "" if x is None else str(x)
    return re.sub(r"\s+", " ", x.strip()).lower()

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
        rows = c.execute("SELECT id, facility, name, phone, profession, status, assigned_template_id, created_at, approved_at, updated_at, hidden FROM trainees ORDER BY id ASC").fetchall()
        c.execute("DELETE FROM trainees")
        c.execute("DELETE FROM sqlite_sequence WHERE name='trainees'")
        id_mapping = {}
        for new_id, r in enumerate(rows, start=1):
            old_id = r["id"]
            c.execute("INSERT INTO trainees(id, facility, name, phone, profession, status, assigned_template_id, created_at, approved_at, updated_at, hidden) VALUES(?,?,?,?,?,?,?,?,?,?,?)", 
                      (new_id, r["facility"], r["name"], r["phone"], r["profession"] if r["profession"] is not None else "", r["status"], r["assigned_template_id"], r["created_at"], r["approved_at"], r["updated_at"], r["hidden"] if r["hidden"] is not None else 0))
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
        rows = c.execute("SELECT id, name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, start_time, end_time, active, created_at FROM exam_templates ORDER BY id ASC").fetchall()
        c.execute("DELETE FROM exam_templates")
        c.execute("DELETE FROM sqlite_sequence WHERE name='exam_templates'")
        t_mapping = {}
        for new_id, r in enumerate(rows, start=1):
            old_id = r["id"]
            c.execute("INSERT INTO exam_templates(id, name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, start_time, end_time, active, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", 
                      (new_id, r["name"], r["exam_type"], r["num_questions"], r["duration_minutes"], r["pass_percent"], r["categories_json"], r["start_time"], r["end_time"], r["active"], r["created_at"]))
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
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trainees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                facility TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                profession TEXT NOT NULL DEFAULT 'أخصائي الأمراض المتوطنة',
                status TEXT NOT NULL DEFAULT 'pending',
                assigned_template_id INTEGER,
                created_at TEXT NOT
