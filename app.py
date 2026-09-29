import os, io, re, ast, json, html, sqlite3, hashlib, secrets, random, shutil
from datetime import datetime, timedelta
from contextlib import contextmanager
from urllib.request import urlopen, Request

import pandas as pd
import streamlit as st

# ============================================================
# 1) إعدادات التطبيق
# ============================================================
st.set_page_config(
    page_title="منصة اختبارات معامل المتوطنة - Professional v2.2 FINAL",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "endemic_labs_exam_v2_2.db")
BACKUP_DIR = os.path.join(BASE, "backups")
LEGACY_URL = "https://raw.githubusercontent.com/AhmedSalehHegazy86/Endemic-Labs-Exam/main/app.py"

ROLES = {
    "admin": "مدير النظام",
    "exam_manager": "مسؤول الامتحانات",
    "viewer": "مراقب",
}
DIFF_AR = {"easy": "سهل", "medium": "متوسط", "hard": "صعب"}
STATUS_AR = {"pending": "في انتظار الاعتماد", "approved": "معتمد", "rejected": "مرفوض", "active": "اختبار جارٍ", "completed": "مكتمل"}
PASS_DEFAULT = 60

os.makedirs(BACKUP_DIR, exist_ok=True)

st.markdown("""
<style>
html,body,[class*="css"]{direction:rtl;text-align:right;font-family:"Cairo","Tahoma",sans-serif}
.stApp{background:linear-gradient(135deg,#f6fff8 0%,#e8f5e9 45%,#dcedc8 100%)}
.block-container{max-width:1500px;padding-top:1rem}
.hero{background:linear-gradient(90deg,#14532d,#166534,#3f6212);color:#fff;padding:22px;border-radius:20px;text-align:center;box-shadow:0 8px 25px #0002;margin-bottom:18px}
.card,.question{background:#fff;padding:18px;border-radius:16px;margin-bottom:16px;box-shadow:0 5px 18px #00000012;border-right:6px solid #3f6212}
.metric{background:#fff;padding:18px;border-radius:15px;text-align:center;border-top:4px solid #3f6212;box-shadow:0 5px 16px #00000012}
.metric .v{font-size:28px;font-weight:800;color:#166534}.metric .l{color:#555;font-weight:700}
.badge{display:inline-block;padding:5px 12px;border-radius:20px;background:#e8f5e9;color:#166534;font-weight:800}
.timer{font-size:24px;font-weight:900;text-align:center;background:#fff3cd;border:2px solid #e0a800;padding:10px;border-radius:12px}
.stButton>button{border-radius:12px;font-weight:800;min-height:44px}
[data-testid="stSidebar"]{display:none !important;}

/* تنسيقات الطباعة لورق A4 */
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
        border: 5px solid #166534;
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
# 2) أدوات عامة وأمان
# ============================================================
def now():
    return datetime.now().isoformat(timespec="seconds")

def esc(x):
    return html.escape("" if x is None else str(x))

def normalize_text(x):
    x = "" if x is None else str(x)
    x = re.sub(r"\s+", " ", x.strip())
    return x

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
# 3) SQLite (مع التحديث التلقائي للجداول Migration)
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
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
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
            quality_status TEXT NOT NULL DEFAULT 'pending_review',
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
            require_approval INTEGER NOT NULL DEFAULT 1,
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
        CREATE INDEX IF NOT EXISTS idx_questions_active ON questions(active);
        CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category);
        CREATE INDEX IF NOT EXISTS idx_questions_quality ON questions(quality_status);
        CREATE INDEX IF NOT EXISTS idx_sessions_trainee ON exam_sessions(trainee_id);
        CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
        """)
        
        # ترحيل وإصلاح جدول المتدربين في حال وجود أعمدة قديمة مثل access_pin
        tr_cols = {r["name"] for r in c.execute("PRAGMA table_info(trainees)").fetchall()}
        if tr_cols and "access_pin" in tr_cols:
            c.execute("CREATE TABLE IF NOT EXISTS trainees_new (id INTEGER PRIMARY KEY AUTOINCREMENT, facility TEXT NOT NULL, name TEXT NOT NULL, phone TEXT, status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL, approved_at TEXT, updated_at TEXT NOT NULL)")
            c.execute("INSERT INTO trainees_new(id, facility, name, phone, status, created_at, approved_at, updated_at) SELECT id, facility, name, phone, status, created_at, approved_at, updated_at FROM trainees")
            c.execute("DROP TABLE trainees")
            c.execute("ALTER TABLE trainees_new RENAME TO trainees")

        cols = {r["name"] for r in c.execute("PRAGMA table_info(questions)").fetchall()}
        if "quality_status" not in cols: c.execute("ALTER TABLE questions ADD COLUMN quality_status TEXT NOT NULL DEFAULT 'pending_review'")
        if "reviewer" not in cols: c.execute("ALTER TABLE questions ADD COLUMN reviewer TEXT")
        if "reviewed_at" not in cols: c.execute("ALTER TABLE questions ADD COLUMN reviewed_at TEXT")
        tcols = {r["name"] for r in c.execute("PRAGMA table_info(exam_templates)").fetchall()}
        if "max_attempts" not in tcols: c.execute("ALTER TABLE exam_templates ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 1")
        if "require_approval" not in tcols: c.execute("ALTER TABLE exam_templates ADD COLUMN require_approval INTEGER NOT NULL DEFAULT 1")

        defaults = {
            "schema_version": "2.2",
            "legacy_import_done": "0",
        }
        for k, v in defaults.items():
            c.execute("INSERT OR IGNORE INTO app_meta(key,value) VALUES(?,?)", (k, v))
        if c.execute("SELECT COUNT(*) n FROM exam_templates").fetchone()["n"] == 0:
            c.execute("""INSERT INTO exam_templates
                (name,num_questions,duration_minutes,pass_percent,easy_pct,medium_pct,hard_pct,categories_json,max_attempts,require_approval,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("الاختبار القياسي",10,20,60,20,50,30,"[]",1,1,now(),now()))

def meta(key, default=None):
    with db() as c:
        r = c.execute("SELECT value FROM app_meta WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

def set_meta(key, value):
    with db() as c:
        c.execute("INSERT OR REPLACE INTO app_meta(key,value) VALUES(?,?)", (key, str(value)))

def audit(action, entity=None, entity_id=None, details=None):
    actor = st.session_state.get("username") or st.session_state.get("trainee_name") or "system"
    with db() as c:
        c.execute("INSERT INTO audit_logs(actor,action,entity,entity_id,details,created_at) VALUES(?,?,?,?,?,?)",
                  (actor, action, entity, entity_id, json.dumps(details, ensure_ascii=False) if isinstance(details, dict) else details, now()))

init_db()

# ============================================================
# 4) استيراد بنك الأسئلة القديم بأمان
# ============================================================
class LegacyEvalError(Exception):
    pass

def safe_eval(node, env):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        if node.id == "range":
            return range
        raise LegacyEvalError(f"اسم غير مسموح: {node.id}")
    if isinstance(node, ast.List): return [safe_eval(x, env) for x in node.elts]
    if isinstance(node, ast.Tuple): return tuple(safe_eval(x, env) for x in node.elts)
    if isinstance(node, ast.Dict): return {safe_eval(k, env): safe_eval(v, env) for k,v in zip(node.keys,node.values)}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v=safe_eval(node.operand,env); return -v if isinstance(node.op,ast.USub) else +v
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add,ast.Sub,ast.Mult,ast.Mod,ast.Div,ast.FloorDiv)):
        a,b=safe_eval(node.left,env),safe_eval(node.right,env)
        return {ast.Add:lambda:a+b,ast.Sub:lambda:a-b,ast.Mult:lambda:a*b,ast.Mod:lambda:a%b,ast.Div:lambda:a/b,ast.FloorDiv:lambda:a//b}[type(node.op)]()
    if isinstance(node, ast.IfExp): return safe_eval(node.body,env) if safe_eval(node.test,env) else safe_eval(node.orelse,env)
    if isinstance(node, ast.Compare):
        left=safe_eval(node.left,env)
        for op,comp in zip(node.ops,node.comparators):
            right=safe_eval(comp,env)
            ok = isinstance(op,ast.Eq) and left==right or isinstance(op,ast.NotEq) and left!=right or isinstance(op,ast.Lt) and left<right or isinstance(op,ast.LtE) and left<=right or isinstance(op,ast.Gt) and left>right or isinstance(op,ast.GtE) and left>=right
            if not ok:return False
            left=right
        return True
    if isinstance(node, ast.JoinedStr):
        out=""
        for v in node.values:
            if isinstance(v,ast.Constant): out += str(v.value)
            elif isinstance(v,ast.FormattedValue): out += str(safe_eval(v.value,env))
            else: raise LegacyEvalError("f-string غير مدعوم")
        return out
    if isinstance(node, ast.Call):
        if isinstance(node.func,ast.Name) and node.func.id=="range":
            return range(*[safe_eval(a,env) for a in node.args])
        if isinstance(node.func,ast.Attribute) and node.func.attr in ("append","extend"):
            raise LegacyEvalError("calls handled by executor")
    raise LegacyEvalError(f"نوع AST غير مدعوم: {type(node).__name__}")

def execute_legacy_block(source):
    tree=ast.parse(source)
    env={"QUESTIONS_DB":[]}
    start=None
    for i,n in enumerate(tree.body):
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="QUESTIONS_DB" for t in n.targets):
            start=i; break
    if start is None: raise LegacyEvalError("QUESTIONS_DB غير موجود")
    nodes=[]
    for n in tree.body[start:]:
        if isinstance(n,(ast.FunctionDef,ast.ClassDef,ast.Import,ast.ImportFrom)): break
        nodes.append(n)
    for n in nodes:
        if isinstance(n,ast.Assign):
            val=safe_eval(n.value,env)
            for t in n.targets:
                if isinstance(t,ast.Name): env[t.id]=val
        elif isinstance(n,ast.For):
            iterable=safe_eval(n.iter,env)
            for item in iterable:
                if isinstance(n.target,ast.Name): env[n.target.id]=item
                for stmt in n.body:
                    if isinstance(stmt,ast.Expr) and isinstance(stmt.value,ast.Call):
                        call=stmt.value
                        if isinstance(call.func,ast.Attribute) and call.func.attr in ("append","extend") and isinstance(call.func.value,ast.Name):
                            obj=env.get(call.func.value.id)
                            if obj is None: raise LegacyEvalError("قائمة غير موجودة")
                            arg=safe_eval(call.args[0],env)
                            if call.func.attr=="append": obj.append(arg)
                            else: obj.extend(arg)
                        else: raise LegacyEvalError("عملية غير مسموحة")
                    elif isinstance(stmt,ast.Assign):
                        val=safe_eval(stmt.value,env)
                        for t in stmt.targets:
                            if isinstance(t,ast.Name): env[t.id]=val
                    else: raise LegacyEvalError("تعليمة legacy غير مسموحة")
        elif isinstance(n,ast.Expr):
            call=n.value
            if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr in ("extend","append") and isinstance(call.func.value,ast.Name):
                obj=env.get(call.func.value.id); arg=safe_eval(call.args[0],env)
                if call.func.attr=="append":obj.append(arg)
                else:obj.extend(arg)
            else: raise LegacyEvalError("تعبير غير مسموح")
        else: raise LegacyEvalError(f"تعليمة غير مدعومة: {type(n).__name__}")
    return env["QUESTIONS_DB"]

def normalize_question(q, source="legacy"):
    if not isinstance(q,dict): return None
    options=q.get("options") or []
    try: answer=int(q.get("answer",0))
    except: answer=0
    if not q.get("question") or len(options)<2 or not 0 <= answer < len(options): return None
    difficulty=q.get("difficulty","medium")
    if difficulty not in DIFF_AR: difficulty="medium"
    category=normalize_text(q.get("category") or "عام")
    question=normalize_text(q.get("question"))
    options=[normalize_text(x) for x in options]
    explanation=normalize_text(q.get("explanation") or "")
    fp=hashlib.sha256((question+"|"+"|".join(options)).encode("utf-8")).hexdigest()
    return {"legacy_id":q.get("id"),"difficulty":difficulty,"category":category,"question":question,"options":options,"answer":answer,"explanation":explanation,"reference":q.get("reference", ""),"quality_status":q.get("quality_status", "pending_review"),"source":source,"fingerprint":fp}

def import_questions(questions, replace=False):
    valid=[]; seen=set()
    for q in questions:
        nq=normalize_question(q)
        if nq and nq["fingerprint"] not in seen:
            seen.add(nq["fingerprint"]); valid.append(nq)
    inserted=updated=skipped=0
    with db() as c:
        if replace:
            c.execute("DELETE FROM questions")
        for q in valid:
            existing=c.execute("SELECT id FROM questions WHERE fingerprint=?",(q["fingerprint"],)).fetchone()
            if existing:
                skipped+=1; continue
            c.execute("""INSERT INTO questions(legacy_id,difficulty,category,question,options_json,answer,explanation,reference,quality_status,source,active,fingerprint,created_at,updated_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (q["legacy_id"],q["difficulty"],q["category"],q["question"],json.dumps(q["options"],ensure_ascii=False),q["answer"],q["explanation"],q["reference"],q["quality_status"],q["source"],1,q["fingerprint"],now(),now()))
            inserted+=1
    return inserted,updated,skipped,len(valid)

def load_legacy_file(path):
    with open(path,"r",encoding="utf-8") as f:return f.read()

def import_legacy_source(source, label="legacy"):
    qs=execute_legacy_block(source)
    result=import_questions(qs)
    set_meta("legacy_import_done","1")
    set_meta("legacy_import_at",now())
    set_meta("legacy_import_count",result[3])
    audit("import_questions", "questions", None, {"source":label,"valid":result[3],"inserted":result[0],"skipped":result[2]})
    return result

# ============================================================
# 5) حسابات وإدارة المستخدمين
# ============================================================
def ensure_admin():
    with db() as c:
        if c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]==0:
            username=os.getenv("ENDEMIC_ADMIN_USER","admin")
            password=os.getenv("ENDEMIC_ADMIN_PASSWORD","ChangeMe_2026!")
            c.execute("INSERT INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,?,?)",
                      (username,hash_password(password),"admin",1,now()))
            c.execute("INSERT OR REPLACE INTO app_meta(key,value) VALUES(?,?)", ("default_admin_created","1"))
            c.execute("INSERT OR REPLACE INTO app_meta(key,value) VALUES(?,?)", ("must_change_default_admin","1" if password=="ChangeMe_2026!" else "0"))
