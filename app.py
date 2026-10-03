import os, io, re, ast, json, sqlite3, hashlib, secrets, random, time, html
from datetime import datetime, timedelta, date
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
    "🖨 الطباعة والترويسة": "إعدادات الطباعة والترويسة وخلفيات الشهادات",
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
            c.execute("INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, logo_base64, logo2_base64, logo3_base64, bg_base64, frame_base64, default_cert_title, default_cert_notes, trainee_prefix, trainee_title, trainee_profession, professions_list_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (default_header, "2mm", "2mm", "2mm", "2mm", DEFAULT_LOGO, "", "", "", "", "شهادة اجتياز اختبار معتمدة", "تقرير أداء المعامل والإشراف الفني المعتمد", "", "دكتور", "أخصائي تحاليل طبية", json.dumps(default_professions, ensure_ascii=False)))

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
            return res
        return {
            "header_text": "جمهورية مصر العربية<br>وزارة الصحة والسكان<br>مديرية الشئون الصحية بالشرقية<br>الإدارة الصحية بأولاد صقر",
            "margin_top": "2mm", "margin_bottom": "2mm", "margin_right": "2mm", "margin_left": "2mm",
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

def save_print_settings(h_text, m_top, m_bot, m_right, m_left, logo_data, logo2_data, logo3_data, bg_data, frame_data, def_title, def_notes, trainee_prefix, trainee_title, trainee_profession, professions_list):
    with db() as c:
        c.execute("DELETE FROM print_settings")
        c.execute("INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, logo_base64, logo2_base64, logo3_base64, bg_base64, frame_base64, default_cert_title, default_cert_notes, trainee_prefix, trainee_title, trainee_profession, professions_list_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (h_text, m_top, m_bot, m_right, m_left, logo_data, logo2_data, logo3_data, bg_data, frame_data, def_title, def_notes, trainee_prefix, trainee_title, trainee_profession, json.dumps(professions_list, ensure_ascii=False)))

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
    
    logos_list_html = f'<img src="{logo1}" style="width: 25px; height: 25px; object-fit: contain;" alt="Logo 1">'
    if logo2:
        logos_list_html += f'<img src="{logo2}" style="width: 25px; height: 25px; object-fit: contain;" alt="Logo 2">'
        
    return f"""
    <div style="display: flex; gap: 2px; align-items: center;">
        {logos_list_html}
    </div>
    """

def render_top_left_logo_html():
    sett = get_print_settings()
    logo3 = sett.get("logo3_base64", "")
    if logo3:
        return f"""
        <div style="position: absolute; top: 1.5mm; left: 3mm; text-align: left; z-index: 2;">
            <img src="{logo3}" style="width: 25px; height: 25px; object-fit: contain;" alt="Logo 3">
        </div>
        """
    return ""

def generate_qr_code_base64(data_text):
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return "data:image/png;base64," + __import__("base64").b64encode(buffered.getvalue()).decode("utf-8")

def generate_exam_template_print_html(template_id):
    sett = get_print_settings()
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
                img_tag_html = f'<div style="margin: 1px 0; text-align: center;"><img src="{img_uri}" style="max-height: 30px; max-width: 100%; object-fit: contain; border-radius: 2px; border: 1px solid #cbd5e1;"></div>'
        else:
            q_text_clean = raw_q_text

        opts_html = "".join([f'<div style="padding: 0.3px 1.5px; margin: 0.3px 0; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 1px; font-size: 6pt; line-height: 1.0;">🔲 {esc(opt)}</div>' for opt in opts])
        
        q_html_content += f"""
        <div style="margin-bottom: 1.5px; padding: 1.5px 2px; background: #ffffff; border: 1px solid #059669; border-radius: 1px; page-break-inside: avoid; break-inside: avoid;">
            <div style="font-weight: bold; color: #065f46; margin-bottom: 0.5px; font-size: 6.5pt; line-height: 1.05;">({idx}) {esc(q_text_clean)}</div>
            {img_tag_html}
            <div style="margin-top: 0.5px; padding-right: 1px;">{opts_html}</div>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 auto; margin: 1.5mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0; padding: 1mm; direction: rtl; -webkit-print-color-adjust: exact; }}
            .report-wrapper {{ max-width: 210mm; margin: auto; position: relative; }}
            .report-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #059669; padding-bottom: 1.5mm; margin-bottom: 1.5mm; }}
            .header-right {{ font-size: 7pt; font-weight: bold; color: #065f46; line-height: 1.05; }}
            h2 {{ text-align: center; color: #047857; font-size: 9pt; margin: 1px 0; }}
            .tpl-info {{ background: #f0fdf4; border: 1px dashed #059669; padding: 1.5px 3px; border-radius: 2px; margin-bottom: 2mm; font-size: 6.5pt; font-weight: bold; color: #065f46; text-align: center; }}
            .questions-grid {{
                column-count: 3;
                column-gap: 1.5mm;
                column-fill: auto;
            }}
            .footer {{ margin-top: 2mm; display: flex; justify-content: space-between; font-size: 6.5pt; font-weight: bold; border-top: 1px dashed #059669; padding-top: 1.5mm; page-break-inside: avoid; break-inside: avoid; }}
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

def generate_general_report_html(title, content_html, target_pages=1):
    sett = get_print_settings()
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 auto; margin: 2mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0; padding: 2mm; direction: rtl; -webkit-print-color-adjust: exact; }}
            .report-wrapper {{ max-width: 210mm; margin: auto; position: relative; }}
            .report-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1.5px solid #059669; padding-bottom: 2mm; margin-bottom: 3mm; }}
            .header-right {{ font-size: 8pt; font-weight: bold; color: #065f46; line-height: 1.1; }}
            h2 {{ text-align: center; color: #047857; font-size: 11pt; margin: 3px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 3mm; font-size: 7.5pt; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 2px 4px; text-align: center; line-height: 1.1; }}
            th {{ background-color: #059669; color: white; font-weight: bold; }}
            tr:nth-child(even) {{ background-color: #f0fdf4; }}
            .footer {{ margin-top: 4mm; display: flex; justify-content: space-between; font-size: 8pt; font-weight: bold; border-top: 1px dashed #059669; padding-top: 2mm; page-break-inside: avoid; break-inside: avoid; }}
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
            <div style="text-align: left; font-size: 7pt; color: #6b7280; margin-bottom: 2mm;">تاريخ الإصدار: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</div>
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
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 auto; margin: 10mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0; padding: 6mm; direction: rtl; -webkit-print-color-adjust: exact; }}
            .report-wrapper {{ max-width: 210mm; margin: auto; position: relative; }}
            .report-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #059669; padding-bottom: 4mm; margin-bottom: 6mm; }}
            .header-right {{ font-size: 10pt; font-weight: bold; color: #065f46; line-height: 1.3; }}
            h2 {{ text-align: center; color: #047857; font-size: 14pt; margin: 10px 0; }}
            .footer {{ margin-top: 25mm; display: flex; justify-content: space-between; font-size: 9.5pt; font-weight: bold; border-top: 1px dashed #059669; padding-top: 8mm; page-break-inside: avoid; break-inside: avoid; }}
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
            <div style="text-align: left; font-size: 8.5pt; color: #6b7280; margin-bottom: 6mm;">تاريخ الإصدار: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</div>
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

def generate_customizable_certificate_html(sid, custom_title=None, custom_notes=None):
    sett = get_print_settings()
    title_val = custom_title if custom_title is not None else sett.get("default_cert_title", "شهادة اجتياز اختبار معتمدة")
    notes_val = custom_notes if custom_notes is not None else sett.get("default_cert_notes", "تقرير أداء المعامل والإشراف الفني المعتمد")
    prefix_val = sett.get("trainee_prefix", "").strip()
    title_role_val = sett.get("trainee_title", "").strip()
    profession_val = sett.get("trainee_profession", "").strip()

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
    frame_style = f"background: url('{frame_data}') no-repeat center center; background-size: 100% 100%;" if frame_data else "border: none;"

    prefix_str = f"{prefix_val} " if prefix_val else ""
    title_role_str = f"{title_role_val} " if title_role_val else ""
    profession_str = f" - {profession_val}" if profession_val else ""
    full_line_text = f"{prefix_str}{title_role_str}{r['trainee_name']}{profession_str}"
    line_html = f"<div style='font-size: 12pt; color: #065f46; font-weight: 900; margin: 1px 0;'>{esc(full_line_text)}</div>"

    qr_data_str = f"{r['certificate_id']}"
    qr_base64 = generate_qr_code_base64(qr_data_str)

    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 portrait; margin: 1.5mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #fdfbf7; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; direction: rtl; -webkit-print-color-adjust: exact; }}
            .cert-wrapper {{ 
                width: 98%; max-width: 200mm; min-height: 250mm; max-height: 292mm;
                {frame_style} {bg_style}
                display: flex; flex-direction: column; justify-content: space-between; align-items: center; 
                padding: 2mm 4mm; box-sizing: border-box; position: relative; margin: auto;
                box-shadow: 0 1px 4px rgba(0,0,0,0.06); page-break-inside: avoid; break-inside: avoid;
            }}
            .header-top {{ position: absolute; top: 2mm; left: 4mm; text-align: left; z-index: 2; }}
            .header-right {{ position: absolute; top: 2mm; right: 4mm; text-align: right; font-size: 7pt; font-weight: bold; color: #065f46; line-height: 1.05; z-index: 2; }}
            .cert-body {{ text-align: center; margin-top: 2mm; width: 100%; z-index: 2; }}
            h2 {{ color: #047857; font-size: 10.5pt; margin-bottom: 1px; }}
            p {{ font-size: 7.5pt; line-height: 1.1; color: #1f2937; margin: 1px 0; }}
            .notes-box {{ background: rgba(240, 253, 244, 0.9); border: 1px dashed #059669; padding: 1.5px 2mm; margin: 1px auto; width: 85%; border-radius: 3px; font-weight: bold; color: #065f46; font-size: 7pt; }}
            .footer-bottom {{ width: 100%; display: flex; justify-content: space-between; align-items: center; font-size: 7pt; font-weight: bold; text-align: center; border-top: 1px dashed #059669; padding-top: 1mm; margin-top: 1mm; z-index: 2; }}
            .cert-watermark {{ font-size: 5.5pt; color: #065f46; font-weight: bold; margin-top: 0.5px; z-index: 2; }}
        </style>
    </head>
    <body>
        <div class="cert-wrapper">
            <div class="header-right">{formatted_header}</div>
            <div class="header-top">{render_logos_html()}</div>
            {render_top_left_logo_html()}
            <div class="cert-body">
                <h2>{esc(title_val)}</h2>
                <hr style="width: 25%; border: 1px solid #059669; margin: 1px auto 2px auto;">
                {line_html}
                <p style="margin-top: 1px;">
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
                    <img src="{qr_base64}" style="width: 28px; height: 28px; display: block; margin: auto;" alt="QR Code">
                    <div style="font-size: 4pt; color: #065f46; margin-top: 0.5px;">مسح للتحقق</div>
                </div>
            </div>
            <div class="cert-watermark">Developed by Dr/Ahmed.S.Hegazy</div>
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
                var pageRule = '@page { size: A4 """ + orient_css + """; margin: 1.5mm; @bottom-right { content: counter(page); }; }';
                
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
    search_cert_code = st.text_input("أدخل رقم الشهادة أو كود التحقق (مثل: ELX-000001):", value="")
    if search_cert_code.strip():
        with db() as c:
            r = c.execute("SELECT s.*, t.name trainee_name, t.facility, e.name template_name FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.certificate_id LIKE ? AND t.hidden=0", (f"%{search_cert_code.strip().upper()}%",)).fetchone()
        if r:
            st.success(f"✅ الشهادة صحيحة ومعتمدة للمتدرب: {esc(r['trainee_name'])} - الجهة: {esc(r['facility'])}")
        else:
            st.warning("⚠️ لم يتم العثور على شهادة بهذا الكود.")
    if st.button("العودة"):
        st.session_state.show_verification_portal = False
        st.rerun()

def login_portal():
    header()
    col1, col2 = st.columns([2, 1])
    with col1: st.markdown("#### بوابة اختبارات العاملين بمعامل المتوطنة.")
    with col2:
        if st.button("🔍 التحقق من شهادة (QR)", use_container_width=True):
            st.session_state.show_verification_portal = True
            st.rerun()

    hier_data = get_hierarchical_data(include_hidden=False)
    with st.form("trainee_request_hierarchical"):
        if hier_data:
            sel_auth = st.selectbox("الهيئة:", ["-- اختر الهيئة --"] + sorted(list(set(i["authority"] for i in hier_data))))
            sel_gov = st.selectbox("المحافظة:", ["-- اختر المحافظة --"] + sorted(list(set(i["governorate"] for i in hier_data))))
            sel_admin = st.selectbox("الإدارة الصحية:", ["-- اختر الإدارة الصحية --"] + sorted(list(set(i["administration"] for i in hier_data))))
            sel_center = st.selectbox("المركز:", ["-- اختر المركز --"] + sorted(list(set(i["center"] for i in hier_data))))
            sel_fac = st.selectbox("اسم المنشأة:", ["-- اختر المنشأة --"] + sorted(list(set(i["facility_name"] for i in hier_data))))
            facility_final_str = f"{sel_auth} - {sel_gov} - {sel_admin} - {sel_center} - {sel_fac}" if all(x != "-- اختر الهيئة --" and x != "-- اختر المحافظة --" and x != "-- اختر الإدارة الصحية --" and x != "-- اختر المركز --" and x != "-- اختر المنشأة --" for x in [sel_auth, sel_gov, sel_admin, sel_center, sel_fac]) else ""
        else:
            facility_final_str = ""

        name = st.text_input("الاسم الرباعي:")
        phone = st.text_input("رقم الهاتف:")
        with db() as c: all_tpls_opts = {row["name"]: row["id"] for row in c.execute("SELECT id, name FROM exam_templates").fetchall()}
        selected_req_tpl_name = st.selectbox("اختر نموذج الاختبار:", ["-- اختر --"] + list(all_tpls_opts.keys()))

        if st.form_submit_button("إرسال الطلب والدخول", use_container_width=True):
            if facility_final_str and selected_req_tpl_name != "-- اختر --" and name.strip():
                assigned_tpl_id = all_tpls_opts.get(selected_req_tpl_name)
                existing = trainee_by_credentials(name, facility_final_str)
                if existing:
                    st.session_state.trainee_id = existing["id"]
                    st.rerun()
                else:
                    tid = create_trainee(facility_final_str, name, phone, assigned_tpl_id)
                    st.session_state.trainee_id = tid
                    st.rerun()

    with st.expander("🔐 تسجيل دخول الإدارة"):
        with st.form("admin_login_form_hidden"):
            u = st.text_input("اسم المستخدم")
            p = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("دخول", use_container_width=True):
                user = login_user(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.role = user["role"]
                    st.session_state.permissions = json.loads(user["permissions_json"]) if user["permissions_json"] else list(ALL_MENU_MODULES.keys())
                    st.rerun()

def admin_dashboard():
    header()
    c_info, c_btn = st.columns([4, 1])
    with c_info: st.write(f"**المستخدم:** {st.session_state.username} | **الصلاحية:** {ROLES.get(st.session_state.role, '')}")
    with c_btn:
        if st.button("تسجيل الخروج", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    available_menus = [m for m in ALL_MENU_MODULES.keys() if m in st.session_state.permissions or st.session_state.role == "admin"]
    cols_per_row = 3
    for i in range(0, len(available_menus), cols_per_row):
        row_cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(available_menus):
                m_key = available_menus[i + j]
                if row_cols[j].button(f"📍 {m_key}" if st.session_state.active_admin_tab == m_key else m_key, use_container_width=True, key=f"btn_{i+j}"):
                    st.session_state.active_admin_tab = m_key
                    st.rerun()

    selected_menu = st.session_state.active_admin_tab
    st.markdown("---")

    if selected_menu == "📊 لوحة التحكم":
        st.subheader("📊 لوحة المؤشرات العامة")
        with db() as c:
            cnts = c.execute("SELECT (SELECT COUNT(*) FROM trainees WHERE hidden=0) tr, (SELECT COUNT(*) FROM questions) qs").fetchone()
        st.metric("إجمالي المتدربين الظاهرين", cnts["tr"])
        st.metric("إجمالي الأسئلة", cnts["qs"])

    elif selected_menu == "🖨 الطباعة والترويسة":
        st.subheader("🖨 إعدادات الطباعة والترويسة")
        current_set = get_print_settings()
        with st.form("print_settings_form"):
            header_text_val = st.text_area("نص ترويسة الجهة:", value=current_set.get("header_text", ""))
            def_title_val = st.text_input("عنوان الشهادة:", value=current_set.get("default_cert_title", ""))
            if st.form_submit_button("حفظ", use_container_width=True):
                save_print_settings(header_text_val, "1.5mm", "1.5mm", "1.5mm", "1.5mm", current_set["logo_base64"], "", "", "", "", def_title_val, "", "", "", "", current_set.get("professions_list", []))
                st.success("تم الحفظ!"); st.rerun()

    elif selected_menu == "🏥 الهيكل الإداري":
        st.subheader("🏥 الهيكل الإداري")
        df = pd.DataFrame(get_hierarchical_data(include_hidden=True))
        if not df.empty: st.dataframe(df, use_container_width=True, hide_index=True)

    elif selected_menu == "🧑‍🔬 المتدربين والنماذج":
        st.subheader("🧑‍🔬 المتدربين والشهادات المضغوطة")
        with db() as c: sessions_list = c.execute("SELECT s.id, t.name, t.facility FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.status='submitted' AND t.hidden=0").fetchall()
        if sessions_list:
            sel = st.selectbox("اختر المتدرب:", [f"{s['id']} - {s['name']} ({s['facility']})" for s in sessions_list])
            sid = int(sel.split(" - ")[0])
            render_print_button_only(generate_customizable_certificate_html(sid), f"شهادة متدرب {sid}")

    elif selected_menu == "🧠 بنك الأسئلة":
        st.subheader("🧠 بنك الأسئلة")
        with db() as c: df = pd.read_sql_query("SELECT * FROM questions", c)
        st.dataframe(df, use_container_width=True, hide_index=True)

    elif selected_menu == "⚙ إدارة الأسئلة":
        st.subheader("⚙️ إدارة الأسئلة")
        st.info("إدارة الأسئلة المفردة.")

    elif selected_menu == "🧩 مواعيد الاختبارات و طباعة النماذج":
        st.subheader("🧩 نماذج الاختبارات والأسئلة (3 أعمدة مكثفة)")
        with db() as c: tpls = c.execute("SELECT id, name FROM exam_templates").fetchall()
        for t in tpls:
            st.write(f"نموذج: {t['name']}")
            render_print_button_only(generate_exam_template_print_html(t["id"]), f"نموذج امتحان {t['id']}")

    elif selected_menu == "✍ تسجيل نتيجة يدوي":
        st.subheader("✍ تسجيل نتيجة يدوي")
        st.info("قسم التسجيل اليدوي.")

    elif selected_menu == "📊 التقارير":
        st.subheader("📊 التقارير وتحليل الأداء (مضغوطة لزيادة الاستيعاب)")
        with db() as c:
            df_rep = pd.read_sql_query("SELECT t.id AS 'مسلسل', t.name AS 'اسم المتدرب', t.facility AS 'جهة العمل', COALESCE(s.percent, 0) AS 'النسبة %' FROM trainees t LEFT JOIN exam_sessions s ON s.trainee_id=t.id WHERE t.hidden=0", c)
        if not df_rep.empty:
            st.dataframe(df_rep, use_container_width=True, hide_index=True)
            render_print_button_only(generate_general_report_html("تقرير النتائج الشامل", df_rep.to_html(index=False, border=0)), "التقرير الشامل")

    elif selected_menu == "📈 خطط العمل":
        st.subheader("📈 خطط العمل التدريبية ومعالجة الضعف (مسافات معتدلة ومريحة)")
        with db() as c: plans = c.execute("SELECT * FROM action_plans").fetchall()
        if not plans:
            st.info("لا توجد خطط عمل مسجلة.")
        else:
            for p in plans:
                st.write(f"خطة رقم ({p['id']}) - المستهدف: {p['target_name']}")
                html_p = f"""
                <div style="font-family: 'Cairo', sans-serif; direction: rtl; padding: 12px; line-height: 1.6;">
                    <p style="font-size: 11pt; margin-bottom: 8px;"><b>نطاق الخطة:</b> {esc(p['target_type'])} | <b>المستهدف:</b> {esc(p['target_name'])} | <b>الإطار الزمني:</b> شهر {esc(p['specific_month'])} لسنة {esc(p['specific_year'])}</p>
                    <div style="background: #f0fdf4; border: 1px solid #059669; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                        <h4 style="color: #065f46; margin-top: 0; font-size: 12pt;">🎯 نقاط الضعف والأقسام المرصودة:</h4>
                        <p style="white-space: pre-wrap; margin-bottom: 0; font-size: 10.5pt; color: #1f2937;">{esc(p['weakness_areas'])}</p>
                    </div>
                    <div style="background: #ffffff; border: 1px solid #cbd5e1; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                        <h4 style="color: #065f46; margin-top: 0; font-size: 12pt;">🛠 الخطوات الإجرائية والبرنامج العلاجي:</h4>
                        <p style="white-space: pre-wrap; margin-bottom: 0; font-size: 10.5pt; color: #1f2937;">{esc(p['action_steps'])}</p>
                    </div>
                </div>
                """
                render_print_button_only(generate_action_plan_report_html(f"خطة عمل - {p['target_name']}", html_p), f"خطة عمل {p['id']}")

    elif selected_menu == "💾 النسخ الاحتياطي":
        st.subheader("💾 النسخ الاحتياطي")
        with open(DB_PATH, "rb") as f: st.download_button("تحميل قاعدة البيانات", f, file_name="db.db", use_container_width=True)

    elif selected_menu == "👥 إدارة المستخدمين":
        st.subheader("👥 المستخدمين")
        st.info("إدارة المستخدمين.")

    elif selected_menu == "🧾 سجل التدقيق":
        st.subheader("🧾 سجل التدقيق")
        with db() as c: df = pd.read_sql_query("SELECT * FROM audit_logs LIMIT 50", c)
        st.dataframe(df, use_container_width=True, hide_index=True)

def trainee_portal():
    with db() as c: tr = c.execute("SELECT * FROM trainees WHERE id=? AND hidden=0", (st.session_state.trainee_id,)).fetchone()
    if not tr: st.session_state.trainee_id = None; st.rerun()
    header()
    if tr["status"] == "pending":
        st.info("⏳ حسابك في انتظار اعتماد الإدارة...")
        return
    with db() as c: tpl = c.execute("SELECT * FROM exam_templates WHERE id=?", (tr["assigned_template_id"],)).fetchone()
    if tpl:
        try:
            sid = start_session(tr["id"], tpl["id"])
            st.session_state.exam_session_id = sid
            st.rerun()
        except Exception as e:
            st.error(str(e))

def exam_interface(session_id):
    header()
    with db() as c: rows = c.execute("SELECT eq.*, q.question, q.options_json FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=?", (session_id,)).fetchall()
    for row in rows:
        try: opts = json.loads(row["options_json"])
        except: opts = ["نعم", "لا"]
        order = json.loads(row["option_order_json"])
        disp_opts = [opts[i] for i in order]
        st.markdown(f'<div class="question"><b>س ({row["position"]+1}):</b> {clean_question_text(row["question"])}</div>', unsafe_allow_html=True)
        choice = st.radio("اختر:", disp_opts, key=f"q_{row['id']}", label_visibility="collapsed")
        if choice:
            sel = order[disp_opts.index(choice)]
            with db() as c: c.execute("UPDATE exam_questions SET selected_option=?, is_correct=CASE WHEN ?=(SELECT answer FROM questions WHERE id=question_id) THEN 1 ELSE 0 END WHERE id=?", (sel, sel, row["id"]))
    if st.button("تسليم الاختبار", use_container_width=True):
        submit_session(session_id)
        st.session_state.exam_session_id = None
        st.success("تم التسليم!")
        st.rerun()

# ============================================================
# 7) التوجيه الأساسي الشامل للشاشات
# ============================================================
if st.session_state.get("show_verification_portal", False):
    verification_portal_view()
elif st.session_state.get("exam_session_id"):
    exam_interface(st.session_state.exam_session_id)
elif st.session_state.trainee_id and not st.session_state.logged_in:
    if st.session_state.get("last_result_id"):
        sid = st.session_state.last_result_id
        header()
        st.success("النتيجة جاهزة!")
        render_print_button_only(generate_customizable_certificate_html(sid), f"الشهادة {sid}")
        if st.button("العودة"): st.session_state.trainee_id = None; st.session_state.last_result_id = None; st.rerun()
    else:
        trainee_portal()
elif not st.session_state.logged_in:
    login_portal()
else:
    admin_dashboard()
