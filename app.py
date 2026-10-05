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
    top: 0; left: 0; width: 100%; height: 100%;
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
document.addEventListener("contextmenu", function(e) { e.preventDefault(); });
document.addEventListener("copy", function(e) { e.preventDefault(); alert("⚠ عذراً، نسخ النصوص محظور حفاظاً على سرية الأسئلة والبيانات!"); });

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
    if not q_text:
        return ""
    cleaned = re.sub(r"\(نموذج متوطنة.*?\)", "", q_text)
    cleaned = re.sub(r"\(مجموعة متوطنة.*?\)", "", cleaned)
    return normalize_text(cleaned)

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
                      (r["governorate"], r["authority"], r["center"], r["administration"], r["facility_name"], r["created_at"], r.get("hidden", 0)))

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
                      (new_id, r["facility"], r["name"], r["phone"], r.get("profession", ""), r["status"], r["assigned_template_id"], r["created_at"], r["approved_at"], r["updated_at"], r.get("hidden", 0)))
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
            created_at TEXT NOT NULL
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
            default_cert_title TEXT NOT NULL DEFAULT 'شهادة اجتياز اختبار معتمدة',
            default_cert_notes TEXT NOT NULL DEFAULT 'تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد',
            trainee_prefix TEXT NOT NULL DEFAULT '',
            trainee_title TEXT NOT NULL DEFAULT '',
            trainee_profession TEXT NOT NULL DEFAULT '',
            professions_list_json TEXT NOT NULL DEFAULT '[]'
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

        for col_table, col_name, col_type in [
            ("trainees", "hidden", "INTEGER NOT NULL DEFAULT 0"),
            ("trainees", "profession", "TEXT NOT NULL DEFAULT 'أخصائي الأمراض المتوطنة'"),
            ("hierarchical_facilities", "hidden", "INTEGER NOT NULL DEFAULT 0"),
            ("users", "permissions_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("exam_templates", "exam_type", "TEXT NOT NULL DEFAULT 'قبل التدريب'"),
            ("exam_templates", "start_time", "TEXT"), 
            ("exam_templates", "end_time", "TEXT"), 
            ("action_plans", "start_date", "TEXT"),
            ("action_plans", "end_date", "TEXT"),
            ("print_settings", "line_spacing", "REAL NOT NULL DEFAULT 1.25"),
            ("print_settings", "logo2_base64", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "logo3_base64", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "bg_base64", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "frame_base64", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "default_cert_title", "TEXT NOT NULL DEFAULT 'شهادة اجتياز اختبار معتمدة'"),
            ("print_settings", "default_cert_notes", "TEXT NOT NULL DEFAULT 'تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد'"),
            ("print_settings", "trainee_prefix", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "trainee_title", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "trainee_profession", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "professions_list_json", "TEXT NOT NULL DEFAULT '[]'")
        ]:
            try:
                c.execute(f"ALTER TABLE {col_table} ADD COLUMN {col_name} {col_type}")
            except:
                pass

        cnt = c.execute("SELECT COUNT(*) FROM print_settings").fetchone()[0]
        if cnt == 0:
            default_header = "جمهورية مصر العربية<br>وزارة الصحة والسكان<br>مديرية الشئون الصحية بالشرقية<br>الإدارة الصحية بأولاد صقر"
            default_professions = [
                "أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", 
                "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"
            ]
            c.execute("INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, line_spacing, logo_base64, logo2_base64, logo3_base64, bg_base64, frame_base64, default_cert_title, default_cert_notes, trainee_prefix, trainee_title, trainee_profession, professions_list_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (default_header, "3mm", "3mm", "3mm", "3mm", 1.25, DEFAULT_LOGO, "", "", "", "", "شهادة اجتياز اختبار معتمدة", "تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد", "", "دكتور", "أخصائي الأمراض المتوطنة", json.dumps(default_professions, ensure_ascii=False)))

        cnt_tpl = c.execute("SELECT COUNT(*) FROM exam_templates").fetchone()[0]
        if cnt_tpl == 0:
            default_start = now_cairo().isoformat(timespec="seconds")
            default_end = (now_cairo() + timedelta(days=365)).isoformat(timespec="seconds")
            c.execute("""INSERT INTO exam_templates(name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, start_time, end_time, active, created_at) 
                         VALUES(?,?,?,?,?,?,?,?,?,?)""",
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
                res["professions_list"] = ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "فني صحي متوطنة"]
            if "line_spacing" not in res or res["line_spacing"] is None:
                res["line_spacing"] = 1.25
            return res
        return {
            "header_text": "جمهورية مصر العربية<br>وزارة الصحة والسكان<br>مديرية الشئون الصحية بالشرقية<br>الإدارة الصحية بأولاد صقر",
            "margin_top": "3mm", "margin_bottom": "3mm", "margin_right": "3mm", "margin_left": "3mm",
            "line_spacing": 1.25,
            "logo_base64": DEFAULT_LOGO,
            "logo2_base64": "",
            "logo3_base64": "",
            "bg_base64": "",
            "frame_base64": "",
            "default_cert_title": "شهادة اجتياز اختبار معتمدة",
            "default_cert_notes": "تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد",
            "trainee_prefix": "",
            "trainee_title": "دكتور",
            "trainee_profession": "أخصائي الأمراض المتوطنة",
            "professions_list": ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"]
        }

def save_print_settings(h_text, m_top, m_bot, m_right, m_left, line_spacing, logo_data, logo2_data, logo3_data, bg_data, frame_data, def_title, def_notes, trainee_prefix, trainee_title, trainee_profession, professions_list):
    with db() as c:
        c.execute("DELETE FROM print_settings")
        c.execute("INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, line_spacing, logo_base64, logo2_base64, logo3_base64, bg_base64, frame_base64, default_cert_title, default_cert_notes, trainee_prefix, trainee_title, trainee_profession, professions_list_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (h_text, m_top, m_bot, m_right, m_left, float(line_spacing), logo_data, logo2_data, logo3_data, bg_data, frame_data, def_title, def_notes, trainee_prefix, trainee_title, trainee_profession, json.dumps(professions_list, ensure_ascii=False)))

def get_hierarchical_data(include_hidden=False):
    with db() as c:
        q = "SELECT * FROM hierarchical_facilities"
        if not include_hidden:
            q += " WHERE hidden = 0"
        q += " ORDER BY id ASC"
        rows = c.execute(q).fetchall()
        return [dict(r) for r in rows] if rows else []

def ensure_admin():
    with db() as c:
        u = c.execute("SELECT * FROM users WHERE role='admin'").fetchone()
        all_modules = list(ALL_MENU_MODULES.keys())
        if not u:
            c.execute("INSERT OR REPLACE INTO users(username,password_hash,role,permissions_json,active,created_at) VALUES(?,?,?,?,?,?)",
                      ("admin", hash_password("admin"), "admin", json.dumps(all_modules, ensure_ascii=False), 1, now()))
        else:
            c.execute("UPDATE users SET password_hash=?, permissions_json=? WHERE role='admin'", (hash_password("admin"), json.dumps(all_modules, ensure_ascii=False)))

ensure_admin()

def login_user(u, p):
    with db() as c:
        user = c.execute("SELECT * FROM users WHERE username=? AND active=1", (u.strip(),)).fetchone()
        if user and verify_password(p, user["password_hash"]):
            c.execute("UPDATE users SET last_login=? WHERE id=?", (now(), user["id"]))
            return dict(user)
    return None

def create_trainee(facility, name, phone, profession, assigned_template_id=None):
    with db() as c:
        cur = c.execute("INSERT INTO trainees(facility,name,phone,profession,status,assigned_template_id,created_at,updated_at,hidden) VALUES(?,?,?,?,?,?,?,?,?)",
                        (facility, normalize_text(name), normalize_text(phone), profession, "pending", assigned_template_id, now(), now(), 0))
        tid = cur.lastrowid
    return tid

def trainee_by_credentials(name, facility):
    with db() as c:
        r = c.execute("SELECT * FROM trainees WHERE name=? AND facility=? AND status IN ('approved','active') AND hidden=0",
                      (normalize_text(name), facility)).fetchone()
        return dict(r) if r else None

def set_trainee_status_and_template(tid, status, assigned_template_id):
    with db() as c:
        c.execute("""UPDATE trainees 
                     SET status=?, assigned_template_id=?, updated_at=?, 
                         approved_at=CASE WHEN ?='approved' THEN ? ELSE approved_at END 
                     WHERE id=?""",
                  (status, assigned_template_id, now(), status, now(), tid))

def set_bulk_template_for_all(assigned_template_id):
    with db() as c:
        c.execute("""UPDATE trainees 
                     SET assigned_template_id=?, 
                         status=CASE WHEN status='pending' THEN 'approved' ELSE status END,
                         approved_at=CASE WHEN status='pending' THEN ? ELSE approved_at END,
                         updated_at=? WHERE hidden=0""",
                  (assigned_template_id, now(), now()))

def trainees_df(status=None, include_hidden=False):
    with db() as c:
        q = "SELECT id, facility, name, phone, profession, status, assigned_template_id, created_at, approved_at, hidden FROM trainees"
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
    if not t: return []
    t_dict = dict(t)
    cats_raw = t_dict.get("categories_json", "[]")
    try: cats = json.loads(cats_raw) if cats_raw else []
    except: cats = []
    limit_count = int(t_dict.get("num_questions", 999999))

    with db() as c:
        if cats:
            placeholders = ','.join(['?'] * len(cats))
            all_db_questions = [dict(r) for r in c.execute(f"SELECT * FROM questions WHERE active=1 AND category IN ({placeholders}) ORDER BY RANDOM()", cats).fetchall()]
            if not all_db_questions:
                all_db_questions = [dict(r) for r in c.execute("SELECT * FROM questions WHERE active=1 ORDER BY RANDOM()").fetchall()]
        else:
            all_db_questions = [dict(r) for r in c.execute("SELECT * FROM questions WHERE active=1 ORDER BY RANDOM()").fetchall()]
            
    if limit_count >= 999900: return all_db_questions
    return all_db_questions[:limit_count]

def start_session(trainee_id, template_id):
    with db() as c:
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        if not t: raise ValueError("نموذج الاختبار غير موجود.")
        
        t_dict = dict(t)
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
        completed_today = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND template_id=? AND status='submitted' AND started_at>=?",
                                    (trainee_id, template_id, today_start)).fetchone()
        if completed_today: raise ValueError("عذراً، لا يمكنك أداء هذا الاختبار أكثر من مرة في نفس اليوم.")
        active = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND status='active'", (trainee_id,)).fetchone()
        if active: raise ValueError("لديك اختبار نشط بالفعل.")

    qs = choose_questions(t)
    started = now_cairo()
    expires = started + timedelta(minutes=int(t_dict.get("duration_minutes", 60)))
    
    with db() as c:
        cur = c.execute("INSERT INTO exam_sessions(trainee_id,template_id,started_at,expires_at,status) VALUES(?,?,?,?,?)",
                        (trainee_id, template_id, started.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds"), "active"))
        sid = cur.lastrowid
        for pos, q in enumerate(qs):
            try: opts_parsed = json.loads(q["options_json"])
            except: opts_parsed = ["نعم", "لا"]
            order = list(range(len(opts_parsed)))
            random.shuffle(order)
            c.execute("INSERT INTO exam_questions(session_id,question_id,position,option_order_json) VALUES(?,?,?,?)",
                      (sid, q["id"], pos, json.dumps(order)))
        c.execute("UPDATE trainees SET status='active', updated_at=? WHERE id=?", (now(), trainee_id))
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
    logo1 = sett.get("logo_base64", DEFAULT_LOGO)
    logo2 = sett.get("logo2_base64", "")
    
    logos_list_html = f'<img src="{logo1}" style="width: 35px; height: 35px; object-fit: contain;" alt="Logo 1">'
    if logo2:
        logos_list_html += f'<img src="{logo2}" style="width: 35px; height: 35px; object-fit: contain;" alt="Logo 2">'
        
    return f"""
    <div style="display: flex; gap: 4px; align-items: center;">
        {logos_list_html}
    </div>
    """

def render_top_left_logo_html():
    sett = get_print_settings()
    logo3 = sett.get("logo3_base64", "")
    if logo3:
        return f"""
        <div style="position: absolute; top: 10mm; left: 12mm; text-align: left; z-index: 2;">
            <img src="{logo3}" style="width: 35px; height: 35px; object-fit: contain;" alt="Logo 3">
        </div>
        """
    return ""

def generate_qr_code_base64(data_text):
    qr = qrcode.QRCode(version=1, box_size=5, border=1)
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return "data:image/png;base64," + __import__("base64").b64encode(buffered.getvalue()).decode("utf-8")

def generate_customizable_certificate_html(sid, custom_title=None, custom_notes=None):
    sett = get_print_settings()
    title_val = custom_title if custom_title is not None else sett.get("default_cert_title", "شهادة اجتياز اختبار معتمدة")
    notes_val = custom_notes if custom_notes is not None else sett.get("default_cert_notes", "تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد")
    prefix_val = sett.get("trainee_prefix", "").strip()
    title_role_val = sett.get("trainee_title", "").strip()
    line_sp = sett.get("line_spacing", 1.25)

    with db() as c:
        r = c.execute("""SELECT s.*, t.name trainee_name, t.facility, t.profession trainee_profession, e.name template_name, e.exam_type 
                         FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?""", (sid,)).fetchone()
    if not r: return ""
    status_text = "اجتزت بنجاح" if r["passed"] else "لم تجتز الاختبار"
    score_val, max_score_val, percent_val = r["score"] or 0, r["max_score"] or 0, r["percent"] or 0.0
    tpl_name = r["template_name"] or "اختبار تقييمي معتمد"
    exam_type_str = r["exam_type"] or "قبل التدريب"
    
    formatted_header = sett.get("header_text", "جمهورية مصر العربية<br>وزارة الصحة والسكان<br>مديرية الشئون الصحية بالشرقية<br>الإدارة الصحية بأولاد صقر")

    bg_data = sett.get("bg_base64", "")
    frame_data = sett.get("frame_base64", "")
    
    bg_style = f"background: url('{bg_data}') no-repeat center center; background-size: cover;" if bg_data else "background: #ffffff;"
    
    if frame_data:
        frame_style = f"background: url('{frame_data}') no-repeat center center; background-size: 100% 100%;"
    else:
        frame_style = "border: none;"

    prefix_str = f"{prefix_val} " if prefix_val else ""
    title_role_str = f"{title_role_val} " if title_role_val else ""
    prof_field_val = r.get("trainee_profession", "") or sett.get("trainee_profession", "أخصائي الأمراض المتوطنة")
    profession_str = f" - {prof_field_val}" if prof_field_val else ""
    
    full_line_text = f"{prefix_str}{title_role_str}{r['trainee_name']}{profession_str}"
    line_html = f"<div style='font-size: 14pt; color: #065f46; font-weight: 900; margin: 4px 0; line-height: {line_sp};'>{esc(full_line_text)}</div>"

    qr_data_str = f"{r['certificate_id']}"
    qr_base64 = generate_qr_code_base64(qr_data_str)

    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ 
                size: A4 portrait; 
                margin: 4mm; 
            }}
            body {{ 
                font-family: 'Cairo', 'Tahoma', sans-serif; 
                background: #fdfbf7; 
                margin: 0; 
                padding: 0; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                direction: rtl; 
                -webkit-print-color-adjust: exact; 
                line-height: {line_sp};
            }}
            .cert-wrapper {{ 
                width: 90%;
                max-width: 180mm;
                min-height: 230mm;
                max-height: 255mm;
                {frame_style}
                {bg_style}
                display: flex; 
                flex-direction: column; 
                justify-content: space-between; 
                align-items: center; 
                padding: 8mm 12mm; 
                box-sizing: border-box; 
                position: relative; 
                margin: auto;
                box-shadow: 0 4px 12px rgba(0,0,0,0.06); 
                page-break-inside: avoid;
                break-inside: avoid;
            }}
            .header-top {{ position: absolute; top: 8mm; left: 12mm; text-align: left; z-index: 2; }}
            .header-right {{ position: absolute; top: 8mm; right: 12mm; text-align: right; font-size: 8.5pt; font-weight: bold; color: #065f46; line-height: {line_sp}; z-index: 2; }}
            .cert-body {{ text-align: center; margin-top: 8mm; width: 100%; z-index: 2; }}
            h2 {{ color: #047857; font-size: 13pt; margin-bottom: 2px; line-height: {line_sp}; }}
            p {{ font-size: 9pt; line-height: {line_sp}; color: #1f2937; margin: 4px 0; }}
            .notes-box {{ background: rgba(240, 253, 244, 0.9); border: 1px dashed #059669; padding: 3px 4mm; margin: 3px auto; width: 85%; border-radius: 6px; font-weight: bold; color: #065f46; font-size: 8pt; line-height: {line_sp}; }}
            .footer-bottom {{ width: 100%; display: flex; justify-content: space-between; align-items: center; font-size: 8pt; font-weight: bold; text-align: center; border-top: 2px dashed #059669; padding-top: 2mm; margin-top: 2mm; z-index: 2; }}
            .cert-watermark {{ font-size: 7pt; color: #065f46; font-weight: bold; margin-top: 1px; z-index: 2; }}
        </style>
    </head>
    <body>
        <div class="cert-wrapper">
            <div class="header-right">{formatted_header}</div>
            <div class="header-top">{render_logos_html()}</div>
            {render_top_left_logo_html()}
            <div class="cert-body">
                <h2>{esc(title_val)}</h2>
                <hr style="width: 30%; border: 1px solid #059669; margin: 2px auto 6px auto;">
                {line_html}
                <p style="margin-top: 4px;">
                    جهة العمل: <b>{esc(r["facility"])}</b> &nbsp;|&nbsp; الوظيفة: <b>{esc(prof_field_val)}</b><br>
                    الاختبار: <b>{esc(tpl_name)} ({esc(exam_type_str)})</b><br>
                    النتيجة: <b>{score_val} / {max_score_val} ({percent_val:.1f}%)</b> &nbsp;|&nbsp; 
                    الحالة: <b style="color: {'green' if r['passed'] else 'red'};">{status_text}</b><br>
                    رقم التحقق والشهادة: <span style="font-weight: bold; color: #065f46;">{r["certificate_id"]}</span>
                </p>
                {f'<div class="notes-box">{esc(notes_val)}</div>' if notes_val else ''}
            </div>
            <div class="footer-bottom">
                <div>مسؤول التدريب</div>
                <div>رئيس وحدة الأمراض المتوطنة</div>
                <div>مدير وحدة المتوطنة</div>
                <div>يعتمد مدير عام الإدارة</div>
                <div style="background: transparent; padding: 0px; text-align: center;">
                    <img src="{qr_base64}" style="width: 38px; height: 38px; display: block; margin: auto;" alt="QR Code">
                    <div style="font-size: 5pt; color: #065f46; margin-top: 1px;">مسح للتحقق</div>
                </div>
            </div>
            <div class="cert-watermark">Developed by Dr/Ahmed.S.Hegazy</div>
        </div>
    </body>
    </html>
    """

def generate_trainee_exam_sheet_html(sid):
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    with db() as c:
        s = c.execute("""SELECT s.*, t.name trainee_name, t.facility, t.profession trainee_profession, e.name template_name, e.exam_type 
                         FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?""", (sid,)).fetchone()
        if not s: return ""
        rows = c.execute("""SELECT eq.*, q.question, q.options_json, q.answer 
                            FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=? ORDER BY eq.position""", (sid,)).fetchall()
    
    q_html_content = ""
    for idx, r in enumerate(rows, start=1):
        try: opts = json.loads(r["options_json"])
        except: opts = ["نعم", "لا"]
        try: order = json.loads(r["option_order_json"])
        except: order = list(range(len(opts)))
        
        disp_opts = [opts[i] for i in order]
        selected_opt_idx = r["selected_option"]
        correct_ans_idx = r["answer"]
        is_correct = r["is_correct"]

        raw_q_text = r["question"]
        img_tag_html = ""
        if "IMAGE:" in raw_q_text:
            parts = raw_q_text.split("\n\n")
            img_uri = parts[0].replace("IMAGE:", "").strip()
            q_text_clean = parts[1] if len(parts) > 1 else ""
            if img_uri:
                img_tag_html = f'<div style="margin: 2px 0; text-align: center;"><img src="{img_uri}" style="max-height: 45px; max-width: 100%; object-fit: contain; border-radius: 3px; border: 1px solid #cbd5e1;"></div>'
        else:
            q_text_clean = raw_q_text

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
            
            opts_html += f'<div style="padding: 1px 4px; margin: 1px 0; background: {style_bg}; border: 1px solid {border_color}; border-radius: 2px; font-size: 7.5pt; line-height: {line_sp};">{icon_str} {esc(opt_text)}</div>'
        
        status_badge = '<span style="color: green; font-weight: bold;">صحيح</span>' if is_correct else '<span style="color: red; font-weight: bold;">خاطئ</span>'
        
        q_html_content += f"""
        <div style="margin-bottom: 4px; padding: 4px 6px; background: #ffffff; border: 1px solid #059669; border-radius: 3px; page-break-inside: avoid; break-inside: avoid;">
            <div style="font-weight: bold; color: #065f46; margin-bottom: 1px; font-size: 8pt; line-height: {line_sp};">({idx}) {esc(q_text_clean)} &nbsp;|&nbsp; النتيجة: {status_badge}</div>
            {img_tag_html}
            <div style="margin-top: 2px; padding-right: 2px;">{opts_html}</div>
        </div>
        """

    score_val, max_score_val, percent_val = s["score"] or 0, s["max_score"] or 0, s["percent"] or 0.0
    
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 auto; margin: 5mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0; padding: 3mm; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
            .report-wrapper {{ max-width: 210mm; margin: auto; position: relative; }}
            .report-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #059669; padding-bottom: 3mm; margin-bottom: 4mm; }}
            .header-right {{ font-size: 8.5pt; font-weight: bold; color: #065f46; line-height: {line_sp}; }}
            h2 {{ text-align: center; color: #047857; font-size: 11pt; margin: 2px 0; line-height: {line_sp}; }}
            .tpl-info {{ background: #f0fdf4; border: 1px dashed #059669; padding: 3px 6px; border-radius: 3px; margin-bottom: 5px; font-size: 8pt; font-weight: bold; color: #065f46; text-align: center; line-height: {line_sp}; }}
            .questions-grid {{
                column-count: 2;
                column-gap: 4mm;
                column-fill: auto;
            }}
            .footer {{ margin-top: 5px; display: flex; justify-content: space-between; font-size: 8pt; font-weight: bold; border-top: 1px dashed #059669; padding-top: 3mm; page-break-inside: avoid; break-inside: avoid; line-height: {line_sp}; }}
        </style>
    </head>
    <body>
        <div class="report-wrapper">
            {render_top_left_logo_html()}
            <div class="report-header">
                <div class="header-right">{sett.get('header_text', '')}</div>
                <div>{render_logos_html()}</div>
            </div>
            <h2>نموذج إجابة واختبار المتدرب: {esc(s['trainee_name'])}</h2>
            <div class="tpl-info">
                جهة العمل: {esc(s['facility'])} | الوظيفة: {esc(s.get('trainee_profession', ''))} | الاختبار: {esc(s['template_name'] or 'اختبار معتمد')} ({esc(s['exam_type'] or 'قبل التدريب')}) | النتيجة: {score_val} / {max_score_val} ({percent_val:.1f}%)
            </div>
            <div class="questions-grid">
                {q_html_content}
            </div>
            <div class="footer">
                <div>مسؤول التدريب</div>
                <div>رئيس وحدة الأمراض المتوطنة</div>
                <div>مدير وحدة المتوطنة</div>
                <div>مدير عام الإدارة</div>
            </div>
        </div>
    </body>
    </html>
    """

def generate_general_report_html(title, content_html, target_pages=1):
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 auto; margin: 5mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0; padding: 4mm; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
            .report-wrapper {{ max-width: 210mm; margin: auto; position: relative; }}
            .report-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #059669; padding-bottom: 4px; margin-bottom: 8px; }}
            .header-right {{ font-size: 9pt; font-weight: bold; color: #065f46; line-height: {line_sp}; }}
            h2 {{ text-align: center; color: #047857; font-size: 13pt; margin: 6px 0; line-height: {line_sp}; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 6px; font-size: 8.5pt; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 4px 6px; text-align: center; line-height: {line_sp}; }}
            th {{ background-color: #059669; color: white; font-weight: bold; }}
            tr:nth-child(even) {{ background-color: #f0fdf4; }}
            .footer {{ margin-top: 10px; display: flex; justify-content: space-between; font-size: 9pt; font-weight: bold; border-top: 1px dashed #059669; padding-top: 6px; page-break-inside: avoid; break-inside: avoid; line-height: {line_sp}; }}
        </style>
    </head>
    <body>
        <div class="report-wrapper">
            {render_top_left_logo_html()}
            <div class="report-header">
                <div class="header-right">{sett.get('header_text', '')}</div>
                <div>{render_logos_html()}</div>
            </div>
            <h2>{esc(title)}</h2>
            <div style="text-align: left; font-size: 8pt; color: #6b7280; margin-bottom: 4px;">تاريخ الإصدار: {now_cairo().strftime('%Y-%m-%d %I:%M %p')}</div>
            {content_html}
            <div class="footer">
                <div>مسؤول التدريب</div>
                <div>رئيس وحدة الأمراض المتوطنة</div>
                <div>مدير وحدة المتوطنة</div>
                <div>مدير عام الإدارة</div>
            </div>
        </div>
    </body>
    </html>
    """

def generate_action_plan_report_html(title, content_html, target_pages=1):
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 auto; margin: 5mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0; padding: 4mm; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
            .report-wrapper {{ max-width: 210mm; margin: auto; position: relative; }}
            .report-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #059669; padding-bottom: 4px; margin-bottom: 8px; }}
            .header-right {{ font-size: 9pt; font-weight: bold; color: #065f46; line-height: {line_sp}; }}
            h2 {{ text-align: center; color: #047857; font-size: 13pt; margin: 6px 0; line-height: {line_sp}; }}
            .footer {{ margin-top: 10px; display: flex; justify-content: space-between; font-size: 9pt; font-weight: bold; border-top: 1px dashed #059669; padding-top: 6px; page-break-inside: avoid; break-inside: avoid; line-height: {line_sp}; }}
        </style>
    </head>
    <body>
        <div class="report-wrapper">
            {render_top_left_logo_html()}
            <div class="report-header">
                <div class="header-right">{sett.get('header_text', '')}</div>
                <div>{render_logos_html()}</div>
            </div>
            <h2>{esc(title)}</h2>
            <div style="text-align: left; font-size: 8pt; color: #6b7280; margin-bottom: 4px;">تاريخ الإصدار: {now_cairo().strftime('%Y-%m-%d %I:%M %p')}</div>
            {content_html}
            <div class="footer">
                <div>مسؤول التدريب</div>
                <div>رئيس وحدة الأمراض المتوطنة</div>
                <div>مدير وحدة المتوطنة</div>
                <div>مدير عام الإدارة</div>
            </div>
        </div>
    </body>
    </html>
    """

def generate_exam_template_print_html(template_id):
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    with db() as c:
        tpl = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        if not tpl: return ""
        t_dict = dict(tpl)
        questions_list = choose_questions(t_dict)
    
    q_html_content = ""
    for idx, q in enumerate(questions_list, start=1):
        try: opts = json.loads(q["options_json"])
        except: opts = ["نعم", "لا"]
        
        raw_q_text = q["question"]
        img_tag_html = ""
        if "IMAGE:" in raw_q_text:
            parts = raw_q_text.split("\n\n")
            img_uri = parts[0].replace("IMAGE:", "").strip()
            q_text_clean = parts[1] if len(parts) > 1 else ""
            if img_uri:
                img_tag_html = f'<div style="margin: 2px 0; text-align: center;"><img src="{img_uri}" style="max-height: 55px; max-width: 100%; object-fit: contain; border-radius: 3px; border: 1px solid #cbd5e1;"></div>'
        else:
            q_text_clean = raw_q_text

        opts_html = "".join([f'<div style="padding: 1px 4px; margin: 1px 0; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 2px; font-size: 8pt; line-height: {line_sp};">🔲 {esc(opt)}</div>' for opt in opts])
        
        q_html_content += f"""
        <div style="margin-bottom: 4px; padding: 4px 6px; background: #ffffff; border: 1px solid #059669; border-radius: 3px; page-break-inside: avoid; break-inside: avoid;">
            <div style="font-weight: bold; color: #065f46; margin-bottom: 1px; font-size: 8.5pt; line-height: {line_sp};">({idx}) {esc(q_text_clean)}</div>
            {img_tag_html}
            <div style="margin-top: 2px; padding-right: 2px;">{opts_html}</div>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 auto; margin: 5mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0; padding: 3mm; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
            .report-wrapper {{ max-width: 210mm; margin: auto; position: relative; }}
            .report-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #059669; padding-bottom: 4mm; margin-bottom: 6mm; }}
            .header-right {{ font-size: 9pt; font-weight: bold; color: #065f46; line-height: {line_sp}; }}
            h2 {{ text-align: center; color: #047857; font-size: 12pt; margin: 2px 0; line-height: {line_sp}; }}
            .tpl-info {{ background: #f0fdf4; border: 1px dashed #059669; padding: 3px 6px; border-radius: 3px; margin-bottom: 6mm; font-size: 8pt; font-weight: bold; color: #065f46; text-align: center; line-height: {line_sp}; }}
            .questions-grid {{
                column-count: 2;
                column-gap: 4mm;
                column-fill: auto;
            }}
            .footer {{ margin-top: 6px; display: flex; justify-content: space-between; font-size: 8.5pt; font-weight: bold; border-top: 1px dashed #059669; padding-top: 4mm; page-break-inside: avoid; break-inside: avoid; line-height: {line_sp}; }}
        </style>
    </head>
    <body>
        <div class="report-wrapper">
            {render_top_left_logo_html()}
            <div class="report-header">
                <div class="header-right">{sett.get('header_text', '')}</div>
                <div>{render_logos_html()}</div>
            </div>
            <h2>نموذج امتحان: {esc(t_dict['name'])} ({esc(t_dict.get('exam_type', 'قبل التدريب'))})</h2>
            <div class="tpl-info">
                التصنيف: {esc(t_dict.get('exam_type', 'قبل التدريب'))} | مدة الاختبار: {t_dict['duration_minutes']} د | نسبة النجاح: {t_dict['pass_percent']}% | إجمالي الأسئلة: {len(questions_list)}
            </div>
            <div class="questions-grid">
                {q_html_content}
            </div>
            <div class="footer">
                <div>مسؤول التدريب</div>
                <div>رئيس وحدة الأمراض المتوطنة</div>
                <div>مدير وحدة المتوطنة</div>
                <div>مدير عام الإدارة</div>
            </div>
        </div>
    </body>
    </html>
    """

def render_print_button_only(html_content, label_prefix=""):
    encoded_html = json.dumps(html_content)
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        orient_key = f"orient_{hash(label_prefix) & 0xffffffff}"
        chosen_orient = st.selectbox("اتجاه الورق للطباعة (مقاس A4):", ["رأسي (Portrait)", "أفقي (Landscape)"], key=orient_key)
    with col_opt2:
        copies_key = f"copies_{hash(label_prefix) & 0xffffffff}"
        num_pages_to_print = st.number_input("عدد الأوراق / النسخ المطلوبة (الحد الأقصى للاحتواء):", min_value=1, max_value=50, value=1, key=copies_key)
        
    orient_css = "landscape" if "أفقي" in chosen_orient else "portrait"

    js_code = """
        <div style="margin: 4px 0;">
            <button onclick="printDoc()" style="width: 100%; background-color: #059669; color: white; padding: 8px 12px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-family: 'Cairo', sans-serif; font-size: 13pt;">
                🖨 طباعة / حفظ المستند (A4 """ + chosen_orient + """ - احتواء ضمن """ + str(num_pages_to_print) + """ صفحة - """ + label_prefix + """)
            </button>
        </div>
        <script>
            function printDoc() {
                var win = window.open('', '_blank');
                var targetPages = """ + str(num_pages_to_print) + """;
                
                var styledHtml = """ + encoded_html + """;
                
                var finalPagesHtml = '';
                for (var i = 0; i < targetPages; i++) {
                    finalPagesHtml += styledHtml;
                }
                
                win.document.write(finalPagesHtml);
                win.document.close();
                win.focus();
                setTimeout(function(){ win.print(); }, 600);
            }
        </script>
    """
    components.html(js_code, height=100)

# ============================================================
# 5) واجهات النظام وتوجيه الشاشات
# ============================================================
for k, v in {"logged_in": False, "username": "", "role": "", "permissions": [], "trainee_id": "", "trainee_name": "", "exam_session_id": None, "last_result_id": None, "form_key": 0, "add_success_msg": "", "active_admin_tab": "📊 لوحة التحكم", "scanned_cert_code": ""}.items():
    if k not in st.session_state: st.session_state[k] = v

def header():
    header_html = f"""
    <style>
        @keyframes electricMultiGlow {{
            0% {{
                box-shadow: 0 0 15px rgba(16, 185, 129, 0.4), 0 0 30px rgba(5, 150, 105, 0.3), inset 0 0 15px rgba(255, 255, 255, 0.2);
                border-color: #34d399;
            }}
            14.28% {{
                box-shadow: 0 0 20px rgba(20, 184, 166, 0.5), 0 0 35px rgba(13, 148, 136, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.3);
                border-color: #2dd4bf;
            }}
            28.56% {{
                box-shadow: 0 0 20px rgba(14, 165, 233, 0.5), 0 0 35px rgba(2, 132, 199, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.3);
                border-color: #38bdf8;
            }}
            42.84% {{
                box-shadow: 0 0 20px rgba(139, 92, 246, 0.5), 0 0 35px rgba(109, 40, 217, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.3);
                border-color: #a78bfa;
            }}
            57.12% {{
                box-shadow: 0 0 20px rgba(245, 158, 11, 0.5), 0 0 35px rgba(217, 119, 6, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.3);
                border-color: #fbbf24;
            }}
            71.40% {{
                box-shadow: 0 0 20px rgba(251, 146, 60, 0.5), 0 0 35px rgba(234, 88, 12, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.3);
                border-color: #fb923c;
            }}
            85.68% {{
                box-shadow: 0 0 20px rgba(248, 113, 113, 0.5), 0 0 35px rgba(239, 68, 68, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.3);
                border-color: #f87171;
            }}
            100% {{
                box-shadow: 0 0 15px rgba(16, 185, 129, 0.4), 0 0 30px rgba(5, 150, 105, 0.3), inset 0 0 15px rgba(255, 255, 255, 0.2);
                border-color: #34d399;
            }}
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
            cert_to_verify = c.execute("""SELECT s.*, t.name trainee_name, t.facility, t.profession trainee_profession, e.name template_name, e.exam_type 
                                           FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id 
                                           WHERE (s.certificate_id LIKE ? OR s.id=?) AND t.hidden=0""", (f"%{cert_code_clean}%", cert_code_clean.replace("ELX-", "").lstrip("0") or "0")).fetchone()

    if cert_to_verify:
        r = cert_to_verify
        status_str = "معتمدة وصحيحة بنسبة 100%" if r["passed"] else "غير اجتياز / غير معتمدة"
        score_val, max_score_val, percent_val = r["score"] or 0, r["max_score"] or 0, r["percent"] or 0.0
        
        st.markdown(f"""
        <div style="background: #f0fdf4; border: 2px solid #059669; padding: 20px; border-radius: 12px; margin-top: 15px;">
            <h3 style="color: #065f46; margin-top: 0;">✅ نتيجة التحقق وصحة البيانات الواردة:</h3>
            <p style="font-size: 11pt; color: #111827; line-height: 1.6;">
                👤 <b>اسم المتدرب:</b> {esc(r['trainee_name'])}<br>
                🩺 <b>الوظيفة / التخصص:</b> {esc(r.get('trainee_profession', ''))}<br>
                🏥 <b>جهة العمل والمنشأة:</b> {esc(r['facility'])}<br>
                📋 <b>اسم الاختبار:</b> {esc(r['template_name'] or 'اختبار معتمد')} ({esc(r['exam_type'] or 'قبل التدريب')})<br>
                📊 <b>الدرجة والنسبة المئوية:</b> {score_val} / {max_score_val} ({percent_val:.1f}%)<br>
                🏷️️ <b>حالة الاعتماد:</b> <b style="color: {'green' if r['passed'] else 'red'};">{status_str}</b><br>
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
                .meta-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 11pt; }}
                .meta-table th, .meta-table td {{ border: 1px solid #cbd5e1; padding: 8px 12px; text-align: right; }}
                .meta-table th {{ background-color: #059669; color: white; }}
                .footer {{ margin-top: 30px; display: flex; justify-content: space-between; font-weight: bold; font-size: 10pt; border-top: 1px dashed #059669; padding-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="doc-wrapper">
                <h2>وثيقة إثبات صحة البيانات والاعتماد الرسمي</h2>
                <div style="text-align: center; font-size: 9pt; color: #6b7280; margin-bottom: 15px;">صادر عن نظام تقييم واختبار العاملين بالأمراض المتوطنة</div>
                <table class="meta-table">
                    <tr><th>اسم المتدرب</th><td>{esc(r['trainee_name'])}</td></tr>
                    <tr><th>الوظيفة / التخصص</th><td>{esc(r.get('trainee_profession', ''))}</td></tr>
                    <tr><th>جهة العمل</th><td>{esc(r['facility'])}</td></tr>
                    <tr><th>اسم الاختبار</th><td>{esc(r['template_name'] or 'اختبار معتمد')} ({esc(r['exam_type'] or 'قبل التدريب')})</td></tr>
                    <tr><th>النتيجة والنسبة</th><td>{score_val} / {max_score_val} ({percent_val:.1f}%)</td></tr>
                    <tr><th>حالة التحقق</th><td style="color: green; font-weight: bold;">{status_str}</td></tr>
                    <tr><th>رقم الشهادة</th><td><span style="font-weight: bold; color: #065f46;">{r['certificate_id']}</span></td></tr>
                    <tr><th>تاريخ الاعتماد</th><td>{r['submitted_at'] or r['started_at']}</td></tr>
                </table>
                <div class="footer">
                    <div>مسؤول التدريب</div>
                    <div>رئيس وحدة الأمراض المتوطنة</div>
                    <div>مدير عام الإدارة</div>
                </div>
            </div>
        </body>
        </html>
        """
        st.markdown("<br>", unsafe_allow_html=True)
        render_print_button_only(verification_doc_html, f"توثيق صحة شهادة {r['certificate_id']}")
    elif search_cert_code.strip():
        st.warning("⚠ عذراً، لم يتم العثور على شهادة بهذا الكود. تأكد من صحة رقم الشهادة.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("العودة لتسجيل الدخول / الرئيسية"):
        st.session_state.show_verification_portal = False
        st.rerun()

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
    
    with st.form("trainee_request_hierarchical"):
        st.markdown("##### 📍 الجهة الإدارية التابع لها:")
        st.text_input("جمهورية مصر العربية", value="جمهورية مصر العربية", disabled=True)
        st.text_input("وزارة الصحة والسكان", value="وزارة الصحة والسكان", disabled=True)

        if not hier_data:
            st.warning("⚠ لا توجد بيانات مسجلة في الهيكل الإداري حالياً. يرجى إضافتها من لوحة التحكم أولاً.")
            facility_final_str = ""
        else:
            govs_list = sorted(list(set(item["governorate"] for item in hier_data)))
            sel_gov = st.selectbox("المحافظة:", ["-- اختر المحافظة --"] + govs_list, index=0)
            
            filtered_auths = sorted(list(set(item["authority"] for item in hier_data if sel_gov == "-- اختر المحافظة --" or item["governorate"] == sel_gov)))
            sel_auth = st.selectbox("الهيئة:", ["-- اختر الهيئة --"] + filtered_auths, index=0)
            
            filtered_centers = sorted(list(set(item["center"] for item in hier_data if (sel_gov == "-- اختر المحافظة --" or item["governorate"] == sel_gov) and (sel_auth == "-- اختر الهيئة --" or item["authority"] == sel_auth))))
            sel_center = st.selectbox("المركز:", ["-- اختر المركز --"] + filtered_centers, index=0)
            
            filtered_admins = sorted(list(set(item["administration"] for item in hier_data if (sel_gov == "-- اختر المحافظة --" or item["governorate"] == sel_gov) and (sel_auth == "-- اختر الهيئة --" or item["authority"] == sel_auth) and (sel_center == "-- اختر المركز --" or item["center"] == sel_center))))
            sel_admin = st.selectbox("الإدارة:", ["-- اختر الإدارة --"] + filtered_admins, index=0)
            
            filtered_facs = sorted(list(set(item["facility_name"] for item in hier_data if (sel_gov == "-- اختر المحافظة --" or item["governorate"] == sel_gov) and (sel_auth == "-- اختر الهيئة --" or item["authority"] == sel_auth) and (sel_center == "-- اختر المركز --" or item["center"] == sel_center) and (sel_admin == "-- اختر الإدارة --" or item["administration"] == sel_admin))))
            sel_fac = st.selectbox("المنشأة / وحدة الأمراض المتوطنة:", ["-- اختر المنشأة --"] + filtered_facs, index=0)
            
            if sel_gov != "-- اختر المحافظة --" and sel_auth != "-- اختر الهيئة --" and sel_center != "-- اختر المركز --" and sel_admin != "-- اختر الإدارة --" and sel_fac != "-- اختر المنشأة --":
                facility_final_str = f"جمهورية مصر العربية - وزارة الصحة والسكان - {sel_gov} - {sel_auth} - {sel_center} - {sel_admin} - {sel_fac}"
            else:
                facility_final_str = ""

        name = st.text_input("الاسم الرباعي:", value="")
        phone = st.text_input("رقم الهاتف:", value="")
        selected_profession = st.selectbox("الوظيفة / التخصص:", professions_list)
        
        with db() as c: all_tpls_opts = {f"{row['name']} ({row['exam_type']})": row["id"] for row in c.execute("SELECT id, name, exam_type FROM exam_templates ORDER BY name ASC").fetchall()}
        tpl_choices_list = ["-- اختر نموذج الاختبار --"] + list(all_tpls_opts.keys()) if all_tpls_opts else ["لا توجد نماذج اختبارات مسجلة"]
        selected_req_tpl_name = st.selectbox("اختر نموذج الاختبار:", tpl_choices_list, index=0)
        
        if st.form_submit_button("إرسال الطلب والدخول", use_container_width=True):
            if not facility_final_str:
                st.warning("⚠️ يرجى استكمال اختيار جميع حقول الهيكل الإداري المتسلسلة بدقة.")
            elif selected_req_tpl_name == "-- اختر نموذج الاختبار --":
                st.warning
