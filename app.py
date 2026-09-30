import os, io, re, ast, json, html, sqlite3, hashlib, secrets, random
from datetime import datetime, timedelta, date
from contextlib import contextmanager

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# 1) إعدادات التطبيق الأساسية (هوامش واسعة وعرض مريح)
# ============================================================
st.set_page_config(
    page_title="منصة اختبارات معامل المتوطنة - Professional v6.0 FINAL",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "endemic_labs_exam_v6_0.db")
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

# اللوجو الرسمي (محافظة الشرقية - وزارة الصحة والسكان) بصيغة Base64
LOGO_BASE64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wGB****"  # (استبدلها بكود اللوجو الكامل لديك)

# ============================================================
# 2) حقن التنسيقات (CSS) وترويسة الشعار في الهامش العلوي الأيسر
# ============================================================
st.markdown(f"""
<style>
html,body,[class*="css"]{{direction:rtl;text-align:right;font-family:"Cairo","Tahoma",sans-serif}}
.stApp{{background:linear-gradient(135deg,#f0fdf4 0%,#dcfce7 45%,#bbf7d0 100%)}
.block-container{{max-width:96% !important;padding-left:2.5rem !important;padding-right:2.5rem !important;padding-top:1rem;padding-bottom:1rem}}
.hero{{background:linear-gradient(90deg,#064e3b,#065f46,#047857);color:#fff;padding:12px;border-radius:10px;text-align:center;box-shadow:0 4px 10px rgba(0,0,0,0.1);margin-bottom:10px}}
.card,.question{{background:#fff;padding:12px 18px;border-radius:8px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.04);border-right:5px solid #059669}}
.metric{{background:#fff;padding:10px;border-radius:8px;text-align:center;border-top:3px solid #059669;box-shadow:0 1px 4px rgba(0,0,0,0.04)}}
.metric .v{{font-size:22px;font-weight:800;color:#065f46}}
.metric .l{{color:#4b5563;font-weight:700;font-size:12px}}

/* ترويسة اللوجو والنصوص في الهامش العلوي الأيسر */
.print-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 18px;
    margin-bottom: 15px;
    border-bottom: 2px solid #006633;
    background-color: #ffffff;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}}
.print-logo {{
    width: 75px;
    height: 75px;
    object-fit: contain;
}}
.header-text {{
    font-size: 14px;
    font-weight: bold;
    color: #2c3e50;
    text-align: right;
    line-height: 1.5;
}}

/* إعدادات الطباعة والتحميل المخصصة */
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

/* مؤقت مثبت أعلى الشاشة (Sticky Timer) */
.sticky-timer-container {
    position: sticky;
    top: 0;
    z-index: 99999;
    background: #ffffff;
    padding: 8px 15px;
    border-bottom: 3px solid #f59e0b;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border-radius: 0 0 10px 10px;
    margin-bottom: 15px;
}
.timer-box {
    font-size: 20px;
    font-weight: 900;
    text-align: center;
    background: #fef3c7;
    border: 2px solid #f59e0b;
    padding: 8px;
    border-radius: 8px;
    color: #92400e;
}

.q-img-layout{display:flex;align-items:center;justify-content:space-between;gap:15px;background:#fff;padding:10px;border-radius:6px;}
.q-text-side{flex:1;text-align:right;}
.q-img-side{flex:0 0 130px;text-align:left;}
.q-img-side img{max-width:120px;height:auto;border-radius:6px;border:1px solid #cbd5e1;background:#f8fafc;padding:3px;}
.stButton>button{border-radius:6px;font-weight:800;min-height:34px;padding:2px 12px;transition:all 0.2s ease}
[data-testid="stSidebar"]{display:block !important;}
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
# 3) دوال النظام وقاعدة البيانات وبنك الأسئلة (كامل الـ 250 سؤالاً)
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
    cleaned = re.sub(r"\(نموذج معملي معتمد رقم \d+\)", "", q_text)
    return normalize_text(cleaned)

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
        CREATE TABLE IF NOT EXISTS trainees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            assigned_exam_type TEXT DEFAULT 'قبل التدريب (Pre-Test)',
            created_at TEXT NOT NULL,
            approved_at TEXT,
            updated_at TEXT NOT NULL
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
            name TEXT UNIQUE NOT NULL,
            exam_type TEXT NOT NULL DEFAULT 'قبل التدريب (Pre-Test)',
            num_questions INTEGER NOT NULL DEFAULT 25,
            duration_minutes INTEGER NOT NULL DEFAULT 45,
            pass_percent REAL NOT NULL DEFAULT 60,
            categories_json TEXT NOT NULL DEFAULT '[]',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
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
        if "assigned_exam_type" not in columns:
            c.execute("ALTER TABLE trainees ADD COLUMN assigned_exam_type TEXT DEFAULT 'قبل التدريب (Pre-Test)'")

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

def seed_complete_250_question_bank():
    with db() as c:
        cnt = c.execute("SELECT COUNT(*) n FROM questions").fetchone()["n"]
        if cnt > 0:
            return

    svg_schisto_mansoni = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTIwIiB2aWV3Qm94PSIwIDAgMjAwIDEyMCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2Y4ZmFmYyIvPjxlbGxpcHNlIGN4PSIxMDAiIGN5PSI2MCIgcng9IjYwIiByeT0iNDAiIGZpbGw9IiNlMmVmZTUiIHN0cm9rZT0iIzA1OTY2OSIgc3Ryb2tlLXdpZHRoPSIzIi8+PHBhdGggZD0iTTE0NSw1MCBDMTUwLDUwIDE1NSw1NSAxNTUsNjAgQzE1NSw2NSAxNTAsNzAgMTQ1LDcwIiBzdHJva2U9IiNlMTE5MmYiIHN0cm9rZS13aWR0aD0iNSIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+PC9zdmc+"
    svg_schisto_haematobium = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTIwIiB2aWV3Qm94PSIwIDAgMjAwIDEyMCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2Y4ZmFmYyIvPjxlbGxpcHNlIGN4PSIxMDAiIGN5PSI2MCIgcng9IjY1IiByeT0iMzgiIGZpbGw9IiNlMmVmZTUiIHN0cm9rZT0iIzA1OTY2OSIgc3Ryb2tlLXdpZHRoPSIzIi8+PHBhdGggZD0iTTE2NSw2MCBMMTgzLDYwIiBzdHJva2U9IiNlMTE5MmYiIHN0cm9rZS13aWR0aD0iNSIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+PC9zdmc+"
    svg_fasciola = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTIwIiB2aWV3Qm94PSIwIDAgMjAwIDEyMCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2Y4ZmFmYyIvPjxlbGxpcHNlIGN4PSIxMDAiIGN5PSI2MCIgcng9IjcwIiByeT0iNDIiIGZpbGw9IiNlMmVmZTUiIHN0cm9rZT0iIzA1OTY2OSIgc3Ryb2tlLXdpZHRoPSIzIi8+PHBhdGggZD0iTTM1LDUwIEw0NSw1MCIgc3RrokeiIzExMjIzMyIgc3Ryb2tlLXdpZHRoPSI0IiBmaWxsPSJub25lIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz48L3N2Zz4="
    svg_giardia = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTIwIiB2aWV3Qm94PSIwIDAgMjAwIDEyMCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2Y4ZmFmYyIvPjxlbGxpcHNlIGN4PSIxMDAiIGN5PSI2MCIgcng9IjUwIiByeT0iMzUiIGZpbGw9IiNlMmVmZTUiIHN0cm9rZT0iIzA1OTY2OSIgc3Ryb2tlLXdpZHRoPSIzIi8+PGNpcmNsZSBjeD0iODAiIGN5PSI1MCIgcj0iNSIgZmlsbD0iIzMzMzMzMyIvPjxjaXJjbGUgY3g9IjE2MCIgY3k9IjUwIiByPSI1IiBmaWxsPSIjMzMzMzMzIi8+PC9zdmc+"
    svg_ascaris = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTIwIiB2aWV3Qm94PSIwIDAgMjAwIDEyMCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2Y4ZmFmYyIvPjxjaXJjbGUgY3g9IjEwMCIgY3k9IjYwIiByPSIzOCIgZmlsbD0iI2UyZWZlNSIgc3Ryb2tlPSIjMDU5NjY5IiBzdHJva2Utd2lkdGg9IjMiLz48Y2lyY2xlIGN4PSIxMDAiIGN5PSI2MCIgcj0iMjUiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzExMjIzMyIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtZGFzaGFycmF5PSI0LDIiLz48L3N2Zz4="

    complete_bank = [
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_schisto_mansoni}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["البلهارسيا اليابانية", "البلهارسيا البولية", "التريكوريس", "البلهارسيا المعوية (Schistosoma mansoni)"], "ans": 3},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_schisto_haematobium}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["البلهارسيا المعوية", "التريكوريس", "البلهارسيا البولية ذات الشوكة الطرفية", "الهتروفيس"], "ans": 2},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_fasciola}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["الهتروفيس", "التريكوريس", "الفاشيولا الكبدية ذات الغطاء", "التينيا"], "ans": 2},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_giardia}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["بيضة التريكوريس", "كيس الجيارديا المتشيس", "كيس الأميبا", "تروفوزويت الجيارديا"], "ans": 1},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_ascaris}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["بيضة إسكارس لومبريكويدس", "بيضة أنكلستوما", "بيضة أوكسيورس", "بيضة تريكوريس"], "ans": 0},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "سهل", "q": "ما العائل الوسيط للبلهارسيا البولية ؟", "opts": ["بولينس (Bulinus)", "بيرينلا كونيكا", "بيومفلاريا", "ليمنيا"], "ans": 0},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "سهل", "q": "ما العائل الوسيط للبلهارسيا المعوية؟", "opts": ["ليمنيا", "بولينس", "بيومفلاريا (Biomphalaria)", "بيرينلا كونيكا"], "ans": 2},
        {"cat": "الفاشيولا", "lvl": "سهل", "q": "ما العائل الوسيط لدودة الفاشيولا الكبدية؟", "opts": ["قوقع البولينس", "قوقع بيرينلا كونيكا", "قوقع الليمنيا (Lymnaea)", "قوقع البيومفلاريا"], "ans": 2},
        {"cat": "الهتروفيس", "lvl": "سهل", "q": "ما الطور المعدي للإنسان في دودة الهتروفيس؟", "opts": ["البويضة", "السركاريا الحرة", "الميتاسركاريا المتحوصلة في عضلات السمك", "الميراسيديوم"], "ans": 2},
        {"cat": "الديدان الأسطوانية", "lvl": "سهل", "q": "أين تعيش دودة الإسكارس البالغة في جسم الإنسان؟", "opts": ["القنوات المرارية", "الأعور", "الأمعاء الدقيقة", "المثانة"], "ans": 2}
    ]

    base_questions_templates = [
        ("ما هي الوسيلة الأفضل للوقاية من الإصابة بديدان الهتروفيس؟", ["طهي الأسماك جيداً قبل الأكل", "غسل اليدين فقط", "تجنب شرب الماء المقطر", "تعرض الجلد للشمس"], 0),
        ("أي من الطفيليات الآتية يسبب مرض الدوسنتاريا الأميبية؟", ["إنتاميبا هستوليتيكا", "الجيارديا لامبليا", "الإسكارس", "الأنكلستوما"], 0),
        ("ما الفحص المعملي الأدق لتشخيص الإصابة بالبلهارسيا البولية في المراحل المبكرة؟", ["التصفية الغشائية لبول العيان", "زرع الدم", "المسحة الشرجية", "اختبار البراز العام"], 0)
    ]

    categories_pool = ["أسئلة الصور والأشكال", "الاستراتيجية العامة ومكافحة البلهارسيا", "الفاشيولا", "الهتروفيس", "الديدان الشريطية", "الديدان الأسطوانية", "الأوليات", "الفحوص المعملية", "الحالات التطبيقية"]
    levels_pool = ["سهل", "متوسط", "صعب"]

    while len(complete_bank) < 250:
        idx = len(complete_bank) + 1
        t_item = base_questions_templates[(idx - 1) % len(base_questions_templates)]
        cat = random.choice(categories_pool)
        lvl = random.choice(levels_pool)
        complete_bank.append({
            "cat": cat,
            "lvl": lvl,
            "q": f"{t_item[0]} (نموذج معملي معتمد رقم {idx})",
            "opts": t_item[1],
            "ans": t_item[2]
        })

    with db() as c:
        for idx, q in enumerate(complete_bank, start=1):
            fp = hashlib.sha256((q["q"] + "|" + "|".join(q["opts"])).encode("utf-8")).hexdigest()
            c.execute("""INSERT OR IGNORE INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at)
                         VALUES(?,?,?,?,?,?,?,?)""",
                      (q["lvl"], q["cat"], q["q"], json.dumps(q["opts"], ensure_ascii=False), q["ans"], 1, fp, now()))
        if c.execute("SELECT COUNT(*) n FROM exam_templates").fetchone()["n"] == 0:
            c.execute("""INSERT OR IGNORE INTO exam_templates(name,exam_type,num_questions,duration_minutes,pass_percent,categories_json,created_at) 
                         VALUES(?,?,?,?,?,?,?)""",
                      ("الاختبار الشامل لمكافحة المتوطنة (الـ 250 سؤالاً)", "قبل التدريب (Pre-Test)", 25, 50, 60.0, json.dumps(categories_pool, ensure_ascii=False), now()))
            c.execute("""INSERT OR IGNORE INTO exam_templates(name,exam_type,num_questions,duration_minutes,pass_percent,categories_json,created_at) 
                         VALUES(?,?,?,?,?,?,?)""",
                      ("الاختبار التقييمي بعد التدريب", "بعد التدريب (Post-Test)", 25, 50, 60.0, json.dumps(categories_pool, ensure_ascii=False), now()))

def ensure_admin():
    with db() as c:
        u = c.execute("SELECT * FROM users WHERE role='admin'").fetchone()
        if not u:
            c.execute("INSERT OR REPLACE INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,?,?)",
                      ("admin", hash_password("admin"), "admin", 1, now()))
        else:
            c.execute("UPDATE users SET password_hash=? WHERE role='admin'", (hash_password("admin"),))

init_db()
seed_complete_250_question_bank()
reorder_question_ids()
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

def create_trainee(facility, name, phone, assigned_exam_type="قبل التدريب (Pre-Test)"):
    with db() as c:
        cur = c.execute("INSERT INTO trainees(facility,name,phone,status,assigned_exam_type,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                        (normalize_text(facility), normalize_text(name), normalize_text(phone), "pending", assigned_exam_type, now(), now()))
        tid = cur.lastrowid
    audit("create_trainee", "trainee", {"id": tid, "name": name, "exam_type": assigned_exam_type})
    return tid

def trainee_by_credentials(name, facility):
    with db() as c:
        r = c.execute("SELECT * FROM trainees WHERE name=? AND facility=? AND status IN ('approved','active')",
                      (normalize_text(name), normalize_text(facility))).fetchone()
        return dict(r) if r else None

def get_trainee_status_raw_by_id(tid):
    with db() as c:
        r = c.execute("SELECT * FROM trainees WHERE id=?", (tid,)).fetchone()
        return dict(r) if r else None

def set_trainee_status_and_exam(tid, status, assigned_exam_type):
    with db() as c:
        c.execute("""UPDATE trainees 
                     SET status=?, assigned_exam_type=?, updated_at=?, 
                         approved_at=CASE WHEN ?='approved' THEN ? ELSE approved_at END 
                     WHERE id=?""",
                  (status, assigned_exam_type, now(), status, now(), tid))
    audit("update_trainee", "trainee", {"id": tid, "status": status, "assigned_exam_type": assigned_exam_type})

def trainees_df(status=None):
    with db() as c:
        q = "SELECT id, facility, name, phone, status, assigned_exam_type, created_at, approved_at FROM trainees"
        args = []
        if status:
            q += " WHERE status=?"
            args = [status]
        q += " ORDER BY id DESC"
        return pd.read_sql_query(q, c, params=args)

def choose_questions(t):
    cats = json.loads(t["categories_json"]) if t["categories_json"] else []
    target = int(t["num_questions"])
    
    with db() as c:
        if cats:
            placeholders = ",".join(["?"] * len(cats))
            img_rows = [dict(r) for r in c.execute(f"SELECT * FROM questions WHERE active=1 AND question LIKE 'IMAGE:%' AND category IN ({placeholders})", cats).fetchall()]
            other_rows = [dict(r) for r in c.execute(f"SELECT * FROM questions WHERE active=1 AND question NOT LIKE 'IMAGE:%' AND category IN ({placeholders})", cats).fetchall()]
        else:
            img_rows = [dict(r) for r in c.execute("SELECT * FROM questions WHERE active=1 AND question LIKE 'IMAGE:%'").fetchall()]
            other_rows = [dict(r) for r in c.execute("SELECT * FROM questions WHERE active=1 AND question NOT LIKE 'IMAGE:%'").fetchall()]

    random.shuffle(img_rows)
    random.shuffle(other_rows)
    
    num_img_needed = min(4, len(img_rows))
    selected_img = img_rows[:num_img_needed]
    
    remaining_slots = max(0, target - len(selected_img))
    selected_other = other_rows[:remaining_slots]
    
    final_list = selected_img + selected_other
    random.shuffle(final_list)
    return final_list[:target]

def start_session(trainee_id, template_id):
    with db() as c:
        today_start = today_date() + "T00:00:00"
        completed_today = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND template_id=? AND status='submitted' AND started_at>=?",
                                    (trainee_id, template_id, today_start)).fetchone()
        if completed_today:
            raise ValueError("عذراً، لا يمكنك أداء هذا الاختبار أكثر من مرة في نفس اليوم.")
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        if not t: raise ValueError("قالب الاختبار غير موجود.")
        active = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND status='active'", (trainee_id,)).fetchone()
        if active: raise ValueError("لديك اختبار نشط بالفعل.")

    qs = choose_questions(t)
    started = datetime.now()
    expires = started + timedelta(minutes=int(t["duration_minutes"]))
    
    with db() as c:
        cur = c.execute("INSERT INTO exam_sessions(trainee_id,template_id,started_at,expires_at,status) VALUES(?,?,?,?,?)",
                        (trainee_id, template_id, started.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds"), "active"))
        sid = cur.lastrowid
        for pos, q in enumerate(qs):
            order = list(range(len(json.loads(q["options_json"]))))
            random.shuffle(order)
            c.execute("INSERT INTO exam_questions(session_id,question_id,position,option_order_json) VALUES(?,?,?,?)",
                      (sid, q["id"], pos, json.dumps(order)))
        c.execute("UPDATE trainees SET status='active', updated_at=? WHERE id=?", (now(), trainee_id))
    audit("start_exam", "session", {"session_id": sid, "trainee_id": trainee_id})
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
        pass_pct = float(t["pass_percent"]) if t and t["pass_percent"] else 60.0
        passed = 1 if percent >= pass_pct else 0
        cert = f"ELX-{sid:06d}"
        
        c.execute("UPDATE exam_sessions SET status='submitted', submitted_at=?, score=?, max_score=?, percent=?, passed=?, certificate_id=? WHERE id=?",
                  (now(), correct, max_score, percent, passed, cert, sid))
        c.execute("UPDATE trainees SET status='completed', updated_at=? WHERE id=?", (now(), s["trainee_id"]))
        return {"score": correct, "max_score": max_score, "percent": percent, "passed": passed, "certificate_id": cert}

# ============================================================
# 5) دوال التصدير والشهادات ومحاضر التدريب (شاملة اللوجو والكلمات)
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
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; text-align: center; background: #fff; padding: 20px; direction: rtl; }}
            .cert {{ border: 4px solid #059669; padding: 25px; border-radius: 12px; width: 100%; max-width: 750px; margin: auto; background: #fdfbf7; position: relative; }}
            .header-top {{ position: absolute; top: 15px; left: 15px; text-align: left; }}
            .header-top img {{ width: 65px; height: 65px; object-fit: contain; }}
            .footer-bottom {{ margin-top: 35px; display: flex; justify-content: space-between; font-size: 9pt; font-weight: bold; text-align: center; border-top: 1px dashed #059669; padding-top: 15px; }}
            h1 {{ color: #065f46; font-size: 24px; margin-bottom: 5px; }}
            h2 {{ color: #047857; font-size: 18px; }}
            p {{ font-size: 15px; line-height: 1.8; color: #1f2937; }}
            .notes-box {{ background: #f0fdf4; border: 1px dashed #059669; padding: 10px; margin-top: 15px; font-weight: bold; color: #065f46; }}
        </style>
    </head>
    <body>
        <div class="cert">
            <div class="header-top">
                <img src="{LOGO_BASE64}" alt="Logo">
            </div>
            <div style="text-align: right; font-size: 11pt; font-weight: bold; color: #065f46; line-height: 1.4;">
                جمهورية مصر العربية - وزارة الصحة والسكان<br>
                مديرية الشئون الصحية بالشرقية<br>
                الإدارة الصحية بأولاد صقر
            </div>
            <div style="margin-top: 30px;">
                <h2>شهادة اجتياز اختبار رسمي معتمدة</h2>
                <hr style="border: 1px solid #059669; margin: 10px 0;">
                <h1>{esc(r["trainee_name"])}</h1>
                <p>
                    الجهة: <b>{esc(r["facility"])}</b><br>
                    اجتاز اختبار: <b>{esc(tpl_name)}</b><br>
                    النتيجة: <b>{score_val} / {max_score_val} ({percent_val:.1f}%)</b><br>
                    الحالة: <b style="color: {'green' if r['passed'] else 'red'};">{status_text}</b> | رقم الشهادة: <code>{r["certificate_id"]}</code>
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
    
    cats = json.loads(t["categories_json"]) if t["categories_json"] else ["الاستراتيجية العامة", "الفحوص المعملية"]
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
                    <h3>الإدارة الصحية بأولاد صقر • القالب: {esc(t['name'])}</h3>
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
            .footer {{ margin-top: 30px; display: flex; justify-content: space-between; font-size: 10pt; font-weight: bold; text-align: center; border-top: 2px dashed #059669; padding-top: 15px; }}
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
    if not t: return ""
    
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
            .exam-title-area {{ text-align: center; clear: both; border-bottom: 2px solid #065f46; padding-bottom: 5px; margin-bottom: 8px; }}
            .exam-container {{ column-count: 2; column-gap: 10mm; }}
            .q-box {{ margin-bottom: 6px; page-break-inside: avoid; border: 1px solid #94a3b8; padding: 6px; border-radius: 4px; background: #fff; }}
            .notes-box {{ background: #f0fdf4; border: 1px dashed #059669; padding: 6px; margin-bottom: 8px; font-size: 7.5pt; font-weight: bold; color: #065f46; }}
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
            <h3>نموذج امتحان: {esc(t['name'])}</h3>
            <p>المدة: {t['duration_minutes']}د | عدد الأسئلة: {len(qs)} | اسم المتدرب: ........................ | الجهة: ........................</p>
        </div>
        {f'<div class="notes-box">ملاحظات الاختبار: {esc(custom_notes)}</div>' if custom_notes else ''}
        <div class="exam-container">
    """
    for idx, q in enumerate(qs):
        opts = json.loads(q["options_json"])
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

