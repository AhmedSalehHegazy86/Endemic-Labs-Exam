import os, io, re, ast, json, html, sqlite3, hashlib, secrets, random
from datetime import datetime, timedelta, date
from contextlib import contextmanager

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# 1) إعدادات التطبيق الأساسية (إلغاء الشريط الجانبي تماماً)
# ============================================================
st.set_page_config(
    page_title="منصة اختبارات معامل المتوطنة - Professional v38.0",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "endemic_labs_exam_v38_0.db")
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

LOGO_BASE64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="

# ============================================================
# 2) حقن التنسيقات (CSS) وتثبيت الألوان والشاشات ومنع التباين
# ============================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

html, body, [class*="css"] {{
    direction: rtl;
    text-align: right;
    font-family: 'Cairo', 'Tahoma', sans-serif !important;
    color-scheme: light !important;
}}

.stApp {{
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 45%, #bbf7d0 100%) !important;
    background-attachment: fixed !important;
}}

.block-container {{
    max-width: 1100px !important;
    margin: auto !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
    padding-top: 5.5rem !important;
    padding-bottom: 6rem !important;
}}

.hero {{
    background: linear-gradient(90deg, #064e3b, #065f46, #047857) !important;
    color: #ffffff !important;
    padding: 18px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    margin-bottom: 30px;
}}

.card, .question {{
    background: #ffffff !important;
    color: #111827 !important;
    padding: 18px 24px;
    border-radius: 10px;
    margin-bottom: 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    border-right: 6px solid #059669 !important;
}}

.metric {{
    background: #ffffff !important;
    padding: 16px;
    border-radius: 10px;
    text-align: center;
    border-top: 4px solid #059669 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}}

.metric .v {{
    font-size: 24px;
    font-weight: 800;
    color: #065f46 !important;
}}

.metric .l {{
    color: #4b5563 !important;
    font-weight: 700;
    font-size: 13px;
}}

[data-testid="stSidebar"], [data-testid="collapsedControl"] {{
    display: none !important;
}}

.print-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 18px 24px;
    margin-bottom: 35px;
    border-bottom: 2px solid #006633;
    background-color: #ffffff !important;
    border-radius: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}}

.print-logo {{
    width: 75px;
    height: 75px;
    object-fit: contain;
}}

.header-text {{
    font-size: 15px;
    font-weight: bold;
    color: #2c3e50 !important;
    text-align: right;
    line-height: 1.6;
}}

@media print {{
    #MainMenu, header, footer, .stButton {{ visibility: hidden; }}
    body {{ direction: rtl; }}
    .print-header {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 20px;
        border-bottom: 2px solid #006633;
        background: white;
        z-index: 9999;
    }}
}}

.stButton>button {{
    background-color: #059669 !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    font-weight: 800 !important;
    min-height: 40px !important;
    padding: 6px 18px;
    border: none !important;
    transition: all 0.2s ease;
}}

.stButton>button:hover {{
    background-color: #047857 !important;
    color: #ffffff !important;
}}

input, select, textarea {{
    background-color: #ffffff !important;
    color: #111827 !important;
    border: 1px solid #cbd5e1 !important;
}}
</style>

<div class="print-header">
    <div class="header-text">
        جمهورية مصر العربية - وزارة الصحة والسكان<br>
        مديرية الشئون الصحية بالشرقية<br>
        الإدارة الصحية بأولاد صقر
    </div>
    <img src="{LOGO_BASE64}" class="print-logo" alt="Logo">
</div>
""", unsafe_allow_html=True)

# ============================================================
# 3) دوال النظام وقاعدة البيانات وبنك الأسئلة
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
        CREATE TABLE IF NOT EXISTS facilities_list (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
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
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT,
            action TEXT NOT NULL,
            entity TEXT,
            details TEXT,
            created_at TEXT NOT NULL
        );
        """)

        cursor = c.execute("PRAGMA table_info(trainees)")
        columns = [col[1] for col in cursor.fetchall()]
        if "assigned_template_id" not in columns:
            c.execute("ALTER TABLE trainees ADD COLUMN assigned_template_id INTEGER")

        cursor_tpl = c.execute("PRAGMA table_info(exam_templates)")
        tpl_columns = [col[1] for col in cursor_tpl.fetchall()]
        if "num_questions" not in tpl_columns:
            c.execute("ALTER TABLE exam_templates ADD COLUMN num_questions INTEGER NOT NULL DEFAULT 999999")

def get_facilities():
    with db() as c:
        rows = c.execute("SELECT id, name FROM facilities_list ORDER BY id ASC").fetchall()
        return [{"id": r["id"], "name": r["name"]} for r in rows] if rows else []

def add_facility_manual_db(fac_id, fac_name):
    norm = normalize_text(fac_name)
    if not norm: return False, "اسم المنشأة فارغ."
    with db() as c:
        try:
            c.execute("INSERT INTO facilities_list(id, name, created_at) VALUES(?, ?, ?)", (int(fac_id), norm, now()))
            return True, "تم الإضافة بنجاح"
        except sqlite3.IntegrityError:
            return False, "رقم المعرف (ID) أو اسم المنشأة مستخدم مسبقاً."

def delete_facility_db_by_id(fac_id):
    with db() as c:
        c.execute("DELETE FROM facilities_list WHERE id=?", (fac_id,))