ensure_admin()

def seed_final_questions():
    with db() as c:
        if c.execute("SELECT COUNT(*) n FROM questions").fetchone()["n"] > 0: return
    seeds=[
      {"question":"ما هي المرحلة المعدية للإنسان في Schistosoma mansoni؟","options":["Miracidium","Cercaria","Metacercaria","Egg"],"answer":1,"difficulty":"easy","category":"البلهارسيا","explanation":"السركاريا تخرج من القوقع وتخترق جلد الإنسان أثناء التعرض للماء الملوث.","reference":"Garcia, Diagnostic Medical Parasitology; WHO schistosomiasis materials"},
      {"question":"ما هو العائل الوسيط الشائع لـ Schistosoma mansoni؟","options":["Biomphalaria","Lymnaea","Bulinus","Culex"],"answer":0,"difficulty":"easy","category":"البلهارسيا","explanation":"قواقع جنس Biomphalaria هي العائل الوسيط لـ S. mansoni.","reference":"Garcia, Diagnostic Medical Parasitology"},
      {"question":"ما الهدف الأساسي من طريقة Kato-Katz؟","options":["كشف الطفيليات الدموية","التقدير الكمي لبيض الديدان في البراز","زرع البكتيريا","كشف الأجسام المضادة"],"answer":1,"difficulty":"easy","category":"Kato-Katz","explanation":"تستخدم Kato-Katz لفحص البراز والكشف عن بيض الديدان، ويمكن استخدامها لتقدير شدة العدوى بعدد البيوض لكل غرام براز.","reference":"WHO; Garcia, Diagnostic Medical Parasitology"},
      {"question":"ما المرحلة المعدية الشائعة لـ Fasciola hepatica للإنسان؟","options":["Egg","Miracidium","Metacercaria","Redia"],"answer":2,"difficulty":"easy","category":"الفاشيولا","explanation":"تحدث العدوى غالبًا بابتلاع الميتاسركاريا الموجودة على النباتات المائية أو في الماء الملوث.","reference":"Garcia, Diagnostic Medical Parasitology"},
      {"question":"أي جزء في المجهر الضوئي يركز الضوء على العينة؟","options":["Condenser","Nosepiece","Stage clip","Eyepiece"],"answer":0,"difficulty":"easy","category":"المجهر","explanation":"المكثف يجمع ويركز الضوء على العينة.","reference":"Cheesbrough, District Laboratory Practice in Tropical Countries"},
      {"question":"ما الزيت المستخدم عادة مع العدسة الشيئية 100×؟","options":["Immersion oil","Distilled water","Ethanol","Glycerol only"],"answer":0,"difficulty":"easy","category":"المجهر","explanation":"عدسة 100× الزيتية تستخدم immersion oil مناسبًا لتحسين القدرة على الفصل البصري.","reference":"Cheesbrough, District Laboratory Practice in Tropical Countries"},
      {"question":"أي عبارة تصف بيضة Taenia saginata؟","options":["يمكن تمييزها بسهولة عن T. solium بالمجهر الضوئي الروتيني","ذات غلاف مخطط شعاعيًا ولا يمكن عادة التفريق بين بيض النوعين روتينيًا","ذات شوكة طرفية واضحة","ذات سدادتين قطبيتين"],"answer":1,"difficulty":"hard","category":"الديدان الشريطية","explanation":"بيض Taenia spp. متشابه مورفولوجيًا ولا يمكن الاعتماد على البيضة وحدها للتمييز بين T. saginata وT. solium.","reference":"Garcia, Diagnostic Medical Parasitology"},
      {"question":"ما أفضل إجراء عام عند انسكاب مادة بيولوجية يحتمل أن تكون معدية؟","options":["تنظيفها فورًا باليد","اتباع SOP وتقييم الخطر واستخدام وسائل الوقاية والتطهير المناسبة","تركها حتى تجف","استخدام ماء فقط دون حماية"],"answer":1,"difficulty":"medium","category":"السلامة الحيوية","explanation":"إدارة الانسكاب يجب أن تكون وفق تقييم المخاطر وSOP المناسبة ووسائل الوقاية والتطهير المعتمدة.","reference":"WHO Laboratory Biosafety Manual, 4th ed."},
      {"question":"أي عبارة صحيحة عن Hymenolepis nana؟","options":["لا يمكن أن تحدث العدوى دون عائل وسيط","يمكن للبيض المعدي أن يبدأ العدوى في الإنسان مباشرة","المرحلة المعدية هي cercaria","تنتقل فقط عبر اللحوم"],"answer":1,"difficulty":"medium","category":"الديدان الشريطية","explanation":"يمكن لبيض H. nana المعدي أن ينتقل مباشرة إلى الإنسان، ولا يلزم عائل وسيط في الدورة المباشرة.","reference":"Garcia, Diagnostic Medical Parasitology"},
      {"question":"في فحص مجهري، ما الإجراء الأكثر أهمية لتجنب حمل نتيجة غير موثوقة بسبب شريحة غير مناسبة؟","options":["قراءة أي شريحة دون فحص الجودة","التأكد من جودة العينة والتحضير والإضاءة والتركيز قبل تفسير النتيجة","زيادة التكبير فقط","تجاهل الضوابط"],"answer":1,"difficulty":"medium","category":"ضبط الجودة","explanation":"جودة العينة والتحضير والإضاءة والتركيز عناصر أساسية قبل تفسير أي نتيجة مجهرية.","reference":"Cheesbrough, District Laboratory Practice in Tropical Countries; WHO LBM4"}
    ]
    for q in seeds:
        try:create_manual_question(q["question"],q["options"],q["answer"],q["difficulty"],q["category"],q["explanation"],q["reference"])
        except Exception: pass
    with db() as c:
        c.execute("UPDATE questions SET quality_status='approved',reviewer='system-seed',reviewed_at=? WHERE source='manual' AND quality_status='pending_review'",(now(),))