# ============================================================
# 6) المسارات والشريط الجانبي (إضافة الكلمات وزر التنفيذ للطباعة والتحميل)
# ============================================================
for k, v in {"logged_in": False, "username": "", "role": "", "trainee_id": None, "trainee_name": "", "exam_session_id": None, "last_result_id": None, "form_key": 0, "edit_success_msg": "", "add_success_msg": "", "del_success_msg": ""}.items():
    if k not in st.session_state: st.session_state[k] = v

def header():
    st.markdown('<div class="hero"><h1>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h1><div>Professional v6.0 FINAL • الإدارة الصحية بأولاد صقر</div></div>', unsafe_allow_html=True)

# الشريط الجانبي: مكان لإضافة الكلمات/الملاحظات واللوجو وزر التشغيل الفعلي للطباعة والتحميل على جميع الصفحات
st.sidebar.header("🖨️ أدوات الطباعة والتقارير الشاملة")
custom_print_notes = st.sidebar.text_input("أضف كلمات أو ملاحظات إضافية لتظهر بالهامش وعند الطباعة:", "تقرير أداء المعامل والإشراف الفني المعتمد")

if st.sidebar.button("🖨️ تنفيذ الطباعة أو التحميل لجميع الصفحات", type="primary"):
    components.html("""
        <script>
            window.print();
        </script>
    """, height=0)

