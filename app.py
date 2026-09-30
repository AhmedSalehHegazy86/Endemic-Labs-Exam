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

st.markdown("""
<style>
html,body,[class*="css"]{direction:rtl;text-align:right;font-family:"Cairo","Tahoma",sans-serif}
.stApp{background:linear-gradient(135deg,#f0fdf4 0%,#dcfce7 45%,#bbf7d0 100%)}
.block-container{max-width:96% !important;padding-left:2.5rem !important;padding-right:2.5rem !important;padding-top:1rem;padding-bottom:1rem}
.hero{background:linear-gradient(90deg,#064e3b,#065f46,#047857);color:#fff;padding:12px;border-radius:10px;text-align:center;box-shadow:0 4px 10px rgba(0,0,0,0.1);margin-bottom:10px}
.card,.question{background:#fff;padding:12px 18px;border-radius:8px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.04);border-right:5px solid #059669}
.metric{background:#fff;padding:10px;border-radius:8px;text-align:center;border-top:3px solid #059669;box-shadow:0 1px 4px rgba(0,0,0,0.04)}
.metric .v{font-size:22px;font-weight:800;color:#065f46}
.metric .l{color:#4b5563;font-weight:700;font-size:12px}

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
[data-testid="stSidebar"]{display:none !important;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2) دوال النظام وقاعدة البيانات وبنك الأسئلة
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
            exam_type TEXT NOT NULL DEFAULT 'تدريبي (قبل التدريب)',
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
    svg_fasciola = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTIwIiB2aWV3Qm94PSIwIDAgMjAwIDEyMCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2Y4ZmFmYyIvPjxlbGxpcHNlIGN4PSIxMDAiIGN5PSI2MCIgcng9IjcwIiByeT0iNDIiIGZpbGw9IiNlMmVmZTUiIHN0cm9rZT0iIzA1OTY2OSIgc3Ryb2tlLXdpZHRoPSIzIi8+PHBhdGggZD0iTTM1LDUwIEw0NSw1MCIgc3Ryb2tlPSIjMTEyMjMzIiBzdHJva2Utd2lkdGg9IjQiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPjwvc3ZnPg=="
    svg_giardia = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTIwIiB2aWV3Qm94PSIwIDAgMjAwIDEyMCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2Y4ZmFmYyIvPjxlbGxpcHNlIGN4PSIxMDAiIGN5PSI2MCIgcng9IjUwIiByeT0iMzUiIGZpbGw9IiNlMmVmZTUiIHN0cm9rZT0iIzA1OTY2OSIgc3Ryb2tlLXdpZHRoPSIzIi8+PGNpcmNsZSBjeD0iODAiIGN5PSI1MCIgcj0iNSIgZmlsbD0iIzMzMzMzMyIvPjxjaXJjbGUgY3g9IjEyMCIgY3k9IjUwIiByPSI1IiBmaWxsPSIjMzMzMzMzIi8+PC9zdmc+"
    svg_ascaris = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMTIwIiB2aWV3Qm94PSIwIDAgMjAwIDEyMCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2Y4ZmFmYyIvPjxjaXJjbGUgY3g9IjEwMCIgY3k9IjYwIiByPSIzOCIgZmlsbD0iI2UyZWZlNSIgc3Ryb2tlPSIjMDU5NjY5IiBzdHJva2Utd2lkdGg9IjMiLz48Y2lyY2xlIGN4PSIxMDAiIGN5PSI2MCIgcj0iMjUiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzExMjIzMyIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtZGFzaGFycmF5PSI0LDIiLz48L3N2Zz4="

    complete_bank = [
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_schisto_mansoni}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["البلهارسيا اليابانية", "البلهارسيا البولية", "التريكوريس", "البلهارسيا المعوية (Schistosoma mansoni)"], "ans": 3},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_schisto_haematobium}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["البلهارسيا المعوية", "التريكوريس", "البلهارسيا البولية ذات الشوكة الطرفية", "الهتروفيس"], "ans": 2},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_fasciola}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["الهتروفيس", "التريكوريس", "الفاشيولا الكبدية ذات الغطاء", "التينيا"], "ans": 2},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_giardia}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["بيضة التريكوريس", "كيس الجيارديا المتشيس", "كيس الأميبا", "تروفوزويت الجيارديا"], "ans": 1},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_ascaris}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["بيضة إسكارس لومبريكويدس", "بيضة أنكلستوما", "بيضة أوكسيورس", "بيضة تريكوريس"], "ans": 0},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_schisto_mansoni}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["بيضة الإسكارس", "بيضة الأنكلستوما", "بيضة الفاشيولا", "بيضة الهيمينولبس"], "ans": 1},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_giardia}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["بيضة الهيمينولبس نانا", "بيضة التينيا", "بيضة الهتروفيس", "بيضة البلهارسيا"], "ans": 0},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_ascaris}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["كيس إنتاميبا هستوليتيكا", "كيس الجيارديا", "تروفوزويت الملاريا", "بويضة الإسكارس"], "ans": 0},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_schisto_haematobium}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["بيضة تريكوريس تريكيورا ذات السدادات", "بيضة الفاشيولا", "بيضة البلهارسيا", "بيضة التينيا"], "ans": 0},
        {"cat": "أسئلة الصور والأشكال", "lvl": "صعب", "q": f"IMAGE:{svg_fasciola}\n\nتعرف على العينة المجهرية الظاهرة وحدد الطفيل المناسب:", "opts": ["بيضة ديدان التينيا الشريطية", "بيضة الهيمينولبس", "بيضة الإسكارس", "بيضة الهتروفيس"], "ans": 0},

        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "سهل", "q": "ما العائل الوسيط للبلهارسيا البولية ؟", "opts": ["بولينس (Bulinus)", "بيرينلا كونيكا", "بيومفلاريا", "ليمنيا"], "ans": 0},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "سهل", "q": "ما العائل الوسيط للبلهارسيا المعوية؟", "opts": ["ليمنيا", "بولينس", "بيومفلاريا (Biomphalaria)", "بيرينلا كونيكا"], "ans": 2},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "متوسط", "q": "ما الطور الذي يخرج من البويضة بعد وصولها إلى الماء العذب في دورة البلهارسيا ؟", "opts": ["الميراسيديوم (Miracidium)", "الميتاسركاريا", "السركاريا", "اليرقة الربدية"], "ans": 0},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "متوسط", "q": "إذا لم يجد الميراسيديوم القوقع المناسب خلال المدة المحددة، فما مصيره؟", "opts": ["يموت", "يتكاثر في الماء", "يتحول إلى ميتاسركاريا", "يصبح دودة بالغة"], "ans": 0},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "متوسط", "q": "ما الطور الذي يخرج من القوقع ويبحث عن الإنسان في الماء؟", "opts": ["الميراسيديوم", "السركاريا (Cercaria)", "اليرقة الربدية", "البيضة"], "ans": 1},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "صعب", "q": "أي عبارة تصف انتقال البلهارسيا من الماء إلى الإنسان بصورة صحيحة؟", "opts": ["البيضة تخترق الجلد مباشرة", "الميتاسركاريا تلتصق بالجلد", "الميراسيديوم يهاجر إلى الدم", "السركاريا تخترق جلد الإنسان"], "ans": 3},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "صعب", "q": "الموضع النهائي للأنثى في البلهارسيا البولية هو أوعية جدار:", "opts": ["الأمعاء الدقيقة", "القنوات المرارية", "القولون", "المثانة البولية"], "ans": 3},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "صعب", "q": "الموضع النهائي للأنثى في البلهارسيا المعوية هو أوعية جدار:", "opts": ["القنوات المرارية", "المعدة", "المثانة", "القولون والأمعاء الغليظة"], "ans": 3},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "سهل", "q": "أي مضاعفة صحية ترتبط بالبلهارسيا البولية على المدى الطويل؟", "opts": ["انسداد الأمعاء", "سرطان المثانة البولية", "خراج الكبد", "فقر الدم الحاد"], "ans": 1},
        {"cat": "الاستراتيجية العامة ومكافحة البلهارسيا", "lvl": "سهل", "q": "أي مجموعة من المضاعفات ترتبط بالبلهارسيا المعوية؟", "opts": ["سرطان الرئة", "تليف الكبد وتضخم الطحال ودوالى المريء", "انسداد الأمعاء", "التهاب المثانة"], "ans": 1},

        {"cat": "الفاشيولا", "lvl": "سهل", "q": "ما العائل الوسيط لدودة الفاشيولا الكبدية؟", "opts": ["قوقع البولينس", "قوقع بيرينلا كونيكا", "قوقع الليمنيا (Lymnaea)", "قوقع البيومفلاريا"], "ans": 2},
        {"cat": "الفاشيولا", "lvl": "سهل", "q": "ما الطور المعدي للإنسان في الإصابة بالفاشيولا؟", "opts": ["البويضة", "الميراسيديوم", "السركاريا الحرة", "الميتاسركاريا المتحوصلة"], "ans": 3},
        {"cat": "الفاشيولا", "lvl": "متوسط", "q": "ما الطريق الرئيس لعدوى الإنسان بالفاشيولا؟", "opts": ["اختراق الجلد", "استنشاق البيوض", "تناول لحم غير مطهو", "تناول خضروات أو أعشاب ملوثة بالميتاسركاريا المتحوصلة"], "ans": 3},
        {"cat": "الفاشيولا", "lvl": "متوسط", "q": "لماذا يصعب تشخيص الحالات الحادة بالفحص البرازي مباشرة؟", "opts": ["لأن الطفيل في الرئة", "لأن البيوض لا تظهر في البراز في هذه المرحلة المبكرة للهجرة الكبدية", "لعدم وجود طفيل", "لأنها تظهر في البول"], "ans": 1},
        {"cat": "الفاشيولا", "lvl": "متوسط", "q": "أين تستقر دودة الفاشيولا البالغة داخل جسم العائل الأساسي؟", "opts": ["القنوات المرارية للكبد", "الأعور", "الأمعاء الدقيقة", "المثانة"], "ans": 0},

        {"cat": "الهتروفيس", "lvl": "سهل", "q": "ما الطور المعدي للإنسان في دودة الهتروفيس؟", "opts": ["البويضة", "السركاريا الحرة", "الميتاسركاريا المتحوصلة في عضلات السمك", "الميراسيديوم"], "ans": 2},
        {"cat": "الهتروفيس", "lvl": "متوسط", "q": "أي أسماك ذكرت كمضيف ثان للطور المعدي للهتروفيس في مصر؟", "opts": ["السردين", "القرش", "الجمبري", "البوري والبلطي"], "ans": 3},
        {"cat": "الهتروفيس", "lvl": "متوسط", "q": "ما طريقة العدوى الأساسية بدودة الهتروفيس المعوية؟", "opts": ["تناول الأسماك المصابة غير المطهوة جيداً", "شرب ماء ملوث", "اختراق الجلد", "استنشاق الغبار"], "ans": 0},

        {"cat": "الديدان الشريطية", "lvl": "سهل", "q": "ما الطور المعدي المباشر لدودة الهيمنولبس نانا (Hymenolepis nana)؟", "opts": ["اليرقة الخيطية", "البويضة فور خروجها مع البراز", "الميتاسركاريا", "السركاريا"], "ans": 1},
        {"cat": "الديدان الشريطية", "lvl": "متوسط", "q": "ما الذي يميز دورة حياة الهيمينولبس نانا مقارنة بالديدان الشريطية الأخرى؟", "opts": ["تحتاج لسمكة", "تحتاج لقوقع", "تحتاج لخنزير", "يمكن أن تكتمل داخل الإنسان دون الحاجة لعائل وسيط خارجي"], "ans": 3},
        {"cat": "الديدان الشريطية", "lvl": "متوسط", "q": "ما الطور المعدي للإنسان في ديدان التينيا (Taenia) المرتبطة بلحوم الأبقار أو الخنازير؟", "opts": ["البويضة الناضجة", "الجنين المتكيس في العضلات (Cysticercus)", "السركاريا", "الميراسيديوم"], "ans": 1},

        {"cat": "الديدان الأسطوانية", "lvl": "سهل", "q": "أين تعيش دودة الإسكارس البالغة في جسم الإنسان؟", "opts": ["القنوات المرارية", "الأعور", "الأمعاء الدقيقة", "المثانة"], "ans": 2},
        {"cat": "الديدان الأسطوانية", "lvl": "متوسط", "q": "ما الطور المعدي لدودة الإسكارس للإنسان؟", "opts": ["اليرقة الربدية", "اليرقة الخيطية", "البويضة غير الملقحة", "البويضة الناضجة التي تحتوي على اليرقة"], "ans": 3},
        {"cat": "الديدان الأسطوانية", "lvl": "سهل", "q": "ما أكثر علامة سريرية مميزة للعدوى بالدودة الدبوسية (الإكسيورس)؟", "opts": ["يرقان كبدي", "فقر دم", "حكة شديدة حول الشرج ليلاً", "بول دموي"], "ans": 2},
        {"cat": "الديدان الأسطوانية", "lvl": "سهل", "q": "ما الطور المعدي لدودة الأنكلستوما للإنسان؟", "opts": ["البويضة وحدها", "اليرقة الخيطية المعدية (Filariform larva) النافذة عبر الجلد", "الميتاسركاريا", "السركاريا"], "ans": 1},

        {"cat": "الأوليات", "lvl": "سهل", "q": "أين تستقر طفيليات إنتاميبا هستوليتيكا (Entamoeba histolytica) أساساً؟", "opts": ["الأمعاء الدقيقة", "الأمعاء الغليظة (القولون)", "المثانة", "الكبد مباشرة"], "ans": 1},
        {"cat": "الأوليات", "lvl": "متوسط", "q": "ما الطور المقاوم للعصارة المعدية القادر على نقل عدوى الأميبا؟", "opts": ["السركاريا", "الكيس (Cyst)", "الميراسيديوم", "التروفوزويت"], "ans": 1},
        {"cat": "الأوليات", "lvl": "سهل", "q": "أين تعيش طفيليات الجيارديا لامبليا (Giardia lamblia) أساساً؟", "opts": ["الأعور", "المثانة", "القنوات المرارية", "الأمعاء الدقيقة وخاصة الاثنا عشر"], "ans": 3},

        {"cat": "الفحوص المعملية", "lvl": "سهل", "q": "أي طريقة معملية مخصصة للفحص النوعي والكمي لبويضات البراز؟", "opts": ["كاتو كاتس (Kato-Katz)", "التصفية الغشائية للبول", "المسحة الشرجية", "زرع الدم"], "ans": 0},
        {"cat": "الفحوص المعملية", "lvl": "متوسط", "q": "ما المبدأ الأساسي لطريقة التعويم في تحليل البراز معملياً؟", "opts": ["إذابة البويضات", "تعويم البيوض الأخف وزناً على سطح محلول ملحي مشبع", "قتل اليرقات", "ترسيب البيوض الثقيلة"], "ans": 1},

        {"cat": "الحالات التطبيقية", "lvl": "صعب", "q": "عينة براز أظهرت عند الفحص المجهري بويضة بيضاوية تحتوي على شوكة جانبية واضحة. ما التشخيص المناسب؟", "opts": ["البلهارسيا البولية", "البلهارسيا المعوية (Schistosoma mansoni)", "التريكوريس", "الهتروفيس"], "ans": 1},
        {"cat": "الحالات التطبيقية", "lvl": "صعب", "q": "عامل زراعي يمشي حافي القدمين على تربة رطبة وظهرت عليه أعراض فقر دم وطفح جلدي موضعي. ما الطفيل الأرجح؟", "opts": ["الهيمينولبس", "الأنكلستوما (Ancylostoma)", "الهتروفيس", "الجيارديا"], "ans": 1},

        {"cat": "أسئلة الصح والخطأ", "lvl": "متنوع", "q": "البلهارسيا المعوية ترتبط بقوقع بيومفلاريا كوسيط.", "opts": ["صح", "خطأ"], "ans": 0},
        {"cat": "أسئلة الصح والخطأ", "lvl": "متنوع", "q": "السركاريا هي الطور الذي يخترق جلد الإنسان في دورة البلهارسيا.", "opts": ["صح", "خطأ"], "ans": 0}
    ]

    base_questions_templates = [
        ("ما هي الوسيلة الأفضل للوقاية من الإصابة بديدان الهتروفيس؟", ["طهي الأسماك جيداً قبل الأكل", "غسل اليدين فقط", "تجنب شرب الماء المقطر", "تعرض الجلد للشمس"], 0),
        ("أي من الطفيليات الآتية يسبب مرض الدوسنتاريا الأميبية؟", ["إنتاميبا هستوليتيكا", "الجيارديا لامبليا", "الإسكارس", "الأنكلستوما"], 0),
        ("ما الفحص المعملي الأدق لتشخيص الإصابة بالبلهارسيا البولية في المراحل المبكرة؟", ["التصفية الغشائية لبول العيان", "زرع الدم", "المسحة الشرجية", "اختبار البراز العام"], 0),
        ("ما هو العرض السريري الأبرز للإصابة الشديدة بديدان الإسكارس للأطفال؟", ["اضطرابات معوية وآلام بالبطن", "حكة جلدية شديدة", "اصفرار العينين فقط", "التهاب المثانة الحاد"], 0)
    ]

    categories_pool = ["الاستراتيجية العامة ومكافحة البلهارسيا", "الفاشيولا", "الهتروفيس", "الديدان الشريطية", "الديدان الأسطوانية", "الأوليات", "الفحوص المعملية", "الحالات التطبيقية", "أسئلة الصور والأشكال"]
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
# 3) دوال إدارة المتدربين والامتحانات
# ============================================================
def login_user(u, p):
    with db() as c:
        user = c.execute("SELECT * FROM users WHERE username=? AND active=1", (u.strip(),)).fetchone()
        if user and verify_password(p, user["password_hash"]):
            c.execute("UPDATE users SET last_login=? WHERE id=?", (now(), user["id"]))
            return dict(user)
    return None

def create_trainee(facility, name, phone):
    with db() as c:
        cur = c.execute("INSERT INTO trainees(facility,name,phone,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                        (normalize_text(facility), normalize_text(name), normalize_text(phone), "pending", now(), now()))
        tid = cur.lastrowid
    audit("create_trainee", "trainee", {"id": tid, "name": name})
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

def set_trainee_status(tid, status):
    with db() as c:
        c.execute("UPDATE trainees SET status=?, updated_at=?, approved_at=CASE WHEN ?='approved' THEN ? ELSE approved_at END WHERE id=?",
                  (status, now(), status, now(), tid))
    audit("update_trainee", "trainee", {"id": tid, "status": status})

def trainees_df(status=None):
    with db() as c:
        q = "SELECT id, facility, name, phone, status, created_at, approved_at FROM trainees"
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
    if len(final_list) < target and len(img_rows) > num_img_needed:
        extra_img = img_rows[num_img_needed : num_img_needed + (target - len(final_list))]
        final_list.extend(extra_img)
        
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
        passed = 1 if percent >= float(t["pass_percent"]) else 0
        cert = f"ELX-{sid:06d}"
        
        c.execute("UPDATE exam_sessions SET status='submitted', submitted_at=?, score=?, max_score=?, percent=?, passed=?, certificate_id=? WHERE id=?",
                  (now(), correct, max_score, percent, passed, cert, sid))
        c.execute("UPDATE trainees SET status='completed', updated_at=? WHERE id=?", (now(), s["trainee_id"]))
        return {"score": correct, "max_score": max_score, "percent": percent, "passed": passed, "certificate_id": cert}

# ============================================================
# 4) دوال التصدير والشهادات
# ============================================================
def generate_compact_certificate_html(sid):
    with db() as c:
        r = c.execute("""SELECT s.*, t.name trainee_name, t.facility, e.name template_name 
                         FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?""", (sid,)).fetchone()
    if not r: return ""
    status_text = "اجتزت بنجاح" if r["passed"] else "لم تجتز الاختبار"
    
    score_val = r["score"] if r["score"] is not None else 0
    max_score_val = r["max_score"] if r["max_score"] is not None else 0
    percent_val = r["percent"] if r["percent"] is not None else 0.0
    
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; text-align: center; background: #fff; padding: 20px; direction: rtl; }}
            .cert {{ border: 4px solid #059669; padding: 25px; border-radius: 12px; width: 100%; max-width: 750px; margin: auto; background: #fdfbf7; position: relative; }}
            .header-top {{ position: absolute; top: 15px; right: 20px; text-align: right; font-size: 10pt; font-weight: bold; color: #065f46; line-height: 1.3; }}
            .footer-bottom {{ margin-top: 35px; display: flex; justify-content: space-between; font-size: 9pt; font-weight: bold; text-align: center; border-top: 1px dashed #059669; padding-top: 15px; }}
            h1 {{ color: #065f46; font-size: 24px; margin-bottom: 5px; }}
            h2 {{ color: #047857; font-size: 18px; }}
            p {{ font-size: 15px; line-height: 1.8; color: #1f2937; }}
        </style>
    </head>
    <body>
        <div class="cert">
            <div class="header-top">
                الإدارة الصحية باولاد صقر<br>
                قسم المتوطنة و قسم المعامل<br>
                وحدة تدريب معامل المتوطنة
            </div>
            <div style="margin-top: 40px;">
                <h2>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h2>
                <hr style="border: 1px solid #059669; margin: 10px 0;">
                <h1>شهادة اجتياز اختبار رسمي معتمدة</h1>
                <p>
                    تشهد إدارة المنصة بأن المتدرب/ـة: <b style="font-size: 18px; color: #047857;">{esc(r["trainee_name"])}</b><br>
                    التابع/ـة لجهة: <b>{esc(r["facility"])}</b><br>
                    قد أتم/ت بنجاح اختبار: <b>{esc(r["template_name"])}</b><br>
                    النتيجة النهائية: <b>{score_val} / {max_score_val} ({percent_val:.1f}%)</b><br>
                    الحالة: <b style="color: {'green' if r['passed'] else 'red'};">{status_text}</b><br>
                    رقم الشهادة: <code>{r["certificate_id"]}</code> | التاريخ: {esc(r["submitted_at"])}
                </p>
            </div>
            <div class="footer-bottom">
                <div>مسؤل تدريب معامل المتوطنة</div>
                <div>رئيس قسم المعامل</div>
                <div>مدير المتوطنة</div>
                <div>يعتمد مدير عام الادارة</div>
            </div>
        </div>
    </body>
    </html>
    """

def generate_compact_exam_html(template_id):
    with db() as c:
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        qs = choose_questions(t)
    
    html_out = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 8mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; direction: rtl; text-align: right; background: #fff; padding: 5px; font-size: 8pt; color: #111; line-height: 1.2; }}
            .top-right-header {{ float: right; text-align: right; font-size: 9pt; font-weight: bold; color: #065f46; line-height: 1.2; margin-bottom: 5px; }}
            .exam-title-area {{ text-align: center; clear: both; border-bottom: 2px solid #065f46; padding-bottom: 5px; margin-bottom: 8px; }}
            .exam-title-area h2 {{ font-size: 11pt; margin: 0 0 2px 0; color: #065f46; }}
            .exam-title-area h3 {{ font-size: 9.5pt; margin: 0 0 2px 0; }}
            .exam-title-area p {{ font-size: 7.5pt; margin: 0; }}
            .exam-container {{ column-count: 2; column-gap: 10mm; }}
            .q-box {{ margin-bottom: 6px; page-break-inside: avoid; break-inside: avoid; border: 1px solid #94a3b8; padding: 6px; border-radius: 4px; background: #fff; }}
            .q-img-layout-print {{ display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 4px; }}
            .q-text-print {{ flex: 1; text-align: right; font-weight: bold; font-size: 8pt; }}
            .q-img-print {{ flex: 0 0 75px; text-align: left; }}
            .q-img-print img {{ max-width: 70px; height: auto; border-radius: 3px; background: #fff; border: 1px solid #cbd5e1; }}
            ul {{ list-style-type: none; padding-right: 12px; margin: 2px 0; }}
            li {{ margin-bottom: 2px; font-size: 7.5pt; }}
            .exam-footer {{ margin-top: 20px; display: flex; justify-content: space-between; font-size: 8pt; font-weight: bold; text-align: center; border-top: 1px dashed #059669; padding-top: 8px; page-break-inside: avoid; }}
        </style>
    </head>
    <body>
        <div class="top-right-header">
            الإدارة الصحية باولاد صقر<br>
            قسم المتوطنة و قسم المعامل<br>
            وحدة تدريب معامل المتوطنة
        </div>
        <div class="exam-title-area">
            <h2>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h2>
            <h3>نموذج امتحان: {esc(t['name'])}</h3>
            <p>المدة: {t['duration_minutes']}د | عدد الأسئلة: {len(qs)} | اسم المتدرب: ........................................ | الجهة: ........................</p>
        </div>
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
                <div class='q-img-layout-print'>
                    <div class='q-text-print'><b>س {idx+1}:</b> {esc(actual_q)}</div>
                    <div class='q-img-print'><img src='{img_data}' alt='عينة مجهرية' crossorigin='anonymous'></div>
                </div>
                <ul>
            """
        else:
            cleaned_q = clean_question_text(q_raw)
            html_out += f"<div class='q-box'><b>س {idx+1}: {cleaned_q}</b><ul>"
            
        for opt in opts:
            html_out += f"<li>[ &nbsp; ] {esc(opt)}</li>"
        html_out += "</ul></div>"
        
    html_out += f"""
        </div>
        <div class="exam-footer">
            <div>مسؤل تدريب معامل المتوطنة</div>
            <div>رئيس قسم المعامل</div>
            <div>مدير المتوطنة</div>
            <div>يعتمد مدير عام الادارة</div>
        </div>
    </body></html>
    """
    return html_out

# ============================================================
# 5) المسارات وواجهات المستخدم
# ============================================================
for k, v in {"logged_in": False, "username": "", "role": "", "trainee_id": None, "trainee_name": "", "exam_session_id": None, "last_result_id": None, "form_key": 0, "edit_success_msg": "", "add_success_msg": "", "del_success_msg": ""}.items():
    if k not in st.session_state: st.session_state[k] = v

def header():
    st.markdown('<div class="hero"><h1>🔬 المنصة الرقمية لاختبارات معامل المتوطنة</h1><div>Professional v6.0 FINAL • مؤقت تنازلي (ساعات ودقائق وثوانٍ) مثبت أعلى صفحة الامتحان ومتزامن بدقة</div></div>', unsafe_allow_html=True)

def login_portal():
    header()
    st.markdown('<div class="card"><h3>🧑‍🔬 بوابة المتدربين والامتحانات</h3><p>أدخل بياناتك للتسجيل أو لبدء الاختبار المباشر.</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("trainee_request"):
            st.markdown("<b>إرسال طلب جديد ودخول</b>", unsafe_allow_html=True)
            facility = st.text_input("الجهة / الإدارة الصحية")
            name = st.text_input("الاسم الرباعي")
            phone = st.text_input("رقم الهاتف")
            if st.form_submit_button("إرسال الطلب والدخول", use_container_width=True):
                if facility and name:
                    existing = trainee_by_credentials(name, facility)
                    if existing:
                        st.session_state.trainee_id = existing["id"]
                        st.session_state.trainee_name = existing["name"]
                        st.success("تم التعرف على حسابك! جاري الدخول...")
                        st.rerun()
                    else:
                        tid = create_trainee(facility, name, phone)
                        st.success(f"✅ تم تسجيل بياناتك بنجاح! رقم التسجيل (ID) الخاص بك هو: **{tid}**. يرجى الاحتفاظ به للاستعلام الفوري وبانتظار اعتماد الإدارة.")
                else:
                    st.warning("الرجاء إدخال الجهة والاسم الرباعي.")
                    
    with col2:
        with st.container(border=True):
            st.markdown("<b>🔍 أيقونة فحص حالة الاعتماد الفوري</b>", unsafe_allow_html=True)
            chk_id = st.number_input("أدخل رقم تسجيل المتدرب (ID)", min_value=1, step=1, value=1)
            if st.button("التحقق الفوري من الحالة", use_container_width=True):
                raw = get_trainee_status_raw_by_id(int(chk_id))
                if raw:
                    status_msg = STATUS_AR.get(raw['status'], raw['status'])
                    st.info(f"📋 نتيجة فحص المتدرب (الاسم: <b>{raw['name']}</b> - الجهة: {raw['facility']}): <b>{status_msg}</b>")
                else:
                    st.warning("⚠️ لم يتم العثور على أي تسجيل بهذا الرقم في سجلات المنصة.")

    st.markdown("---")
    with st.expander("🔐 دخول الإدارة / المالك (انقر هنا للعرض)"):
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
        st.write(f"**المستخدم:** {st.session_state.username} | **الصلاحية:** {ROLES.get(st.session_state.role, '')}")
    with c_btn:
        if st.button("تسجيل الخروج", use_container_width=True):
            audit("logout")
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.rerun()

    tabs = ["لوحة التحكم", "اعتماد المتدربين", "بنك الأسئلة الشامل", "إدارة الأسئلة (إضافة/تعديل/حذف)", "قوالب وامتحانات ورقية", "التقارير المتقدمة والتصدير", "النسخ الاحتياطي"]
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
        st.subheader("🧑‍🔬 اعتماد المتدربين والتحكم بالصلاحيات")
        sub_tabs = st.tabs(["الطلبات المعلقة", "جميع المتدربين"])
        with sub_tabs[0]:
            df_pend = trainees_df("pending")
            if df_pend.empty:
                st.info("لا توجد طلبات معلقة بانتظار الموافقة.")
            else:
                for _, r in df_pend.iterrows():
                    with st.container(border=True):
                        st.write(f"**رقم التسجيل (ID):** {r['id']} | **الاسم:** {r['name']} | **الجهة:** {r['facility']} | **الهاتف:** {r['phone']}")
                        b1, b2 = st.columns(2)
                        if b1.button("✅ موافقة واعتماد", key=f"app_{r['id']}"):
                            set_trainee_status(int(r['id']), "approved")
                            st.success(f"تم اعتماد {r['name']} بنجاح!")
                            st.rerun()
                        if b2.button("❌ رفض", key=f"rej_{r['id']}"):
                            set_trainee_status(int(r['id']), "rejected")
                            st.rerun()
        with sub_tabs[1]:
            df_tr = trainees_df()
            st.dataframe(df_tr, use_container_width=True, hide_index=True)
            if not df_tr.empty:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df_tr.to_excel(writer, index=False, sheet_name="Trainees")
                st.download_button("📥 تصدير المتدربين Excel", buf.getvalue(), file_name="trainees_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with selected_tabs[2]:
        st.subheader("🧠 بنك الأسئلة المتكامل في قاعدة البيانات")
        with db() as c:
            df_q = pd.read_sql_query("SELECT id, difficulty, category, question, active FROM questions ORDER BY id ASC", c)
        st.write(f"إجمالي الأسئلة الحالية في قاعدة البيانات: **{len(df_q)}** سؤالاً.")
        st.dataframe(df_q, use_container_width=True, hide_index=True)

    with selected_tabs[3]:
        st.subheader("⚙️ إدارة الأسئلة (إضافة، تعديل، وحذف)")
        sub_img_tabs = st.tabs(["➕ إضافة سؤال جديد", "✏️ تعديل سؤال موجود", "🗑 حذف سؤال"])
        
        categories_list_opts = [
            "أسئلة الصور والأشكال",
            "الاستراتيجية العامة ومكافحة البلهارسيا",
            "الفاشيولا",
            "الهتروفيس",
            "الديدان الشريطية",
            "الديدان الأسطوانية",
            "الأوليات",
            "الفحوص المعملية",
            "الحالات التطبيقية",
            "أسئلة الصح والخطأ"
        ]

        # 1) إضافة سؤال جديد
        with sub_img_tabs[0]:
            if st.session_state.add_success_msg:
                st.success(st.session_state.add_success_msg)
                st.session_state.add_success_msg = ""
                
            with st.form(key=f"add_custom_img_q_form_{st.session_state.form_key}"):
                st.markdown("<b>إضافة سؤال جديد وتحديد القسم التابع له</b>", unsafe_allow_html=True)
                selected_cat = st.selectbox("اختر القسم:", categories_list_opts)
                c_text = st.text_area("نص السؤال التشخيصي:")
                c_diff = st.selectbox("مستوى الصعوبة", ["سهل", "متوسط", "صعب"])
                uploaded_img = st.file_uploader("رفع ملف الصورة (اختياري):", type=["png", "jpg", "jpeg"])
                
                opt1 = st.text_input("الخيار الأول (الإجابة الصحيحة مثلاً):", value="")
                opt2 = st.text_input("الخيار الثاني:", value="")
                opt3 = st.text_input("الخيار الثالث:", value="")
                opt4 = st.text_input("الخيار الرابع:", value="")
                correct_ans_text = st.text_input("اكتب النص المطابق تماماً للإجابة الصحيحة من الخيارات أعلاه:")
                
                if st.form_submit_button("حفظ وإضافة السؤال الجديد"):
                    if not c_text or not correct_ans_text:
                        st.error("الرجاء إدخال نص السؤال والإجابة الصحيحة على الأقل.")
                    else:
                        img_uri_final = ""
                        if uploaded_img is not None:
                            img_bytes = uploaded_img.read()
                            encoded_b64 = __import__("base64").b64encode(img_bytes).decode("utf-8")
                            img_uri_final = f"data:image/{uploaded_img.type.split('/')[-1]};base64,{encoded_b64}"
                        
                        full_q_str = f"IMAGE:{img_uri_final}\n\n{c_text}" if img_uri_final else c_text
                        opts_list = [o for o in [opt1, opt2, opt3, opt4] if o.strip() != ""]
                        if correct_ans_text not in opts_list:
                            opts_list.append(correct_ans_text)
                        
                        try:
                            ans_idx = opts_list.index(correct_ans_text)
                            fp = hashlib.sha256((full_q_str + "|" + "|".join(opts_list)).encode("utf-8")).hexdigest()
                            with db() as c:
                                c.execute("""INSERT INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at)
                                             VALUES(?,?,?,?,?,?,?,?)""",
                                          (c_diff, selected_cat, full_q_str, json.dumps(opts_list, ensure_ascii=False), ans_idx, 1, fp, now()))
                            
                            reorder_question_ids()
                            st.session_state.add_success_msg = "✅ تم حفظ وإضافة السؤال الجديد بنجاح وإعادة ترقيم الـ IDs تباعاً من 1 حتى النهاية."
                            st.session_state.form_key += 1
                            st.rerun()
                        except Exception as e:
                            st.error(f"خطأ أثناء الحفظ: {e}")

        # 2) تعديل سؤال موجود
        with sub_img_tabs[1]:
            st.markdown("<b>✏️ تعديل بيانات السؤال برقم الـ ID الخاص به</b>", unsafe_allow_html=True)
            if st.session_state.edit_success_msg:
                st.success(st.session_state.edit_success_msg)
                st.session_state.edit_success_msg = ""
                
            with db() as c:
                all_qs_edit = c.execute("SELECT id, category, difficulty FROM questions ORDER BY id ASC").fetchall()
            
            if not all_qs_edit:
                st.info("لا توجد أسئلة متاحة للتعديل.")
            else:
                q_id_to_edit = st.selectbox("اختر رقم السؤال (ID) المراد تعديله:", [q["id"] for q in all_qs_edit], format_func=lambda x: f"رقم السؤال: {x}")
                
                with db() as c:
                    target_q = c.execute("SELECT * FROM questions WHERE id=?", (q_id_to_edit,)).fetchone()
                
                if target_q:
                    old_opts = json.loads(target_q["options_json"])
                    old_cat = target_q["category"]
                    old_diff = target_q["difficulty"]
                    
                    raw_q_text = target_q["question"]
                    extracted_text = raw_q_text
                    if raw_q_text.startswith("IMAGE:"):
                        parts = raw_q_text.split("\n\n", 1)
                        extracted_text = parts[1] if len(parts) > 1 else ""
                    
                    with st.form(key=f"edit_q_form_{q_id_to_edit}"):
                        new_cat = st.selectbox("تعديل القسم:", categories_list_opts, index=categories_list_opts.index(old_cat) if old_cat in categories_list_opts else 0)
                        new_diff = st.selectbox("تعديل المستوى:", ["سهل", "متوسط", "صعب"], index=["سهل", "متوسط", "صعب"].index(old_diff) if old_diff in ["سهل", "متوسط", "صعب"] else 0)
                        new_text = st.text_area("تعديل نص السؤال:", value=extracted_text)
                        
                        st.write("تعديل الخيارات المتاحة:")
                        e_opt1 = st.text_input("الخيار 1", value=old_opts[0] if len(old_opts) > 0 else "")
                        e_opt2 = st.text_input("الخيار 2", value=old_opts[1] if len(old_opts) > 1 else "")
                        e_opt3 = st.text_input("الخيار 3", value=old_opts[2] if len(old_opts) > 2 else "")
                        e_opt4 = st.text_input("الخيار 4", value=old_opts[3] if len(old_opts) > 3 else "")
                        
                        current_correct_ans = old_opts[target_q["answer"]] if target_q["answer"] < len(old_opts) else ""
                        new_correct_text = st.text_input("اكتب نص الإجابة الصحيحة المطابق لأحد الخيارات أعلاه:", value=current_correct_ans)
                        
                        if st.form_submit_button("حفظ التعديلات وتحديث السؤال"):
                            if not new_text or not new_correct_text:
                                st.error("الرجاء إدخال نص السؤال والإجابة الصحيحة.")
                            else:
                                updated_opts = [o for o in [e_opt1, e_opt2, e_opt3, e_opt4] if o.strip() != ""]
                                if new_correct_text not in updated_opts:
                                    updated_opts.append(new_correct_text)
                                try:
                                    new_ans_idx = updated_opts.index(new_correct_text)
                                    prefix = raw_q_text.split("\n\n", 1)[0] if raw_q_text.startswith("IMAGE:") else ""
                                    final_updated_q = f"{prefix}\n\n{new_text}" if prefix else new_text
                                    fp = hashlib.sha256((final_updated_q + "|" + "|".join(updated_opts)).encode("utf-8")).hexdigest()
                                    
                                    with db() as c:
                                        c.execute("""UPDATE questions SET difficulty=?, category=?, question=?, options_json=?, answer=?, fingerprint=? WHERE id=?""",
                                                  (new_diff, new_cat, final_updated_q, json.dumps(updated_opts, ensure_ascii=False), new_ans_idx, fp, q_id_to_edit))
                                    
                                    reorder_question_ids()
                                    st.session_state.edit_success_msg = f"✅ تم تحديث وتعديل بيانات السؤال رقم ({q_id_to_edit}) بنجاح!"
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"خطأ أثناء التعديل: {ex}")

        # 3) حذف سؤال
        with sub_img_tabs[2]:
            if st.session_state.del_success_msg:
                st.success(st.session_state.del_success_msg)
                st.session_state.del_success_msg = ""
                
            with db() as c:
                img_qs = c.execute("SELECT id, difficulty, category FROM questions ORDER BY id ASC").fetchall()
            st.write(f"عدد الأسئلة الإجمالي المتاح في قاعدة البيانات: **{len(img_qs)}**")
            for iq in img_qs:
                with st.container(border=True):
                    st.write(f"📌 **رقم السؤال (ID): {iq['id']}** | القسم: {iq['category']} | المستوى: {iq['difficulty']}")
                    if st.button(f"🗑️ حذف السؤال رقم {iq['id']} نهائياً", key=f"del_iq_{iq['id']}"):
                        with db() as c:
                            c.execute("DELETE FROM questions WHERE id=?", (iq['id'],))
                        reorder_question_ids()
                        st.session_state.del_success_msg = f"🗑️ تم حذف السؤال وإعادة ترقيم الـ IDs تباعاً من 1 حتى النهاية بنجاح!"
                        st.rerun()

    with selected_tabs[4]:
        st.subheader("🧩 قوالب الاختبارات وإدارة الأقسام")
        with db() as c:
            all_cats = [r["category"] for r in c.execute("SELECT DISTINCT category FROM questions").fetchall()]

        if st.session_state.role == "admin":
            with st.form("new_tpl"):
                st.markdown("<b>إضافة قالب اختبار جديد وتخصيص الأقسام (للمديرين فقط)</b>", unsafe_allow_html=True)
                t_name = st.text_input("اسم القالب")
                t_type = st.selectbox("تصنيف الاختبار", ["قبل التدريب (Pre-Test)", "بعد التدريب (Post-Test)", "اختبار تقييمي شامل"])
                t_num = st.number_input("عدد الأسئلة", 4, 100, 25)
                t_dur = st.number_input("المدة (بالدقائق)", 5, 180, 45)
                t_pass = st.number_input("نسبة النجاح %", 1.0, 100.0, 60.0)
                selected_cats = st.multiselect("اختر الأقسام المطلوبة لهذا القالب (اتركها فارغة لتشمل كافة الأقسام)", all_cats, default=all_cats)
                
                if st.form_submit_button("حفظ القالب الجديد"):
                    if t_name.strip():
                        with db() as c:
                            c.execute("""INSERT INTO exam_templates(name,exam_type,num_questions,duration_minutes,pass_percent,categories_json,created_at) VALUES(?,?,?,?,?,?,?)""",
                                      (t_name, t_type, t_num, t_dur, t_pass, json.dumps(selected_cats, ensure_ascii=False), now()))
                        st.success("✅ تم إنشاء قالب الاختبار وتخصيص أقسامه بنجاح بواسطة المدير.")
                        st.rerun()
        else:
            st.info("🔒 ميزة إنشاء وتعديل قوالب الاختبارات مقتصرة حصرياً على مديري النظام (Admins).")
        
        with db() as c:
            tpls = c.execute("SELECT * FROM exam_templates").fetchall()
        for t in tpls:
            with st.container(border=True):
                cats_list = ", ".join(json.loads(t["categories_json"])) if t["categories_json"] else "جميع الأقسام"
                st.write(f"**{t['name']}** — التصنيف: `{t['exam_type']}` | عدد الأسئلة: {t['num_questions']} | المدة: {t['duration_minutes']} دقيقة")
                st.write(f"📌 **الأقسام المخصصة:** {cats_list}")
                
                html_exam = generate_compact_exam_html(t["id"])
                html_bytes = html_exam.encode("utf-8")
                
                b_html, b_pdf, b_del = st.columns(3)
                with b_html:
                    st.download_button(
                        label="📥 تحميل .html",
                        data=html_bytes,
                        file_name=f"exam_template_{t['id']}.html",
                        mime="text/html",
                        key=f"dl_html_{t['id']}"
                    )
                with b_pdf:
                    if st.button(f"🖨️ طباعة .pdf", key=f"print_pdf_{t['id']}", use_container_width=True):
                        components.html(f"""
                        <script>
                            var win = window.open('', '_blank');
                            win.document.write(`{html_exam}`);
                            win.document.close();
                            win.focus();
                            setTimeout(function(){{ win.print(); }}, 500);
                        </script>
                        """, height=0)
                with b_del:
                    if st.session_state.role == "admin":
                        if st.button(f"🗑️ حذف القالب", key=f"del_tpl_{t['id']}", use_container_width=True):
                            with db() as c:
                                c.execute("DELETE FROM exam_templates WHERE id=?", (t["id"],))
                            st.success(f"🗑 تم حذف القالب ({t['name']}) بنجاح.")
                            st.rerun()

    with selected_tabs[5]:
        st.subheader("📊 التقارير المتقدمة والتصدير (يومي، أسبوعي، شهري، سنوي)")
        
        c_p1, c_p2 = st.columns(2)
        period_type = c_p1.selectbox("اختر الفترة الزمنية للتقرير", ["الكل", "يومي", "أسبوعي", "شهري", "كل 3 أشهر", "نصف سنوي", "سنوي", "فترة مخصصة"])
        
        start_filter = None
        end_filter = datetime.now()
        
        if period_type == "يومي":
            start_filter = datetime.now() - timedelta(days=1)
        elif period_type == "أسبوعي":
            start_filter = datetime.now() - timedelta(weeks=1)
        elif period_type == "شهري":
            start_filter = datetime.now() - timedelta(days=30)
        elif period_type == "كل 3 أشهر":
            start_filter = datetime.now() - timedelta(days=90)
        elif period_type == "نصف سنوي":
            start_filter = datetime.now() - timedelta(days=180)
        elif period_type == "سنوي":
            start_filter = datetime.now() - timedelta(days=365)
        elif period_type == "فترة مخصصة":
            d_start = c_p2.date_input("من تاريخ", date.today() - timedelta(days=30))
            d_end = c_p2.date_input("إلى تاريخ", date.today())
            start_filter = datetime.combine(d_start, datetime.min.time())
            end_filter = datetime.combine(d_end, datetime.max.time())

        with db() as c:
            query = """SELECT s.id, s.submitted_at, t.name trainee_name, t.facility, et.name template_name, et.exam_type, s.score, s.max_score, s.percent, s.passed, s.certificate_id 
                       FROM exam_sessions s 
                       JOIN trainees t ON t.id=s.trainee_id 
                       JOIN exam_templates et ON et.id=s.template_id 
                       WHERE s.status='submitted'"""
            params = []
            if start_filter and period_type != "الكل":
                query += " AND s.submitted_at >= ?"
                params.append(start_filter.isoformat())
                query += " AND s.submitted_at <= ?"
                params.append(end_filter.isoformat())
            query += " ORDER BY s.id DESC"
            df_res = pd.read_sql_query(query, c, params=params)

        if not df_res.empty:
            st.write(f"عدد النتائج ضمن الفترة المحددة: **{len(df_res)}**")
            st.dataframe(df_res, use_container_width=True, hide_index=True)
            
            xbuf = io.BytesIO()
            with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
                df_res.to_excel(writer, index=False, sheet_name="Exam_Reports")
            st.download_button("📥 تصدير تقارير التقييمات Excel", xbuf.getvalue(), file_name=f"evaluation_report_{period_type}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            st.markdown("---")
            st.subheader("📥 تحميل أو طباعة الشهادة")
            sid_p = st.selectbox("اختر جلسة الاختبار لخيارات الشهادة", df_res.id.tolist())
            if sid_p:
                cert_html = generate_compact_certificate_html(int(sid_p))
                cert_bytes = cert_html.encode("utf-8")
                b_ch, b_cp = st.columns(2)
                with b_ch:
                    st.download_button(
                        label="📥 تحميل .html",
                        data=cert_bytes,
                        file_name=f"certificate_{sid_p}.html",
                        mime="text/html",
                        key=f"dl_cert_html_{sid_p}"
                    )
                with b_cp:
                    if st.button(f"🖨️ طباعة .pdf", key=f"print_cert_pdf_{sid_p}", use_container_width=True):
                        components.html(f"""
                        <script>
                            var win = window.open('', '_blank');
                            win.document.write(`{cert_html}`);
                            win.document.close();
                            win.focus();
                            setTimeout(function(){{ win.print(); }}, 500);
                        </script>
                        """, height=0)
        else:
            st.info("لا توجد تقييمات مسجلة خلال الفترة الزمنية المحددة.")

    with selected_tabs[6]:
        st.subheader("💾 النسخ الاحتياطي للقاعدة")
        if st.button("إنشاء نسخة احتياطية الآن"):
            path = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            src = sqlite3.connect(DB_PATH)
            dst = sqlite3.connect(path)
            try: src.backup(dst)
            finally: dst.close(); src.close()
            st.success("✅ تم إنشاء النسخة الاحتياطية بنجاح.")

    if st.session_state.role == "admin":
        with selected_tabs[7]:
            st.subheader("👥 إدارة المستخدمين")
            with db() as c:
                users_list = c.execute("SELECT id, username, role, active, created_at FROM users").fetchall()
            st.dataframe(pd.DataFrame([dict(u) for u in users_list]), use_container_width=True, hide_index=True)
        with selected_tabs[8]:
            st.subheader("🧾 سجل التدقيق والعمليات")
            with db() as c:
                df_audit = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 300", c)
            st.dataframe(df_audit, use_container_width=True, hide_index=True)

def trainee_portal():
    with db() as c:
        tr = c.execute("SELECT * FROM trainees WHERE id=?", (st.session_state.trainee_id,)).fetchone()
    if not tr:
        st.session_state.trainee_id = None
        st.rerun()
        
    header()
    st.markdown(f'<div class="card"><h3>مرحباً بك، {esc(tr["name"])}</h3><p>الجهة: {esc(tr["facility"])} | رقم التسجيل (ID): <b>{tr["id"]}</b></p></div>', unsafe_allow_html=True)
    
    with db() as c:
        ts = c.execute("SELECT * FROM exam_templates WHERE active=1").fetchall()
    
    with st.form("start_exam_form"):
        tid = st.selectbox("اختر قالب الاختبار المخصص", [t["id"] for t in ts], format_func=lambda x: next(f"{t['name']} ({t['exam_type']})" for t in ts if t["id"] == x))
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

def exam_interface(session_id):
    with db() as c:
        session = c.execute("SELECT * FROM exam_sessions WHERE id=?", (session_id,)).fetchone()
        rows = c.execute("""SELECT eq.*, q.question, q.options_json FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=? ORDER BY eq.position""", (session_id,)).fetchall()
        
    expires_str = session["expires_at"]
    
    # مؤقت تنازلي (ساعات ودقائق وثوانٍ) متزامن وثابت أعلى الصفحة باستخدام JavaScript
    timer_html = f"""
    <div class="sticky-timer-container">
        <div class="timer-box" id="exam-timer-display">⏱️ جاري مزامنة الوقت وتحديث العد التنازلي...</div>
    </div>
    <script>
    (function() {{
        const expiresTime = new Date("{expires_str}").getTime();
        
        function updateTimer() {{
            const now = new Date().getTime();
            const distance = expiresTime - now;
            
            const timerEl = document.getElementById("exam-timer-display");
            if (!timerEl) return;
            
            if (distance <= 0) {{
                timerEl.innerHTML = "⏰ انتهى وقت الاختبار!";
                window.location.reload();
                return;
            }}
            
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            const hStr = String(hours).padStart(2, '0');
            const mStr = String(minutes).padStart(2, '0');
            const sStr = String(seconds).padStart(2, '0');
            
            timerEl.innerHTML = "⏱️ الوقت المتبقي للاختبار: " + hStr + " ساعة : " + mStr + " دقيقة : " + sStr + " ثانية";
        }}
        
        updateTimer();
        setInterval(updateTimer, 1000);
    }})();
    </script>
    """
    components.html(timer_html, height=75)
    
    answered = 0
    for row in rows:
        opts = json.loads(row["options_json"])
        order = json.loads(row["option_order_json"])
        disp_opts = [opts[i] for i in order]
        
        curr_idx = None
        if row["selected_option"] is not None:
            try: curr_idx = disp_opts.index(opts[row["selected_option"]])
            except: pass
            
        q_raw = row["question"]
        if q_raw.startswith("IMAGE:"):
            parts = q_raw.split("\n\n", 1)
            img_data = parts[0].replace("IMAGE:", "").strip()
            actual_q = parts[1] if len(parts) > 1 else "تعرف على الصورة المجهرية وحدد الإجابة الصحيحة:"
            st.markdown(f"""
            <div class="question">
                <div class="q-img-layout">
                    <div class="q-text-side"><b>س ({row["position"]+1}):</b> {esc(actual_q)}</div>
                    <div class="q-img-side"><img src="{img_data}" alt="عينة مجهرية"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            cleaned_q = clean_question_text(q_raw)
            st.markdown(f'<div class="question" style="padding:10px 14px; margin-bottom:10px;"><b>س ({row["position"]+1})</b>: {cleaned_q}</div>', unsafe_allow_html=True)

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
        st.rerun()

# ============================================================
# 6) موجه المسارات الرئيسي
# ============================================================
if st.session_state.get("exam_session_id"):
    exam_interface(st.session_state.exam_session_id)
elif st.session_state.trainee_id and not st.session_state.logged_in:
    if st.session_state.get("last_result_id"):
        sid = st.session_state.last_result_id
        header()
        st.success("تم تسليم الاختبار بنجاح!")
        cert_html = generate_compact_certificate_html(sid)
        cert_bytes = cert_html.encode("utf-8")
        
        bc_h, bc_p = st.columns(2)
        with bc_h:
            st.download_button(
                label="📥 تحميل .html",
                data=cert_bytes,
                file_name=f"certificate_{sid}.html",
                mime="text/html"
            )
        with bc_p:
            if st.button(f"🖨️ طباعة .pdf", key=f"print_res_{sid}", use_container_width=True):
                components.html(f"""
                <script>
                    var win = window.open('', '_blank');
                    win.document.write(`{cert_html}`);
                    win.document.close();
                    win.focus();
                    setTimeout(function(){{ win.print(); }}, 500);
                </script>
                """, height=0)
            
        if st.button("العودة للرئيسية"):
            st.session_state.trainee_id = None
            st.session_state.last_result_id = None
            st.session_state.exam_session_id = None
            st.rerun()
    else:
        trainee_portal()
elif not st.session_state.logged_in:
    login_portal()
else:
    admin_dashboard()