def login(username,password):
    with db() as c:
        r=c.execute("SELECT * FROM users WHERE username=? AND active=1",(username.strip(),)).fetchone()
        if r and verify_password(password,r["password_hash"]):
            c.execute("UPDATE users SET last_login=? WHERE id=?",(now(),r["id"]))
            return dict(r)
    return None

def create_user(username,password,role):
    if len(password)<8: raise ValueError("كلمة المرور يجب ألا تقل عن 8 أحرف")
    with db() as c:
        c.execute("INSERT INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,?,?)",(username.strip(),hash_password(password),role,1,now()))

def get_user_list():
    with db() as c:return c.execute("SELECT id,username,role,active,created_at,last_login FROM users ORDER BY id").fetchall()

# ============================================================
# 6) المتدربون
# ============================================================
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

def set_trainee_status(tid,status):
    with db() as c:c.execute("UPDATE trainees SET status=?,updated_at=?,approved_at=CASE WHEN ?='approved' THEN ? ELSE approved_at END WHERE id=?",(status,now(),status,now(),tid))
    audit("update_trainee","trainee",tid,{"status":status})

def trainees_df(status=None):
    with db() as c:
        q="SELECT id,facility,name,phone,status,created_at,approved_at FROM trainees"
        args=[]
        if status:q+=" WHERE status=?";args=[status]
        q+=" ORDER BY id DESC"
        return pd.read_sql_query(q, c, params=args)

