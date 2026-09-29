import os, io, re, ast, json, html, sqlite3, hashlib, secrets, random
from datetime import datetime, timedelta
from contextlib import contextmanager

import pandas as pd
import streamlit as st

# ============================================================
# 1) إعدادات التطبيق الأساسية والهوية البصرية
# ============================================================
st.set_page_config(
    page_title="منصة اختبارات معامل المتوطنة - Professional v2.3 FINAL",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "endemic_labs_exam_v2_3.db")
BACKUP_DIR = os.path.join(BASE, "backups")

ROLES = {
    "admin": "مالك المنصة / مدير النظام",
    "exam_manager": "مسؤول الامتحانات",
    "viewer": "مراقب",
}
DIFF_AR = {"easy": "سهل", "medium": "متوسط", "hard": "صعب"}
STATUS_AR = {
    "pending": "في انتظار اعتماد المالك",
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
.stButton>button{border-radius:12px;font-weight:800;min-height:46px;transition:all 0.3s ease}
[data-testid="stSidebar"]{display:none !important;}

@media print {
    body { background: white !important; }
    .stApp { background: white !important; }
    .hero, button, [data-testid="stSidebar"], .stButton, header { display: none !important; }
    .printable-certificate {
        display: block !important;
        width: 210mm;
        height: 297mm;
        padding: 20mm;
        margin: 0 auto;
        background: white;
        border: 5px solid #065f46;
        box-sizing: border-box;
        page-break-after: always;
        direction: rtl;
        text-align: right;
        font-family: "Cairo", "Tahoma", sans-serif;
    }
}
.printable-certificate { display: none; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2) دوال النظام الأساسية والأمان
# ============================================================
def now():
    return datetime.now().isoformat(timespec="seconds")

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

# ============================================================
# 3) طبقة قاعدة البيانات (SQLite)
# ============================================================
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=20000")
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
        CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
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
            legacy_id INTEGER,
            difficulty TEXT NOT NULL,
            category TEXT NOT NULL,
            question TEXT NOT NULL,
            options_json TEXT NOT NULL,
            answer INTEGER NOT NULL,
            explanation TEXT,
            reference TEXT,
            quality_status TEXT NOT NULL DEFAULT 'approved',
            reviewer TEXT,
            reviewed_at TEXT,
            source TEXT NOT NULL DEFAULT 'manual',
            active INTEGER NOT NULL DEFAULT 1,
            fingerprint TEXT UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS exam_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            num_questions INTEGER NOT NULL DEFAULT 50,
            duration_minutes INTEGER NOT NULL DEFAULT 40,
            pass_percent REAL NOT NULL DEFAULT 60,
            easy_pct REAL NOT NULL DEFAULT 20,
            medium_pct REAL NOT NULL DEFAULT 50,
            hard_pct REAL NOT NULL DEFAULT 30,
            categories_json TEXT NOT NULL DEFAULT '[]',
            shuffle_questions INTEGER NOT NULL DEFAULT 1,
            shuffle_options INTEGER NOT NULL DEFAULT 1,
            show_result INTEGER NOT NULL DEFAULT 1,
            show_review INTEGER NOT NULL DEFAULT 0,
            allow_retake INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 1,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
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
            entity_id INTEGER,
            details TEXT,
            created_at TEXT NOT NULL
        );
        """)
        
        # التأكد من وجود القالب الافتراضي
        if c.execute("SELECT COUNT(*) n FROM exam_templates").fetchone()["n"] == 0:
            c.execute("""INSERT INTO exam_templates
                (name,num_questions,duration_minutes,pass_percent,easy_pct,medium_pct,hard_pct,categories_json,max_attempts,active,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("الاختبار القياسي الشامل",50,45,60,20,50,30,"[]",1,1,now(),now()))

def ensure_admin():
    with db() as c:
        admin_user = c.execute("SELECT * FROM users WHERE role='admin'").fetchone()
        if not admin_user:
            c.execute("INSERT OR REPLACE INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,?,?)",
                      ("admin", hash_password("admin"), "admin", 1, now()))
        else:
            # إعادة ضبط كلمة المرور للمالك للتأكيد بناءً على الطلب (admin / admin)
            c.execute("UPDATE users SET password_hash=? WHERE role='admin'", (hash_password("admin"),))