def reorder_template_ids():
    with db() as c:
        c.execute("PRAGMA foreign_keys=OFF;")
        rows = c.execute("SELECT * FROM exam_templates ORDER BY id ASC").fetchall()
        
        id_mapping = {}
        for idx, r in enumerate(rows, start=1):
            id_mapping[r["id"]] = idx

        c.execute("DROP TABLE IF EXISTS exam_templates_temp")
        c.execute("""
            CREATE TABLE exam_templates_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                exam_type TEXT NOT NULL DEFAULT 'اختبار مخصص للمالك',
                num_questions INTEGER NOT NULL DEFAULT 999999,
                duration_minutes INTEGER NOT NULL DEFAULT 60,
                pass_percent REAL NOT NULL DEFAULT 60,
                categories_json TEXT NOT NULL DEFAULT '[]',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)
        
        for idx, r in enumerate(rows, start=1):
            num_q_val = dict(r).get("num_questions", 999999)
            c.execute("""
                INSERT INTO exam_templates_temp(id, name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, active, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (idx, r["name"], r["exam_type"], num_q_val, r["duration_minutes"], r["pass_percent"], r["categories_json"], r["active"], r["created_at"]))
        
        c.execute("DROP TABLE exam_templates")
        c.execute("ALTER TABLE exam_templates_temp RENAME TO exam_templates")
        
        for old_id, new_id in id_mapping.items():
            if old_id != new_id:
                c.execute("UPDATE exam_sessions SET template_id=? WHERE template_id=?", (new_id, old_id))
                c.execute("UPDATE trainees SET assigned_template_id=? WHERE assigned_template_id=?", (new_id, old_id))
                
        c.execute("PRAGMA foreign_keys=ON;")

def delete_template_db_by_id(tpl_id):
    with db() as c:
        c.execute("PRAGMA foreign_keys=OFF;")
        c.execute("DELETE FROM exam_templates WHERE id=?", (tpl_id,))
        c.execute("PRAGMA foreign_keys=ON;")
    reorder_template_ids()

def reorder_question_ids():
    with db() as c:
        c.execute("PRAGMA foreign_keys=OFF;")
        rows = c.execute("SELECT * FROM questions ORDER BY id ASC").fetchall()
        
        id_mapping = {}
        for idx, r in enumerate(rows, start=1):
            id_mapping[r["id"]] = idx

        c.execute("DROP TABLE IF EXISTS questions_temp")
        c.execute("""
            CREATE TABLE questions_temp (
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
            )
        """)
        
        for idx, r in enumerate(rows, start=1):
            c.execute("""
                INSERT INTO questions_temp(id, difficulty, category, question, options_json, answer, explanation, reference, active, fingerprint, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (idx, r["difficulty"], r["category"], r["question"], r["options_json"], r["answer"], r["explanation"], r["reference"], r["active"], r["fingerprint"], r["created_at"]))
        
        c.execute("DROP TABLE questions")
        c.execute("ALTER TABLE questions_temp RENAME TO questions")
        
        for old_id, new_id in id_mapping.items():
            if old_id != new_id:
                c.execute("UPDATE exam_questions SET question_id=? WHERE question_id=?", (new_id, old_id))
                
        c.execute("PRAGMA foreign_keys=ON;")

def ensure_admin():
    with db() as c:
        u = c.execute("SELECT * FROM users WHERE role='admin'").fetchone()
        if not u:
            c.execute("INSERT OR REPLACE INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,?,?)",
                      ("admin", hash_password("admin"), "admin", 1, now()))
        else:
            c.execute("UPDATE users SET password_hash=? WHERE role='admin'", (hash_password("admin"),))

init_db()
reorder_question_ids()
reorder_template_ids()
ensure_admin()

def audit(action, entity=None, details=None):
    actor = st.session_state.get("username") or st.session_state.get("trainee_name") or "system"
    with db() as c:
        c.execute("INSERT INTO audit_logs(actor,action,entity,details,created_at) VALUES(?,?,?,?,?)",
                  (actor, action, entity, json.dumps(details, ensure_ascii=False) if isinstance(details, dict) else details, now()))

# ============================================================
# 4) دوال إدارة المتدربين والامتحانات ومحاضر التدريب والتقارير
# ============================================================
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
    audit("create_trainee", "trainee", {"id": tid, "name": name, "assigned_template_id": assigned_template_id})
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
    audit("update_trainee", "trainee", {"id": tid, "status": status, "assigned_template_id": assigned_template_id})

def set_bulk_template_for_all(assigned_template_id):
    with db() as c:
        c.execute("""UPDATE trainees 
                     SET assigned_template_id=?, 
                         status=CASE WHEN status='pending' THEN 'approved' ELSE status END,
                         approved_at=CASE WHEN status='pending' THEN ? ELSE approved_at END,
                         updated_at=? """,
                  (assigned_template_id, now(), now()))
    audit("bulk_assign_template", "trainees", {"assigned_template_id": assigned_template_id})

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
        today_start = today_date() + "T00:00:00"
        completed_today = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND template_id=? AND status='submitted' AND started_at>=?",
                                    (trainee_id, template_id, today_start)).fetchone()
        if completed_today:
            raise ValueError("عذراً، لا يمكنك أداء هذا الاختبار أكثر من مرة في نفس اليوم.")
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        if not t: raise ValueError("قالب الاختبار غير موجود. يرجى مراجعة إدارة المنصة.")
        active = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND status='active'", (trainee_id,)).fetchone()
        if active: raise ValueError("لديك اختبار نشط بالفعل.")

    qs = choose_questions(t)
    started = datetime.now()
    t_dict = dict(t)
    expires = started + timedelta(minutes=int(t_dict.get("duration_minutes", 60)))
    
    with db() as c:
        cur = c.execute("INSERT INTO exam_sessions(trainee_id,template_id,started_at,expires_at,status) VALUES(?,?,?,?,?)",
                        (trainee_id, template_id, started.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds"), "active"))
        sid = cur.lastrowid
        for pos, q in enumerate(qs):
            raw_opts = q["options_json"]
            try:
                opts_parsed = json.loads(raw_opts)
                if not isinstance(opts_parsed, list):
                    opts_parsed = ["نعم", "لا"]
            except:
                opts_parsed = ["نعم", "لا"]
            order = list(range(len(opts_parsed)))
            random.shuffle(order)
            c.execute("INSERT INTO exam_questions(session_id,question_id,position,option_order_json) VALUES(?,?,?,?)",
                      (sid, q["id"], pos, json.dumps(order)))
        c.execute("UPDATE trainees SET status='active', updated_at=? WHERE id=?", (now(), trainee_id))
    audit("start_exam", "session", {"session_id": sid, "trainee_id": trainee_id, "template_id": template_id})
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

# ============================================================
# 5) دوال التصدير والشهادات
# ============================================================
def generate_compact_certificate_html(sid, custom_notes=""):
    with db() as c:
        r = c.execute("""SELECT s.*, t.name trainee_name, t.facility, e.name template_name 
                         FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?""", (sid,)).fetchone()
    if not r: return ""
    status_text = "اجتزت بنجاح" if r["passed"] else "لم تجتز الاختبار"
    
    score_val = r["score"] if r["score"] is not None else 0
    max_score_val = r["max_score"] if r["max_score"] is not None else 0
    percent_val = r["percent"] if r["percent"] is not None else 0.0
    tpl_name = r["template_name"] if r["template_name"] else "اختبار تقييمي معتمد"
    
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 landscape; margin: 0; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #fdfbf7; margin: 0; padding: 0; width: 297mm; height: 210mm; display: flex; justify-content: center; align-items: center; direction: rtl; -webkit-print-color-adjust: exact; }}
            .cert-wrapper {{ 
                width: 282mm; 
                height: 195mm; 
                border: 12px double #059669; 
                border-radius: 20px; 
                background: #ffffff; 
                display: flex; 
                flex-direction: column; 
                justify-content: space-between; 
                align-items: center; 
                padding: 16mm 22mm; 
                box-sizing: border-box; 
                position: relative; 
                box-shadow: 0 6px 20px rgba(0,0,0,0.06); 
            }}
            .header-top {{ position: absolute; top: 12mm; left: 18mm; text-align: left; }}
            .header-top img {{ width: 65px; height: 65px; object-fit: contain; }}
            .header-right {{ position: absolute; top: 12mm; right: 18mm; text-align: right; font-size: 10.5pt; font-weight: bold; color: #065f46; line-height: 1.4; }}
            .cert-body {{ text-align: center; margin-top: 14mm; width: 100%; }}
            h2 {{ color: #047857; font-size: 19pt; margin-bottom: 4px; }}
            h1 {{ color: #065f46; font-size: 28pt; margin: 10px 0; font-weight: 900; }}
            p {{ font-size: 12pt; line-height: 1.7; color: #1f2937; }}
            .notes-box {{ background: #f0fdf4; border: 1px dashed #059669; padding: 8px 16px; margin: 10px auto; width: 85%; border-radius: 8px; font-weight: bold; color: #065f46; font-size: 10.5pt; }}
            .footer-bottom {{ width: 100%; display: flex; justify-content: space-between; font-size: 10pt; font-weight: bold; text-align: center; border-top: 2px dashed #059669; padding-top: 12px; margin-top: 6mm; }}
        </style>
    </head>
    <body>
        <div class="cert-wrapper">
            <div class="header-right">
                جمهورية مصر العربية - وزارة الصحة والسكان<br>
                مديرية الشئون الصحية بالشرقية<br>
                الإدارة الصحية بأولاد صقر
            </div>
            <div class="header-top">
                <img src="{LOGO_BASE64}" alt="Logo">
            </div>
            <div class="cert-body">
                <h2>شهادة اجتياز اختبار معتمدة</h2>
                <hr style="width: 45%; border: 1px solid #059669; margin: 6px auto;">
                <h1>{esc(r["trainee_name"])}</h1>
                <p>
                    الجهة: <b>{esc(r["facility"])}</b> &nbsp;|&nbsp; الاختبار: <b>{esc(tpl_name)}</b><br>
                    النتيجة: <b>{score_val} / {max_score_val} ({percent_val:.1f}%)</b> &nbsp;|&nbsp; 
                    الحالة: <b style="color: {'green' if r['passed'] else 'red'};">{status_text}</b><br>
                    رقم التحقق والشهادة: <code>{r["certificate_id"]}</code>
                </p>
                {f'<div class="notes-box">ملاحظات إضافية: {esc(custom_notes)}</div>' if custom_notes else ''}
            </div>
            <div class="footer-bottom">
                <div>مسؤول التدريب</div>
                <div>رئيس قسم المعامل</div>
                <div>مدير المتوطنة</div>
                <div>يعتمد مدير عام الإدارة</div>
            </div>
        </div>
    </body>
    </html>
    """

def generate_training_minutes_html(template_id, training_date, facility_name, custom_notes=""):
    with db() as c:
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
    if not t: return "<p>القالب غير موجود</p>"
    t_dict = dict(t)
    cats = json.loads(t_dict.get("categories_json", "[]")) if t_dict.get("categories_json") else ["الاستراتيجية العامة", "الفحوص المعملية"]
    bullets_html = "".join([f"<li>{idx}. محور تدريبي: <b>{esc(cat)}</b> وتطبيقاته العملية.</li>" for idx, cat in enumerate(cats[:5], start=1)])
    formatted_date = training_date.strftime('%Y/%m/%d')
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; direction: rtl; text-align: right; background: #fff; padding: 25px; color: #111; line-height: 1.6; }}
            .minutes-box {{ border: 3px solid #059669; padding: 30px; border-radius: 12px; max-width: 800px; margin: auto; background: #fffdf9; }}
            .header-top {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #065f46; padding-bottom: 12px; margin-bottom: 20px; }}
            .notes-box {{ background: #f0fdf4; border: 1px dashed #059669; padding: 10px; margin-top: 15px; font-weight: bold; color: #065f46; }}
            .signatures {{ margin-top: 45px; display: flex; justify-content: space-between; font-size: 10pt; font-weight: bold; text-align: center; border-top: 1px dashed #059669; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="minutes-box">
            <div class="header-top">
                <div>
                    <h2>محضر تدريب معتمد - وحدة معامل المتوطنة</h2>
                    <h3>الإدارة الصحية بأولاد صقر • القالب: {esc(t_dict.get('name', ''))}</h3>
                </div>
                <img src="{LOGO_BASE64}" style="width:70px; height:70px; object-fit:contain;" alt="Logo">
            </div>
            <p>أنه في يوم الموافق <b>{formatted_date}</b>، تم تدريب أخصائي وفني المختبرات بمنشأة <b>{esc(facility_name)}</b> على المحاور الآتية:</p>
            <ul>{bullets_html}</ul>
            {f'<div class="notes-box">ملاحظات تدوين البرنامج: {esc(custom_notes)}</div>' if custom_notes else ''}
            <div class="signatures">
                <div>مسؤول التدريب</div>
                <div>رئيس قسم المعامل</div>
                <div>مدير المتوطنة</div>
                <div>يعتمد مدير عام الإدارة</div>
            </div>
        </div>
    </body>
    </html>
    """

def generate_report_html_document(df, title_desc, custom_notes=""):
    html_doc = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; direction: rtl; text-align: right; background: #fff; padding: 15px; color: #111; }}
            .header-top {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #065f46; padding-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 10pt; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: right; }}
            th {{ background-color: #065f46; color: #fff; }}
            .notes-box {{ background: #f0fdf4; border: 1px dashed #059669; padding: 8px; margin-bottom: 10px; font-weight: bold; color: #065f46; }}
            .footer {{ margin-top: 30px; display: flex; justify-content: space-between; font-size: 10pt; font-weight: bold; text-align: center; border-top: 2px dashed #065f46; padding-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="header-top">
            <div>
                <h2>🔬 تقرير أداء متدربي معامل المتوطنة</h2>
                <p>{title_desc}</p>
            </div>
            <img src="{LOGO_BASE64}" style="width:65px; height:65px; object-fit:contain;" alt="Logo">
        </div>
        {f'<div class="notes-box">ملاحظات التقرير الشامل: {esc(custom_notes)}</div>' if custom_notes else ''}
        <table>
            <thead>
                <tr>
                    <th>رقم الجلسة</th>
                    <th>اسم المتدرب</th>
                    <th>جهة العمل</th>
                    <th>اسم الاختبار</th>
                    <th>تصنيف التقييم</th>
                    <th>الدرجة</th>
                    <th>النسبة %</th>
                    <th>الحالة</th>
                    <th>تاريخ التسليم</th>
                </tr>
            </thead>
            <tbody>
    """
    for _, row in df.iterrows():
        html_doc += f"""
                <tr>
                    <td>{row['رقم الجلسة']}</td>
                    <td>{esc(row['اسم المتدرب'])}</td>
                    <td>{esc(row['جهة العمل'])}</td>
                    <td>{esc(row['اسم الاختبار'])}</td>
                    <td>{esc(row['تصنيف التقييم'])}</td>
                    <td>{row['الدرجة']} / {row['الدرجة الكلية']}</td>
                    <td>{row['النسبة المئوية %']:.1f}%</td>
                    <td>{esc(row['حالة الاجتياز'])}</td>
                    <td>{esc(row['تاريخ ووقت التسليم'])}</td>
                </tr>
        """
    html_doc += """
            </tbody>
        </table>
        <div class="footer">
            <div>مسؤول التدريب</div>
            <div>رئيس قسم المعامل</div>
            <div>مدير المتوطنة</div>
            <div>يعتمد مدير عام الإدارة</div>
        </div>
    </body>
    </html>
    """
    return html_doc

def generate_compact_exam_html(template_id, custom_notes=""):
    with db() as c:
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        qs = choose_questions(t) if t else []
    if not t: return "<p>القالب غير موجود</p>"
    t_dict = dict(t)
    html_out = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 8mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; direction: rtl; text-align: right; background: #fff; padding: 5px; font-size: 8pt; color: #111; line-height: 1.2; }}
            .top-right-header {{ float: right; text-align: right; font-size: 9pt; font-weight: bold; color: #065f46; line-height: 1.2; }}
            .top-left-logo {{ float: left; text-align: left; }}
            .top-left-logo img {{ width: 55px; height: 55px; object-fit: contain; }}
            .exam-title-area {{ text-align: center; clear: both; border-bottom: 2px solid #065f46; padding-bottom: 5px; margin-bottom: 8mm; }}
            .exam-container {{ column-count: 2; column-gap: 10mm; }}
            .q-box {{ margin-bottom: 6mm; page-break-inside: avoid; border: 1px solid #94a3b8; padding: 6px; border-radius: 4px; background: #fff; }}
            .notes-box {{ background: #f0fdf4; border: 1px dashed #059669; padding: 6px; margin-bottom: 8mm; font-size: 7.5pt; font-weight: bold; color: #065f46; }}
            .exam-footer {{ margin-top: 15px; display: flex; justify-content: space-between; font-size: 8pt; font-weight: bold; text-align: center; border-top: 1px dashed #059669; padding-top: 8px; page-break-inside: avoid; }}
        </style>
    </head>
    <body>
        <div class="top-left-logo">
            <img src="{LOGO_BASE64}" alt="Logo">
        </div>
        <div class="top-right-header">
            الإدارة الصحية بأولاد صقر<br>
            قسم المتوطنة وقسم المعامل<br>
            وحدة تدريب معامل المتوطنة
        </div>
        <div class="exam-title-area">
            <h2>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h2>
            <h3>نموذج امتحان: {esc(t_dict.get('name', ''))}</h3>
            <p>المدة: {t_dict.get('duration_minutes', 60)}د | عدد الأسئلة: {len(qs)} | اسم المتدرب: ........................ | الجهة: ........................</p>
        </div>
        {f'<div class="notes-box">ملاحظات الاختبار: {esc(custom_notes)}</div>' if custom_notes else ''}
        <div class="exam-container">
    """
    for idx, q in enumerate(qs):
        try:
            opts = json.loads(q["options_json"])
            if not isinstance(opts, list):
                opts = ["نعم", "لا"]
        except:
            opts = ["نعم", "لا"]
        q_raw = q["question"]
        if q_raw.startswith("IMAGE:"):
            parts = q_raw.split("\n\n", 1)
            img_data = parts[0].replace("IMAGE:", "").strip()
            actual_q = parts[1] if len(parts) > 1 else "تعرف على الصورة المجهرية وحدد الإجابة الصحيحة:"
            html_out += f"""
            <div class='q-box'>
                <div style='font-weight: bold; font-size: 8pt; margin-bottom:3px;'>س {idx+1}: {esc(actual_q)}</div>
                <div style='text-align: center;'><img src='{img_data}' style='max-width:65px; height:auto; border:1px solid #ccc;' crossorigin='anonymous'></div>
                <ul style='list-style-type: none; padding-right: 10px; margin: 2px 0;'>
            """
        else:
            cleaned_q = clean_question_text(q_raw)
            html_out += f"<div class='q-box'><b>س {idx+1}: {cleaned_q}</b><ul style='list-style-type: none; padding-right: 10px; margin: 2px 0;'>"
        for opt in opts:
            html_out += f"<li style='font-size: 7.5pt; margin-bottom: 2px;'>[ &nbsp; ] {esc(opt)}</li>"
        html_out += "</ul></div>"
    html_out += f"""
        </div>
        <div class="exam-footer">
            <div>مسؤول التدريب</div>
            <div>رئيس قسم المعامل</div>
            <div>مدير المتوطنة</div>
            <div>يعتمد مدير عام الإدارة</div>
        </div>
    </body></html>
    """
    return html_out

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
# 6) المسارات والشاشات
# ============================================================
for k, v in {"logged_in": False, "username": "", "role": "", "trainee_id": None, "trainee_name": "", "exam_session_id": None, "last_result_id": None, "form_key": 0, "edit_success_msg": "", "add_success_msg": "", "del_success_msg": "", "tpl_success_msg": ""}.items():
    if k not in st.session_state: st.session_state[k] = v

def header():
    st.markdown('<div class="hero"><h1>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h1><div>Professional v38.0 OPEN-QUESTIONS • الإدارة الصحية بأولاد صقر</div></div>', unsafe_allow_html=True)

def login_portal():
    header()
    st.markdown("<b>تسجيل وإرسال طلب المتدربين</b>", unsafe_allow_html=True)
    with st.form("trainee_request"):
        facilities_list = [f["name"] for f in get_facilities()]
        facility = st.selectbox("اختر جهة العمل أو المنشأة التابع لها:", facilities_list if facilities_list else ["لا توجد منشآت مسجلة يرجى إضافتها من لوحة الإدارة"])
        name = st.text_input("الاسم الرباعي")
        phone = st.text_input("رقم الهاتف")
        
        with db() as c:
            all_tpls_opts = {row["name"]: row["id"] for row in c.execute("SELECT id, name FROM exam_templates").fetchall()}
        
        tpl_choices_list = list(all_tpls_opts.keys()) if all_tpls_opts else ["لا توجد قوالب امتحانات مسجلة"]
        selected_req_tpl_name = st.selectbox("اختر القالب المبدئي:", tpl_choices_list)
        
        if st.form_submit_button("إرسال الطلب والدخول للمتدرب", use_container_width=True):
            if facility.strip() and name.strip() and facilities_list and all_tpls_opts:
                assigned_tpl_id = all_tpls_opts.get(selected_req_tpl_name)
                existing = trainee_by_credentials(name, facility)
                if existing:
                    st.session_state.trainee_id = existing["id"]
                    st.session_state.trainee_name = existing["name"]
                    st.success("تم التعرف على حسابك! جاري الدخول...")
                    st.rerun()
                else:
                    tid = create_trainee(facility, name, phone, assigned_tpl_id)
                    st.success(f"✅ تم تسجيل بياناتك بنجاح! رقم التسجيل (ID) الخاص بك هو: **{tid}**")
            else:
                st.warning("الرجاء التأكد من إضافة منشآت وإنشاء قوالب امتحانات أولاً.")

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
                    audit("login", "user", {"username": user["username"]})
                    st.rerun()
                else:
                    st.error("بيانات الدخول الإدارية غير صحيحة.")

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

    menu_options = [
        "📊 لوحة التحكم",
        "🏥 إدارة المنشآت",
        "🧑‍🔬 اعتماد المتدربين وتحديد القالب",
        "🧠 بنك الأسئلة الشامل (استيراد/تصدير Excel)",
        "⚙ إدارة الأسئلة",
        "🧩 قوالب ومحاضر التدريب (للمالك فقط)",
        "✍️ تسجيل نتيجة يدوي",
        "📊 التقارير المتقدمة والتصدير",
        "💾 النسخ الاحتياطي"
    ]
    if st.session_state.role == "admin":
        menu_options += ["👥 إدارة المستخدمين", "🧾 سجل التدقيق"]

    selected_menu = st.selectbox("📌 القائمة الرئيسية لإدارة المنصة:", menu_options, label_visibility="collapsed")
    st.markdown("---")

    if selected_menu == "📊 لوحة التحكم":
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

    elif selected_menu == "🏥 إدارة المنشآت":
        st.subheader("🏥 نظام إدارة وتكويد المنشآت الصحية (إضافة وعرض القائمة)")
        tab_fac_1, tab_fac_2 = st.tabs(["➕ إضافة منشأة بمعرف يدوي", "📋 قائمة المنشآت الحالية"])
        with tab_fac_1:
            with st.form("add_facility_manual_form_v38", clear_on_submit=True):
                manual_id_input = st.number_input("رقم المعرف (ID) المخصص:", min_value=1, max_value=99999, value=1)
                new_fac_input = st.text_input("اسم المنشأة الجديدة:")
                if st.form_submit_button("حفظ وإضافة المنشأة بمعرفها اليدوي", use_container_width=True):
                    if new_fac_input.strip():
                        success, msg = add_facility_manual_db(manual_id_input, new_fac_input)
                        if success:
                            st.success(f"✅ تم إضافة المنشأة ({new_fac_input}) بنجاح!")
                            st.rerun()
                        else:
                            st.warning(f"⚠️️ {msg}")
                    else:
                        st.error("الرجاء كتابة اسم المنشأة.")
        with tab_fac_2:
            facs_rows = get_facilities()
            if not facs_rows:
                st.info("لا توجد منشآت مسجلة حالياً.")
            else:
                df_facs = pd.DataFrame(facs_rows)
                df_facs.columns = ["رقم المعرف (ID)", "اسم المنشأة"]
                st.dataframe(df_facs, use_container_width=True, hide_index=True)
                fac_del_map = {f"معرف رقم ({f['id']}) - {f['name']}": f['id'] for f in facs_rows}
                with st.form("delete_facility_manual_form_v38", clear_on_submit=True):
                    selected_fac_label = st.selectbox("اختر المنشأة للحذف:", list(fac_del_map.keys()))
                    if st.form_submit_button("🗑 حذف المنشأة المحددة نهائياً", use_container_width=True):
                        delete_facility_db_by_id(fac_del_map[selected_fac_label])
                        st.success("✅ تم حذف المنشأة بنجاح!")
                        st.rerun()

    elif selected_menu == "🧑‍🔬 اعتماد المتدربين وتحديد القالب":
        st.subheader("🧑‍🔬 اعتماد المتدربين وتحديد القالب (تحديد فردي أو تعميم جماعي دفعة واحدة)")
        
        with db() as c:
            all_tpls_map = {row["name"]: row["id"] for row in c.execute("SELECT id, name FROM exam_templates").fetchall()}
        tpl_names_list = list(all_tpls_map.keys()) if all_tpls_map else ["لا توجد قوالب امتحانات مسجلة"]

        with st.container(border=True):
            st.markdown("#### ⚡ تعميم قالب واحد لجميع المتدربين دفعة واحدة (للأعداد الكبيرة):")
            with st.form("bulk_assign_form"):
                bulk_tpl_name = st.selectbox("اختر القالب لتعميمه على كافة المتدربين:", tpl_names_list)
                if st.form_submit_button("🚀 تعميم هذا القالب واعتماد الكل دفعة واحدة", use_container_width=True):
                    if all_tpls_map:
                        bulk_tpl_id = all_tpls_map[bulk_tpl_name]
                        set_bulk_template_for_all(bulk_tpl_id)
                        st.success(f"✅ تم بنجاح تعميم القالب ({bulk_tpl_name}) واعتماد جميع المتدربين دفعة واحدة!")
                        st.rerun()
                    else:
                        st.error("لا توجد قوالب امتحانات مسجلة.")

        sub_tabs = st.tabs(["الطلبات المعلقة (تخصيص فردي)", "جميع المتدربين المسجلين"])
        
        with sub_tabs[0]:
            df_pend = trainees_df("pending")
            if df_pend.empty:
                st.info("لا توجد طلبات معلقة بانتظار الموافقة.")
            else:
                for _, r in df_pend.iterrows():
                    with st.container(border=True):
                        st.write(f"**رقم التسجيل (ID):** {r['id']} | **الاسم:** {r['name']} | **الجهة:** {r['facility']} | **الهاتف:** {r['phone']}")
                        
                        current_assigned_id = r['assigned_template_id']
                        current_tpl_name_default = tpl_names_list[0]
                        for name_k, id_v in all_tpls_map.items():
                            if id_v == current_assigned_id:
                                current_tpl_name_default = name_k
                                break
                        default_idx = tpl_names_list.index(current_tpl_name_default) if current_tpl_name_default in tpl_names_list else 0

                        with st.form(f"approve_form_{r['id']}"):
                            chosen_tpl_name = st.selectbox(f"اختر القالب الحصري لهذا المتدرب (ID: {r['id']}):", tpl_names_list, index=default_idx)
                            col_b1, col_b2 = st.columns(2)
                            with col_b1:
                                submit_approve = st.form_submit_button("✅ اعتماد وتثبيت هذا القالب للمتدرب", use_container_width=True)
                            with col_b2:
                                submit_reject = st.form_submit_button("❌ رفض الطلب", use_container_width=True)
                            
                            if submit_approve:
                                if all_tpls_map:
                                    assigned_id = all_tpls_map[chosen_tpl_name]
                                    set_trainee_status_and_template(int(r['id']), "approved", assigned_id)
                                    st.success(f"✅ تم اعتماد المتدرب {r['name']} وربطه بالقالب بنجاح!")
                                    st.rerun()
                                else:
                                    st.error("يجب إنشاء قوالب امتحانات أولاً.")
                            if submit_reject:
                                set_trainee_status_and_template(int(r['id']), "rejected", r.get('assigned_template_id'))
                                st.warning(f"تم رفض الطلب للمتدرب {r['name']}.")
                                st.rerun()

        with sub_tabs[1]:
            st.markdown("#### تعديل وتحديث القوالب المخصصة للمتدربين المعتمدين:")
            df_all_tr = trainees_df()
            if df_all_tr.empty:
                st.info("لا توجد بيانات متدربين مسجلة.")
            else:
                for _, tr_row in df_all_tr.iterrows():
                    with st.container(border=True):
                        st.write(f"**المتدرب:** {tr_row['name']} | **الجهة:** {tr_row['facility']} | **الحالة:** `{STATUS_AR.get(tr_row['status'], tr_row['status'])}`")
                        with st.form(f"update_tr_tpl_{tr_row['id']}"):
                            curr_id = tr_row['assigned_template_id']
                            curr_name = [k for k, v in all_tpls_map.items() if v == curr_id]
                            def_name = curr_name[0] if curr_name else (tpl_names_list[0] if tpl_names_list else "")
                            def_idx = tpl_names_list.index(def_name) if def_name in tpl_names_list else 0
                            
                            new_chosen_tpl = st.selectbox(f"تعديل القالب المخصص للمتدرب ID: {tr_row['id']}", tpl_names_list, index=def_idx, key=f"sel_tr_{tr_row['id']}")
                            if st.form_submit_button("💾 تحديث قالب هذا المتدرب"):
                                if all_tpls_map:
                                    new_id_val = all_tpls_map[new_chosen_tpl]
                                    set_trainee_status_and_template(int(tr_row['id']), tr_row['status'], new_id_val)
                                    st.success(f"✅ تم تحديث قالب المتدرب {tr_row['name']} بنجاح!")
                                    st.rerun()

    elif selected_menu == "🧠 بنك الأسئلة الشامل (استيراد/تصدير Excel)":
        st.subheader("🧠 بنك الأسئلة الشامل (استيراد وتصدير مرن ومستقر)")
        tab_ex_1, tab_ex_2 = st.tabs(["📥 استيراد بنك الأسئلة من شيت إكسيل", "📤 تصدير بنك الأسئلة الحالي إلى إكسيل"])
        
        with tab_ex_1:
            st.markdown("#### رفع ملف إكسيل (.xlsx أو .csv) لإضافة ودمج الأسئلة:")
            st.info("الأعمدة المطلوبة في الملف: `difficulty`, `category`, `question`, `options_json`, `answer`")
            uploaded_excel = st.file_uploader("اختر ملف إكسيل الأسئلة:", type=["xlsx", "xls", "csv"], key="excel_uploader_v38")
            
            if uploaded_excel is not None:
                try:
                    if uploaded_excel.name.endswith('.csv'):
                        df_import = pd.read_csv(uploaded_excel)
                    else:
                        xls_file = pd.ExcelFile(uploaded_excel)
                        sheet_to_read = xls_file.sheet_names[0]
                        df_import = pd.read_excel(xls_file, sheet_name=sheet_to_read)
                    
                    st.write(f"📊 معاينة البيانات المستوردة (إجمالي الصفوف: {len(df_import)}):", df_import.head(3))
                    
                    if st.button("🚀 تأكيد ودمج الأسئلة بقاعدة البيانات الآن", use_container_width=True):
                        imported_count = 0
                        skipped_count = 0
                        with db() as c:
                            for _, row in df_import.iterrows():
                                diff = str(row.get("difficulty", "متوسط"))
                                cat = str(row.get("category", "الفحوص المعملية"))
                                q_text = str(row.get("question", ""))
                                
                                raw_opts = row.get("options_json", '["خيار 1", "خيار 2", "خيار 3", "خيار 4"]')
                                if isinstance(raw_opts, str):
                                    try:
                                        if raw_opts.startswith("["):
                                            opts_list = json.loads(raw_opts)
                                        else:
                                            opts_list = [o.strip() for o in raw_opts.split(",") if o.strip()]
                                    except:
                                        opts_list = [o.strip() for o in raw_opts.split(",") if o.strip()]
                                elif isinstance(raw_opts, list):
                                    opts_list = raw_opts
                                else:
                                    opts_list = ["نعم", "لا"]
                                
                                try:
                                    ans_idx = int(row.get("answer", 0))
                                except:
                                    ans_idx = 0
                                    
                                if ans_idx < 0 or ans_idx >= len(opts_list):
                                    ans_idx = 0
                                
                                if q_text.strip() and opts_list:
                                    fp = hashlib.sha256((q_text + "|" + "|".join(str(o) for o in opts_list)).encode("utf-8")).hexdigest()
                                    try:
                                        c.execute("INSERT INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                                  (diff, cat, q_text, json.dumps(opts_list, ensure_ascii=False), ans_idx, 1, fp, now()))
                                        imported_count += 1
                                    except sqlite3.IntegrityError:
                                        skipped_count += 1
                                        continue
                        reorder_question_ids()
                        st.success(f"🎉 تم بنجاح دمج بنك الأسئلة! تم إضافة ({imported_count}) سؤالاً جديداً (تم استبعاد {skipped_count} سؤالاً مكرراً).")
                        st.balloons()
                except Exception as e:
                    st.error(f"حدث خطأ أثناء معالجة ملف الإكسيل: {e}")

        with tab_ex_2:
            st.markdown("#### تصدير بنك الأسئلة الحالي إلى شيت إكسيل:")
            with db() as c:
                df_bank = pd.read_sql_query("SELECT id, difficulty, category, question, options_json, answer FROM questions ORDER BY id ASC", c)
            
            if df_bank.empty:
                st.info("بنك الأسئلة فارغ حالياً.")
            else:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_bank.to_excel(writer, index=False, sheet_name='QuestionBank')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 تحميل شيت إكسيل بنك الأسئلة (.xlsx)",
                    data=excel_data,
                    file_name=f"question_bank_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                st.dataframe(df_bank, use_container_width=True, hide_index=True)

    elif selected_menu == "⚙ إدارة الأسئلة":
        st.subheader("⚙️ إدارة الأسئلة (إضافة، تعديل، وحذف)")
        sub_img_tabs = st.tabs(["➕ إضافة سؤال جديد", "✏️ تعديل سؤال موجود", "🗑 حذف سؤال"])
        categories_list_opts = [
            "الاستراتيجية العامة ومكافحة البلهارسيا", "البلهارسيا", "علاج البلهارسيا", 
            "الفاشيولا", "علاج الفاشيولا", "الهتروفيس", "علاج الهتروفيس", "التينيا", 
            "هيمنولبس نانا", "الديدان الشريطية", "علاج الديدان الشريطية", "الإسكارس", 
            "الأنكلستوما", "الأكسيورس", "تركيورس تركيورا", "Strongyloides stercoralis", 
            "علاج الديدان المعوية", "Entamoeba histolytica", "Giardia lamblia", "الأوليات", 
            "الفحوص المعملية", "فحص البول", "فحص البراز", "طرق فحص البراز", "الترسيب", 
            "التعويم", "اللطخة المباشرة", "التصفية الغشائية", "Kato-Katz", "تحضير العينات", 
            "جداول الطفيليات", "مهام الوزارات والفرق", "مهام طبيب الرعاية الأساسية", 
            "مهام فني ومساعد المعمل", "ملخص بويضات الطفيليات", "أسئلة الصور والأشكال"
        ]
        with sub_img_tabs[0]:
            if st.session_state.add_success_msg:
                st.success(st.session_state.add_success_msg)
                st.session_state.add_success_msg = ""
            with st.form(key=f"add_custom_img_q_form_{st.session_state.form_key}"):
                selected_cat = st.selectbox("اختر القسم:", categories_list_opts, key="add_q_cat_v38")
                c_text = st.text_area("نص السؤال التشخيصي:", key="add_q_txt_v38")
                c_diff = st.selectbox("مستوى الصعوبة", ["سهل", "متوسط", "صعب"], key="add_q_diff_v38")
                uploaded_img = st.file_uploader("رفع ملف الصورة (اختياري):", type=["png", "jpg", "jpeg"], key="add_q_img_v38")
                opt1 = st.text_input("الخيار الأول:", key="add_q_o1_v38")
                opt2 = st.text_input("الخيار الثاني:", key="add_q_o2_v38")
                opt3 = st.text_input("الخيار الثالث:", key="add_q_o3_v38")
                opt4 = st.text_input("الخيار الرابع:", key="add_q_o4_v38")
                correct_ans_text = st.text_input("نص الإجابة الصحيحة:", key="add_q_ans_v38")
                if st.form_submit_button("حفظ وإضافة السؤال الجديد", use_container_width=True):
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
                        reorder_question_ids()
                        st.session_state.add_success_msg = "✅ تم إضافة السؤال بنجاح!"
                        st.session_state.form_key += 1
                        st.rerun()
        with sub_img_tabs[1]:
            with db() as c: all_questions = c.execute("SELECT id, question, category FROM questions ORDER BY id ASC").fetchall()
            if all_questions:
                q_options_map = {f"سؤال ({q['id']}) - [{q['category']}] : {q['question'][:50]}...": q['id'] for q in all_questions}
                selected_q_label = st.selectbox("اختر السؤال المراد تعديله:", list(q_options_map.keys()), key="edit_q_box_v38")
                selected_q_id = q_options_map[selected_q_label]
                with db() as c: q_data = c.execute("SELECT * FROM questions WHERE id=?", (selected_q_id,)).fetchone()
                if q_data:
                    current_opts = json.loads(q_data["options_json"])
                    while len(current_opts) < 4: current_opts.append("")
                    with st.form(f"edit_question_form_{selected_q_id}"):
                        e_cat = st.selectbox("القسم:", categories_list_opts, index=categories_list_opts.index(q_data["category"]) if q_data["category"] in categories_list_opts else 0)
                        e_diff = st.selectbox("مستوى الصعوبة:", ["سهل", "متوسط", "صعب"], index=["سهل", "متوسط", "صعب"].index(q_data["difficulty"]) if q_data["difficulty"] in ["سهل", "متوسط", "صعب"] else 0)
                        raw_q_db = q_data["question"]
                        actual_text_editable = raw_q_db.replace("IMAGE:", "").split("\n\n")[-1] if "IMAGE:" in raw_q_db else raw_q_db
                        e_text = st.text_area("نص السؤال:", value=actual_text_editable)
                        e_opt1 = st.text_input("الخيار 1:", value=str(current_opts[0]))
                        e_opt2 = st.text_input("الخيار 2:", value=str(current_opts[1]))
                        e_opt3 = st.text_input("الخيار 3:", value=str(current_opts[2]))
                        e_opt4 = st.text_input("الخيار 4:", value=str(current_opts[3]))
                        e_correct_text = st.text_input("الإجابة الصحيحة:", value=current_opts[q_data["answer"]] if 0 <= q_data["answer"] < len(current_opts) else "")
                        if st.form_submit_button("💾 حفظ التعديلات", use_container_width=True):
                            updated_opts = [o for o in [e_opt1, e_opt2, e_opt3, e_opt4] if o.strip() != ""]
                            if e_correct_text not in updated_opts: updated_opts.append(e_correct_text)
                            new_ans_idx = updated_opts.index(e_correct_text)
                            prefix_img = raw_q_db.split("\n\n")[0] + "\n\n" if "IMAGE:" in raw_q_db else ""
                            final_updated_q_str = prefix_img + e_text
                            new_fp = hashlib.sha256((final_updated_q_str + "|" + "|".join(updated_opts)).encode("utf-8")).hexdigest()
                            with db() as c:
                                c.execute("UPDATE questions SET difficulty=?, category=?, question=?, options_json=?, answer=?, fingerprint=? WHERE id=?",
                                          (e_diff, e_cat, final_updated_q_str, json.dumps(updated_opts, ensure_ascii=False), new_ans_idx, new_fp, selected_q_id))
                            st.success("✅ تم التعديل بنجاح!")
                            st.rerun()
        with sub_img_tabs[2]:
            with db() as c: all_questions_del = c.execute("SELECT id, question, category FROM questions ORDER BY id ASC").fetchall()
            if all_questions_del:
                q_del_map = {f"سؤال رقم {q['id']} - {q['question'][:40]}": q['id'] for q in all_questions_del}
                selected_del_label = st.selectbox("اختر السؤال للحذف:", list(q_del_map.keys()), key="del_q_box_v38")
                if st.button("🗑️ تأكيد وحذف السؤال نهائياً", key="del_q_btn_v38", use_container_width=True):
                    with db() as c: c.execute("DELETE FROM questions WHERE id=?", (q_del_map[selected_del_label],))
                    reorder_question_ids()
                    st.success("✅ تم الحذف وإعادة الترتيب بنجاح!")
                    st.rerun()

    elif selected_menu == "🧩 قوالب ومحاضر التدريب (للمالك فقط)":
        st.subheader("🧩 إنشاء وإدارة قوالب الامتحانات (عدد أسئلة مفتوح وغير محدد)")
        sub_tpl_mode = st.radio("اختر القسم المطلوب:", ["📋 عرض القوالب وتوليد الأوراق", "➕ إنشاء قالب جديد كلياً", "🗑 حذف قالب امتحان"], horizontal=True)
        if sub_tpl_mode == "📋 عرض القوالب وتوليد الأوراق":
            with db() as c: tpls = c.execute("SELECT * FROM exam_templates ORDER BY id ASC").fetchall()
            facilities_list = [f["name"] for f in get_facilities()] or ["الإدارة الصحية بأولاد صقر"]
            if tpls:
                for t in tpls:
                    t_dict = dict(t)
                    num_q_display = "مفتوح (كامل البنك)" if int(t_dict.get('num_questions', 999999)) >= 999900 else t_dict.get('num_questions')
                    with st.container(border=True):
                        st.markdown(f"#### 🏷️ قالب رقم ({t_dict.get('id')}): {t_dict.get('name')} | عدد الأسئلة: {num_q_display}")
                        col_m1, col_m2 = st.columns(2)
                        with col_m1: m_date = st.date_input(f"تاريخ المحضر ({t_dict.get('id')})", date.today(), key=f"m_date_{t_dict.get('id')}")
                        with col_m2: m_facility = st.selectbox(f"المنشأة ({t_dict.get('id')})", facilities_list, key=f"m_fac_{t_dict.get('id')}")
                        minutes_html = generate_training_minutes_html(t_dict.get('id'), m_date, m_facility, "تقرير أداء المعامل والإشراف الفني المعتمد")
                        html_exam = generate_compact_exam_html(t_dict.get('id'), "تقرير أداء المعامل والإشراف الفني المعتمد")
                        b1, b2 = st.columns(2)
                        with b1:
                            st.download_button("📥 تحميل المحضر .html", data=minutes_html.encode("utf-8"), file_name=f"training_minutes_{t_dict.get('id')}.html", mime="text/html", key=f"dl_min_{t_dict.get('id')}", use_container_width=True)
                            render_print_button_only(minutes_html, f"محضر التدريب {t_dict.get('id')}")
                        with b2:
                            st.download_button("📥 تحميل الامتحان .html", data=html_exam.encode("utf-8"), file_name=f"exam_template_{t_dict.get('id')}.html", mime="text/html", key=f"dl_exam_{t_dict.get('id')}", use_container_width=True)
                            render_print_button_only(html_exam, f"نموذج الامتحان {t_dict.get('id')}")
        elif sub_tpl_mode == "➕ إنشاء قالب جديد كلياً":
            if st.session_state.tpl_success_msg:
                st.success(st.session_state.tpl_success_msg)
                st.session_state.tpl_success_msg = ""
            categories_pool_opts = [
                "الاستراتيجية العامة ومكافحة البلهارسيا", "البلهارسيا", "علاج البلهارسيا", 
                "الفاشيولا", "علاج الفاشيولا", "الهتروفيس", "علاج الهتروفيس", "التينيا", 
                "هيمنولبس نانا", "الديدان الشريطية", "علاج الديدان الشريطية", "الإسكارس", 
                "الأنكلستوما", "الأكسيورس", "تركيورس تركيورا", "Strongyloides stercoralis", 
                "علاج الديدان المعوية", "Entamoeba histolytica", "Giardia lamblia", "الأوليات", 
                "الفحوص المعملية", "فحص البول", "فحص البراز", "طرق فحص البراز", "الترسيب", 
                "التعويم", "اللطخة المباشرة", "التصفية الغشائية", "Kato-Katz", "تحضير العينات", 
                "جداول الطفيليات", "مهام الوزارات والفرق", "مهام طبيب الرعاية الأساسية", 
                "مهام فني ومساعد المعمل", "ملخص بويضات الطفيليات", "أسئلة الصور والأشكال"
            ]
            with st.form("create_template_from_scratch_form"):
                new_tpl_name = st.text_input("اسم قالب الاختبار الجديد:")
                is_open_questions = st.checkbox("جعل عدد الأسئلة مفتوح وغير محدد (سحب كامل بنك الأسئلة المتاح)", value=True)
                new_tpl_num_q = st.number_input("عدد الأسئلة المخصص (يُهمل إذا تم تفعيل الخيار المفتوح):", min_value=1, max_value=5000, value=50)
                new_tpl_duration = st.number_input("مدة الاختبار بالدقائق:", min_value=5, max_value=300, value=60)
                new_tpl_pass = st.slider("نسبة النجاح المطلوبة %:", min_value=30.0, max_value=95.0, value=60.0)
                new_tpl_cats = st.multiselect("الأقسام المشمولة (اتركها فارغة لسحب كامل البنك):", categories_pool_opts)
                if st.form_submit_button("💾 حفظ وإنشاء القالب الجديد", use_container_width=True):
                    if new_tpl_name.strip():
                        final_num_q = 999999 if is_open_questions else int(new_tpl_num_q)
                        with db() as c:
                            c.execute("INSERT INTO exam_templates(name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, created_at) VALUES(?,?,?,?,?,?,?)",
                                      (new_tpl_name.strip(), "اختبار مخصص للمالك", final_num_q, int(new_tpl_duration), float(new_tpl_pass), json.dumps(new_tpl_cats, ensure_ascii=False), now()))
                        reorder_template_ids()
                        st.session_state.tpl_success_msg = f"✅ تم إنشاء القالب ({new_tpl_name}) بنجاح وبعدد أسئلة {'مفتوح' if is_open_questions else final_num_q}!"
                        st.rerun()
                    else:
                        st.error("الرجاء إدخال اسم القالب.")
        else:
            with db() as c: tpls_del = c.execute("SELECT id, name FROM exam_templates ORDER BY id ASC").fetchall()
            if tpls_del:
                tpl_map = {f"قالب رقم {t['id']} - {t['name']}": t['id'] for t in tpls_del}
                with st.form("delete_template_form"):
                    selected_tpl_label = st.selectbox("اختر القالب للحذف:", list(tpl_map.keys()))
                    if st.form_submit_button("🗑️ تأكيد وحذف القالب نهائياً", use_container_width=True):
                        delete_template_db_by_id(tpl_map[selected_tpl_label])
                        st.success("✅ تم حذف القالب بنجاح!")
                        st.rerun()

    elif selected_menu == "✍️ تسجيل نتيجة يدوي":
        st.subheader("✍️ تسجيل نتيجة متدرب يدوياً من الإدارة")
        facilities_list = [f["name"] for f in get_facilities()] or ["الإدارة الصحية بأولاد صقر"]
        with st.form("manual_score_form"):
            m_trainee_name = st.text_input("اسم المتدرب الرباعي:")
            m_facility_name = st.selectbox("جهة العمل:", facilities_list)
            with db() as c: all_tpls = c.execute("SELECT id, name FROM exam_templates").fetchall()
            tpl_choices = {row["name"]: row["id"] for row in all_tpls}
            selected_tpl_name = st.selectbox("اختر القالب المرتبط:", list(tpl_choices.keys()) if tpl_choices else ["افتراضي"])
            col_sc1, col_sc2 = st.columns(2)
            with col_sc1: manual_score = st.number_input("الدرجة المحصلة:", min_value=0, max_value=9999, value=40)
            with col_sc2: manual_max = st.number_input("الدرجة الكلية:", min_value=1, max_value=9999, value=50)
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

    elif selected_menu == "📊 التقارير المتقدمة والتصدير":
        st.subheader("📊 تقارير قياس المستويات وطباعة الشهادات")
        d_start = st.date_input("من تاريخ", date.today() - timedelta(days=30))
        d_end = st.date_input("إلى تاريخ", date.today())
        with db() as c:
            df_res = pd.read_sql_query("""SELECT s.id AS 'رقم الجلسة', t.name AS 'اسم المتدرب', t.facility AS 'جهة العمل', COALESCE(et.name, 'اختبار معتمد') AS 'اسم الاختبار', s.score AS 'الدرجة', s.max_score AS 'الدرجة الكلية', s.percent AS 'النسبة %', CASE WHEN s.passed = 1 THEN 'اجتزت بنجاح' ELSE 'لم تجتز' END AS 'الحالة', s.certificate_id AS 'رقم الشهادة', s.submitted_at AS 'تاريخ ووقت التسليم' FROM exam_sessions s JOIN trainees t ON t.id = s.trainee_id LEFT JOIN exam_templates et ON et.id = s.template_id WHERE s.status = 'submitted' AND s.submitted_at >= ? AND s.submitted_at <= ? ORDER BY s.submitted_at DESC""", c, params=[datetime.combine(d_start, datetime.min.time()).isoformat(), datetime.combine(d_end, datetime.max.time()).isoformat()])
        if not df_res.empty:
            st.dataframe(df_res, use_container_width=True, hide_index=True)
            st.markdown("---")
            with db() as c: submitted_sessions = c.execute("SELECT s.id, t.name, t.facility, s.certificate_id FROM exam_sessions s JOIN trainees t ON t.id = s.trainee_id WHERE s.status='submitted' ORDER BY s.id DESC").fetchall()
            if submitted_sessions:
                session_options = {f"جلسة رقم {row['id']} - المتدرب: {row['name']} ({row['facility']}) - شهادة: {row['certificate_id']}": row['id'] for row in submitted_sessions}
                selected_sid = session_options[st.selectbox("اختر المتدرب لطباعة شهادته:", list(session_options.keys()))]
                cert_html_admin = generate_compact_certificate_html(selected_sid, "شهادة معتمدة ومصدرة من لوحة إشراف المالك")
                col_b1, col_b2 = st.columns(2)
                with col_b1: st.download_button("📥 تحميل الشهادة .html", data=cert_html_admin.encode("utf-8"), file_name=f"cert_{selected_sid}.html", mime="text/html", use_container_width=True)
                with col_b2: render_print_button_only(cert_html_admin, f"شهادة متدرب {selected_sid}")

    elif selected_menu == "💾 النسخ الاحتياطي":
        st.subheader("💾 النسخ الاحتياطي واستخلاص قاعدة البيانات")
        with open(DB_PATH, "rb") as f: db_bytes = f.read()
        st.download_button("📥 تحميل وتخزين قاعدة البيانات الكاملة (.db)", data=db_bytes, file_name="database_backup.db", mime="application/octet-stream", use_container_width=True)

    elif selected_menu == "👥 إدارة المستخدمين":
        st.subheader("👥 إدارة المستخدمين")
        with db() as c: users_list = c.execute("SELECT id, username, role, active, created_at FROM users").fetchall()
        st.dataframe(pd.DataFrame([dict(u) for u in users_list]), use_container_width=True, hide_index=True)

    elif selected_menu == "🧾 سجل التدقيق":
        st.subheader("🧾 سجل التدقيق")
        with db() as c: df_audit = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100", c)
        st.dataframe(df_audit, use_container_width=True, hide_index=True)

def trainee_portal():
    with db() as c:
        tr = c.execute("SELECT * FROM trainees WHERE id=?", (st.session_state.trainee_id,)).fetchone()
    if not tr:
        st.session_state.trainee_id = None
        st.rerun()
    header()
    
    assigned_tpl_id = tr["assigned_template_id"]
    with db() as c:
        matching_template = c.execute("SELECT * FROM exam_templates WHERE id=?", (assigned_tpl_id,)).fetchone() if assigned_tpl_id else None
            
    tpl_name_str = matching_template["name"] if matching_template else "لم يتم تخصيص قالب بعد"
    
    st.markdown(f'<div class="card"><h3>مرحباً بك، {esc(tr["name"])}</h3><p>الجهة: {esc(tr["facility"])} | القالب المخصص لك حصرياً: <b>{esc(tpl_name_str)}</b></p></div>', unsafe_allow_html=True)
    if matching_template:
        st.info(f"📌 سيتم بدء اختبارك المخصص بناءً على القالب المعتمد لك: **{tpl_name_str}**")
    else:
        st.warning("⚠️ عذراً، لم تقم الإدارة بتعيين قالب امتحان مخصص لك بعد من لوحة التحكم.")

    if matching_template and st.button("بدء الاختبار المخصص الآن", use_container_width=True):
        try:
            sid = start_session(tr["id"], matching_template["id"])
            st.session_state.exam_session_id = sid
            st.rerun()
        except Exception as e:
            st.error(str(e))
            
    if st.button("خروج من الحساب"):
        st.session_state.trainee_id = None
        st.rerun()

def exam_interface(session_id):
    with db() as c:
        session = c.execute("SELECT * FROM exam_sessions WHERE id=?", (session_id,)).fetchone()
        rows = c.execute("""SELECT eq.*, q.question, q.options_json FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=? ORDER BY eq.position""", (session_id,)).fetchall()
    answered = 0
    for row in rows:
        try:
            opts = json.loads(row["options_json"])
            if not isinstance(opts, list):
                opts = ["نعم", "لا"]
        except:
            opts = ["نعم", "لا"]
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
            with db() as c:
                c.execute("UPDATE exam_questions SET selected_option=?, is_correct=CASE WHEN ?=(SELECT answer FROM questions WHERE id=question_id) THEN 1 ELSE 0 END WHERE id=?", (sel, sel, row["id"]))
            answered += 1
    st.progress(answered / len(rows) if rows else 0)
    if st.button("تسليم الاختبار نهائياً", use_container_width=True):
        res = submit_session(session_id)
        if res: st.session_state.last_result_id = session_id
        st.session_state.exam_session_id = None
        st.success("🎉 تم تسليم الاختبار بنجاح!")
        st.rerun()

# ============================================================
# 7) التوجيه الأساسي للشاشات
# ============================================================
if st.session_state.get("exam_session_id"):
    exam_interface(st.session_state.exam_session_id)
elif st.session_state.trainee_id and not st.session_state.logged_in:
    if st.session_state.get("last_result_id"):
        sid = st.session_state.last_result_id
        header()
        st.success("تم تسليم الاختبار بنجاح ونتيجتك جاهزة!")
        cert_html = generate_compact_certificate_html(sid, "تقرير أداء المعامل والإشراف الفني المعتمد")
        st.download_button("📥 تحميل شهادة الاجتياز المعتمدة .html", data=cert_html.encode("utf-8"), file_name=f"certificate_{sid}.html", mime="text/html")
        render_print_button_only(cert_html, f"الشهادة المعتمدة {sid}")
        if st.button("العودة للرئيسية"):
            st.session_state.trainee_id = None
            st.session_state.last_result_id = None
            st.rerun()
    else:
        trainee_portal()
elif not st.session_state.logged_in:
    login_portal()
else:
    admin_dashboard()
