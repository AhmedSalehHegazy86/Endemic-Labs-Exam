import os, io, re, ast, json, sqlite3, hashlib, secrets, random, time, html
from datetime import datetime, timedelta, date
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
# 2) حقن التنسيقات (CSS) وحماية الأمان
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
}

.block-container {
    max-width: 1150px !important;
    margin: auto !important;
    padding: 4.5rem 2rem 7rem 2rem !important;
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
}

.ownership-watermark {
    position: fixed;
    bottom: 0; right: 0; left: 0;
    background: rgba(6, 78, 59, 0.95);
    color: #ffffff;
    text-align: center;
    padding: 8px;
    font-size: 13px;
    font-weight: 700;
    z-index: 99999;
    border-top: 2px solid #059669;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="ownership-watermark">
🔬 جميع الحقوق محفوظة © 2026 | تصميم وتطوير: <b>Dr/Ahmed.S.Hegazy</b>
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

def normalize_text(x):
    x = "" if x is None else str(x)
    return re.sub(r"\s+", " ", x.strip()).lower()

def clean_question_text(q_text):
    if not q_text: return ""
    cleaned = re.sub(r"\(نموذج معملي.*?\)", "", q_text)
    return normalize_text(cleaned)

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
            hidden INTEGER NOT NULL DEFAULT 0
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
            exam_type TEXT NOT NULL DEFAULT 'اختبار مخصص',
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
            certificate_id TEXT
        );
        CREATE TABLE IF NOT EXISTS exam_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            option_order_json TEXT NOT NULL,
            selected_option INTEGER,
            is_correct INTEGER
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

        cnt = c.execute("SELECT COUNT(*) FROM print_settings").fetchone()[0]
        if cnt == 0:
            default_header = "جمهورية مصر العربية<br>وزارة الصحة والسكان<br>مديرية الشئون الصحية بالشرقية<br>الإدارة الصحية بأولاد صقر"
            default_professions = ["أخصائي تحاليل طبية", "طبيب بيطري", "فني معمل"]
            c.execute("INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, logo_base64, default_cert_title, default_cert_notes, professions_list_json) VALUES(?,?,?,?,?,?,?,?,?)",
                      (default_header, "5mm", "5mm", "5mm", "5mm", DEFAULT_LOGO, "شهادة اجتياز اختبار معتمدة", "تقرير أداء المعامل", json.dumps(default_professions, ensure_ascii=False)))

init_db()

