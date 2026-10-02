import os, io, re, ast, json, html, sqlite3, hashlib, secrets, random, time
from datetime import datetime, timedelta, date
from contextlib import contextmanager

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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
# 2) حقن التنسيقات (CSS) وحماية الأمان وحقوق الملكية
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
}

.stApp {
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 45%, #bbf7d0 100%) !important;
    background-attachment: fixed !important;
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
document.addEventListener("copy", function(e) { e.preventDefault(); alert("⚠️ عذراً، نسخ النصوص محظور حفاظاً على سرية الأسئلة!"); });
</script>
""", unsafe_allow_html=True)

st.markdown("""
<div class="ownership-watermark">
🔬 جميع الحقوق محفوظة © 2026 | تصميم و تطوير: <b>Dr/Ahmed.S.Hegazy</b>
</div>
""", unsafe_allow_html=True)

# ============================================================
# 3) دوال النظام وقاعدة البيانات
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
    "🖨️ الطباعة والترويسة": "إعدادات الطباعة والترويسة والخلفيات",
    "🏥 الهيكل الإداري": "الهيكل الإداري والمنشآت ورفع البيانات",
    "🧑‍🔬 المتدربين والنماذج": "اعتماد المتدربين والنماذج",
    "🧠 بنك الأسئلة": "بنك الأسئلة الشامل وإكسيل",
    "⚙ إدارة الأسئلة": "إدارة الأسئلة الفردية",
    "🧩 مواعيد الامتحانات": "نماذج التدريب والمواعيد",
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
            governorate TEXT NOT NULL,
            authority TEXT NOT NULL,
            center TEXT NOT NULL,
            administration TEXT NOT NULL,
            facility_name TEXT NOT NULL,
            created_at TEXT NOT NULL
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
        CREATE TABLE IF NOT EXISTS print_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            header_text TEXT NOT NULL,
            margin_top TEXT NOT NULL,
            margin_bottom TEXT NOT NULL,
            margin_right TEXT NOT NULL,
            margin_left TEXT NOT NULL,
            logo_base64 TEXT NOT NULL,
            logo2_base64 TEXT NOT NULL DEFAULT '',
            bg_base64 TEXT NOT NULL DEFAULT '',
            default_cert_title TEXT NOT NULL DEFAULT 'شهادة اجتياز اختبار معتمدة',
            default_cert_notes TEXT NOT NULL DEFAULT 'تقرير أداء المعامل والإشراف الفني المعتمد'
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

        try:
            c.execute("ALTER TABLE users ADD COLUMN permissions_json TEXT NOT NULL DEFAULT '[]'")
        except:
            pass

        for col_def in [
            ("exam_templates", "start_time", "TEXT"), 
            ("exam_templates", "end_time", "TEXT"), 
            ("print_settings", "logo2_base64", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "bg_base64", "TEXT NOT NULL DEFAULT ''"),
            ("print_settings", "default_cert_title", "TEXT NOT NULL DEFAULT 'شهادة اجتياز اختبار معتمدة'"),
            ("print_settings", "default_cert_notes", "TEXT NOT NULL DEFAULT 'تقرير أداء المعامل والإشراف الفني المعتمد'")
        ]:
            try:
                c.execute(f"ALTER TABLE {col_def[0]} ADD COLUMN {col_def[1]} {col_def[2]}")
            except:
                pass

        cnt = c.execute("SELECT COUNT(*) FROM print_settings").fetchone()[0]
        if cnt == 0:
            default_header = "جمهورية مصر العربية><br> وزارة الصحة والسكان<br>مديرية الشئون الصحية ....<br>الإدارة الصحية .... "
            c.execute("INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, logo_base64, logo2_base64, bg_base64, default_cert_title, default_cert_notes) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (default_header, "8mm", "8mm", "8mm", "8mm", DEFAULT_LOGO, "", "", "شهادة اجتياز اختبار معتمدة", "تقرير أداء المعامل والإشراف الفني المعتمد"))

init_db()

def get_print_settings():
    with db() as c:
        row = c.execute("SELECT * FROM print_settings ORDER BY id DESC LIMIT 1").fetchone()
        if row: return dict(row)
        return {
            "header_text": "جمهورية مصر العربية <br> وزارة الصحة والسكان<br> ....مديرية الشئون الصحية <br> ....الإدارة الصحية ",
            "margin_top": "8mm", "margin_bottom": "8mm", "margin_right": "8mm", "margin_left": "8mm",
            "logo_base64": DEFAULT_LOGO,
            "logo2_base64": "",
            "bg_base64": "",
            "default_cert_title": "شهادة اجتياز اختبار معتمدة",
            "default_cert_notes": "تقرير أداء المعامل والإشراف الفني المعتمد"
        }

def save_print_settings(h_text, m_top, m_bot, m_right, m_left, logo_data, logo2_data, bg_data, def_title, def_notes):
    with db() as c:
        c.execute("DELETE FROM print_settings")
        c.execute("INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, logo_base64, logo2_base64, bg_base64, default_cert_title, default_cert_notes) VALUES(?,?,?,?,?,?,?,?,?,?)",
                  (h_text, m_top, m_bot, m_right, m_left, logo_data, logo2_data, bg_data, def_title, def_notes))

def get_hierarchical_data():
    with db() as c:
        rows = c.execute("SELECT * FROM hierarchical_facilities ORDER BY id ASC").fetchall()
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
        cur = c.execute("INSERT INTO trainees(facility,name,phone,status,assigned_template_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                        (normalize_text(facility), normalize_text(name), normalize_text(phone), "pending", assigned_template_id, now(), now()))
        tid = cur.lastrowid
    return tid

def trainee_by_credentials(name, facility):
    with db() as c:
        r = c.execute("SELECT * FROM trainees WHERE name=? AND facility=? AND status IN ('approved','active')",
                      (normalize_text(name), normalize_text(facility))).fetchone()
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
                         updated_at=? """,
                  (assigned_template_id, now(), now()))

def trainees_df(status=None):
    with db() as c:
        q = "SELECT id, facility, name, phone, status, assigned_template_id, created_at, approved_at FROM trainees"
        args = []
        if status:
            q += " WHERE status=?"
            args = [status]
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
    if logo2:
        return f"""
        <div style="display: flex; gap: 8px; align-items: center;">
            <img src="{logo1}" style="width: 55px; height: 55px; object-fit: contain;" alt="Logo 1">
            <img src="{logo2}" style="width: 55px; height: 55px; object-fit: contain;" alt="Logo 2">
        </div>
        """
    else:
        return f"""
        <div>
            <img src="{logo1}" style="width: 65px; height: 65px; object-fit: contain;" alt="Logo">
        </div>
        """