# ============================================================
# 7) الأسئلة والقوالب
# ============================================================
def questions_df(active_only=False):
    with db() as c:
        q="SELECT id,legacy_id,difficulty,category,question,options_json,answer,explanation,reference,quality_status,reviewer,reviewed_at,source,active FROM questions"
        if active_only:q+=" WHERE active=1"
        q+=" ORDER BY id"
        return pd.read_sql_query(q,c)

def question_by_id(qid):
    with db() as c:
        r=c.execute("SELECT * FROM questions WHERE id=?",(qid,)).fetchone()
        return dict(r) if r else None

def review_question(qid, status, reference=None):
    if status not in ("approved","rejected","pending_review"):
        raise ValueError("حالة مراجعة غير صحيحة")
    with db() as c:
        c.execute("UPDATE questions SET quality_status=?,reference=COALESCE(?,reference),reviewer=?,reviewed_at=?,updated_at=? WHERE id=?",(status,reference,st.session_state.get("username"),now() if status != "pending_review" else None,now(),qid))
    audit("review_question","question",qid,{"status":status,"reference":reference})

def update_question(qid, question, options, answer, difficulty, category, explanation, reference, active=1):
    nq=normalize_question({"question":question,"options":options,"answer":answer,"difficulty":difficulty,"category":category,"explanation":explanation,"reference":reference,"quality_status":"pending_review"})
    if not nq: raise ValueError("بيانات السؤال غير صحيحة")
    with db() as c:
        other=c.execute("SELECT id FROM questions WHERE fingerprint=? AND id<>?",(nq["fingerprint"],qid)).fetchone()
        if other: raise ValueError("يوجد سؤال مطابق بالفعل")
        c.execute("""UPDATE questions SET difficulty=?,category=?,question=?,options_json=?,answer=?,explanation=?,reference=?,active=?,fingerprint=?,quality_status='pending_review',reviewer=NULL,reviewed_at=NULL,updated_at=? WHERE id=?""",(nq["difficulty"],nq["category"],nq["question"],json.dumps(nq["options"],ensure_ascii=False),nq["answer"],nq["explanation"],nq["reference"],int(active),nq["fingerprint"],now(),qid))
    audit("update_question","question",qid)