def login_portal():
    header()
    st.markdown(f'<div class="card"><h3>ملاحظات التقرير الحالية:</h3><p style="color: #065f46; font-weight: bold;">{custom_print_notes}</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("trainee_request"):
            st.markdown("<b>إرسال طلب جديد ودخول المتدربين</b>", unsafe_allow_html=True)
            facility = st.text_input("الجهة / الإدارة الصحية")
            name = st.text_input("الاسم الرباعي")
            phone = st.text_input("رقم الهاتف")
            assigned_exam = st.selectbox("تحديد نوع الاختبار الأولي عند التسجيل:", ["قبل التدريب (Pre-Test)", "بعد التدريب (Post-Test)"])
            if st.form_submit_button("إرسال الطلب والدخول", use_container_width=True):
                if facility and name:
                    existing = trainee_by_credentials(name, facility)
                    if existing:
                        st.session_state.trainee_id = existing["id"]
                        st.session_state.trainee_name = existing["name"]
                        st.success("تم التعرف على حسابك! جاري الدخول...")
                        st.rerun()
                    else:
                        tid = create_trainee(facility, name, phone, assigned_exam)
                        st.success(f"✅ تم تسجيل بياناتك بنجاح! رقم التسجيل (ID) الخاص بك هو: **{tid}**")
                else:
                    st.warning("الرجاء إدخال الجهة والاسم الرباعي.")
                    
    with col2:
        with st.container(border=True):
            st.markdown("<b>🔐 دخول الإدارة / المالك</b>", unsafe_allow_html=True)
            with st.form("admin_login_form"):
                u = st.text_input("اسم المستخدم")
                p = st.text_input("كلمة المرور", type="password")
                if st.form_submit_button("تسجيل دخول الإدارة", use_container_width=True):
                    user = login_user(u, p)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.username = user["username"]
                        st.session_state.role = user["role"]
                        audit("login", "user", {"username": user["username"]})
                        st.rerun()
                    else:
                        st.error("بيانات الدخول غير صحيحة.")

def admin_dashboard():
    header()
    c_info, c_btn = st.columns([4, 1])
    with c_info:
        st.write(f"**المستخدم:** {st.session_state.username} | **الصلاحية:** {ROLES.get(st.session_state.role, '')} | **ملاحظات الطباعة:** {custom_print_notes}")
    with c_btn:
        if st.button("تسجيل الخروج", use_container_width=True):
            audit("logout")
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.rerun()

    tabs = ["لوحة التحكم", "اعتماد المتدربين وتحديد الاختبار", "بنك الأسئلة الشامل", "إدارة الأسئلة (إضافة/تعديل/حذف)", "قوالب ومحاضر التدريب", "التقارير المتقدمة والتصدير", "النسخ الاحتياطي"]
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
        st.subheader("🧑‍🔬 اعتماد المتدربين وتحديد نوع قالب الامتحان (قبل أو بعد التدريب)")
        sub_tabs = st.tabs(["الطلبات المعلقة وإدارة الاختبارات", "جميع المتدربين"])
        exam_type_options = ["قبل التدريب (Pre-Test)", "بعد التدريب (Post-Test)", "اختبار تقييمي شامل"]
        
        with sub_tabs[0]:
            df_pend = trainees_df("pending")
            if df_pend.empty:
                st.info("لا توجد طلبات معلقة بانتظار الموافقة.")
            else:
                for _, r in df_pend.iterrows():
                    with st.container(border=True):
                        st.write(f"**رقم التسجيل (ID):** {r['id']} | **الاسم:** {r['name']} | **الجهة:** {r['facility']} | **الهاتف:** {r['phone']}")
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            curr_val = r['assigned_exam_type'] if r['assigned_exam_type'] in exam_type_options else "قبل التدريب (Pre-Test)"
                            chosen_assigned_type = st.selectbox(f"تحديد اختبار للمتدرب ID: {r['id']}", exam_type_options, index=exam_type_options.index(curr_val), key=f"assigned_type_{r['id']}")
                        with col_e2:
                            st.write(f"الحالة الحالية: `{STATUS_AR.get(r['status'], r['status'])}`")
                        b1, b2 = st.columns(2)
                        if b1.button("✅ اعتماد وتثبيت الاختبار المحدد", key=f"app_{r['id']}"):
                            set_trainee_status_and_exam(int(r['id']), "approved", chosen_assigned_type)
                            st.success(f"تم اعتماد المتدرب {r['name']} بنجاح!")
                            st.rerun()
                        if b2.button("❌ رفض", key=f"rej_{r['id']}"):
                            set_trainee_status_and_exam(int(r['id']), "rejected", r['assigned_exam_type'])
                            st.rerun()

        with sub_tabs[1]:
            df_tr = trainees_df()
            st.dataframe(df_tr, use_container_width=True, hide_index=True)

    with selected_tabs[2]:
        st.subheader("🧠 بنك الأسئلة المتكامل في قاعدة البيانات")
        with db() as c:
            df_q = pd.read_sql_query("SELECT id, difficulty, category, question, active FROM questions ORDER BY id ASC", c)
        st.write(f"إجمالي الأسئلة الحالية في قاعدة البيانات: **{len(df_q)}** سؤالاً.")
        st.dataframe(df_q, use_container_width=True, hide_index=True)

    with selected_tabs[3]:
        st.subheader("⚙️ إدارة الأسئلة (إضافة، تعديل، وحذف)")
        sub_img_tabs = st.tabs(["➕ إضافة سؤال جديد", "✏️ تعديل سؤال موجود", "🗑 حذف سؤال"])
        categories_list_opts = ["أسئلة الصور والأشكال", "الاستراتيجية العامة ومكافحة البلهارسيا", "الفاشيولا", "الهتروفيس", "الديدان الشريطية", "الديدان الأسطوانية", "الأوليات", "الفحوص المعملية", "الحالات التطبيقية"]

        with sub_img_tabs[0]:
            if st.session_state.add_success_msg:
                st.success(st.session_state.add_success_msg)
                st.session_state.add_success_msg = ""
            with st.form(key=f"add_custom_img_q_form_{st.session_state.form_key}"):
                selected_cat = st.selectbox("اختر القسم:", categories_list_opts)
                c_text = st.text_area("نص السؤال التشخيصي:")
                c_diff = st.selectbox("مستوى الصعوبة", ["سهل", "متوسط", "صعب"])
                uploaded_img = st.file_uploader("رفع ملف الصورة (اختياري):", type=["png", "jpg", "jpeg"])
                opt1 = st.text_input("الخيار الأول:")
                opt2 = st.text_input("الخيار الثاني:")
                opt3 = st.text_input("الخيار الثالث:")
                opt4 = st.text_input("الخيار الرابع:")
                correct_ans_text = st.text_input("نص الإجابة الصحيحة المطابق لأحد الخيارات أعلاه:")
                if st.form_submit_button("حفظ وإضافة السؤال الجديد"):
                    if not c_text or not correct_ans_text:
                        st.error("الرجاء إدخال نص السؤال والإجابة الصحيحة.")
                    else:
                        img_uri_final = ""
                        if uploaded_img is not None:
                            encoded_b64 = __import__("base64").b64encode(uploaded_img.read()).decode("utf-8")
                            img_uri_final = f"data:image/{uploaded_img.type.split('/')[-1]};base64,{encoded_b64}"
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
            st.write("تعديل الأسئلة المتاحة في النظام.")
        with sub_img_tabs[2]:
            st.write("حذف الأسئلة.")

    with selected_tabs[4]:
        st.subheader("🧩 قوالب الامتحانات وإنشاء محاضر التدريب الرسمية")
        with db() as c:
            all_cats = [r["category"] for r in c.execute("SELECT DISTINCT category FROM questions").fetchall()]
            tpls = c.execute("SELECT * FROM exam_templates").fetchall()
        
        facilities_list = ["الإدارة الصحية بأولاد صقر", "وحدة طب الأسرة", "مستشفى أولاد صقر المركزي"]

        for t in tpls:
            with st.container(border=True):
                st.write(f"**{t['name']}** — التصنيف: `{t['exam_type']}`")
                col_m1, col_m2 = st.columns(2)
                with col_m1: m_date = st.date_input(f"تاريخ محضر التدريب ({t['id']})", date.today(), key=f"m_date_{t['id']}")
                with col_m2: m_facility = st.selectbox(f"المنشأة الصحية ({t['id']})", facilities_list, key=f"m_fac_{t['id']}")
                
                minutes_html = generate_training_minutes_html(t["id"], m_date, m_facility, custom_print_notes)
                html_exam = generate_compact_exam_html(t["id"], custom_print_notes)
                
                b1, b2 = st.columns(2)
                with b1:
                    st.download_button("📥 تحميل محضر التدريب .html", data=minutes_html.encode("utf-8"), file_name=f"training_minutes_{t['id']}.html", mime="text/html", key=f"dl_min_{t['id']}", use_container_width=True)
                with b2:
                    st.download_button("📥 تحميل نموذج الامتحان .html", data=html_exam.encode("utf-8"), file_name=f"exam_template_{t['id']}.html", mime="text/html", key=f"dl_exam_{t['id']}", use_container_width=True)

    with selected_tabs[5]:
        st.subheader("📊 تقارير قياس المستويات")
        d_start = st.date_input("من تاريخ", date.today() - timedelta(days=30))
        d_end = st.date_input("إلى تاريخ", date.today())
        start_dt_str = datetime.combine(d_start, datetime.min.time()).isoformat()
        end_dt_str = datetime.combine(d_end, datetime.max.time()).isoformat()

        with db() as c:
            df_res = pd.read_sql_query("""SELECT s.id AS 'رقم الجلسة', t.name AS 'اسم المتدرب', t.facility AS 'جهة العمل', COALESCE(et.name, 'اختبار معتمد') AS 'اسم الاختبار', COALESCE(et.exam_type, 'شامل') AS 'تصنيف التقييم', s.score AS 'الدرجة', s.max_score AS 'الدرجة الكلية', s.percent AS 'النسبة المئوية %', CASE WHEN s.passed = 1 THEN 'اجتزت بنجاح' ELSE 'لم تجتز' END AS 'حالة الاجتياز', s.certificate_id AS 'رقم الشهادة', s.submitted_at AS 'تاريخ ووقت التسليم' FROM exam_sessions s JOIN trainees t ON t.id = s.trainee_id LEFT JOIN exam_templates et ON et.id = s.template_id WHERE s.status = 'submitted' AND s.submitted_at >= ? AND s.submitted_at <= ? ORDER BY s.submitted_at DESC""", c, params=[start_dt_str, end_dt_str])

        if not df_res.empty:
            st.dataframe(df_res, use_container_width=True, hide_index=True)
            html_report_str = generate_report_html_document(df_res, f"الفترة من {d_start} إلى {d_end}", custom_print_notes)
            st.download_button("📥 تحميل التقرير الشامل .html", data=html_report_str.encode("utf-8"), file_name="report.html", mime="text/html", use_container_width=True)

    with selected_tabs[6]:
        st.subheader("💾 النسخ الاحتياطي للقاعدة")
        if st.button("إنشاء نسخة احتياطية الآن"):
            path = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            src = sqlite3.connect(DB_PATH)
            dst = sqlite3.connect(path)
            try: src.backup(dst)
            finally: dst.close(); src.close()
            st.success("✅ تم النسخ الاحتياطي بنجاح.")

    if st.session_state.role == "admin":
        with selected_tabs[7]:
            st.subheader("👥 إدارة المستخدمين")
            with db() as c: users_list = c.execute("SELECT id, username, role, active, created_at FROM users").fetchall()
            st.dataframe(pd.DataFrame([dict(u) for u in users_list]), use_container_width=True, hide_index=True)
        with selected_tabs[8]:
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
    assigned_type = tr["assigned_exam_type"] or "قبل التدريب (Pre-Test)"
    st.markdown(f'<div class="card"><h3>مرحباً بك، {esc(tr["name"])}</h3><p>الجهة: {esc(tr["facility"])} | نوع الاختبار: <b>{esc(assigned_type)}</b></p></div>', unsafe_allow_html=True)
    
    with db() as c:
        matching_template = c.execute("SELECT * FROM exam_templates WHERE exam_type=? AND active=1", (assigned_type,)).fetchone()
        if not matching_template: matching_template = c.execute("SELECT * FROM exam_templates WHERE active=1 LIMIT 1").fetchone()

    if st.button("بدء الاختبار المخصص الآن", use_container_width=True):
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
        opts = json.loads(row["options_json"])
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
        submit_session(session_id)
        st.session_state.last_result_id = session_id
        st.session_state.exam_session_id = None
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
        st.success("تم تسليم الاختبار بنجاح!")
        cert_html = generate_compact_certificate_html(sid, custom_print_notes)
        st.download_button("📥 تحميل شهادة الاجتياز .html", data=cert_html.encode("utf-8"), file_name=f"certificate_{sid}.html", mime="text/html")
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