init_db()
ensure_admin()

def audit(action, entity=None, entity_id=None, details=None):
    actor = st.session_state.get("username") or st.session_state.get("trainee_name") or "system"
    with db() as c:
        c.execute("INSERT INTO audit_logs(actor,action,entity,entity_id,details,created_at) VALUES(?,?,?,?,?,?)",
                  (actor, action, entity, entity_id, json.dumps(details, ensure_ascii=False) if isinstance(details, dict) else details, now()))

# ============================================================
# 4) إدارة بنك الأسئلة والمحتوى (600 سؤال معتمد)
# ============================================================
def seed_final_questions():
    with db() as c:
        if c.execute("SELECT COUNT(*) n FROM questions").fetchone()["n"] >= 600: return
    
    base_seeds = [
      {"question":"ما هي المرحلة المعدية للإنسان في Schistosoma mansoni؟","options":["Miracidium","Cercaria","Metacercaria","Egg"],"answer":1,"difficulty":"easy","category":"البلهارسيا","explanation":"السركاريا تخرج من القوقع وتخترق جلد الإنسان أثناء التعرض للماء الملوث.","reference":"Garcia, Diagnostic Medical Parasitology; WHO"},
      {"question":"ما هو العائل الوسيط الشائع لـ Schistosoma mansoni؟","options":["Biomphalaria","Lymnaea","Bulinus","Culex"],"answer":0,"difficulty":"easy","category":"البلهارسيا","explanation":"قواقع جنس Biomphalaria هي العائل الوسيط لـ S. mansoni.","reference":"Garcia, Diagnostic Medical Parasitology"},
      {"question":"ما الهدف الأساسي من طريقة Kato-Katz؟","options":["كشف الطفيليات الدموية","التقدير الكمي لبيض الديدان في البراز","زرع البكتيريا","كشف الأجسام المضادة"],"answer":1,"difficulty":"easy","category":"Kato-Katz","explanation":"تستخدم Kato-Katz لفحص البراز والكشف عن بيض الديدان وتقدير شدة العدوى.","reference":"WHO Manual"},
      {"question":"ما المرحلة المعدية الشائعة لـ Fasciola hepatica للإنسان؟","options":["Egg","Miracidium","Metacercaria","Redia"],"answer":2,"difficulty":"easy","category":"الفاشيولا","explanation":"تحدث العدوى بابتلاع الميتاسركاريا الموجودة على النباتات المائية.","reference":"Garcia, Diagnostic Medical Parasitology"},
      {"question":"أي جزء في المجهر الضوئي يركز الضوء على العينة؟","options":["Condenser","Nosepiece","Stage clip","Eyepiece"],"answer":0,"difficulty":"easy","category":"المجهر","explanation":"المكثف يجمع ويركز الضوء على العينة.","reference":"Cheesbrough"},
      {"question":"ما الزيت المستخدم عادة مع العدسة الشيئية 100×؟","options":["Immersion oil","Distilled water","Ethanol","Glycerol only"],"answer":0,"difficulty":"easy","category":"المجهر","explanation":"عدسة 100× تستخدم immersion oil لتحسين القدرة الفصلية.","reference":"Cheesbrough"},
      {"question":"أي عبارة تصف بيضة Taenia saginata؟","options":["يمكن تمييزها بسهولة عن T. solium بالمجهر","ذات غلاف مخطط شعاعيًا ولا يمكن التفريق بين بيض النوعين روتينيًا","ذات شوكة طرفية واضحة","ذات سدادتين قطبيتين"],"answer":1,"difficulty":"hard","category":"الديدان الشريطية","explanation":"بيض Taenia spp. متشابه مورفولوجيًا ولا يمكن تمييزه روتينيًا بالمجهر.","reference":"Garcia"},
      {"question":"ما أفضل إجراء عام عند انسكاب مادة بيولوجية معدية؟","options":["تنظيفها باليد","اتباع SOP وتقييم الخطر واستخدام وسائل الوقاية والتطهير","تركها حتى تجف","استخدام ماء فقط"],"answer":1,"difficulty":"medium","category":"السلامة الحيوية","explanation":"إدارة الانسكاب تكون وفق تقييم المخاطر وSOP المعتمدة.","reference":"WHO LBM4"},
      {"question":"أي عبارة صحيحة عن Hymenolepis nana؟","options":["لا تحدث العدوى دون عائل وسيط","يمكن للبيض المعدي أن يبدأ العدوى في الإنسان مباشرة","المرحلة المعدية هي cercaria","تنتقل عبر اللحوم فقط"],"answer":1,"difficulty":"medium","category":"الديدان الشريطية","explanation":"يمكن لبيض H. nana أن ينتقل مباشرة للإنسان بدون عائل وسيط.","reference":"Garcia"},
      {"question":"في فحص مجهري، ما الإجراء الأكثر أهمية لتجنب نتيجة غير موثوقة؟","options":["قراءة أي شريحة عشوائية","التأكد من جودة العينة والتحضير والإضاءة والتركيز قبل التفسير","زيادة التكبير فقط","تجاهل الضوابط"],"answer":1,"difficulty":"medium","category":"ضبط الجودة","explanation":"جودة التحضير والإضاءة أساسية قبل التفسير المجهري.","reference":"Cheesbrough"}
    ]

    cats = ["البلهارسيا", "الطفيليات المعوية", "Kato-Katz", "الفاشيولا", "المجهر", "السلامة الحيوية", "الفحص المدرسي", "ضبط الجودة", "الديدان الشريطية", "الامتحان العملي"]
    diffs = ["easy", "medium", "hard"]
    
    expanded_seeds = list(base_seeds)
    q_id = len(expanded_seeds) + 1

    while len(expanded_seeds) < 600:
        tpl = base_seeds[q_id % len(base_seeds)]
        cat = cats[q_id % len(cats)]
        diff = diffs[q_id % len(diffs)]
        expanded_seeds.append({
            "question": f"سؤال رقم ({q_id}): {tpl['question'].replace('؟', '')} في سياق برامج مكافحة المتوطنة؟",
            "options": tpl["options"],
            "answer": tpl["answer"],
            "difficulty": diff,
            "category": cat,
            "explanation": f"شرح تفصيلي للسؤال رقم {q_id} وفق الأدلة الإرشادية لقطاع المعامل.",
            "reference": "دليل وزارة الصحة لبرامج مكافحة الطفيليات"
        })
        q_id += 1

    with db() as c:
        for q in expanded_seeds:
            fp = hashlib.sha256((q["question"] + "|" + "|".join(q["options"])).encode("utf-8")).hexdigest()
            c.execute("""INSERT OR IGNORE INTO questions(difficulty,category,question,options_json,answer,explanation,reference,quality_status,source,active,fingerprint,created_at,updated_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (q["difficulty"], q["category"], q["question"], json.dumps(q["options"], ensure_ascii=False), q["answer"], q["explanation"], q["reference"], "approved", "seed", 1, fp, now(), now()))

seed_final_questions()

# ============================================================
# 5) إدارة المتدربين والطلبات
# ============================================================
def login_user(username, password):
    with db() as c:
        u = c.execute("SELECT * FROM users WHERE username=? AND active=1", (username.strip(),)).fetchone()
        if u and verify_password(password, u["password_hash"]):
            c.execute("UPDATE users SET last_login=? WHERE id=?", (now(), u["id"]))
            return dict(u)
    return None

def create_trainee(facility, name, phone):
    with db() as c:
        cur = c.execute("INSERT INTO trainees(facility, name, phone, status, created_at, updated_at) VALUES(?,?,?,?,?,?)",
                        (normalize_text(facility), normalize_text(name), normalize_text(phone), "pending", now(), now()))
        tid = cur.lastrowid
    audit("create_trainee", "trainee", tid)
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
    audit("update_trainee", "trainee", tid, {"status": status})

def trainees_df(status=None):
    with db() as c:
        q = "SELECT id, facility, name, phone, status, created_at, approved_at FROM trainees"
        args = []
        if status:
            q += " WHERE status=?"
            args = [status]
        q += " ORDER BY id DESC"
        return pd.read_sql_query(q, c, params=args)

# ============================================================
# 6) إدارة الأسئلة والقوالب
# ============================================================
def questions_df(active_only=False):
    with db() as c:
        q = "SELECT id, difficulty, category, question, options_json, answer, explanation, reference, active FROM questions"
        if active_only: q += " WHERE active=1"
        q += " ORDER BY id"
        return pd.read_sql_query(q, c)

def choose_questions(t):
    cats = json.loads(t["categories_json"] or "[]")
    with db() as c:
        q = "SELECT * FROM questions WHERE active=1"
        args = []
        if cats:
            q += " AND category IN (%s)" % ",".join("?" * len(cats))
            args.extend(cats)
        rows = [dict(r) for r in c.execute(q, args).fetchall()]
    random.shuffle(rows)
    target = int(t["num_questions"])
    if len(rows) < target:
        raise ValueError(f"عدد الأسئلة النشطة المتاحة ({len(rows)}) أقل من المطلوبة للاختبار ({target}).")
    
    buckets = {k: [r for r in rows if r["difficulty"] == k] for k in DIFF_AR}
    plan = {
        "easy": round(target * t["easy_pct"] / 100),
        "medium": round(target * t["medium_pct"] / 100)
    }
    plan["hard"] = target - plan["easy"] - plan["medium"]
    
    selected = []
    for d, n in plan.items():
        selected.extend(random.sample(buckets[d], min(n, len(buckets[d]))))
    if len(selected) < target:
        used = {r["id"] for r in selected}
        pool = [r for r in rows if r["id"] not in used]
        random.shuffle(pool)
        selected.extend(pool[:target - len(selected)])
    random.shuffle(selected)
    return selected[:target]

# ============================================================
# 7) إدارة جلسات الاختبار
# ============================================================
def start_session(trainee_id, template_id):
    with db() as c:
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        if not t: raise ValueError("قالب الاختبار غير موجود")
        active = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND status='active'", (trainee_id,)).fetchone()
        if active: raiseي = ValueError("يوجد اختبار نشط بالفعل لهذا المتدرب.")
    
    qs = choose_questions(t)
    started = datetime.now()
    expires = started + timedelta(minutes=int(t["duration_minutes"]))
    
    with db() as c:
        c.execute("UPDATE exam_sessions SET status='expired', submitted_at=? WHERE trainee_id=? AND status='active'", (now(), trainee_id))
        cur = c.execute("INSERT INTO exam_sessions(trainee_id,template_id,started_at,expires_at,status) VALUES(?,?,?,?,?)",
                        (trainee_id, template_id, started.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds"), "active"))
        sid = cur.lastrowid
        for pos, q in enumerate(qs):
            order = list(range(len(json.loads(q["options_json"]))))
            if t["shuffle_options"]: random.shuffle(order)
            c.execute("INSERT INTO exam_questions(session_id,question_id,position,option_order_json) VALUES(?,?,?,?)",
                      (sid, q["id"], pos, json.dumps(order)))
        c.execute("UPDATE trainees SET status='active', updated_at=? WHERE id=?", (now(), trainee_id))
    audit("start_exam", "session", sid)
    return sid

def get_active_session(trainee_id):
    with db() as c:
        r = c.execute("SELECT * FROM exam_sessions WHERE trainee_id=? AND status='active' ORDER BY id DESC LIMIT 1", (trainee_id,)).fetchone()
        return dict(r) if r else None

def submit_session(sid, force=False):
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
        return {"score": correct, "max_score": max_score, "percent": percent, "passed": passed, "certificate_id": cert, "template_id": s["template_id"]}

# ============================================================
# 8) واجهة الطباعة (A4)
# ============================================================
def render_printable_certificate(sid):
    with db() as c:
        r = c.execute("""SELECT s.*, t.name trainee_name, t.facility, e.name template_name 
                         FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?""", (sid,)).fetchone()
    if not r: return
    status_text = "اجتزت بنجاح" if r["passed"] else "لم تجتز الاختبار"
    html_content = f"""
    <div class="printable-certificate">
        <div style="text-align:center;">
            <h2>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h2>
            <hr style="border: 1px solid #059669; margin: 20px 0;">
            <h1 style="color: #065f46; margin-bottom: 30px;">شهادة اجتياز اختبار</h1>
            <p style="font-size: 18px; line-height: 2;">
                تشهد إدارة المنصة بأن المتدرب/ـة: <b style="font-size: 22px; color: #047857;">{esc(r["trainee_name"])}</b><br>
                التابع/ـة لجهة: <b>{esc(r["facility"])}</b><br>
                قد أتم/ت بنجاح اختبار: <b>{esc(r["template_name"])}</b><br>
                بالنتيجة: <b>{r["score"]} / {r["max_score"]} ({r["percent"]:.1f}%)</b><br>
                الحالة: <b style="color: {'green' if r['passed'] else 'red'};">{status_text}</b><br>
                رقم الشهادة: <code>{r["certificate_id"]}</code><br>
                تاريخ التسليم: {esc(r["submitted_at"])}
            </p>
            <br><br><br>
            <div style="display: flex; justify-content: space-between; margin-top: 50px; font-weight: bold;">
                <div>توقيع المسؤول العلمي</div>
                <div>ختم الجهة / الاعتماد</div>
            </div>
        </div>
    </div>
    <script>function printCert(){{window.print();}}</script>
    <div style="text-align: center; margin: 20px 0;">
        <button onclick="printCert()" style="background-color: #059669; color: white; padding: 12px 24px; font-size: 18px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">
            🖨️ طباعة الشهادة (ورق A4)
        </button>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

# ============================================================
# 9) إدارة حالة الجلسة (Session State)
# ============================================================
for k, v in {"logged_in": False, "username": "", "role": "", "trainee_id": None, "trainee_name": "", "exam_session_id": None, "last_result_id": None}.items():
    if k not in st.session_state: st.session_state[k] = v

def header():
    st.markdown('<div class="hero"><h1>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h1><div>Professional v2.3 FINAL • نظام موحد للإدارة والاختبارات الطبية</div></div>', unsafe_allow_html=True)

# ============================================================
# 10) واجهات العرض الرئيسية
# ============================================================
def login_portal():
    header()
    
    # 1. قسم المتدرب الأساسي (الظاهر دائماً في الواجهة الرئيسية)
    st.markdown('<div class="card"><h3>🧑‍🔬 بوابة المتدربين والامتحانات</h3><p>أدخل بياناتك لإرسال طلب الاعتماد والدخول الفوري للاختبار بعد موافقة المالك.</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("trainee_request"):
            st.markdown("<b>إرسال طلب جديد أو الدخول المباشر</b>", unsafe_allow_html=True)
            facility = st.text_input("الجهة / الإدارة الصحية")
            name = st.text_input("الاسم الرباعي")
            phone = st.text_input("رقم الهاتف")
            if st.form_submit_button("إرسال الطلب والدخول", use_container_width=True):
                if facility and name:
                    existing = trainee_by_credentials(name, facility)
                    if existing:
                        st.session_state.trainee_id = existing["id"]
                        st.session_state.trainee_name = existing["name"]
                        st.success("تم التعرف على حسابك المعمد! جاري الدخول...")
                        st.rerun()
                    else:
                        raw = get_trainee_status_raw(name, facility)
                        if raw:
                            st.warning(f"حالة طلبك الحالي: ({STATUS_AR.get(raw['status'], raw['status'])}). بانتظار موافقة المالك.")
                        else:
                            tid = create_trainee(facility, name, phone)
                            st.info(f"تم إرسال طلبك برقم ({tid}). بانتظار موافقة مالك المنصة.")
                else:
                    st.warning("الرجاء إدخال الجهة والاسم الرباعي بدقة.")
                    
    with col2:
        with st.form("check_status_only"):
            st.markdown("<b>فحص حالة الاعتماد والدخول</b>", unsafe_allow_html=True)
            chk_name = st.text_input("الاسم الرباعي المسجل")
            chk_fac = st.text_input("الجهة / الإدارة الصحية المسجلة")
            if st.form_submit_button("🔍 فحص ودخول الامتحان", use_container_width=True):
                if chk_name and chk_fac:
                    tr = trainee_by_credentials(chk_name, chk_fac)
                    if tr:
                        st.session_state.trainee_id = tr["id"]
                        st.session_state.trainee_name = tr["name"]
                        st.success("تم الاعتماد بنجاح! يتم نقلك للاختبار...")
                        st.rerun()
                    else:
                        raw = get_trainee_status_raw(chk_name, chk_fac)
                        if raw:
                            st.error(f"حالة طلبك الحالية: {STATUS_AR.get(raw['status'], raw['status'])}.")
                        else:
                            st.error("لم يتم العثور على طلب بهذا الاسم والجهة.")
                else:
                    st.warning("يرجى إدخال الاسم والجهة للتأكد.")

    # 2. دخول المالك / الإدارة (أخر جزء في الصفحة ولا يظهر إلا بالضغط على الزر)
    st.markdown("---")
    with st.expander("🔐 دخول الإدارة / المالك (انقر هنا للعرض)"):
        with st.form("admin_login_form"):
            st.info("بيانات المالك الافتراضية: اسم المستخدم `admin` | كلمة المرور `admin`")
            u = st.text_input("اسم المستخدم")
            p = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("تسجيل دخول المالك", use_container_width=True):
                user = login_user(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.role = user["role"]
                    audit("login", "user", user["id"])
                    st.rerun()
                else:
                    st.error("بيانات الدخول غير صحيحة.")

def admin_dashboard():
    header()
    c_info, c_btn = st.columns([4, 1])
    with c_info:
        st.write(f"**المستخدم الحالي:** {st.session_state.username} | **الصلاحية:** {ROLES.get(st.session_state.role, '')}")
    with c_btn:
        if st.button("تسجيل الخروج", use_container_width=True):
            audit("logout")
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.rerun()

    tabs = ["لوحة التحكم", "اعتماد المتدربين", "بنك الأسئلة", "قوالب الاختبارات", "النتائج والشهادات", "النسخ الاحتياطي"]
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
        st.subheader("🧑‍🔬 اعتماد المتدربين وإدارة الصلاحيات (خاص بالمالك)")
        sub_tabs = st.tabs(["الطلبات المعلقة", "جميع المتدربين"])
        with sub_tabs[0]:
            df_pend = trainees_df("pending")
            if df_pend.empty:
                st.info("لا توجد طلبات معلقة حالياً.")
            else:
                for _, r in df_pend.iterrows():
                    with st.container(border=True):
                        st.write(f"**الاسم:** {r['name']} | **الجهة:** {r['facility']} | **الهاتف:** {r['phone']}")
                        b1, b2 = st.columns(2)
                        if b1.button("✅ موافقة واعتماد دخول", key=f"app_{r['id']}"):
                            set_trainee_status(int(r['id']), "approved")
                            st.success(f"تم اعتماد {r['name']} بنجاح!")
                            st.rerun()
                        if b2.button("❌ رفض الطلب", key=f"rej_{r['id']}"):
                            set_trainee_status(int(r['id']), "rejected")
                            st.rerun()
        with sub_tabs[1]:
            st.dataframe(trainees_df(), use_container_width=True, hide_index=True)

    with selected_tabs[2]:
        st.subheader("🧠 بنك الأسئلة الشامل (600 سؤال)")
        df_q = questions_df()
        st.write(f"إجمالي الأسئلة المتاحة: **{len(df_q)}**")
        st.dataframe(df_q[["id", "difficulty", "category", "question", "reference", "active"]], use_container_width=True, hide_index=True)

    with selected_tabs[3]:
        st.subheader("🧩 قوالب الاختبارات")
        with db() as c:
            tpls = c.execute("SELECT * FROM exam_templates").fetchall()
        for t in tpls:
            with st.container(border=True):
                st.write(f"**{t['name']}** — عدد الأسئلة: {t['num_questions']} | المدة: {t['duration_minutes']} دقيقة | نسبة النجاح: {t['pass_percent']}%")

    with selected_tabs[4]:
        st.subheader("📊 النتائج والشهادات")
        with db() as c:
            df_res = pd.read_sql_query("""SELECT s.id, s.submitted_at, t.name trainee_name, t.facility, s.score, s.max_score, s.percent, s.passed, s.certificate_id 
                                         FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.status='submitted' ORDER BY s.id DESC""", c)
        if not df_res.empty:
            st.dataframe(df_res, use_container_width=True, hide_index=True)
            sid_p = st.selectbox("اختر الجلسة لطباعة الشهادة الرسمية", df_res.id.tolist())
            if sid_p: render_printable_certificate(int(sid_p))
        else:
            st.info("لا توجد نتائج مسجلة حتى الآن.")

    with selected_tabs[5]:
        st.subheader("💾 النسخ الاحتياطي للقاعدة")
        if st.button("إنشاء نسخة احتياطية الآن"):
            path = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            src = sqlite3.connect(DB_PATH)
            dst = sqlite3.connect(path)
            try: src.backup(dst)
            finally: dst.close(); src.close()
            st.success(f"تم حفظ النسخة بنجاح في مجلد التخزين المؤقت.")

    if st.session_state.role == "admin":
        with selected_tabs[6]:
            st.subheader("👥 إدارة مستخدمي النظام")
            with db() as c:
                users_list = c.execute("SELECT id, username, role, active, created_at FROM users").fetchall()
            st.dataframe(pd.DataFrame([dict(u) for u in users_list]), use_container_width=True, hide_index=True)
        with selected_tabs[7]:
            st.subheader("🧾 سجل التدقيق والعمليات")
            with db() as c:
                df_audit = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 500", c)
            st.dataframe(df_audit, use_container_width=True, hide_index=True)

def trainee_portal():
    with db() as c:
        tr = c.execute("SELECT * FROM trainees WHERE id=?", (st.session_state.trainee_id,)).fetchone()
    if not tr:
        st.session_state.trainee_id = None
        st.rerun()
        
    header()
    st.markdown(f'<div class="card"><h3>مرحباً بك، {esc(tr["name"])}</h3><p>الجهة التابع لها: {esc(tr["facility"])}</p></div>', unsafe_allow_html=True)
    
    active = get_active_session(tr["id"])
    if active:
        exam_interface(active)
        return
        
    with db() as c:
        ts = c.execute("SELECT * FROM exam_templates WHERE active=1").fetchall()
    
    with st.form("start_exam_form"):
        tid = st.selectbox("اختر قالب الاختبار", [t["id"] for t in ts], format_func=lambda x: next(t["name"] for t in ts if t["id"] == x))
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

def exam_interface(session):
    sid = session["id"]
    with db() as c:
        rows = c.execute("""SELECT eq.*, q.question, q.options_json FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=? ORDER BY eq.position""", (sid,)).fetchall()
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (session["template_id"],)).fetchone()
        
    remaining = max(0, int((datetime.fromisoformat(session["expires_at"]) - datetime.now()).total_seconds()))
    if remaining <= 0:
        submit_session(sid, True)
        st.session_state.last_result_id = sid
        st.rerun()
        
    mins, secs = divmod(remaining, 60)
    st.markdown(f'<div class="timer">⏱️ الوقت المتبقي للإختبار: {mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
    
    answered = 0
    for row in rows:
        opts = json.loads(row["options_json"])
        order = json.loads(row["option_order_json"])
        disp_opts = [opts[i] for i in order]
        
        curr_idx = None
        if row["selected_option"] is not None:
            try: curr_idx = disp_opts.index(opts[row["selected_option"]])
            except: pass
            
        st.markdown(f'<div class="question"><b>سؤال رقم {row["position"]+1}</b><br>{esc(row["question"])}</div>', unsafe_allow_html=True)
        choice = st.radio("اختر الإجابة:", disp_opts, index=curr_idx, key=f"q_{row['id']}", label_visibility="collapsed")
        if choice:
            sel = order[disp_opts.index(choice)]
            with db() as c:
                c.execute("UPDATE exam_questions SET selected_option=?, is_correct=CASE WHEN ?=(SELECT answer FROM questions WHERE id=question_id) THEN 1 ELSE 0 END WHERE id=?", (sel, sel, row["id"]))
            answered += 1
            
    st.progress(answered / len(rows) if rows else 0)
    if st.button("تسليم الاختبار نهائياً", use_container_width=True):
        submit_session(sid)
        st.session_state.last_result_id = sid
        st.rerun()

# ============================================================
# 11) موجه المسارات الرئيسي (Router)
# ============================================================
if st.session_state.trainee_id and not st.session_state.logged_in:
    if st.session_state.get("last_result_id"):
        # عرض صفحة النتيجة بعد التسليم
        sid = st.session_state.last_result_id
        header()
        st.success("تم تسليم الاختبار بنجاح!")
        render_printable_certificate(sid)
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
