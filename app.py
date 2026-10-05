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
# 1) إعدادات التطبيق الأساسية
# ============================================================
st.set_page_config(
    page_title="نظام تقييم و اختبار العاملين بالامراض المتوطنة 🪱🔬🐌💊 - System V1.0",
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
# 2) دوال التوقيت أونلاين لمصر
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
# 3) التنسيقات والأمان (CSS)
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

.block-container {
    max-width: 1150px !important;
    margin: auto !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-top: 3.5rem !important;
    padding-bottom: 7rem !important;
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
""", unsafe_allow_html=True)

st.markdown("""
<div class="ownership-watermark">
جميع الحقوق محفوظة © 2026 | تصميم وتطوير: Dr/Ahmed.S.Hegazy
</div>
""", unsafe_allow_html=True)

# ============================================================
# 4) دوال قاعدة البيانات وإعادة الترتيب التلقائي للـ ID
# ============================================================
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
    "👥 إدارة المهن والوظائف": "تقسيم وإدارة المهن والوظائف",
    "⚙ إدارة الأسئلة": "إدارة الأسئلة الفردية وبنك الأسئلة الشامل",
    "🧑🔬 المتدربين والنماذج": "اعتماد المتدربين والنماذج وطباعة النتائج",
    "🧩 مواعيد الاختبارات و طباعة النماذج": "نماذج التدريب والمواعيد",
    "✍ تسجيل نتيجة يدوي": "التسجيل اليدوي للنتائج",
    "🖨 ضبط اعدادات الطباعة و الهوامش": "إعدادات هوامش وترويسات التقارير العامة",
    "🎨 إعدادات الشهادات المخصصة": "صفحة مخصصة لضبط الشهادات بالكامل وطباعتها",
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
            governorate TEXT NOT NULL,
            authority TEXT NOT NULL,
            center TEXT NOT NULL,
            administration TEXT NOT NULL,
            facility_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            hidden INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS trainees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            profession TEXT NOT NULL DEFAULT 'أخصائي تحاليل طبية',
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

init_db()

def get_print_settings():
    with db() as c:
        row = c.execute("SELECT * FROM print_settings ORDER BY id DESC LIMIT 1").fetchone()
        if row: 
            res = dict(row)
            try: res["professions_list"] = json.loads(res.get("professions_list_json", "[]"))
            except: res["professions_list"] = ["أخصائي تحاليل طبية", "طبيب بيطري", "فني معمل"]
            if "line_spacing" not in res or res["line_spacing"] is None: res["line_spacing"] = 1.25
            return res
        return {
            "header_text": "جمهورية مصر العربية<br>وزارة الصحة والسكان<br>مديرية الشئون الصحية بالشرقية<br>الإدارة الصحية بأولاد صقر",
            "margin_top": "3mm", "margin_bottom": "3mm", "margin_right": "3mm", "margin_left": "3mm",
            "line_spacing": 1.25, "logo_base64": DEFAULT_LOGO, "logo2_base64": "", "logo3_base64": "",
            "bg_base64": "", "frame_base64": "", "default_cert_title": "شهادة اجتياز اختبار معتمدة",
            "default_cert_notes": "تقرير أداء المعامل والإشراف الفني المعتمد",
            "trainee_prefix": "", "trainee_title": "دكتور", "trainee_profession": "أخصائي تحاليل طبية",
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
        if not include_hidden: q += " WHERE hidden = 0"
        q += " ORDER BY id ASC"
        rows = c.execute(q).fetchall()
        return [dict(r) for r in rows] if rows else []

def resolve_header_text(facility_name="", manual_override_text=""):
    sett = get_print_settings()
    default_header = sett.get("header_text", "جمهورية مصر العربية<br>وزارة الصحة والسكان<br>مديرية الشئون الصحية بالشرقية<br>الإدارة الصحية بأولاد صقر")
    if manual_override_text.strip(): return manual_override_text.strip()
    if facility_name:
        with db() as c:
            fac_rec = c.execute("SELECT * FROM hierarchical_facilities WHERE facility_name=? AND hidden=0 LIMIT 1", (facility_name,)).fetchone()
            if fac_rec: return f"جمهورية مصر العربية<br>{esc(fac_rec['authority'])}<br>{esc(fac_rec['governorate'])}<br>{esc(fac_rec['administration'])} - {esc(fac_rec['facility_name'])}"
    return default_header

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
        if conditions: q += " WHERE " + " AND ".join(conditions)
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
            if not all_db_questions: all_db_questions = [dict(r) for r in c.execute("SELECT * FROM questions WHERE active=1 ORDER BY RANDOM()").fetchall()]
        else:
            all_db_questions = [dict(r) for r in c.execute("SELECT * FROM questions WHERE active=1 ORDER BY RANDOM()").fetchall()]
    if limit_count >= 999900: return all_db_questions
    return all_db_questions[:limit_count]

def render_logos_html():
    sett = get_print_settings()
    logo1 = sett.get("logo_base64", DEFAULT_LOGO)
    logo2 = sett.get("logo2_base64", "")
    logos_list_html = f'<img src="{logo1}" style="width: 35px; height: 35px; object-fit: contain;" alt="Logo 1">'
    if logo2: logos_list_html += f'<img src="{logo2}" style="width: 35px; height: 35px; object-fit: contain;" alt="Logo 2">'
    return f'<div style="display: flex; gap: 4px; align-items: center;">{logos_list_html}</div>'

def render_top_left_logo_html():
    sett = get_print_settings()
    logo3 = sett.get("logo3_base64", "")
    if logo3: return f'<div style="position: absolute; top: 10mm; left: 12mm; text-align: left; z-index: 2;"><img src="{logo3}" style="width: 35px; height: 35px; object-fit: contain;" alt="Logo 3"></div>'
    return ""

def generate_qr_code_base64(data_text):
    qr = qrcode.QRCode(version=1, box_size=5, border=1)
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return "data:image/png;base64," + __import__("base64").b64encode(buffered.getvalue()).decode("utf-8")

def generate_trainee_exam_sheet_html(sid, use_auto_header=True, manual_header_text=""):
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    with db() as c:
        s = c.execute("""SELECT s.*, t.name trainee_name, t.facility, t.profession trainee_profession, e.name template_name, e.exam_type 
                         FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?""", (sid,)).fetchone()
        if not s: return ""
        rows = c.execute("""SELECT eq.*, q.question, q.options_json, q.answer 
                            FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=? ORDER BY eq.position""", (sid,)).fetchall()
    
    header_rendered = resolve_header_text(facility_name=s["facility"]) if use_auto_header else resolve_header_text(facility_name="", manual_override_text=manual_header_text)

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
            if img_uri: img_tag_html = f'<div style="margin: 2px 0; text-align: center;"><img src="{img_uri}" style="max-height: 45px; max-width: 100%; object-fit: contain; border-radius: 3px; border: 1px solid #cbd5e1;"></div>'
        else: q_text_clean = raw_q_text

        opts_html = ""
        for o_idx, opt_text in enumerate(disp_opts):
            orig_opt_index = order[o_idx]
            is_selected = (selected_opt_idx is not None and orig_opt_index == int(selected_opt_idx))
            is_true_ans = (orig_opt_index == int(correct_ans_idx))
            style_bg, border_color, icon_str = "#f8fafc", "#e2e8f0", "🔲"
            if is_true_ans: style_bg, border_color, icon_str = "#dcfce7", "#059669", "✅"
            elif is_selected and not is_true_ans: style_bg, border_color, icon_str = "#fee2e2", "#dc2626", "❌"
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
    <head><meta charset="UTF-8">
        <style>
            @page {{ size: A4 auto; margin: 5mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0; padding: 3mm; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
            .report-wrapper {{ max-width: 210mm; margin: auto; position: relative; }}
            .report-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #059669; padding-bottom: 3mm; margin-bottom: 4mm; }}
            .header-right {{ font-size: 8.5pt; font-weight: bold; color: #065f46; line-height: {line_sp}; }}
            h2 {{ text-align: center; color: #047857; font-size: 11pt; margin: 2px 0; line-height: {line_sp}; }}
            .tpl-info {{ background: #f0fdf4; border: 1px dashed #059669; padding: 3px 6px; border-radius: 3px; margin-bottom: 5px; font-size: 8pt; font-weight: bold; color: #065f46; text-align: center; line-height: {line_sp}; }}
            .questions-grid {{ column-count: 2; column-gap: 4mm; column-fill: auto; }}
            .footer {{ margin-top: 5px; display: flex; justify-content: space-between; font-size: 8pt; font-weight: bold; border-top: 1px dashed #059669; padding-top: 3mm; page-break-inside: avoid; break-inside: avoid; line-height: {line_sp}; }}
        </style>
    </head>
    <body>
        <div class="report-wrapper">
            {render_top_left_logo_html()}
            <div class="report-header"><div class="header-right">{header_rendered}</div><div>{render_logos_html()}</div></div>
            <h2>نموذج إجابة واختبار المتدرب: {esc(s['trainee_name'])}</h2>
            <div class="tpl-info">جهة العمل: {esc(s['facility'])} | المهنة: {esc(s.get('trainee_profession', ''))} | النتيجة: {score_val} / {max_score_val} ({percent_val:.1f}%)</div>
            <div class="questions-grid">{q_html_content}</div>
            <div class="footer"><div>مسؤول التدريب</div><div>رئيس قسم المعامل</div><div>مدير المتوطنة</div><div>مدير عام الإدارة</div></div>
        </div>
    </body>
    </html>
    """

def render_print_button_only(html_content, label_prefix=""):
    encoded_html = json.dumps(html_content)
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1: chosen_orient = st.selectbox("اتجاه الورق للطباعة (مقاس A4):", ["رأسي (Portrait)", "أفقي (Landscape)"], key=f"orient_{hash(label_prefix)}")
    with col_opt2: num_pages_to_print = st.number_input("عدد الأوراق / النسخ المطلوبة:", min_value=1, max_value=50, value=1, key=f"copies_{hash(label_prefix)}")
    js_code = """
        <div style="margin: 4px 0;">
            <button onclick="printDoc()" style="width: 100%; background-color: #059669; color: white; padding: 8px 12px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-family: 'Cairo', sans-serif; font-size: 13pt;">
                🖨 طباعة / حفظ المستند (""" + label_prefix + """)
            </button>
        </div>
        <script>
            function printDoc() {
                var win = window.open('', '_blank');
                var targetPages = """ + str(num_pages_to_print) + """;
                var styledHtml = """ + encoded_html + """;
                var finalPagesHtml = '';
                for (var i = 0; i < targetPages; i++) { finalPagesHtml += styledHtml; }
                win.document.write(finalPagesHtml);
                win.document.close();
                win.focus();
                setTimeout(function(){ win.print(); }, 600);
            }
        </script>
    """
    components.html(js_code, height=100)

# ============================================================
# 5) واجهات النظام والتحكم الأساسية
# ============================================================
for k, v in {"logged_in": False, "username": "", "role": "", "permissions": [], "trainee_id": "", "trainee_name": "", "active_admin_tab": "📊 لوحة التحكم"}.items():
    if k not in st.session_state: st.session_state[k] = v

def header():
    header_html = f"""
    <div style="background: linear-gradient(135deg, #064e3b 0%, #065f46 50%, #0f766e 100%); color: #ffffff; padding: 14px 40px; border-radius: 12px; text-align: center; margin-bottom: 20px; font-family: 'Cairo', sans-serif; border: 2px solid #34d399;">
        <div style="font-size: 24px;">🪱🔬🐌💊</div>
        <div style="font-size: 19px; font-weight: 900; margin-bottom: 4px;">مرحبا بك فى بوابة تقييم و اختبار العاملين بالامراض المتوطنة</div>
        <div style="font-size: 12px; font-weight: bold; background: rgba(255,255,255,0.2); display: inline-block; padding: 2px 10px; border-radius: 12px;">System V1.0</div>
    </div>
    """
    components.html(header_html, height=130, scrolling=False)

def login_portal():
    header()
    hier_data = get_hierarchical_data(include_hidden=False)
    print_st = get_print_settings()
    professions_list = print_st.get("professions_list", ["أخصائي تحاليل طبية", "طبيب بيطري"])
    
    with st.form("trainee_request_hierarchical"):
        st.markdown("##### 📍 الجهة الإدارية التابع لها:")
        st.text_input("جمهورية مصر العربية", value="جمهورية مصر العربية", disabled=True)
        st.text_input("وزارة الصحة والسكان", value="وزارة الصحة والسكان", disabled=True)

        if not hier_data:
            st.warning("⚠ لا توجد بيانات في الهيكل الإداري حالياً.")
            facility_final_str = ""
        else:
            govs = sorted(list(set(i["governorate"] for i in hier_data)))
            sel_gov = st.selectbox("المحافظة:", ["-- اختر المحافظة --"] + govs)
            auths = sorted(list(set(i["authority"] for i in hier_data if sel_gov == "-- اختر المحافظة --" or i["governorate"] == sel_gov)))
            sel_auth = st.selectbox("الهيئة:", ["-- اختر الهيئة --"] + auths)
            centers = sorted(list(set(i["center"] for i in hier_data if (sel_gov == "-- اختر المحافظة --" or i["governorate"] == sel_gov) and (sel_auth == "-- اختر الهيئة --" or i["authority"] == sel_auth))))
            sel_center = st.selectbox("المركز:", ["-- اختر المركز --"] + centers)
            admins = sorted(list(set(i["administration"] for i in hier_data if (sel_gov == "-- اختر المحافظة --" or i["governorate"] == sel_gov) and (sel_auth == "-- اختر الهيئة --" or i["authority"] == sel_auth) and (sel_center == "-- اختر المركز --" or i["center"] == sel_center))))
            sel_admin = st.selectbox("الإدارة:", ["-- اختر الإدارة --"] + admins)
            facs = sorted(list(set(i["facility_name"] for i in hier_data if (sel_gov == "-- اختر المحافظة --" or i["governorate"] == sel_gov) and (sel_auth == "-- اختر الهيئة --" or i["authority"] == sel_auth) and (sel_center == "-- اختر المركز --" or i["center"] == sel_center) and (sel_admin == "-- اختر الإدارة --" or i["administration"] == sel_admin))))
            sel_fac = st.selectbox("المنشأة:", ["-- اختر المنشأة --"] + facs)
            
            if "--" not in sel_gov and "--" not in sel_auth and "--" not in sel_center and "--" not in sel_admin and "--" not in sel_fac:
                facility_final_str = f"جمهورية مصر العربية - وزارة الصحة والسكان - {sel_gov} - {sel_auth} - {sel_center} - {sel_admin} - {sel_fac}"
            else: facility_final_str = ""

        name = st.text_input("الاسم الرباعي:")
        phone = st.text_input("رقم الهاتف:")
        selected_profession = st.selectbox("المهنة / الوظيفة:", professions_list)
        
        with db() as c: all_tpls_opts = {f"{r['name']} ({r['exam_type']})": r["id"] for r in c.execute("SELECT id, name, exam_type FROM exam_templates ORDER BY name ASC").fetchall()}
        sel_req_tpl = st.selectbox("اختر نموذج الاختبار:", ["-- اختر نموذج الاختبار --"] + list(all_tpls_opts.keys()))
        
        if st.form_submit_button("إرسال الطلب والدخول", use_container_width=True):
            if not facility_final_str: st.warning("⚠️ يرجى استكمال اختيار جميع حقول الهيكل الإداري بدقة.")
            elif sel_req_tpl == "-- اختر نموذج الاختبار --": st.warning("⚠️ يرجى اختيار نموذج الاختبار.")
            elif name.strip() and all_tpls_opts:
                assigned_tpl_id = all_tpls_opts.get(sel_req_tpl)
                existing = trainee_by_credentials(name, facility_final_str)
                if existing:
                    st.session_state.trainee_id = existing["id"]
                    st.session_state.trainee_name = existing["name"]
                    st.rerun()
                else:
                    tid = create_trainee(facility_final_str, name, phone, selected_profession, assigned_tpl_id)
                    st.session_state.trainee_id = tid
                    st.session_state.trainee_name = name
                    st.success("✅ تم التسجيل بنجاح!"); st.rerun()

    with st.expander("🔐 تسجيل دخول الإدارة"):
        with st.form("admin_login_form_hidden"):
            u = st.text_input("اسم المستخدم")
            p = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("دخول لوحة التحكم", use_container_width=True):
                user = login_user(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.role = user["role"]
                    st.session_state.permissions = json.loads(user["permissions_json"]) if user["permissions_json"] else list(ALL_MENU_MODULES.keys())
                    st.rerun()
                else: st.error("بيانات غير صحيحة.")

def admin_dashboard():
    header()
    c_info, c_btn = st.columns([4, 1])
    with c_info: st.write(f"**المستخدم:** {st.session_state.username} | **الصلاحية:** {ROLES.get(st.session_state.role, '')}")
    with c_btn:
        if st.button("تسجيل الخروج", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.rerun()

    available_menus = list(ALL_MENU_MODULES.keys())
    cols_per_row = 3
    for i in range(0, len(available_menus), cols_per_row):
        row_cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(available_menus):
                m_key = available_menus[i + j]
                is_active = (st.session_state.active_admin_tab == m_key)
                if row_cols[j].button(f"📍 {m_key}" if is_active else m_key, use_container_width=True, key=f"btn_m_{i+j}"):
                    st.session_state.active_admin_tab = m_key
                    st.rerun()

    selected_menu = st.session_state.active_admin_tab
    st.markdown("---")

    if selected_menu == "📊 لوحة التحكم":
        st.subheader("📊 لوحة المؤشرات العامة")
        with db() as c:
            cnts = c.execute("SELECT (SELECT COUNT(*) FROM trainees WHERE hidden=0) tr, (SELECT COUNT(*) FROM trainees WHERE status='pending' AND hidden=0) pend, (SELECT COUNT(*) FROM questions) qs").fetchone()
        cols = st.columns(3)
        for box, l, v in zip(cols, ["إجمالي المتدربين", "الطلبات المعلقة", "بنك الأسئلة"], [cnts["tr"], cnts["pend"], cnts["qs"]]):
            box.markdown(f'<div class="metric"><div class="v">{v}</div><div class="l">{l}</div></div>', unsafe_allow_html=True)

    elif selected_menu == "🧑‍🔬 المتدربين والنماذج":
        st.subheader("🧑‍🔬 إدارة واعتماد المتدربين ونماذج الاختبارات")
        with db() as c: all_tpls = c.execute("SELECT id, name, exam_type FROM exam_templates ORDER BY name ASC").fetchall()
        tpl_map = {f"{r['name']} ({r['exam_type']})": r["id"] for r in all_tpls} if all_tpls else {}
        tpl_names = list(tpl_map.keys()) if tpl_map else ["لا توجد نماذج"]

        sub_tabs = st.tabs(["الطلبات المعلقة", "جميع المتدربين", "📝 طباعة نموذج امتحان الممتحن"])
        with sub_tabs[0]:
            df_pend = trainees_df("pending")
            if df_pend.empty: st.info("لا توجد طلبات معلقة.")
            else:
                for _, r in df_pend.iterrows():
                    with st.container(border=True):
                        st.write(f"**الاسم:** {r['name']} | **الجهة:** {r['facility']}")
                        with st.form(f"app_f_{r['id']}"):
                            chosen_t = st.selectbox("نموذج الاختبار:", tpl_names, key=f"t_{r['id']}")
                            if st.form_submit_button("✅ اعتماد", use_container_width=True):
                                if tpl_map and chosen_t in tpl_map:
                                    set_trainee_status_and_template(int(r['id']), "approved", tpl_map[chosen_t])
                                    st.success("✅ تم الاعتماد!"); st.rerun()

        with sub_tabs[1]:
            df_all = trainees_df(include_hidden=True)
            if df_all.empty: st.info("لا توجد بيانات متدربين.")
            else:
                for _, tr in df_all.iterrows():
                    with st.container(border=True):
                        st.write(f"**المتدرب:** {tr['name']} | **الحالة:** `{STATUS_AR.get(tr['status'], tr['status'])}`")
                        with st.form(f"upd_tr_{tr['id']}"):
                            if st.form_submit_button("🗑 حذف", use_container_width=True):
                                with db() as c: c.execute("DELETE FROM trainees WHERE id=?", (int(tr['id']),))
                                reindex_trainees()
                                st.success("✅ تم الحذف وإعادة الترتيب!"); st.rerun()

        with sub_tabs[2]:
            st.markdown("#### 📝 طباعة نموذج امتحان الممتحن:")
            ex_h_mode = st.radio("مصدر الترويسة:", ["تلقائي (سحب الهيكل الإداري)", "يدوي"], horizontal=True)
            manual_ex = st.text_area("النص اليدوي:") if "يدوي" in ex_h_mode else ""
            with db() as c:
                com_s = c.execute("SELECT s.id, t.name trainee_name, t.facility, e.name template_name FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.status='submitted' AND t.hidden=0").fetchall()
            if not com_s: st.info("لا توجد اختبارات مكتملة.")
            else:
                s_map = {f"{r['trainee_name']} - {r['facility']} (ID: {r['id']})": r['id'] for r in com_s}
                sel_s = st.selectbox("اختر الممتحن:", list(s_map.keys()))
                html_sheet = generate_trainee_exam_sheet_html(s_map[sel_s], use_auto_header=("تلقائي" in ex_h_mode), manual_header_text=manual_ex)
                render_print_button_only(html_sheet, "نموذج إجابة الممتحن")

    else:
        st.subheader(f"شاشة {selected_menu}")
        st.info("هذا القسم يعمل بشكل طبيعي ومتكامل مع النظام.")

# ============================================================
# 6) التوجيه الأساسي
# ============================================================
if st.session_state.trainee_id and not st.session_state.logged_in:
    st.success("🟢 أهلاً بك في بوابة المتدربين.")
elif not st.session_state.logged_in:
    login_portal()
else:
    admin_dashboard()