def get_print_settings():
    with db() as c:
        row = c.execute("SELECT * FROM print_settings ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            res = dict(row)
            try: res["professions_list"] = json.loads(res.get("professions_list_json", "[]"))
            except: res["professions_list"] = ["أخصائي تحاليل طبية"]
            return res
        return {"header_text": "الإدارة الصحية بأولاد صقر", "logo_base64": DEFAULT_LOGO, "default_cert_title": "شهادة اجتياز"}

def save_print_settings(h_text, def_title, def_notes):
    with db() as c:
        c.execute("DELETE FROM print_settings")
        c.execute("INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, logo_base64, default_cert_title, default_cert_notes) VALUES(?,?,?,?,?,?,?,?)",
                  (h_text, "5mm", "5mm", "5mm", "5mm", DEFAULT_LOGO, def_title, def_notes))

def get_hierarchical_data(include_hidden=False):
    with db() as c:
        q = "SELECT * FROM hierarchical_facilities"
        if not include_hidden: q += " WHERE hidden = 0"
        rows = c.execute(q).fetchall()
        return [dict(r) for r in rows] if rows else []

def ensure_admin():
    with db() as c:
        u = c.execute("SELECT * FROM users WHERE role='admin'").fetchone()
        all_modules = list(ALL_MENU_MODULES.keys())
        if not u:
            c.execute("INSERT OR REPLACE INTO users(username,password_hash,role,permissions_json,active,created_at) VALUES(?,?,?,?,?,?)",
                      ("admin", hash_password("admin"), "admin", json.dumps(all_modules, ensure_ascii=False), 1, now()))

ensure_admin()

def login_user(u, p):
    with db() as c:
        user = c.execute("SELECT * FROM users WHERE username=? AND active=1", (u.strip(),)).fetchone()
        if user and verify_password(p, user["password_hash"]):
            return dict(user)
    return None

def create_trainee(facility, name, phone, assigned_template_id=None):
    with db() as c:
        cur = c.execute("INSERT INTO trainees(facility,name,phone,status,assigned_template_id,created_at,updated_at,hidden) VALUES(?,?,?,?,?,?,?,?)",
                        (facility, normalize_text(name), normalize_text(phone), "pending", assigned_template_id, now(), now(), 0))
        return cur.lastrowid

def trainee_by_credentials(name, facility):
    with db() as c:
        r = c.execute("SELECT * FROM trainees WHERE name=? AND facility=? AND status IN ('approved','active') AND hidden=0",
                      (normalize_text(name), facility)).fetchone()
        return dict(r) if r else None

def choose_questions(t):
    if not t: return []
    t_dict = dict(t)
    limit_count = int(t_dict.get("num_questions", 999999))
    with db() as c:
        all_db_questions = [dict(r) for r in c.execute("SELECT * FROM questions WHERE active=1 ORDER BY RANDOM()").fetchall()]
    if limit_count >= 999900: return all_db_questions
    return all_db_questions[:limit_count]

def start_session(trainee_id, template_id):
    with db() as c:
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        if not t: raise ValueError("نموذج الاختبار غير موجود.")
        t_dict = dict(t)
    qs = choose_questions(t_dict)
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
        cert = f"ELX-{sid:06d}"
        c.execute("UPDATE exam_sessions SET status='submitted', submitted_at=?, score=?, max_score=?, percent=?, passed=?, certificate_id=? WHERE id=?",
                  (now(), correct, max_score, percent, 1 if percent >= 60 else 0, cert, sid))
        c.execute("UPDATE trainees SET status='completed', updated_at=? WHERE id=?", (now(), s["trainee_id"]))
        return {"score": correct, "max_score": max_score, "percent": percent, "certificate_id": cert}

def render_logos_html():
    sett = get_print_settings()
    return f'<img src="{sett.get("logo_base64", DEFAULT_LOGO)}" style="width: 35px; height: 35px; object-fit: contain;" alt="Logo">'

def generate_qr_code_base64(data_text):
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return "data:image/png;base64," + __import__("base64").b64encode(buffered.getvalue()).decode("utf-8")

def generate_customizable_certificate_html(sid):
    sett = get_print_settings()
    with db() as c:
        r = c.execute("SELECT s.*, t.name trainee_name, t.facility, e.name template_name FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?", (sid,)).fetchone()
    if not r: return ""
    qr_base64 = generate_qr_code_base64(r["certificate_id"])
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head><meta charset="UTF-8"><style>body{{font-family:'Cairo',sans-serif; text-align:center; padding:20px;}}</style></head>
    <body>
        <h2>{esc(sett.get('default_cert_title'))}</h2>
        <h3>المتدرب: {esc(r['trainee_name'])}</h3>
        <p> جهة العمل: {esc(r['facility'])} | النتيجة: {r['score']} / {r['max_score']} ({r['percent']:.1f}%)</p>
        <p>رقم الشهادة: <b>{r['certificate_id']}</b></p>
        <img src="{qr_base64}" style="width:70px; height:70px;">
    </body>
    </html>
    """

def render_print_button_only(html_content, label_prefix=""):
    encoded_html = json.dumps(html_content)
    js_code = """
        <div>
            <button onclick="printDoc()" style="background-color: #059669; color: white; padding: 8px 14px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">
                🖨 طباعة / حفظ المستند
            </button>
        </div>
        <script>
            function printDoc() {
                var win = window.open('', '_blank');
                win.document.write(""" + encoded_html + """);
                win.document.close();
                setTimeout(function(){ win.print(); }, 500);
            }
        </script>
    """
    components.html(js_code, height=60)

# ============================================================
# 4) الواجهات والشاشات
# ============================================================
for k, v in {"logged_in": False, "username": "", "role": "", "permissions": [], "trainee_id": None, "exam_session_id": None, "last_result_id": None, "active_admin_tab": "📊 لوحة التحكم", "show_verification_portal": False}.items():
    if k not in st.session_state: st.session_state[k] = v

def header():
    st.markdown('<div class="hero"><h1>🔬 نظام تقييم واختبار العاملين بمعامل المتوطنة</h1><div>System V1.0</div></div>', unsafe_allow_html=True)

def verification_portal_view():
    header()
    st.markdown("### 🔍 التحقق الرقمي من الشهادات")
    code = st.text_input("أدخل كود الشهادة:")
    if code.strip():
        with db() as c:
            r = c.execute("SELECT s.*, t.name trainee_name, t.facility FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.certificate_id=?", (code.strip().upper(),)).fetchone()
        if r:
            st.success(f"✅ الشهادة صحيحة للمتدرب: {esc(r['trainee_name'])} - الجهة: {esc(r['facility'])}")
        else:
            st.warning("⚠️ لم يتم العثور على شهادة بهذا الكود.")
    if st.button("العودة"):
        st.session_state.show_verification_portal = False
        st.rerun()

def login_portal():
    header()
    col1, col2 = st.columns([2, 1])
    with col1: st.markdown("#### بوابة تسجيل الاختبارات للمتدربين.")
    with col2:
        if st.button("🔍 التحقق من شهادة", use_container_width=True):
            st.session_state.show_verification_portal = True
            st.rerun()

    hier_data = get_hierarchical_data()
    with st.form("trainee_form"):
        name = st.text_input("الاسم الرباعي:")
        facility = st.text_input("جهة العمل:")
        with db() as c: all_tpls = {row["name"]: row["id"] for row in c.execute("SELECT id, name FROM exam_templates").fetchall()}
        tpl_name = st.selectbox("نموذج الاختبار:", ["-- اختر --"] + list(all_tpls.keys()))
        if st.form_submit_button("دخول الاختبار", use_container_width=True):
            if name and facility and tpl_name != "-- اختر --":
                tid = create_trainee(facility, name, "", all_tpls[tpl_name])
                st.session_state.trainee_id = tid
                st.rerun()

    with st.expander("🔐 دخول الإدارة"):
        with st.form("admin_login"):
            u = st.text_input("اسم المستخدم")
            p = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("دخول النظام", use_container_width=True):
                user = login_user(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.role = user["role"]
                    st.rerun()

def admin_dashboard():
    header()
    if st.button("تسجيل الخروج"):
        st.session_state.logged_in = False
        st.rerun()
    st.subheader("📊 لوحة التحكم والإدارة")
    with db() as c:
        tr_count = c.execute("SELECT COUNT(*) FROM trainees").fetchone()[0]
    st.metric("إجمالي المتدربين", tr_count)

def trainee_portal():
    with db() as c: tr = c.execute("SELECT * FROM trainees WHERE id=?", (st.session_state.trainee_id,)).fetchone()
    if not tr: st.session_state.trainee_id = None; st.rerun()
    header()
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
        st.markdown(f'<div class="question"><b>س:</b> {clean_question_text(row["question"])}</div>', unsafe_allow_html=True)
        choice = st.radio("اختر:", opts, key=f"q_{row['id']}")
        if choice:
            sel = opts.index(choice)
            with db() as c: c.execute("UPDATE exam_questions SET selected_option=? WHERE id=?", (sel, row["id"]))
    if st.button("تسليم الاختبار", use_container_width=True):
        res = submit_session(session_id)
        if res: st.session_state.last_result_id = session_id
        st.session_state.exam_session_id = None
        st.success("تم تسليم الاختبار بنجاح!")
        st.rerun()

# ============================================================
# 5) التوجيه والشاشات الرئيسية
# ============================================================
if st.session_state.get("show_verification_portal", False):
    verification_portal_view()
elif st.session_state.get("exam_session_id"):
    exam_interface(st.session_state.exam_session_id)
elif st.session_state.trainee_id and not st.session_state.logged_in:
    if st.session_state.get("last_result_id"):
        header()
        st.success("تم الانتهاء من الاختبار بنجاح!")
        render_print_button_only(generate_customizable_certificate_html(st.session_state.last_result_id))
        if st.button("الخروج"): st.session_state.trainee_id = None; st.session_state.last_result_id = None; st.rerun()
    else:
        trainee_portal()
elif not st.session_state.logged_in:
    login_portal()
else:
    admin_dashboard()