def generate_customizable_certificate_html(sid, custom_title=None, custom_notes=None):
    sett = get_print_settings()
    title_val = custom_title if custom_title is not None else sett.get("default_cert_title", "شهادة اجتياز اختبار معتمدة")
    notes_val = custom_notes if custom_notes is not None else sett.get("default_cert_notes", "تقرير أداء المعامل والإشراف الفني المعتمد")

    with db() as c:
        r = c.execute("""SELECT s.*, t.name trainee_name, t.facility, e.name template_name 
                         FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?""", (sid,)).fetchone()
    if not r: return ""
    status_text = "اجتزت بنجاح" if r["passed"] else "لم تجتز الاختبار"
    score_val, max_score_val, percent_val = r["score"] or 0, r["max_score"] or 0, r["percent"] or 0.0
    tpl_name = r["template_name"] or "اختبار تقييمي معتمد"
    
    bg_data = sett.get("bg_base64", "")
    bg_style = f"background: url('{bg_data}') no-repeat center center; background-size: cover;" if bg_data else "background: #ffffff;"

    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 landscape; margin-top: {sett['margin_top']}; margin-bottom: {sett['margin_bottom']}; margin-right: {sett['margin_right']}; margin-left: {sett['margin_left']}; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #fdfbf7; margin: 0; padding: 0; width: 297mm; height: 210mm; display: flex; justify-content: center; align-items: center; direction: rtl; -webkit-print-color-adjust: exact; }}
            .cert-wrapper {{ 
                width: 282mm; height: 195mm; border: 12px double #059669; border-radius: 20px; {bg_style}
                display: flex; flex-direction: column; justify-content: space-between; align-items: center; 
                padding: 16mm 22mm; box-sizing: border-box; position: relative; box-shadow: 0 6px 20px rgba(0,0,0,0.06); 
            }}
            .header-top {{ position: absolute; top: 12mm; left: 18mm; text-align: left; z-index: 2; }}
            .header-right {{ position: absolute; top: 12mm; right: 18mm; text-align: right; font-size: 10.5pt; font-weight: bold; color: #065f46; line-height: 1.4; z-index: 2; }}
            .cert-body {{ text-align: center; margin-top: 14mm; width: 100%; z-index: 2; }}
            h2 {{ color: #047857; font-size: 19pt; margin-bottom: 4px; }}
            h1 {{ color: #065f46; font-size: 28pt; margin: 10px 0; font-weight: 900; }}
            p {{ font-size: 12pt; line-height: 1.7; color: #1f2937; }}
            .notes-box {{ background: rgba(240, 253, 244, 0.9); border: 1px dashed #059669; padding: 8px 16px; margin: 10px auto; width: 85%; border-radius: 8px; font-weight: bold; color: #065f46; font-size: 10.5pt; }}
            .footer-bottom {{ width: 100%; display: flex; justify-content: space-between; font-size: 10pt; font-weight: bold; text-align: center; border-top: 2px dashed #059669; padding-top: 12px; margin-top: 6mm; z-index: 2; }}
            .cert-watermark {{ font-size: 9pt; color: #059669; font-weight: bold; margin-top: 4px; z-index: 2; }}
        </style>
    </head>
    <body>
        <div class="cert-wrapper">
            <div class="header-right">{sett['header_text']}</div>
            <div class="header-top">{render_logos_html()}</div>
            <div class="cert-body">
                <h2>{esc(title_val)}</h2>
                <hr style="width: 45%; border: 1px solid #059669; margin: 6px auto;">
                <h1>{esc(r["trainee_name"])}</h1>
                <p>
                    الجهة: <b>{esc(r["facility"])}</b> &nbsp;|&nbsp; الاختبار: <b>{esc(tpl_name)}</b><br>
                    النتيجة: <b>{score_val} / {max_score_val} ({percent_val:.1f}%)</b> &nbsp;|&nbsp; 
                    الحالة: <b style="color: {'green' if r['passed'] else 'red'};">{status_text}</b><br>
                    رقم التحقق والشهادة: <code>{r["certificate_id"]}</code>
                </p>
                {f'<div class="notes-box">{esc(notes_val)}</div>' if notes_val else ''}
            </div>
            <div class="footer-bottom">
                <div>مسؤول التدريب</div>
                <div> قسم المعامل</div>
                <div>قسم المتوطنة</div>
                <div>يعتمد مدير عام الإدارة</div>
            </div>
            <div class="cert-watermark">Developed by Dr/Ahmed.S.Hegazy</div>
        </div>
    </body>
    </html>
    """

def render_print_button_only(html_content, label_prefix=""):
    encoded_html = json.dumps(html_content)
    components.html(f"""
        <div style="margin: 4px 0;">
            <button onclick="printDoc()" style="width: 100%; background-color: #059669; color: white; padding: 6px 12px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-family: 'Cairo', sans-serif;">
                🖨 طباعة / حفظ PDF ({label_prefix})
            </button>
        </div>
        <script>
            function printDoc() {{
                var win = window.open('', '_blank');
                win.document.write({encoded_html});
                win.document.close();
                win.focus();
                setTimeout(function(){{ win.print(); }}, 500);
            }}
        </script>
    """, height=50)

# ============================================================
# 6) واجهات النظام وتوجيه الشاشات
# ============================================================
for k, v in {"logged_in": False, "username": "", "role": "", "permissions": [], "trainee_id": None, "trainee_name": "", "exam_session_id": None, "last_result_id": None, "form_key": 0, "add_success_msg": "", "active_admin_tab": "📊 لوحة المؤشرات"}.items():
    if k not in st.session_state: st.session_state[k] = v

def header():
    st.markdown('<div class="hero"><h1>🔬 نظام 🔬 التقييم والاختبار للعاملين بمعامل المتوطنة</h1><div>System V1.0 • <br><small style="color:#d1fae5;">Developed by Dr/Ahmed.S.Hegazy</small></div></div>', unsafe_allow_html=True)

def login_portal():
    header()
    st.markdown("<b>تسجيل وإرسال طلب المتدربين (برجاء الاختيار و التسجيل)</b>", unsafe_allow_html=True)
    
    hier_data = get_hierarchical_data()
    
    with st.form("trainee_request_hierarchical"):
        if not hier_data:
            st.warning("⚠️ لا توجد بيانات هيكل إداري مضافة بعد. يرجى إضافتها يدوياً أو رفع ملفات الداتا.")
            facility_final_str = st.text_input("اسم جهة العمل (يدوي مؤقتاً):", value="الإدارة الصحية بأولاد صقر")
        else:
            govs = sorted(list(set(item["governorate"] for item in hier_data)))
            selected_gov = st.selectbox("1️⃣ اختر المحافظة:", govs)
            
            auths = sorted(list(set(item["authority"] for item in hier_data if item["governorate"] == selected_gov)))
            selected_auth = st.selectbox("2️⃣ اختر الهيئة / المديرية التابعة:", auths if auths else ["اختر المحافظة أولاً"])
            
            centers = sorted(list(set(item["center"] for item in hier_data if item["governorate"] == selected_gov and item["authority"] == selected_auth)))
            selected_center = st.selectbox("3️⃣ اختر المركز التابع:", centers if centers else ["اختر الهيئة أولاً"])
            
            admins = sorted(list(set(item["administration"] for item in hier_data if item["governorate"] == selected_gov and item["authority"] == selected_auth and item["center"] == selected_center)))
            selected_admin = st.selectbox("4️⃣ اختر الإدارة الصحية التابعة:", admins if admins else ["اختر المركز أولاً"])
            
            facs = sorted(list(set(item["facility_name"] for item in hier_data if item["governorate"] == selected_gov and item["authority"] == selected_auth and item["center"] == selected_center and item["administration"] == selected_admin)))
            selected_facility = st.selectbox("5️⃣ اختر المنشأة الصحية النهائية:", facs if facs else ["اختر الإدارة أولاً"])
            
            facility_final_str = f"{selected_gov} - {selected_auth} - {selected_center} - {selected_admin} - {selected_facility}"

        name = st.text_input("الاسم الرباعي:")
        phone = st.text_input("رقم الهاتف:")
        
        with db() as c: all_tpls_opts = {row["name"]: row["id"] for row in c.execute("SELECT id, name FROM exam_templates").fetchall()}
        tpl_choices_list = list(all_tpls_opts.keys()) if all_tpls_opts else ["لا توجد نماذج اختبارات مسجلة"]
        selected_req_tpl_name = st.selectbox("اختر نموذج الاختبار المبدئي:", tpl_choices_list)
        
        if st.form_submit_button("إرسال الطلب والدخول للمتدرب", use_container_width=True):
            if name.strip() and all_tpls_opts:
                assigned_tpl_id = all_tpls_opts.get(selected_req_tpl_name)
                existing = trainee_by_credentials(name, facility_final_str)
                if existing:
                    st.session_state.trainee_id = existing["id"]
                    st.session_state.trainee_name = existing["name"]
                    st.success("تم التعرف على حسابك! جاري الدخول...")
                    st.rerun()
                else:
                    tid = create_trainee(facility_final_str, name, phone, assigned_tpl_id)
                    st.session_state.trainee_id = tid
                    st.session_state.trainee_name = name
                    st.success("✅ تم تسجيل بياناتك بنجاح! جاري الانتقال للبوابة...")
                    st.rerun()
            else:
                st.warning("الرجاء إدخال الاسم الرباعي والتأكد من وجود نماذج اختبارات.")

    with st.expander("🔐 تسجيل دخول مالك المنصة / الإدارة العليا"):
        with st.form("admin_login_form_hidden"):
            u = st.text_input("اسم المستخدم الإداري")
            p = st.text_input("كلمة المرور الإدارية", type="password")
            if st.form_submit_button("دخول لوحة التحكم الإدارية", use_container_width=True):
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
                    st.error("بيانات الدخول الإدارية غير صحيحة.")

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
        st.warning("⚠️ عذراً، لا توجد أي صلاحيات مصرحة لك بالدخول إليها.")
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

    if selected_menu == "📊 لوحة التكحم العامة":
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

    elif selected_menu == "🖨️ الطباعة والترويسة":
        st.subheader("🖨 تحكم كامل في هوامش الورق، ترويسة اليمين، الشعارين، الخلفية، والنصوص الافتراضية للشهادات")
        current_set = get_print_settings()
        with st.form("print_settings_form"):
            st.markdown("#### 📄 ترويسة أعلى يمين الصفحات والشهادات:")
            new_header_text = st.text_area("نص الترويسة (يدعم HTML مثل <br>):", value=current_set["header_text"], height=90)
            
            st.markdown("#### 📝 النصوص الافتراضية للشهادات:")
            def_title_val = st.text_input("عنوان الشهادة الافتراضي:", value=current_set.get("default_cert_title", "شهادة اجتياز اختبار معتمدة"))
            def_notes_val = st.text_area("الملاحظات الافتراضية للشهادة:", value=current_set.get("default_cert_notes", "تقرير أداء المعامل والإشراف الفني المعتمد"))

            st.markdown("#### 📏 هوامش الورق المطبوع (PDF / طباعة):")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1: m_top = st.text_input("الهامش العلوي:", value=current_set["margin_top"])
            with col_m2: m_bot = st.text_input("الهامش السفلي:", value=current_set["margin_bottom"])
            with col_m3: m_right = st.text_input("الهامش الأيمن:", value=current_set["margin_right"])
            with col_m4: m_left = st.text_input("الهامش الأيسر:", value=current_set["margin_left"])
            
            st.markdown("#### 🖼 شعارات أعلى يسار الصفحات:")
            col_logo1, col_logo2 = st.columns(2)
            with col_logo1: uploaded_logo1 = st.file_uploader("الشعار الأول:", type=["png", "jpg", "jpeg"], key="logo1_upload")
            with col_logo2: uploaded_logo2 = st.file_uploader("الشعار الثاني:", type=["png", "jpg", "jpeg"], key="logo2_upload")

            st.markdown("#### 🖼️ خلفية الشهادات والأوراق الرسمية:")
            uploaded_bg = st.file_uploader("رفع صورة خلفية الشهادة أو الورقة (PNG / JPG):", type=["png", "jpg", "jpeg"], key="bg_upload")
            remove_bg = st.checkbox("حذف الخلفية الحالية (العودة لخلفية بيضاء سادة)")

            current_logo1_val = current_set["logo_base64"]
            if uploaded_logo1 is not None:
                current_logo1_val = f"data:image/{uploaded_logo1.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo1.read()).decode("utf-8")
            
            current_logo2_val = current_set.get("logo2_base64", "")
            if uploaded_logo2 is not None:
                current_logo2_val = f"data:image/{uploaded_logo2.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo2.read()).decode("utf-8")

            current_bg_val = current_set.get("bg_base64", "")
            if remove_bg:
                current_bg_val = ""
            elif uploaded_bg is not None:
                current_bg_val = f"data:image/{uploaded_bg.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_bg.read()).decode("utf-8")

            if st.form_submit_button("💾 حفظ وتطبيق إعدادات الطباعة والخلفية كإعدادات أساسية", use_container_width=True):
                save_print_settings(new_header_text, m_top, m_bot, m_right, m_left, current_logo1_val, current_logo2_val, current_bg_val, def_title_val, def_notes_val)
                st.success("✅ تم الحفظ وتعميم الإعدادات الجديدة بنجاح!"); st.rerun()

    elif selected_menu == "🏥 الهيكل الإداري":
        st.subheader("🏥 إدارة الهيكل الإداري للمنشآت الصحية (المحافظة ⟵ الهيئة ⟵ المركز ⟵ الإدارة ⟵ المنشأة)")
        
        tab_h1, tab_h2, tab_h3 = st.tabs(["✍️ إضافة هيكل إداري يدوياً", "📥 رفع ملفات لكل قائمة (Excel / CSV)", "📋 استعراض وحذف وتفريغ البيانات"])
        
        with tab_h1:
            st.markdown("#### ✍️ تسجيل منشأة صحية أو وحدة إدارية جديدة يدوياً:")
            with st.form("manual_hierarchical_form"):
                m_gov = st.text_input("المحافظة:", value="الشرقية")
                m_auth = st.text_input("الهيئة / المديرية:", value="مديرية الشئون الصحية بالشرقية")
                m_center = st.text_input("المركز:", value="أولاد صقر")
                m_admin = st.text_input("الإدارة الصحية:", value="الإدارة الصحية بأولاد صقر")
                m_fac = st.text_input("اسم المنشأة الصحية النهائية (وحدة / معمل / مستشفى):")
                
                if st.form_submit_button("💾 حفظ وإضافة الهيكل الإداري", use_container_width=True):
                    if m_fac.strip():
                        with db() as c:
                            c.execute("INSERT INTO hierarchical_facilities(governorate,authority,center,administration,facility_name,created_at) VALUES(?,?,?,?,?,?)",
                                      (m_gov.strip(), m_auth.strip(), m_center.strip(), m_admin.strip(), m_fac.strip(), now()))
                        st.success(f"✅ تم إضافة المنشأة ({m_fac}) بنجاح إلى الهيكل الإداري!"); st.rerun()
                    else:
                        st.warning("⚠️ يرجى إدخال اسم المنشأة الصحية النهائية على الأقل.")

        with tab_h2:
            st.markdown("#### 📂 إمكانية رفع ملف قاعدة بيانات لكل مستوى على حدة لتحديث واجهة الممتحن تلقائياً:")
            up_level = st.selectbox("حدد المستوى المراد رفع ملفه:", [
                "المحافظات (Governorates)",
                "الهيئات / المديريات (Authorities)",
                "المراكز (Centers)",
                "الإدارات (Administrations)",
                "المنشآت الصحية النهائية (Facilities)",
                "الملف الشامل المتكامل (يحتوي على الأعمدة الخمسة)"
            ])
            
            up_file = st.file_uploader("اختر ملف إكسيل أو CSV:", type=["xlsx", "xls", "csv"], key="hier_file_upload_v1_0")
            if up_file is not None:
                try:
                    df_up = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
                    st.write("📊 معاينة البيانات المرفوعة:", df_up.head(3))
                    if st.button("🚀 دمج وتحديث قاعدة بيانات الهيكل الإداري", use_container_width=True):
                        added_cnt = 0
                        with db() as c:
                            for _, r in df_up.iterrows():
                                gov = str(r.get("governorate", r.get("المحافظة", "الشرقية"))).strip()
                                auth = str(r.get("authority", r.get("الهيئة", "مديرية الشئون الصحية"))).strip()
                                cent = str(r.get("center", r.get("المركز", "أولاد صقر"))).strip()
                                adm = str(r.get("administration", r.get("الإدارة", "الإدارة الصحية بأولاد صقر"))).strip()
                                fac = str(r.get("facility_name", r.get("المنشأة", "وحدة صحية"))).strip()
                                
                                if fac:
                                    c.execute("INSERT INTO hierarchical_facilities(governorate,authority,center,administration,facility_name,created_at) VALUES(?,?,?,?,?,?)",
                                              (gov, auth, cent, adm, fac, now()))
                                    added_cnt += 1
                        st.success(f"🎉 تم إضافة وتحديث ({added_cnt}) سجل إداري بنجاح! واجهة الممتحن تم تحديثها فوراً."); st.balloons()
                except Exception as e:
                    st.error(f"خطأ في قراءة الملف: {e}")

        with tab_h3:
            st.markdown("#### 📋 استعراض وإدارة بيانات الهيكل الإداري:")
            hier_rows = get_hierarchical_data()
            if not hier_rows:
                st.info("لا توجد بيانات هيكل إداري مسجلة بعد.")
            else:
                facility_map = {f"ID ({row['id']}) - {row['governorate']} / {row['administration']} / {row['facility_name']}": row['id'] for row in hier_rows}
                with st.form("delete_single_hier_form"):
                    selected_item_to_delete = st.selectbox("اختر المنشأة أو العنصر الإداري للحذف:", list(facility_map.keys()))
                    c_del_btn, c_empty_all_btn = st.columns(2)
                    with c_del_btn:
                        single_del = st.form_submit_button("🗑️ حذف العنصر المختار نهائياً", use_container_width=True)
                    with c_empty_all_btn:
                        empty_all = st.form_submit_button("⚠️ تفريغ كافة الهيكل الإداري بالكامل", use_container_width=True)
                    
                    if single_del:
                        target_id = facility_map[selected_item_to_delete]
                        with db() as c:
                            c.execute("DELETE FROM hierarchical_facilities WHERE id=?", (target_id,))
                        st.success("✅ تم حذف العنصر الإداري بنجاح!"); st.rerun()
                    if empty_all:
                        with db() as c:
                            c.execute("DELETE FROM hierarchical_facilities")
                        st.success("✅ تم تفريغ جدول الهيكل الإداري بالكامل!"); st.rerun()

                df_hier = pd.DataFrame(hier_rows)
                df_hier.columns = ["ID", "المحافظة", "الهيئة", "المركز", "الإدارة", "المنشأة", "تاريخ الإنشاء"]
                st.dataframe(df_hier, use_container_width=True, hide_index=True)

    elif selected_menu == "🧑‍🔬 المتدربين والنماذج":
        st.subheader("🧑‍🔬 اعتماد المتدربين، تعديل النماذج، وحذف المتدربين نهائياً")
        with db() as c: all_tpls_map = {row["name"]: row["id"] for row in c.execute("SELECT id, name FROM exam_templates").fetchall()}
        tpl_names_list = list(all_tpls_map.keys()) if all_tpls_map else ["لا توجد نماذج اختبارات مسجلة"]

        with st.container(border=True):
            st.markdown("#### ⚡ تعميم نموذج اختبار واحد لجميع المتدربين دفعة واحدة:")
            with st.form("bulk_assign_form"):
                bulk_tpl_name = st.selectbox("اختر نموذج الاختبار لتعميمه:", tpl_names_list)
                if st.form_submit_button("🚀 تعميم نموذج الاختبار واعتماد الكل", use_container_width=True):
                    if all_tpls_map:
                        set_bulk_template_for_all(all_tpls_map[bulk_tpl_name])
                        st.success("✅ تم تعميم نموذج الاختبار واعتماد الجميع دفعة واحدة!"); st.rerun()
                    else: st.error("لا توجد نماذج اختبارات مسجلة.")

        sub_tabs = st.tabs(["الطلبات المعلقة (فردي)", "جميع المتدربين وإدارتهم/حذفهم"])
        with sub_tabs[0]:
            df_pend = trainees_df("pending")
            if df_pend.empty: st.info("لا توجد طلبات معلقة.")
            else:
                for _, r in df_pend.iterrows():
                    with st.container(border=True):
                        st.write(f"**ID:** {r['id']} | **الاسم:** {r['name']} | **الجهة:** {r['facility']}")
                        with st.form(f"approve_form_{r['id']}"):
                            chosen_tpl_name = st.selectbox(f"نموذج الاختبار المخصص:", tpl_names_list)
                            c1, c2 = st.columns(2)
                            with c1: app_btn = st.form_submit_button("✅ اعتماد وتثبيت", use_container_width=True)
                            with c2: rej_btn = st.form_submit_button("❌ رفض الطلب", use_container_width=True)
                            if app_btn and all_tpls_map:
                                set_trainee_status_and_template(int(r['id']), "approved", all_tpls_map[chosen_tpl_name])
                                st.success("✅ تم الاعتماد!"); st.rerun()
                            if rej_btn:
                                set_trainee_status_and_template(int(r['id']), "rejected", r.get('assigned_template_id'))
                                st.warning("تم الرفض."); st.rerun()
        with sub_tabs[1]:
            df_all_tr = trainees_df()
            if df_all_tr.empty: st.info("لا توجد بيانات متدربين مسجلة.")
            else:
                for _, tr_row in df_all_tr.iterrows():
                    with st.container(border=True):
                        st.write(f"**ID رقم:** {tr_row['id']} | **المتدرب:** {tr_row['name']} | **الجهة:** {tr_row['facility']} | **الحالة:** `{STATUS_AR.get(tr_row['status'], tr_row['status'])}`")
                        with st.form(f"update_tr_tpl_{tr_row['id']}"):
                            curr_id = tr_row['assigned_template_id']
                            curr_name = [k for k, v in all_tpls_map.items() if v == curr_id]
                            def_name = curr_name[0] if curr_name else (tpl_names_list[0] if tpl_names_list else "")
                            def_idx = tpl_names_list.index(def_name) if def_name in tpl_names_list else 0
                            new_chosen_tpl = st.selectbox(f"تعديل نموذج الاختبار للمتدرب ID: {tr_row['id']}", tpl_names_list, index=def_idx, key=f"sel_tr_{tr_row['id']}")
                            c_upd, c_del = st.columns(2)
                            with c_upd:
                                upd_btn = st.form_submit_button("💾 تحديث النموذج", use_container_width=True)
                            with c_del:
                                del_btn = st.form_submit_button("🗑️ حذف المتدرب نهائياً", use_container_width=True)
                            
                            if upd_btn:
                                if all_tpls_map:
                                    set_trainee_status_and_template(int(tr_row['id']), tr_row['status'], all_tpls_map[new_chosen_tpl])
                                    st.success("✅ تم التحديث بنجاح!"); st.rerun()
                            if del_btn:
                                with db() as c:
                                    c.execute("PRAGMA foreign_keys=OFF;")
                                    c.execute("DELETE FROM trainees WHERE id=?", (int(tr_row['id']),))
                                    c.execute("DELETE FROM exam_sessions WHERE trainee_id=?", (int(tr_row['id']),))
                                    c.execute("PRAGMA foreign_keys=ON;")
                                st.success(f"✅ تم حذف المتدرب ({tr_row['name']}) وسجلاته نهائياً!")
                                st.rerun()

    elif selected_menu == "🧠 بنك الأسئلة":
        st.subheader("🧠 بنك الأسئلة الشامل (استيراد وتصدير Excel)")
        tab_ex_1, tab_ex_2 = st.tabs(["📥 استيراد من إكسيل", "📤 تصدير إلى إكسيل"])
        with tab_ex_1:
            uploaded_excel = st.file_uploader("اختر ملف إكسيل الأسئلة:", type=["xlsx", "xls", "csv"], key="excel_uploader_v1_0")
            if uploaded_excel is not None:
                try:
                    df_import = pd.read_csv(uploaded_excel) if uploaded_excel.name.endswith('.csv') else pd.read_excel(uploaded_excel)
                    st.write("📊 معاينة البيانات:", df_import.head(3))
                    if st.button("🚀 تأكيد ودمج الأسئلة", use_container_width=True):
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
                        st.success(f"🎉 تم إضافة ({imported_count}) سؤالاً جديداً بنجاح!"); st.balloons()
                except Exception as e: st.error(f"خطأ: {e}")
        with tab_ex_2:
            with db() as c: df_bank = pd.read_sql_query("SELECT id, difficulty, category, question, options_json, answer FROM questions ORDER BY id ASC", c)
            if df_bank.empty: st.info("بنك الأسئلة فارغ.")
            else:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer: df_bank.to_excel(writer, index=False, sheet_name='QuestionBank')
                st.download_button("📥 تحميل إكسيل بنك الأسئلة (.xlsx)", data=output.getvalue(), file_name="question_bank.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                st.dataframe(df_bank, use_container_width=True, hide_index=True)

    elif selected_menu == "⚙ إدارة الأسئلة":
        st.subheader("⚙️ إدارة الأسئلة (إضافة، تعديل، وحذف)")
        sub_img_tabs = st.tabs(["➕ إضافة سؤال", "✏️ تعديل سؤال", "🗑 حذف سؤال"])
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
                c_text = st.text_area("نص السؤال التشخيصي:")
                c_diff = st.selectbox("الصعوبة:", ["سهل", "متوسط", "صعب"])
                uploaded_img = st.file_uploader("رفع صورة (اختياري):", type=["png", "jpg", "jpeg"])
                opt1, opt2 = st.text_input("الخيار 1:"), st.text_input("الخيار 2:")
                opt3, opt4 = st.text_input("الخيار 3:"), st.text_input("الخيار 4:")
                correct_ans_text = st.text_input("نص الإجابة الصحيحة:")
                if st.form_submit_button("حفظ وإضافة السؤال", use_container_width=True):
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
                        st.session_state.add_success_msg = "✅ تم إضافة السؤال بنجاح!"
                        st.session_state.form_key += 1
                        st.rerun()
        with sub_img_tabs[1]:
            with db() as c: all_questions = c.execute("SELECT id, question, category FROM questions ORDER BY id ASC").fetchall()
            if all_questions:
                q_options_map = {f"سؤال ({q['id']}) - [{q['category']}] : {q['question'][:40]}...": q['id'] for q in all_questions}
                selected_q_label = st.selectbox("اختر السؤال للتعديل:", list(q_options_map.keys()))
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
                        if st.form_submit_button("💾 حفظ التعديلات", use_container_width=True):
                            updated_opts = [o for o in [e_o1, e_o2, e_o3, e_o4] if o.strip() != ""]
                            if e_correct not in updated_opts: updated_opts.append(e_correct)
                            new_ans_idx = updated_opts.index(e_correct)
                            prefix_img = raw_q_db.split("\n\n")[0] + "\n\n" if "IMAGE:" in raw_q_db else ""
                            final_str = prefix_img + e_text
                            new_fp = hashlib.sha256((final_str + "|" + "|".join(updated_opts)).encode("utf-8")).hexdigest()
                            with db() as c:
                                c.execute("UPDATE questions SET difficulty=?, category=?, question=?, options_json=?, answer=?, fingerprint=? WHERE id=?",
                                          (e_diff, e_cat, final_str, json.dumps(updated_opts, ensure_ascii=False), new_ans_idx, new_fp, selected_q_id))
                            st.success("✅ تم التعديل بنجاح!"); st.rerun()
        with sub_img_tabs[2]:
            with db() as c: all_questions_del = c.execute("SELECT id, question, category FROM questions ORDER BY id ASC").fetchall()
            if all_questions_del:
                q_del_map = {f"سؤال رقم {q['id']} - {q['question'][:40]}": q['id'] for q in all_questions_del}
                selected_del_label = st.selectbox("اختر السؤال للحذف:", list(q_del_map.keys()))
                if st.button("🗑️ حذف السؤال نهائياً", use_container_width=True):
                    with db() as c: c.execute("DELETE FROM questions WHERE id=?", (q_del_map[selected_del_label],))
                    st.success("✅ تم الحذف بنجاح!"); st.rerun()

    elif selected_menu == "🧩 مواعيد الامتحانات":
        st.subheader("🧩 إنشاء نماذج الاختبارات وتحديد مواعيد الفتح والغلق للممتحنين")
        sub_tpl_mode = st.radio("القسم:", ["📋 عرض النماذج ومواعيدها والطباعة", "➕ إنشاء نموذج اختبار جديد وتحديد موعده", "⚙ تعديل موعد اختبار", "🗑 حذف نموذج اختبار"], horizontal=True)
        
        if sub_tpl_mode == "📋 عرض النماذج ومواعيدها والطباعة":
            with db() as c: tpls = c.execute("SELECT * FROM exam_templates ORDER BY id ASC").fetchall()
            if tpls:
                curr_sett_for_cert = get_print_settings()
                for t in tpls:
                    t_dict = dict(t)
                    num_q_display = "مفتوح (كامل البنك)" if int(t_dict.get('num_questions', 999999)) >= 999900 else t_dict.get('num_questions')
                    s_t = t_dict.get('start_time') or "غير محدد"
                    e_t = t_dict.get('end_time') or "غير محدد"
                    with st.container(border=True):
                        st.markdown(f"#### 🏷 نموذج اختبار ({t_dict.get('id')}): {t_dict.get('name')}")
                        st.write(f"🔹 **البدء:** {s_t.replace('T', ' الساعة ')} | 🔸 **النهاية:** {e_t.replace('T', ' الساعة ')} | 📝 **الأسئلة:** {num_q_display}")
                        
                        st.markdown("##### ✏️️ تخصيص وتعديل نصوص الشهادة والوثائق:")
                        with st.form(f"custom_print_form_{t_dict.get('id')}"):
                            edit_title = st.text_input("عنوان الشهادة أو المستند:", value=curr_sett_for_cert.get("default_cert_title", "شهادة اجتياز اختبار معتمدة"), key=f"t_{t_dict.get('id')}")
                            edit_notes = st.text_area("الملاحظات / التوجيهات الإضافية:", value=curr_sett_for_cert.get("default_cert_notes", " تقرير أداء المعامل والإشراف الفني المعتمد"), key=f"n_{t_dict.get('id')}")
                            
                            save_as_default = st.checkbox("💾 حفظ هذه التعديلات وتعميمها كإعداد افتراضي دائم لكل الشهادات والوثائق القادمة")
                            submitted_preview = st.form_submit_button("🔄 تحديث وعرض معاينة الطباعة", use_container_width=True)
                            
                            if submitted_preview and save_as_default:
                                with db() as c:
                                    c.execute("UPDATE print_settings SET default_cert_title=?, default_cert_notes=?", (edit_title, edit_notes))
                                st.success("✅ تم حفظ وتعميم هذه التعديلات لتصبح الإعداد الافتراضي للوثائق القادمة!")
                        
                        sample_sid = 1
                        with db() as c:
                            any_s = c.execute("SELECT id FROM exam_sessions WHERE template_id=? LIMIT 1", (t_dict.get('id'),)).fetchone()
                            if any_s: sample_sid = any_s["id"]
                        
                        custom_html_out = generate_customizable_certificate_html(sample_sid, edit_title, edit_notes)
                        render_print_button_only(custom_html_out, f"طباعة نموذج {t_dict.get('id')}")

        elif sub_tpl_mode == "➕ إنشاء نموذج اختبار جديد وتحديد موعده":
            categories_pool_opts = [
                "الاستراتيجية العامة ومكافحة البلهارسيا", "البلهارسيا", "علاج البلهارسيا", "الفاشيولا", "علاج الفاشيولا",
                "الهتروفيس", "التينيا", "هيمنولبس نانا", "الإسكارس", "الأنكلستوما", "الأكسيورس", "تركيورس تركيورا",
                "Strongyloides stercoralis", "Entamoeba histolytica", "Giardia lamblia", "الفحوص المعملية",
                "فحص البول", "فحص البراز", "طرق فحص البراز", "الترسيب", "التعويم", "اللطخة المباشرة",
                "التصفية الغشائية", "Kato-Katz", "تحضير العينات", "أسئلة الصور والأشكال"
            ]
            with st.form("create_template_schedule_form"):
                new_tpl_name = st.text_input("اسم نموذج الاختبار الجديد:")
                is_open_questions = st.checkbox("جعل عدد الأسئلة مفتوح وغير محدد (سحب كامل بنك الأسئلة المتاح)", value=True)
                new_tpl_num_q = st.number_input("عدد الأسئلة:", min_value=1, max_value=5000, value=50)
                new_tpl_duration = st.number_input("مدة الاختبار بالدقائق:", min_value=5, max_value=300, value=60)
                new_tpl_pass = st.slider("نسبة النجاح %:", min_value=30.0, max_value=95.0, value=60.0)
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    start_d = st.date_input("تاريخ البدء:", date.today())
                    start_t = st.time_input("وقت البدء:", datetime.now().time())
                with col_d2:
                    end_d = st.date_input("تاريخ النهاية:", date.today() + timedelta(days=1))
                    end_t = st.time_input("وقت النهاية:", datetime.now().time())

                new_tpl_cats = st.multiselect("الأقسام المشمولة:", categories_pool_opts)
                if st.form_submit_button("💾 حفظ وإنشاء النموذج والموعد", use_container_width=True):
                    if new_tpl_name.strip():
                        final_num_q = 999999 if is_open_questions else int(new_tpl_num_q)
                        start_dt_str = datetime.combine(start_d, start_t).isoformat(timespec="seconds")
                        end_dt_str = datetime.combine(end_d, end_t).isoformat(timespec="seconds")
                        with db() as c:
                            c.execute("INSERT INTO exam_templates(name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, start_time, end_time, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                                      (new_tpl_name.strip(), "اختبار مخصص للمالك", final_num_q, int(new_tpl_duration), float(new_tpl_pass), json.dumps(new_tpl_cats, ensure_ascii=False), start_dt_str, end_dt_str, now()))
                        st.success("✅ تم إنشاء نموذج الاختبار وموعده بنجاح!"); st.rerun()

        elif sub_tpl_mode == "⚙ تعديل موعد اختبار":
            with db() as c: tpls_mod = c.execute("SELECT id, name, start_time, end_time FROM exam_templates ORDER BY id ASC").fetchall()
            if tpls_mod:
                tpl_mod_map = {f"نموذج ({t['id']}) - {t['name']}": t['id'] for t in tpls_mod}
                with st.form("update_schedule_form"):
                    sel_mod_label = st.selectbox("اختر نموذج الاختبار لتعديل موعده:", list(tpl_mod_map.keys()))
                    chosen_id = tpl_mod_map[sel_mod_label]
                    col_u1, col_u2 = st.columns(2)
                    with col_u1:
                        new_sd = st.date_input("تاريخ البدء الجديد:", date.today())
                        new_st = st.time_input("وقت البدء الجديد:", datetime.now().time())
                    with col_u2:
                        new_ed = st.date_input("تاريخ النهاية الجديد:", date.today() + timedelta(days=1))
                        new_et = st.time_input("وقت النهاية الجديد:", datetime.now().time())
                    
                    if st.form_submit_button("💾 تحديث الموعد للممتحنين", use_container_width=True):
                        new_s_str = datetime.combine(new_sd, new_st).isoformat(timespec="seconds")
                        new_e_str = datetime.combine(new_ed, new_et).isoformat(timespec="seconds")
                        with db() as c:
                            c.execute("UPDATE exam_templates SET start_time=?, end_time=? WHERE id=?", (new_s_str, new_e_str, chosen_id))
                        st.success("✅ تم تحديث موعد الاختبار بنجاح!"); st.rerun()

        else:
            with db() as c: tpls_del = c.execute("SELECT id, name FROM exam_templates ORDER BY id ASC").fetchall()
            if tpls_del:
                tpl_map = {f"نموذج رقم {t['id']} - {t['name']}": t['id'] for t in tpls_del}
                with st.form("delete_template_form"):
                    selected_tpl_label = st.selectbox("اختر نموذج الاختبار للحذف:", list(tpl_map.keys()))
                    if st.form_submit_button("🗑 حذف نموذج الاختبار نهائياً", use_container_width=True):
                        with db() as c:
                            c.execute("PRAGMA foreign_keys=OFF;")
                            c.execute("DELETE FROM exam_templates WHERE id=?", (tpl_map[selected_tpl_label],))
                            c.execute("PRAGMA foreign_keys=ON;")
                        st.success("✅ تم الحذف بنجاح!"); st.rerun()

    elif selected_menu == "✍️ تسجيل نتيجة يدوي":
        st.subheader("✍️ تسجيل نتيجة متدرب يدوياً من الإدارة")
        hier_data = get_hierarchical_data()
        default_fac_str = hier_data[0]["facility_name"] if hier_data else "الإدارة الصحية بأولاد صقر"
        with st.form("manual_score_form"):
            m_trainee_name = st.text_input("اسم المتدرب الرباعي:")
            m_facility_name = st.text_input("جهة العمل أو المنشأة:", value=default_fac_str)
            with db() as c: all_tpls = c.execute("SELECT id, name FROM exam_templates").fetchall()
            tpl_choices = {row["name"]: row["id"] for row in all_tpls}
            selected_tpl_name = st.selectbox("اختر نموذج الاختبار المرتبط:", list(tpl_choices.keys()) if tpl_choices else ["افتراضي"])
            c1, c2 = st.columns(2)
            with c1: manual_score = st.number_input("الدرجة المحصلة:", min_value=0, max_value=9999, value=40)
            with c2: manual_max = st.number_input("الدرجة الكلية:", min_value=1, max_value=9999, value=50)
            manual_passed = st.radio("حالة الاجتياز:", ["اجتزت بنجاح", "لم تجتز الاختبار"])
            if st.form_submit_button("💾 حفظ وتسجيل النتيجة", use_container_width=True):
                if m_trainee_name:
                    with db() as c:
                        tpl_id_val = tpl_choices.get(selected_tpl_name) if tpl_choices else None
                        cur_tr = c.execute("INSERT INTO trainees(facility,name,phone,status,assigned_template_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                                           (normalize_text(m_facility_name), normalize_text(m_trainee_name), "0000000000", "completed", tpl_id_val, now(), now()))
                        new_tid = cur_tr.lastrowid
                        pct_val = (manual_score / manual_max) * 100 if manual_max > 0 else 0
                        passed_flag = 1 if manual_passed == "اجتزت بنجاح" else 0
                        cur_sess = c.execute("INSERT INTO exam_sessions(trainee_id,template_id,started_at,expires_at,submitted_at,status,score,max_score,percent,passed) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                             (new_tid, tpl_id_val, now(), now(), now(), "submitted", manual_score, manual_max, pct_val, passed_flag))
                        new_sid = cur_sess.lastrowid
                        cert_code = f"ELX-{new_sid:06d}"
                        c.execute("UPDATE exam_sessions SET certificate_id=? WHERE id=?", (cert_code, new_sid))
                    st.success(f"✅ تم التسجيل بنجاح برقم شهادة: **{cert_code}**")

    elif selected_menu == "📊 التقارير":
        st.subheader("📊 تقارير ومقارنة أداء المعامل")
        st.info("تقارير أداء المعامل ومقارنة الفترات متاحة للرصد والإشراف الفني.")

    elif selected_menu == "📈 خطط العمل":
        st.subheader("📈 خطط العمل التدريبية")
        st.info("قسم خطط العمل التدريبية الشهرية والسنوية جاهز لإصدار التقارير المعتمدة.")

    elif selected_menu == "💾 النسخ الاحتياطي":
        st.subheader("💾 النسخ الاحتياطي")
        with open(DB_PATH, "rb") as f: db_bytes = f.read()
        st.download_button("📥 تحميل قاعدة البيانات (.db)", data=db_bytes, file_name="database_backup_v1_0.db", mime="application/octet-stream", use_container_width=True)

    elif selected_menu == "👥 إدارة المستخدمين":
        st.subheader("👥 إدارة المستخدمين وتحديد الصلاحيات التفصيلية لكل مكون")
        
        tab_u1, tab_u2 = st.tabs(["➕ إضافة مستخدم جديد وتحديد صلاحياته", "⚙ تعديل صلاحيات وحذف المستخدمين"])
        
        with tab_u1:
            with st.form("add_user_form_v1_0"):
                new_u_name = st.text_input("اسم المستخدم الجديد:")
                new_u_pass = st.text_input("كلمة المرور:", type="password")
                new_u_role = st.selectbox("المسمى الوظيفي:", ["exam_manager", "viewer"], format_func=lambda x: ROLES[x])
                
                st.markdown("#### 🔐 تحديد صلاحيات الوصول لمكونات النظام:")
                selected_modules_checkboxes = {}
                for mod_key, mod_desc in ALL_MENU_MODULES.items():
                    selected_modules_checkboxes[mod_key] = st.checkbox(f"{mod_key} ({mod_desc})", value=True)
                
                if st.form_submit_button("💾 إنشاء المستخدم وحفظ الصلاحيات", use_container_width=True):
                    if new_u_name.strip() and new_u_pass.strip():
                        assigned_perms = [k for k, v in selected_modules_checkboxes.items() if v]
                        with db() as c:
                            try:
                                c.execute("INSERT INTO users(username, password_hash, role, permissions_json, active, created_at) VALUES(?,?,?,?,?,?)",
                                          (new_u_name.strip(), hash_password(new_u_pass), new_u_role, json.dumps(assigned_perms, ensure_ascii=False), 1, now()))
                                st.success("✅ تم إضافة المستخدم وصلاحياته بنجاح!")
                            except sqlite3.IntegrityError:
                                st.error("⚠️ اسم المستخدم مستخدم مسبقاً.")
                    else:
                        st.warning("الرجاء إدخال اسم المستخدم وكلمة المرور.")

        with tab_u2:
            with db() as c: all_users = c.execute("SELECT id, username, role, permissions_json FROM users WHERE role != 'admin'").fetchall()
            if not all_users:
                st.info("لا توجد حسابات مستخدمين فرعيين مسجلة.")
            else:
                user_map = {f"مستخدم: {u['username']} ({ROLES.get(u['role'], u['role'])})": u for u in all_users}
                sel_user_label = st.selectbox("اختر المستخدم للتعديل أو الحذف:", list(user_map.keys()))
                target_user = user_map[sel_user_label]
                
                try:
                    curr_user_perms = json.loads(target_user["permissions_json"]) if target_user["permissions_json"] else []
                except:
                    curr_user_perms = []

                with st.form(f"edit_user_perms_{target_user['id']}"):
                    st.markdown(f"#### ⚙️ تعديل صلاحيات المستخدم: `{target_user['username']}`")
                    edit_checkboxes = {}
                    for mod_key, mod_desc in ALL_MENU_MODULES.items():
                        is_checked = mod_key in curr_user_perms
                        edit_checkboxes[mod_key] = st.checkbox(f"{mod_key} ({mod_desc})", value=is_checked, key=f"mod_chk_{target_user['id']}_{mod_key}")
                    
                    c_save, c_del = st.columns(2)
                    with c_save:
                        save_btn = st.form_submit_button("💾 حفظ الصلاحيات الجديدة", use_container_width=True)
                    with c_del:
                        del_btn = st.form_submit_button("🗑️ حذف المستخدم نهائياً", use_container_width=True)
                    
                    if save_btn:
                        new_assigned = [k for k, v in edit_checkboxes.items() if v]
                        with db() as c:
                            c.execute("UPDATE users SET permissions_json=? WHERE id=?", (json.dumps(new_assigned, ensure_ascii=False), target_user["id"]))
                        st.success("✅ تم تحديث صلاحيات المستخدم بنجاح!"); st.rerun()
                    if del_btn:
                        with db() as c:
                            c.execute("DELETE FROM users WHERE id=?", (target_user["id"],))
                        st.success(f"✅ تم حذف المستخدم ({target_user['username']}) بنجاح!"); st.rerun()

    elif selected_menu == "🧾 سجل التدقيق":
        st.subheader("🧾 سجل التدقيق")
        with db() as c: df_audit = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100", c)
        st.dataframe(df_audit, use_container_width=True, hide_index=True)

def trainee_portal():
    with db() as c: tr = c.execute("SELECT * FROM trainees WHERE id=?", (st.session_state.trainee_id,)).fetchone()
    if not tr: st.session_state.trainee_id = None; st.rerun()
    header()

    assigned_tpl_id = tr["assigned_template_id"]
    with db() as c: matching_template = c.execute("SELECT * FROM exam_templates WHERE id=?", (assigned_tpl_id,)).fetchone() if assigned_tpl_id else None

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
        
        st.markdown(f'<div class="card"><h3>مرحباً بك، {esc(tr["name"])}</h3><p>الجهة: {esc(tr["facility"])} | الاختبار المخصص لك: <b>{esc(tpl_name_str)}</b></p></div>', unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("#### 📅 موعد وتوقيت الاختبار المجدول:")
            format_s = start_t.replace("T", " الساعة ")
            format_e = end_t.replace("T", " الساعة ")
            col_s1, col_s2 = st.columns(2)
            with col_s1: st.markdown(f"🟢 **وقت البدء الرسمي:**\n`{format_s}`")
            with col_s2: st.markdown(f"🔴 **وقت النهاية الرسمي:**\n`{format_e}`")

        st.success(f"🟢 **الاختبار مفتوح ومتاح الآن للتنفيذ!**")
        if st.button("🚀 بدء الاختبار المخصص الآن", use_container_width=True):
            try:
                sid = start_session(tr["id"], matching_template["id"])
                st.session_state.exam_session_id = sid
                st.rerun()
            except Exception as e: st.error(str(e))

    st.markdown("<br>", unsafe_allow_html=True)
    col_space1, col_btn, col_space2 = st.columns([1, 2, 1])
    with col_btn:
        if st.button("🚪 تسجيل الخروج من الحساب", use_container_width=True):
            st.session_state.trainee_id = None
            st.rerun()

def exam_interface(session_id):
    with db() as c:
        session = c.execute("SELECT * FROM exam_sessions WHERE id=?", (session_id,)).fetchone()
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
if st.session_state.get("exam_session_id"):
    exam_interface(st.session_state.exam_session_id)
elif st.session_state.trainee_id and not st.session_state.logged_in:
    if st.session_state.get("last_result_id"):
        sid = st.session_state.last_result_id
        header()
        st.success("تم تسليم الاختبار بنجاح ونتيجتك جاهزة!")
        
        curr_sett = get_print_settings()
        with st.form("custom_trainee_cert_form"):
            st.markdown("### ✏️ تخصيص وتعديل نصوص الشهادة قبل الطباعة:")
            c_title = st.text_input("عنوان الشهادة الرئيسي:", value=curr_sett.get("default_cert_title", "شهادة اجتياز اختبار معتمدة"))
            c_notes = st.text_area("الملاحظات / التوجيهات الإضافية:", value=curr_sett.get("default_cert_notes", "تقرير أداء المعامل والإشراف الفني المعتمد"))
            save_default_flag = st.checkbox("💾 تعميم هذه التعديلات كإعداد افتراضي دائم")
            
            if st.form_submit_button("🔄 تحديث وحفظ التعديلات", use_container_width=True):
                if save_default_flag:
                    with db() as c:
                        c.execute("UPDATE print_settings SET default_cert_title=?, default_cert_notes=?", (c_title, c_notes))
                    st.success("✅ تم تحديث وتعميم النصوص بنجاح!")
                else:
                    st.success("✅ تم تحديث المعاينة للطباعة الحالية فقط.")
        
        cert_html = generate_customizable_certificate_html(sid, c_title, c_notes)
        st.download_button("📥 تحميل شهادة الاجتياز المعتمدة .html", data=cert_html.encode("utf-8"), file_name=f"certificate_{sid}.html", mime="text/html")
        render_print_button_only(cert_html, f"الشهادة المعتمدة {sid}")
        if st.button("العودة للرئيسية"): st.session_state.trainee_id = None; st.session_state.last_result_id = None; st.rerun()
    else:
        trainee_portal()
elif not st.session_state.logged_in:
    login_portal()
else:
    admin_dashboard()
