import os, io, re, ast, json, sqlite3, hashlib, secrets, random, time, html
from datetime import datetime, timedelta, date
from contextlib import contextmanager

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import qrcode
from PIL import Image

# ============================================================
# 1) إعدادات التطبيق الأساسية (الإصدار V1.0 - مع حماية كاملة لـ Screenshot)
# ============================================================
st.set_page_config(
    page_title="نظام تقييم واختبار العاملين بمعامل المتوطنة🔬 - System V1.0",
    page_icon="🔬",
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
# 2) حقن التنسيقات (CSS) وحماية الأمان ومنع لقطات الشاشة
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
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 45%, #bbf7d0 100%) !important;
    background-attachment: fixed !important;
    -webkit-filter: contrast(102%);
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
    padding-top: 4.5rem !important;
    padding-bottom: 7rem !important;
}

.hero {
    background: linear-gradient(90deg, #064e3b, #065f46, #047857) !important;
    color: #ffffff !important;
    padding: 18px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    margin-bottom: 25px;
}

.card, .question {
    background: #ffffff !important;
    color: #111827 !important;
    padding: 18px 24px;
    border-radius: 10px;
    margin-bottom: 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    border-right: 6px solid #059669 !important;
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
🔬 جميع الحقوق محفوظة © 2026 | تصميم وتطوير: <b>Dr/Ahmed.S.Hegazy</b>
</div>
""", unsafe_allow_html=True)

# ============================================================
# 3) دوال النظام وقاعدة البيانات وإعادة الترتيب التلقائي للـ ID
# ============================================================
def now():
    return datetime.now().isoformat(timespec="seconds")

def today_date():
    return date.today().isoformat()

def esc(x):
    return html.escape("" if x is None else str(x))

def clean_question_text(q_text):
    if not q_text:
        return ""
    cleaned = re.sub(r"\(نموذج معملي.*?\)", "", q_text)
    cleaned = re.sub(r"\(مجموعة معملية.*?\)", "", cleaned)
    return normalize_text(cleaned)

def normalize_text(x):
    x = "" if x is None else str(x)
    return re.sub(r"\s+", " ", x.strip()).lower()

def reindex_hierarchical_facilities():
    with db() as c:
        rows = c.execute("SELECT authority, governorate, administration, center, facility_name, created_at, hidden FROM hierarchical_facilities ORDER BY id ASC").fetchall()
        c.execute("DELETE FROM hierarchical_facilities")
        c.execute("DELETE FROM sqlite_sequence WHERE name='hierarchical_facilities'")
        for r in rows:
            c.execute("INSERT INTO hierarchical_facilities(authority, governorate, administration, center, facility_name, created_at, hidden) VALUES(?,?,?,?,?,?,?)",
                      (r["authority"], r["governorate"], r["administration"], r["center"], r["facility_name"], r["created_at"], r.get("hidden", 0)))

def reindex_trainees():
    with db() as c:
        c.execute("PRAGMA foreign_keys=OFF;")
        rows = c.execute("SELECT id, facility, name, phone, status, assigned_template_id, created_at, approved_at, updated_at, hidden FROM trainees ORDER BY id ASC").fetchall()
        c.execute("DELETE FROM trainees")
        c.execute("DELETE FROM sqlite_sequence WHERE name='trainees'")
        id_mapping = {}
        for new_id, r in enumerate(rows, start=1):
            old_id = r["id"]
            c.execute("INSERT INTO trainees(id, facility, name, phone, status, assigned_template_id, created_at, approved_at, updated_at, hidden) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (new_id, r["facility"], r["name"], r["phone"], r["status"], r["assigned_template_id"], r["created_at"], r["approved_at"], r["updated_at"], r.get("hidden", 0)))
            id_mapping[old_id] = new_id
        
        for old_id, new_id in id_mapping.items():
            c.execute("UPDATE exam_sessions SET trainee_id=? WHERE trainee_id=?", (new_id, old_id))
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
    "🖨 الطباعة والترويسة": "إعدادات هوامش وترويسات التقارير العامة",
    "🎨 إعدادات الشهادات المخصصة": "صفحة مخصصة لضبط الشهادات بالكامل",
    "🏥 الهيكل الإداري": "الهيكل الإداري والمنشآت ورفع البيانات",
    "🧑‍🔬 المتدربين والنماذج": "اعتماد المتدربين والنماذج وطباعة النتائج",
    "🧠 بنك الأسئلة": "بنك الأسئلة الشامل وإكسيل",
    "⚙ إدارة الأسئلة": "إدارة الأسئلة الفردية",
    "🧩 مواعيد الاختبارات و طباعة النماذج": "نماذج التدريب والمواعيد",
    "✍ تسجيل نتيجة يدوي": "التسجيل اليدوي للنتائج",
    "📊 التقارير": "التقارير وتحليل الأداء",
    "📈 خطط العمل": "خطط العمل التدريبية",
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
            authority TEXT NOT NULL,
            governorate TEXT NOT NULL,
            administration TEXT NOT NULL,
            center TEXT NOT NULL,
            facility_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            hidden INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS trainees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
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
        CREATE TABLE IF NOT EXISTS exam_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            exam_type TEXT NOT NULL DEFAULT 'اختبار مخصص للمالك',
            num_questions INTEGER NOT NULL DEFAULT 999999,
            duration_minutes INTEGER NOT NULL DEFAULT 60,
            pass_percent REAL NOT NULL DEFAULT 60,
            categories_json TEXT NOT NULL DEFAULT '[]',
            start_time TEXT,
            end_time TEXT,
            active INTEGER NOT NULL DEFAULT 1,
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
            specific_date TEXT,
            specific_month TEXT,
            specific_year TEXT,
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
            default_cert_notes TEXT NOT NULL DEFAULT 'تقرير أداء المعامل والإشراف الفني المعتمد',
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
            ("hierarchical_facilities", "hidden", "INTEGER NOT NULL DEFAULT 0"),
            ("users", "permissions_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("exam_templates", "start_time", "TEXT"), 
            ("exam_templates", "end_time", "TEXT"), 
            ("print_settings", "line_spacing", "REAL NOT NULL DEFAULT 1.25"),
            ("print_settings", "logo2_base64", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "logo3_base64", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "bg_base64", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "frame_base64", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "default_cert_title", "TEXT NOT NULL DEFAULT 'شهادة اجتياز اختبار معتمدة'"),
            ("print_settings", "default_cert_notes", "TEXT NOT NULL DEFAULT 'تقرير أداء المعامل والإشراف الفني المعتمد'"),
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
                "أخصائي تحاليل طبية", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني معمل", 
                "فني تمريض", "مسؤول معامل", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات)"
            ]
            c.execute("INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, line_spacing, logo_base64, logo2_base64, logo3_base64, bg_base64, frame_base64, default_cert_title, default_cert_notes, trainee_prefix, trainee_title, trainee_profession, professions_list_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (default_header, "3mm", "3mm", "3mm", "3mm", 1.25, DEFAULT_LOGO, "", "", "", "", "شهادة اجتياز اختبار معتمدة", "تقرير أداء المعامل والإشراف الفني المعتمد", "", "دكتور", "أخصائي تحاليل طبية", json.dumps(default_professions, ensure_ascii=False)))

init_db()

def get_print_settings():
    with db() as c:
        row = c.execute("SELECT * FROM print_settings ORDER BY id DESC LIMIT 1").fetchone()
        if row: 
            res = dict(row)
            try:
                res["professions_list"] = json.loads(res.get("professions_list_json", "[]"))
            except:
                res["professions_list"] = ["أخصائي تحاليل طبية", "طبيب بيطري", "فني معمل"]
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
            "default_cert_notes": "تقرير أداء المعامل والإشراف الفني المعتمد",
            "trainee_prefix": "",
            "trainee_title": "دكتور",
            "trainee_profession": "أخصائي تحاليل طبية",
            "professions_list": ["أخصائي تحاليل طبية", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني معمل", "فني تمريض", "مسؤول معامل", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات)"]
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

def create_trainee(facility, name, phone, assigned_template_id=None):
    with db() as c:
        cur = c.execute("INSERT INTO trainees(facility,name,phone,status,assigned_template_id,created_at,updated_at,hidden) VALUES(?,?,?,?,?,?,?,?)",
                        (facility, normalize_text(name), normalize_text(phone), "pending", assigned_template_id, now(), now(), 0))
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
        q = "SELECT id, facility, name, phone, status, assigned_template_id, created_at, approved_at, hidden FROM trainees"
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
            dt_now = datetime.now()
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
    started = datetime.now()
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
    notes_val = custom_notes if custom_notes is not None else sett.get("default_cert_notes", "تقرير أداء المعامل والإشراف الفني المعتمد")
    prefix_val = sett.get("trainee_prefix", "").strip()
    title_role_val = sett.get("trainee_title", "").strip()
    profession_val = sett.get("trainee_profession", "").strip()
    line_sp = sett.get("line_spacing", 1.25)

    with db() as c:
        r = c.execute("""SELECT s.*, t.name trainee_name, t.facility, e.name template_name 
                         FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?""", (sid,)).fetchone()
    if not r: return ""
    status_text = "اجتزت بنجاح" if r["passed"] else "لم تجتز الاختبار"
    score_val, max_score_val, percent_val = r["score"] or 0, r["max_score"] or 0, r["percent"] or 0.0
    tpl_name = r["template_name"] or "اختبار تقييمي معتمد"
    
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
    profession_str = f" - {profession_val}" if profession_val else ""
    
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
                    جهة العمل: <b>{esc(r["facility"])}</b> &nbsp;|&nbsp; الاختبار: <b>{esc(tpl_name)}</b><br>
                    النتيجة: <b>{score_val} / {max_score_val} ({percent_val:.1f}%)</b> &nbsp;|&nbsp; 
                    الحالة: <b style="color: {'green' if r['passed'] else 'red'};">{status_text}</b><br>
                    رقم التحقق والشهادة: <span style="font-weight: bold; color: #065f46;">{r["certificate_id"]}</span>
                </p>
                {f'<div class="notes-box">{esc(notes_val)}</div>' if notes_val else ''}
            </div>
            <div class="footer-bottom">
                <div>مسؤول التدريب</div>
                <div>رئيس قسم المعامل</div>
                <div>مدير المتوطنة</div>
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
        s = c.execute("""SELECT s.*, t.name trainee_name, t.facility, e.name template_name 
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
                جهة العمل: {esc(s['facility'])} | الاختبار: {esc(s['template_name'] or 'اختبار معتمد')} | النتيجة: {score_val} / {max_score_val} ({percent_val:.1f}%) | تاريخ أداء الاختبار: {s['submitted_at'] or s['started_at']}
            </div>
            <div class="questions-grid">
                {q_html_content}
            </div>
            <div class="footer">
                <div>مسؤول التدريب</div>
                <div>رئيس قسم المعامل</div>
                <div>مدير المتوطنة</div>
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
            <div style="text-align: left; font-size: 8pt; color: #6b7280; margin-bottom: 4px;">تاريخ الإصدار: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</div>
            {content_html}
            <div class="footer">
                <div>مسؤول التدريب</div>
                <div>رئيس قسم المعامل</div>
                <div>مدير المتوطنة</div>
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
            <div style="text-align: left; font-size: 8pt; color: #6b7280; margin-bottom: 4px;">تاريخ الإصدار: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</div>
            {content_html}
            <div class="footer">
                <div>مسؤول التدريب</div>
                <div>رئيس قسم المعامل</div>
                <div>مدير المتوطنة</div>
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
            .tpl-info {{ background: #f0fdf4; border: 1px dashed #059669; padding: 3px 6px; border-radius: 3px; margin-bottom: 6px; font-size: 8pt; font-weight: bold; color: #065f46; text-align: center; line-height: {line_sp}; }}
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
            <h2>نموذج امتحان: {esc(t_dict['name'])}</h2>
            <div class="tpl-info">
                مدة الاختبار: {t_dict['duration_minutes']} د | نسبة النجاح: {t_dict['pass_percent']}% | إجمالي الأسئلة: {len(questions_list)}
            </div>
            <div class="questions-grid">
                {q_html_content}
            </div>
            <div class="footer">
                <div>مسؤول التدريب</div>
                <div>رئيس قسم المعامل</div>
                <div>مدير المتوطنة</div>
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
                var pageRule = '@page { size: A4 """ + orient_css + """; margin: 4mm; @bottom-right { content: counter(page); }; }';
                
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
# 7) واجهات النظام وتوجيه الشاشات
# ============================================================
for k, v in {"logged_in": False, "username": "", "role": "", "permissions": [], "trainee_id": None, "trainee_name": "", "exam_session_id": None, "last_result_id": None, "form_key": 0, "add_success_msg": "", "active_admin_tab": "📊 لوحة التحكم", "scanned_cert_code": ""}.items():
    if k not in st.session_state: st.session_state[k] = v

def header():
    st.markdown('<div class="hero"><h1>🔬 نظام تقييم واختبار العاملين بمعامل المتوطنة</h1><div>System V1.0<br><small style="color:#d1fae5;">Developed by Dr/Ahmed.S.Hegazy</small></div></div>', unsafe_allow_html=True)

def verification_portal_view():
    header()
    st.markdown("### 🔍 صفحة التحقق الرقمي من صحة الشهادات والبيانات الواردة")
    st.info("يمكنك إدخال رقم الشهادة أو كود التحقق يدوياً، أو رفع صورة QR Code للشهادة للتحقق الفوري منها.")

    uploaded_qr_img = st.file_uploader("📥 رفع صورة QR Code للشهادة:", type=["png", "jpg", "jpeg"])
    if uploaded_qr_img is not None:
        try:
            from PIL import Image as PILImage
            import numpy as np
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
            cert_to_verify = c.execute("""SELECT s.*, t.name trainee_name, t.facility, e.name template_name 
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
                🏥 <b>جهة العمل والمنشأة:</b> {esc(r['facility'])}<br>
                📋 <b>اسم الاختبار:</b> {esc(r['template_name'] or 'اختبار معتمد')}<br>
                📊 <b>الدرجة والنسبة المئوية:</b> {score_val} / {max_score_val} ({percent_val:.1f}%)<br>
                🏷️ <b>حالة الاعتماد:</b> <b style="color: {'green' if r['passed'] else 'red'};">{status_str}</b><br>
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
                .doc-wrapper {{ max-width: 200mm; margin: auto; border: 3px double #059669; padding: 15mm; border-radius: 10px; position: relative; }}
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
                <div style="text-align: center; font-size: 9pt; color: #6b7280; margin-bottom: 15px;">صادر عن نظام تقييم واختبار العاملين بمعامل المتوطنة</div>
                <table class="meta-table">
                    <tr><th>اسم المتدرب</th><td>{esc(r['trainee_name'])}</td></tr>
                    <tr><th>جهة العمل</th><td>{esc(r['facility'])}</td></tr>
                    <tr><th>اسم الاختبار</th><td>{esc(r['template_name'] or 'اختبار معتمد')}</td></tr>
                    <tr><th>النتيجة والنسبة</th><td>{score_val} / {max_score_val} ({percent_val:.1f}%)</td></tr>
                    <tr><th>حالة التحقق</th><td style="color: green; font-weight: bold;">{status_str}</td></tr>
                    <tr><th>رقم الشهادة</th><td><span style="font-weight: bold; color: #065f46;">{r['certificate_id']}</span></td></tr>
                    <tr><th>تاريخ الاعتماد</th><td>{r['submitted_at'] or r['started_at']}</td></tr>
                </table>
                <div class="footer">
                    <div>مسؤول التدريب</div>
                    <div>رئيس قسم المعامل</div>
                    <div>مدير عام الإدارة</div>
                </div>
            </div>
        </body>
        </html>
        """
        st.markdown("<br>", unsafe_allow_html=True)
        render_print_button_only(verification_doc_html, f"توثيق صحة شهادة {r['certificate_id']}")
    elif search_cert_code.strip():
        st.warning("⚠️️ عذراً، لم يتم العثور على شهادة بهذا الكود. تأكد من صحة رقم الشهادة.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("العودة لتسجيل الدخول / الرئيسية"):
        st.session_state.show_verification_portal = False
        st.rerun()

def login_portal():
    header()
    
    col_v_btn1, col_v_btn2 = st.columns([2, 1])
    with col_v_btn1:
        st.markdown("#### مرحباً بك في بوابة اختبارات العاملين بمعامل المتوطنة.")
    with col_v_btn2:
        if st.button("🔍 التحقق من شهادة (QR)", use_container_width=True):
            st.session_state.show_verification_portal = True
            st.rerun()

    hier_data = get_hierarchical_data(include_hidden=False)
    
    with st.form("trainee_request_hierarchical"):
        if not hier_data:
            st.warning("⚠ لا توجد بيانات مسجلة في الهيكل الإداري حالياً. يرجى إضافتها من لوحة التحكم أولاً.")
            facility_final_str = ""
        else:
            authorities_list = sorted(list(set(item["authority"] for item in hier_data)))
            sel_auth = st.selectbox("الهيئة:", ["-- اختر الهيئة --"] + authorities_list, index=0)
            
            filtered_govs = sorted(list(set(item["governorate"] for item in hier_data if sel_auth == "-- اختر الهيئة --" or item["authority"] == sel_auth)))
            sel_gov = st.selectbox("المحافظة:", ["-- اختر المحافظة --"] + filtered_govs, index=0)
            
            filtered_admins = sorted(list(set(item["administration"] for item in hier_data if (sel_auth == "-- اختر الهيئة --" or item["authority"] == sel_auth) and (sel_gov == "-- اختر المحافظة --" or item["governorate"] == sel_gov))))
            sel_admin = st.selectbox("الإدارة الصحية:", ["-- اختر الإدارة الصحية --"] + filtered_admins, index=0)
            
            filtered_centers = sorted(list(set(item["center"] for item in hier_data if (sel_auth == "-- اختر الهيئة --" or item["authority"] == sel_auth) and (sel_gov == "-- اختر المحافظة --" or item["governorate"] == sel_gov) and (sel_admin == "-- اختر الإدارة الصحية --" or item["administration"] == sel_admin))))
            sel_center = st.selectbox("المركز:", ["-- اختر المركز --"] + filtered_centers, index=0)
            
            filtered_facs = sorted(list(set(item["facility_name"] for item in hier_data if (sel_auth == "-- اختر الهيئة --" or item["authority"] == sel_auth) and (sel_gov == "-- اختر المحافظة --" or item["governorate"] == sel_gov) and (sel_admin == "-- اختر الإدارة الصحية --" or item["administration"] == sel_admin) and (sel_center == "-- اختر المركز --" or item["center"] == sel_center))))
            sel_fac = st.selectbox("اسم المنشأة:", ["-- اختر المنشأة --"] + filtered_facs, index=0)
            
            if sel_auth != "-- اختر الهيئة --" and sel_gov != "-- اختر المحافظة --" and sel_admin != "-- اختر الإدارة الصحية --" and sel_center != "-- اختر المركز --" and sel_fac != "-- اختر المنشأة --":
                facility_final_str = f"{sel_auth} - {sel_gov} - {sel_admin} - {sel_center} - {sel_fac}"
            else:
                facility_final_str = ""

        name = st.text_input("الاسم الرباعي:", value="")
        phone = st.text_input("رقم الهاتف:", value="")
        
        with db() as c: all_tpls_opts = {row["name"]: row["id"] for row in c.execute("SELECT id, name FROM exam_templates").fetchall()}
        tpl_choices_list = ["-- اختر نموذج الاختبار --"] + list(all_tpls_opts.keys()) if all_tpls_opts else ["لا توجد نماذج اختبارات مسجلة"]
        selected_req_tpl_name = st.selectbox("اختر نموذج الاختبار:", tpl_choices_list, index=0)
        
        if st.form_submit_button("إرسال الطلب والدخول", use_container_width=True):
            if not facility_final_str:
                st.warning("⚠️ يرجى استكمال اختيار جميع حقول الهيكل الإداري المتسلسلة بدقة.")
            elif selected_req_tpl_name == "-- اختر نموذج الاختبار --":
                st.warning("⚠️ يرجى اختيار نموذج الاختبار.")
            elif name.strip() and all_tpls_opts:
                assigned_tpl_id = all_tpls_opts.get(selected_req_tpl_name)
                existing = trainee_by_credentials(name, facility_final_str)
                if existing:
                    st.session_state.trainee_id = existing["id"]
                    st.session_state.trainee_name = existing["name"]
                    st.success("تم الدخول بنجاح...")
                    st.rerun()
                else:
                    tid = create_trainee(facility_final_str, name, phone, assigned_tpl_id)
                    st.session_state.trainee_id = tid
                    st.session_state.trainee_name = name
                    st.success("✅ تم التسجيل بنجاح!")
                    st.rerun()
            else:
                st.warning("الرجاء إدخال البيانات المطلوبة.")

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
                        st.session_state.permissions = json.loads(user["permissions_json"]) if user["permissions_json"] else []
                    except:
                        st.session_state.permissions = list(ALL_MENU_MODULES.keys())
                    st.rerun()
                else:
                    st.error("بيانات غير صحيحة.")

def admin_dashboard():
    header()
    c_info, c_btn = st.columns([4, 1])
    with c_info: st.write(f"**المستخدم:** {st.session_state.username} | **الصلاحية:** {ROLES.get(st.session_state.role, '')}")
    with c_btn:
        if st.button("تسجيل الخروج", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.session_state.permissions = []
            st.rerun()

    all_modules_list = list(ALL_MENU_MODULES.keys())
    user_perms = st.session_state.permissions if st.session_state.role != "admin" else all_modules_list
    available_menus = [m for m in all_modules_list if m in user_perms]

    if not available_menus:
        st.warning("⚠️ لا توجد صلاحيات مصرحة.")
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
        st.subheader("📊 لوحة المؤشرات العامة")
        with db() as c:
            cnts = c.execute("""SELECT
                (SELECT COUNT(*) FROM trainees WHERE hidden=0) tr,
                (SELECT COUNT(*) FROM trainees WHERE status='pending' AND hidden=0) pend,
                (SELECT COUNT(*) FROM questions) qs,
                (SELECT COUNT(*) FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.status='submitted' AND t.hidden=0) ex,
                (SELECT COALESCE(AVG(s.percent),0) FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.status='submitted' AND t.hidden=0) avgp
            """).fetchone()
        cols = st.columns(5)
        for box, l, v in zip(cols, ["إجمالي المتدربين", "الطلبات المعلقة", "بنك الأسئلة", "الاختبارات المقدمة", "متوسط النتائج"],
                             [cnts["tr"], cnts["pend"], cnts["qs"], cnts["ex"], f"{cnts['avgp']:.1f}%"]):
            box.markdown(f'<div class="metric"><div class="v">{v}</div><div class="l">{l}</div></div>', unsafe_allow_html=True)

    elif selected_menu == "🖨 الطباعة والترويسة":
        st.subheader("🖨 إعدادات هوامش وترويسات التقارير العامة (مع إمكانية رفع الصور والشعارات)")
        current_set = get_print_settings()
        
        with st.form("print_settings_form"):
            header_text_val = st.text_area("نص ترويسة الجهة العامة (أعلى يمين التقارير):", value=current_set.get("header_text", "جمهورية مصر العربية"))

            st.markdown("#### 📏 هوامش الورق المطبوع للتقارير العامة (مقاس A4):")
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            with col_m1: m_top = st.text_input("الهامش العلوي:", value=current_set["margin_top"])
            with col_m2: m_bot = st.text_input("الهامش السفلي:", value=current_set["margin_bottom"])
            with col_m3: m_right = st.text_input("الهامش الأيمن:", value=current_set["margin_right"])
            with col_m4: m_left = st.text_input("الهامش الأيسر:", value=current_set["margin_left"])
            with col_m5: line_spacing_val = st.number_input("المسافة بين الأسطر:", min_value=0.8, max_value=3.0, value=float(current_set.get("line_spacing", 1.25)), step=0.05)

            st.markdown("#### 🖼️ رفع الصور والشعارات لترويسة التقارير:")
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
            if remove_logo1: current_logo1_val = DEFAULT_LOGO
            elif uploaded_logo1 is not None: current_logo1_val = f"data:image/{uploaded_logo1.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo1.read()).decode("utf-8")
            
            current_logo2_val = current_set.get("logo2_base64", "")
            if remove_logo2: current_logo2_val = ""
            elif uploaded_logo2 is not None: current_logo2_val = f"data:image/{uploaded_logo2.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo2.read()).decode("utf-8")

            current_logo3_val = current_set.get("logo3_base64", "")
            if remove_logo3: current_logo3_val = ""
            elif uploaded_logo3 is not None: current_logo3_val = f"data:image/{uploaded_logo3.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo3.read()).decode("utf-8")

            if st.form_submit_button("💾 حفظ ترويسة وهوامش التقارير العامة", use_container_width=True):
                save_print_settings(
                    header_text_val, m_top, m_bot, m_right, m_left, line_spacing_val, 
                    current_logo1_val, current_logo2_val, current_logo3_val, 
                    current_set.get("bg_base64",""), current_set.get("frame_base64",""), 
                    current_set.get("default_cert_title",""), current_set.get("default_cert_notes",""), 
                    current_set.get("trainee_prefix",""), current_set.get("trainee_title",""), 
                    current_set.get("trainee_profession",""), current_set.get("professions_list", [])
                )
                st.success("✅ تم حفظ هوامش وترويسة التقارير العامة بنجاح!"); st.rerun()

    elif selected_menu == "🎨 إعدادات الشهادات المخصصة":
        st.subheader("🎨 صفحة إدارة وضبط الشهادات المستقلة")
        st.info("💡 هذه الصفحة مخصصة بالكامل لضبط تصاميم الشهادات، الألقاب، المسافات، الخلفيات، الشعارات، والإطارات بمعزل عن باقي التقارير.")
        
        current_set = get_print_settings()
        professions_options_list = current_set.get("professions_list", [
            "أخصائي تحاليل طبية", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني معمل", 
            "فني تمريض", "مسؤول معامل", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات)"
        ])

        with st.form(" dedicated_certificate_settings_form"):
            st.markdown("#### 🏷️ إعدادات الألقاب والمهنة في الشهادة:")
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                trainee_prefix_val = st.text_input("1. البادئة قبل الاسم (مثل: الزميل / الأستاذ):", value=current_set.get("trainee_prefix", ""))
            with col_p2:
                trainee_title_val = st.text_input("2. اللقب (يظهر أمام الاسم مباشرة):", value=current_set.get("trainee_title", "دكتور"))
            with col_p3:
                curr_prof = current_set.get("trainee_profession", "أخصائي تحاليل طبية")
                prof_idx = professions_options_list.index(curr_prof) if curr_prof in professions_options_list else 0
                trainee_profession_val = st.selectbox("3. اختيار المهنة / الوظيفة من القائمة:", professions_options_list, index=prof_idx)

            st.markdown("#### 📐 التحكم بالمسافات بين الأسطر وتخطيط الشهادة:")
            line_spacing_val = st.number_input("المسافة بين الأسطر داخل الشهادة:", min_value=0.8, max_value=3.0, value=float(current_set.get("line_spacing", 1.25)), step=0.05)

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

            st.markdown("#### 🖼️ إطار وخلفية الشهادات:")
            col_bg_up, col_frame_up = st.columns(2)
            with col_bg_up:
                uploaded_bg = st.file_uploader("رفع خلفية الشهادة (صورة):", type=["png", "jpg", "jpeg"], key="cert_bg")
                remove_bg = st.checkbox("حذف الخلفية الحالية", key="c_rem_bg")
            with col_frame_up:
                uploaded_frame = st.file_uploader("رفع إطار/هامش الشهادة الكبير:", type=["png", "jpg", "jpeg"], key="cert_frame")
                remove_frame = st.checkbox("حذف الإطار الحالي", key="c_rem_frame")

            current_logo1_val = current_set["logo_base64"]
            if remove_logo1: current_logo1_val = DEFAULT_LOGO
            elif uploaded_logo1 is not None: current_logo1_val = f"data:image/{uploaded_logo1.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo1.read()).decode("utf-8")
            
            current_logo2_val = current_set.get("logo2_base64", "")
            if remove_logo2: current_logo2_val = ""
            elif uploaded_logo2 is not None: current_logo2_val = f"data:image/{uploaded_logo2.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo2.read()).decode("utf-8")

            current_logo3_val = current_set.get("logo3_base64", "")
            if remove_logo3: current_logo3_val = ""
            elif uploaded_logo3 is not None: current_logo3_val = f"data:image/{uploaded_logo3.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo3.read()).decode("utf-8")

            current_bg_val = current_set.get("bg_base64", "")
            if remove_bg: current_bg_val = ""
            elif uploaded_bg is not None: current_bg_val = f"data:image/{uploaded_bg.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_bg.read()).decode("utf-8")

            current_frame_val = current_set.get("frame_base64", "")
            if remove_frame: current_frame_val = ""
            elif uploaded_frame is not None: current_frame_val = f"data:image/{uploaded_frame.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_frame.read()).decode("utf-8")

            if st.form_submit_button("💾 حفظ إعدادات الشهادة المخصصة", use_container_width=True):
                save_print_settings(
                    current_set["header_text"], current_set["margin_top"], current_set["margin_bottom"], 
                    current_set["margin_right"], current_set["margin_left"], line_spacing_val, 
                    current_logo1_val, current_logo2_val, current_logo3_val, current_bg_val, current_frame_val, 
                    current_set["default_cert_title"], current_set["default_cert_notes"], 
                    trainee_prefix_val, trainee_title_val, trainee_profession_val, professions_options_list
                )
                st.success("✅ تم تحديث وحفظ ضبط الشهادات المخصصة بنجاح!"); st.rerun()

    elif selected_menu == "🏥 الهيكل الإداري":
        st.subheader("🏥 إدارة الهيكل الإداري للمنشآت الصحية (مع إمكانية الإخفاء والإظهار)")
        tab_h1, tab_h2, tab_h3 = st.tabs(["✍️ إضافة يدوية", "📥 رفع ملفات", "📋 استعراض وإخفاء/إظهار/حذف"])
        
        with tab_h1:
            with st.form("manual_hierarchical_form"):
                m_auth = st.text_input("الهيئة:", value="")
                m_gov = st.text_input("المحافظة:", value="")
                m_admin = st.text_input("الإدارة الصحية:", value="")
                m_center = st.text_input("المركز:", value="")
                m_fac = st.text_input("اسم المنشأة:", value="")
                
                if st.form_submit_button("💾 حفظ", use_container_width=True):
                    if m_fac.strip():
                        with db() as c:
                            c.execute("INSERT INTO hierarchical_facilities(authority,governorate,administration,center,facility_name,created_at,hidden) VALUES(?,?,?,?,?,?,?)",
                                      (m_auth.strip(), m_gov.strip(), m_admin.strip(), m_center.strip(), m_fac.strip(), now(), 0))
                        reindex_hierarchical_facilities()
                        st.success("✅ تمت الإضافة بنجاح وإعادة الترتيب!"); st.rerun()
                    else:
                        st.warning("أدخل اسم المنشأة.")

        with tab_h2:
            up_file = st.file_uploader("اختر ملف إكسيل أو CSV:", type=["xlsx", "xls", "csv"], key="hier_file_upload_v1_0")
            if up_file is not None:
                try:
                    df_up = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
                    if st.button("🚀 دمج وتحديث البيانات", use_container_width=True):
                        added_cnt = 0
                        with db() as c:
                            for _, r in df_up.iterrows():
                                auth = str(r.get("authority", r.get("الهيئة", "مديرية الشئون الصحية"))).strip()
                                gov = str(r.get("governorate", r.get("المحافظة", "الشرقية"))).strip()
                                adm = str(r.get("administration", r.get("الإدارة", "الإدارة الصحية"))).strip()
                                cent = str(r.get("center", r.get("المركز", "أولاد صقر"))).strip()
                                fac = str(r.get("facility_name", r.get("المنشأة", "وحدة صحية"))).strip()
                                if fac:
                                    c.execute("INSERT INTO hierarchical_facilities(authority,governorate,administration,center,facility_name,created_at,hidden) VALUES(?,?,?,?,?,?,?)",
                                              (auth, gov, adm, cent, fac, now(), 0))
                                    added_cnt += 1
                        reindex_hierarchical_facilities()
                        st.success(f"🎉 تم إضافة ({added_cnt}) سجل وإعادة الترتيب بنجاح!"); st.balloons()
                except Exception as e:
                    st.error(f"خطأ: {e}")

        with tab_h3:
            hier_rows_all = get_hierarchical_data(include_hidden=True)
            if not hier_rows_all:
                st.info("لا توجد بيانات مسجلة.")
            else:
                facility_map = {f"ID ({row['id']}) - {row['authority']} / {row['governorate']} / {row['administration']} / {row['facility_name']} (حالة الإخفاء: {'مخفي 👁️️‍🗨️' if row['hidden']==1 else 'ظاهر ✅'})": row['id'] for row in hier_rows_all}
                with st.form("manage_single_hier_form"):
                    selected_item_manage = st.selectbox("اختر المنشأة لإدارتها:", list(facility_map.keys()))
                    target_id = facility_map[selected_item_manage]
                    
                    with db() as c:
                        curr_fac_rec = c.execute("SELECT hidden FROM hierarchical_facilities WHERE id=?", (target_id,)).fetchone()
                    is_currently_hidden = curr_fac_rec["hidden"] == 1 if curr_fac_rec else False
                    
                    c_hide_btn, c_show_btn, c_del_btn = st.columns(3)
                    with c_hide_btn:
                        hide_fac_submit = st.form_submit_button("👁️‍🗨️ إخفاء المنشأة من التقارير", use_container_width=True)
                    with c_show_btn:
                        show_fac_submit = st.form_submit_button("✅ إظهار المنشأة بالتقارير", use_container_width=True)
                    with c_del_btn:
                        single_del = st.form_submit_button("🗑 حذف نهائي", use_container_width=True)
                    
                    if hide_fac_submit:
                        with db() as c: c.execute("UPDATE hierarchical_facilities SET hidden=1 WHERE id=?", (target_id,))
                        st.success("✅ تم إخفاء المنشأة من جميع التقارير بنجاح!"); st.rerun()
                    if show_fac_submit:
                        with db() as c: c.execute("UPDATE hierarchical_facilities SET hidden=0 WHERE id=?", (target_id,))
                        st.success("✅ تم إظهار المنشأة في التقارير بنجاح!"); st.rerun()
                    if single_del:
                        with db() as c: c.execute("DELETE FROM hierarchical_facilities WHERE id=?", (target_id,))
                        reindex_hierarchical_facilities()
                        st.success("✅ تم الحذف وإعادة الترتيب التسلسلي للـ ID بنجاح!"); st.rerun()

                df_hier = pd.DataFrame(hier_rows_all)
                df_hier["hidden"] = df_hier["hidden"].apply(lambda x: "مخفي 👁‍🗨️" if x==1 else "ظاهر ✅")
                df_hier.columns = ["ID", "الهيئة", "المحافظة", "الإدارة", "المركز", "المنشأة", "تاريخ الإنشاء", "حالة الإخفاء"]
                st.dataframe(df_hier, use_container_width=True, hide_index=True)

    elif selected_menu == "🧑‍🔬 المتدربين والنماذج":
        st.subheader("🧑‍🔬 اعتماد المتدربين والنماذج (مع إمكانية الإخفاء والإظهار الفردي أو الجماعي)")
        with db() as c: all_tpls_map = {row["name"]: row["id"] for row in c.execute("SELECT id, name FROM exam_templates").fetchall()}
        tpl_names_list = list(all_tpls_map.keys()) if all_tpls_map else ["لا توجد نماذج اختبارات مسجلة"]

        with st.container(border=True):
            with st.form("bulk_assign_form"):
                bulk_tpl_name = st.selectbox("اختر نموذج الاختبار لتعميمه:", tpl_names_list)
                if st.form_submit_button("🚀 تعميم الاختبار واعتماد الجميع", use_container_width=True):
                    if all_tpls_map:
                        set_bulk_template_for_all(all_tpls_map[bulk_tpl_name])
                        st.success("✅ تم التعميم بنجاح!"); st.rerun()

        sub_tabs = st.tabs(["الطلبات المعلقة", "جميع المتدربين (إدارة وإخفاء/إظهار)", "🖨 طباعة النتائج والشهادات", "📝 طباعة نموذج امتحان الممتحن"])
        with sub_tabs[0]:
            df_pend = trainees_df("pending", include_hidden=False)
            if df_pend.empty: st.info("لا توجد طلبات معلقة.")
            else:
                for _, r in df_pend.iterrows():
                    with st.container(border=True):
                        st.write(f"**ID:** {r['id']} | **الاسم:** {r['name']} | **الجهة:** {r['facility']}")
                        with st.form(f"approve_form_{r['id']}"):
                            chosen_tpl_name = st.selectbox("نموذج الاختبار المخصص:", tpl_names_list)
                            c1, c2 = st.columns(2)
                            with c1: app_btn = st.form_submit_button("✅ اعتماد", use_container_width=True)
                            with c2: rej_btn = st.form_submit_button("❌ رفض", use_container_width=True)
                            if app_btn and all_tpls_map:
                                set_trainee_status_and_template(int(r['id']), "approved", all_tpls_map[chosen_tpl_name])
                                st.success("✅ تم الاعتماد!"); st.rerun()
                            if rej_btn:
                                set_trainee_status_and_template(int(r['id']), "rejected", r.get('assigned_template_id'))
                                st.warning("تم الرفض."); st.rerun()
        with sub_tabs[1]:
            df_all_tr_include_hidden = trainees_df(include_hidden=True)
            if df_all_tr_include_hidden.empty: st.info("لا توجد بيانات.")
            else:
                for _, tr_row in df_all_tr_include_hidden.iterrows():
                    is_hidden_tr = tr_row.get("hidden", 0) == 1
                    hidden_badge = " [مخفي 👁️‍🗨️]" if is_hidden_tr else " [ظاهر ✅]"
                    with st.container(border=True):
                        st.write(f"**ID:** {tr_row['id']} | **المتدرب:** {tr_row['name']}{hidden_badge} | **الحالة:** `{STATUS_AR.get(tr_row['status'], tr_row['status'])}`")
                        with st.form(f"update_tr_tpl_{tr_row['id']}"):
                            curr_id = tr_row['assigned_template_id']
                            curr_name = [k for k, v in all_tpls_map.items() if v == curr_id]
                            def_name = curr_name[0] if curr_name else (tpl_names_list[0] if tpl_names_list else "")
                            def_idx = tpl_names_list.index(def_name) if def_name in tpl_names_list else 0
                            new_chosen_tpl = st.selectbox("تعديل النموذج:", tpl_names_list, index=def_idx, key=f"sel_tr_{tr_row['id']}")
                            
                            c_upd, c_hide, c_show, c_del = st.columns(4)
                            with c_upd: upd_btn = st.form_submit_button("💾 تحديث", use_container_width=True)
                            with c_hide: hide_btn = st.form_submit_button("👁‍🗨️ إخفاء", use_container_width=True)
                            with c_show: show_btn = st.form_submit_button("✅ إظهار", use_container_width=True)
                            with c_del: del_btn = st.form_submit_button("🗑 حذف", use_container_width=True)
                            
                            if upd_btn and all_tpls_map:
                                set_trainee_status_and_template(int(tr_row['id']), tr_row['status'], all_tpls_map[new_chosen_tpl])
                                st.success("✅ تم التحديث!"); st.rerun()
                            if hide_btn:
                                with db() as c: c.execute("UPDATE trainees SET hidden=1 WHERE id=?", (int(tr_row['id']),))
                                st.success("✅ تم إخفاء المتدرب بنجاح من جميع التقارير!"); st.rerun()
                            if show_btn:
                                with db() as c: c.execute("UPDATE trainees SET hidden=0 WHERE id=?", (int(tr_row['id']),))
                                st.success("✅ تم إظهار المتدرب في التقارير بنجاح!"); st.rerun()
                            if del_btn:
                                with db() as c:
                                    c.execute("PRAGMA foreign_keys=OFF;")
                                    c.execute("DELETE FROM trainees WHERE id=?", (int(tr_row['id']),))
                                    c.execute("DELETE FROM exam_sessions WHERE trainee_id=?", (int(tr_row['id']),))
                                    c.execute("PRAGMA foreign_keys=ON;")
                                reindex_trainees()
                                st.success("✅ تم الحذف وإعادة ترتيب أرقام الـ ID بنجاح!"); st.rerun()
        with sub_tabs[2]:
            st.markdown("#### 🖨 طباعة شهادات ونتائج الامتحانات على مقاس A4 (تتجاهل المخفيين تلقائياً)")
            with db() as c:
                sessions_list = c.execute("""SELECT s.id, t.name trainee_name, t.facility, s.score, s.max_score, s.percent, s.passed 
                                             FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.status='submitted' AND t.hidden=0 ORDER BY s.id DESC""").fetchall()
            
            if not sessions_list:
                st.info("لا توجد اختبارات مسجلة أو مكتملة حتى الآن للمتدربين الظاهرين.")
            else:
                print_mode = st.radio("اختر وضع الطباعة:", ["طباعة فردية (لمتدرب محدد)", "طباعة جماعية (لكل النتائج المكتملة)"], horizontal=True)
                if "فردية" in print_mode:
                    sess_choices = {f"مجلد رقم ({s['id']}) - المتدرب: {s['trainee_name']} - الجهة: {s['facility']} (النتيجة: {s['percent']}%)": s['id'] for s in sessions_list}
                    sel_sess_label = st.selectbox("اختر المتدرب للطباعة الفردية:", list(sess_choices.keys()))
                    chosen_sid = sess_choices[sel_sess_label]
                    
                    curr_set = get_print_settings()
                    cert_html_single = generate_customizable_certificate_html(chosen_sid, curr_set.get("default_cert_title"), curr_set.get("default_cert_notes"))
                    render_print_button_only(cert_html_single, f"شهادة متدرب رقم {chosen_sid}")
                else:
                    st.markdown("##### 📚 طباعة وتصدير كافة الشهادات دفعة واحدة:")
                    combined_all_html = ""
                    for s in sessions_list:
                        combined_all_html += generate_customizable_certificate_html(s['id']) + "<div style='page-break-after: always;'></div>"
                    render_print_button_only(combined_all_html, "طباعة جماعية لكل الشهادات")

        with sub_tabs[3]:
            st.markdown("#### 📝 طباعة نموذج امتحان الإجابة والأسئلة لممتحن أدى الامتحان على البرنامج:")
            with db() as c:
                completed_sessions = c.execute("""
                    SELECT s.id, t.name trainee_name, t.facility, s.submitted_at, s.started_at, e.name template_name 
                    FROM exam_sessions s 
                    JOIN trainees t ON t.id=s.trainee_id 
                    LEFT JOIN exam_templates e ON e.id=s.template_id 
                    WHERE s.status='submitted' AND t.hidden=0 ORDER BY s.id DESC
                """).fetchall()

            if not completed_sessions:
                st.info("لا توجد اختبارات مكتملة مسجلة للممتحنين الظاهرين حتى الآن.")
            else:
                exam_records_map = {f"المتدرب: {r['trainee_name']} | الجهة: {r['facility']} | الاختبار: {r['template_name'] or 'موافق'} | التاريخ: {r['submitted_at'] or r['started_at']} (ID: {r['id']})": r['id'] for r in completed_sessions}
                sel_exam_rec_label = st.selectbox("اختر الممتحن وتاريخ الامتحان:", list(exam_records_map.keys()))
                chosen_exam_session_id = exam_records_map[sel_exam_rec_label]

                trainee_exam_sheet_html = generate_trainee_exam_sheet_html(chosen_exam_session_id)
                st.markdown("<br>", unsafe_allow_html=True)
                render_print_button_only(trainee_exam_sheet_html, f"نموذج إجابة الامتحان للممتحد رقم {chosen_exam_session_id}")

    elif selected_menu == "🧠 بنك الأسئلة":
        st.subheader("🧠 بنك الأسئلة الشامل")
        tab_ex_1, tab_ex_2 = st.tabs(["📥 استيراد", "📤 تصدير"])
        with tab_ex_1:
            uploaded_excel = st.file_uploader("اختر ملف إكسيل:", type=["xlsx", "xls", "csv"], key="excel_uploader_v1_0")
            if uploaded_excel is not None:
                try:
                    df_import = pd.read_csv(uploaded_excel) if uploaded_excel.name.endswith('.csv') else pd.read_excel(uploaded_excel)
                    if st.button("🚀 تأكيد ودمج", use_container_width=True):
                        imported_count = 0
                        with db() as c:
                            for _, row in df_import.iterrows():
                                diff, cat, q_text = str(row.get("difficulty", "متوسط")), str(row.get("category", "الفحوص المعملية")), str(row.get("question", ""))
                                raw_opts = row.get("options_json", '["خيار 1", "خيار 2", "خيار 3", "خيار 4"]')
                                try: opts_list = json.loads(raw_opts) if isinstance(raw_opts, str) and raw_opts.startswith("[") else [o.strip() for o in str(raw_opts).split(",") if o.strip()]
                                except: opts_list = ["نعم", "لا"]
                                try: ans_idx = int(row.get("answer", 0))
                                except: ans_idx = 0
                                if ans_idx < 0 or ans_idx >= len(opts_list): ans_idx = 0
                                if q_text.strip() and opts_list:
                                    fp = hashlib.sha256((q_text + "|" + "|".join(str(o) for o in opts_list)).encode("utf-8")).hexdigest()
                                    try:
                                        c.execute("INSERT INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                                  (diff, cat, q_text, json.dumps(opts_list, ensure_ascii=False), ans_idx, 1, fp, now()))
                                        imported_count += 1
                                    except: continue
                        st.success(f"🎉 تم إضافة ({imported_count}) سؤالاً!"); st.balloons()
                except Exception as e: st.error(f"خطأ: {e}")
        with tab_ex_2:
            with db() as c: df_bank = pd.read_sql_query("SELECT id, difficulty, category, question, options_json, answer FROM questions ORDER BY id ASC", c)
            if df_bank.empty: st.info("فارغ.")
            else:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer: df_bank.to_excel(writer, index=False, sheet_name='QuestionBank')
                st.download_button("📥 تحميل الإكسيل (.xlsx)", data=output.getvalue(), file_name="question_bank.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                st.dataframe(df_bank, use_container_width=True, hide_index=True)

    elif selected_menu == "⚙ إدارة الأسئلة":
        st.subheader("⚙️ إدارة الأسئلة والفردية")
        sub_img_tabs = st.tabs(["➕ إضافة", "✏️ تعديل", "🗑 حذف"])
        categories_list_opts = [
            "الاستراتيجية العامة ومكافحة البلهارسيا", "البلهارسيا", "علاج البلهارسيا", "الفاشيولا", "علاج الفاشيولا",
            "الهتروفيس", "التينيا", "هيمنولبس نانا", "الإسكارس", "الأنكلستوما", "الأكسيورس", "تركيورس تركيورا",
            "Strongyloides stercoralis", "Entamoeba histolytica", "Giardia lamblia", "الفحوص المعملية",
            "فحص البول", "فحص البراز", "طرق فحص البراز", "الترسيب", "التعويم", "اللطخة المباشرة",
            "التصفية الغشائية", "Kato-Katz", "تحضير العينات", "أسئلة الصور والأشكال"
        ]
        with sub_img_tabs[0]:
            if st.session_state.add_success_msg: st.success(st.session_state.add_success_msg); st.session_state.add_success_msg = ""
            with st.form(key=f"add_q_form_{st.session_state.form_key}"):
                selected_cat = st.selectbox("القسم:", categories_list_opts)
                c_text = st.text_area("نص السؤال:", value="")
                c_diff = st.selectbox("الصعوبة:", ["سهل", "متوسط", "صعب"])
                uploaded_img = st.file_uploader("رفع صورة (اختياري):", type=["png", "jpg", "jpeg"])
                opt1, opt2 = st.text_input("خيار 1:", value=""), st.text_input("خيار 2:", value="")
                opt3, opt4 = st.text_input("خيار 3:", value=""), st.text_input("خيار 4:", value="")
                correct_ans_text = st.text_input("الإجابة الصحيحة:", value="")
                if st.form_submit_button("حفظ", use_container_width=True):
                    if c_text and correct_ans_text:
                        img_uri_final = f"data:image/{uploaded_img.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_img.read()).decode("utf-8") if uploaded_img else ""
                        full_q_str = f"IMAGE:{img_uri_final}\n\n{c_text}" if img_uri_final else c_text
                        opts_list = [o for o in [opt1, opt2, opt3, opt4] if o.strip() != ""]
                        if correct_ans_text not in opts_list: opts_list.append(correct_ans_text)
                        ans_idx = opts_list.index(correct_ans_text)
                        fp = hashlib.sha256((full_q_str + "|" + "|".join(opts_list)).encode("utf-8")).hexdigest()
                        with db() as c:
                            c.execute("INSERT INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                      (c_diff, selected_cat, full_q_str, json.dumps(opts_list, ensure_ascii=False), ans_idx, 1, fp, now()))
                        st.session_state.add_success_msg = "✅ تم الإضافة!"
                        st.session_state.form_key += 1
                        st.rerun()
        with sub_img_tabs[1]:
            with db() as c: all_questions = c.execute("SELECT id, question, category FROM questions ORDER BY id ASC").fetchall()
            if all_questions:
                q_options_map = {f"سؤال ({q['id']}) - {q['question'][:40]}...": q['id'] for q in all_questions}
                selected_q_label = st.selectbox("اختر السؤال:", list(q_options_map.keys()))
                selected_q_id = q_options_map[selected_q_label]
                with db() as c: q_data = c.execute("SELECT * FROM questions WHERE id=?", (selected_q_id,)).fetchone()
                if q_data:
                    current_opts = json.loads(q_data["options_json"])
                    while len(current_opts) < 4: current_opts.append("")
                    with st.form(f"edit_q_{selected_q_id}"):
                        e_cat = st.selectbox("القسم:", categories_list_opts, index=categories_list_opts.index(q_data["category"]) if q_data["category"] in categories_list_opts else 0)
                        e_diff = st.selectbox("الصعوبة:", ["سهل", "متوسط", "صعب"], index=["سهل", "متوسط", "صعب"].index(q_data["difficulty"]) if q_data["difficulty"] in ["سهل", "متوسط", "صعب"] else 0)
                        raw_q_db = q_data["question"]
                        actual_text_editable = raw_q_db.replace("IMAGE:", "").split("\n\n")[-1] if "IMAGE:" in raw_q_db else raw_q_db
                        e_text = st.text_area("نص السؤال:", value=actual_text_editable)
                        e_o1, e_o2 = st.text_input("خيار 1:", value=str(current_opts[0])), st.text_input("خيار 2:", value=str(current_opts[1]))
                        e_o3, e_o4 = st.text_input("خيار 3:", value=str(current_opts[2])), st.text_input("خيار 4:", value=str(current_opts[3]))
                        e_correct = st.text_input("الإجابة الصحيحة:", value=current_opts[q_data["answer"]] if 0 <= q_data["answer"] < len(current_opts) else "")
                        if st.form_submit_button("💾 حفظ", use_container_width=True):
                            updated_opts = [o for o in [e_o1, e_o2, e_o3, e_o4] if o.strip() != ""]
                            if e_correct not in updated_opts: updated_opts.append(e_correct)
                            new_ans_idx = updated_opts.index(e_correct)
                            prefix_img = raw_q_db.split("\n\n")[0] + "\n\n" if "IMAGE:" in raw_q_db else ""
                            final_str = prefix_img + e_text
                            new_fp = hashlib.sha256((final_str + "|" + "|".join(updated_opts)).encode("utf-8")).hexdigest()
                            with db() as c:
                                c.execute("UPDATE questions SET difficulty=?, category=?, question=?, options_json=?, answer=?, fingerprint=? WHERE id=?",
                                          (e_diff, e_cat, final_str, json.dumps(updated_opts, ensure_ascii=False), new_ans_idx, new_fp, selected_q_id))
                            st.success("✅ تم التعديل!"); st.rerun()
        with sub_img_tabs[2]:
            with db() as c: all_questions_del = c.execute("SELECT id, question FROM questions ORDER BY id ASC").fetchall()
            if all_questions_del:
                q_del_map = {f"سؤال رقم {q['id']} - {q['question'][:40]}": q['id'] for q in all_questions_del}
                selected_del_label = st.selectbox("اختر السؤال للحذف:", list(q_del_map.keys()))
                if st.button("🗑 حذف", use_container_width=True):
                    with db() as c: c.execute("DELETE FROM questions WHERE id=?", (q_del_map[selected_del_label],))
                    st.success("✅ تم الحذف!"); st.rerun()

    elif selected_menu == "🧩 مواعيد الاختبارات و طباعة النماذج":
        st.subheader("🧩 مواعيد الاختبارات ونماذج الأسئلة (نظام 12 ساعة - مقاس A4)")
        sub_tpl_mode = st.radio("القسم:", ["📋 عرض النماذج وطباعة الأسئلة", "➕ إنشاء نموذج جديد", "⚙ تعديل موعد", "🗑 حذف نموذج"], horizontal=True)
        
        if sub_tpl_mode == "📋 عرض النماذج وطباعة الأسئلة":
            with db() as c: tpls = c.execute("SELECT * FROM exam_templates ORDER BY id ASC").fetchall()
            if tpls:
                for t in tpls:
                    t_dict = dict(t)
                    num_q_display = "مفتوح" if int(t_dict.get('num_questions', 999999)) >= 999900 else t_dict.get('num_questions')
                    s_t = t_dict.get('start_time') or "غير محدد"
                    e_t = t_dict.get('end_time') or "غير محدد"
                    
                    def format_12h(iso_str):
                        if not iso_str or "T" not in iso_str: return iso_str
                        try:
                            dt = datetime.fromisoformat(iso_str)
                            return dt.strftime("%Y-%m-%d %I:%M %p").replace("AM", "صباحاً").replace("PM", "مساءً")
                        except:
                            return iso_str

                    with st.container(border=True):
                        st.markdown(f"#### 🏷 نموذج ({t_dict.get('id')}): {t_dict.get('name')}")
                        st.write(f"🔹 البدء: `{format_12h(s_t)}` | 🔸 النهاية: `{format_12h(e_t)}` | 📝 الأسئلة: {num_q_display}")
                        
                        exam_template_html_out = generate_exam_template_print_html(t_dict.get('id'))
                        render_print_button_only(exam_template_html_out, f"نموذج امتحان رقم {t_dict.get('id')}")

        elif sub_tpl_mode == "➕ إنشاء نموذج جديد":
            categories_pool_opts = [
                "الاستراتيجية العامة ومكافحة البلهارسيا", "البلهارسيا", "علاج البلهارسيا", "الفاشيولا", "علاج الفاشيولا",
                "الهتروفيس", "التينيا", "هيمنولبس نانا", "الإسكارس", "الأنكلستوما", "الأكسيورس", "تركيورس تركيورا",
                "Strongyloides stercoralis", "Entamoeba histolytica", "Giardia lamblia", "الفحوص المعملية",
                "فحص البول", "فحص البراز", "طرق فحص البراز", "الترسيب", "التعويم", "اللطخة المباشرة",
                "التصفية الغشائية", "Kato-Katz", "تحضير العينات", "أسئلة الصور والأشكال"
            ]

            with st.form("create_template_schedule_form"):
                new_tpl_name = st.text_input("اسم النموذج:", value="")
                is_open_questions = st.checkbox("عدد أسئلة مفتوح (كامل البنك)", value=True)
                new_tpl_num_q = st.number_input("عدد الأسئلة:", min_value=1, max_value=5000, value=50)
                new_tpl_duration = st.number_input("المدة (بالدقائق):", min_value=5, max_value=300, value=60)
                new_tpl_pass = st.slider("نسبة النجاح %:", min_value=30.0, max_value=95.0, value=60.0)
                
                st.markdown("---")
                st.markdown("#### ⏰ تحديد توقيت البدء والنهاية (نظام 12 ساعة):")
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    start_d = st.date_input("تاريخ البدء:", date.today())
                    st.markdown("##### وقت البدء:")
                    sh_col1, sh_col2, sh_col3 = st.columns(3)
                    with sh_col1: start_h = st.number_input("الساعة (1-12):", min_value=1, max_value=12, value=9, key="sh_in")
                    with sh_col2: start_m = st.number_input("الدقيقة (0-59):", min_value=0, max_value=59, value=0, key="sm_in")
                    with sh_col3: start_ampm = st.selectbox("الفترة:", ["صباحاً", "مساءً"], key="sap_in")

                with col_d2:
                    end_d = st.date_input("تاريخ النهاية:", date.today() + timedelta(days=1))
                    st.markdown("##### وقت النهاية:")
                    eh_col1, eh_col2, eh_col3 = st.columns(3)
                    with eh_col1: end_h = st.number_input("الساعة (1-12):", min_value=1, max_value=12, value=5, key="eh_in")
                    with eh_col2: end_m = st.number_input("الدقيقة (0-59):", min_value=0, max_value=59, value=0, key="em_in")
                    with eh_col3: end_ampm = st.selectbox("الفترة:", ["صباحاً", "مساءً"], index=1, key="eap_in")

                new_tpl_cats = st.multiselect("الأقسام:", categories_pool_opts)
                if st.form_submit_button("💾 حفظ النموذج والمواعيد", use_container_width=True):
                    if new_tpl_name.strip():
                        def convert_to_24h(h, m, ampm):
                            h_24 = h % 12
                            if "مساءً" in ampm:
                                h_24 += 12
                            return h_24, m

                        s_h24, s_m24 = convert_to_24h(start_h, start_m, start_ampm)
                        e_h24, e_m24 = convert_to_24h(end_h, end_m, end_ampm)

                        start_dt_str = datetime.combine(start_d, datetime.min.time().replace(hour=s_h24, minute=s_m24)).isoformat(timespec="seconds")
                        end_dt_str = datetime.combine(end_d, datetime.min.time().replace(hour=e_h24, minute=e_m24)).isoformat(timespec="seconds")
                        
                        final_num_q = 999999 if is_open_questions else int(new_tpl_num_q)
                        with db() as c:
                            c.execute("INSERT INTO exam_templates(name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, start_time, end_time, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                                      (new_tpl_name.strip(), "اختبار مخصص للمالك", final_num_q, int(new_tpl_duration), float(new_tpl_pass), json.dumps(new_tpl_cats, ensure_ascii=False), start_dt_str, end_dt_str, now()))
                        st.success("✅ تم إنشاء وتحديد موعد النموذج بنجاح!"); st.rerun()

        elif sub_tpl_mode == "⚙ تعديل موعد":
            with db() as c: tpls_mod = c.execute("SELECT id, name FROM exam_templates ORDER BY id ASC").fetchall()
            if tpls_mod:
                tpl_mod_map = {f"نموذج ({t['id']}) - {t['name']}": t['id'] for t in tpls_mod}
                with st.form("update_schedule_form"):
                    sel_mod_label = st.selectbox("اختر النموذج:", list(tpl_mod_map.keys()))
                    chosen_id = tpl_mod_map[sel_mod_label]
                    
                    st.markdown("#### ⏰ تعديل التوقيت (نظام 12 ساعة):")
                    col_u1, col_u2 = st.columns(2)
                    with col_u1:
                        new_sd = st.date_input("البدء الجديد:", date.today())
                        uh1, uh2, uh3 = st.columns(3)
                        with uh1: ns_h = st.number_input("الساعة:", 1, 12, 9, key="ns_h")
                        with uh2: ns_m = st.number_input("الدقيقة:", 0, 59, 0, key="ns_m")
                        with uh3: ns_ampm = st.selectbox("الفترة:", ["صباحاً", "مساءً"], key="ns_ampm")
                    with col_u2:
                        new_ed = st.date_input("النهاية الجديدة:", date.today() + timedelta(days=1))
                        ne1, ne2, ne3 = st.columns(3)
                        with ne1: ne_h = st.number_input("الساعة:", 1, 12, 5, key="ne_h")
                        with ne2: ne_m = st.number_input("الدقيقة:", 0, 59, 0, key="ne_m")
                        with ne3: ne_ampm = st.selectbox("الفترة:", ["صباحاً", "مساءً"], index=1, key="ne_ampm")
                    
                    if st.form_submit_button("💾 تحديث الموعد", use_container_width=True):
                        def convert_to_24h(h, m, ampm):
                            h_24 = h % 12
                            if "مساءً" in ampm: h_24 += 12
                            return h_24, m

                        s_h24, s_m24 = convert_to_24h(ns_h, ns_m, ns_ampm)
                        e_h24, e_m24 = convert_to_24h(ne_h, ne_m, ne_ampm)

                        new_s_str = datetime.combine(new_sd, datetime.min.time().replace(hour=s_h24, minute=s_m24)).isoformat(timespec="seconds")
                        new_e_str = datetime.combine(new_ed, datetime.min.time().replace(hour=e_h24, minute=e_m24)).isoformat(timespec="seconds")
                        
                        with db() as c: c.execute("UPDATE exam_templates SET start_time=?, end_time=? WHERE id=?", (new_s_str, new_e_str, chosen_id))
                        st.success("✅ تم تحديث موعد الاختبار بنجاح!"); st.rerun()

        else:
            with db() as c: tpls_del = c.execute("SELECT id, name FROM exam_templates ORDER BY id ASC").fetchall()
            if tpls_del:
                tpl_map = {f"نموذج رقم {t['id']} - {t['name']}": t['id'] for t in tpls_del}
                with st.form("delete_template_form"):
                    selected_tpl_label = st.selectbox("اختر النموذج للحذف:", list(tpl_map.keys()))
                    if st.form_submit_button("🗑 حذف", use_container_width=True):
                        with db() as c:
                            c.execute("PRAGMA foreign_keys=OFF;")
                            c.execute("DELETE FROM exam_templates WHERE id=?", (tpl_map[selected_tpl_label],))
                            c.execute("PRAGMA foreign_keys=ON;")
                        st.success("✅ تم الحذف!"); st.rerun()

    elif selected_menu == "✍ تسجيل نتيجة يدوي":
        st.subheader("✍ تسجيل نتيجة يدوي (مع اختيار الأسئلة الخاطئة لضمان الدقة)")
        hier_data = get_hierarchical_data(include_hidden=False)
        default_fac_str = hier_data[0]["facility_name"] if hier_data else ""
        
        with db() as c: all_tpls_records = c.execute("SELECT id, name FROM exam_templates").fetchall()
        manual_tpl_choices = {row["name"]: row["id"] for row in all_tpls_records} if all_tpls_records else {}
        manual_tpl_keys = list(manual_tpl_choices.keys()) if manual_tpl_choices else ["لا توجد نماذج اختبارات مسجلة"]

        with st.form("manual_score_form_enhanced"):
            m_trainee_name = st.text_input("اسم المتدرب:", value="")
            m_facility_name = st.text_input("جهة العمل:", value=default_fac_str)
            selected_manual_tpl_name = st.selectbox("اختر قالب/نموذج الاختبار:", manual_tpl_keys)
            
            c1, c2 = st.columns(2)
            with c1: manual_score = st.number_input("الدرجة الحاصل عليها:", min_value=0, max_value=9999, value=45)
            with c2: manual_max = st.number_input("الدرجة الكلية:", min_value=1, max_value=9999, value=50)
            
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
                    st.warning("⚠️️ يرجى إنشاء نماذج اختبارات أولاً.")
                else:
                    with db() as c:
                        tpl_id_val = manual_tpl_choices.get(selected_manual_tpl_name)
                        cur_tr = c.execute("INSERT INTO trainees(facility,name,phone,status,assigned_template_id,created_at,updated_at,hidden) VALUES(?,?,?,?,?,?,?,?)",
                                           (m_facility_name, normalize_text(m_trainee_name), "0000000000", "completed", tpl_id_val, now(), now(), 0))
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
        st.subheader("📊 تقارير وأداء المعامل وتحليل النتائج (تستبعد المخفيين تلقائياً)")
        
        rep_tab1, rep_tab2, rep_tab3, rep_tab4 = st.tabs([
            "👤 تقرير فردي (لمتدرب مع فلترة ومقارنة فترات)", 
            "🏢 تقرير جماعي (لمنشأة مع فلترة ومقارنة فترات)", 
            "📋 تقرير النتائج الشامل", 
            "📈 تقرير أداء الجهات"
        ])
        
        with rep_tab1:
            st.markdown("#### 👤 التقرير الفردي للمتدرب (مع تحديد المدى الزمني ومقارنة فترتين):")
            with db() as c:
                tr_list_rep = c.execute("SELECT id, name, facility FROM trainees WHERE hidden=0 ORDER BY id DESC").fetchall()
            
            if not tr_list_rep:
                st.info("لا توجد بيانات متدربين ظاهرة متاحة.")
            else:
                tr_choices_rep = {f"متدرب: {t['name']} - الجهة: {t['facility']} (ID: {t['id']})": t['id'] for t in tr_list_rep}
                sel_tr_rep_label = st.selectbox("اختر المتدرب لاستعراض تقريره الفردي:", list(tr_choices_rep.keys()), key="sel_ind_tr_rep")
                chosen_tr_id = tr_choices_rep[sel_tr_rep_label]
                
                st.markdown("---")
                col_d_f1, col_d_f2 = st.columns(2)
                with col_d_f1:
                    st.markdown("##### 📅 الفترة الأولى (أو التقرير الأساسي):")
                    d_start_1 = st.date_input("من تاريخ (الأولى):", date.today() - timedelta(days=30), key="ds1")
                    d_end_1 = st.date_input("إلى تاريخ (الأولى):", date.today(), key="de1")
                with col_d_f2:
                    st.markdown("##### 📅 الفترة الثانية (للمقارنة):")
                    d_start_2 = st.date_input("من تاريخ (الثانية):", date.today() - timedelta(days=60), key="ds2")
                    d_end_2 = st.date_input("إلى تاريخ (الثانية):", date.today() - timedelta(days=31), key="de2")

                with db() as c:
                    ind_tr_data = c.execute("SELECT * FROM trainees WHERE id=? AND hidden=0", (chosen_tr_id,)).fetchone()
                    s_q1 = c.execute("""SELECT s.*, e.name as tpl_name FROM exam_sessions s LEFT JOIN exam_templates e ON e.id=s.template_id 
                                        WHERE s.trainee_id=? AND date(s.submitted_at) >= date(?) AND date(s.submitted_at) <= date(?) ORDER BY s.id DESC LIMIT 1""", 
                                     (chosen_tr_id, d_start_1.isoformat(), d_end_1.isoformat())).fetchone()
                    s_q2 = c.execute("""SELECT s.*, e.name as tpl_name FROM exam_sessions s LEFT JOIN exam_templates e ON e.id=s.template_id 
                                        WHERE s.trainee_id=? AND date(s.submitted_at) >= date(?) AND date(s.submitted_at) <= date(?) ORDER BY s.id DESC LIMIT 1""", 
                                     (chosen_tr_id, d_start_2.isoformat(), d_end_2.isoformat())).fetchone()
                
                if ind_tr_data:
                    p1_score = f"{s_q1['score']}/{s_q1['max_score']} ({s_q1['percent']:.1f}%)" if s_q1 and s_q1['score'] is not None else "لا توجد بيانات"
                    p1_status = "اجتزت بنجاح" if s_q1 and s_q1["passed"] == 1 else ("لم تجتز" if s_q1 else "-")
                    
                    p2_score = f"{s_q2['score']}/{s_q2['max_score']} ({s_q2['percent']:.1f}%)" if s_q2 and s_q2['score'] is not None else "لا توجد بيانات"
                    p2_status = "اجتزت بنجاح" if s_q2 and s_q2["passed"] == 1 else ("لم تجتز" if s_q2 else "-")

                    individual_report_html = f"""
                    <div style="font-family: 'Cairo', sans-serif; direction: rtl; padding: 10px;">
                        <h3 style="color: #047857; text-align: center;">تقرير أداء ونتيجة متدرب (مع مقارنة الفترات)</h3>
                        <hr style="border: 1px solid #059669;">
                        <p><b>اسم المتدرب:</b> {esc(ind_tr_data['name'])} | <b>جهة العمل:</b> {esc(ind_tr_data['facility'])}</p>
                        <table style="width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 10pt;">
                            <tr>
                                <th style="border: 1px solid #cbd5e1; padding: 8px; background-color: #059669; color: white;">فترة المقارنة</th>
                                <th style="border: 1px solid #cbd5e1; padding: 8px; background-color: #059669; color: white;">النتيجة والنسبة</th>
                                <th style="border: 1px solid #cbd5e1; padding: 8px; background-color: #059669; color: white;">حالة الاجتياز</th>
                            </tr>
                            <tr>
                                <td style="border: 1px solid #cbd5e1; padding: 8px; font-weight: bold;">الفترة الأولى ({d_start_1} إلى {d_end_1})</td>
                                <td style="border: 1px solid #cbd5e1; padding: 8px;">{p1_score}</td>
                                <td style="border: 1px solid #cbd5e1; padding: 8px; color: {'green' if p1_status=='اجتزت بنجاح' else 'red'};">{p1_status}</td>
                            </tr>
                            <tr>
                                <td style="border: 1px solid #cbd5e1; padding: 8px; font-weight: bold;">الفترة الثانية ({d_start_2} إلى {d_end_2})</td>
                                <td style="border: 1px solid #cbd5e1; padding: 8px;">{p2_score}</td>
                                <td style="border: 1px solid #cbd5e1; padding: 8px; color: {'green' if p2_status=='اجتزت بنجاح' else 'red'};">{p2_status}</td>
                            </tr>
                        </table>
                    </div>
                    """
                    st.markdown(individual_report_html, unsafe_allow_html=True)
                    full_ind_html = generate_general_report_html(f"مقارنة أداء المتدرب: {ind_tr_data['name']}", individual_report_html)
                    render_print_button_only(full_ind_html, f"مقارنة فترات المتدرب {chosen_tr_id}")

        with rep_tab2:
            st.markdown("#### 🏢 التقرير الجماعي للمنشأة (مع تحديد المدى الزمني ومقارنة أدائها بين فترتين):")
            with db() as c:
                facs_list_rep = [row[0] for row in c.execute("SELECT DISTINCT facility FROM trainees WHERE facility IS NOT NULL AND facility != '' AND hidden=0").fetchall()]
            
            if not facs_list_rep:
                st.info("لا توجد جهات أو منشآت ظاهرة مسجلة.")
            else:
                sel_fac_rep = st.selectbox("اختر الجهة / المنشأة لاستعراض تقريرها الجماعي:", facs_list_rep, key="sel_group_fac_rep")
                
                col_gf1, col_gf2 = st.columns(2)
                with col_gf1:
                    st.markdown("##### 📅 الفترة الأولى:")
                    gf_start_1 = st.date_input("من تاريخ (الأولى):", date.today() - timedelta(days=30), key="gfs1")
                    gf_end_1 = st.date_input("إلى تاريخ (الأولى):", date.today(), key="gfe1")
                with col_gf2:
                    st.markdown("##### 📅 الفترة الثانية (للمقارنة):")
                    gf_start_2 = st.date_input("من تاريخ (الثانية):", date.today() - timedelta(days=60), key="gfs2")
                    gf_end_2 = st.date_input("إلى تاريخ (الثانية):", date.today() - timedelta(days=31), key="gfe2")

                with db() as c:
                    p1_stat = c.execute("""SELECT COUNT(DISTINCT t.id) as total_tr, COALESCE(AVG(s.percent), 0) as avg_pct,
                                           SUM(CASE WHEN s.passed=1 THEN 1 ELSE 0 END) as passed_cnt
                                           FROM trainees t JOIN exam_sessions s ON s.trainee_id=t.id AND s.status='submitted'
                                           WHERE t.facility=? AND t.hidden=0 AND date(s.submitted_at) >= date(?) AND date(s.submitted_at) <= date(?)""",
                                        (sel_fac_rep, gf_start_1.isoformat(), gf_end_1.isoformat())).fetchone()
                    
                    p2_stat = c.execute("""SELECT COUNT(DISTINCT t.id) as total_tr, COALESCE(AVG(s.percent), 0) as avg_pct,
                                           SUM(CASE WHEN s.passed=1 THEN 1 ELSE 0 END) as passed_cnt
                                           FROM trainees t JOIN exam_sessions s ON s.trainee_id=t.id AND s.status='submitted'
                                           WHERE t.facility=? AND t.hidden=0 AND date(s.submitted_at) >= date(?) AND date(s.submitted_at) <= date(?)""",
                                        (sel_fac_rep, gf_start_2.isoformat(), gf_end_2.isoformat())).fetchone()

                group_compare_html = f"""
                <div style="font-family: 'Cairo', sans-serif; direction: rtl; padding: 10px;">
                    <h3 style="color: #047857; text-align: center;">تقرير مقارنة أداء منشأة بين فترتين: {esc(sel_fac_rep)}</h3>
                    <hr style="border: 1px solid #059669;">
                    <table style="width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 10pt;">
                        <tr>
                            <th style="border: 1px solid #cbd5e1; padding: 8px; background-color: #059669; color: white;">فترة المقارنة</th>
                            <th style="border: 1px solid #cbd5e1; padding: 8px; background-color: #059669; color: white;">إجمالي المختبرين</th>
                            <th style="border: 1px solid #cbd5e1; padding: 8px; background-color: #059669; color: white;">المجتازين</th>
                            <th style="border: 1px solid #cbd5e1; padding: 8px; background-color: #059669; color: white;">متوسط النسبة المئوية %</th>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #cbd5e1; padding: 8px; font-weight: bold;">الفترة الأولى ({gf_start_1} إلى {gf_end_1})</td>
                            <td style="border: 1px solid #cbd5e1; padding: 8px;">{p1_stat['total_tr'] if p1_stat else 0}</td>
                            <td style="border: 1px solid #cbd5e1; padding: 8px;">{p1_stat['passed_cnt'] if p1_stat else 0}</td>
                            <td style="border: 1px solid #cbd5e1; padding: 8px;">{p1_stat['avg_pct']:.1f}%</td>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #cbd5e1; padding: 8px; font-weight: bold;">الفترة الثانية ({gf_start_2} إلى {gf_end_2})</td>
                            <td style="border: 1px solid #cbd5e1; padding: 8px;">{p2_stat['total_tr'] if p2_stat else 0}</td>
                            <td style="border: 1px solid #cbd5e1; padding: 8px;">{p2_stat['passed_cnt'] if p2_stat else 0}</td>
                            <td style="border: 1px solid #cbd5e1; padding: 8px;">{p2_stat['avg_pct']:.1f}%</td>
                        </tr>
                    </table>
                </div>
                """
                st.markdown(group_compare_html, unsafe_allow_html=True)
                full_group_comp_html = generate_general_report_html(f"مقارنة أداء منشأة: {sel_fac_rep}", group_compare_html)
                render_print_button_only(full_group_comp_html, f"مقارنة فترات منشأة {sel_fac_rep}")

        with rep_tab3:
            with db() as c:
                df_rep = pd.read_sql_query("""
                    SELECT t.id AS 'مسلسل', t.name AS 'اسم المتدرب', t.facility AS 'جهة العمل', 
                           COALESCE(s.percent, 0) AS 'النسبة المئوية %', 
                           CASE WHEN s.passed=1 THEN 'اجتزت بنجاح' ELSE 'لم تجتز' END AS 'الحالة',
                           s.certificate_id AS 'رقم الشهادة'
                    FROM trainees t LEFT JOIN exam_sessions s ON s.trainee_id=t.id AND s.status='submitted'
                    WHERE t.hidden=0
                    ORDER BY t.id DESC
                """, c)
            
            if df_rep.empty:
                st.info("لا توجد بيانات متدربين ظاهرة لعرضها في التقرير.")
            else:
                st.dataframe(df_rep, use_container_width=True, hide_index=True)
                table_html = df_rep.to_html(index=False, border=0, classes='table')
                full_rep_html = generate_general_report_html("تقرير نتائج المتدربين الشامل", f"<div>{table_html}</div>")
                render_print_button_only(full_rep_html, "تقرير النتائج الشامل")

        with rep_tab4:
            with db() as c:
                df_fac = pd.read_sql_query("""
                    SELECT t.facility AS 'جهة العمل', 
                           COUNT(t.id) AS 'إجمالي المتدربين',
                           SUM(CASE WHEN s.passed=1 THEN 1 ELSE 0 END) AS 'المجتازين',
                           COALESCE(AVG(s.percent), 0) AS 'متوسط النسبة %'
                    FROM trainees t LEFT JOIN exam_sessions s ON s.trainee_id=t.id AND s.status='submitted'
                    WHERE t.hidden=0
                    GROUP BY t.facility
                    ORDER BY COUNT(t.id) DESC
                """, c)
            
            if df_fac.empty:
                st.info("لا توجد بيانات جهات أو منشآت لتحليلها.")
            else:
                st.dataframe(df_fac, use_container_width=True, hide_index=True)
                table_fac_html = df_fac.to_html(index=False, border=0, classes='table')
                full_fac_html = generate_general_report_html("تقرير أداء المنشآت والجهات الصحية", f"<div>{table_fac_html}</div>")
                render_print_button_only(full_fac_html, "تقرير أداء الجهات")

    elif selected_menu == "📈 خطط العمل":
        st.subheader("📈 خطط العمل التدريبية ومعالجة نقاط الضعف (تستبعد المخفيين تلقائياً)")
        
        plan_tabs = st.tabs(["➕ إنشاء وتحديث خطة عمل ذكية", "📋 استعراض وإدارة خطط العمل المسجلة"])
        
        with plan_tabs[0]:
            with db() as c:
                all_tr_list = c.execute("SELECT id, name, facility FROM trainees WHERE hidden=0 ORDER BY id ASC").fetchall()
                all_fac_list = [row[0] for row in c.execute("SELECT DISTINCT facility FROM trainees WHERE facility IS NOT NULL AND facility != '' AND hidden=0").fetchall()]
            
            with st.form("create_action_plan_form"):
                target_category = st.radio("نطاق الخطة:", ["فرد (متدرب محدد)", "جماعة (منشأة صحية بالكامل)"], horizontal=True)
                
                auto_weakness_text = ""
                auto_steps_text = ""
                
                if "فرد" in target_category:
                    if not all_tr_list:
                        st.warning("⚠️ لا توجد بيانات متدربين ظاهرة مسجلة بعد.")
                        target_name = ""
                    else:
                        tr_choices = {f"{t['name']} - الجهة: {t['facility']} (ID: {t['id']})": t for t in all_tr_list}
                        sel_tr_label = st.selectbox("اختر المتدرب لاستخراج نقاط ضعفه تلقائياً:", list(tr_choices.keys()))
                        chosen_tr_obj = tr_choices[sel_tr_label]
                        target_name = chosen_tr_obj['name']
                        
                        with db() as c:
                            incorrect_qs = c.execute("""
                                SELECT q.category, q.question, eq.selected_option, q.answer 
                                FROM exam_questions eq 
                                JOIN questions q ON q.id=eq.question_id 
                                JOIN exam_sessions s ON s.id=eq.session_id 
                                WHERE s.trainee_id=? AND eq.is_correct=0
                            """, (chosen_tr_obj['id'],)).fetchall()
                            
                        if incorrect_qs:
                            failed_cats = list(set([r['category'] for r in incorrect_qs]))
                            auto_weakness_text = f"تم رصد إخفاقات للمتدرب {target_name} في الأقسام التالية بناءً على نتائج الاختبارات الأخيرة:\n- " + "\n- ".join(failed_cats)
                            auto_steps_text = f"1. عقد جلسة تدريب مركزة ومكثفة للأقسام التالية: {', '.join(failed_cats)}.\n2. إعادة الاختبار العملي والنظري بعد استكمال البرنامج العلاجي.\n3. متابعة أداء المتدرب الميداني داخل المنشأة."
                        else:
                            auto_weakness_text = "لم يتم رصد إخفاقات واضحة أو اجتاز المتدرب كافة الأسئلة بنجاح."
                            auto_steps_text = "1. استمرار المتابعة الدورية وتحفيز المتدرب.\n2. إدراج المتدرب في دورات تنشيطية متقدمة."
                else:
                    if not all_fac_list:
                        st.warning("⚠ لا توجد جهات صحية ظاهرة مسجلة بعد.")
                        target_name = ""
                    else:
                        target_name = st.selectbox("اختر الجهة / المنشأة المستهدفة:", all_fac_list)
                        
                        with db() as c:
                            fac_incorrect = c.execute("""
                                SELECT q.category 
                                FROM exam_questions eq 
                                JOIN questions q ON q.id=eq.question_id 
                                JOIN exam_sessions s ON s.id=eq.session_id 
                                JOIN trainees t ON t.id=s.trainee_id 
                                WHERE t.facility=? AND t.hidden=0 AND eq.is_correct=0
                            """, (target_name,)).fetchall()
                            
                        if fac_incorrect:
                            fac_cats = list(set([r['category'] for r in fac_incorrect]))
                            auto_weakness_text = f"تم رصد نقاط ضعف متكررة لكوادر منشأة ({target_name}) في الأقسام التالية:\n- " + "\n- ".join(fac_cats)
                            auto_steps_text = f"1. تنفيذ برنامج تدريبي جماعي للعاملين بالمنشأة يركز على: {', '.join(fac_cats)}.\n2. توفير الأدلة الإرشادية والمواد التعليمية داخل معمل المنشأة.\n3. تقييم العاملين بعد أسبوعين من تاريخ الخطة."
                        else:
                            auto_weakness_text = "مستوى العاملين بالمنشأة مستقر وتجتاز الاختبارات بكفاءة."
                            auto_steps_text = "1. الحفاظ على مستوى الأداء المتميز.\n2. إجراء تقييم فصلي دوري."

                st.markdown("---")
                st.markdown("#### 🎯 نقاط الضعف (تم استنتاجها وتحليلها تلقائياً):")
                weak_areas = st.text_area("أبرز نقاط الضعف والأقسام المرصودة:", value=auto_weakness_text)
                
                st.markdown("#### 🛠️ الخطوات الإجرائية والبرنامج التدريبي المقترح:")
                action_steps = st.text_area("الخطوات العلاجية:", value=auto_steps_text)

                st.markdown("---")
                st.markdown("#### 📅 تحديد الإطار الزمني للخطة (بالشهر والسنة):")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    year_val = st.selectbox("السنة:", ["2026", "2027", "2028"], index=0)
                with col_d2:
                    month_val = st.selectbox("الشهر:", ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"], index=8)

                if st.form_submit_button("💾 حفظ وإنشاء خطة العمل الذكية", use_container_width=True):
                    if not target_name.strip() or not weak_areas.strip():
                        st.warning("⚠️ يرجى استكمال البيانات.")
                    else:
                        with db() as c:
                            c.execute("""INSERT INTO action_plans(target_type, target_name, weakness_areas, action_steps, time_frame_type, specific_date, specific_month, specific_year, created_at)
                                         VALUES(?,?,?,?,?,?,?,?,?)""",
                                      (target_category, target_name, weak_areas.strip(), action_steps.strip(), "تحديد بشهر وسنة فقط", "1", month_val, year_val, now()))
                        st.success("✅ تم حفظ خطة العمل بناءً على التحليل التلقائي بنجاح!"); st.rerun()

        with plan_tabs[1]:
            with db() as c:
                plans_list = c.execute("SELECT * FROM action_plans ORDER BY id DESC").fetchall()
            
            if not plans_list:
                st.info("لا توجد خطط عمل مسجلة حتى الآن.")
            else:
                plan_map = {f"خطة رقم ({p['id']}) - [{p['target_type']}] المستهدف: {p['target_name']} (شهر {p['specific_month']} {p['specific_year']})": p['id'] for p in plans_list}
                sel_plan_label = st.selectbox("اختر خطة العمل للمعاينة والطباعة الذكية:", list(plan_map.keys()))
                chosen_plan_id = plan_map[sel_plan_label]
                
                with db() as c:
                    p_data = dict(c.execute("SELECT * FROM action_plans WHERE id=?", (chosen_plan_id,)).fetchone())

                plan_detail_html = f"""
                <div style="font-family: 'Cairo', sans-serif; direction: rtl; padding: 5px; page-break-inside: avoid; break-inside: avoid;">
                    <h3 style="color: #047857; text-align: center; font-size: 14pt; margin: 5px 0;">خطة عمل لعلاج نقاط الضعف وتحسين الأداء المعملي</h3>
                    <hr style="border: 1px solid #059669; margin: 8px 0;">
                    <p style="font-size: 9.5pt; margin: 4px 0;"><b>نوع النطاق:</b> {esc(p_data['target_type'])} | <b>المستهدف:</b> {esc(p_data['target_name'])} | <b>الإطار الزمني:</b> شهر {p_data['specific_month']} لسنة {p_data['specific_year']}</p>
                    
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
                
                full_plan_print_html = generate_action_plan_report_html(f"خطة عمل - {p_data['target_name']}", plan_detail_html)
                render_print_button_only(full_plan_print_html, f"خطة عمل رقم {chosen_plan_id}")

                if st.button("🗑️️ حذف خطة العمل المحددة", use_container_width=True):
                    with db() as c:
                        c.execute("DELETE FROM action_plans WHERE id=?", (chosen_plan_id,))
                    st.success("✅ تم حذف خطة العمل بنجاح!"); st.rerun()

    elif selected_menu == "💾 النسخ الاحتياطي":
        st.subheader("💾 النسخ الاحتياطي واستعادة قاعدة البيانات والدمج")
        
        if st.button("🗑️ تفرغ جميع بيانات النظام (تصفير قاعدة البيانات)", use_container_width=True):
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
            with open(DB_PATH, "rb") as f: db_bytes = f.read()
            st.download_button("📥 تحميل النسخة (.db)", data=db_bytes, file_name="endemic_labs_exam_v1_0.db", mime="application/octet-stream", use_container_width=True)
        with col_bk2:
            uploaded_db_file = st.file_uploader("رفع ملف قاعدة بيانات (.db):", type=["db"], key="restore_db_uploader")
            if uploaded_db_file is not None:
                c_btn_res, c_btn_merge = st.columns(2)
                with c_btn_res:
                    if st.button("⚠️ استبدال القاعدة الحالية بالكامل", use_container_width=True):
                        try:
                            with open(DB_PATH, "wb") as f_out: f_out.write(uploaded_db_file.getbuffer())
                            st.success("✅ تمت الاستعادة بنجاح!"); time.sleep(1); st.rerun()
                        except Exception as e: st.error(f"خطأ: {e}")
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
                                    exists = dest_conn.execute("SELECT 1 FROM hierarchical_facilities WHERE authority=? AND governorate=? AND administration=? AND center=? AND facility_name=?",
                                                               (h["authority"], h["governorate"], h["administration"], h["center"], h["facility_name"])).fetchone()
                                    if not exists:
                                        dest_conn.execute("INSERT INTO hierarchical_facilities(authority, governorate, administration, center, facility_name, created_at, hidden) VALUES(?,?,?,?,?,?,?)",
                                                          (h["authority"], h["governorate"], h["administration"], h["center"], h["facility_name"], h["created_at"], h.get("hidden", 0)))
                                        merged_h_count += 1

                            src_conn.close()
                            if os.path.exists(temp_db_path):
                                os.remove(temp_db_path)
                            
                            reindex_hierarchical_facilities()
                            st.success(f"🎉 تم الدمج بنجاح! (تم إضافة {merged_q_count} سؤالاً، و {merged_h_count} منشأة جديدة دون فقدان البيانات السابقة).")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"خطأ أثناء الدمج: {e}")

    elif selected_menu == "👥 إدارة المستخدمين":
        st.subheader("👥 إدارة المستخدمين وصلاحياتهم وتعديل بيانات الاعتماد")
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
                            except sqlite3.IntegrityError: st.error("مستخدم مسبقاً.")
                    else: st.warning("أدخل البيانات.")
                    
        with tab_u2:
            with db() as c: all_users = c.execute("SELECT id, username, role, permissions_json FROM users WHERE role != 'admin'").fetchall()
            if not all_users: st.info("لا توجد مستخدمين.")
            else:
                user_map = {f"مستخدم: {u['username']}": u for u in all_users}
                sel_user_label = st.selectbox("اختر المستخدم:", list(user_map.keys()))
                target_user = user_map[sel_user_label]
                try: curr_user_perms = json.loads(target_user["permissions_json"]) if target_user["permissions_json"] else []
                except: curr_user_perms = []

                with st.form(f"edit_user_perms_{target_user['id']}"):
                    edit_checkboxes = {}
                    for mod_key, mod_desc in ALL_MENU_MODULES.items():
                        is_checked = mod_key in curr_user_perms
                        edit_checkboxes[mod_key] = st.checkbox(f"{mod_key}", value=is_checked, key=f"mod_chk_{target_user['id']}_{mod_key}")
                    c_save, c_del = st.columns(2)
                    with c_save: save_btn = st.form_submit_button("💾 حفظ", use_container_width=True)
                    with c_del: del_btn = st.form_submit_button("🗑 حذف", use_container_width=True)
                    if save_btn:
                        new_assigned = [k for k, v in edit_checkboxes.items() if v]
                        with db() as c: c.execute("UPDATE users SET permissions_json=? WHERE id=?", (json.dumps(new_assigned, ensure_ascii=False), target_user["id"]))
                        st.success("✅ تم التحديث!"); st.rerun()
                    if del_btn:
                        with db() as c: c.execute("DELETE FROM users WHERE id=?", (target_user["id"],))
                        st.success("✅ تم الحذف!"); st.rerun()
                        
        with tab_u3:
            st.markdown("#### 🔑 تعديل اسم المستخدم وكلمة المرور للمالك أو المستخدمين")
            st.info("📌 **شروط التعديل:** يجب إدخال كلمة المرور الحالية بشكل صحيح (أو كلمة مرور المالك الأساسية في حال تعديل حساب آخر) لضمان الأمان.")
            
            with db() as c: all_sys_users = c.execute("SELECT id, username, role FROM users").fetchall()
            sys_user_choices = {f"{u['username']} ({ROLES.get(u['role'], u['role'])})": u for u in all_sys_users}
            
            with st.form("edit_credentials_form"):
                sel_target_user_label = st.selectbox("اختر الحساب المراد تعديله:", list(sys_user_choices.keys()))
                chosen_target = sys_user_choices[sel_target_user_label]
                
                new_username_input = st.text_input("اسم المستخدم الجديد:", value=chosen_target["username"])
                current_password_input = st.text_input("كلمة المرور الحالية (للتأكيد):", type="password", value="")
                new_password_input = st.text_input("كلمة المرور الجديدة (اتركها فارغة إن لم ترد تغييرها):", type="password", value="")
                
                if st.form_submit_button("🔒 تحديث بيانات الدخول", use_container_width=True):
                    if not current_password_input.strip():
                        st.warning("⚠️ يرجى إدخال كلمة المرور الحالية للتأكيد.")
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
        with db() as c: df_audit = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100", c)
        st.dataframe(df_audit, use_container_width=True, hide_index=True)

def trainee_portal():
    with db() as c: 
        tr = c.execute("SELECT * FROM trainees WHERE id=? AND hidden=0", (st.session_state.trainee_id,)).fetchone()
    if not tr: 
        st.session_state.trainee_id = None
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
            st.session_state.trainee_id = None
            st.rerun()
        return

    assigned_tpl_id = tr["assigned_template_id"]
    with db() as c: 
        matching_template = c.execute("SELECT * FROM exam_templates WHERE id=?", (assigned_tpl_id,)).fetchone() if assigned_tpl_id else None

    is_exam_open = False
    if matching_template:
        t_dict = dict(matching_template)
        start_t = t_dict.get("start_time")
        end_t = t_dict.get("end_time")
        if start_t and end_t:
            try:
                dt_now = datetime.now()
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
        start_t = t_dict.get("start_time")
        end_t = t_dict.get("end_time")
        
        def format_12h(iso_str):
            if not iso_str or "T" not in iso_str: return iso_str
            try:
                dt = datetime.fromisoformat(iso_str)
                return dt.strftime("%Y-%m-%d %I:%M %p").replace("AM", "صباحاً").replace("PM", "مساءً")
            except:
                return iso_str

        st.markdown(f'<div class="card"><h3>مرحباً بك، {esc(tr["name"])}</h3><p>الاختبار المخصص لك: <b>{esc(tpl_name_str)}</b></p></div>', unsafe_allow_html=True)
        
        with st.container(border=True):
            format_s = format_12h(start_t)
            format_e = format_12h(end_t)
            col_s1, col_s2 = st.columns(2)
            with col_s1: st.markdown(f"🟢 **وقت البدء:**\n`{format_s}`")
            with col_s2: st.markdown(f"🔴 **وقت النهاية:**\n`{format_e}`")

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
            st.session_state.trainee_id = None
            st.rerun()

def exam_interface(session_id):
    header()
    with db() as c:
        session = c.execute("SELECT s.*, t.facility FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.id=? AND t.hidden=0", (session_id,)).fetchone()
        rows = c.execute("""SELECT eq.*, q.question, q.options_json FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=? ORDER BY eq.position""", (session_id,)).fetchall()

    answered = 0
    for row in rows:
        try: opts = json.loads(row["options_json"])
        except: opts = ["نعم", "لا"]
        order = json.loads(row["option_order_json"])
        disp_opts = [opts[i] for i in order]
        curr_idx = None
        if row["selected_option"] is not None:
            try: curr_idx = disp_opts.index(opts[row["selected_option"]])
            except: pass
        st.markdown(f'<div class="question"><b>س ({row["position"]+1}):</b> {clean_question_text(row["question"])}</div>', unsafe_allow_html=True)
        choice = st.radio("اختر الإجابة:", disp_opts, index=curr_idx, key=f"q_{row['id']}", label_visibility="collapsed")
        if choice:
            sel = order[disp_opts.index(choice)]
            with db() as c: c.execute("UPDATE exam_questions SET selected_option=?, is_correct=CASE WHEN ?=(SELECT answer FROM questions WHERE id=question_id) THEN 1 ELSE 0 END WHERE id=?", (sel, sel, row["id"]))
            answered += 1
    st.progress(answered / len(rows) if rows else 0)
    if st.button("تسليم الاختبار نهائياً", use_container_width=True):
        res = submit_session(session_id)
        if res: st.session_state.last_result_id = session_id
        st.session_state.exam_session_id = None
        st.success("🎉 تم تسليم الاختبار بنجاح!")
        st.rerun()

# ============================================================
# 7) التوجيه الأساسي الشامل للشاشات
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
        if st.button("العودة للرئيسية"): st.session_state.trainee_id = None; st.session_state.last_result_id = None; st.rerun()
    else:
        trainee_portal()
elif not st.session_state.logged_in:
    login_portal()
else:
    admin_dashboard()