def create_manual_question(question, options, answer, difficulty, category, explanation, reference):
    nq=normalize_question({"question":question,"options":options,"answer":answer,"difficulty":difficulty,"category":category,"explanation":explanation,"reference":reference,"quality_status":"pending_review"},source="manual")
    if not nq: raise ValueError("بيانات السؤال غير صحيحة")
    with db() as c:
        c.execute("""INSERT INTO questions(legacy_id,difficulty,category,question,options_json,answer,explanation,reference,quality_status,source,active,fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(None,nq["difficulty"],nq["category"],nq["question"],json.dumps(nq["options"],ensure_ascii=False),nq["answer"],nq["explanation"],nq["reference"],"pending_review","manual",1,nq["fingerprint"],now(),now()))
        qid=c.execute("SELECT last_insert_rowid() id").fetchone()["id"]
    audit("create_question","question",qid)
    return qid

def templates():
    with db() as c:return c.execute("SELECT * FROM exam_templates WHERE active=1 ORDER BY id").fetchall()

def template_by_id(tid):
    with db() as c:return c.execute("SELECT * FROM exam_templates WHERE id=?",(tid,)).fetchone()

def choose_questions(t):
    cats=json.loads(t["categories_json"] or "[]")
    with db() as c:
        q="SELECT * FROM questions WHERE active=1"; args=[]
        if int(t["require_approval"]): q += " AND quality_status='approved'"
        if cats:
            q += " AND category IN (%s)" % ",".join("?"*len(cats)); args.extend(cats)
        rows=[dict(r) for r in c.execute(q,args).fetchall()]
    random.shuffle(rows)
    target=int(t["num_questions"])
    if len(rows)<target: raise ValueError(f"عدد الأسئلة النشطة المتاحة ({len(rows)}) أقل من المطلوب ({target}).")
    buckets={k:[r for r in rows if r["difficulty"]==k] for k in DIFF_AR}
    plan={"easy":round(target*t["easy_pct"]/100),"medium":round(target*t["medium_pct"]/100)}
    plan["hard"]=target-plan["easy"]-plan["medium"]
    selected=[]
    for d,n in plan.items():selected.extend(random.sample(buckets[d],min(n,len(buckets[d]))))
    if len(selected)<target:
        used={r["id"] for r in selected}; pool=[r for r in rows if r["id"] not in used]; random.shuffle(pool); selected.extend(pool[:target-len(selected)])
    random.shuffle(selected)
    return selected[:target]

# ============================================================
# 8) جلسات الامتحان
# ============================================================
def start_session(trainee_id,template_id):
    t=template_by_id(template_id)
    if not t: raise ValueError("قالب الاختبار غير موجود")
    with db() as c:
        active=c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND status='active'",(trainee_id,)).fetchone()
        if active: raise ValueError("يوجد اختبار نشط بالفعل لهذا المتدرب.")
        if not int(t["allow_retake"]):
            done=c.execute("SELECT COUNT(*) n FROM exam_sessions WHERE trainee_id=? AND template_id=? AND status='submitted'",(trainee_id,template_id)).fetchone()["n"]
            if done >= 1: raise ValueError("هذا الاختبار تم أداؤه من قبل، وإعادة الاختبار غير مفعلة.")
        else:
            done=c.execute("SELECT COUNT(*) n FROM exam_sessions WHERE trainee_id=? AND template_id=? AND status='submitted'",(trainee_id,template_id)).fetchone()["n"]
            if done >= int(t["max_attempts"]): raise ValueError(f"تم استنفاد عدد المحاولات المسموح به ({t['max_attempts']}).")
    qs=choose_questions(t)
    started=datetime.now(); expires=started+timedelta(minutes=int(t["duration_minutes"]))
    with db() as c:
        c.execute("UPDATE exam_sessions SET status='expired',submitted_at=? WHERE trainee_id=? AND status='active' AND expires_at<?",(now(),trainee_id,now()))
        cur=c.execute("INSERT INTO exam_sessions(trainee_id,template_id,started_at,expires_at,status) VALUES(?,?,?,?,?)",
                      (trainee_id,template_id,started.isoformat(timespec="seconds"),expires.isoformat(timespec="seconds"),"active"))
        sid=cur.lastrowid
        for pos,q in enumerate(qs):
            order=list(range(len(json.loads(q["options_json"]))));
            if t["shuffle_options"]:random.shuffle(order)
            c.execute("INSERT INTO exam_questions(session_id,question_id,position,option_order_json) VALUES(?,?,?,?)",(sid,q["id"],pos,json.dumps(order)))
        c.execute("UPDATE trainees SET status='active',updated_at=? WHERE id=?",(now(),trainee_id))
    audit("start_exam","session",sid,{"trainee_id":trainee_id,"template_id":template_id})
    return sid

def get_active_session(trainee_id):
    with db() as c:
        r=c.execute("SELECT * FROM exam_sessions WHERE trainee_id=? AND status='active' ORDER BY id DESC LIMIT 1",(trainee_id,)).fetchone()
        return dict(r) if r else None

def session_questions(sid):
    with db() as c:
        rows=c.execute("""SELECT eq.*,q.question,q.options_json,q.answer,q.explanation,q.reference,q.difficulty,q.category
                         FROM exam_questions eq JOIN questions q ON q.id=eq.question_id
                         WHERE eq.session_id=? ORDER BY eq.position""",(sid,)).fetchall()
        return [dict(r) for r in rows]

def save_answer(sid,eqid,selected):
    with db() as c:c.execute("UPDATE exam_questions SET selected_option=?,is_correct=CASE WHEN ?=(SELECT answer FROM questions WHERE id=question_id) THEN 1 ELSE 0 END WHERE id=? AND session_id=?",(selected,selected,eqid,sid))

def submit_session(sid,force=False):
    with db() as c:
        s=c.execute("SELECT * FROM exam_sessions WHERE id=?",(sid,)).fetchone()
        if not s or s["status"]!="active": return None
        rows=c.execute("SELECT eq.*,q.answer FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=?",(sid,)).fetchall()
        correct=sum(1 for r in rows if r["selected_option"] is not None and int(r["selected_option"])==int(r["answer"]))
        max_score=len(rows); percent=(correct/max_score*100) if max_score else 0
        t=c.execute("SELECT * FROM exam_templates WHERE id=?",(s["template_id"],)).fetchone()
        passed=1 if percent>=float(t["pass_percent"]) else 0
        cert=f"ELX-{sid:06d}"
        status="submitted" if not force else "submitted"
        c.execute("UPDATE exam_sessions SET status=?,submitted_at=?,score=?,max_score=?,percent=?,passed=?,certificate_id=? WHERE id=?",
                  (status,now(),correct,max_score,percent,passed,cert,sid))
        c.execute("UPDATE trainees SET status='completed',updated_at=? WHERE id=?",(now(),s["trainee_id"]))
        return {"score":correct,"max_score":max_score,"percent":percent,"passed":passed,"certificate_id":cert,"template_id":s["template_id"],"trainee_id":s["trainee_id"]}

def session_result(sid):
    with db() as c:
        r=c.execute("""SELECT s.*,t.name trainee_name,t.facility,t.phone,e.name template_name,e.pass_percent
                       FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?""",(sid,)).fetchone()
        return dict(r) if r else None

seed_final_questions()

# ============================================================
# 9) قالب الطباعة A4 المباشر
# ============================================================
def render_printable_certificate(sid):
    r = session_result(sid)
    if not r: return
    status_text = "اجتزت بنجاح" if r["passed"] else "لم تجتز الاختبار"
    html_content = f"""
    <div class="printable-certificate">
        <div style="text-align:center;">
            <h2>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h2>
            <hr style="border: 1px solid #166534; margin: 20px 0;">
            <h1 style="color: #166534; margin-bottom: 30px;">شهادة اجتياز اختبار</h1>
            <p style="font-size: 18px; line-height: 2;">
                تشهد إدارة المنصة بأن المتدرب/ـة: <b style="font-size: 22px; color: #14532d;">{esc(r["trainee_name"])}</b><br>
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
    <script>
        function printCert() {{
            window.print();
        }}
    </script>
    <div style="text-align: center; margin: 20px 0;">
        <button onclick="printCert()" style="background-color: #166534; color: white; padding: 12px 24px; font-size: 18px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">
            🖨️ طباعة الشهادة (ورق A4)
        </button>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

# ============================================================
# 10) Session state
# ============================================================
for k,v in {"logged_in":False,"username":"","role":"","trainee_id":None,"trainee_name":"","exam_session_id":None,"last_result_id":None}.items():
    if k not in st.session_state:st.session_state[k]=v

# ============================================================
# 11) الواجهة
# ============================================================
def header():
    st.markdown('<div class="hero"><h1>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h1><div>Professional v2.2 FINAL • SQLite • بنك أسئلة قابل للإدارة • امتحانات مؤقتة • نتائج وطباعة A4</div></div>',unsafe_allow_html=True)

def login_page():
    header(); a,b=st.columns(2)
    with a:
        st.markdown('<div class="card"><h3>🔐 دخول الإدارة</h3></div>',unsafe_allow_html=True)
        with st.form("login"):
            u=st.text_input("اسم المستخدم")
            p=st.text_input("كلمة المرور",type="password")
            if st.form_submit_button("تسجيل الدخول",use_container_width=True):
                user=login(u,p)
                if user:
                    st.session_state.logged_in=True;st.session_state.username=user["username"];st.session_state.role=user["role"]
                    audit("login","user",user["id"]);st.rerun()
                st.error("بيانات الدخول غير صحيحة.")
    with b:
        st.markdown('<div class="card"><h3>🧑‍🔬 دخول المتدرب</h3><p>أدخل الاسم والجهة بعد اعتماد طلبك لبدء الاختبار.</p></div>',unsafe_allow_html=True)
        with st.form("trainee_login"):
            tname=st.text_input("الاسم الرباعي")
            tfacility=st.text_input("الجهة / الإدارة الصحية")
            if st.form_submit_button("دخول الاختبار",use_container_width=True):
                tr=trainee_by_credentials(tname, tfacility)
                if tr:
                    st.session_state.trainee_id=tr["id"];st.session_state.trainee_name=tr["name"];st.session_state.exam_session_id=None;st.rerun()
                st.error("البيانات غير صحيحة أو أن الحساب لم يتم اعتماده بعد.")
        with st.expander("طلب اعتماد متدرب جديد"):
            with st.form("register"):
                facility=st.text_input("الجهة / الإدارة الصحية", key="reg_fac")
                name=st.text_input("الاسم الرباعي", key="reg_name")
                phone=st.text_input("رقم الهاتف")
                if st.form_submit_button("إرسال طلب الاعتماد"):
                    if facility and name:
                        tid=create_trainee(facility,name,phone);st.success(f"تم إرسال الطلب بنجاح. رقم الطلب: {tid}")
                    else:st.warning("أكمل الجهة والاسم.")

def dashboard():
    header()
    col_info, col_btn = st.columns([4, 1])
    with col_info:
        st.write(f"**المستخدم:** {st.session_state.username} | **الصلاحية:** {ROLES.get(st.session_state.role,'')}")
    with col_btn:
        if st.button("تسجيل الخروج", use_container_width=True):
            audit("logout"); st.session_state.logged_in=False; st.session_state.username=""; st.session_state.role=""; st.rerun()

    pages = ["لوحة التحكم", "المتدربون", "بنك الأسئلة", "قوالب الاختبارات", "النتائج", "النسخ الاحتياطي"]
    if st.session_state.role == "admin":
        pages += ["المستخدمون", "سجل التدقيق"]
    
    selected_tab = st.tabs(pages)

    with selected_tab[0]:
        st.subheader("📊 لوحة التحكم")
        with db() as c:
            counts=c.execute("""SELECT
                (SELECT COUNT(*) FROM trainees) trainees,
                (SELECT COUNT(*) FROM questions) questions,
                (SELECT COUNT(*) FROM questions WHERE active=1 AND quality_status='approved') approved,
                (SELECT COUNT(*) FROM questions WHERE quality_status='pending_review') pending,
                (SELECT COUNT(*) FROM exam_sessions WHERE status='submitted') exams,
                (SELECT COALESCE(AVG(percent),0) FROM exam_sessions WHERE status='submitted') avgp
            """).fetchone()
        cols=st.columns(6)
        for c_box,l,v in zip(cols,["المتدربون","كل الأسئلة","المعتمدة","تحت المراجعة","الامتحانات","متوسط النتائج"],[counts["trainees"],counts["questions"],counts["approved"],counts["pending"],counts["exams"],f'{counts["avgp"]:.1f}%']):
            c_box.markdown(f'<div class="metric"><div class="v">{esc(v)}</div><div class="l">{esc(l)}</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="card"><b>وضع الجودة:</b> الأسئلة غير المعتمدة لا تدخل الامتحان إذا كان القالب مضبوطًا على طلب الاعتماد العلمي.</div>',unsafe_allow_html=True)
        with db() as c:
            df=pd.read_sql_query("SELECT category,COUNT(*) total,SUM(CASE WHEN quality_status='approved' THEN 1 ELSE 0 END) approved FROM questions GROUP BY category ORDER BY total DESC",c)
        if not df.empty: st.dataframe(df,use_container_width=True,hide_index=True)

    with selected_tab[1]:
        st.subheader("🧑‍🔬 إدارة المتدربين")
        tabs_tr=st.tabs(["طلبات الاعتماد","كل المتدربين"])
        with tabs_tr[0]:
            df=trainees_df("pending")
            if df.empty:st.info("لا توجد طلبات معلقة.")
            else:
                for _,r in df.iterrows():
                    with st.container(border=True):
                        st.write(f"**{r['name']}** — {r['facility']} — {r['phone']}")
                        c1,c2=st.columns(2)
                        if c1.button("اعتماد",key=f"app_{r['id']}"):set_trainee_status(int(r['id']),"approved");st.rerun()
                        if c2.button("رفض",key=f"rej_{r['id']}"):set_trainee_status(int(r['id']),"rejected");st.rerun()
        with tabs_tr[1]:
            df=trainees_df();st.dataframe(df,use_container_width=True,hide_index=True)
            if not df.empty:
                xbuf=io.BytesIO()
                with pd.ExcelWriter(xbuf,engine="openpyxl") as writer:
                    df.to_excel(writer,index=False,sheet_name="trainees")
                st.download_button("⬇️ تصدير Excel",xbuf.getvalue(),file_name="trainees.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with selected_tab[2]:
        st.subheader("🧠 بنك الأسئلة — إدارة واعتماد علمي")
        with st.expander("⬆️ استيراد بنك الأسئلة القديم"):
            st.write("الاستيراد يقرأ QUESTIONS_DB فقط ولا يشغّل التطبيق القديم.")
            uploaded=st.file_uploader("ارفع app.py القديم",type=["py"])
            c1,c2=st.columns(2)
            if c1.button("استيراد الملف المرفوع"):
                if uploaded:
                    try:
                        result=import_legacy_source(uploaded.getvalue().decode("utf-8"),"uploaded app.py")
                        st.success(f"تمت المعالجة: صالح {result[3]} | جديد {result[0]} | مكرر {result[2]}");st.rerun()
                    except Exception as e: st.error(f"فشل الاستيراد: {e}")
                else: st.warning("اختر ملفًا أولًا.")
            if c2.button("جلب نسخة GitHub الرسمية واستيرادها"):
                try:
                    req=Request(LEGACY_URL,headers={"User-Agent":"EndemicLabsExam/2.2"})
                    src=urlopen(req,timeout=20).read().decode("utf-8")
                    result=import_legacy_source(src,"GitHub")
                    st.success(f"تمت المعالجة: صالح {result[3]} | جديد {result[0]} | مكرر {result[2]}");st.rerun()
                except Exception as e: st.error(f"تعذر الجلب: {e}")
        with st.expander("➕ إضافة سؤال يدوي"):
            with st.form("manual_q"):
                q=st.text_area("السؤال")
                opts=[st.text_input(f"الاختيار {i+1}") for i in range(4)]
                ans=st.selectbox("الإجابة الصحيحة",[0,1,2,3],format_func=lambda x:f"الاختيار {x+1}")
                d=st.selectbox("الصعوبة",list(DIFF_AR),format_func=lambda x:DIFF_AR[x])
                cat=st.text_input("التصنيف",value="طفيليات")
                exp=st.text_area("الشرح العلمي")
                ref=st.text_input("المرجع العلمي",value="Garcia, Diagnostic Medical Parasitology")
                if st.form_submit_button("إضافة السؤال"):
                    try: create_manual_question(q,opts,ans,d,cat,exp,ref); st.success("تمت الإضافة، وحالة السؤال: مراجعة مطلوبة."); st.rerun()
                    except Exception as e: st.error(str(e))
        df=questions_df()
        if not df.empty:
            c1,c2,c3,c4=st.columns(4)
            cat=c1.selectbox("التصنيف",["الكل"]+sorted(df.category.dropna().unique().tolist()))
            diff=c2.selectbox("الصعوبة",["الكل"]+list(DIFF_AR.values()))
            quality=c3.selectbox("الجودة",["الكل","معتمد","مراجعة مطلوبة","مرفوض"])
            active=c4.selectbox("الحالة",["الكل","نشط","غير نشط"])
            view=df.copy()
            if cat!="الكل": view=view[view.category==cat]
            if diff!="الكل": view=view[view.difficulty.map(DIFF_AR)==diff]
            qmap={"معتمد":"approved","مراجعة مطلوبة":"pending_review","مرفوض":"rejected"}
            if quality!="الكل": view=view[view.quality_status==qmap[quality]]
            if active=="نشط": view=view[view.active==1]
            if active=="غير نشط": view=view[view.active==0]
            st.write(f"عدد النتائج: **{len(view)}**")
            st.dataframe(view[["id","difficulty","category","question","quality_status","reference","active"]],use_container_width=True,hide_index=True)
            st.download_button("⬇️ تصدير CSV",view.to_csv(index=False).encode("utf-8-sig"),file_name="question_bank_v2_2.csv",mime="text/csv")
            with st.expander("🔎 مراجعة / اعتماد سؤال"):
                qid=st.number_input("ID السؤال",min_value=1,step=1)
                qr=question_by_id(int(qid)) if qid else None
                if qr:
                    st.markdown(f'<div class="question"><b>{esc(qr["question"])}</b><br>الحالة: {esc(qr["quality_status"])}<br>المرجع: {esc(qr["reference"] or "غير محدد")}</div>',unsafe_allow_html=True)
                    a,b,c=st.columns(3)
                    ref2=st.text_input("المرجع المستخدم في الاعتماد",value=qr["reference"] or "",key=f"ref_{qid}")
                    if a.button("✅ اعتماد السؤال"): review_question(qid,"approved",ref2);st.success("تم اعتماد السؤال.");st.rerun()
                    if b.button("⏳ إبقاء للمراجعة"): review_question(qid,"pending_review",ref2);st.rerun()
                    if c.button("❌ رفض السؤال"): review_question(qid,"rejected",ref2);st.rerun()
                    with st.form(f"editq_{qid}"):
                        qtext=st.text_area("نص السؤال",qr["question"])
                        oldopts=json.loads(qr["options_json"]); newopts=[st.text_input(f"اختيار {i+1}",oldopts[i] if i<len(oldopts) else "") for i in range(4)]
                        aa=st.selectbox("الإجابة الصحيحة",range(4),index=int(qr["answer"]))
                        dd=st.selectbox("الصعوبة",list(DIFF_AR),index=list(DIFF_AR).index(qr["difficulty"]))
                        cc=st.text_input("التصنيف",qr["category"]); ee=st.text_area("الشرح",qr["explanation"] or ""); rr=st.text_input("المرجع",qr["reference"] or ""); ac=st.checkbox("نشط",bool(qr["active"]))
                        if st.form_submit_button("حفظ التعديل"):
                            try:update_question(qid,qtext,newopts,aa,dd,cc,ee,rr,ac);st.success("تم الحفظ، وأعيد السؤال للمراجعة.");st.rerun()
                            except Exception as e:st.error(str(e))

    with selected_tab[3]:
        st.subheader("🧩 قوالب الاختبارات")
        with st.expander("➕ إنشاء قالب جديد"):
            with st.form("newtpl"):
                name=st.text_input("اسم القالب");n=st.number_input("عدد الأسئلة",5,500,50);dur=st.number_input("المدة بالدقائق",5,300,40);pas=st.number_input("نسبة النجاح",1.0,100.0,60.0);e=st.number_input("سهل %",0.0,100.0,20.0);m=st.number_input("متوسط %",0.0,100.0,50.0);h=st.number_input("صعب %",0.0,100.0,30.0);cats=sorted(questions_df(True).category.unique().tolist());selected=st.multiselect("التصنيفات",cats);allow=st.checkbox("السماح بإعادة الاختبار");maxa=st.number_input("أقصى عدد محاولات",1,20,1);req=st.checkbox("يشترط اعتماد السؤال",True);show=st.checkbox("إظهار النتيجة",True);review=st.checkbox("السماح بمراجعة الإجابات",False)
                if st.form_submit_button("إنشاء القالب"):
                    if not name.strip() or abs(e+m+h-100)>0.01: st.error("أدخل اسمًا صحيحًا ومجموع نسب = 100%.")
                    else:
                        try:
                            with db() as c:c.execute("""INSERT INTO exam_templates(name,num_questions,duration_minutes,pass_percent,easy_pct,medium_pct,hard_pct,categories_json,shuffle_questions,shuffle_options,show_result,show_review,allow_retake,max_attempts,require_approval,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(name,n,dur,pas,e,m,h,json.dumps(selected,ensure_ascii=False),1,1,int(show),int(review),int(allow),maxa,int(req),1,now(),now()))
                            audit("create_template","template");st.success("تم إنشاء القالب.");st.rerun()
                        except Exception as ex:st.error(str(ex))
        for t in templates():
            with st.expander(f"{t['name']} — {t['num_questions']} سؤال / {t['duration_minutes']} دقيقة"):
                with st.form(f"tpl_{t['id']}"):
                    name=st.text_input("اسم القالب",t["name"]);n=st.number_input("عدد الأسئلة",5,500,int(t["num_questions"]));dur=st.number_input("المدة بالدقائق",5,300,int(t["duration_minutes"]));pas=st.number_input("نسبة النجاح",1.0,100.0,float(t["pass_percent"]));e=st.number_input("سهل %",0.0,100.0,float(t["easy_pct"]));m=st.number_input("متوسط %",0.0,100.0,float(t["medium_pct"]));h=st.number_input("صعب %",0.0,100.0,float(t["hard_pct"]));cats=sorted(questions_df(True).category.unique().tolist());selected=st.multiselect("التصنيفات",cats,default=[x for x in json.loads(t["categories_json"] or "[]") if x in cats], key=f"sel_{t['id']}");shufq=st.checkbox("خلط الأسئلة",bool(t["shuffle_questions"]), key=f"sq_{t['id']}");shufopt=st.checkbox("خلط الاختيارات",bool(t["shuffle_options"]), key=f"so_{t['id']}");show=st.checkbox("إظهار النتيجة",bool(t["show_result"]), key=f"sr_{t['id']}");review=st.checkbox("السماح بمراجعة الإجابات",bool(t["show_review"]), key=f"srev_{t['id']}");allow=st.checkbox("السماح بإعادة الاختبار",bool(t["allow_retake"]), key=f"ar_{t['id']}");maxa=st.number_input("أقصى عدد محاولات",1,20,int(t["max_attempts"]), key=f"ma_{t['id']}");req=st.checkbox("يشترط اعتماد السؤال",bool(t["require_approval"]), key=f"req_{t['id']}")
                    if st.form_submit_button("حفظ القالب"):
                        if abs(e+m+h-100)>0.01:st.error("نسب الصعوبة يجب أن تساوي 100%.")
                        else:
                            with db() as c:c.execute("""UPDATE exam_templates SET name=?,num_questions=?,duration_minutes=?,pass_percent=?,easy_pct=?,medium_pct=?,hard_pct=?,categories_json=?,shuffle_questions=?,shuffle_options=?,show_result=?,show_review=?,allow_retake=?,max_attempts=?,require_approval=?,updated_at=? WHERE id=?""",(name,n,dur,pas,e,m,h,json.dumps(selected,ensure_ascii=False),int(shufq),int(shufopt),int(show),int(review),int(allow),maxa,int(req),now(),t["id"]))
                            audit("update_template","template",t["id"]);st.success("تم الحفظ.");st.rerun()

    with selected_tab[4]:
        st.subheader("📊 النتائج")
        with db() as c:
            df=pd.read_sql_query("""SELECT s.id,s.submitted_at,t.name trainee_name,t.facility,s.score,s.max_score,s.percent,s.passed,s.certificate_id,e.name template_name FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id JOIN exam_templates e ON e.id=s.template_id WHERE s.status='submitted' ORDER BY s.id DESC""",c)
        if not df.empty:
            c1,c2=st.columns(2); fac=c1.selectbox("الجهة",["الكل"]+sorted(df.facility.dropna().unique().tolist())); state=c2.selectbox("الحالة",["الكل","ناجح","غير مجتاز"])
            view=df.copy()
            if fac!="الكل":view=view[view.facility==fac]
            if state=="ناجح":view=view[view.passed==1]
            if state=="غير مجتاز":view=view[view.passed==0]
            st.dataframe(view,use_container_width=True,hide_index=True)
            out=io.BytesIO()
            try:
                with pd.ExcelWriter(out,engine="openpyxl") as writer:view.to_excel(writer,index=False,sheet_name="Results")
                st.download_button("📥 تصدير النتائج Excel",out.getvalue(),file_name="exam_results_v2_2.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception: pass
            
            sid_print=st.selectbox("اختر جلسة لطباعة الشهادة",view.id.tolist(), key="print_sel_res")
            if sid_print:
                render_printable_certificate(int(sid_print))
        else:
            st.info("لا توجد نتائج بعد.")

    with selected_tab[5]:
        st.subheader("💾 النسخ الاحتياطي")
        st.info("يتم إنشاء نسخة SQLite مستقلة باستخدام آلية backup الرسمية، بدل نسخ ملف WAL يدويًا.")
        if st.button("إنشاء نسخة احتياطية الآن"):
            path=os.path.join(BACKUP_DIR,f"endemic_labs_exam_v2_2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            src=sqlite3.connect(DB_PATH); dst=sqlite3.connect(path)
            try: src.backup(dst)
            finally: dst.close();src.close()
            audit("backup_created",details={"file":os.path.basename(path)});st.success(f"تم إنشاء النسخة: {os.path.basename(path)}")
        files=sorted([x for x in os.listdir(BACKUP_DIR) if x.endswith('.db')],reverse=True)
        for f in files[:10]:
            with open(os.path.join(BACKUP_DIR,f),'rb') as h: st.download_button(f"⬇️ {f}",h.read(),file_name=f,key=f"bk_{f}")

    tab_idx = 6
    if st.session_state.role == "admin":
        with selected_tab[tab_idx]:
            st.subheader("👥 المستخدمون")
            with st.form("newuser"):
                u=st.text_input("اسم المستخدم");p=st.text_input("كلمة المرور",type="password");role=st.selectbox("الصلاحية",list(ROLES),format_func=lambda x:ROLES[x])
                if st.form_submit_button("إنشاء المستخدم"):
                    try:create_user(u,p,role);audit("create_user","user");st.success("تم إنشاء المستخدم.")
                    except Exception as e:st.error(str(e))
            st.dataframe(pd.DataFrame([dict(x) for x in get_user_list()]),use_container_width=True,hide_index=True)
            st.markdown("#### تغيير كلمة مرور حسابك")
            with st.form("changepass"):
                old=st.text_input("القديمة",type="password");new=st.text_input("الجديدة",type="password")
                if st.form_submit_button("تغيير كلمة المرور"):
                    with db() as c:r=c.execute("SELECT * FROM users WHERE username=?",(st.session_state.username,)).fetchone()
                    if r and verify_password(old,r["password_hash"]) and len(new)>=8:
                        with db() as c:c.execute("UPDATE users SET password_hash=? WHERE id=?",(hash_password(new),r["id"]))
                        set_meta("must_change_default_admin","0");audit("change_password","user",r["id"]);st.success("تم تغيير كلمة المرور.")
                    else:st.error("تعذر تغيير كلمة المرور.")
        tab_idx += 1

        with selected_tab[tab_idx]:
            st.subheader("🧾 سجل التدقيق")
            with db() as c:df=pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 1000",c)
            st.dataframe(df,use_container_width=True,hide_index=True)

def trainee_portal():
    with db() as c:
        tr=c.execute("SELECT * FROM trainees WHERE id=?",(st.session_state.trainee_id,)).fetchone()
    if not tr:st.session_state.trainee_id=None;st.session_state.trainee_name="";st.rerun()
    header();st.markdown(f'<div class="card"><h3>مرحباً {esc(tr["name"])}</h3><p>الجهة: {esc(tr["facility"])}</p></div>',unsafe_allow_html=True)
    active=get_active_session(tr["id"])
    if active:
        st.session_state.exam_session_id=active["id"];exam_page(active);return
    ts=templates()
    if not ts:st.error("لا يوجد قالب امتحان فعال.");return
    with st.form("start_exam"):
        tid=st.selectbox("نوع الاختبار",[t["id"] for t in ts],format_func=lambda x:next(t["name"] for t in ts if t["id"]==x))
        if st.form_submit_button("بدء الاختبار"):
            try:
                sid=start_session(tr["id"],tid);st.session_state.exam_session_id=sid;st.rerun()
            except Exception as e:st.error(str(e))
    if st.button("خروج المتدرب"):st.session_state.trainee_id=None;st.session_state.trainee_name="";st.rerun()

def exam_page(session):
    sid=session["id"];r=session_questions(sid);t=template_by_id(session["template_id"])
    remaining=max(0,int((datetime.fromisoformat(session["expires_at"])-datetime.now()).total_seconds()))
    if remaining<=0:
        submit_session(sid,True);st.session_state.last_result_id=sid;st.session_state.exam_session_id=None;st.rerun()
    mins,secs=divmod(remaining,60);st.markdown(f'<div class="timer">⏱️ الوقت المتبقي: {mins:02d}:{secs:02d}</div>',unsafe_allow_html=True)
    answered=0
    for row in r:
        opts=json.loads(row["options_json"]);order=json.loads(row["option_order_json"]);display_opts=[opts[i] for i in order]
        current=None
        if row["selected_option"] is not None:
            try:current=display_opts.index(opts[row["selected_option"]])
            except:current=None
        st.markdown(f'<div class="question"><b>سؤال {row["position"]+1}</b><br>{esc(row["question"])}</div>',unsafe_allow_html=True)
        choice=st.radio("اختر إجابة",display_opts,index=current, key=f"q_{row['id']}",label_visibility="collapsed")
        if choice:
            selected=display_opts.index(choice);original=order[selected];save_answer(sid,row["id"],original);answered+=1
    st.progress(answered/len(r) if r else 0)
    if st.button("تسليم الاختبار نهائياً",use_container_width=True):
        if answered<len(r):st.warning(f"لم تتم الإجابة عن {len(r)-answered} سؤال.")
        else:submit_session(sid);st.session_state.last_result_id=sid;st.session_state.exam_session_id=None;st.rerun()
    st.caption("يتم حفظ الإجابات مباشرة في SQLite. لا تعتمد على إعادة تحميل الصفحة لحفظ الإجابة.")

def result_page(sid):
    r=session_result(sid)
    if not r:return
    t=template_by_id(r["template_id"])
    header(); st.success("تم تسليم الاختبار بنجاح.")
    cols=st.columns(4)
    for c,l,v in zip(cols,["النتيجة","النسبة","الحالة","رقم الشهادة"],[f'{r["score"]}/{r["max_score"]}',f'{r["percent"]:.1f}%',"ناجح" if r["passed"] else "غير مجتاز",r["certificate_id"]]): c.metric(l,v)
    
    if int(t["show_result"]):
        render_printable_certificate(sid)

    if int(t["show_review"]):
        st.subheader("📝 مراجعة الإجابات")
        for row in session_questions(sid):
            opts=json.loads(row["options_json"]);selected=row["selected_option"];correct=int(row["answer"]);mark="✅" if selected is not None and int(selected)==correct else "❌"
            st.markdown(f'<div class="question"><b>{mark} سؤال {row["position"]+1}</b><br>{esc(row["question"])}<br>إجابتك: {esc(opts[selected] if selected is not None else "لم تتم الإجابة")}<br>الإجابة الصحيحة: {esc(opts[correct])}<br><small>{esc(row["explanation"] or "")}</small></div>',unsafe_allow_html=True)
    if st.button("إنهاء الجلسة"): st.session_state.trainee_id=None;st.session_state.trainee_name="";st.session_state.last_result_id=None;st.rerun()

# ============================================================
# 12) التشغيل
# ============================================================
if st.session_state.trainee_id and not st.session_state.logged_in:
    if st.session_state.last_result_id:result_page(st.session_state.last_result_id)
    else:trainee_portal()
elif not st.session_state.logged_in:
    login_page()
else:
    dashboard()
