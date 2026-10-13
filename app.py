import os, io, re, ast, json, sqlite3, hashlib, secrets, random, time, html, urllib.request, socket
from datetime import datetime, timedelta, date, time as datetime_time
from zoneinfo import ZoneInfo
from contextlib import contextmanager
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import qrcode
from PIL import Image




st.set_page_config(
    page_title="نظام تقييم واختبار العاملين بالأمراض المتوطنة 🪱🔬🐌💊 - System V1.0",
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

DEFAULT_LOGO = ""




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




st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: 'Cairo', 'Tahoma', sans-serif !important;
    font-size: 16px;
    color-scheme: light !important;
    -webkit-user-select: none !important;
    -moz-user-select: none !important;
    -ms-user-select: none !important;
    user-select: none !important;
    -webkit-touch-callout: none !important;
}
/* خلفية سماوية صافية وسحب بيضاء ناعمة قريبة من التصميم المرجعي */
.stApp {
    position: relative !important; isolation: isolate !important; min-height: 100vh !important;
    background-color: #72c9f4 !important;
    background-image:
      radial-gradient(ellipse 22% 12% at 4% 9%, rgba(255,255,255,.98) 0%, rgba(255,255,255,.70) 35%, transparent 72%),
      radial-gradient(ellipse 28% 13% at 95% 15%, rgba(255,255,255,.95) 0%, rgba(255,255,255,.56) 38%, transparent 74%),
      radial-gradient(ellipse 30% 15% at 6% 50%, rgba(255,255,255,.78) 0%, rgba(255,255,255,.32) 38%, transparent 74%),
      radial-gradient(ellipse 26% 13% at 100% 68%, rgba(255,255,255,.84) 0%, rgba(255,255,255,.35) 40%, transparent 74%),
      radial-gradient(ellipse 35% 17% at 50% 100%, rgba(255,255,255,.78) 0%, rgba(255,255,255,.25) 45%, transparent 75%),
      linear-gradient(180deg, #48b5ef 0%, #8ed8fa 47%, #b7e9ff 100%) !important;
    background-attachment: fixed !important; background-size: cover !important;
}
.stApp::before {
    content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
    background:
      radial-gradient(ellipse 18% 5% at 0% 22%, rgba(255,255,255,.85) 0%, transparent 75%),
      radial-gradient(ellipse 24% 7% at 100% 37%, rgba(255,255,255,.7) 0%, transparent 75%),
      radial-gradient(ellipse 23% 7% at 0% 79%, rgba(255,255,255,.7) 0%, transparent 75%);
    filter: blur(12px); opacity: .9;
}
.stApp::after { content: none !important; }
@media (max-width: 768px) { .stApp { background-attachment: scroll !important; } }
.stApp, .stApp p, .stApp label, .stApp [data-testid="stMarkdownContainer"] {
    font-size: 16px;
}
/* توحيد الخط العريض في جميع عناصر واجهة البرنامج مع الحفاظ على التصميم الأزرق */
.stApp,
.stApp p,
.stApp span,
.stApp label,
.stApp div,
.stApp li,
.stApp td,
.stApp th,
.stApp summary,
.stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stCaptionContainer"],
.stApp [data-testid="stAlert"],
.stApp input,
.stApp textarea,
.stApp select,
.stApp [role="combobox"],
.stApp button,
.stApp [data-baseweb="tag"],
.stApp [data-testid="stDataFrame"] {
    font-weight: 700 !important;
}
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp strong, .stApp b,
.stApp .stButton > button,
.stApp [data-testid="stFormSubmitButton"] > button {
    font-weight: 800 !important;
}
.stApp h1 { font-size: 1.8rem !important; }
.stApp h2 { font-size: 1.55rem !important; }
.stApp h3 { font-size: 1.3rem !important; }
.stApp input, .stApp textarea, .stApp select, .stApp button {
    font-size: 15px !important;
}
.block-container {
    max-width: 1000px !important;
    margin: auto !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-top: 1.6rem !important;
    padding-bottom: 7rem !important;
}
.card, .question, [data-testid="stForm"], [data-testid="stVerticalBlock"] > div {
    box-sizing: border-box !important;
}
.card, .question {
    background: #ffffff !important;
    color: #111827 !important;
    padding: 18px 24px;
    border-radius: 10px;
    margin-bottom: 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    border-right: 6px solid #3d9eaf !important;
    width: 100% !important;
}
.metric {
    background: #ffffff !important;
    padding: 16px;
    border-radius: 10px;
    text-align: center;
    border-top: 4px solid #3d9eaf !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.metric .v {
    font-size: 24px;
    font-weight: 800;
    color: #347f91 !important;
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
    background: linear-gradient(112deg, #087eae 0%, #079fd0 46%, #087fb2 100%) !important;
    color: #ffffff !important; border-radius: 22px !important;
    font-weight: 800 !important; min-height: 58px !important; padding: 10px 18px !important;
    border: 1.5px solid rgba(190,250,255,.98) !important; width: 100% !important;
    box-shadow: inset 0 2px 5px rgba(255,255,255,.62), inset 0 -5px 12px rgba(0,48,112,.22), 0 3px 8px rgba(0,96,150,.18) !important;
    transition: transform .18s ease, filter .18s ease;
}
.stButton>button:hover { filter: brightness(1.08) saturate(1.05); transform: translateY(-1px); color:#fff !important; }
.stButton>button:active { transform: translateY(1px); }

/* توحيد الأيقونات والتركيز مع لوحة الأزرق والنيلي */
    .stApp [data-testid="stMarkdownContainer"] svg,
    .stApp [data-testid="stWidgetLabel"] svg,
    .stApp [data-testid="stExpander"] svg,
    .stApp [data-testid="stSelectbox"] svg,
    .stApp [data-testid="stMultiSelect"] svg { color: #0a5b80 !important; fill: #0a5b80 !important; opacity: .82; }
    .stApp button:focus-visible, .stApp input:focus, .stApp textarea:focus, .stApp select:focus {
        outline: 2px solid #54b9bd !important;
        outline-offset: 2px !important;
        border-color: #54b9bd !important;
        box-shadow: 0 0 0 3px rgba(84,185,189,.24) !important;
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
    background: linear-gradient(112deg, #087eae 0%, #079fd0 46%, #087fb2 100%);
    color: #ffffff;
    text-align: center;
    padding: 8px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
    z-index: 99999;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    border: 1px solid #a9f4ff; border-top: 2px solid #bdfaff; border-radius: 16px 16px 0 0;
}
</style>
<script>
document.addEventListener("contextmenu", function(e) {
    e.preventDefault();
});
document.addEventListener("copy", function(e) {
    e.preventDefault();
    alert("⚠ عذراً، نسخ النصوص محظور حفاظاً على سرية الأسئلة والبيانات!");
});
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
function concealSensitiveView() {
    if (document.body) document.body.style.filter = "blur(14px)";
}
function revealSensitiveView() {
    if (document.body) document.body.style.filter = "none";
}
window.addEventListener("blur", concealSensitiveView);
window.addEventListener("focus", revealSensitiveView);
document.addEventListener("visibilitychange", function() {
    if (document.hidden) concealSensitiveView(); else revealSensitiveView();
});
window.addEventListener("pagehide", concealSensitiveView);
</script>
""", unsafe_allow_html=True)

st.markdown("""
<div class="ownership-watermark">
    جميع الحقوق محفوظة © 2026 | تصميم وتطوير: Dr/Ahmed.S.Hegazy
</div>
""", unsafe_allow_html=True)




def esc(x):
    return html.escape("" if x is None else str(x))

def clean_question_text(q_text):
    if q_text is None:
        return ""
    cleaned = str(q_text).strip()
    patterns = [
        r"\(\s*نموذج\s*[^)]*\)",
        r"\[\s*نموذج\s*[^]]*\]",
        r"\(\s*النموذج\s*[^)]*\)",
        r"\[\s*النموذج\s*[^]]*\]",
        r"\(\s*مجموعة\s*[^)]*\)",
        r"\[\s*مجموعة\s*[^]]*\]",
        r"\(\s*سؤال\s*[^)]*\)",
        r"\[\s*سؤال\s*[^]]*\]",
        r"\(\s*رقم\s*\d+\s*[^)]*\)",
        r"\[\s*رقم\s*\d+\s*[^]]*\]",
        r"\(\s*رقم[^)]*\)",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*(?:سؤال\s*(?:رقم|#)?\s*)?\d+\s*[\)\].:-]+\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\s+([،,:؛.)])", r"\1", cleaned)
    return cleaned.strip()

def normalize_text(x):
    x = "" if x is None else str(x)
    return re.sub(r"\s+", " ", x.strip()).lower()

_DIGIT_TRANSLATION = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_EGYPT_PHONE_RE = re.compile(r"^01[0125]\d{8}$")
_VALID_NID_GOV_CODES = {"01", "02", "03", "04", "11", "12", "13", "14", "15", "16", "17", "18", "19", "21", "22", "23", "24", "25", "26", "27", "28", "29", "31", "32", "33", "34", "35", "88"}

def normalize_digits(value):
    """Translate Arabic/Persian digits to ASCII and keep digits only."""
    return re.sub(r"\D", "", str(value or "").translate(_DIGIT_TRANSLATION))

def normalize_national_id(value):
    return normalize_digits(value)

def normalize_egyptian_phone(value):
    """Canonicalize common Egyptian mobile formats to 01xxxxxxxxx."""
    raw = str(value or "").translate(_DIGIT_TRANSLATION).strip()
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0020"):
        digits = digits[4:]
    elif digits.startswith("20") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("1"):
        digits = "0" + digits
    return digits

def is_valid_egyptian_mobile(value):
    return bool(_EGYPT_PHONE_RE.fullmatch(normalize_egyptian_phone(value)))

def is_valid_egyptian_national_id(value):
    nid = normalize_national_id(value)
    if len(nid) != 14 or nid[0] not in {"2", "3"}:
        return False
    try:
        century = 1900 if nid[0] == "2" else 2000
        year = century + int(nid[1:3])
        month = int(nid[3:5])
        day = int(nid[5:7])
        datetime(year, month, day)
    except (ValueError, OverflowError):
        return False
    return nid[7:9] in _VALID_NID_GOV_CODES and nid[9:].isdigit()

def trainee_matches_hierarchy(facility_value, hierarchy_row):
    """Match both legacy facility-only values and the full hierarchy string."""
    value = str(facility_value or "").strip()
    h = dict(hierarchy_row)
    if value == str(h.get("facility_name") or "").strip():
        return True
    new_path = " - ".join(str(h.get(k) or "").strip() for k in ("authority", "directorate_section", "administration", "administration_section", "facility_name") if str(h.get(k) or "").strip())
    legacy_path = " - ".join(str(h.get(k) or "").strip() for k in ("governorate", "authority", "directorate_section", "center", "administration", "administration_section", "facility_name") if str(h.get(k) or "").strip())
    return any(path and value.endswith(path) for path in (new_path, legacy_path))

def hierarchy_row_matches_scope(row, scope, allow_shared_section_rows=True):
    """Match a legacy hierarchy row using shared-section semantics consistently.

    A department is not duplicated for each directorate section, and a facility is
    not duplicated for each administration section. Thus blank section fields on a
    shared descendant are compatible with a selected section, while a row explicitly
    assigned to a different section is not.
    """
    try:
        data = dict(row)
    except Exception:
        data = row or {}
    scope = scope or {}
    if scope.get("_scope_denied") or any(str(v) == "__NO_ACCESS__" for v in scope.values()):
        return False
    if scope.get("scope_all") is True:
        return True
    mapping = (
        ("scope_governorate", "governorate"),
        ("scope_authority", "authority"),
        ("scope_center", "center"),
        ("scope_administration", "administration"),
        ("scope_facility", "facility_name"),
    )
    for scope_key, column in mapping:
        wanted = str(scope.get(scope_key) or "").strip()
        if wanted and str(data.get(column) or "").strip() != wanted:
            return False
    for scope_key, column in (("scope_directorate_section", "directorate_section"), ("scope_administration_section", "administration_section")):
        wanted = str(scope.get(scope_key) or "").strip()
        actual = str(data.get(column) or "").strip()
        if wanted and actual != wanted and not (allow_shared_section_rows and not actual):
            return False
    return True


def hierarchy_filter_for_trainees(scope, trainee_alias="t"):
    """SQL predicate for trainee records stored with a full administrative path."""
    keys = ("scope_governorate", "scope_authority", "scope_directorate_section", "scope_center", "scope_administration", "scope_administration_section", "scope_facility")
    if scope.get("_scope_denied"):
        return "0=1", []
    if scope.get("scope_all") is True or not any(str(scope.get(k) or "").strip() for k in keys):
        return "1=1", []
    scope_sql, args = hierarchy_scope_sql("h", scope)
    pred = (f"EXISTS (SELECT 1 FROM hierarchical_facilities h WHERE ({scope_sql}) AND "
            f"({trainee_alias}.facility=h.facility_name OR "
            f"{trainee_alias}.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR "
            f"{trainee_alias}.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || "
            f"h.center || ' - ' || h.administration || ' - ' || h.facility_name))")
    return pred, args

def reindex_hierarchical_facilities():
    """Compact hierarchy IDs safely without losing row identity during the two-phase update.

    In SQLite, an INTEGER PRIMARY KEY is an alias for rowid. Updating id therefore
    changes rowid too; the second phase must target the temporary ID, not the old rowid.
    Hierarchy references elsewhere in this app are stored as names/paths, not this ID.
    """
    with db() as c:
        existing = {row["name"] for row in c.execute("PRAGMA table_info(hierarchical_facilities)").fetchall()}
        migrations = {
            "governorate": "TEXT NOT NULL DEFAULT ''", "authority": "TEXT NOT NULL DEFAULT ''",
            "center": "TEXT NOT NULL DEFAULT ''", "administration": "TEXT NOT NULL DEFAULT ''",
            "facility_name": "TEXT NOT NULL DEFAULT ''", "created_at": "TEXT NOT NULL DEFAULT ''",
            "hidden": "INTEGER NOT NULL DEFAULT 0",
            "directorate_section": "TEXT NOT NULL DEFAULT ''",
            "administration_section": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in migrations.items():
            if column not in existing:
                c.execute(f"ALTER TABLE hierarchical_facilities ADD COLUMN {column} {definition}")
        existing = {row["name"] for row in c.execute("PRAGMA table_info(hierarchical_facilities)").fetchall()}
        if "id" not in existing:
            c.execute("ALTER TABLE hierarchical_facilities ADD COLUMN id INTEGER")
            c.execute("UPDATE hierarchical_facilities SET id=rowid WHERE id IS NULL")
        rows = c.execute("SELECT id AS old_id, rowid AS old_rowid FROM hierarchical_facilities ORDER BY id, rowid").fetchall()
        if not rows:
            try:
                c.execute("DELETE FROM sqlite_sequence WHERE name='hierarchical_facilities'")
            except sqlite3.OperationalError:
                pass
            return
        current_ids = [int(r["old_id"]) for r in rows if r["old_id"] is not None]
        temp_base = max([0] + [abs(v) for v in current_ids]) + len(rows) + 10000

        temporary_ids = []
        for idx, row in enumerate(rows, start=1):
            old_id = row["old_id"]
            temp_id = temp_base + idx
            if old_id is None:
                c.execute("UPDATE hierarchical_facilities SET id=? WHERE rowid=?", (temp_id, row["old_rowid"]))
            else:
                c.execute("UPDATE hierarchical_facilities SET id=? WHERE id=?", (temp_id, old_id))
            temporary_ids.append(temp_id)
        for new_id, temp_id in enumerate(temporary_ids, start=1):
            c.execute("UPDATE hierarchical_facilities SET id=? WHERE id=?", (new_id, temp_id))
        try:
            cur = c.execute("UPDATE sqlite_sequence SET seq=? WHERE name='hierarchical_facilities'", (len(rows),))
            if cur.rowcount == 0:
                c.execute("INSERT INTO sqlite_sequence(name, seq) VALUES('hierarchical_facilities', ?)", (len(rows),))
        except sqlite3.OperationalError:
            pass

def reindex_trainees():
    with db() as c:
        c.execute("PRAGMA foreign_keys=OFF;")
        rows = c.execute("SELECT id, facility, name, phone, national_id, profession, work_start_date, status, assigned_template_id, created_at, approved_at, updated_at, hidden FROM trainees ORDER BY id ASC").fetchall()
        c.execute("DELETE FROM trainees")
        c.execute("DELETE FROM sqlite_sequence WHERE name='trainees'")
        id_mapping = {}
        for new_id, r in enumerate(rows, start=1):
            old_id = r["id"]
            c.execute("INSERT INTO trainees(id, facility, name, phone, national_id, profession, work_start_date, status, assigned_template_id, created_at, approved_at, updated_at, hidden) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (new_id, r["facility"], r["name"], r["phone"], r["national_id"] if r["national_id"] is not None else "", r["profession"] if r["profession"] is not None else "", r["work_start_date"] if r["work_start_date"] is not None else "", r["status"], r["assigned_template_id"], r["created_at"], r["approved_at"], r["updated_at"], r["hidden"] if r["hidden"] is not None else 0))
            id_mapping[old_id] = new_id
        for old_id, new_id in id_mapping.items():
            c.execute("UPDATE exam_sessions SET trainee_id=? WHERE trainee_id=?", (new_id, old_id))
        c.execute("PRAGMA foreign_keys=ON;")

def reindex_questions():
    with db() as c:
        c.execute("PRAGMA foreign_keys=OFF;")
        rows = c.execute("SELECT id, difficulty, category, question, options_json, answer, explanation, reference, active, fingerprint, created_at FROM questions ORDER BY id ASC").fetchall()
        c.execute("DELETE FROM questions")
        c.execute("DELETE FROM sqlite_sequence WHERE name='questions'")
        q_mapping = {}
        for new_id, r in enumerate(rows, start=1):
            old_id = r["id"]
            c.execute("INSERT INTO questions(id, difficulty, category, question, options_json, answer, explanation, reference, active, fingerprint, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (new_id, r["difficulty"], r["category"], r["question"], r["options_json"], r["answer"], r["explanation"], r["reference"], r["active"], r["fingerprint"], r["created_at"]))
            q_mapping[old_id] = new_id
        for old_id, new_id in q_mapping.items():
            c.execute("UPDATE exam_questions SET question_id=? WHERE question_id=?", (new_id, old_id))
        c.execute("PRAGMA foreign_keys=ON;")

def reindex_templates():
    """Compact exam-template IDs from 1 while preserving every dependent reference.

    References are moved to temporary negative IDs first. This avoids collisions
    when an old ID becomes another template's new ID (for example 2 -> 1 and 5 -> 2).
    """
    with db() as c:
        c.execute("PRAGMA foreign_keys=OFF")
        rows = c.execute("SELECT id, name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, start_time, end_time, active, created_at, scope_governorate, scope_authority, scope_center, scope_administration, scope_facility, profession FROM exam_templates ORDER BY id ASC").fetchall()
        schedule_rows = [dict(r) for r in c.execute("SELECT * FROM exam_schedules ORDER BY id ASC").fetchall()] if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='exam_schedules'").fetchone() else []
        old_ids = [int(r['id']) for r in rows]
        t_mapping = {old_id: new_id for new_id, old_id in enumerate(old_ids, start=1)}


        for old_id in old_ids:
            temp_id = -old_id
            c.execute("UPDATE exam_sessions SET template_id=? WHERE template_id=?", (temp_id, old_id))
            c.execute("UPDATE trainees SET assigned_template_id=? WHERE assigned_template_id=?", (temp_id, old_id))
            try:
                c.execute("UPDATE action_plans SET template_id=? WHERE template_id=?", (temp_id, old_id))
            except sqlite3.OperationalError:
                pass

        c.execute("DELETE FROM exam_templates")
        c.execute("DELETE FROM sqlite_sequence WHERE name='exam_templates'")
        for new_id, r in enumerate(rows, start=1):
            c.execute("""INSERT INTO exam_templates(id, name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, start_time, end_time, active, created_at, scope_governorate, scope_authority, scope_center, scope_administration, scope_facility, profession)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (new_id, r["name"], r["exam_type"], r["num_questions"], r["duration_minutes"], r["pass_percent"], r["categories_json"], r["start_time"], r["end_time"], r["active"], r["created_at"], r["scope_governorate"] or "", r["scope_authority"] or "", r["scope_center"] or "", r["scope_administration"] or "", r["scope_facility"] or "", r["profession"] or ""))

        for old_id, new_id in t_mapping.items():
            temp_id = -old_id
            c.execute("UPDATE exam_sessions SET template_id=? WHERE template_id=?", (new_id, temp_id))
            c.execute("UPDATE trainees SET assigned_template_id=? WHERE assigned_template_id=?", (new_id, temp_id))
            try:
                c.execute("UPDATE action_plans SET template_id=? WHERE template_id=?", (new_id, temp_id))
            except sqlite3.OperationalError:
                pass


        if schedule_rows:
            c.execute("DELETE FROM exam_schedules")
            for sched in schedule_rows:
                mapped_template_id = t_mapping.get(int(sched["template_id"]))
                if mapped_template_id:
                    cols = {r[1] for r in c.execute("PRAGMA table_info(exam_schedules)").fetchall()}
                    if "stage" in cols:
                        c.execute("""INSERT INTO exam_schedules(id,template_id,scope_governorate,scope_authority,scope_center,scope_administration,scope_facility,start_time,end_time,profession,stage,active,created_at,updated_at)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (sched["id"], mapped_template_id, sched["scope_governorate"], sched["scope_authority"], sched["scope_center"], sched["scope_administration"], sched["scope_facility"], sched["start_time"], sched["end_time"], sched["profession"], sched.get("stage", ""), sched["active"], sched["created_at"], sched["updated_at"]))
                    else:
                        c.execute("""INSERT INTO exam_schedules(id,template_id,scope_governorate,scope_authority,scope_center,scope_administration,scope_facility,start_time,end_time,profession,active,created_at,updated_at)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (sched["id"], mapped_template_id, sched["scope_governorate"], sched["scope_authority"], sched["scope_center"], sched["scope_administration"], sched["scope_facility"], sched["start_time"], sched["end_time"], sched["profession"], sched["active"], sched["created_at"], sched["updated_at"]))

        c.execute("UPDATE sqlite_sequence SET seq=? WHERE name='exam_templates'", (len(rows),))
        if rows and c.execute("SELECT changes()").fetchone()[0] == 0:
            c.execute("INSERT INTO sqlite_sequence(name,seq) VALUES('exam_templates',?)", (len(rows),))
        c.execute("PRAGMA foreign_keys=ON")

def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210000)
    return salt.hex() + "$" + digest.hex()

def verify_password(password, stored):
    """Verify current PBKDF2 hashes and safely support legacy plaintext records for migration."""
    if not isinstance(stored, str):
        return False
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210000)
        return secrets.compare_digest(digest.hex(), digest_hex)
    except Exception:


        return secrets.compare_digest(str(password), stored)

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
    "👥 إدارة المهن والوظائف": "تقسيم وإدارة المهن والوظائف بالأمراض المتوطنة",
    "⚙ إدارة الأسئلة": "إدارة الأسئلة الفردية وبنوك الأقسام الإدارية",
    "🧑‍🔬 المتدربين والنماذج": "اعتماد المتدربين والنماذج وطباعة النتائج",
    "📚 قاعدة بيانات المتدربين": "عرض وتعديل وطباعة وتصدير جميع بيانات المتدربين",
    "🧪 إنشاء و تعديل و حذف النماذج": "إنشاء وتعديل وحذف نماذج الاختبارات",
    "✍ التسجيل اليدوي للاختبارات و التقييم الواقعي": "التسجيل اليدوي للاختبارات و التقييم الواقعي للمنشآت",
    "🖨 ضبط اعدادات الطباعة و الهوامش": "إعدادات هوامش وترويسات التقارير العامة",
    "🎨 إعدادات الشهادات المخصصة": "صفحة مخصصة لضبط الشهادات بالكامل وطباعتها",
    "📊 التقارير": "التقارير وتحليل الأداء للأمراض المتوطنة",
    "📈 خطط العمل": "خطط العمل التدريبية للأمراض المتوطنة",
    "💾 النسخ الاحتياطي": "النسخ الاحتياطي لقاعدة البيانات",
    "👥 إدارة المستخدمين": "إدارة المستخدمين والصلاحيات",
    "🧾 سجل التدقيق": "سجل التدقيق والأحداث"
}

def get_role_labels():
    """Return built-in and user-managed permission labels without changing role keys."""
    labels = dict(ROLES)
    try:
        with db() as c:
            rows = c.execute("SELECT role_key, role_label FROM role_labels").fetchall()
        for row in rows:
            if row["role_key"] and row["role_label"]:
                labels[str(row["role_key"])] = str(row["role_label"])
    except Exception:
        pass
    return labels

def role_label(role_key):
    return get_role_labels().get(str(role_key or ""), str(role_key or "غير محدد"))

def init_db():
    with db() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                job_title TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                permissions_json TEXT NOT NULL DEFAULT '[]',
                hierarchy_scope_json TEXT NOT NULL DEFAULT '{}',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT
            );
            CREATE TABLE IF NOT EXISTS role_labels (
                role_key TEXT PRIMARY KEY,
                role_label TEXT NOT NULL
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
            -- Normalized hierarchy tables: each level owns an independent ID sequence.
            CREATE TABLE IF NOT EXISTS directorates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                hidden INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                directorate_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                hidden INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT '',
                UNIQUE(directorate_id, name),
                FOREIGN KEY(directorate_id) REFERENCES directorates(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS facilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                hidden INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT '',
                UNIQUE(department_id, name),
                FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_departments_directorate_id ON departments(directorate_id);
            CREATE INDEX IF NOT EXISTS idx_facilities_department_id ON facilities(department_id);
            CREATE TABLE IF NOT EXISTS directorate_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                directorate_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                hidden INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT '',
                UNIQUE(directorate_id, name),
                FOREIGN KEY(directorate_id) REFERENCES directorates(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS administration_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                hidden INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT '',
                UNIQUE(department_id, name),
                FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_directorate_sections_parent ON directorate_sections(directorate_id);
            CREATE INDEX IF NOT EXISTS idx_administration_sections_parent ON administration_sections(department_id);
            -- Explicit many-to-many visibility relationships: every administration under a
            -- directorate is visible through every section of that directorate; likewise,
            -- every facility under an administration is visible through every section of it.
            CREATE TABLE IF NOT EXISTS department_directorate_sections (
                department_id INTEGER NOT NULL,
                directorate_section_id INTEGER NOT NULL,
                PRIMARY KEY(department_id, directorate_section_id),
                FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE CASCADE,
                FOREIGN KEY(directorate_section_id) REFERENCES directorate_sections(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS facility_administration_sections (
                facility_id INTEGER NOT NULL,
                administration_section_id INTEGER NOT NULL,
                PRIMARY KEY(facility_id, administration_section_id),
                FOREIGN KEY(facility_id) REFERENCES facilities(id) ON DELETE CASCADE,
                FOREIGN KEY(administration_section_id) REFERENCES administration_sections(id) ON DELETE CASCADE
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
                created_at TEXT NOT NULL,
                scope_governorate TEXT NOT NULL DEFAULT '',
                scope_authority TEXT NOT NULL DEFAULT '',
                scope_center TEXT NOT NULL DEFAULT '',
                scope_administration TEXT NOT NULL DEFAULT '',
                scope_facility TEXT NOT NULL DEFAULT '',
                scope_directorate_section TEXT NOT NULL DEFAULT '',
                scope_administration_section TEXT NOT NULL DEFAULT '',
                profession TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS exam_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                scope_governorate TEXT NOT NULL DEFAULT '',
                scope_authority TEXT NOT NULL DEFAULT '',
                scope_center TEXT NOT NULL DEFAULT '',
                scope_administration TEXT NOT NULL DEFAULT '',
                scope_facility TEXT NOT NULL DEFAULT '',
                scope_directorate_section TEXT NOT NULL DEFAULT '',
                scope_administration_section TEXT NOT NULL DEFAULT '',
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                profession TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(template_id) REFERENCES exam_templates(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_exam_schedules_template ON exam_schedules(template_id, active);
            CREATE TABLE IF NOT EXISTS trainees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                facility TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                national_id TEXT NOT NULL DEFAULT '',
                profession TEXT NOT NULL DEFAULT 'أخصائي الأمراض المتوطنة',
                work_start_date TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                assigned_template_id INTEGER,
                created_at TEXT NOT NULL,
                approved_at TEXT,
                updated_at TEXT NOT NULL,
                hidden INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(assigned_template_id) REFERENCES exam_templates(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS functional_staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                profession TEXT NOT NULL DEFAULT '',
                facility TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_functional_staff_facility_profession
                ON functional_staff(facility, profession, active);
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
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trainee_id INTEGER NOT NULL,
                template_id INTEGER,
                started_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                submitted_at TEXT,
                review_expires_at TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                exam_stage TEXT NOT NULL DEFAULT '',
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
            CREATE TABLE IF NOT EXISTS facility_certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                certificate_code TEXT NOT NULL UNIQUE,
                facility_name TEXT NOT NULL,
                session_ids_json TEXT NOT NULL DEFAULT '[]',
                average_percent REAL NOT NULL DEFAULT 0,
                issued_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS action_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                target_name TEXT NOT NULL,
                weakness_areas TEXT NOT NULL,
                action_steps TEXT NOT NULL,
                time_frame_type TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                created_at TEXT NOT NULL,
                scope_governorate TEXT NOT NULL DEFAULT '',
                scope_authority TEXT NOT NULL DEFAULT '',
                scope_center TEXT NOT NULL DEFAULT '',
                scope_administration TEXT NOT NULL DEFAULT '',
                scope_facility TEXT NOT NULL DEFAULT '',
                scope_directorate_section TEXT NOT NULL DEFAULT '',
                scope_administration_section TEXT NOT NULL DEFAULT '',
                template_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS facility_real_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visit_date TEXT NOT NULL,
                governorate TEXT NOT NULL DEFAULT '',
                authority TEXT NOT NULL DEFAULT '',
                administration TEXT NOT NULL DEFAULT '',
                facility TEXT NOT NULL DEFAULT '',
                profession TEXT NOT NULL DEFAULT '',
                responsible_person TEXT NOT NULL DEFAULT '',
                items_json TEXT NOT NULL DEFAULT '{}',
                notes TEXT NOT NULL DEFAULT '',
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
                default_cert_title TEXT NOT NULL DEFAULT 'شهادة',
                default_cert_notes TEXT NOT NULL DEFAULT 'تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد',
                trainee_prefix TEXT NOT NULL DEFAULT '',
                trainee_title TEXT NOT NULL DEFAULT '',
                trainee_profession TEXT NOT NULL DEFAULT '',
                professions_list_json TEXT NOT NULL DEFAULT '[]',
                cert_box_inset TEXT NOT NULL DEFAULT '13mm',
                cert_hierarchy_json TEXT NOT NULL DEFAULT '{}',
                report_hierarchy_json TEXT NOT NULL DEFAULT '{}',
                paper_print_settings_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT,
                action TEXT NOT NULL,
                entity TEXT,
                details TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS training_minutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER UNIQUE,
                minutes_text TEXT NOT NULL,
                training_items TEXT NOT NULL DEFAULT '',
                training_goals TEXT NOT NULL DEFAULT '',
                training_date TEXT NOT NULL DEFAULT '',
                facility_name TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
        """)

        print_cols = {row[1] for row in c.execute("PRAGMA table_info(print_settings)").fetchall()}
        if "cert_hierarchy_json" not in print_cols:
            c.execute("ALTER TABLE print_settings ADD COLUMN cert_hierarchy_json TEXT NOT NULL DEFAULT '{}'")
        if "report_hierarchy_json" not in print_cols:
            c.execute("ALTER TABLE print_settings ADD COLUMN report_hierarchy_json TEXT NOT NULL DEFAULT '{}'")



        facility_cert_cols = {row[1] for row in c.execute("PRAGMA table_info(facility_certificates)").fetchall()}
        if "verification_status" not in facility_cert_cols:
            c.execute("ALTER TABLE facility_certificates ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'valid'")
        if "verification_notes" not in facility_cert_cols:
            c.execute("ALTER TABLE facility_certificates ADD COLUMN verification_notes TEXT NOT NULL DEFAULT ''")
        c.execute("CREATE INDEX IF NOT EXISTS idx_facility_certificates_code ON facility_certificates(certificate_code)")
        c.execute("CREATE TABLE IF NOT EXISTS app_schema_migrations (migration_key TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        c.execute("""CREATE TABLE IF NOT EXISTS hierarchy_print_logos (
            scope_key TEXT PRIMARY KEY, scope_json TEXT NOT NULL DEFAULT '{}',
            logo1_base64 TEXT NOT NULL DEFAULT '', logo2_base64 TEXT NOT NULL DEFAULT '',
            logo3_base64 TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT ''
        )""")
        c.execute("INSERT OR IGNORE INTO app_schema_migrations(migration_key, applied_at) VALUES(?,?)", ("secure_certificate_verification_v2", now()))

    for col_table, col_name, col_type in [
        ("questions", "scope_type", "TEXT NOT NULL DEFAULT 'global'"),
        ("questions", "scope_id", "INTEGER"),
        ("trainees", "hidden", "INTEGER NOT NULL DEFAULT 0"),
        ("trainees", "profession", "TEXT NOT NULL DEFAULT 'أخصائي الأمراض المتوطنة'"),
        ("trainees", "work_start_date", "TEXT NOT NULL DEFAULT ''"),
        ("trainees", "phone", "TEXT NOT NULL DEFAULT ''"),
        ("trainees", "national_id", "TEXT NOT NULL DEFAULT ''"),
        ("hierarchical_facilities", "hidden", "INTEGER NOT NULL DEFAULT 0"),
        ("hierarchical_facilities", "directorate_section", "TEXT NOT NULL DEFAULT ''"),
        ("hierarchical_facilities", "administration_section", "TEXT NOT NULL DEFAULT ''"),
        ("users", "permissions_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("users", "hierarchy_scope_json", "TEXT NOT NULL DEFAULT '{}'"),
        ("exam_templates", "exam_type", "TEXT NOT NULL DEFAULT 'قبل التدريب'"),
        ("exam_templates", "start_time", "TEXT"),
        ("exam_templates", "end_time", "TEXT"),
        ("exam_templates", "scope_governorate", "TEXT NOT NULL DEFAULT ''"),
        ("exam_templates", "scope_authority", "TEXT NOT NULL DEFAULT ''"),
        ("exam_templates", "scope_center", "TEXT NOT NULL DEFAULT ''"),
        ("exam_templates", "scope_administration", "TEXT NOT NULL DEFAULT ''"),
        ("exam_templates", "scope_facility", "TEXT NOT NULL DEFAULT ''"),
        ("exam_templates", "scope_directorate_section", "TEXT NOT NULL DEFAULT ''"),
        ("exam_templates", "scope_administration_section", "TEXT NOT NULL DEFAULT ''"),
        ("exam_templates", "profession", "TEXT NOT NULL DEFAULT ''"),
        ("exam_sessions", "exam_stage", "TEXT NOT NULL DEFAULT ''"),
        ("exam_schedules", "stage", "TEXT NOT NULL DEFAULT ''"),
        ("exam_schedules", "scope_directorate_section", "TEXT NOT NULL DEFAULT ''"),
        ("exam_schedules", "scope_administration_section", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "scope_governorate", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "scope_authority", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "scope_center", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "scope_administration", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "scope_facility", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "scope_directorate_section", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "scope_administration_section", "TEXT NOT NULL DEFAULT ''"),
        ("action_plans", "template_id", "INTEGER"),
        ("action_plans", "start_date", "TEXT"),
        ("action_plans", "end_date", "TEXT"),
        ("exam_sessions", "review_expires_at", "TEXT"),
        ("print_settings", "line_spacing", "REAL NOT NULL DEFAULT 1.25"),
        ("print_settings", "logo2_base64", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "logo3_base64", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "bg_base64", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "frame_base64", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "default_cert_title", "TEXT NOT NULL DEFAULT 'شهادة'"),
        ("print_settings", "default_cert_notes", "TEXT NOT NULL DEFAULT 'تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد'"),
        ("print_settings", "trainee_prefix", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "trainee_title", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "trainee_profession", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "professions_list_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("print_settings", "cert_box_inset", "TEXT NOT NULL DEFAULT '13mm'"),
        ("print_settings", "cert_trainee_extra", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "cert_facility_extra", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "cert_facility_section", "TEXT NOT NULL DEFAULT ''"),
        ("print_settings", "paper_print_settings_json", "TEXT NOT NULL DEFAULT '{}'"),
        ("training_minutes", "training_items", "TEXT NOT NULL DEFAULT ''"),
        ("training_minutes", "training_goals", "TEXT NOT NULL DEFAULT ''"),
        ("training_minutes", "training_date", "TEXT NOT NULL DEFAULT ''"),
        ("training_minutes", "facility_name", "TEXT NOT NULL DEFAULT ''")
    ]:
        try:
            with db() as c:
                c.execute(f"ALTER TABLE {col_table} ADD COLUMN {col_name} {col_type}")
        except:
            pass


    with db() as c:
        c.execute("CREATE INDEX IF NOT EXISTS idx_questions_scope ON questions(scope_type, scope_id, active)")

    with db() as c:
        legacy_rows = c.execute("SELECT * FROM exam_templates WHERE COALESCE(start_time,'')<>'' AND COALESCE(end_time,'')<>''").fetchall()
        for row in legacy_rows:
            scope = tuple((row[k] or "") for k in ("scope_governorate", "scope_authority", "scope_center", "scope_administration", "scope_facility"))
            exists = c.execute("SELECT id FROM exam_schedules WHERE template_id=? AND scope_governorate=? AND scope_authority=? AND scope_center=? AND scope_administration=? AND scope_facility=? LIMIT 1", (row["id"], *scope)).fetchone()
            if not exists:
                c.execute("INSERT INTO exam_schedules(template_id,scope_governorate,scope_authority,scope_center,scope_administration,scope_facility,start_time,end_time,profession,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,1,?,?)", (row["id"], *scope, row["start_time"], row["end_time"], row["profession"] or "", now(), now()))

        c.execute("UPDATE exam_templates SET start_time=NULL, end_time=NULL")

    with db() as c:
        c.execute("UPDATE exam_templates SET scope_governorate='', scope_authority='', scope_center='', scope_administration='', scope_facility='' WHERE COALESCE(scope_governorate,'')<>'' OR COALESCE(scope_authority,'')<>'' OR COALESCE(scope_center,'')<>'' OR COALESCE(scope_administration,'')<>'' OR COALESCE(scope_facility,'')<>''")
        c.execute("UPDATE action_plans SET scope_governorate='', scope_center='' WHERE COALESCE(scope_governorate,'')<>'' OR COALESCE(scope_center,'')<>''")



    with db() as c:
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_trainees_unique_phone_insert
            BEFORE INSERT ON trainees
            WHEN TRIM(COALESCE(NEW.phone,'')) <> '' AND EXISTS (SELECT 1 FROM trainees WHERE TRIM(phone)=TRIM(NEW.phone))
            BEGIN SELECT RAISE(ABORT, 'DUPLICATE_TRAINEE_PHONE'); END;
        """)
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_trainees_unique_phone_update
            BEFORE UPDATE OF phone ON trainees
            WHEN TRIM(COALESCE(NEW.phone,'')) <> '' AND EXISTS (SELECT 1 FROM trainees WHERE TRIM(phone)=TRIM(NEW.phone) AND id<>NEW.id)
            BEGIN SELECT RAISE(ABORT, 'DUPLICATE_TRAINEE_PHONE'); END;
        """)
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_trainees_unique_national_id_insert
            BEFORE INSERT ON trainees
            WHEN TRIM(COALESCE(NEW.national_id,'')) <> '' AND EXISTS (SELECT 1 FROM trainees WHERE TRIM(national_id)=TRIM(NEW.national_id))
            BEGIN SELECT RAISE(ABORT, 'DUPLICATE_TRAINEE_NATIONAL_ID'); END;
        """)
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_trainees_unique_national_id_update
            BEFORE UPDATE OF national_id ON trainees
            WHEN TRIM(COALESCE(NEW.national_id,'')) <> '' AND EXISTS (SELECT 1 FROM trainees WHERE TRIM(national_id)=TRIM(NEW.national_id) AND id<>NEW.id)
            BEGIN SELECT RAISE(ABORT, 'DUPLICATE_TRAINEE_NATIONAL_ID'); END;
        """)

    with db() as c:
        cnt = c.execute("SELECT COUNT(*) FROM print_settings").fetchone()[0]
        if cnt == 0:
            default_header = "جمهورية مصر العربية<br>وزارة الصحة والسكان<br>مديرية الشئون الصحية بالشرقية<br>الإدارة الصحية بأولاد صقر"
            default_professions = [
                "أخصائي الأمراض المتوطنة",
                "طبيب بيطري",
                "أخصائي ميكروبيولوجي",
                "فني صحي متوطنة",
                "فني تمريض",
                "مسؤول وحدة متوطنة",
                "مراقب صحي",
                "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"
            ]
            c.execute("""INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, line_spacing, logo_base64, logo2_base64, logo3_base64, bg_base64, frame_base64, default_cert_title, default_cert_notes, trainee_prefix, trainee_title, trainee_profession, professions_list_json, cert_box_inset) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (default_header, "12mm", "auto", "8mm", "8mm", 1.10, DEFAULT_LOGO, "", "", "", "", "شهادة", "تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد", "", "دكتور", "أخصائي الأمراض المتوطنة", json.dumps(default_professions, ensure_ascii=False), "13mm"))


        user_columns = {row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()}
        if "display_name" not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN display_name TEXT NOT NULL DEFAULT ''")
        if "job_title" not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN job_title TEXT NOT NULL DEFAULT ''")
        c.execute("UPDATE users SET display_name=username WHERE display_name IS NULL OR TRIM(display_name)=''")


        c.execute("UPDATE users SET hierarchy_scope_json=? WHERE hierarchy_scope_json IS NULL OR TRIM(hierarchy_scope_json)='' OR hierarchy_scope_json='{}'", (json.dumps({"scope_all": True}),))

        cnt_tpl = c.execute("SELECT COUNT(*) FROM exam_templates").fetchone()[0]
        if cnt_tpl == 0:
            default_start = now_cairo().isoformat(timespec="seconds")
            default_end = (now_cairo() + timedelta(days=365)).isoformat(timespec="seconds")
            c.execute("""INSERT INTO exam_templates(name, exam_type, num_questions, duration_minutes, pass_percent, categories_json, start_time, end_time, active, created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                      ("النموذج التقييمي العام للاستجابة والتدريب للأمراض المتوطنة", "قبل التدريب", 999999, 60, 60.0, '[]', default_start, default_end, 1, now()))

init_db()


reindex_hierarchical_facilities()

def sync_normalized_hierarchy():
    """Synchronize normalized hierarchy tables from legacy path rows without inventing parent links.

    Each row in hierarchical_facilities represents one valid path. Repeated administration
    or facility names across rows intentionally encode multiple parent-section relationships.
    """
    with db() as c:
        c.execute("PRAGMA foreign_keys=ON")
        rows = c.execute(
            "SELECT authority, directorate_section, administration, administration_section, "
            "facility_name, hidden, created_at FROM hierarchical_facilities ORDER BY id"
        ).fetchall()

        # Rebuild in dependency order. Explicit links are restored from each path row only.
        for table_name in ("department_directorate_sections", "facility_administration_sections",
                           "facilities", "administration_sections", "departments",
                           "directorate_sections", "directorates"):
            c.execute(f"DELETE FROM {table_name}")
        for table_name in ("facilities", "administration_sections", "departments", "directorate_sections", "directorates"):
            c.execute("DELETE FROM sqlite_sequence WHERE name=?", (table_name,))

        for r in rows:
            directorate = str(r["authority"] or "").strip()
            section = str(r["directorate_section"] or "").strip()
            admin = str(r["administration"] or "").strip()
            admin_section = str(r["administration_section"] or "").strip()
            facility = str(r["facility_name"] or "").strip()
            hidden, created_at = int(r["hidden"] or 0), str(r["created_at"] or "")
            if not directorate:
                continue
            c.execute("INSERT OR IGNORE INTO directorates(name, hidden, created_at) VALUES(?,?,?)",
                      (directorate, hidden, created_at))
            did = c.execute("SELECT id FROM directorates WHERE name=?", (directorate,)).fetchone()[0]
            c.execute("UPDATE directorates SET hidden=MIN(hidden, ?) WHERE id=?", (hidden, did))

            dsid = None
            if section:
                c.execute("INSERT OR IGNORE INTO directorate_sections(directorate_id,name,hidden,created_at) VALUES(?,?,?,?)",
                          (did, section, hidden, created_at))
                dsid = c.execute("SELECT id FROM directorate_sections WHERE directorate_id=? AND name=?",
                                 (did, section)).fetchone()[0]
                c.execute("UPDATE directorate_sections SET hidden=MIN(hidden, ?) WHERE id=?", (hidden, dsid))

            depid = None
            if admin:
                c.execute("INSERT OR IGNORE INTO departments(directorate_id,name,hidden,created_at) VALUES(?,?,?,?)",
                          (did, admin, hidden, created_at))
                depid = c.execute("SELECT id FROM departments WHERE directorate_id=? AND name=?",
                                  (did, admin)).fetchone()[0]
                c.execute("UPDATE departments SET hidden=MIN(hidden, ?) WHERE id=?", (hidden, depid))
                if dsid is not None:
                    c.execute("INSERT OR IGNORE INTO department_directorate_sections(department_id,directorate_section_id) VALUES(?,?)",
                              (depid, dsid))

            asid = None
            if admin and admin_section and depid is not None:
                c.execute("INSERT OR IGNORE INTO administration_sections(department_id,name,hidden,created_at) VALUES(?,?,?,?)",
                          (depid, admin_section, hidden, created_at))
                asid = c.execute("SELECT id FROM administration_sections WHERE department_id=? AND name=?",
                                 (depid, admin_section)).fetchone()[0]
                c.execute("UPDATE administration_sections SET hidden=MIN(hidden, ?) WHERE id=?", (hidden, asid))

            if admin and facility and depid is not None:
                c.execute("INSERT OR IGNORE INTO facilities(department_id,name,hidden,created_at) VALUES(?,?,?,?)",
                          (depid, facility, hidden, created_at))
                fid = c.execute("SELECT id FROM facilities WHERE department_id=? AND name=?",
                                (depid, facility)).fetchone()[0]
                c.execute("UPDATE facilities SET hidden=MIN(hidden, ?) WHERE id=?", (hidden, fid))
                if asid is not None:
                    c.execute("INSERT OR IGNORE INTO facility_administration_sections(facility_id,administration_section_id) VALUES(?,?)",
                              (fid, asid))

        fk_errors = c.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise sqlite3.IntegrityError(
                f"Normalized hierarchy foreign-key validation failed: {len(fk_errors)} issue(s)"
            )

sync_normalized_hierarchy()

def default_paper_print_settings():
    """Independent, safe print profiles for each document family."""
    return {
        "reports": {"paper": "A4", "orientation": "landscape", "top": 28, "right": 8, "bottom": 18, "left": 8, "font_size": 9, "line_spacing": 1.15},
        "action_plans": {"paper": "A4", "orientation": "landscape", "top": 28, "right": 8, "bottom": 18, "left": 8, "font_size": 9, "line_spacing": 1.15},
        "training_minutes": {"paper": "A4", "orientation": "landscape", "top": 28, "right": 8, "bottom": 18, "left": 8, "font_size": 9, "line_spacing": 1.15},
        "exam_templates": {"paper": "A4", "orientation": "portrait", "top": 12, "right": 8, "bottom": 16, "left": 8, "font_size": 9, "line_spacing": 1.1},
        "answer_sheets": {"paper": "A4", "orientation": "landscape", "top": 12, "right": 8, "bottom": 16, "left": 8, "font_size": 10, "line_spacing": 1.2},
        "trainee_database": {"paper": "A4", "orientation": "landscape", "top": 12, "right": 8, "bottom": 16, "left": 8, "font_size": 8, "line_spacing": 1.1},
    }


def normalized_paper_print_settings(raw=None):
    defaults = default_paper_print_settings()
    try:
        supplied = json.loads(raw or "{}") if isinstance(raw, str) else (raw or {})
    except Exception:
        supplied = {}
    if not isinstance(supplied, dict):
        supplied = {}
    for key, base in defaults.items():
        value = supplied.get(key, {})
        if not isinstance(value, dict):
            value = {}
        merged = dict(base)
        merged.update({k: value[k] for k in base if k in value})
        merged["paper"] = merged["paper"] if merged["paper"] in ("A4", "A3", "Letter") else base["paper"]
        merged["orientation"] = merged["orientation"] if merged["orientation"] in ("portrait", "landscape") else base["orientation"]
        for k, low, high in (("top", 0, 50), ("right", 0, 30), ("bottom", 0, 50), ("left", 0, 30), ("font_size", 6, 18), ("line_spacing", 0.8, 3.0)):
            try:
                merged[k] = min(high, max(low, float(merged[k])))
            except Exception:
                merged[k] = base[k]
        # Respect the user's selected margins for every document profile.
        defaults[key] = merged
    return defaults


def get_print_settings():
    with db() as c:
        row = c.execute("SELECT * FROM print_settings ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            res = dict(row)
            try:
                res["professions_list"] = json.loads(res.get("professions_list_json", "[]"))
            except:
                res["professions_list"] = ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"]
            if "line_spacing" not in res or res["line_spacing"] is None:
                res["line_spacing"] = 1.10
            res["paper_print_settings"] = normalized_paper_print_settings(res.get("paper_print_settings_json", "{}"))
            return res
    return {
        "header_text": "جمهورية مصر العربية<br>وزارة الصحة والسكان<br>مديرية الشئون الصحية بالشرقية<br>الإدارة الصحية بأولاد صقر",
        "margin_top": "12mm",
        "margin_bottom": "auto",
        "margin_right": "8mm",
        "margin_left": "8mm",
        "line_spacing": 1.10,
        "paper_print_settings": default_paper_print_settings(),
        "logo_base64": DEFAULT_LOGO,
        "logo2_base64": "",
        "logo3_base64": "",
        "bg_base64": "",
        "frame_base64": "",
        "default_cert_title": "شهادة",
        "default_cert_notes": "تقرير أداء الأمراض المتوطنة والإشراف الفني المعتمد",
        "trainee_prefix": "",
        "trainee_title": "دكتور",
        "trainee_profession": "أخصائي الأمراض المتوطنة",
        "professions_list": ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"]
    }

def save_print_settings(h_text, m_top, m_bot, m_right, m_left, line_spacing, logo_data, logo2_data, logo3_data, bg_data, frame_data, def_title, def_notes, trainee_prefix, trainee_title, trainee_profession, professions_list, cert_box_inset="13mm", cert_trainee_extra=None, cert_facility_extra=None, cert_facility_section=None, cert_hierarchy=None, report_hierarchy=None, paper_print_settings=None):
    with db() as c:
        old_settings = c.execute("SELECT * FROM print_settings ORDER BY id DESC LIMIT 1").fetchone()
        old_cert = old_settings
        if cert_trainee_extra is None:
            cert_trainee_extra = old_cert["cert_trainee_extra"] if old_cert and "cert_trainee_extra" in old_cert.keys() else ""
        if cert_facility_extra is None:
            cert_facility_extra = old_cert["cert_facility_extra"] if old_cert and "cert_facility_extra" in old_cert.keys() else ""
        if cert_facility_section is None:
            cert_facility_section = old_cert["cert_facility_section"] if old_cert and "cert_facility_section" in old_cert.keys() else ""
        if cert_hierarchy is None:
            old_hierarchy = c.execute("SELECT cert_hierarchy_json FROM print_settings ORDER BY id DESC LIMIT 1").fetchone()
            cert_hierarchy = old_hierarchy["cert_hierarchy_json"] if old_hierarchy and "cert_hierarchy_json" in old_hierarchy.keys() else "{}"
        elif not isinstance(cert_hierarchy, str):
            cert_hierarchy = json.dumps(cert_hierarchy, ensure_ascii=False)
        if report_hierarchy is None:
            old_report_hierarchy = c.execute("SELECT report_hierarchy_json FROM print_settings ORDER BY id DESC LIMIT 1").fetchone()
            report_hierarchy = old_report_hierarchy["report_hierarchy_json"] if old_report_hierarchy and "report_hierarchy_json" in old_report_hierarchy.keys() else "{}"
        elif not isinstance(report_hierarchy, str):
            report_hierarchy = json.dumps(report_hierarchy, ensure_ascii=False)
        if paper_print_settings is None:
            old_paper_json = old_settings["paper_print_settings_json"] if old_settings and "paper_print_settings_json" in old_settings.keys() else "{}"
            paper_print_settings = normalized_paper_print_settings(old_paper_json)
        else:
            paper_print_settings = normalized_paper_print_settings(paper_print_settings)
        paper_json = json.dumps(paper_print_settings, ensure_ascii=False)
        c.execute("DELETE FROM print_settings")
        c.execute("INSERT INTO print_settings(header_text, margin_top, margin_bottom, margin_right, margin_left, line_spacing, logo_base64, logo2_base64, logo3_base64, bg_base64, frame_base64, default_cert_title, default_cert_notes, trainee_prefix, trainee_title, trainee_profession, professions_list_json, cert_box_inset, cert_hierarchy_json, report_hierarchy_json, paper_print_settings_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (h_text, m_top, "auto", m_right, m_left, float(line_spacing), logo_data, logo2_data, logo3_data, bg_data, frame_data, def_title, def_notes, trainee_prefix, trainee_title, trainee_profession, json.dumps(professions_list, ensure_ascii=False), cert_box_inset, cert_hierarchy or "{}", report_hierarchy or "{}", paper_json))
        c.execute("UPDATE print_settings SET cert_trainee_extra=?, cert_facility_extra=?, cert_facility_section=? WHERE id=(SELECT MAX(id) FROM print_settings)", (cert_trainee_extra or "", cert_facility_extra or "", cert_facility_section or ""))

def hierarchy_ordered_unique(values):
    """Return unique non-empty hierarchy names in the same order as their source rows.

    get_hierarchical_data() reads rows by their stable insertion ID, so this preserves
    the upload order across every dropdown instead of alphabetically sorting names.
    """
    result = []
    seen = set()
    for value in values:
        name = str(value or "").strip()
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return result

def hierarchy_level_codes(rows):
    """Build independent display codes for each hierarchy level, scoped to its parent.

    Returns five maps: directorates, directorate sections, administrations, administration
    sections, and facilities. These are display codes only; actual database primary keys remain
    the relationship keys and must not be rewritten to match display numbering.
    """
    clean = []
    for row in rows:
        clean.append({k: str(row.get(k) or "").strip() for k in (
            "authority", "directorate_section", "administration", "administration_section", "facility_name")})
    authorities = hierarchy_ordered_unique(r["authority"] for r in clean)
    auth_codes = {name: i for i, name in enumerate(authorities, 1)}
    directorate_section_codes = {}
    admin_codes = {}
    administration_section_codes = {}
    facility_codes = {}
    for authority in authorities:
        sections = hierarchy_ordered_unique(r["directorate_section"] for r in clean if r["authority"] == authority)
        for code, section in enumerate(sections, 1):
            directorate_section_codes[(authority, section)] = code
        admins = hierarchy_ordered_unique(r["administration"] for r in clean if r["authority"] == authority)
        for code, admin in enumerate(admins, 1):
            admin_codes[(authority, admin)] = code
            admin_rows = [r for r in clean if r["authority"] == authority and r["administration"] == admin]
            admin_sections = hierarchy_ordered_unique(r["administration_section"] for r in admin_rows)
            for section_code, section in enumerate(admin_sections, 1):
                administration_section_codes[(authority, admin, section)] = section_code
            facilities = hierarchy_ordered_unique(r["facility_name"] for r in admin_rows)
            for facility_code, facility in enumerate(facilities, 1):
                facility_codes[(authority, admin, facility)] = facility_code
    return auth_codes, directorate_section_codes, admin_codes, administration_section_codes, facility_codes

def get_hierarchical_data(include_hidden=False):
    """Return only hierarchy nodes within the logged-in user's assigned scope."""
    with db() as c:
        q = "SELECT * FROM hierarchical_facilities"
        if not include_hidden:
            q += " WHERE hidden = 0"
        q += " ORDER BY id ASC"
        rows = [dict(r) for r in c.execute(q).fetchall()]
    if not rows:
        return []

    if st.session_state.get("logged_in") and not is_owner():
        scope = st.session_state.get("user_hierarchy_scope") or {}
        if scope.get("scope_all") is True:
            return rows
        keys = ("scope_governorate", "scope_authority", "scope_directorate_section", "scope_center", "scope_administration", "scope_administration_section", "scope_facility")
        if not any(str(scope.get(k) or "").strip() for k in keys):
            return []
        if any(str(scope.get(k) or "").strip() for k in keys):


            mapping = (("scope_governorate", "governorate"), ("scope_authority", "authority"), ("scope_center", "center"), ("scope_administration", "administration"), ("scope_facility", "facility_name"))
            rows = [r for r in rows if all(not str(scope.get(sk) or "").strip() or str(r.get(col) or "").strip() == str(scope.get(sk) or "").strip() for sk, col in mapping)]
            directorate_section = str(scope.get("scope_directorate_section") or "").strip()
            if directorate_section:
                rows = [r for r in rows if str(r.get("directorate_section") or "").strip() == directorate_section]
            administration_section = str(scope.get("scope_administration_section") or "").strip()
            if administration_section:
                rows = [r for r in rows if str(r.get("administration_section") or "").strip() == administration_section]
    return rows

def current_user_trainee_scope():
    """Return the authenticated user's enforced hierarchy scope. Empty scope is fail-closed unless explicitly marked all."""
    if not st.session_state.get("logged_in") or is_owner():
        return {}
    scope = st.session_state.get("user_hierarchy_scope") or {}
    if scope.get("scope_all") is True:
        return {"scope_all": True}
    keys = ("scope_governorate", "scope_authority", "scope_directorate_section", "scope_center", "scope_administration", "scope_administration_section", "scope_facility")
    vals = {k: str(scope.get(k) or "").strip() for k in keys}
    return vals if any(vals.values()) else {**vals, "_scope_denied": True}

def user_can_access_trainee_id(trainee_id, conn=None):
    """Server-side authorization check; unauthenticated access fails closed."""
    if not st.session_state.get("logged_in"):
        return False
    if is_owner():
        return True
    scope = current_user_trainee_scope()
    if scope.get("scope_all") is True:
        return True
    pred, args = hierarchy_filter_for_trainees(scope, "t")
    own_conn = conn is None
    if own_conn:
        ctx = db()
        conn = ctx.__enter__()
    try:
        row = conn.execute(f"SELECT 1 FROM trainees t WHERE t.id=? AND {pred} LIMIT 1", (int(trainee_id), *args)).fetchone()
        return row is not None
    finally:
        if own_conn:
            ctx.__exit__(None, None, None)

def enforce_trainee_scope_or_raise(trainee_id, conn=None):
    if not user_can_access_trainee_id(trainee_id, conn):
        raise PermissionError("خارج نطاق الهيكل الإداري المخصص لهذا المستخدم")

def enforce_session_access_or_raise(session_id, conn=None):
    """Authorize a session by admin hierarchy scope or the public trainee's own identity."""
    own_conn = conn is None
    if own_conn:
        ctx = db()
        conn = ctx.__enter__()
    try:
        row = conn.execute("SELECT trainee_id FROM exam_sessions WHERE id=?", (int(session_id),)).fetchone()
        if not row:
            raise PermissionError("جلسة الاختبار غير موجودة أو غير متاحة.")
        trainee_id = int(row["trainee_id"])
        if st.session_state.get("logged_in"):
            if not is_owner():
                enforce_trainee_scope_or_raise(trainee_id, conn)
        else:

            current_tid = st.session_state.get("trainee_id")
            if not current_tid or int(current_tid) != trainee_id:
                raise PermissionError("لا يمكنك الوصول إلى جلسة اختبار تخص متدربًا آخر.")
        return True
    finally:
        if own_conn:
            ctx.__exit__(None, None, None)

def effective_hierarchy_scope(requested):
    assigned = current_user_trainee_scope()
    if assigned.get("scope_all") is True:
        return requested
    if assigned.get("_scope_denied"):
        return {"_scope_denied": True}

    out = dict(assigned)
    for key, value in (requested or {}).items():
        if value and not out.get(key):
            out[key] = value
        elif value and out.get(key) and str(value) != str(out[key]):

            out[key] = "__NO_ACCESS__"
    return out

def get_hierarchy_linked_projection_rows(include_hidden=False):
    """Build display-only hierarchy paths from the normalized many-to-many links.

    The legacy table stores sections and shared descendants as separate rows. This
    projection repeats a node only in the returned display paths (never in storage),
    so every administration appears beneath each directorate section and every
    facility beneath each administration section.
    """
    with db() as c:
        hidden_clause = "" if include_hidden else "WHERE hidden=0"
        raw = [dict(r) for r in c.execute(f"SELECT * FROM hierarchical_facilities {hidden_clause} ORDER BY id").fetchall()]
        directorates = [dict(r) for r in c.execute("SELECT * FROM directorates WHERE (?=1 OR hidden=0) ORDER BY id", (1 if include_hidden else 0,)).fetchall()]
        dir_sections = [dict(r) for r in c.execute("SELECT * FROM directorate_sections WHERE (?=1 OR hidden=0) ORDER BY id", (1 if include_hidden else 0,)).fetchall()]
        departments = [dict(r) for r in c.execute("SELECT * FROM departments WHERE (?=1 OR hidden=0) ORDER BY id", (1 if include_hidden else 0,)).fetchall()]
        admin_sections = [dict(r) for r in c.execute("SELECT * FROM administration_sections WHERE (?=1 OR hidden=0) ORDER BY id", (1 if include_hidden else 0,)).fetchall()]
        facilities = [dict(r) for r in c.execute("SELECT * FROM facilities WHERE (?=1 OR hidden=0) ORDER BY id", (1 if include_hidden else 0,)).fetchall()]
        dept_links = c.execute("SELECT department_id,directorate_section_id FROM department_directorate_sections").fetchall()
        facility_links = c.execute("SELECT facility_id,administration_section_id FROM facility_administration_sections").fetchall()


    assigned = {}
    if st.session_state.get("logged_in") and not is_owner():
        assigned = st.session_state.get("user_hierarchy_scope") or {}
        if assigned.get("scope_all") is not True:
            if not any(str(assigned.get(k) or "").strip() for k in ("scope_authority","scope_directorate_section","scope_administration","scope_administration_section","scope_facility","scope_governorate","scope_center")):
                return []
            def parent_ok(authority, admin="", facility=""):
                for key, val in (("scope_authority",authority),("scope_administration",admin),("scope_facility",facility)):
                    want=str(assigned.get(key) or "").strip()
                    if want and want != str(val or "").strip(): return False
                return True
            allowed_authorities={str(r.get("authority") or "").strip() for r in raw if parent_ok(r.get("authority"),r.get("administration"),r.get("facility_name"))}
            directorates=[d for d in directorates if d["name"] in allowed_authorities]

    wanted_ds = str(assigned.get("scope_directorate_section") or "").strip()
    wanted_admin = str(assigned.get("scope_administration") or "").strip()
    wanted_as = str(assigned.get("scope_administration_section") or "").strip()
    wanted_fac = str(assigned.get("scope_facility") or "").strip()
    if wanted_ds: dir_sections = [x for x in dir_sections if str(x.get("name") or "").strip() == wanted_ds]
    if wanted_admin: departments = [x for x in departments if str(x.get("name") or "").strip() == wanted_admin]
    if wanted_as: admin_sections = [x for x in admin_sections if str(x.get("name") or "").strip() == wanted_as]
    if wanted_fac: facilities = [x for x in facilities if str(x.get("name") or "").strip() == wanted_fac]
    sections_by_dir={d["id"]:[] for d in directorates}
    for x in dir_sections:
        if x["directorate_id"] in sections_by_dir: sections_by_dir[x["directorate_id"]].append(x)
    depts_by_dir={d["id"]:[] for d in directorates}
    for x in departments:
        if x["directorate_id"] in depts_by_dir: depts_by_dir[x["directorate_id"]].append(x)
    dept_section_ids={}
    for x in dept_links: dept_section_ids.setdefault(x["department_id"],set()).add(x["directorate_section_id"])
    admin_sections_by_dept={d["id"]:[] for d in departments}
    for x in admin_sections:
        if x["department_id"] in admin_sections_by_dept: admin_sections_by_dept[x["department_id"]].append(x)
    facility_section_ids={}
    for x in facility_links: facility_section_ids.setdefault(x["facility_id"],set()).add(x["administration_section_id"])
    facilities_by_dept={d["id"]:[] for d in departments}
    for x in facilities:
        if x["department_id"] in facilities_by_dept: facilities_by_dept[x["department_id"]].append(x)
    result=[]
    for d in directorates:
        auth=d["name"]
        if not any(str(r.get("authority") or "").strip()==auth for r in raw): continue
        base={"id":None,"governorate":"","authority":auth,"center":"","administration":"","facility_name":"","directorate_section":"","administration_section":"","hidden":d.get("hidden",0),"created_at":d.get("created_at","")}
        result.append(dict(base))
        # Strict chain: no administration is exposed unless linked to a real directorate
        # section, and no facility is exposed unless linked to a real administration section.
        # This prevents legacy/incomplete rows from bypassing required parent selection.
        sections = sections_by_dir.get(d["id"], [])
        for ds in sections:
            ds_name = ds["name"]
            section_row = dict(base)
            section_row.update(directorate_section=ds_name, id=f"ds:{ds['id']}", hidden=ds.get("hidden", 0))
            result.append(section_row)
            for dep in depts_by_dir.get(d["id"], []):
                if not parent_ok_for_projection(raw, auth, dep["name"]):
                    continue
                if ds["id"] not in dept_section_ids.get(dep["id"], set()):
                    continue
                admin_base = dict(base)
                admin_base.update(administration=dep["name"], directorate_section=ds_name,
                                  id=f"dep:{dep['id']}", hidden=dep.get("hidden", 0))
                result.append(admin_base)
                for asec in admin_sections_by_dept.get(dep["id"], []):
                    as_name = asec["name"]
                    as_row = dict(admin_base)
                    as_row.update(administration_section=as_name, id=f"as:{asec['id']}", hidden=asec.get("hidden", 0))
                    result.append(as_row)
                    for fac in facilities_by_dept.get(dep["id"], []):
                        if asec["id"] not in facility_section_ids.get(fac["id"], set()):
                            continue
                        fac_row = dict(as_row)
                        fac_row.update(facility_name=fac["name"], id=f"fac:{fac['id']}", hidden=fac.get("hidden", 0))
                        result.append(fac_row)

    # Deliberately do not append unlinked legacy rows here. They remain visible in the
    # hierarchy maintenance screen so an administrator can repair their missing parent links,
    # but are not selectable by downstream workflows until the chain is valid.
    return result

def parent_ok_for_projection(raw_rows, authority, administration):
    return any(str(r.get("authority") or "").strip()==str(authority or "").strip() and str(r.get("administration") or "").strip()==str(administration or "").strip() for r in raw_rows)

def hierarchy_scope_widget(label="الهيكل الإداري المستهدف:", key="hier_scope"):
    """Select a target through a validated, mandatory parent-to-child path."""
    rows = get_hierarchy_linked_projection_rows(include_hidden=False)
    scope = {"scope_governorate":"", "scope_authority":"", "scope_center":"", "scope_administration":"", "scope_facility":"", "scope_directorate_section":"", "scope_administration_section":""}
    levels = ["كل الهيكل الإداري", "المديرية / الجهة", "قسم داخل المديرية", "الإدارة", "قسم داخل الإدارة", "المنشأة"]
    selected_level = st.selectbox(label, levels, key=f"{key}_level")
    if selected_level == "كل الهيكل الإداري":
        scope = effective_hierarchy_scope(scope)
        st.session_state["_last_hierarchy_scope"] = dict(scope)
        return scope

    authority_values = hierarchy_ordered_unique(r.get("authority") for r in rows if r.get("authority"))
    if not authority_values:
        st.warning("لا توجد مسارات إدارية مكتملة للاختيار. راجع ربط الإدارات بأقسام المديرية والمنشآت بأقسام الإدارة من صفحة الهيكل الإداري.")
        denied = effective_hierarchy_scope({"_scope_denied": True})
        st.session_state["_last_hierarchy_scope"] = dict(denied)
        return denied
    authority = st.selectbox("المديرية / الجهة", authority_values, key=f"{key}_authority")
    scope["scope_authority"] = authority
    directorate_rows = [r for r in rows if str(r.get("authority") or "").strip() == authority]
    if selected_level == "المديرية / الجهة":
        scope = effective_hierarchy_scope(scope)
        st.session_state["_last_hierarchy_scope"] = dict(scope)
        return scope

    directorate_sections = hierarchy_ordered_unique(r.get("directorate_section") for r in directorate_rows if r.get("directorate_section"))
    if not directorate_sections:
        st.warning("لا توجد أقسام مديرية مرتبطة بهذه المديرية. أضف قسمًا واربط الإدارات التابعة به أولًا.")
        denied = effective_hierarchy_scope({"_scope_denied": True})
        st.session_state["_last_hierarchy_scope"] = dict(denied)
        return denied
    directorate_section = st.selectbox("قسم المديرية", directorate_sections, key=f"{key}_directorate_section")
    scope["scope_directorate_section"] = directorate_section
    section_rows = [r for r in directorate_rows if str(r.get("directorate_section") or "").strip() == directorate_section]
    if selected_level == "قسم داخل المديرية":
        scope = effective_hierarchy_scope(scope)
        st.session_state["_last_hierarchy_scope"] = dict(scope)
        return scope

    admin_values = hierarchy_ordered_unique(r.get("administration") for r in section_rows if r.get("administration"))
    if not admin_values:
        st.warning("لا توجد إدارات مرتبطة بقسم المديرية المختار.")
        denied = effective_hierarchy_scope({"_scope_denied": True})
        st.session_state["_last_hierarchy_scope"] = dict(denied)
        return denied
    administration = st.selectbox("الإدارة", admin_values, key=f"{key}_administration")
    scope["scope_administration"] = administration
    admin_rows = [r for r in section_rows if str(r.get("administration") or "").strip() == administration]
    if selected_level == "الإدارة":
        scope = effective_hierarchy_scope(scope)
        st.session_state["_last_hierarchy_scope"] = dict(scope)
        return scope

    admin_sections = hierarchy_ordered_unique(r.get("administration_section") for r in admin_rows if r.get("administration_section"))
    if not admin_sections:
        st.warning("لا توجد أقسام إدارة مرتبطة بالإدارة المختارة. أضف قسمًا واربط المنشآت التابعة به أولًا.")
        denied = effective_hierarchy_scope({"_scope_denied": True})
        st.session_state["_last_hierarchy_scope"] = dict(denied)
        return denied
    administration_section = st.selectbox("قسم الإدارة", admin_sections, key=f"{key}_administration_section")
    scope["scope_administration_section"] = administration_section
    admin_section_rows = [r for r in admin_rows if str(r.get("administration_section") or "").strip() == administration_section]
    if selected_level == "قسم داخل الإدارة":
        scope = effective_hierarchy_scope(scope)
        st.session_state["_last_hierarchy_scope"] = dict(scope)
        return scope

    facility_values = hierarchy_ordered_unique(r.get("facility_name") for r in admin_section_rows if r.get("facility_name"))
    if not facility_values:
        st.warning("لا توجد منشآت مرتبطة بقسم الإدارة المختار.")
        denied = effective_hierarchy_scope({"_scope_denied": True})
        st.session_state["_last_hierarchy_scope"] = dict(denied)
        return denied
    scope["scope_facility"] = st.selectbox("المنشأة / وحدة الأمراض المتوطنة", facility_values, key=f"{key}_facility")
    scope = effective_hierarchy_scope(scope)
    st.session_state["_last_hierarchy_scope"] = dict(scope)
    return scope

def hierarchy_scope_sql(alias, scope):
    if (scope or {}).get("_scope_denied") or any(str(v) == "__NO_ACCESS__" for v in (scope or {}).values()):
        return "0=1", []
    if (scope or {}).get("scope_all") is True:
        return "1=1", []
    conditions, args = [], []


    mapping = [("scope_governorate","governorate"),("scope_authority","authority"),("scope_center","center"),("scope_administration","administration"),("scope_facility","facility_name")]
    scoped = False
    for scope_key, col in mapping:
        val = str(scope.get(scope_key) or "").strip()
        if val:
            scoped = True
            conditions.append(f"{alias}.{col}=?")
            args.append(val)
    for scope_key, col in (("scope_directorate_section", "directorate_section"), ("scope_administration_section", "administration_section")):
        val = str(scope.get(scope_key) or "").strip()
        if val:
            scoped = True
            conditions.append(f"COALESCE({alias}.{col},'')=?")
            args.append(val)
    if scoped:
        conditions.insert(0, f"COALESCE({alias}.hidden,0)=0")
    return (" AND ".join(conditions) if conditions else "1=1"), args

def template_scope_text(row):
    parts = [row.get("scope_authority"), row.get("scope_directorate_section"), row.get("scope_administration"), row.get("scope_administration_section"), row.get("scope_facility")]
    parts = [str(x).strip() for x in parts if str(x or "").strip()]
    label = "كل الهيكل الإداري" if not parts else " ← ".join(parts)
    try:
        extra_scopes = get_template_scopes(row.get("id")) if row.get("id") else []
        if extra_scopes:
            label += f" (+{len(extra_scopes)} أماكن إضافية)"
    except Exception:
        pass
    return label

def _logo_scope_values(scope):
    scope = dict(scope or {})
    keys = ("scope_governorate", "scope_authority", "scope_center", "scope_directorate_section", "scope_administration", "scope_administration_section", "scope_facility")
    aliases = {"scope_governorate": ("scope_governorate", "governorate"), "scope_authority": ("scope_authority", "authority"), "scope_center": ("scope_center", "center"), "scope_directorate_section": ("scope_directorate_section", "directorate_section"), "scope_administration": ("scope_administration", "administration"), "scope_administration_section": ("scope_administration_section", "administration_section"), "scope_facility": ("scope_facility", "facility_name", "facility")}
    out = {}
    for k in keys:
        out[k] = next((str(scope.get(a) or "").strip() for a in aliases[k] if str(scope.get(a) or "").strip()), "")
    return out

def _logo_scope_key(scope):
    return json.dumps(_logo_scope_values(scope), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def get_hierarchy_print_logos(scope):
    """Return logos saved for the most specific matching administrative scope; no cross-scope mixing."""
    values = _logo_scope_values(scope)
    candidates = []
    # Exact scope first, then nearest explicitly configured parent, without mixing individual logo slots.
    active = [k for k, v in values.items() if v]
    for n in range(len(active), 0, -1):
        for subset in [active[:n]]:
            probe = {k: (values[k] if k in subset else "") for k in values}
            try:
                with get_conn() as conn:
                    row = conn.execute("SELECT logo1_base64,logo2_base64,logo3_base64 FROM hierarchy_print_logos WHERE scope_key=?", (_logo_scope_key(probe),)).fetchone()
                if row and any(row):
                    return [row[0] or "", row[1] or "", row[2] or ""]
            except Exception:
                pass
    sett = get_print_settings()
    return [sett.get("logo_base64", "") or "", sett.get("logo2_base64", "") or "", sett.get("logo3_base64", "") or ""]

def save_hierarchy_print_logos(scope, logos):
    values = _logo_scope_values(scope)
    if not any(values.values()):
        raise ValueError("اختر مستوى إداريًا محددًا قبل حفظ الشعارات.")
    with get_conn() as conn:
        conn.execute("""INSERT INTO hierarchy_print_logos(scope_key,scope_json,logo1_base64,logo2_base64,logo3_base64,updated_at)
            VALUES(?,?,?,?,?,?) ON CONFLICT(scope_key) DO UPDATE SET scope_json=excluded.scope_json,logo1_base64=excluded.logo1_base64,logo2_base64=excluded.logo2_base64,logo3_base64=excluded.logo3_base64,updated_at=excluded.updated_at""",
            (_logo_scope_key(values), json.dumps(values, ensure_ascii=False), *(logos + [""]*3)[:3], datetime.now(CAIRO_TZ).isoformat()))

def hierarchy_header_html(scope=None, facility_value=None):
    """Render the selected administrative hierarchy as a compact top-of-page print header."""
    scope = dict(scope or {})
    if facility_value and not any(str(scope.get(k) or "").strip() for k in ("scope_facility", "facility_name")):
        scope["scope_facility"] = facility_value
    fields = [
        (("scope_authority", "authority"), "المديرية / الهيئة"),
        (("scope_directorate_section", "directorate_section"), "القسم بالمديرية"),
        (("scope_administration", "administration"), "الإدارة"),
        (("scope_administration_section", "administration_section"), "القسم بالإدارة"),
        (("scope_facility", "facility_name", "facility"), "المنشأة"),
    ]
    levels = []
    for keys, label in fields:
        value = next((str(scope.get(k) or "").strip() for k in keys if str(scope.get(k) or "").strip()), "")
        if value and (not levels or levels[-1][1] != value):
            levels.append((label, value))
    if not levels:
        try:
            saved = get_print_settings().get("report_hierarchy_json", "{}")
            saved = json.loads(saved or "{}") if isinstance(saved, str) else (saved or {})
            if isinstance(saved, dict):
                for keys, label in fields:
                    value = next((str(saved.get(k) or "").strip() for k in keys if str(saved.get(k) or "").strip()), "")
                    if value and (not levels or levels[-1][1] != value):
                        levels.append((label, value))
        except Exception:
            pass
    hierarchy_html = "".join(
        f'<div class="print-hierarchy-line"><span class="print-hierarchy-label">{esc(label)}:</span> {esc(value)}</div>'
        for label, value in levels
    )
    target_html = (f'<div class="print-target-line">الجهة المستهدفة: {esc(levels[-1][1])}</div>' if levels else "")
    logos = get_hierarchy_print_logos(scope)
    logo_html = "".join(
        f'<img src="{logo}" alt="الشعار {i}" style="width:13mm;height:13mm;object-fit:contain;display:block;" />'
        for i, logo in enumerate(logos, 1) if logo
    )
    return (f'<div class="print-admin-header" dir="ltr"><div class="print-admin-logos">{logo_html}</div><div class="print-admin-hierarchy" dir="rtl">{hierarchy_html}{target_html}</div></div>' if (levels or logo_html) else "")

def hierarchy_margin_html(scope=None):
    """Compatibility alias for the administrative header in the top print area."""
    return hierarchy_header_html(scope)

def current_hierarchy_header():
    """Return the selected hierarchy header for the current printable document."""
    return hierarchy_header_html(st.session_state.get("_last_hierarchy_scope", {}))

def template_matches_scope(template_row, scope):
    """True when an exam template applies to at least one facility inside the chosen plan scope."""
    t = dict(template_row) if not isinstance(template_row, dict) else template_row
    t_scope = {"scope_authority": t.get("scope_authority") or "", "scope_administration": t.get("scope_administration") or "", "scope_facility": t.get("scope_facility") or ""}
    if not any(str(v).strip() for v in t_scope.values()):
        return True
    scope = dict(scope or {})
    rows = get_hierarchical_data(include_hidden=False)
    for item in rows:
        if scope.get("scope_authority") and item.get("authority") != scope.get("scope_authority"):
            continue
        if scope.get("scope_administration") and item.get("administration") != scope.get("scope_administration"):
            continue
        if scope.get("scope_facility") and item.get("facility_name") != scope.get("scope_facility"):
            continue
        if t_scope["scope_authority"] and item.get("authority") != t_scope["scope_authority"]:
            continue
        if t_scope["scope_administration"] and item.get("administration") != t_scope["scope_administration"]:
            continue
        if t_scope["scope_facility"] and item.get("facility_name") != t_scope["scope_facility"]:
            continue
        return True
    return False

def parse_professions(value):
    """Read legacy single-profession values or the newer JSON list of professions."""
    raw = str(value or "").strip()
    if not raw or normalize_text(raw) in {normalize_text("كل الوظائف"), normalize_text("جميع الوظائف")}:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    return [raw]

def professions_display(value):
    items = parse_professions(value)
    return "، ".join(items) if items else "كل الوظائف"

def template_matches_profession(template_row, trainee_profession):
    """Blank profession means all professions; JSON lists and legacy single values are supported."""
    t = dict(template_row) if not isinstance(template_row, dict) else template_row
    required = {normalize_text(x) for x in parse_professions(t.get("profession") or "")}
    actual = normalize_text(trainee_profession or "")
    return not required or actual in required

def get_schedule_for_trainee(trainee_id, template_id, exam_stage=None):
    """Return the most-specific active schedule for a trainee/template/stage pair."""
    with db() as c:
        trainee = c.execute("SELECT facility, profession FROM trainees WHERE id=? AND hidden=0", (int(trainee_id),)).fetchone()
        if not trainee:
            return None






        facility_candidates = c.execute(
            "SELECT * FROM hierarchical_facilities WHERE facility_name=? AND hidden=0 ORDER BY id DESC",
            (str(trainee["facility"] or "").strip(),),
        ).fetchall()
        if not facility_candidates:
            all_facilities = c.execute("SELECT * FROM hierarchical_facilities WHERE hidden=0 ORDER BY id DESC").fetchall()
            facility_candidates = [candidate for candidate in all_facilities if trainee_matches_hierarchy(trainee["facility"], candidate)]
        if not facility_candidates:
            return None
        rows = c.execute("SELECT * FROM exam_schedules WHERE template_id=? AND active=1 ORDER BY id DESC", (int(template_id),)).fetchall()
        keys = [("scope_governorate", "governorate"), ("scope_authority", "authority"), ("scope_directorate_section", "directorate_section"), ("scope_center", "center"), ("scope_administration", "administration"), ("scope_administration_section", "administration_section"), ("scope_facility", "facility_name")]
        matches = []
        wanted_stage = str(exam_stage or "").strip()
        for row in rows:
            d = dict(row)
            row_stage = str(d.get("stage") or "").strip()
            if wanted_stage and row_stage and row_stage != wanted_stage:
                continue
            required_professions = {normalize_text(x) for x in parse_professions(d.get("profession") or "")}
            if required_professions and normalize_text(trainee["profession"] or "") not in required_professions:
                continue
            schedule_scope = {sk: str(d.get(sk) or "").strip() for sk, _ in keys}
            if any(hierarchy_row_matches_scope(candidate, schedule_scope, allow_shared_section_rows=True) for candidate in facility_candidates):
                specificity = sum(bool((d.get(sk) or "").strip()) for sk, _ in keys)
                matches.append((specificity, d))
        return max(matches, key=lambda x: x[0])[1] if matches else None


def template_matches_facility(template_row, facility_name):
    """Check whether a template scope contains a facility, including shared-section descendants."""
    t = dict(template_row) if not isinstance(template_row, dict) else template_row
    scope = {
        "scope_authority": t.get("scope_authority") or "",
        "scope_directorate_section": t.get("scope_directorate_section") or "",
        "scope_administration": t.get("scope_administration") or "",
        "scope_administration_section": t.get("scope_administration_section") or "",
        "scope_facility": t.get("scope_facility") or "",
    }
    if not any(str(v or "").strip() for v in scope.values()):
        return True
    if scope["scope_facility"] and str(scope["scope_facility"]).strip() != str(facility_name or "").strip():
        return False
    with db() as c:
        candidates = c.execute(
            "SELECT * FROM hierarchical_facilities WHERE facility_name=? AND COALESCE(hidden,0)=0 ORDER BY id",
            (facility_name,),
        ).fetchall()
    return any(hierarchy_row_matches_scope(h, scope, allow_shared_section_rows=True) for h in candidates)


def ensure_admin():
    with db() as c:
        u = c.execute("SELECT * FROM users WHERE role='admin'").fetchone()
        all_modules = list(ALL_MENU_MODULES.keys())
        if not u:
            c.execute("INSERT OR REPLACE INTO users(username,password_hash,role,permissions_json,active,created_at) VALUES(?,?,?,?,?,?)",
                      ("admin", hash_password("admin"), "admin", json.dumps(all_modules, ensure_ascii=False), 1, now()))
        else:

            c.execute("UPDATE users SET permissions_json=?, active=1 WHERE role='admin'", (json.dumps(all_modules, ensure_ascii=False),))

ensure_admin()

def login_user(u, p):
    """Authenticate admin users without changing passwords or touching trainee data.

    Username matching is case-insensitive and ignores accidental spaces around the
    username; passwords remain exact and case-sensitive.
    """
    username = str(u or "").strip()
    password = str(p or "")
    st.session_state["admin_login_error"] = ""
    if not username or not password:
        st.session_state["admin_login_error"] = "أدخل اسم المستخدم وكلمة المرور أولاً."
        return None
    with db() as c:
        user = c.execute(
            "SELECT * FROM users WHERE lower(trim(username))=lower(?) LIMIT 1",
            (username,),
        ).fetchone()
        if not user:
            st.session_state["admin_login_error"] = "اسم المستخدم غير موجود في قاعدة البيانات الحالية. تأكد أنك تستخدم نسخة البرنامج وقاعدة البيانات الصحيحتين."
            return None
        if not int(user["active"] or 0):
            st.session_state["admin_login_error"] = "هذا الحساب موقوف. اطلب من مالك النظام تفعيله."
            return None
        if not verify_password(password, user["password_hash"]):
            st.session_state["admin_login_error"] = "اسم المستخدم موجود، لكن كلمة المرور لا تطابق كلمة المرور المحفوظة لهذا الحساب. لم يتم تغيير أي بيانات."
            return None

        if "$" not in str(user["password_hash"]):
            c.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(password), user["id"]))
        c.execute("UPDATE users SET last_login=? WHERE id=?", (now(), user["id"]))
        return dict(user)

def _find_duplicate_trainee_value(c, field, normalized_value, exclude_id=None):
    if field not in {"phone", "national_id"} or not normalized_value:
        return False
    rows = c.execute(f"SELECT id, {field} FROM trainees WHERE COALESCE({field},'')<>''").fetchall()
    normalizer = normalize_egyptian_phone if field == "phone" else normalize_national_id
    for row in rows:
        if exclude_id is not None and int(row["id"]) == int(exclude_id):
            continue
        if normalizer(row[field]) == normalized_value:
            return True
    return False

def create_trainee(facility, name, phone, national_id, profession, assigned_template_id=None, work_start_date=""):
    phone_norm = normalize_egyptian_phone(phone)
    nid_norm = normalize_national_id(national_id)
    if not is_valid_egyptian_mobile(phone_norm):
        raise ValueError("INVALID_TRAINEE_PHONE")
    if not is_valid_egyptian_national_id(nid_norm):
        raise ValueError("INVALID_TRAINEE_NATIONAL_ID")
    with db() as c:
        if _find_duplicate_trainee_value(c, "phone", phone_norm):
            raise ValueError("DUPLICATE_TRAINEE_PHONE")
        if _find_duplicate_trainee_value(c, "national_id", nid_norm):
            raise ValueError("DUPLICATE_TRAINEE_NATIONAL_ID")
        cur = c.execute("INSERT INTO trainees(facility,name,phone,national_id,profession,work_start_date,status,assigned_template_id,created_at,updated_at,hidden) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (facility.strip(), normalize_text(name), phone_norm, nid_norm, profession, str(work_start_date or ""), "pending", assigned_template_id, now(), now(), 0))
        return cur.lastrowid

def update_trainee_data(tid, facility, name, phone, national_id, profession, work_start_date=None):
    phone_norm = normalize_egyptian_phone(phone)
    nid_norm = normalize_national_id(national_id)
    if not is_valid_egyptian_mobile(phone_norm):
        raise ValueError("INVALID_TRAINEE_PHONE")
    if not is_valid_egyptian_national_id(nid_norm):
        raise ValueError("INVALID_TRAINEE_NATIONAL_ID")
    with db() as c:
        enforce_trainee_scope_or_raise(tid, c)
        if _find_duplicate_trainee_value(c, "phone", phone_norm, exclude_id=tid):
            raise ValueError("DUPLICATE_TRAINEE_PHONE")
        if _find_duplicate_trainee_value(c, "national_id", nid_norm, exclude_id=tid):
            raise ValueError("DUPLICATE_TRAINEE_NATIONAL_ID")
        if work_start_date is None:
            c.execute("UPDATE trainees SET facility=?, name=?, phone=?, national_id=?, profession=?, updated_at=? WHERE id=?",
                      (facility.strip(), normalize_text(name), phone_norm, nid_norm, profession, now(), int(tid)))
        else:
            c.execute("UPDATE trainees SET facility=?, name=?, phone=?, national_id=?, profession=?, work_start_date=?, updated_at=? WHERE id=?",
                      (facility.strip(), normalize_text(name), phone_norm, nid_norm, profession, str(work_start_date or ""), now(), int(tid)))

def trainee_by_credentials(name, facility):
    with db() as c:
        r = c.execute("SELECT * FROM trainees WHERE name=? AND facility=? AND status IN ('approved','active') AND hidden=0", (normalize_text(name), facility)).fetchone()
        return dict(r) if r else None

def trainee_by_national_id(national_id):
    nid_norm = normalize_national_id(national_id)
    if not nid_norm:
        return None
    with db() as c:
        rows = c.execute("SELECT * FROM trainees WHERE status IN ('approved','active') AND hidden=0 ORDER BY id DESC").fetchall()
        matches = [dict(r) for r in rows if normalize_national_id(r["national_id"]) == nid_norm]
        return matches[0] if len(matches) == 1 else None

def trainee_by_phone_and_national_id(phone, national_id):
    phone_norm = normalize_egyptian_phone(phone)
    nid_norm = normalize_national_id(national_id)
    if not phone_norm or not nid_norm:
        return None
    with db() as c:
        rows = c.execute("SELECT * FROM trainees WHERE status IN ('approved','active') AND hidden=0 ORDER BY id DESC").fetchall()
        matches = [dict(r) for r in rows if normalize_egyptian_phone(r["phone"]) == phone_norm and normalize_national_id(r["national_id"]) == nid_norm]
        return matches[0] if len(matches) == 1 else None

def trainee_by_phone(phone):
    phone_norm = normalize_egyptian_phone(phone)
    if not phone_norm:
        return None
    with db() as c:
        rows = c.execute("SELECT * FROM trainees WHERE status IN ('approved','active') AND hidden=0 ORDER BY id DESC").fetchall()
        matches = [dict(r) for r in rows if normalize_egyptian_phone(r["phone"]) == phone_norm]
        return matches[0] if len(matches) == 1 else None

def phone_exists(phone):
    phone_norm = normalize_egyptian_phone(phone)
    if not phone_norm:
        return False
    with db() as c:
        return _find_duplicate_trainee_value(c, "phone", phone_norm)

def set_trainee_status_and_template(tid, status, assigned_template_id):
    with db() as c:
        enforce_trainee_scope_or_raise(tid, c)
        c.execute("""UPDATE trainees SET status=?, assigned_template_id=?, updated_at=?, approved_at=CASE WHEN ?='approved' THEN ? ELSE approved_at END WHERE id=?""",
                  (status, assigned_template_id, now(), status, now(), tid))

def set_bulk_template_for_all(assigned_template_id):
    with db() as c:
        c.execute("""UPDATE trainees SET assigned_template_id=?, status=CASE WHEN status='pending' THEN 'approved' ELSE status END, approved_at=CASE WHEN status='pending' THEN ? ELSE approved_at END, updated_at=? WHERE hidden=0""",
                  (assigned_template_id, now(), now()))

def trainees_df(status=None, include_hidden=False):
    with db() as c:
        q = "SELECT id, facility, name, phone, national_id, profession, status, assigned_template_id, created_at, approved_at, hidden FROM trainees"
        conditions = []
        args = []
        if status:
            conditions.append("status=?")
            args.append(status)
        if not include_hidden:
            conditions.append("hidden=0")

        scope_pred, scope_args = hierarchy_filter_for_trainees(current_user_trainee_scope(), "trainees")
        if scope_pred != "1=1":
            conditions.append(scope_pred)
            args.extend(scope_args)
        if conditions:
            q += " WHERE " + " AND ".join(conditions)
        q += " ORDER BY id DESC"
        return pd.read_sql_query(q, c, params=args)

def choose_questions(t):
    """Select global questions plus questions owned by the selected administrative section(s)."""
    if not t:
        return []
    t_dict = dict(t)
    cats_raw = t_dict.get("categories_json", "[]")
    try:
        cats = json.loads(cats_raw) if cats_raw else []
    except Exception:
        cats = []
    limit_count = int(t_dict.get("num_questions", 999999))
    scope_ids = {"directorate_section": set(), "administration_section": set()}
    with db() as c:
        dsec = str(t_dict.get("scope_directorate_section") or "").strip()
        authority = str(t_dict.get("scope_authority") or "").strip()
        asec = str(t_dict.get("scope_administration_section") or "").strip()
        administration = str(t_dict.get("scope_administration") or "").strip()
        if dsec:
            sql = "SELECT ds.id FROM directorate_sections ds JOIN directorates d ON d.id=ds.directorate_id WHERE ds.name=?"
            args = [dsec]
            if authority:
                sql += " AND d.name=?"; args.append(authority)
            scope_ids["directorate_section"].update(int(r[0]) for r in c.execute(sql, args).fetchall())
        if asec:
            sql = "SELECT s.id FROM administration_sections s JOIN departments a ON a.id=s.department_id WHERE s.name=?"
            args = [asec]
            if administration:
                sql += " AND a.name=?"; args.append(administration)
            scope_ids["administration_section"].update(int(r[0]) for r in c.execute(sql, args).fetchall())
        clauses = ["active=1", "(COALESCE(scope_type,'global')='global' OR (scope_type='directorate_section' AND scope_id IN (%s)) OR (scope_type='administration_section' AND scope_id IN (%s)))" % (
            ",".join("?" for _ in scope_ids["directorate_section"]) or "NULL",
            ",".join("?" for _ in scope_ids["administration_section"]) or "NULL")]
        args = list(scope_ids["directorate_section"]) + list(scope_ids["administration_section"])
        if cats:
            clauses.append("category IN (%s)" % ",".join("?" for _ in cats)); args.extend(cats)
        rows = [dict(r) for r in c.execute("SELECT * FROM questions WHERE " + " AND ".join(clauses) + " ORDER BY RANDOM()", args).fetchall()]
        # If category filtering returns no questions, retain the scoped bank and global bank as a safe fallback.
        if not rows and cats:
            clauses = ["active=1", "(COALESCE(scope_type,'global')='global' OR (scope_type='directorate_section' AND scope_id IN (%s)) OR (scope_type='administration_section' AND scope_id IN (%s)))" % (
                ",".join("?" for _ in scope_ids["directorate_section"]) or "NULL",
                ",".join("?" for _ in scope_ids["administration_section"]) or "NULL")]
            args = list(scope_ids["directorate_section"]) + list(scope_ids["administration_section"])
            rows = [dict(r) for r in c.execute("SELECT * FROM questions WHERE " + " AND ".join(clauses) + " ORDER BY RANDOM()", args).fetchall()]
    if limit_count >= 999900:
        return rows
    return rows[:limit_count]

def start_session(trainee_id, template_id, exam_stage=None):

    if st.session_state.get("logged_in"):
        if not is_owner():
            enforce_trainee_scope_or_raise(trainee_id)
    else:
        current_tid = st.session_state.get("trainee_id")
        if not current_tid or int(current_tid) != int(trainee_id):
            raise PermissionError("يجب تسجيل دخول المتدرب نفسه قبل بدء الاختبار.")
    with db() as c:
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        if not t:
            raise ValueError("نموذج الاختبار غير موجود.")
        t_dict = dict(t)
        trainee_row = c.execute("SELECT facility, profession FROM trainees WHERE id=? AND hidden=0", (trainee_id,)).fetchone()
        if not trainee_row:
            raise ValueError("المتدرب غير موجود أو غير متاح حالياً.")
        scope_values = {
            "governorate": t_dict.get("scope_governorate") or "",
            "authority": t_dict.get("scope_authority") or "",
            "center": t_dict.get("scope_center") or "",
            "administration": t_dict.get("scope_administration") or "",
            "facility_name": t_dict.get("scope_facility") or "",
        }
        if any(scope_values.values()):
            h_row = c.execute("SELECT * FROM hierarchical_facilities WHERE facility_name=? AND hidden=0 LIMIT 1", (trainee_row["facility"],)).fetchone()
            if not h_row or not all((not v) or str(h_row[k] or "").strip() == str(v).strip() for k, v in scope_values.items()):
                raise ValueError("هذا النموذج غير مخصص للجهة الإدارية التابعة لك.")
        stage_value = str(exam_stage or t_dict.get("exam_type") or "").strip()
        if stage_value == "قبل وبعد التدريب (نفس النموذج)":
            raise ValueError("اختر مرحلة الامتحان: قبل التدريب أو بعد التدريب.")
        schedule = get_schedule_for_trainee(trainee_id, template_id, stage_value)
        start_t_str = schedule.get("start_time") if schedule else None
        end_t_str = schedule.get("end_time") if schedule else None
        if start_t_str and end_t_str:
            dt_now = now_cairo()
            dt_start = datetime.fromisoformat(str(start_t_str))
            dt_end = datetime.fromisoformat(str(end_t_str))
            if dt_start.tzinfo is None:
                dt_start = dt_start.replace(tzinfo=CAIRO_TZ)
            else:
                dt_start = dt_start.astimezone(CAIRO_TZ)
            if dt_end.tzinfo is None:
                dt_end = dt_end.replace(tzinfo=CAIRO_TZ)
            else:
                dt_end = dt_end.astimezone(CAIRO_TZ)
            dt_now = dt_now.astimezone(CAIRO_TZ)
            if dt_now < dt_start:
                raise ValueError(f"عذراً، لم يحن موعد الاختبار بعد. موعد البدء المحدد: {start_t_str.replace('T', ' الساعة ')}")
            if dt_now > dt_end:
                raise ValueError("عذراً، انتهى موعد هذا الاختبار ولم يعد متاحاً.")
        else:
            raise ValueError("عذراً، لم تقم الإدارة بتحديد موعد ساري لبدء ونهاية هذا الاختبار بعد.")

        today_start = today_date() + "T00:00:00"
        completed_today = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND template_id=? AND status='submitted' AND started_at>=? AND COALESCE(exam_stage,'')=?", (trainee_id, template_id, today_start, stage_value)).fetchone()
        if completed_today:
            raise ValueError("عذراً، لا يمكنك أداء هذه المرحلة من الاختبار أكثر من مرة في نفس اليوم.")

        active = c.execute("SELECT 1 FROM exam_sessions WHERE trainee_id=? AND status='active'", (trainee_id,)).fetchone()
        if active:
            raise ValueError("لديك اختبار نشط بالفعل.")

        qs = choose_questions(t)
        started = now_cairo()
        expires = started + timedelta(minutes=int(t_dict.get("duration_minutes", 60)))

        if schedule and schedule.get("end_time"):
            try:
                schedule_end_dt = datetime.fromisoformat(str(schedule["end_time"]))
                if schedule_end_dt.tzinfo is None:
                    schedule_end_dt = schedule_end_dt.replace(tzinfo=CAIRO_TZ)
                if schedule_end_dt < expires:
                    expires = schedule_end_dt
            except Exception:
                pass
        if expires <= started:
            raise ValueError("انتهت نافذة إتاحة الامتحان؛ لا يمكن بدء اختبار الآن.")
        with db() as c:
            cur = c.execute("INSERT INTO exam_sessions(trainee_id,template_id,started_at,expires_at,status,exam_stage) VALUES(?,?,?,?,?,?)",
                            (trainee_id, template_id, started.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds"), "active", stage_value))
            sid = cur.lastrowid
            for pos, q in enumerate(qs):
                try:
                    opts_parsed = json.loads(q["options_json"])
                except:
                    opts_parsed = ["نعم", "لا"]
                order = list(range(len(opts_parsed)))
                random.shuffle(order)
                c.execute("INSERT INTO exam_questions(session_id,question_id,position,option_order_json) VALUES(?,?,?,?)",
                          (sid, q["id"], pos, json.dumps(order)))
            c.execute("UPDATE trainees SET status='active', updated_at=? WHERE id=?", (now(), trainee_id))
            return sid


def generate_individual_certificate_code(session_id, trainee_id=None, template_id=None):
    """Create a stable, non-sequential verification code for an individual certificate."""
    payload = f"individual-certificate|{int(session_id)}|{int(trainee_id or 0)}|{int(template_id or 0)}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12].upper()
    return "CERT-" + digest

def submit_session(sid):
    with db() as c:
        s = c.execute("SELECT * FROM exam_sessions WHERE id=?", (int(sid),)).fetchone()
        if not s:
            raise PermissionError("جلسة الاختبار غير موجودة أو غير متاحة.")

        enforce_session_access_or_raise(sid, c)
        if s["status"] != "active":
            return None
        rows = c.execute("SELECT eq.*, q.answer FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=?", (sid,)).fetchall()
        correct = sum(1 for r in rows if r["selected_option"] is not None and int(r["selected_option"]) == int(r["answer"]))
        max_score = len(rows)
        percent = (correct / max_score * 100) if max_score else 0
        t = c.execute("SELECT * FROM exam_templates WHERE id=?", (s["template_id"],)).fetchone()
        t_dict = dict(t) if t else {}
        pass_pct = float(t_dict.get("pass_percent", 60.0))
        passed = 1 if percent >= pass_pct else 0
        cert = generate_individual_certificate_code(sid, s["trainee_id"], s["template_id"])
        submitted_dt = now_cairo()
        try:
            started_dt = datetime.fromisoformat(s["started_at"])
            expires_dt = datetime.fromisoformat(s["expires_at"])
            if started_dt.tzinfo is None:
                started_dt = started_dt.replace(tzinfo=CAIRO_TZ)
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=CAIRO_TZ)
            exam_duration_minutes = max(1, int((expires_dt - started_dt).total_seconds() // 60))
        except Exception:
            exam_duration_minutes = max(1, int(t_dict.get("duration_minutes", 60)))
        review_expires = (submitted_dt + timedelta(minutes=exam_duration_minutes)).isoformat(timespec="seconds")
        submitted_str = submitted_dt.isoformat(timespec="seconds")
        c.execute("UPDATE exam_sessions SET status='submitted', submitted_at=?, review_expires_at=?, score=?, max_score=?, percent=?, passed=?, certificate_id=? WHERE id=?",
                  (submitted_str, review_expires, correct, max_score, percent, passed, cert, sid))
        c.execute("UPDATE trainees SET status='completed', updated_at=? WHERE id=?", (submitted_str, s["trainee_id"]))
        return {"score": correct, "max_score": max_score, "percent": percent, "passed": passed, "certificate_id": cert, "review_expires_at": review_expires}

def render_logos_html():
    sett = get_print_settings()
    logo1 = sett.get("logo_base64", DEFAULT_LOGO) or DEFAULT_LOGO
    logo2 = sett.get("logo2_base64", "") or ""
    logo3 = sett.get("logo3_base64", "") or ""
    logos = [logo1, logo2, logo3]
    logos_list_html = ""
    for i, logo in enumerate(logos, start=1):
        if logo:
            logos_list_html += f'<img src="{logo}" style="width:45px; height:45px; object-fit:contain; display:block;" alt="Logo {i}">'
    return f"""
    <div style="display:flex; flex-direction:row; gap:8px; align-items:center; justify-content:flex-start; direction:ltr;">
        {logos_list_html}
    </div>
    """

def generate_qr_code_base64(data_text):
    qr = qrcode.QRCode(version=1, box_size=5, border=1)
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return "data:image/png;base64," + __import__("base64").b64encode(buffered.getvalue()).decode("utf-8")

def _certificate_background_css(sett):
    """Return the certificate page background. Background image is the only frame source."""
    bg_data = sett.get("bg_base64", "") or ""
    if bg_data:
        return f"background-image:url('{bg_data}'); background-repeat:no-repeat; background-position:center center; background-size:100% 100%;"
    return "background:#ffffff; border:1.2mm solid #059669;"


def _certificate_inner_box_css(sett):
    """Return the adjustable inner content box used for every certificate element."""
    raw = sett.get("cert_box_inset", "13mm") or "13mm"
    try:
        value = float(str(raw).replace("mm", "").strip())
    except Exception:
        value = 13.0
    value = max(4.0, min(35.0, value))
    return f"top:{value:g}mm;right:{value:g}mm;bottom:{value:g}mm;left:{value:g}mm;"


def _certificate_common_html(inner_content, sett):
    bg_css = _certificate_background_css(sett)
    box_css = _certificate_inner_box_css(sett)
    return f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@500;700;800;900&family=Reem+Kufi:wght@700&display=swap');
@page {{ size:A4 landscape; margin:0 !important; }}
html,body {{ margin:0 !important; padding:0 !important; width:297mm; height:210mm; }}
body {{ font-family:'Cairo','Tahoma',sans-serif; direction:rtl; overflow:hidden; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }}
.cert-page {{ width:297mm; height:210mm; position:relative; overflow:hidden; margin:0; padding:0; box-sizing:border-box; {bg_css} }}
.cert-inner-box {{ position:absolute; {box_css} box-sizing:border-box; display:flex; flex-direction:column; justify-content:flex-start; overflow:hidden; text-align:center; padding:4mm 7mm 3mm 7mm; }}
.cert-header {{ display:none !important; flex:0 0 auto; width:100%; display:flex; justify-content:space-between; align-items:flex-start; direction:rtl; min-height:18mm; margin-bottom:0; }}
.header-right {{ text-align:right; font-size:11pt; line-height:1.3; font-weight:900; color:#064e3b; max-width:72%; }}
.cert-logos {{ text-align:left; flex:0 0 auto; }}
.cert-body {{ flex:0 0 auto; min-height:0; width:100%; display:flex; flex-direction:column; justify-content:flex-start; align-items:center; overflow:hidden; }}
h1.cert-main-title {{ font-family:'Reem Kufi','Amiri','Cairo',serif; color:#047857; font-size:32pt; line-height:1.05; margin:0 0 2mm 0; font-weight:700; }}
.cert-prefix-line {{ font-size:18pt; line-height:1.2; color:#374151; font-weight:800; margin:1mm 0 2mm; min-height:7mm; }}
.cert-person-line {{ font-size:25pt; line-height:1.15; color:#064e3b; font-weight:900; margin:1mm 0 3mm; white-space:nowrap; }}
.cert-facility-line {{ font-size:20pt; line-height:1.2; color:#047857; font-weight:900; margin:1mm 0 3mm; white-space:nowrap; }}
.cert-profession-line {{ font-size:16pt; line-height:1.2; color:#374151; font-weight:800; margin:0.5mm 0 1.5mm; white-space:nowrap; min-height:0; }}
.cert-result-row {{ width:94%; display:flex; align-items:center; justify-content:center; gap:10mm; margin-top:2mm; margin-bottom:0; }}
.cert-result {{ font-size:15pt; line-height:1.35; color:#1f2937; font-weight:900; white-space:nowrap; }}
.cert-number {{ font-size:12pt; line-height:1.2; color:#064e3b; font-weight:900; white-space:nowrap; }}
.cert-qr {{ display:flex; align-items:center; gap:2mm; direction:ltr; flex:0 0 auto; }}
.cert-qr img {{ width:18mm; height:18mm; display:block; }}
.cert-code {{ font-size:8pt; font-weight:900; color:#064e3b; white-space:nowrap; }}
.cert-footer {{ flex:0 0 auto; width:100%; margin-top:4mm; }}
.credits-footer-row {{ width:100%; display:flex; justify-content:space-between; align-items:flex-end; direction:rtl; font-size:9.5pt; font-weight:900; color:#065f46; margin-top:2mm; line-height:1.2; }}
.ownership-footer-row {{ width:100%; text-align:center; font-size:8pt; font-weight:800; color:#047857; padding:1.5mm 0; margin-top:1mm; line-height:1.2; border-top:1.2px solid #047857; border-bottom:1.2px solid #047857; box-sizing:border-box; }}
</style>
</head>
<body>
<div class="cert-page">
  <div class="cert-inner-box">
    {inner_content}
  </div>
</div>
</body>
</html>
"""


def _certificate_footer_html():
    return """
<div class="cert-footer">
  <div class="ownership-footer-row">جميع الحقوق محفوظة © 2026 | تطوير Dr/Ahmed.S.Hegazy</div>
  <div class="credits-footer-row">
    <span>مسؤول التدريب</span><span>رئيس القسم</span><span>مدير المتوطنة</span><span>يعتمد: مدير عام الإدارة</span>
  </div>
</div>
"""


def generate_customizable_certificate_html(sid, custom_title=None, custom_notes=None):
    """Generate one individual A4-landscape certificate."""
    sett = get_print_settings()
    title_val = "شَهَادَةُ حُضُورِ دَوْرَةٍ تَدْرِيبِيَّةٍ"
    prefix_val = (sett.get("trainee_prefix", "") or "").strip()
    title_role_val = (sett.get("trainee_title", "") or "").strip()

    with db() as c:
        r = c.execute("""SELECT s.*, t.name trainee_name, t.facility, t.profession trainee_profession,
                        e.name template_name, e.exam_type
                        FROM exam_sessions s
                        JOIN trainees t ON t.id=s.trainee_id
                        LEFT JOIN exam_templates e ON e.id=s.template_id
                        WHERE s.id=?""", (sid,)).fetchone()
    if not r:
        return ""
    enforce_session_access_or_raise(sid)

    name = str(r["trainee_name"] or "").strip()
    prof = str(r["trainee_profession"] or sett.get("trainee_profession", "أخصائي الأمراض المتوطنة") or "").strip()
    facility = str(r["facility"] or "").strip()
    score = r["score"] or 0
    max_score = r["max_score"] or 0
    percent = float(r["percent"] or 0)
    status_text = "اجتاز الاختبار بنجاح" if r["passed"] else "لم يجتز الاختبار"
    cert_no = str(r["certificate_id"] or generate_individual_certificate_code(sid, r["trainee_id"], r["template_id"]))
    qr = generate_qr_code_base64(cert_no)


    prefix_html = f"<div class='cert-prefix-line'>{esc(prefix_val)}</div>" if prefix_val else ""
    person_label = " ".join(x for x in [title_role_val, name] if x)

    inner = f"""
<div class="cert-header">
  <div class="header-right">{hierarchy_header_html(scope=(json.loads(sett.get("cert_hierarchy_json", "{}") or "{}") if isinstance(sett.get("cert_hierarchy_json", "{}"), str) else (sett.get("cert_hierarchy_json") or {})), facility_value=facility)}</div>
  <div class="cert-logos">{render_logos_html()}</div>
</div>
<div class="cert-body">
  <h1 class="cert-main-title">{esc(title_val)}</h1>
  {prefix_html}
  <div class="cert-person-line" style="color:#b91c1c;">{esc(person_label)}</div>
  <div class="cert-profession-line">الوظيفة: {esc(prof)} &nbsp;&nbsp; | &nbsp;&nbsp; المنشأة: {esc(facility)}</div>
  <div class="cert-profession-line">{esc(str(sett.get("cert_trainee_extra", "") or "").strip())}</div>
  <div class="cert-result-row">
    <div class="cert-result">النتيجة: {score} / {max_score} ({percent:.1f}%) — {status_text}</div>
    <div class="cert-number">رقم الشهادة: {esc(cert_no)}</div>
    <div class="cert-qr"><img src="{qr}" alt="QR"><span class="cert-code">QR</span></div>
  </div>
</div>
{_certificate_footer_html()}
"""
    return _certificate_common_html(inner, sett)


def generate_facility_certificate_html(facility_name, session_ids, custom_title=None):
    """Generate one A4-landscape certificate evaluating an entire facility from submitted reports."""
    sett = get_print_settings()
    title_val = (custom_title or "شهادة تقييم منشأة") or "شهادة تقييم منشأة"
    prefix_val = (sett.get("trainee_prefix", "") or "").strip()

    if not st.session_state.get("logged_in"):
        raise PermissionError("يجب تسجيل دخول الإدارة لإنشاء شهادة تقييم منشأة.")
    rows = []
    with db() as c:
        for sid in session_ids:
            row = c.execute("SELECT s.percent, s.trainee_id, t.facility FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.id=? AND s.status='submitted' AND t.hidden=0", (sid,)).fetchone()
            if row:
                if st.session_state.get("logged_in") and not is_owner():
                    enforce_trainee_scope_or_raise(row["trainee_id"], c)
                if str(row["facility"] or "").strip() != str(facility_name or "").strip():
                    continue
                rows.append(float(row["percent"] or 0))
    if not rows:
        return ""

    avg = sum(rows) / len(rows)

    issued_at = now()
    valid_session_ids = []
    with db() as c:
        for sid in session_ids:
            row = c.execute("SELECT s.id, t.facility FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.id=? AND s.status='submitted' AND t.hidden=0", (sid,)).fetchone()
            if row and str(row["facility"] or "").strip() == str(facility_name or "").strip():
                valid_session_ids.append(int(row["id"]))
        facility_code = None
        for _attempt in range(5):
            candidate = "FAC-" + secrets.token_hex(12).upper()
            try:
                c.execute("INSERT INTO facility_certificates(certificate_code, facility_name, session_ids_json, average_percent, issued_at) VALUES(?,?,?,?,?)",
                          (candidate, str(facility_name), json.dumps(valid_session_ids), float(avg), issued_at))
                facility_code = candidate
                break
            except sqlite3.IntegrityError:
                continue
        if not facility_code:
            raise RuntimeError("تعذر إنشاء رقم شهادة منشأة فريد. حاول مرة أخرى.")
    qr = generate_qr_code_base64(facility_code)
    prefix_html = f"<div class='cert-prefix-line'>{esc(prefix_val)}</div>" if prefix_val else ""

    inner = f"""
<div class="cert-header">
  <div class="header-right">{hierarchy_header_html(scope=(json.loads(sett.get("cert_hierarchy_json", "{}") or "{}") if isinstance(sett.get("cert_hierarchy_json", "{}"), str) else (sett.get("cert_hierarchy_json") or {})), facility_value=facility_name)}</div>
  <div class="cert-logos">{render_logos_html()}</div>
</div>
<div class="cert-body">
  <h1 class="cert-main-title">{esc(title_val)}</h1>
  {prefix_html}
  <div class="cert-profession-line" style="color:#b91c1c; font-size:18pt;">{esc(str(sett.get("cert_facility_section", "") or "").strip())}</div>
  <div class="cert-facility-line" style="color:#b91c1c;">{esc(facility_name)}</div>
  <div class="cert-profession-line">{esc(str(sett.get("cert_facility_extra", "") or "").strip())}</div>
  <div class="cert-result-row">
    <div class="cert-result">نتيجة تقييم المنشأة: {avg:.1f}%</div>
    <div class="cert-number">رقم الشهادة: {esc(facility_code)}</div>
    <div class="cert-qr"><img src="{qr}" alt="QR"><span class="cert-code">QR</span></div>
  </div>
</div>
{_certificate_footer_html()}
"""
    return _certificate_common_html(inner, sett)


def generate_certificates_batch_html(session_ids, custom_title=None, custom_notes=None):
    """Create one print document containing one individual certificate per A4 page."""
    pages = []
    for sid in session_ids:
        one = generate_customizable_certificate_html(sid, custom_title, custom_notes)
        if not one:
            continue
        body_start = one.find('<body>')
        body_end = one.rfind('</body>')
        if body_start >= 0 and body_end >= 0:
            pages.append(one[body_start + len('<body>'):body_end])
    if not pages:
        return ""
    return f"""
<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8">
<style>@page {{ size:A4 landscape; margin:0 !important; }} html,body {{margin:0!important;padding:0!important;width:297mm;}} body {{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;}} .cert-page {{page-break-after:always!important;break-after:page!important;}} .cert-page:last-child {{page-break-after:avoid!important;break-after:avoid-page!important;}}</style></head><body>{''.join(pages)}</body></html>"""

def generate_trainee_exam_sheet_html(sid):
    if not st.session_state.get("logged_in"):
        raise PermissionError("طباعة نموذج الإجابة متاحة للإدارة المصرح لها فقط.")
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    with db() as c:
        s = c.execute("""SELECT s.*, t.name trainee_name, t.facility, t.profession trainee_profession, e.name template_name, COALESCE(NULLIF(s.exam_stage,''), e.exam_type) AS exam_type FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?""", (sid,)).fetchone()
        if not s:
            return ""
        enforce_session_access_or_raise(sid, c)
        rows = c.execute("""SELECT eq.*, q.question, q.options_json, q.answer FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=? ORDER BY eq.position""", (sid,)).fetchall()
    q_html_content = ""
    for idx, r in enumerate(rows, start=1):
        try:
            opts = json.loads(r["options_json"])
        except:
            opts = ["نعم", "لا"]
        try:
            order = json.loads(r["option_order_json"])
        except:
            order = list(range(len(opts)))
        disp_opts = [opts[i] for i in order]
        selected_opt_idx = r["selected_option"]
        correct_ans_idx = r["answer"]
        is_correct = r["is_correct"]
        raw_q_text = r["question"]
        
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
            opts_html += f'<div style="padding: 0.1mm 1mm; margin: 0 0 0.1mm 0; background: {style_bg}; border: 1px solid {border_color}; border-radius: 2px; font-size: 8pt; line-height: 1.0;">{icon_str} {esc(opt_text)}</div>'

        if "IMAGE:" in raw_q_text:
            parts = raw_q_text.split("\n\n")
            img_uri = parts[0].replace("IMAGE:", "").strip()
            q_text_clean = parts[1] if len(parts) > 1 else ""
            if img_uri:
                content_inner_html = f'''
                <div style="display: flex; flex-direction: row; gap: 4mm; align-items: flex-start; width: 100%;">
                    <div style="flex: 1; min-width: 0;">{opts_html}</div>
                    <div style="width: 32mm; flex-shrink: 0; text-align: center;">
                        <img src="{img_uri}" style="max-height: 18mm; max-width: 32mm; object-fit: contain; border-radius: 2px; border: 1px solid #cbd5e1; display: block; margin: auto;">
                    </div>
                </div>
                '''
            else:
                content_inner_html = opts_html
        else:
            q_text_clean = raw_q_text
            content_inner_html = opts_html

        q_text_clean = clean_question_text(q_text_clean)
        status_badge = '<span style="color: green; font-weight: bold;">صحيح</span>' if is_correct else '<span style="color: red; font-weight: bold;">خاطئ</span>'
        q_html_content += f"""
        <div style="margin: 0; padding: 0.6mm 1.2mm; background:#ffffff; border:1px solid #059669; border-radius:4px; box-sizing:border-box; width:100%; height:30mm; min-height:30mm; max-height:30mm; overflow:hidden; display:flex; flex-direction:column; justify-content:flex-start; page-break-inside:avoid; break-inside:avoid;">
            <div style="font-weight: bold; color: #065f46; margin-bottom: 0.3px; font-size: 8pt; line-height: 1.0; height: 7.5mm; overflow: hidden;">({idx}) {esc(q_text_clean)} | النتيجة: {status_badge}</div>
            <div style="margin-top: 0px; padding-right: 0px; flex-grow: 1;">{content_inner_html}</div>
        </div>
        """
    score_val, max_score_val, percent_val = s["score"] or 0, s["max_score"] or 0, s["percent"] or 0.0
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
    <meta charset="UTF-8">
    <style>
    @page {{ size: A4 landscape; margin: 10mm 8mm 18mm 8mm !important; }}
    body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0 !important; padding: 0 !important; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
    .report-wrapper {{ width: 281mm; max-width: 281mm; margin: 0 auto !important; padding: 0 !important; position: relative; }}
    h2 {{ text-align: center; color: #047857; font-size: 11pt; margin: 0 0 2px 0 !important; padding-top: 0 !important; line-height: {line_sp}; }}
    .tpl-info {{ background: #f0fdf4; border: 1px dashed #059669; padding: 2mm 6px; border-radius: 4px; margin-top: 2mm !important; margin-bottom: 2mm; font-size: 7.5pt; font-weight: bold; color: #065f46; text-align: center; line-height: {line_sp}; }}
    .questions-grid {{ display: grid; grid-template-columns: 1fr 1fr; grid-auto-rows: 30mm; gap: 2mm; width: 100%; }}
    </style>
    </head>
    <body>
    <div class="report-wrapper">
        <h2>نموذج إجابة واختبار المتدرب: {esc(s['trainee_name'])}</h2>
        <div class="tpl-info">
            جهة العمل: {esc(s['facility'])} | الوظيفة: {esc(s['trainee_profession'] if s['trainee_profession'] is not None else '')} | الاختبار: {esc(s['template_name'] or 'اختبار معتمد')} ({esc(s['exam_type'] or 'قبل التدريب')}) | النتيجة: {score_val} / {max_score_val} ({percent_val:.1f}%)
        </div>
        <div class="questions-grid">
            {q_html_content}
        </div>
    </div>
    </body>
    </html>
    """

def generate_staff_signature_table_html(scope=None, title="كشف العاملين والتوقيع"):
    """Build a printable staff roster matching the selected administrative hierarchy."""
    scope = dict(scope or {})
    selected_keys = (
        ("scope_governorate", "governorate"),
        ("scope_authority", "authority"),
        ("scope_center", "center"),
        ("scope_administration", "administration"),
        ("scope_facility", "facility_name"),
    )
    with db() as c:
        staff_rows = [dict(r) for r in c.execute(
            "SELECT id, name, profession, facility FROM trainees "
            "WHERE COALESCE(hidden,0)=0 ORDER BY name COLLATE NOCASE"
        ).fetchall()]

    active_hierarchy = get_hierarchical_data(include_hidden=False)
    if any(str(scope.get(k) or "").strip() for k, _ in selected_keys):
        scoped_hierarchy = [
            h for h in active_hierarchy
            if all(
                not str(scope.get(scope_key) or "").strip()
                or str(h.get(hierarchy_key) or "").strip() == str(scope.get(scope_key) or "").strip()
                for scope_key, hierarchy_key in selected_keys
            )
        ]
        staff_rows = [
            person for person in staff_rows
            if any(trainee_matches_hierarchy(person.get("facility"), h) for h in scoped_hierarchy)
        ]

    body_rows = []
    for idx, person in enumerate(staff_rows, start=1):
        body_rows.append(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td style='text-align:right'>{esc(person.get('name') or '')}</td>"
            f"<td>{esc(person.get('profession') or '')}</td>"
            "<td style='height:9mm'>&nbsp;</td>"
            "</tr>"
        )
    if not body_rows:
        body_rows.append(
            "<tr><td>1</td><td style='text-align:right;height:9mm'>&nbsp;</td>"
            "<td>&nbsp;</td><td style='height:9mm'>&nbsp;</td></tr>"
        )

    return f"""
    <section class="staff-signature-roster" style="margin-top:7mm; page-break-inside:auto; break-inside:auto;">
      <h3 style="text-align:center; margin:0 0 3mm; font-size:12pt; color:#047857;">{esc(title)}</h3>
      <table style="width:100%; border-collapse:collapse; font-size:10pt;">
        <thead><tr>
          <th style="border:1px solid #64748b; padding:5px; width:8%;">م</th>
          <th style="border:1px solid #64748b; padding:5px; width:38%;">اسم العامل</th>
          <th style="border:1px solid #64748b; padding:5px; width:29%;">الوظيفة</th>
          <th style="border:1px solid #64748b; padding:5px; width:25%;">التوقيع</th>
        </tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </section>
    """


def generate_general_report_html(title, content_html, target_pages=1, header_text=None):
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    report_scope = st.session_state.get("_last_hierarchy_scope", {})
    if not isinstance(report_scope, dict) or not any(str(v or "").strip() for v in report_scope.values()):
        try:
            report_scope = json.loads(sett.get("report_hierarchy_json", "{}") or "{}")
        except Exception:
            report_scope = {}
    has_report_scope = isinstance(report_scope, dict) and any(str(v or "").strip() for v in report_scope.values())
    target_name = ""
    if has_report_scope:
        for _key in ("scope_facility", "facility_name", "scope_administration_section", "administration_section", "scope_administration", "administration", "scope_directorate_section", "directorate_section", "scope_authority", "authority"):
            if str((report_scope or {}).get(_key) or "").strip():
                target_name = str(report_scope[_key]).strip()
                break
    header_html = hierarchy_header_html(report_scope if has_report_scope else {})
    target_html = ""  # The target is included in the administrative header to avoid duplication.
    roster_html = generate_staff_signature_table_html(report_scope if has_report_scope else {})
    printable_content = content_html + roster_html
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
    <meta charset="UTF-8">
    <style>
    @page {{ size: A4 landscape; margin: 10mm 8mm 18mm 8mm !important; }}
    body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0 !important; padding: 0 !important; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
    .report-wrapper {{ width: 281mm; max-width: 281mm; margin: 0 auto !important; padding: 0 !important; position: relative; }}
    .print-admin-header {{ display:flex; flex-direction:row; align-items:flex-start; justify-content:space-between; gap:5mm; width:100%; margin:0; padding:0; border:0; box-sizing:border-box; direction:ltr; }}
    .print-admin-logos {{ display:flex; flex:0 0 auto; flex-direction:row; align-items:flex-start; justify-content:flex-start; gap:2mm; min-width:16mm; }}
    .print-admin-hierarchy {{ flex:1; text-align:right; font-size:8.5pt; font-weight:700; line-height:1.25; color:#1f2937; }}
    .print-hierarchy-line {{ margin:0 0 0.5mm 0; }} .print-hierarchy-label {{ color:#475569; font-weight:900; }}
    .print-target-line {{ box-sizing:border-box; width:50%; margin:1.5mm auto 0 auto; padding:1.2mm 2mm; border:1px solid #065f46; border-radius:1.5mm; text-align:center; color:#065f46; font-size:10.5pt; font-weight:900; }}
    h2 {{ text-align: center; color: #047857; font-size: 12pt; margin: 0 0 2px 0 !important; padding-top: 0 !important; line-height: {line_sp}; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 2px; font-size: 8pt; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 3px 5px; text-align: center; line-height: {line_sp}; page-break-inside: avoid; break-inside: avoid; }}
    th {{ background-color: #059669; color: white; font-weight: bold; }}
    tr {{ page-break-inside: avoid; break-inside: avoid; }}
    tr:nth-child(even) {{ background-color: #f0fdf4; }}
    </style>
    </head>
    <body>
    <div class="report-wrapper">
        {header_html}
        <h2>{esc(title)}</h2>
        {target_html}
        <div style="text-align: left; font-size: 7.5pt; color: #6b7280; margin-bottom: 2px;">تاريخ الإصدار: {now_cairo().strftime('%Y-%m-%d %I:%M %p')}</div>
        {printable_content}
    </div>
    </body>
    </html>
    """

def generate_action_plan_report_html(title, content_html, target_pages=1, header_text=None, hierarchy_scope=None):
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    plan_scope = hierarchy_scope or st.session_state.get("_last_hierarchy_scope", {}) or {}
    has_plan_scope = isinstance(plan_scope, dict) and any(str(v or "").strip() for v in plan_scope.values())
    header_html = hierarchy_header_html(plan_scope if has_plan_scope else {})
    target_html = ""  # The lowest selected hierarchy level is identified in the header.
    roster_html = generate_staff_signature_table_html(plan_scope if has_plan_scope else {})
    printable_content = content_html + roster_html
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
    <meta charset="UTF-8">
    <style>
    @page {{ size: A4 landscape; margin: 10mm 8mm 18mm 8mm !important; }}
    body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0 !important; padding: 0 !important; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
    .report-wrapper {{ width: 281mm; max-width: 281mm; margin: 0 auto !important; padding: 0 !important; position: relative; }}
    .print-admin-header {{ display:flex; flex-direction:row; align-items:flex-start; justify-content:space-between; gap:5mm; width:100%; margin:0; padding:0; border:0; box-sizing:border-box; direction:ltr; }}
    .print-admin-logos {{ display:flex; flex:0 0 auto; flex-direction:row; align-items:flex-start; justify-content:flex-start; gap:2mm; min-width:16mm; }}
    .print-admin-hierarchy {{ flex:1; text-align:right; font-size:8.5pt; font-weight:700; line-height:1.25; color:#1f2937; }}
    .print-hierarchy-line {{ margin:0 0 0.5mm 0; }} .print-hierarchy-label {{ color:#475569; font-weight:900; }}
    .print-target-line {{ box-sizing:border-box; width:50%; margin:1.5mm auto 0 auto; padding:1.2mm 2mm; border:1px solid #065f46; border-radius:1.5mm; text-align:center; color:#065f46; font-size:10.5pt; font-weight:900; }}
    h2 {{ text-align: center; color: #047857; font-size: 12pt; margin: 0 0 2px 0 !important; padding-top: 0 !important; line-height: {line_sp}; }}
    </style>
    </head>
    <body>
    <div class="report-wrapper">
        {header_html}
        <h2>{esc(title)}</h2>
        {target_html}
        <div style="text-align: left; font-size: 7.5pt; color: #6b7280; margin-bottom: 2px;">تاريخ الإصدار: {now_cairo().strftime('%Y-%m-%d %I:%M %p')}</div>
        {printable_content}
    </div>
    </body>
    </html>
    """

def generate_exam_template_print_html(template_id, hierarchy_scope=None):
    if not st.session_state.get("logged_in"):
        raise PermissionError("طباعة نموذج الاختبار متاحة للإدارة المصرح لها فقط.")
    sett = get_print_settings()
    line_sp = sett.get("line_spacing", 1.25)
    with db() as c:
        tpl = c.execute("SELECT * FROM exam_templates WHERE id=?", (template_id,)).fetchone()
        if not tpl:
            return ""
        t_dict = dict(tpl)
    questions_list = choose_questions(t_dict)
    # Use the selected print scope for this exam template. Keep the existing
    # target-facility line, but show the parent hierarchy names without labels.
    exam_scope = dict(hierarchy_scope or {})
    if not any(str(v or "").strip() for v in exam_scope.values()):
        exam_scope = {k: t_dict.get(k, "") for k in (
            "scope_authority", "scope_directorate_section", "scope_administration",
            "scope_administration_section", "scope_facility", "scope_governorate", "scope_center"
        )}
    exam_header_html = hierarchy_header_html(exam_scope)
    # Remove the labels preceding each hierarchy name; preserve the target line as-is.
    exam_header_html = re.sub(r'<span class="print-hierarchy-label">.*?</span>\s*', '', exam_header_html)
    q_html_content = ""
    for idx, q in enumerate(questions_list, start=1):
        try:
            opts = json.loads(q["options_json"])
        except:
            opts = ["نعم", "لا"]
        raw_q_text = q["question"]
        
        opts_html = "".join([f'<div style="padding: 0.1mm 1mm; margin: 0 0 0.1mm 0; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 2px; font-size: 8pt; line-height: 1.0;">🔲 {esc(opt)}</div>' for opt in opts])
        
        if "IMAGE:" in raw_q_text:
            parts = raw_q_text.split("\n\n")
            img_uri = parts[0].replace("IMAGE:", "").strip()
            q_text_clean = parts[1] if len(parts) > 1 else ""
            if img_uri:
                content_inner_html = f'''
                <div style="display: flex; flex-direction: row; gap: 4mm; align-items: flex-start; width: 100%;">
                    <div style="flex: 1; min-width: 0;">{opts_html}</div>
                    <div style="width: 32mm; flex-shrink: 0; text-align: center;">
                        <img src="{img_uri}" style="max-height: 18mm; max-width: 32mm; object-fit: contain; border-radius: 2mm; border: 1px solid #cbd5e1; display: block; margin: auto;">
                    </div>
                </div>
                '''
            else:
                content_inner_html = opts_html
        else:
            q_text_clean = raw_q_text
            content_inner_html = opts_html

        q_text_clean = clean_question_text(q_text_clean)
        q_html_content += f"""
        <div style="margin: 0; padding: 0.6mm 1.2mm; background:#ffffff; border:1px solid #059669; border-radius:4px; box-sizing:border-box; width:100%; height:30mm; min-height:30mm; max-height:30mm; overflow:hidden; display:flex; flex-direction:column; justify-content:flex-start; page-break-inside:avoid; break-inside:avoid;">
            <div style="font-weight: bold; color: #065f46; margin-bottom: 0.3px; font-size: 8pt; line-height: 1.0; height: 7.5mm; overflow: hidden;">({idx}) {esc(q_text_clean)}</div>
            <div style="margin-top: 0px; padding-right: 0px; flex-grow: 1;">{content_inner_html}</div>
        </div>
        """
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
    <meta charset="UTF-8">
    <style>
    @page {{ size: A4 portrait; margin: 10mm 8mm 18mm 8mm !important; }}
    body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0 !important; padding: 0 !important; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp}; }}
    .report-wrapper {{ width: 194mm; max-width: 194mm; margin: 0 auto !important; padding: 0 !important; position: relative; }}
    .print-admin-header {{ display:flex; flex-direction:row; align-items:flex-start; justify-content:space-between; gap:4mm; width:100%; margin:0 0 2mm 0; padding:0; box-sizing:border-box; direction:ltr; }}
    .print-admin-logos {{ display:flex; flex:0 0 auto; flex-direction:row; align-items:flex-start; justify-content:flex-start; gap:2mm; min-width:13mm; }}
    .print-admin-hierarchy {{ flex:1; text-align:right; font-size:8pt; font-weight:700; line-height:1.25; color:#1f2937; }}
    .print-hierarchy-line {{ margin:0 0 0.5mm 0; }}
    .print-target-line {{ box-sizing:border-box; width:50%; margin:1.5mm auto 0 auto; padding:1.2mm 2mm; border:1px solid #065f46; border-radius:1.5mm; text-align:center; color:#065f46; font-size:10.5pt; font-weight:900; }}
    h2 {{ text-align: center; color: #047857; font-size: 11pt; margin: 0 0 2px 0 !important; padding-top: 0 !important; line-height: {line_sp}; }}
    .tpl-info {{ background: #f0fdf4; border: 1px dashed #059669; padding: 2mm 6px; border-radius: 4px; margin-top: 2mm !important; margin-bottom: 2mm; font-size: 7.5pt; font-weight: bold; color: #065f46; text-align: center; line-height: {line_sp}; }}
    .questions-grid {{ display: grid; grid-template-columns: 1fr 1fr; grid-auto-rows: 30mm; gap: 2mm; width: 100%; }}
    </style>
    </head>
    <body>
    <div class="report-wrapper">
        {exam_header_html}
        <h2>نموذج امتحان: {esc(t_dict['name'])} ({esc(t_dict.get('exam_type', 'قبل التدريب'))})</h2>
        <div class="tpl-info">
            التصنيف: {esc(t_dict.get('exam_type', 'قبل التدريب'))} | مدة الاختبار: {t_dict['duration_minutes']} د | نسبة النجاح: {t_dict['pass_percent']}% | إجمالي الأسئلة: {len(questions_list)}
        </div>
        <div class="questions-grid">
            {q_html_content}
        </div>
    </div>
    </body>
    </html>
    """

def render_print_button_only(html_content, label_prefix=""):
    print_sett = get_print_settings()
    is_cert = ("شهاد" in label_prefix) or ("certificate" in label_prefix.lower())


    label_lower = str(label_prefix or "").lower()
    paper_profiles = normalized_paper_print_settings(print_sett.get("paper_print_settings_json", print_sett.get("paper_print_settings", {})))
    if is_cert:
        profile_key = "certificates"
    elif "نموذج امتحان" in label_prefix or "نماذج الامتحان" in label_prefix:
        profile_key = "exam_templates"
    elif "محضر تدريب" in label_prefix:
        profile_key = "training_minutes"
    elif "خطة عمل" in label_prefix:
        profile_key = "action_plans"
    elif "قاعدة بيانات المتدربين" in label_prefix:
        profile_key = "trainee_database"
    elif any(term in label_prefix for term in ("نموذج إجابة الامتحان", "تقرير نتيجة الممتحن", "نتائج جميع الممتحنين")):
        profile_key = "answer_sheets"
    else:
        profile_key = "reports"
    profile = paper_profiles.get(profile_key, default_paper_print_settings()["reports"])
    page_orientation = profile.get("orientation", "landscape")
    chosen_orient = "رأسي (Portrait)" if page_orientation == "portrait" else "أفقي (Landscape)"
    page_size = profile.get("paper", "A4")
    m_top = f'{profile.get("top", 12)}mm'
    m_right = f'{profile.get("right", 8)}mm'
    m_bottom = f'{profile.get("bottom", 16)}mm'
    m_left = f'{profile.get("left", 8)}mm'
    font_size = profile.get("font_size", 9)
    profile_line_spacing = profile.get("line_spacing", print_sett.get("line_spacing", 1.15))
    
    if is_cert:
        repeated_print_css = """
        <style>
        @page {
            size: A4 landscape;
            margin: 0 !important;
        }
        @media print {
            html, body {
                margin: 0 !important;
                padding: 0 !important;
                width: 297mm !important;
                height: 210mm !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            .cert-page {
                page-break-after: always !important;
                break-after: page !important;
            }
            .cert-page:last-child {
                page-break-after: avoid !important;
                break-after: avoid-page !important;
            }
        }
        </style>
        """
    else:
        repeated_print_css = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Naskh+Arabic:wght@400;500;600;700&display=swap');
        html, body, body * {{
            font-family: 'Noto Naskh Arabic', 'Amiri', 'Traditional Arabic', serif !important;
        }}
        html, body {{ font-size: {font_size}pt !important; }}
        body {{ line-height: {profile_line_spacing} !important; }}
        p, li {{ font-size: {max(7, font_size - 0.5)}pt; }}
        table {{ font-size: {max(7, font_size - 0.5)}pt; }}
        th, td {{ line-height: {profile_line_spacing}; }}
        .report-wrapper {{ width: 100% !important; max-width: 100% !important; box-sizing: border-box !important; }}
        .print-admin-header {{ position:static !important; top:auto !important; left:auto !important; right:auto !important; display:flex !important; flex-direction:row !important; align-items:flex-start !important; justify-content:space-between !important; gap:5mm !important; width:100% !important; margin:0 0 2mm 0 !important; padding:0 !important; border:0 !important; box-sizing:border-box !important; direction:ltr !important; z-index:auto !important; page-break-inside:avoid; break-inside:avoid; }}
        .print-admin-logos {{ display:flex !important; visibility:visible !important; opacity:1 !important; flex:0 0 auto !important; flex-direction:row !important; align-items:flex-start !important; justify-content:flex-start !important; gap:2mm !important; min-width:16mm; }}
        .print-admin-hierarchy {{ visibility:visible !important; opacity:1 !important; flex:1 !important; text-align:right !important; direction:rtl !important; font-size:8.5pt !important; font-weight:700 !important; line-height:1.25 !important; color:#1f2937 !important; }}
        .print-hierarchy-line {{ margin:0 0 0.5mm 0 !important; }} .print-hierarchy-label {{ color:#475569 !important; font-weight:900 !important; }}
        .print-target-line {{ box-sizing:border-box !important; width:50% !important; margin:1.5mm auto 0 auto !important; padding:1.2mm 2mm !important; border:1px solid #065f46 !important; border-radius:1.5mm !important; text-align:center !important; color:#065f46 !important; font-size:10.5pt !important; font-weight:900 !important; }}
        .print-admin-logos img {{ width:13mm !important; height:13mm !important; object-fit:contain !important; display:block !important; visibility:visible !important; opacity:1 !important; }}
        @page {{
            size: {page_size} {page_orientation};
            margin: {m_top} {m_right} {m_bottom} {m_left} !important;
        }}
        @media print {{
            html, body {{
                margin: 0 !important;
                padding: 0 !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            body {{
                counter-reset: page;
                margin-top: 0 !important;
            }}
            .report-wrapper {{
                margin-top: 0 !important;
                /* The hierarchy/logo block stays in normal document flow, so the title
                   automatically moves down when the block or the top page margin grows. */
                padding-top: 0 !important;
                box-sizing: border-box !important;
            }}
            .print-footer-dynamic {{
                position: fixed !important;
                left: 0 !important;
                right: 0 !important;
                bottom: 0 !important;
                inset-inline: 0 !important;
                display: block !important;
                width: 100% !important;
                background: #ffffff !important;
                border: 1px solid #a9f4ff; border-top: 2px solid #bdfaff; border-radius: 10px 10px 0 0;
                margin: 0 !important;
                padding: 3px 4px !important;
                font-family: 'Cairo', Tahoma, sans-serif;
                font-size: 9pt;
                font-weight: 900;
                color: #065f46;
                box-sizing: border-box;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}
            .print-footer-container {{
                display: block !important;
                position: fixed !important;
                left: 0 !important;
                right: 0 !important;
                bottom: 0 !important;
                margin: 0 !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}
            .report-wrapper {{
                margin-bottom: 0 !important;
                padding-bottom: 0 !important;
                overflow: visible !important;
            }}
            .page-number-box {{
                counter-increment: page;
            }}
            .page-number-box::after {{
                content: "صفحة " counter(page);
            }}
            .print-footer-top-row {{
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                width: 100% !important;
                direction: rtl !important;
                font-size: 9.5pt;
                font-weight: 800;
                color: #047857;
                border-bottom: 1px dotted #059669;
                padding-bottom: 2px;
                margin-bottom: 2px;
            }}
            .print-footer-bottom-row {{
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                width: 100% !important;
                direction: rtl !important;
                font-size: 10pt;
                font-weight: 900;
                color: #065f46;
            }}
        }}
        .print-footer-dynamic {{
            position: static !important;
            inset: auto !important;
            width: 100% !important;
            background: #ffffff !important;
            border: 1px solid #a9f4ff; border-top: 2px solid #bdfaff; border-radius: 16px 16px 0 0;
            margin-top: 6mm;
            padding: 6px 4px;
            font-family: 'Cairo', Tahoma, sans-serif;
            font-size: 10pt;
            font-weight: 900;
            color: #065f46;
            box-sizing: border-box;
        }}
        .print-footer-top-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            direction: rtl;
            font-size: 9.5pt;
            font-weight: 800;
            color: #047857;
            border-bottom: 1px dotted #059669;
            padding-bottom: 2px;
            margin-bottom: 2px;
        }}
        .print-footer-bottom-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            direction: rtl;
            font-size: 10pt;
            font-weight: 900;
            color: #065f46;
        }}
        </style>
        """
        if not is_cert and 'class="print-admin-header"' not in html_content:
            _scope_for_print_header = st.session_state.get("_last_hierarchy_scope", {}) or {}
            _print_header_html = hierarchy_header_html(_scope_for_print_header)
            if _print_header_html:
                if '<div class="report-wrapper">' in html_content:
                    html_content = html_content.replace('<div class="report-wrapper">', '<div class="report-wrapper">' + _print_header_html, 1)
                elif "<body>" in html_content:
                    html_content = html_content.replace("<body>", "<body>" + _print_header_html, 1)

        footer_bar_html = f"""
        <div class="print-footer-container">
            <div class="print-footer-dynamic">
                <div class="print-footer-top-row">
                    <div style="text-align: center; width: 100%; font-size: 8pt;">جميع الحقوق محفوظة © 2026 | تطوير Dr/Ahmed.S.Hegazy</div>
                </div>
                <div class="print-footer-bottom-row">
                    <span>مسؤول التدريب</span>
                    <span>رئيس القسم</span>
                    <span>مدير المتوطنة</span>
                    <span>يعتمد: مدير عام الإدارة</span>
                </div>
            </div>
        </div>
        """
        if "</body>" in html_content:
            html_content = html_content.replace("</body>", footer_bar_html + "</body>")
        else:
            html_content += footer_bar_html

    if "</head>" in html_content:
        html_content = html_content.replace("</head>", repeated_print_css + "</head>", 1)
    else:
        html_content = repeated_print_css + html_content

    encoded_html = json.dumps(html_content)
    
    js_code = """
    <div style="margin: 4px 0;">
        <button onclick="printDoc()" style="width: 100%; background-color: #059669; color: white; padding: 8px 12px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-family: 'Cairo', sans-serif; font-size: 13pt;">
            🖨 طباعة / حفظ المستند (""" + page_size + """ """ + chosen_orient + """ - """ + label_prefix + """)
        </button>
    </div>
    <script>
    function printDoc() {
        var win = window.open('', '_blank');
        var styledHtml = """ + encoded_html + """;
        win.document.open();
        win.document.write(styledHtml);
        win.document.close();
        win.document.title = 'محضر وتقارير البرنامج';
        
        // عدد الصفحات يُحدد تلقائياً بواسطة محرك الطباعة حسب طول المحتوى.
        // لا يوجد أي حد ثابت لعدد الصفحات أو قص للمحتوى.

        win.focus();
        setTimeout(function(){
            win.print();
        }, 600);
    }
    </script>
    """
    components.html(js_code, height=100)




for k, v in {"logged_in": False, "username": "", "role": "", "permissions": [], "trainee_id": "", "trainee_name": "", "exam_session_id": None, "last_result_id": None, "form_key": 0, "add_success_msg": "", "active_admin_tab": "📊 لوحة التحكم", "scanned_cert_code": ""}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def header():
    header_html = f"""
    <style>
    .electric-box {{
        background: linear-gradient(145deg, rgba(0,188,231,.96) 0%, rgba(0,137,202,.97) 48%, rgba(0,103,177,.96) 100%);
        color: #ffffff; backdrop-filter: blur(12px) saturate(1.25); -webkit-backdrop-filter: blur(12px) saturate(1.25);
        width: 100%; max-width: 100%; padding: 20px 28px; border-radius: 28px; text-align: center;
        margin-bottom: 20px; font-family: 'Cairo', sans-serif; box-sizing: border-box;
        border: 2px solid #b8faff;
        box-shadow: inset 0 3px 10px rgba(255,255,255,.68), inset 0 -10px 18px rgba(0,54,120,.2), 0 0 0 3px rgba(50,226,255,.32), 0 5px 16px rgba(0,92,150,.22);
    }}
    </style>
    <div class="electric-box">
        <div style="display: flex; justify-content: center; align-items: center; gap: 8px; margin-bottom: 2px;">
            <span style="font-size: 24px;">🪱🔬🐌💊</span>
        </div>
        <div style="font-size: 19px; color: #ffffff; font-weight: 900; line-height: 1.3; margin-bottom: 4px; word-wrap: break-word;">مرحباً بك في بوابة تقييم واختبار العاملين بالأمراض المتوطنة</div>
        <div style="display: flex; justify-content: center; align-items: center; gap: 12px; flex-wrap: wrap;">
            <span style="font-size: 12px; font-weight: bold; background: rgba(255,255,255,0.2); color: #ffffff; padding: 2px 10px; border-radius: 12px;">System V1.0</span>
            <span id="live-clock-display" style="font-size: 13px; font-weight: bold; color: #e2e8f0;">جاري تحميل الوقت...</span>
        </div>
    </div>
    <script>
    function updateLiveClock() {{
        const options = {{ timeZone: 'Africa/Cairo', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }};
        const formatter = new Intl.DateTimeFormat('ar-EG', options);
        try {{
            document.getElementById('live-clock-display').innerHTML = "" + formatter.format(new Date()) + "";
        }} catch(e) {{
            document.getElementById('live-clock-display').innerHTML = "" + new Date().toLocaleString() + "";
        }}
    }}
    updateLiveClock();
    setInterval(updateLiveClock, 1000);
    </script>
    """
    components.html(header_html, height=190, scrolling=False)

def decode_qr_from_camera_image(uploaded_image):
    """Decode a QR code from a photo captured with Streamlit's camera widget."""
    if uploaded_image is None:
        return None, ""
    try:
        from PIL import Image as PILImage
        pil_image = PILImage.open(uploaded_image).convert("RGB")

        try:
            import cv2
            import numpy as np
            detector = cv2.QRCodeDetector()
            decoded, points, _ = detector.detectAndDecode(np.array(pil_image))
            if decoded and decoded.strip():
                return decoded.strip(), ""
        except Exception:
            pass
        try:
            from pyzbar.pyzbar import decode
            found = decode(pil_image)
            if found:
                return found[0].data.decode("utf-8", errors="replace").strip(), ""
        except Exception:
            pass
        return None, "لم يتم التعرف على QR في الصورة. تأكد من وضوح الرمز وحاول مرة أخرى، أو أدخل الكود يدوياً."
    except Exception as exc:
        return None, f"تعذر قراءة الصورة: {exc}"


def verification_portal_view():
    header()
    st.markdown("### 🔍 صفحة التحقق الرقمي من صحة الشهادات والبيانات الواردة")
    st.info("وجّه كاميرا الجهاز إلى QR الخاص بالشهادة والتقط صورة واضحة، أو ارفع صورة محفوظة. سيتم استخراج الكود ثم التحقق منه في قاعدة البيانات.")
    camera_photo = st.camera_input("📷 مسح QR بالكاميرا")
    uploaded_qr_img = st.file_uploader("📥 أو ارفع صورة QR للشهادة:", type=["png", "jpg", "jpeg"], key="certificate_qr_upload")
    qr_image = camera_photo if camera_photo is not None else uploaded_qr_img
    if qr_image is not None:
        try:
            from PIL import Image as PILImage
            img_pil = PILImage.open(qr_image)
            st.image(img_pil, caption="الصورة الملتقطة / المرفوعة", width=200)
            decoded_code, decode_error = decode_qr_from_camera_image(qr_image)
            if decoded_code:

                parsed_code = decoded_code.strip()
                if parsed_code.lower().startswith(("http://", "https://")):
                    parsed_code = parsed_code.rstrip("/").split("/")[-1].split("?")[0]
                st.session_state["scanned_cert_code"] = parsed_code
                st.success("✅ تم مسح QR واستخراج كود الشهادة. جارٍ التحقق من قاعدة البيانات.")
            elif decode_error:
                st.warning(decode_error)
        except Exception as e:
            st.error(f"عذراً، تعذر فتح الصورة: {e}")
    search_cert_code = st.text_input("رقم الشهادة أو كود التحقق:", value=st.session_state.get("scanned_cert_code", ""), key="certificate_verification_code")
    cert_to_verify = None
    if search_cert_code.strip():
        cert_code_clean = search_cert_code.strip().upper()
        facility_cert_to_verify = None
        with db() as c:
            cert_to_verify = c.execute("""SELECT s.*, t.name trainee_name, t.facility, t.profession trainee_profession, e.name template_name, COALESCE(NULLIF(s.exam_stage,''), e.exam_type) AS exam_type FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE (UPPER(s.certificate_id)=? OR s.id=?) AND t.hidden=0""", (cert_code_clean, cert_code_clean.replace("ELX-", "").lstrip("0") or "0")).fetchone()
            if not cert_to_verify and cert_code_clean.startswith("FAC-"):
                facility_cert_to_verify = c.execute("SELECT * FROM facility_certificates WHERE certificate_code=? AND COALESCE(verification_status,'valid')='valid'", (cert_code_clean,)).fetchone()
        if facility_cert_to_verify:
            fr = facility_cert_to_verify
            try:
                session_ids_for_cert = json.loads(fr["session_ids_json"] or "[]")
            except Exception:
                session_ids_for_cert = []
            st.markdown(f"""
            <div style="background:#f0fdf4;border:2px solid #059669;padding:20px;border-radius:12px;margin-top:15px;">
              <h3 style="color:#065f46;margin-top:0;">✅ شهادة منشأة مسجلة وصحيحة</h3>
              <p style="font-size:11pt;color:#111827;line-height:1.8;">
                🏥 <b>اسم المنشأة:</b> {esc(fr['facility_name'])}<br>
                📊 <b>نتيجة تقييم المنشأة وقت الإصدار:</b> {float(fr['average_percent'] or 0):.1f}%<br>
                👥 <b>عدد نتائج التقييم المسجلة بالشهادة:</b> {len(session_ids_for_cert)}<br>
                🔖 <b>رقم الشهادة الرسمي:</b> {esc(fr['certificate_code'])}<br>
                ⏰ <b>تاريخ الإصدار:</b> {esc(fr['issued_at'])}
              </p>
            </div>
            """, unsafe_allow_html=True)
        elif cert_to_verify:
            r = cert_to_verify
            status_str = "معتمدة وصحيحة بنسبة 100%" if r["passed"] else "غير اجتياز / غير معتمدة"
            score_val, max_score_val, percent_val = r["score"] or 0, r["max_score"] or 0, r["percent"] or 0.0
            st.markdown(f"""
            <div style="background: #f0fdf4; border: 2px solid #059669; padding: 20px; border-radius: 12px; margin-top: 15px;">
                <h3 style="color: #065f46; margin-top: 0;">✅ نتيجة التحقق وصحة البيانات الواردة:</h3>
                <p style="font-size: 11pt; color: #111827; line-height: 1.6;">
                    👤 <b>اسم المتدرب:</b> {esc(r['trainee_name'])}<br>
                    🩺 <b>الوظيفة / التخصص:</b> {esc(r['trainee_profession'] if r['trainee_profession'] is not None else '')}<br>
                    🏥 <b>جهة العمل والمنشأة:</b> {esc(r['facility'])}<br>
                    📋 <b>اسم الاختبار:</b> {esc(r['template_name'] or 'اختبار معتمد')} ({esc(r['exam_type'] or 'قبل التدريب')})<br>
                    📊 <b>الدرجة والنسبة المئوية:</b> {score_val} / {max_score_val} ({percent_val:.1f}%)<br>
                    🏷 <b>حالة الاعتماد:</b> <b style="color: {'green' if r['passed'] else 'red'};">{status_str}</b><br>
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
            @page {{ size: A4 landscape; margin: 15mm; }}
            body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0; padding: 10mm; direction: rtl; -webkit-print-color-adjust: exact; }}
            .doc-wrapper {{ max-width: 200mm; margin: auto; border: 3px double #059669; padding: 15mm; border-radius: 10mm; position: relative; }}
            h2 {{ text-align: center; color: #047857; margin-bottom: 5px; }}
            .meta-table {{ width: 100%; border-collapse: collapse; margin-top: 15mm; font-size: 11pt; }}
            .meta-table th, .meta-table td {{ border: 1px solid #cbd5e1; padding: 8px 12px; text-align: right; }}
            .meta-table th {{ background-color: #059669; color: white; }}
            </style>
            </head>
            <body>
            <div class="doc-wrapper">
                <h2>وثيقة إثبات صحة البيانات والاعتماد الرسمي</h2>
                <div style="text-align: center; font-size: 9pt; color: #6b7280; margin-bottom: 15mm;">صادر عن نظام تقييم واختبار العاملين بالأمراض المتوطنة</div>
                <table class="meta-table">
                    <tr><th>اسم المتدرب</th><td>{esc(r['trainee_name'])}</td></tr>
                    <tr><th>الوظيفة / التخصص</th><td>{esc(r['trainee_profession'] if r['trainee_profession'] is not None else '')}</td></tr>
                    <tr><th>جهة العمل</th><td>{esc(r['facility'])}</td></tr>
                    <tr><th>اسم الاختبار</th><td>{esc(r['template_name'] or 'اختبار معتمد')} ({esc(r['exam_type'] or 'قبل التدريب')})</td></tr>
                    <tr><th>النتيجة والنسبة</th><td>{score_val} / {max_score_val} ({percent_val:.1f}%)</td></tr>
                    <tr><th>حالة التحقق</th><td style="color: green; font-weight: bold;">{status_str}</td></tr>
                    <tr><th>رقم الشهادة</th><td><span style="font-weight: bold; color: #065f46;">{r['certificate_id']}</span></td></tr>
                    <tr><th>تاريخ الاعتماد</th><td>{r['submitted_at'] or r['started_at']}</td></tr>
                </table>
            </div>
            </body>
            </html>
            """
            st.markdown("<br>", unsafe_allow_html=True)
            render_print_button_only(verification_doc_html, f"توثيق صحة شهادة {r['certificate_id']}")
        elif search_cert_code.strip():
            st.warning("⚠ عذراً، لم نتمكن من العثور على شهادة بهذا الكود. تأكد من صحة رقم الشهادة.")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("العودة لتسجيل الدخول / الرئيسية"):
        st.session_state.show_verification_portal = False
        st.rerun()

def _reset_reg_admin_and_facility():
    st.session_state["reg_administration"] = "-- اختر الإدارة --"
    st.session_state["reg_facility"] = "-- اختر المنشأة --"

    st.session_state.pop("reg_directorate_section", None)
    st.session_state.pop("reg_administration_section", None)

def _reset_reg_facility():
    st.session_state["reg_facility"] = "-- اختر المنشأة --"

    st.session_state.pop("reg_administration_section", None)

def _reset_hier_admin_and_facility():
    st.session_state["hier_manage_administration"] = "-- اختر الإدارة --"
    st.session_state["hier_manage_facility_id"] = None

def _reset_hier_facility():
    st.session_state["hier_manage_facility_id"] = None

def login_portal():
    header()
    col_v_btn1, col_v_btn2 = st.columns([3, 1])
    with col_v_btn2:
        if st.button("🔍 التحقق من شهادة (QR)", use_container_width=True):
            st.session_state.show_verification_portal = True
            st.rerun()

    hier_data = get_hierarchical_data(include_hidden=False)
    print_st = get_print_settings()
    professions_list = print_st.get("professions_list", ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"])


    if "login_portal_section" not in st.session_state:
        st.session_state.login_portal_section = ""
    st.markdown("<style>div.stButton > button {min-height: 3.2rem; font-weight: 800 !important;} .portal-gap {height: 22px;}</style>", unsafe_allow_html=True)

    if st.button("🔐 تسجيل دخول الامتحان", key="portal_exam_button", use_container_width=True, type="primary" if st.session_state.login_portal_section == "exam" else "secondary"):
        st.session_state.login_portal_section = "" if st.session_state.login_portal_section == "exam" else "exam"
        st.rerun()
    if st.session_state.login_portal_section == "exam":
            st.markdown("### 🔐 التسجيل ودخول الامتحان")
            st.info("بعد اعتماد تسجيلك من الإدارة، أدخل الرقم القومي المسجل فقط.")
            with st.form("trainee_national_id_login", clear_on_submit=True):
                nid_login = st.text_input("الرقم القومي:", max_chars=14, placeholder="أدخل الرقم القومي المسجل")
                if st.form_submit_button("🚪 دخول الامتحان", use_container_width=True):
                    digits_nid = normalize_national_id(nid_login)
                    if not is_valid_egyptian_national_id(digits_nid):
                        st.error("❌ الرقم القومي غير صحيح. أدخل 14 رقماً صحيحة.")
                    else:
                        tr = trainee_by_national_id(digits_nid)
                        if not tr:
                            st.error("❌ لم يتم العثور على تسجيل معتمد بهذا الرقم القومي.")
                        elif not tr.get("assigned_template_id"):
                            st.warning("⏳ تم اعتماد التسجيل، لكن لم يتم تخصيص نموذج امتحان لك بعد.")
                        else:
                            with db() as c:
                                login_tpl = c.execute("SELECT * FROM exam_templates WHERE id=? AND active=1", (tr["assigned_template_id"],)).fetchone()
                            if not login_tpl:
                                st.warning("⏳ نموذج الاختبار المخصص لك غير متاح حالياً. يرجى مراجعة الإدارة.")
                            else:
                                st.session_state.trainee_id = tr["id"]
                                st.session_state.trainee_name = tr["name"]
                                st.rerun()


    st.markdown('<div class="portal-gap"></div>', unsafe_allow_html=True)
    if st.button("📝 تسجيل أول مرة", key="portal_register_button", use_container_width=True, type="primary" if st.session_state.login_portal_section == "register" else "secondary"):
        st.session_state.login_portal_section = "" if st.session_state.login_portal_section == "register" else "register"
        st.rerun()
    if st.session_state.login_portal_section == "register":
            st.markdown("### 📝 تسجيل الممتحن لأول مرة")
            st.info("أدخل بياناتك مرة واحدة. بعد إرسال الطلب سيظهر للإدارة في قسم **قبول تسجيل الجدد**، ولا يمكن دخول الامتحان قبل اعتماد التسجيل.")
            st.markdown("##### 📍 الجهة الإدارية التابع لها:")
            st.text_input("جمهورية مصر العربية", value="جمهورية مصر العربية", disabled=True, key="reg_country_fixed")
            st.text_input("وزارة الصحة والسكان", value="وزارة الصحة والسكان", disabled=True, key="reg_ministry_fixed")
            if not hier_data:
                st.warning("⚠ لا توجد بيانات مسجلة في الهيكل الإداري حالياً. يرجى إضافتها من لوحة التحكم أولاً.")
                facility_final_str = ""
            else:
                auth_codes, dir_section_codes, admin_codes, admin_section_codes, facility_codes = hierarchy_level_codes(hier_data)
                placeholder_auth = "-- اختر المديرية / الجهة --"
                placeholder_ds = "-- اختر قسم المديرية --"
                placeholder_admin = "-- اختر الإدارة --"
                placeholder_as = "-- اختر قسم الإدارة --"
                placeholder_fac = "-- اختر المنشأة --"
                auths_list = hierarchy_ordered_unique(item.get("authority") for item in hier_data if item.get("authority"))
                sel_auth = st.selectbox("المديرية / الجهة:", [placeholder_auth] + auths_list, key="reg_authority", on_change=_reset_reg_admin_and_facility)
                rows_auth = [item for item in hier_data if sel_auth != placeholder_auth and str(item.get("authority") or "").strip() == sel_auth]

                dir_sections_list = hierarchy_ordered_unique(item.get("directorate_section") for item in rows_auth if item.get("directorate_section"))
                if dir_sections_list:
                    sel_dir_section = st.selectbox("قسم المديرية:", [placeholder_ds] + dir_sections_list, key="reg_directorate_section", disabled=not bool(rows_auth))
                    rows_auth = [item for item in rows_auth if sel_dir_section != placeholder_ds and str(item.get("directorate_section") or "").strip() == sel_dir_section]
                else:
                    sel_dir_section = ""

                admins_list = hierarchy_ordered_unique(item.get("administration") for item in rows_auth if item.get("administration"))
                sel_admin = st.selectbox("الإدارة:", [placeholder_admin] + admins_list, key="reg_administration", disabled=not bool(rows_auth), on_change=_reset_reg_facility)
                rows_admin = [item for item in rows_auth if sel_admin != placeholder_admin and str(item.get("administration") or "").strip() == sel_admin]

                admin_sections_list = hierarchy_ordered_unique(item.get("administration_section") for item in rows_admin if item.get("administration_section"))
                if admin_sections_list:
                    sel_admin_section = st.selectbox("قسم الإدارة:", [placeholder_as] + admin_sections_list, key="reg_administration_section", disabled=not bool(rows_admin))
                    rows_admin = [item for item in rows_admin if sel_admin_section != placeholder_as and str(item.get("administration_section") or "").strip() == sel_admin_section]
                else:
                    sel_admin_section = ""

                facilities_list = hierarchy_ordered_unique(item.get("facility_name") for item in rows_admin if item.get("facility_name"))
                sel_fac = st.selectbox("المنشأة / وحدة الأمراض المتوطنة:", [placeholder_fac] + facilities_list, key="reg_facility", disabled=not bool(rows_admin))
                hierarchy_parts = ["جمهورية مصر العربية", "وزارة الصحة والسكان", sel_auth, sel_dir_section, sel_admin, sel_admin_section, sel_fac]
                required_parts = (sel_auth != placeholder_auth and sel_admin != placeholder_admin and sel_fac != placeholder_fac)
                if dir_sections_list:
                    required_parts = required_parts and sel_dir_section != placeholder_ds
                if admin_sections_list:
                    required_parts = required_parts and sel_admin_section != placeholder_as
                facility_final_str = " - ".join(str(part).strip() for part in hierarchy_parts if str(part or "").strip() and str(part).strip() not in {placeholder_auth, placeholder_ds, placeholder_admin, placeholder_as, placeholder_fac}) if required_parts else ""
            with st.form("trainee_first_registration", clear_on_submit=True):
                name = st.text_input("الاسم الرباعي:")
                national_id = st.text_input("الرقم القومي:", max_chars=14, help="يجب أن يكون 14 رقماً.")
                phone = st.text_input("رقم الهاتف:", help="رقم الهاتف هو المعرف الرئيسي والفريد بعد اعتماد التسجيل.")
                selected_profession = st.selectbox("الوظيفة / التخصص:", professions_list)
                work_start_date = st.date_input(
                    "📅 تاريخ استلام العمل:",
                    value=now_cairo().date(),
                    max_value=now_cairo().date(),
                    format="DD/MM/YYYY",
                    help="اختر تاريخ استلام العمل الفعلي."
                )
                if st.form_submit_button("📨 إرسال طلب التسجيل", use_container_width=True):
                    digits_nid = normalize_national_id(national_id)
                    phone_norm = normalize_egyptian_phone(phone)
                    if not facility_final_str:
                        st.warning("⚠ يرجى استكمال اختيار الهيكل الإداري بالكامل.")
                    elif not name.strip() or not phone_norm or not digits_nid:
                        st.warning("⚠ يرجى إدخال الاسم والرقم القومي ورقم الهاتف.")
                    elif not is_valid_egyptian_national_id(digits_nid):
                        st.warning("⚠ الرقم القومي غير صحيح. تأكد من 14 رقماً وتاريخ الميلاد وكود المحافظة.")
                    elif not is_valid_egyptian_mobile(phone_norm):
                        st.warning("⚠ أدخل رقم موبايل مصري صحيحاً مثل 01012345678 أو +201012345678.")
                    elif phone_exists(phone_norm):
                        st.error("❌ رقم الهاتف مستخدم بالفعل لممتحن مسجل. رقم الهاتف يجب أن يكون فريداً.")
                    else:
                        with db() as c:
                            nid_exists = c.execute("SELECT 1 FROM trainees WHERE national_id=? LIMIT 1", (digits_nid,)).fetchone()
                        if nid_exists:
                            st.error("❌ الرقم القومي مستخدم بالفعل في تسجيل سابق.")
                        else:
                            try:
                                tid = create_trainee(
                                    facility_final_str, name, phone_norm, digits_nid,
                                    selected_profession, None, work_start_date.isoformat()
                                )
                                st.success(f"✅ تم إرسال طلب التسجيل بنجاح. رقم الطلب: {tid}. انتظر اعتماد الإدارة.")
                            except ValueError as e:
                                msg = {"DUPLICATE_TRAINEE_PHONE": "رقم الهاتف مستخدم بالفعل.", "DUPLICATE_TRAINEE_NATIONAL_ID": "الرقم القومي مستخدم بالفعل.", "INVALID_TRAINEE_PHONE": "رقم الموبايل المصري غير صحيح.", "INVALID_TRAINEE_NATIONAL_ID": "الرقم القومي غير صحيح."}.get(str(e), str(e))
                                st.error("❌ " + msg)

    with st.expander("🔐 تسجيل دخول الإدارة"):
        with st.form("admin_login_form_hidden", clear_on_submit=True):
            u = st.text_input("اسم المستخدم", value="")
            p = st.text_input("كلمة المرور", type="password", value="")
            if st.form_submit_button("دخول لوحة التحكم", use_container_width=True):
                user = login_user(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.role = user["role"]
                    try:
                        stored_permissions = json.loads(user["permissions_json"]) if user["permissions_json"] else []
                    except:
                        stored_permissions = []

                    st.session_state.permissions = list(ALL_MENU_MODULES.keys()) if user["role"] == "admin" else stored_permissions
                    try:
                        st.session_state.user_hierarchy_scope = json.loads(user.get("hierarchy_scope_json") or "{}") if hasattr(user, "get") else json.loads(user["hierarchy_scope_json"] or "{}")
                    except Exception:
                        st.session_state.user_hierarchy_scope = {}
                    st.rerun()
                else:
                    st.error(st.session_state.get("admin_login_error") or "تعذر تسجيل الدخول. راجع بيانات الحساب.")

def is_owner():
    """المالك/مدير النظام يمتلك صلاحية عليا على جميع أجزاء البرنامج."""
    return str(st.session_state.get("role", "")).strip().lower() == "admin"

def has_permission(module_key):
    """فحص مركزي للصلاحيات: المالك يتجاوز أي قائمة صلاحيات محفوظة."""
    if is_owner():
        return True
    perms = st.session_state.get("permissions") or []
    return module_key in perms or any(subtab_permission_key(module_key, label) in perms for label in SUBTAB_PERMISSION_CATALOG.get(module_key, []))

SUBTAB_PERMISSION_CATALOG = {'📊 لوحة التحكم': ['👥 تحليل التخصصات والوظائف', '🏥 توزيع وحدات الأمراض المتوطنة', '📚 تفاصيل بنك الأسئلة والصعوبة'], '🎨 إعدادات الشهادات المخصصة': ['⚙ إعدادات وتصميم الشهادة', '🖨 طباعة الشهادات بناءً على التقارير (فرد / منشأة)'], '🏥 الهيكل الإداري': ['✍ إضافة يدوية', '📥 رفع الملفات', '📋 استعراض وإخفاء/إظهار/حذف'], '⚙ إدارة الأسئلة': ['➕ إضافة وتعديل وحذف فردي', '🧠 بنك الأسئلة الشامل (استيراد وتصدير وحذف البنك)', '➕ إضافة', '✏ تعديل', '🗑 حذف', '📥 رفع شيت إكسيل ودمج الأسئلة', '📤 تصدير وحذف بنك الأسئلة'], '🧑\u200d🔬 المتدربين والنماذج': ['🆕 قبول المسجلين الجدد', 'جميع المتدربين (إدارة وإخفاء/إظهار/حذف)', '📝 طباعة نموذج امتحان الممتحن'], '✍ التسجيل اليدوي للاختبارات و التقييم الواقعي': ['📝 التسجيل اليدوي للاختبارات', '🏥 التقييم الواقعي للمنشآت'], '📊 التقارير': ['👤 تقرير فردي (لمتدرب مع فلترة ومقارنة فترات)', '🏢 تقرير جماعي (لوحدة متوطنة مع فلترة ومقارنة فترات)', '📋 تقرير النتائج الشامل', '📈 تقرير أداء الجهات', '🏆 عرض النتائج والفلترة والأعلى تقييماً', '🏥 تقارير التقييم الواقعي ومقارنة الفترات'], '📈 خطط العمل': ['➕ إنشاء وتحديث خطة عمل ذكية', '📋 استعراض وإدارة خطط العمل المسجلة', '📄 محاضر التدريب'], '👥 إدارة المستخدمين': ['➕ إضافة مستخدم', '⚙ الصلاحيات والحذف', '🔑 تعديل اسم وكلمة المرور', '🛠 إدارة أسماء الصلاحيات']}

def subtab_permission_key(module_key, tab_label):
    return "@tab|" + str(module_key) + "|" + str(tab_label)

def has_subtab_permission(module_key, tab_label):
    if is_owner():
        return True
    perms = st.session_state.get("permissions") or []

    return module_key in perms or subtab_permission_key(module_key, tab_label) in perms

def require_permission(module_key):
    """منع الوصول المباشر لأي قسم عند عدم امتلاك الصلاحية."""
    if has_permission(module_key):
        return True
    st.error("⛔ ليس لديك صلاحية للوصول إلى هذا القسم.")
    return False

def admin_dashboard():
    header()
    c_info, c_btn = st.columns([4, 1])
    with c_info:
        with db() as _c:
            _display_row = _c.execute("SELECT display_name, job_title FROM users WHERE username=?", (st.session_state.username,)).fetchone()
        _display_name = (_display_row["display_name"] if _display_row else "") or st.session_state.username
        _job_title = (_display_row["job_title"] if _display_row else "") or role_label(st.session_state.role)
        st.write(f"**المستخدم:** {_display_name} | **اسم الدخول:** {st.session_state.username} | **الوظيفة:** {_job_title} | **الصلاحية:** {role_label(st.session_state.role)}")
    with c_btn:
        if st.button("تسجيل الخروج", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.session_state.permissions = []
            st.rerun()
    all_modules_list = list(ALL_MENU_MODULES.keys())

    if is_owner():
        available_menus = all_modules_list
    else:
        available_menus = [m for m in all_modules_list if has_permission(m) or any(subtab_permission_key(m, label) in (st.session_state.get("permissions") or []) for label in SUBTAB_PERMISSION_CATALOG.get(m, []))]
    if not available_menus:
        st.warning("⚠ لا توجد صلاحيات مصرحة.")
        return
    st.markdown("### 📌 لوحة المؤشرات وأقسام الإدارة:")
    cols_per_row = 1
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
        st.subheader("📊 لوحة المؤشرات العامة والتحليلات الشاملة للأمراض المتوطنة")
        dash_scope = current_user_trainee_scope()
        dash_pred, dash_args = hierarchy_filter_for_trainees(dash_scope, "t")
        with db() as c:
            cnts = c.execute(f"""SELECT 
                (SELECT COUNT(*) FROM trainees t WHERE t.hidden=0 AND {dash_pred}) tr,
                (SELECT COUNT(*) FROM trainees t WHERE t.status='pending' AND t.hidden=0 AND {dash_pred}) pend,
                (SELECT COUNT(*) FROM trainees t WHERE t.status='approved' AND t.hidden=0 AND {dash_pred}) appr,
                (SELECT COUNT(*) FROM trainees t WHERE t.status='completed' AND t.hidden=0 AND {dash_pred}) comp,
                (SELECT COUNT(*) FROM questions WHERE active=1) qs,
                (SELECT COUNT(*) FROM exam_templates WHERE active=1) tpls,
                (SELECT COUNT(*) FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.status='submitted' AND t.hidden=0 AND {dash_pred}) ex,
                (SELECT COALESCE(AVG(s.percent),0) FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.status='submitted' AND t.hidden=0 AND {dash_pred}) avgp,
                (SELECT COUNT(*) FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id WHERE s.status='submitted' AND s.passed=1 AND t.hidden=0 AND {dash_pred}) passed_cnt,
                (SELECT COUNT(DISTINCT TRIM(authority)) FROM hierarchical_facilities WHERE hidden=0 AND COALESCE(TRIM(authority),'')<>'') authorities_cnt,
                (SELECT COUNT(DISTINCT TRIM(authority) || '||' || TRIM(administration)) FROM hierarchical_facilities WHERE hidden=0 AND COALESCE(TRIM(authority),'')<>'' AND COALESCE(TRIM(administration),'')<>'') administrations_cnt,
                (SELECT COUNT(DISTINCT TRIM(authority) || '||' || TRIM(administration) || '||' || TRIM(facility_name)) FROM hierarchical_facilities WHERE hidden=0 AND COALESCE(TRIM(authority),'')<>'' AND COALESCE(TRIM(administration),'')<>'' AND COALESCE(TRIM(facility_name),'')<>'') facilities_cnt
            """, tuple(dash_args * 7)).fetchone()
        total_tr = cnts["tr"] or 1
        passed_cnt = cnts["passed_cnt"] or 0
        pass_ratio = (passed_cnt / total_tr) * 100
        st.markdown("##### 🚀 المؤشرات الرئيسية (KPIs):")
        cols = st.columns(5)
        metrics_data = [
            ("إجمالي المتدربين", cnts["tr"]),
            ("الطلبات المعلقة", cnts["pend"]),
            ("المتدربين المعتمدين", cnts["appr"]),
            ("الاختبارات المكتملة", cnts["comp"]),
            ("بنك الأسئلة الشامل", cnts["qs"])
        ]
        for box, (l, v) in zip(cols, metrics_data):
            box.markdown(f'<div class="metric"><div class="v">{v}</div><div class="l">{l}</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        cols_sub = st.columns(4)
        sub_metrics = [
            ("النماذج المتاحة", cnts["tpls"]),
            ("متوسط النسبة العام", f"{cnts['avgp']:.1f}%"),
            ("نسبة النجاح العامة", f"{pass_ratio:.1f}%")
        ]
        for box, (l, v) in zip([cols_sub[0], cols_sub[2], cols_sub[3]], sub_metrics):
            box.markdown(f'<div class="metric"><div class="v">{v}</div><div class="l">{l}</div></div>', unsafe_allow_html=True)
        cols_sub[1].markdown(f'<div class="metric"><div class="v">{cnts["facilities_cnt"]}</div><div class="l">المنشآت</div></div>', unsafe_allow_html=True)
        st.markdown("##### 🏥 توزيع الهيكل الإداري:")
        hierarchy_cols = st.columns(3)
        hierarchy_metrics = [
            ("مديريات / هيئات", cnts["authorities_cnt"]),
            ("إدارات", cnts["administrations_cnt"]),
            ("منشآت", cnts["facilities_cnt"]),
        ]
        for box, (label, value) in zip(hierarchy_cols, hierarchy_metrics):
            box.markdown(f'<div class="metric"><div class="v">{value}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("### 📈 تحليلات إضافية وتفصيلية:")
        tab_db_1, tab_db_2, tab_db_3, tab_db_hierarchy = st.tabs(["👥 تحليل التخصصات والوظائف", "🏥 توزيع وحدات الأمراض المتوطنة", "📚 تفاصيل بنك الأسئلة والصعوبة", "🏢 مؤشرات حسب الهيكل الإداري"])
        with tab_db_1:
            if has_subtab_permission('📊 لوحة التحكم', '👥 تحليل التخصصات والوظائف'):
                with db() as c:
                    dash_pred_prof, dash_args_prof = hierarchy_filter_for_trainees(current_user_trainee_scope(), "t")
                    df_prof_analysis = pd.read_sql_query(f"""
                        SELECT t.profession AS 'الوظيفة / التخصص', COUNT(t.id) AS 'إجمالي العاملين',
                               SUM(CASE WHEN t.status='completed' THEN 1 ELSE 0 END) AS 'المكتملين للاختبار',
                               SUM(CASE WHEN t.status='pending' THEN 1 ELSE 0 END) AS 'قيد الانتظار'
                        FROM trainees t WHERE t.hidden=0 AND {dash_pred_prof} GROUP BY t.profession ORDER BY COUNT(t.id) DESC
                    """, c, params=dash_args_prof)
                if df_prof_analysis.empty:
                    st.info("لا توجد بيانات متدربين مسجلة لتحليلها.")
                else:
                    st.dataframe(df_prof_analysis, use_container_width=True, hide_index=True)
        with tab_db_2:
            if has_subtab_permission('📊 لوحة التحكم', '🏥 توزيع وحدات الأمراض المتوطنة'):
                with db() as c:
                    dash_pred_fac, dash_args_fac = hierarchy_filter_for_trainees(current_user_trainee_scope(), "t")
                    df_fac_analysis = pd.read_sql_query(f"""
                        SELECT t.facility AS 'وحدة الأمراض المتوطنة / المنشأة', COUNT(t.id) AS 'عدد العاملين',
                               SUM(CASE WHEN s.passed=1 THEN 1 ELSE 0 END) AS 'عدد المجتازين',
                               COALESCE(AVG(s.percent), 0) AS 'متوسط نسبة النجاح %'
                        FROM trainees t LEFT JOIN exam_sessions s ON s.trainee_id=t.id AND s.status='submitted'
                        WHERE t.hidden=0 AND {dash_pred_fac} GROUP BY t.facility ORDER BY COUNT(t.id) DESC
                    """, c, params=dash_args_fac)
                if df_fac_analysis.empty:
                    st.info("لا توجد بيانات منشآت مسجلة.")
                else:
                    st.dataframe(df_fac_analysis, use_container_width=True, hide_index=True)
        with tab_db_hierarchy:
            if has_subtab_permission('📊 لوحة التحكم', '🏢 مؤشرات حسب الهيكل الإداري') or is_owner():
                st.markdown("#### 🏢 مؤشرات الهيكل الإداري")
                st.caption("الأعداد التالية مستقاة من الهيكل الإداري المسجل، مع عرض كل مستوى على حدة وبالتسلسل الإداري.")
                with db() as c:
                    df_authorities = pd.read_sql_query("""
                        SELECT TRIM(authority) AS 'المديرية / الهيئة', COUNT(DISTINCT NULLIF(TRIM(administration),'')) AS 'عدد الإدارات',
                               COUNT(DISTINCT CASE WHEN TRIM(COALESCE(facility_name,''))<>'' THEN TRIM(authority)||'|'||TRIM(administration)||'|'||TRIM(facility_name) END) AS 'عدد المنشآت'
                        FROM hierarchical_facilities
                        WHERE hidden=0 AND TRIM(COALESCE(authority,''))<>''
                        GROUP BY TRIM(authority) ORDER BY MIN(id)
                    """, c)
                    df_administrations = pd.read_sql_query("""
                        SELECT TRIM(authority) AS 'المديرية / الهيئة', TRIM(administration) AS 'الإدارة',
                               COUNT(DISTINCT CASE WHEN TRIM(COALESCE(facility_name,''))<>'' THEN TRIM(facility_name) END) AS 'عدد المنشآت'
                        FROM hierarchical_facilities
                        WHERE hidden=0 AND TRIM(COALESCE(authority,''))<>'' AND TRIM(COALESCE(administration,''))<>''
                        GROUP BY TRIM(authority), TRIM(administration) ORDER BY MIN(id)
                    """, c)
                    df_facilities = pd.read_sql_query("""
                        SELECT TRIM(authority) AS 'المديرية / الهيئة', TRIM(administration) AS 'الإدارة', TRIM(facility_name) AS 'المنشأة'
                        FROM hierarchical_facilities
                        WHERE hidden=0 AND TRIM(COALESCE(authority,''))<>'' AND TRIM(COALESCE(administration,''))<>'' AND TRIM(COALESCE(facility_name,''))<>''
                        GROUP BY TRIM(authority), TRIM(administration), TRIM(facility_name) ORDER BY MIN(id)
                    """, c)
                st.markdown("##### المديريات / الهيئات")
                st.metric("إجمالي المديريات / الهيئات", len(df_authorities))
                if df_authorities.empty:
                    st.info("لا توجد مديريات أو هيئات مسجلة.")
                else:
                    st.dataframe(df_authorities, use_container_width=True, hide_index=True)
                st.markdown("##### الإدارات")
                st.metric("إجمالي الإدارات", len(df_administrations))
                if df_administrations.empty:
                    st.info("لا توجد إدارات مسجلة.")
                else:
                    st.dataframe(df_administrations, use_container_width=True, hide_index=True)
                st.markdown("##### المنشآت")
                st.metric("إجمالي المنشآت", len(df_facilities))
                if df_facilities.empty:
                    st.info("لا توجد منشآت مسجلة.")
                else:
                    st.dataframe(df_facilities, use_container_width=True, hide_index=True)
            else:
                st.info("لا تتوفر لديك صلاحية عرض مؤشرات الهيكل الإداري.")
        with tab_db_3:
            if has_subtab_permission('📊 لوحة التحكم', '📚 تفاصيل بنك الأسئلة والصعوبة'):
                with db() as c:
                    df_q_analysis = pd.read_sql_query("""
                        SELECT difficulty AS 'مستوى الصعوبة', category AS 'المجال / القسم', COUNT(id) AS 'عدد الأسئلة'
                        FROM questions WHERE active=1 GROUP BY difficulty, category ORDER BY COUNT(id) DESC
                    """, c)
                    df_q_category = pd.read_sql_query("""
                        SELECT COALESCE(NULLIF(TRIM(category), ''), 'غير مصنف') AS 'التصنيف / القسم',
                               COUNT(id) AS 'عدد الأسئلة'
                        FROM questions
                        WHERE active=1
                        GROUP BY COALESCE(NULLIF(TRIM(category), ''), 'غير مصنف')
                        ORDER BY COUNT(id) DESC, 'التصنيف / القسم' ASC
                    """, c)
                if df_q_analysis.empty:
                    st.info("بنك الأسئلة فارغ حالياً.")
                else:
                    st.markdown("#### 📚 توزيع بنك الأسئلة حسب مستوى الصعوبة والتصنيف:")
                    st.dataframe(df_q_analysis, use_container_width=True, hide_index=True)

                    st.markdown("---")
                    st.markdown("#### 🗂️ عدد الأسئلة في كل تصنيف داخل بنك الأسئلة:")
                    st.caption("يتم الحساب من الأسئلة النشطة فقط، مع تجميع كل الأسئلة التي تحمل نفس اسم التصنيف.")

                    total_category_questions = int(df_q_category['عدد الأسئلة'].sum())
                    category_count = len(df_q_category)
                    c1, c2 = st.columns(2)
                    c1.metric("إجمالي الأسئلة المصنفة", total_category_questions)
                    c2.metric("عدد التصنيفات", category_count)

                    st.dataframe(df_q_category, use_container_width=True, hide_index=True)


    elif selected_menu == "👥 إدارة المهن والوظائف":
        st.subheader("👥 إدارة الوظائف والتخصصات بالأمراض المتوطنة (مع إمكانية الحذف)")
        st.info("💡 يمكنك من هنا إضافة وظيفة أو تخصص جديد أو حذف تخصص موجود، واستعراض توزيع العاملين حسب وظائفهم.")
        curr_p_set = get_print_settings()
        current_prof_list = curr_p_set.get("professions_list", [])
        col_add_prof, col_list_prof = st.columns(2)
        with col_add_prof:
            with st.form("add_new_profession_form", clear_on_submit=True):
                st.markdown("#### ➕ إضافة وظيفة أو تخصص جديد:")
                new_prof_input = st.text_input("اسم الوظيفة أو التخصص:", value="")
                if st.form_submit_button("💾 حفظ وإضافة الوظيفة", use_container_width=True):
                    clean_p = new_prof_input.strip()
                    if clean_p:
                        if clean_p not in current_prof_list:
                            current_prof_list.append(clean_p)
                            save_print_settings(
                                curr_p_set["header_text"], curr_p_set["margin_top"], curr_p_set["margin_bottom"],
                                curr_p_set["margin_right"], curr_p_set["margin_left"], curr_p_set.get("line_spacing", 1.25),
                                curr_p_set["logo_base64"], curr_p_set.get("logo2_base64", ""), curr_p_set.get("logo3_base64", ""),
                                curr_p_set.get("bg_base64", ""), curr_p_set.get("frame_base64", ""),
                                curr_p_set["default_cert_title"], curr_p_set["default_cert_notes"],
                                curr_p_set["trainee_prefix"], curr_p_set["trainee_title"], curr_p_set["trainee_profession"], current_prof_list
                            )
                            st.success(f"✅ تمت إضافة الوظيفة ({clean_p}) بنجاح للقائمة المنسدلة!")
                            st.rerun()
                        else:
                            st.warning("⚠ هذه الوظيفة موجودة مسبقاً في القائمة.")
                    else:
                        st.warning("الرجاء إدخال اسم الوظيفة.")
        with col_list_prof:
            with st.form("delete_profession_form", clear_on_submit=True):
                st.markdown("#### 🗑 حذف وظيفة من القائمة:")
                sel_del_prof = st.selectbox("اختر الوظيفة للحذف:", ["-- اختر الوظيفة --"] + current_prof_list)
                if st.form_submit_button("حذف الوظيفة المحددة", use_container_width=True):
                    if sel_del_prof != "-- اختر الوظيفة --":
                        if sel_del_prof in current_prof_list:
                            current_prof_list.remove(sel_del_prof)
                            save_print_settings(
                                curr_p_set["header_text"], curr_p_set["margin_top"], curr_p_set["margin_bottom"],
                                curr_p_set["margin_right"], curr_p_set["margin_left"], curr_p_set.get("line_spacing", 1.25),
                                curr_p_set["logo_base64"], curr_p_set.get("logo2_base64", ""), curr_p_set.get("logo3_base64", ""),
                                curr_p_set.get("bg_base64", ""), curr_p_set.get("frame_base64", ""),
                                curr_p_set["default_cert_title"], curr_p_set["default_cert_notes"],
                                curr_p_set["trainee_prefix"], curr_p_set["trainee_title"], curr_p_set["trainee_profession"], current_prof_list
                            )
                            st.success(f"✅ تم حذف الوظيفة ({sel_del_prof}) بنجاح!")
                            st.rerun()
                    else:
                        st.warning("الرجاء اختيار وظيفة صحيحة للحذف.")
            st.markdown("#### 📋 القائمة الحالية للوظائف المتاحة:")
            for idx, p_name in enumerate(current_prof_list, start=1):
                st.write(f"{idx}. {p_name}")
        st.markdown("---")
        st.markdown("#### 📊 تقسيم وإحصائيات العاملين والممتحنين حسب التخصصات:")
        with db() as c:
            prof_scope_pred, prof_scope_args = hierarchy_filter_for_trainees(current_user_trainee_scope(), "t")
            df_prof_stats = pd.read_sql_query(f"""
                SELECT t.profession AS 'الوظيفة / التخصص', COUNT(t.id) AS 'إجمالي العاملين',
                       SUM(CASE WHEN t.status='completed' THEN 1 ELSE 0 END) AS 'المكتملين للاختبار'
                FROM trainees t WHERE t.hidden=0 AND {prof_scope_pred} GROUP BY t.profession ORDER BY COUNT(t.id) DESC
            """, c, params=prof_scope_args)
        if df_prof_stats.empty:
            st.info("لا توجد بيانات متدربين مسجلة حتى الآن.")
        else:
            df_prof_stats.columns = ["الوظيفة / التخصص", "إجمالي العاملين", "المكتملين للاختبار"]
            st.dataframe(df_prof_stats, use_container_width=True, hide_index=True)
            out_prof_bytes = io.BytesIO()
            with pd.ExcelWriter(out_prof_bytes, engine='openpyxl') as writer:
                df_prof_stats.to_excel(writer, index=False, sheet_name='ProfessionsBreakdown')
            st.download_button("📥 تحميل تقرير وتوزيع التخصصات (.xlsx)", data=out_prof_bytes.getvalue(), file_name="professions_breakdown.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    elif selected_menu == "🖨 ضبط اعدادات الطباعة و الهوامش":
        st.subheader("🖨 إعدادات الطباعة العامة والهيكل الإداري")
        current_set = get_print_settings()
        hierarchy_rows_for_reports = get_hierarchical_data()
        def _report_hierarchy_label(item):
            parts = [str(item.get(k) or "").strip() for k in ("authority", "directorate_section", "administration", "administration_section", "facility_name") if str(item.get(k) or "").strip()]
            return " — ".join(parts) if parts else "هيكل إداري غير محدد"
        hierarchy_options_for_reports = {"كل الهيكل الإداري (بدون تحديد جهة مستهدفة)": {}}
        for _hrow in hierarchy_rows_for_reports:
            _report_label = _report_hierarchy_label(_hrow)
            if _report_label in hierarchy_options_for_reports:
                _report_label += f" (سجل {_hrow.get('id', '')})"
            hierarchy_options_for_reports[_report_label] = {k: _hrow.get(k, "") or "" for k in ("governorate", "authority", "center", "directorate_section", "administration", "administration_section", "facility_name")}
        try:
            saved_report_hierarchy = json.loads(current_set.get("report_hierarchy_json", "{}") or "{}")
        except Exception:
            saved_report_hierarchy = {}
        saved_report_label = next((lab for lab, val in hierarchy_options_for_reports.items() if val == saved_report_hierarchy), "كل الهيكل الإداري (بدون تحديد جهة مستهدفة)")
        st.markdown("#### 🏢 نطاق الجهة المستهدفة في المطبوعات العامة")
        report_hierarchy_label = st.selectbox("اختر الجهة أو المستوى الإداري:", list(hierarchy_options_for_reports.keys()), index=list(hierarchy_options_for_reports.keys()).index(saved_report_label), key="print_report_hierarchy_select", help="يُستخدم الاختيار لتحديد الجهة المستهدفة وتسلسل الهيكل في المطبوعات العامة.")
        report_hierarchy_val = hierarchy_options_for_reports[report_hierarchy_label]
        st.markdown("---")
        st.markdown("#### 🏷️ شعارات الهيكل الإداري")
        st.caption("ارفع شعارات الجهة المحددة هنا. تُحفظ لكل مستوى إداري بصورة مستقلة وتُستخدم تلقائيًا في المطبوعات العامة التي تستهدف هذا المستوى، دون التأثير على شعارات الجهات الأخرى. إعدادات الشهادات تبقى منفصلة.")
        logo_scope_options = {label: value for label, value in hierarchy_options_for_reports.items() if value}
        if logo_scope_options:
            logo_scope_labels = list(logo_scope_options.keys())
            default_logo_label = report_hierarchy_label if report_hierarchy_label in logo_scope_options else logo_scope_labels[0]
            logo_scope_label = st.selectbox("الجهة التي تريد إدارة شعاراتها:", logo_scope_labels, index=logo_scope_labels.index(default_logo_label), key="hierarchy_logo_scope_select")
            logo_scope = logo_scope_options[logo_scope_label]
            scope_for_logo = {"scope_governorate": logo_scope.get("governorate", ""), "scope_authority": logo_scope.get("authority", ""), "scope_center": logo_scope.get("center", ""), "scope_directorate_section": logo_scope.get("directorate_section", ""), "scope_administration": logo_scope.get("administration", ""), "scope_administration_section": logo_scope.get("administration_section", ""), "scope_facility": logo_scope.get("facility_name", "")}
            existing_logos = get_hierarchy_print_logos(scope_for_logo)
            # Load exact-scope logos rather than inherited fallback logos, so one level never overwrites another.
            try:
                with get_conn() as _logo_conn:
                    _saved_logo_row = _logo_conn.execute("SELECT logo1_base64,logo2_base64,logo3_base64 FROM hierarchy_print_logos WHERE scope_key=?", (_logo_scope_key(scope_for_logo),)).fetchone()
                exact_logos = list(_saved_logo_row) if _saved_logo_row else ["", "", ""]
            except Exception:
                exact_logos = ["", "", ""]
            logo_cols = st.columns(3)
            uploaded_logos = []
            for _idx, (_col, _label) in enumerate(zip(logo_cols, ("الشعار الأول", "الشعار الثاني", "الشعار الثالث"))):
                with _col:
                    if exact_logos[_idx]:
                        st.image(exact_logos[_idx], caption=f"{_label} الحالي", width=110)
                    _upload = st.file_uploader(f"رفع {_label}", type=["png", "jpg", "jpeg", "webp"], key=f"hierarchy_logo_upload_{_idx}_{hash(_logo_scope_key(scope_for_logo))}")
                    uploaded_logos.append(_upload)
            _save_col, _delete_col = st.columns(2)
            with _save_col:
                if st.button("💾 حفظ شعارات الجهة المحددة", use_container_width=True, key="save_hierarchy_logos_button"):
                    new_logos = list(exact_logos)
                    for _idx, _upload in enumerate(uploaded_logos):
                        if _upload is not None:
                            new_logos[_idx] = "data:" + _upload.type + ";base64," + base64.b64encode(_upload.getvalue()).decode("ascii")
                    save_hierarchy_print_logos(scope_for_logo, new_logos)
                    st.success("تم حفظ الشعارات لهذا المستوى الإداري فقط، وستُستخدم تلقائيًا في المطبوعات.")
                    st.rerun()
            with _delete_col:
                if st.button("🗑️ حذف شعارات الجهة المحددة", use_container_width=True, key="delete_hierarchy_logos_button"):
                    with get_conn() as _logo_conn:
                        _logo_conn.execute("DELETE FROM hierarchy_print_logos WHERE scope_key=?", (_logo_scope_key(scope_for_logo),))
                    st.success("تم حذف الشعارات الخاصة بهذا المستوى فقط.")
                    st.rerun()
        else:
            st.info("أضف أجزاء الهيكل الإداري أولًا حتى تتمكن من تخصيص الشعارات لكل جهة.")
        st.markdown("---")
        st.markdown("#### ⚙️ إعداد عام")
        line_spacing_val = st.number_input("تباعد الأسطر الأساسي للمستندات غير المحدد لها إعداد خاص:", min_value=0.8, max_value=3.0, value=float(current_set.get("line_spacing", 1.25)), step=0.05, key="print_general_line_spacing")
        if st.button("💾 حفظ إعدادات الطباعة العامة", use_container_width=True, key="save_general_print_settings"):
            save_print_settings(
                "", "12mm", "auto", "8mm", "8mm", line_spacing_val,
                current_set.get("logo_base64", DEFAULT_LOGO) or "", current_set.get("logo2_base64", "") or "", current_set.get("logo3_base64", "") or "",
                current_set.get("bg_base64", ""), current_set.get("frame_base64", ""),
                current_set["default_cert_title"], current_set["default_cert_notes"],
                current_set["trainee_prefix"], current_set["trainee_title"], current_set["trainee_profession"],
                current_set.get("professions_list", []), cert_hierarchy=current_set.get("cert_hierarchy_json", "{}"), report_hierarchy=report_hierarchy_val,
                paper_print_settings=current_set.get("paper_print_settings_json", current_set.get("paper_print_settings", {}))
            )
            st.success("تم حفظ إعدادات الطباعة العامة والجهة المستهدفة.")
            st.rerun()

    elif selected_menu == "🎨 إعدادات الشهادات المخصصة":
        st.subheader("🎨 صفحة إدارة وضبط الشهادات المخصصة وطباعتها")
        cert_sub_tab1, cert_sub_tab2 = st.tabs([
            "⚙ إعدادات وتصميم الشهادة",
            "🖨 طباعة الشهادات بناءً على التقارير (فرد / منشأة)"
        ])
        with cert_sub_tab1:
            if has_subtab_permission('🎨 إعدادات الشهادات المخصصة', '⚙ إعدادات وتصميم الشهادة'):
                st.info("💡 هذه الصفحة مخصصة بالكامل لضبط تصميم الشهادة، الألقاب، المسافات، الخلفية، والشعارات بمعزل عن باقي التقارير.")
                current_set = get_print_settings()
                professions_options_list = current_set.get("professions_list", [
                    "أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"
                ])
                # Legacy database field retained for compatibility; no certificate print header is used.
                cert_hierarchy_val = {}
                with st.form("dedicated_certificate_settings_form", clear_on_submit=False):
                    st.markdown("#### 🏷️ إعدادات الألقاب والوظيفة في الشهادة:")
                    col_p1, col_p2, col_p3 = st.columns(3)
                    with col_p1:
                        trainee_prefix_val = st.text_input("1. البادئة قبل الاسم (مثل: الزميل / الأستاذ):", value=current_set.get("trainee_prefix", ""))
                    with col_p2:
                        trainee_title_val = st.text_input("2. اللقب (يظهر أمام الاسم مباشرة):", value=current_set.get("trainee_title", "دكتور"))
                    with col_p3:
                        curr_prof = current_set.get("trainee_profession", "أخصائي الأمراض المتوطنة")
                        prof_idx = professions_options_list.index(curr_prof) if curr_prof in professions_options_list else 0
                        trainee_profession_val = st.selectbox("3. اختيار الوظيفة الافتراضية للشهادات:", professions_options_list, index=prof_idx)
                    cert_trainee_extra_val = st.text_input(
                        "4. نص إضافي لشهادة المتدرب (يظهر بعد سطر الوظيفة والمنشأة):",
                        value=current_set.get("cert_trainee_extra", ""),
                        placeholder="مثال: أتم حضور الدورة التدريبية بنجاح"
                    )
                    cert_facility_extra_val = st.text_input(
                        "5. نص إضافي لشهادة المنشأة (يظهر بعد سطر اسم المنشأة):",
                        value=current_set.get("cert_facility_extra", ""),
                        placeholder="مثال: اجتازت المنشأة متطلبات التقييم"
                    )
                    cert_facility_section_val = st.text_input(
                        "6. تصنيف القسم في شهادة المنشأة (يظهر قبل اسم المنشأة):",
                        value=current_set.get("cert_facility_section", ""),
                        placeholder="مثال: قسم المتوطنة"
                    )
                    st.markdown("#### 📐 التحكم بالمسافات بين الأسطر وتخطيط الشهادة:")
                    line_spacing_val = st.number_input("المسافة بين الأسطر داخل الشهادة:", min_value=0.8, max_value=3.0, value=float(current_set.get("line_spacing", 1.25)), step=0.05)
                    cert_box_inset_val = st.number_input(
                        "📐 حجم مربع محتوى الشهادة داخل صورة الخلفية (المسافة من الإطار):",
                        min_value=4.0, max_value=35.0,
                        value=float(str(current_set.get("cert_box_inset", "13mm")).replace("mm", "").strip() or 13),
                        step=0.5,
                        help="كلما زادت القيمة صغر مربع المحتوى وابتعد عن إطار الصورة. كلما قلت كبر مربع المحتوى واقترب من الإطار."
                    )
                    cert_box_inset_css = f"{cert_box_inset_val:g}mm"
                
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
                
                    st.markdown("#### 🖼 خلفية الشهادة:")
                    uploaded_bg = st.file_uploader("رفع خلفية الشهادة (صورة):", type=["png", "jpg", "jpeg"], key="cert_bg")
                    remove_bg = st.checkbox("حذف الخلفية الحالية", key="c_rem_bg")
                
                    current_logo1_val = current_set["logo_base64"]
                    if remove_logo1:
                        current_logo1_val = DEFAULT_LOGO
                    elif uploaded_logo1 is not None:
                        current_logo1_val = f"data:image/{uploaded_logo1.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo1.read()).decode("utf-8")
                
                    current_logo2_val = current_set.get("logo2_base64", "")
                    if remove_logo2:
                        current_logo2_val = ""
                    elif uploaded_logo2 is not None:
                        current_logo2_val = f"data:image/{uploaded_logo2.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo2.read()).decode("utf-8")
                
                    current_logo3_val = current_set.get("logo3_base64", "")
                    if remove_logo3:
                        current_logo3_val = ""
                    elif uploaded_logo3 is not None:
                        current_logo3_val = f"data:image/{uploaded_logo3.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_logo3.read()).decode("utf-8")
                
                    current_bg_val = current_set.get("bg_base64", "")
                    if remove_bg:
                        current_bg_val = ""
                    elif uploaded_bg is not None:
                        current_bg_val = f"data:image/{uploaded_bg.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_bg.read()).decode("utf-8")
                
                    current_frame_val = current_set.get("frame_base64", "")
                
                    if st.form_submit_button("💾 حفظ إعدادات الشهادة المخصصة", use_container_width=True):
                        save_print_settings(
                            current_set["header_text"], current_set["margin_top"], "auto",
                            current_set["margin_right"], current_set["margin_left"], line_spacing_val,
                            current_logo1_val, current_logo2_val, current_logo3_val,
                            current_bg_val, current_frame_val,
                            current_set["default_cert_title"], current_set["default_cert_notes"],
                            trainee_prefix_val, trainee_title_val, trainee_profession_val, professions_options_list,
                            cert_box_inset_css, cert_trainee_extra_val, cert_facility_extra_val, cert_facility_section_val,
                            cert_hierarchy_val
                        )
                        st.success("✅ تم تحديث وحفظ ضبط الشهادات المخصصة بنجاح!")
                        st.rerun()

        with cert_sub_tab2:
            if has_subtab_permission('🎨 إعدادات الشهادات المخصصة', '🖨 طباعة الشهادات بناءً على التقارير (فرد / منشأة)'):
                st.markdown("#### 🖨 طباعة الشهادات بناءً على التقارير")
                st.info("اختر طباعة شهادة فردية لمتدرب، أو شهادة تقييم للمنشأة بناءً على نتائج التقارير المعتمدة.")
                st.markdown("#### 🏥 تحديد نطاق الشهادات حسب الهيكل الإداري")
                cert_scope = hierarchy_scope_widget("نطاق الشهادات:", "cert_scope_v12")
                cert_scope_sql, cert_scope_args = hierarchy_scope_sql("h", cert_scope)
                with db() as c:
                    all_facilities_list = [row[0] for row in c.execute(
                        f"SELECT DISTINCT t.facility FROM trainees t LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name) WHERE t.facility IS NOT NULL AND t.facility != '' AND t.hidden=0 AND {cert_scope_sql} ORDER BY t.facility",
                        tuple(cert_scope_args)
                    ).fetchall()]
                    sessions_full_list = c.execute("""SELECT s.id, t.name trainee_name, t.facility, t.profession trainee_profession,
                        s.score, s.max_score, s.percent, s.passed, e.name as tpl_name, e.exam_type
                        FROM exam_sessions s
                        JOIN trainees t ON t.id=s.trainee_id
                        LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name)
                        LEFT JOIN exam_templates e ON e.id=s.template_id
                        WHERE s.status='submitted' AND t.hidden=0 AND {cert_scope_sql} ORDER BY s.id DESC""".format(cert_scope_sql=cert_scope_sql), tuple(cert_scope_args)).fetchall()

                if not sessions_full_list:
                    st.info("لا توجد اختبارات مكتملة أو معتمدة للمتدربين الظاهرين حتى الآن.")
                else:
                    cert_print_type = st.radio(
                        "اختر نوع الشهادة:",
                        ["شهادة فردية (لمتدرب محدد)", "شهادة تقييم منشأة"],
                        horizontal=True
                    )
                    curr_sett = get_print_settings()

                    if cert_print_type == "شهادة فردية (لمتدرب محدد)":
                        sess_choices = {
                            f"متدرب: {s['trainee_name']} | الوظيفة: {s['trainee_profession']} | الجهة: {s['facility']} | النتيجة: {s['percent']}%": s['id']
                            for s in sessions_full_list
                        }
                        sel_sess_lbl = st.selectbox("اختر المتدرب للطباعة الفردية:", list(sess_choices.keys()))
                        chosen_sid_val = sess_choices[sel_sess_lbl]
                        cert_html_ind = generate_customizable_certificate_html(
                            chosen_sid_val,
                            curr_sett.get("default_cert_title"),
                            None
                        )
                        render_print_button_only(cert_html_ind, f"شهادة متدرب رقم {chosen_sid_val}")

                    else:
                        if not all_facilities_list:
                            st.info("لا توجد منشآت مسجلة.")
                        else:
                            sel_fac_print = st.selectbox("اختر المنشأة لإصدار شهادة تقييم لها:", all_facilities_list)
                            fac_filtered_sessions = [s for s in sessions_full_list if s['facility'] == sel_fac_print]
                            st.write(f"📊 عدد النتائج المعتمدة للمنشأة: **{len(fac_filtered_sessions)}**")
                            if fac_filtered_sessions:
                                facility_html = generate_facility_certificate_html(
                                    sel_fac_print,
                                    [s['id'] for s in fac_filtered_sessions],
                                    "شهادة تقييم منشأة"
                                )
                                render_print_button_only(facility_html, f"شهادة تقييم منشأة {sel_fac_print}")
                            else:
                                st.warning("⚠ لا توجد نتائج معتمدة لهذه المنشأة.")

    elif selected_menu == "🏥 الهيكل الإداري":
        st.subheader("🏥 إدارة الهيكل الإداري (مديرية / جهة ⬅ قسم المديرية ⬅ إدارة ⬅ قسم الإدارة ⬅ منشأة)")
        tab_h1, tab_h2, tab_h3 = st.tabs(["✍ إضافة يدوية", "📥 رفع الملفات", "📋 استعراض وإخفاء/إظهار/حذف"])
        with tab_h1:
            if has_subtab_permission('🏥 الهيكل الإداري', '✍ إضافة يدوية'):
                # Audit the existing legacy path rows against the mandatory hierarchy chain.
                with db() as _audit_conn:
                    _audit_rows = [dict(_r) for _r in _audit_conn.execute("SELECT authority,directorate_section,administration,administration_section,facility_name FROM hierarchical_facilities WHERE COALESCE(hidden,0)=0").fetchall()]
                _missing_directorate_section = hierarchy_ordered_unique(
                    f"{_r.get('authority')} — {_r.get('administration')}" for _r in _audit_rows
                    if str(_r.get('administration') or '').strip() and not str(_r.get('directorate_section') or '').strip()
                )
                _missing_admin_section = hierarchy_ordered_unique(
                    f"{_r.get('authority')} — {_r.get('administration')} — {_r.get('facility_name')}" for _r in _audit_rows
                    if str(_r.get('facility_name') or '').strip() and not str(_r.get('administration_section') or '').strip()
                )
                if _missing_directorate_section or _missing_admin_section:
                    with st.expander("⚠️ مراجعة اكتمال روابط الهيكل الإداري", expanded=True):
                        st.warning("توجد سجلات قديمة لا تستكمل سلسلة التبعية المطلوبة؛ ستظل محفوظة في الإدارة، لكنها لن تظهر كاختيارات صالحة في الصفحات التابعة حتى ربطها بالأقسام الصحيحة.")
                        if _missing_directorate_section:
                            st.markdown("**إدارات تحتاج ربطًا بقسم مديرية:**")
                            st.write("، ".join(_missing_directorate_section))
                        if _missing_admin_section:
                            st.markdown("**منشآت تحتاج ربطًا بقسم إدارة:**")
                            st.write("، ".join(_missing_admin_section))
                        st.caption("لربط سجل موجود، أضف قسم المديرية/الإدارة أولًا، ثم أضف الإدارة/المنشأة نفسها مرة أخرى مع اختيار القسم الصحيح. سيُضاف الارتباط دون حذف ارتباطاتها الأخرى.")
                st.markdown("##### 📌 إضافة مستوى جديد تحت الجهة الأعلى")
                current_hier = get_hierarchical_data(include_hidden=True)
                add_level = st.selectbox("المستوى المراد إضافته:", ["مديرية / جهة", "قسم داخل المديرية", "إدارة", "قسم داخل الإدارة", "منشأة / وحدة الأمراض المتوطنة"], key="hier_add_level")
                auth_values = hierarchy_ordered_unique(r.get("authority") for r in current_hier)
                parent_sections = []
                parent_admin_sections = []
                if add_level == "مديرية / جهة":
                    parent_auth = ""
                    parent_admin = ""
                else:
                    if not auth_values:
                        st.info("أضف المديرية / الجهة أولًا حتى يمكنك إضافة المستويات التابعة لها.")
                    parent_auth = st.selectbox("اختر المديرية / الجهة الأعلى:", auth_values, key="hier_add_parent_authority") if auth_values else ""
                    rows_for_authority = [r for r in current_hier if str(r.get("authority") or "").strip() == parent_auth]
                    admin_values = hierarchy_ordered_unique(r.get("administration") for r in rows_for_authority if str(r.get("administration") or "").strip())
                    directorate_section_values = hierarchy_ordered_unique(r.get("directorate_section") for r in rows_for_authority if str(r.get("directorate_section") or "").strip())
                    if add_level == "إدارة":
                        parent_sections = st.multiselect("اختر قسم المديرية أو الأقسام التابعة لها هذه الإدارة (إلزامي):", directorate_section_values, key="hier_add_parent_sections")
                    if add_level == "قسم داخل المديرية":
                        parent_admin = ""
                    elif add_level in ("قسم داخل الإدارة", "منشأة / وحدة الأمراض المتوطنة"):
                        parent_admin = st.selectbox("اختر الإدارة التابعة لها:", admin_values, key="hier_add_parent_admin") if admin_values else ""
                        if not admin_values:
                            st.info("أضف إدارة تحت المديرية المختارة أولًا.")
                        if add_level == "منشأة / وحدة الأمراض المتوطنة" and parent_admin:
                            rows_for_admin = [r for r in rows_for_authority if str(r.get("administration") or "").strip() == parent_admin]
                            admin_section_values = hierarchy_ordered_unique(r.get("administration_section") for r in rows_for_admin if str(r.get("administration_section") or "").strip())
                            parent_admin_sections = st.multiselect("اختر قسم الإدارة أو الأقسام التابعة لها المنشأة (إلزامي):", admin_section_values, key="hier_add_parent_admin_sections")
                    else:
                        parent_admin = ""
                with st.form("manual_hierarchical_form", clear_on_submit=True):
                    st.text_input("جمهورية مصر العربية", value="جمهورية مصر العربية", disabled=True, key="hier_country_fixed")
                    st.text_input("وزارة الصحة والسكان", value="وزارة الصحة والسكان", disabled=True, key="hier_ministry_fixed")
                    label_map = {"مديرية / جهة":"اسم المديرية / الجهة الجديدة:", "قسم داخل المديرية":"اسم القسم داخل المديرية:", "إدارة":"اسم الإدارة الجديدة:", "قسم داخل الإدارة":"اسم القسم داخل الإدارة:", "منشأة / وحدة الأمراض المتوطنة":"اسم المنشأة / وحدة الأمراض المتوطنة الجديدة:"}
                    new_node_name = st.text_input(label_map[add_level])
                    if st.form_submit_button("💾 إضافة المستوى التابع", use_container_width=True):
                        node = new_node_name.strip()
                        if not node:
                            st.warning("اكتب اسم المستوى الجديد أولًا.")
                        elif add_level != "مديرية / جهة" and not parent_auth:
                            st.warning("اختر المديرية / الجهة الأعلى أولًا.")
                        elif add_level in ("قسم داخل الإدارة", "منشأة / وحدة الأمراض المتوطنة") and not parent_admin:
                            st.warning("اختر الإدارة الأعلى أولًا.")
                        elif add_level == "إدارة" and not parent_sections:
                            st.warning("اختر قسمًا واحدًا على الأقل من أقسام المديرية التابعة لها الإدارة.")
                        elif add_level == "منشأة / وحدة الأمراض المتوطنة" and not parent_admin_sections:
                            st.warning("اختر قسمًا واحدًا على الأقل من أقسام الإدارة التابعة لها المنشأة.")
                        else:
                            auth_value = node if add_level == "مديرية / جهة" else parent_auth
                            admin_value = node if add_level == "إدارة" else (parent_admin if add_level in ("قسم داخل الإدارة", "منشأة / وحدة الأمراض المتوطنة") else "")
                            facility_value = node if add_level == "منشأة / وحدة الأمراض المتوطنة" else ""
                            directorate_section_value = node if add_level == "قسم داخل المديرية" else ""
                            administration_section_value = node if add_level == "قسم داخل الإدارة" else ""
                            path_sections = parent_sections if add_level == "إدارة" else [""]
                            path_admin_sections = parent_admin_sections if add_level == "منشأة / وحدة الأمراض المتوطنة" else [""]
                            inserted = False
                            with db() as c:
                                if add_level == "مديرية / جهة":
                                    exists = c.execute("SELECT 1 FROM hierarchical_facilities WHERE authority=? AND COALESCE(directorate_section,'')='' AND COALESCE(administration,'')='' AND COALESCE(facility_name,'')='' LIMIT 1", (auth_value,)).fetchone()
                                elif add_level == "قسم داخل المديرية":
                                    exists = c.execute("SELECT 1 FROM hierarchical_facilities WHERE authority=? AND directorate_section=? LIMIT 1", (auth_value, node)).fetchone()
                                elif add_level == "إدارة":
                                    existing_sections = {str(r[0]) for r in c.execute("SELECT directorate_section FROM hierarchical_facilities WHERE authority=? AND administration=? AND COALESCE(administration,'')<>''", (auth_value, admin_value)).fetchall()}
                                    exists = all(str(s) in existing_sections for s in path_sections)
                                elif add_level == "قسم داخل الإدارة":
                                    exists = c.execute("SELECT 1 FROM hierarchical_facilities WHERE authority=? AND administration=? AND administration_section=? LIMIT 1", (auth_value, admin_value, node)).fetchone()
                                else:
                                    existing_sections = {str(r[0]) for r in c.execute("SELECT administration_section FROM hierarchical_facilities WHERE authority=? AND administration=? AND facility_name=?", (auth_value, admin_value, facility_value)).fetchall()}
                                    exists = all(str(s) in existing_sections for s in path_admin_sections)
                                if not exists:
                                    if add_level == "إدارة":
                                        for section_name in path_sections:
                                            c.execute("INSERT INTO hierarchical_facilities(governorate,authority,center,administration,facility_name,created_at,hidden,directorate_section,administration_section) VALUES(?,?,?,?,?,?,?,?,?)", ("", auth_value, "", admin_value, "", now(), 0, section_name, ""))
                                    elif add_level == "منشأة / وحدة الأمراض المتوطنة":
                                        for section_name in path_admin_sections:
                                            c.execute("INSERT INTO hierarchical_facilities(governorate,authority,center,administration,facility_name,created_at,hidden,directorate_section,administration_section) VALUES(?,?,?,?,?,?,?,?,?)", ("", auth_value, "", admin_value, facility_value, now(), 0, "", section_name))
                                    else:
                                        c.execute("INSERT INTO hierarchical_facilities(governorate,authority,center,administration,facility_name,created_at,hidden,directorate_section,administration_section) VALUES(?,?,?,?,?,?,?,?,?)", ("", auth_value, "", admin_value, facility_value, now(), 0, directorate_section_value, administration_section_value))
                                    inserted = True
                            if not inserted:
                                st.warning("هذا المستوى مسجل بالفعل بالارتباطات المحددة.")
                            else:
                                reindex_hierarchical_facilities()
                                sync_normalized_hierarchy()
                                st.success("تمت إضافة المستوى الإداري وربطه بالارتباطات المحددة بنجاح.")
                                st.rerun()
        with tab_h2:
            if has_subtab_permission('🏥 الهيكل الإداري', '📥 رفع الملفات'):
                st.markdown("## 📥 رفع ملفات الهيكل الإداري")
                st.markdown("**أدوات رفع المستويات الأساسية:** مديريات / جهات ← إدارات حسب المديرية المختارة ← منشآت حسب الإدارة المختارة. ويمكن إضافة أقسام المديرية وأقسام الإدارة من الإضافة اليدوية.")
                st.caption("ارفع المستويات الأساسية على حدة. لإضافة قسم داخل المديرية أو داخل الإدارة استخدم الإضافة اليدوية مع تحديد المستوى الأب. يقبل الرفع ملفات Excel وCSV، وكل صف يمثل اسماً واحداً.")

                def _hierarchy_names_from_upload(uploaded_file, accepted_columns):
                    """Read a one-column hierarchy file, accepting common Arabic/English headers."""
                    if uploaded_file is None:
                        return []
                    uploaded_file.seek(0)
                    frame = pd.read_csv(uploaded_file) if uploaded_file.name.lower().endswith('.csv') else pd.read_excel(uploaded_file)
                    if frame.empty:
                        return []
                    chosen = next((col for col in accepted_columns if col in frame.columns), None)
                    if chosen is None:

                        if len(frame.columns) == 1:
                            chosen = frame.columns[0]
                        else:
                            raise ValueError("لم أجد عمود الأسماء المطلوب. استخدم عنوان العمود الموضح أسفل أداة الرفع أو ارفع ملفاً بعمود واحد فقط.")
                    names = []
                    for value in frame[chosen].tolist():
                        if pd.isna(value):
                            continue
                        name = str(value).strip()
                        if name and name.lower() not in {"nan", "none"}:
                            names.append(name)

                    return list(dict.fromkeys(names))

                current_upload_hierarchy = get_hierarchical_data(include_hidden=True)
                upload_authorities = hierarchy_ordered_unique(r.get("authority") for r in current_upload_hierarchy)
                upload_admin_rows = [r for r in current_upload_hierarchy if str(r.get("administration") or "").strip()]

                with st.expander("1️⃣ رفع المديريات / الجهات", expanded=True):
                    st.caption("عنوان العمود المقترح: المديرية / الجهة — أو ارفع ملفاً بعمود واحد للأسماء.")
                    upload_authorities_file = st.file_uploader("ملف المديريات / الجهات (.xlsx أو .xls أو .csv)", type=["xlsx", "xls", "csv"], key="hier_upload_authorities_file")
                    if st.button("⬆️ استيراد المديريات / الجهات", key="hier_import_authorities_btn", use_container_width=True, disabled=upload_authorities_file is None):
                        try:
                            names = _hierarchy_names_from_upload(upload_authorities_file, ["المديرية / الجهة", "المديرية", "الجهة", "authority", "Authority", "اسم المديرية", "اسم الجهة"])
                            added = 0
                            with db() as c:
                                for name in names:
                                    exists = c.execute("SELECT 1 FROM hierarchical_facilities WHERE authority=? AND COALESCE(administration,'')='' AND COALESCE(facility_name,'')='' LIMIT 1", (name,)).fetchone()
                                    if not exists:
                                        c.execute("INSERT INTO hierarchical_facilities(governorate,authority,center,administration,facility_name,created_at,hidden) VALUES(?,?,?,?,?,?,?)", ("", name, "", "", "", now(), 0))
                                        added += 1
                            reindex_hierarchical_facilities()
                            sync_normalized_hierarchy()
                            st.success(f"تم استيراد {added} مديرية / جهة جديدة. تم تجاهل الأسماء الموجودة مسبقاً.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"تعذر استيراد المديريات / الجهات: {e}")

                with st.expander("2️⃣ رفع الإدارات التابعة لأقسام مديرية محددة", expanded=True):
                    upload_parent_authority = st.selectbox("اختر المديرية / الجهة التي ستتبعها الإدارات:", upload_authorities, key="hier_upload_admin_parent", placeholder="اختر المديرية / الجهة") if upload_authorities else None
                    upload_parent_rows = [r for r in current_upload_hierarchy if str(r.get("authority") or "").strip() == str(upload_parent_authority or "")]
                    upload_parent_sections = hierarchy_ordered_unique(r.get("directorate_section") for r in upload_parent_rows if str(r.get("directorate_section") or "").strip())
                    upload_admin_parent_sections = st.multiselect("اختر قسمًا واحدًا أو أكثر تتبعها هذه الإدارات (إلزامي):", upload_parent_sections, key="hier_upload_admin_parent_sections")
                    st.caption("عنوان العمود المقترح: الإدارة — أو ارفع ملفاً بعمود واحد لأسماء الإدارات.")
                    upload_admins_file = st.file_uploader("ملف الإدارات (.xlsx أو .xls أو .csv)", type=["xlsx", "xls", "csv"], key="hier_upload_admins_file")
                    if not upload_authorities:
                        st.info("ارفع المديريات / الجهات أولاً حتى تظهر هنا.")
                    if st.button("⬆️ استيراد الإدارات للمديرية المختارة", key="hier_import_admins_btn", use_container_width=True, disabled=(upload_admins_file is None or not upload_parent_authority or not upload_admin_parent_sections)):
                        try:
                            names = _hierarchy_names_from_upload(upload_admins_file, ["الإدارة", "اسم الإدارة", "administration", "Administration", "department", "Department"])
                            added = 0
                            with db() as c:
                                for name in names:
                                    existing_sections = {str(r[0] or "") for r in c.execute("SELECT directorate_section FROM hierarchical_facilities WHERE authority=? AND administration=?", (upload_parent_authority, name)).fetchall()}
                                    missing_sections = [section_name for section_name in upload_admin_parent_sections if section_name not in existing_sections]
                                    if missing_sections:
                                        for section_name in missing_sections:
                                            c.execute("INSERT INTO hierarchical_facilities(governorate,authority,center,administration,facility_name,created_at,hidden,directorate_section,administration_section) VALUES(?,?,?,?,?,?,?,?,?)", ("", upload_parent_authority, "", name, "", now(), 0, section_name, ""))
                                        added += 1
                            reindex_hierarchical_facilities()
                            sync_normalized_hierarchy()
                            st.success(f"تم استيراد {added} إدارة جديدة تحت {upload_parent_authority}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"تعذر استيراد الإدارات: {e}")

                with st.expander("3️⃣ رفع المنشآت التابعة لإدارة محددة", expanded=True):
                    upload_facility_authority = st.selectbox("اختر المديرية / الجهة:", upload_authorities, key="hier_upload_facility_authority", placeholder="اختر المديرية / الجهة") if upload_authorities else None
                    upload_facility_admins = hierarchy_ordered_unique(r.get("administration") for r in upload_admin_rows if str(r.get("authority") or "").strip() == str(upload_facility_authority or ""))
                    upload_facility_admin = st.selectbox("اختر الإدارة التي ستتبعها المنشآت:", upload_facility_admins, key="hier_upload_facility_admin", placeholder="اختر الإدارة") if upload_facility_admins else None
                    upload_facility_admin_rows = [r for r in current_upload_hierarchy if str(r.get("authority") or "").strip() == str(upload_facility_authority or "") and str(r.get("administration") or "").strip() == str(upload_facility_admin or "")]
                    upload_facility_admin_sections = hierarchy_ordered_unique(r.get("administration_section") for r in upload_facility_admin_rows if str(r.get("administration_section") or "").strip())
                    upload_facility_parent_sections = st.multiselect("اختر قسمًا واحدًا أو أكثر تتبعها المنشآت (إلزامي):", upload_facility_admin_sections, key="hier_upload_facility_parent_sections")
                    st.caption("عنوان العمود المقترح: المنشأة / وحدة الأمراض المتوطنة — أو ارفع ملفاً بعمود واحد لأسماء المنشآت.")
                    upload_facilities_file = st.file_uploader("ملف المنشآت (.xlsx أو .xls أو .csv)", type=["xlsx", "xls", "csv"], key="hier_upload_facilities_file")
                    if upload_facility_authority and not upload_facility_admins:
                        st.info("لا توجد إدارات تحت المديرية المختارة. ارفع الإدارات أولاً.")
                    if st.button("⬆️ استيراد المنشآت للإدارة المختارة", key="hier_import_facilities_btn", use_container_width=True, disabled=(upload_facilities_file is None or not upload_facility_authority or not upload_facility_admin or not upload_facility_parent_sections)):
                        try:
                            names = _hierarchy_names_from_upload(upload_facilities_file, ["المنشأة / وحدة الأمراض المتوطنة", "المنشأة", "وحدة الأمراض المتوطنة", "اسم المنشأة", "facility_name", "Facility", "facility"])
                            added = 0
                            with db() as c:
                                for name in names:
                                    existing_sections = {str(r[0] or "") for r in c.execute("SELECT administration_section FROM hierarchical_facilities WHERE authority=? AND administration=? AND facility_name=?", (upload_facility_authority, upload_facility_admin, name)).fetchall()}
                                    missing_sections = [section_name for section_name in upload_facility_parent_sections if section_name not in existing_sections]
                                    if missing_sections:
                                        for section_name in missing_sections:
                                            c.execute("INSERT INTO hierarchical_facilities(governorate,authority,center,administration,facility_name,created_at,hidden,directorate_section,administration_section) VALUES(?,?,?,?,?,?,?,?,?)", ("", upload_facility_authority, "", upload_facility_admin, name, now(), 0, "", section_name))
                                        added += 1
                            reindex_hierarchical_facilities()
                            sync_normalized_hierarchy()
                            st.success(f"تم استيراد {added} منشأة جديدة تحت إدارة {upload_facility_admin}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"تعذر استيراد المنشآت: {e}")

                st.markdown("---")
                st.markdown("##### 📄 تنزيل نموذج هيكل إداري فارغ للتعبئة وإعادة الرفع")
                st.caption("يمكنك تعبئة المستويات الإدارية: المديرية / الجهة، قسم المديرية، الإدارة، قسم الإدارة، والمنشأة / وحدة الأمراض المتوطنة. اترك صف العناوين كما هو. يمكن ربط الإدارة بأكثر من قسم مديرية، والمنشأة بأكثر من قسم إدارة؛ سجّل صفًا لكل ارتباط مطلوب.")
                hierarchy_template = pd.DataFrame(columns=["المديرية / الجهة", "قسم المديرية", "الإدارة", "قسم الإدارة", "المنشأة / وحدة الأمراض المتوطنة"])
                hierarchy_template_bytes = io.BytesIO()
                with pd.ExcelWriter(hierarchy_template_bytes, engine="openpyxl") as writer:
                    hierarchy_template.to_excel(writer, index=False, sheet_name="HierarchicalFacilities")
                st.download_button(
                    "📥 تحميل نموذج الهيكل الإداري الفارغ (.xlsx)",
                    data=hierarchy_template_bytes.getvalue(),
                    file_name="hierarchical_facilities_template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_empty_hierarchy_template",
                )
                st.markdown("---")
                st.info("استخدم أدوات الرفع الثلاثة أعلاه حسب المستوى المطلوب. تم إخفاء أداة الرفع العامة القديمة لتجنب رفع البيانات في المستوى الخطأ.")
                st.markdown("---")
                st.markdown("##### 📥 تحميل شيت إكسيل الهيكل الإداري الحالي:")
                hier_all_data = get_hierarchical_data(include_hidden=True)
                if hier_all_data:
                    df_hier_download = pd.DataFrame(hier_all_data)
                    for _col in ("directorate_section", "administration_section"):
                        if _col not in df_hier_download.columns:
                            df_hier_download[_col] = ""
                    df_hier_download = df_hier_download[["id", "authority", "directorate_section", "administration", "administration_section", "facility_name", "created_at", "hidden"]]
                    df_hier_download.columns = ["معرّف السجل الداخلي", "المديرية / الجهة", "قسم المديرية", "الإدارة", "قسم الإدارة", "المنشأة / وحدة الأمراض المتوطنة", "تاريخ الإنشاء", "حالة الإخفاء"]
                    output_hier = io.BytesIO()
                    with pd.ExcelWriter(output_hier, engine='openpyxl') as writer:
                        df_hier_download.to_excel(writer, index=False, sheet_name='HierarchicalFacilities')
                    st.download_button("📥 تحميل شيت الهيكل الإداري (.xlsx)", data=output_hier.getvalue(), file_name="hierarchical_facilities.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                else:
                    st.info("لا توجد بيانات مسجلة في الهيكل الإداري للتحميل حالياً.")
        with tab_h3:
            if has_subtab_permission('🏥 الهيكل الإداري', '📋 استعراض وإخفاء/إظهار/حذف'):
                hier_rows_all = get_hierarchical_data(include_hidden=True)
                st.markdown("##### ♻️ تفريغ الهيكل الإداري وإعادة بدء التكويد")
                st.warning("هذا الإجراء يحذف جميع المديريات والإدارات والمنشآت من جدول الهيكل الإداري نهائيًا. لا يحذف المتدربين أو الأسئلة أو النماذج، لكن أي تقارير أو صلاحيات تعتمد على أسماء الهيكل قد لا تعود مرتبطة بمستويات محذوفة.")
                clear_hierarchy_confirm = st.checkbox(
                    "أؤكد أنني أريد حذف الهيكل الإداري بالكامل، وأفهم أن العملية نهائية.",
                    key="confirm_clear_entire_hierarchy_v1",
                )
                clear_hierarchy_phrase = st.text_input(
                    "للتأكيد اكتب: تفريغ الهيكل الإداري",
                    key="clear_entire_hierarchy_phrase_v1",
                    placeholder="تفريغ الهيكل الإداري",
                )
                if st.button(
                    "🗑️ تفريغ الهيكل الإداري وإعادة بدء IDs من 1",
                    key="clear_entire_hierarchy_button_v1",
                    disabled=not (clear_hierarchy_confirm and clear_hierarchy_phrase.strip() == "تفريغ الهيكل الإداري"),
                    use_container_width=True,
                ):
                    with db() as c:
                        c.execute("DELETE FROM hierarchical_facilities")
                        try:
                            c.execute("DELETE FROM sqlite_sequence WHERE name='hierarchical_facilities'")
                        except sqlite3.OperationalError:
                            pass

                    sync_normalized_hierarchy()

                    for state_key in list(st.session_state.keys()):
                        if state_key.startswith(("hier_", "manual_exam_hierarchy", "real_assessment_hierarchy", "training_minutes_scope", "trainee_schedule_scope")):
                            st.session_state.pop(state_key, None)
                    st.success("تم تفريغ الهيكل الإداري بالكامل. سيبدأ ID الداخلي من 1 عند إضافة السجل التالي، وستبدأ أكواد العرض من 1 لكل مستوى.")
                    st.rerun()
                st.markdown("---")
                if not hier_rows_all:
                    st.info("لا توجد بيانات مسجلة.")
                else:
                    st.markdown("##### استعراض الهيكل: المديرية ← قسم المديرية ← الإدارة ← قسم الإدارة ← المنشأة")
                    manage_auth_codes, manage_directorate_section_codes, manage_admin_codes, manage_administration_section_codes, manage_facility_codes = hierarchy_level_codes(hier_rows_all)
                    manage_auths = hierarchy_ordered_unique(r.get("authority") for r in hier_rows_all)
                    sel_manage_auth = st.selectbox("المديرية / الجهة:", manage_auths, format_func=lambda value: value, key="hier_manage_authority", on_change=_reset_hier_admin_and_facility)
                    manage_auth_rows = [r for r in hier_rows_all if str(r.get("authority") or "").strip() == sel_manage_auth]
                    manage_admins = hierarchy_ordered_unique(r.get("administration") for r in manage_auth_rows)
                    sel_manage_admin = st.selectbox("الإدارة:", ["-- اختر الإدارة --"] + manage_admins, format_func=lambda value: value, key="hier_manage_administration", on_change=_reset_hier_facility)
                    manage_admin_rows = [r for r in manage_auth_rows if sel_manage_admin != "-- اختر الإدارة --" and str(r.get("administration") or "").strip() == sel_manage_admin]


                    st.markdown("##### 🗑️ حذف أي مستوى من الهيكل الإداري وإعادة ترقيم الـ ID")
                    delete_kind = st.selectbox(
                        "حدد نوع الجزء المراد حذفه:",
                        ["مديرية / جهة كاملة", "إدارة بكل منشآتها", "منشأة محددة فقط"],
                        key="hier_delete_any_kind_v2",
                    )
                    delete_target = ""
                    delete_count = 0
                    if delete_kind == "مديرية / جهة كاملة":
                        delete_target = sel_manage_auth
                        delete_count = sum(1 for r in hier_rows_all if str(r.get("authority") or "").strip() == delete_target)
                    elif delete_kind == "إدارة بكل منشآتها":
                        if manage_admins:
                            delete_target = st.selectbox("الإدارة المراد حذفها:", manage_admins, key="hier_delete_any_admin_v2")
                            delete_count = sum(1 for r in hier_rows_all if str(r.get("authority") or "").strip() == sel_manage_auth and str(r.get("administration") or "").strip() == delete_target)
                        else:
                            st.info("لا توجد إدارات مسجلة تحت المديرية / الجهة المختارة.")
                    else:
                        delete_fac_rows = [r for r in manage_admin_rows if str(r.get("facility_name") or "").strip()]
                        delete_fac_options = {int(r["id"]): str(r.get("facility_name") or "") for r in delete_fac_rows}
                        if delete_fac_options:
                            delete_fac_id = st.selectbox(
                                "المنشأة المراد حذفها:", list(delete_fac_options),
                                format_func=lambda value: delete_fac_options[value],
                                key="hier_delete_any_facility_v2",
                            )
                            delete_target = delete_fac_id
                            delete_count = 1
                        else:
                            st.info("لا توجد منشآت مسجلة تحت الإدارة المختارة.")
                    if delete_target and delete_count:
                        confirm_any_delete = st.checkbox(
                            f"أؤكد الحذف النهائي لـ «{delete_target if delete_kind != 'منشأة محددة فقط' else delete_fac_options[delete_target]}» وحذف {delete_count} سجل/سجلات تابعة له.",
                            key="hier_delete_any_confirm_v2",
                        )
                        if st.button("🗑️ حذف المستوى المحدد وإعادة ترقيم IDs من 1", key="hier_delete_any_button_v2", disabled=not confirm_any_delete, use_container_width=True):
                            with db() as c:
                                if delete_kind == "مديرية / جهة كاملة":
                                    c.execute("DELETE FROM hierarchical_facilities WHERE authority=?", (delete_target,))
                                elif delete_kind == "إدارة بكل منشآتها":
                                    c.execute("DELETE FROM hierarchical_facilities WHERE authority=? AND administration=?", (sel_manage_auth, delete_target))
                                else:
                                    c.execute("DELETE FROM hierarchical_facilities WHERE id=?", (delete_target,))
                            reindex_hierarchical_facilities()
                            sync_normalized_hierarchy()
                            st.success("تم حذف الجزء المحدد. أُعيد احتساب أكواد العرض المستقلة لكل مستوى؛ ومعرّفات قاعدة البيانات تُستخدم داخليًا لربط السجلات.")
                            st.rerun()



                    manage_facilities = [r for r in manage_admin_rows if str(r.get("facility_name") or "").strip()]
                    manage_facility_labels = {
                        int(r["id"]): (
                            f"{str(r.get('facility_name') or '').strip()} "
                            f"— {'مخفي' if int(r.get('hidden') or 0) else 'ظاهر'}"
                        )
                        for r in manage_facilities
                    }



                    if not manage_facility_labels:
                        st.info("لا توجد منشآت مسجلة تحت الإدارة المختارة. يمكنك إضافتها من تبويب (إضافة يدوية).")
                        facility_options = [None]
                    else:
                        facility_options = [None] + list(manage_facility_labels.keys())
                    selected_manage_facility_id = st.selectbox(
                        "استعراض المنشآت التابعة للإدارة المختارة:", facility_options,
                        format_func=lambda value: "-- اختر منشأة للاستعراض والتعديل --" if value is None else manage_facility_labels.get(int(value), "-- اختر منشأة للاستعراض والتعديل --"),
                        key="hier_manage_facility_id"
                    )
                    if manage_facility_labels:
                        st.markdown("##### 📋 قائمة المنشآت التابعة للإدارة المختارة")
                        st.dataframe(
                            [{"اسم المنشأة": str(r.get("facility_name") or "").strip(),
                              "الحالة": "مخفي" if int(r.get("hidden") or 0) else "ظاهر"}
                             for r in manage_facilities],
                            use_container_width=True, hide_index=True
                        )
                    if selected_manage_facility_id is not None:
                            target_id = int(selected_manage_facility_id)
                            target_row = next((r for r in manage_facilities if int(r["id"]) == target_id), None)
                            if target_row:
                                st.markdown("##### ✏️ تعديل بيانات الهيكل الإداري")
                                st.caption("تعديل المديرية يطبق على كل الإدارات والمنشآت التابعة لها، وتعديل الإدارة يطبق على كل منشآتها، وتعديل اسم المنشأة يخص المنشأة المحددة فقط.")
                                with st.form(f"edit_hierarchy_node_{target_id}"):
                                    edit_auth = st.text_input("المديرية / الجهة:", value=str(target_row.get("authority") or ""))
                                    edit_admin = st.text_input("الإدارة:", value=str(target_row.get("administration") or ""))
                                    edit_fac = st.text_input("المنشأة / وحدة الأمراض المتوطنة:", value=str(target_row.get("facility_name") or ""))
                                    edit_hierarchy_submit = st.form_submit_button("💾 حفظ تعديلات الهيكل الإداري", use_container_width=True)
                                if edit_hierarchy_submit:
                                    edit_auth, edit_admin, edit_fac = edit_auth.strip(), edit_admin.strip(), edit_fac.strip()
                                    if not (edit_auth and edit_admin and edit_fac):
                                        st.warning("يجب إدخال المديرية والإدارة واسم المنشأة.")
                                    else:
                                        with db() as c:
                                            old = c.execute("SELECT * FROM hierarchical_facilities WHERE id=?", (target_id,)).fetchone()
                                            if not old:
                                                st.error("تعذر العثور على السجل المطلوب.")
                                            else:
                                                duplicate = c.execute("SELECT 1 FROM hierarchical_facilities WHERE authority=? AND administration=? AND facility_name=? AND id<>? LIMIT 1", (edit_auth, edit_admin, edit_fac, target_id)).fetchone()
                                                if duplicate:
                                                    st.warning("يوجد سجل بنفس المديرية والإدارة واسم المنشأة بالفعل.")
                                                else:
                                                    old_auth, old_admin = str(old["authority"] or ""), str(old["administration"] or "")
                                                    if edit_auth != old_auth:
                                                        c.execute("UPDATE hierarchical_facilities SET authority=? WHERE authority=?", (edit_auth, old_auth))
                                                    if edit_admin != old_admin:
                                                        c.execute("UPDATE hierarchical_facilities SET administration=? WHERE authority=? AND administration=?", (edit_admin, edit_auth, old_admin))
                                                    c.execute("UPDATE hierarchical_facilities SET facility_name=? WHERE id=?", (edit_fac, target_id))
                                                    reindex_hierarchical_facilities()
                                                    sync_normalized_hierarchy()
                                                    st.success("تم تعديل بيانات الهيكل الإداري بنجاح.")
                                                    st.rerun()
                                st.markdown("##### 🗑️ حذف جزء من الهيكل الإداري")
                                delete_level = st.selectbox("مستوى الحذف:", ["المنشأة المحددة فقط", "الإدارة بكل منشآتها", "المديرية بكل إداراتها ومنشآتها"], key=f"hier_delete_level_{target_id}")
                                delete_phrase = {"المنشأة المحددة فقط": str(target_row.get("facility_name") or ""), "الإدارة بكل منشآتها": str(target_row.get("administration") or ""), "المديرية بكل إداراتها ومنشآتها": str(target_row.get("authority") or "")}[delete_level]
                                confirm_delete = st.checkbox(f"أؤكد حذف «{delete_phrase}» وكل السجلات التابعة للمستوى المحدد", key=f"confirm_hier_delete_{target_id}")
                                if st.button("🗑️ تأكيد حذف المستوى المحدد", key=f"delete_hier_level_{target_id}", disabled=not confirm_delete, use_container_width=True):
                                    with db() as c:
                                        if delete_level == "المنشأة المحددة فقط":
                                            c.execute("DELETE FROM hierarchical_facilities WHERE id=?", (target_id,))
                                        elif delete_level == "الإدارة بكل منشآتها":
                                            c.execute("DELETE FROM hierarchical_facilities WHERE authority=? AND administration=?", (target_row.get("authority"), target_row.get("administration")))
                                        else:
                                            c.execute("DELETE FROM hierarchical_facilities WHERE authority=?", (target_row.get("authority"),))
                                    reindex_hierarchical_facilities()
                                    sync_normalized_hierarchy()
                                    st.success("تم حذف المستوى الإداري المحدد والسجلات التابعة له.")
                                    st.rerun()
                            with st.form("manage_single_hier_form", clear_on_submit=True):
                                c_hide_btn, c_show_btn, c_del_btn = st.columns(3)
                                with c_hide_btn:
                                    hide_fac_submit = st.form_submit_button("👁🗨️ إخفاء المنشأة", use_container_width=True)
                                with c_show_btn:
                                    show_fac_submit = st.form_submit_button("✅ إظهار المنشأة", use_container_width=True)
                                with c_del_btn:
                                    single_del = st.form_submit_button("🗑 حذف نهائي", use_container_width=True)
                            if hide_fac_submit:
                                with db() as c:
                                    c.execute("UPDATE hierarchical_facilities SET hidden=1 WHERE id=?", (target_id,))
                                sync_normalized_hierarchy()
                                st.success("✅ تم إخفاء المنشأة من التقارير بنجاح!")
                                st.rerun()
                            if show_fac_submit:
                                with db() as c:
                                    c.execute("UPDATE hierarchical_facilities SET hidden=0 WHERE id=?", (target_id,))
                                sync_normalized_hierarchy()
                                st.success("✅ تم إظهار المنشأة في التقارير بنجاح!")
                                st.rerun()
                            if single_del:
                                with db() as c:
                                    c.execute("DELETE FROM hierarchical_facilities WHERE id=?", (target_id,))
                                reindex_hierarchical_facilities()
                                sync_normalized_hierarchy()
                                st.success("✅ تم حذف المنشأة وإعادة الترتيب التسلسلي للـ ID بنجاح!")
                                st.rerun()
                    df_hier = pd.DataFrame(hier_rows_all)
                    df_hier["hidden"] = df_hier["hidden"].apply(lambda x: "مخفي 👁‍🗨" if x==1 else "ظاهر ✅")
                    for col in ("directorate_section", "administration_section"):
                        if col not in df_hier.columns: df_hier[col] = ""
                    df_hier = df_hier[["id", "authority", "directorate_section", "administration", "administration_section", "facility_name", "created_at", "hidden"]]
                    df_hier.columns = ["ID السجل", "المديرية / الجهة", "قسم المديرية", "الإدارة", "قسم الإدارة", "المنشأة / وحدة الأمراض المتوطنة", "تاريخ الإنشاء", "حالة الإخفاء"]
                    st.dataframe(df_hier, use_container_width=True, hide_index=True)
                    st.markdown("##### 🌳 عرض مسارات الربط الفعلية للأقسام المشتركة")
                    linked_preview = get_hierarchy_linked_projection_rows(include_hidden=True)
                    preview_rows = []
                    for rr in linked_preview:
                        if str(rr.get("directorate_section") or "").strip() or str(rr.get("administration_section") or "").strip():
                            preview_rows.append({"المديرية":rr.get("authority",""),"قسم المديرية":rr.get("directorate_section",""),"الإدارة المشتركة":rr.get("administration",""),"قسم الإدارة":rr.get("administration_section",""),"المنشأة المشتركة":rr.get("facility_name","")})
                    if preview_rows:
                        st.dataframe(pd.DataFrame(preview_rows).drop_duplicates(), use_container_width=True, hide_index=True)
                    else:
                        st.info("أضف أقسام المديرية وأقسام الإدارة لتظهر مسارات الربط هنا.")

    elif selected_menu == "⚙ إدارة الأسئلة":
        st.subheader("⚙ إدارة الأسئلة وبنوك الأقسام الإدارية")
        categories_list_opts = [
            "الاستراتيجية العامة ومكافحة البلهارسيا", "البلهارسيا", "علاج البلهارسيا", "الفاشيولا", "علاج الفاشيولا", "الهتروفيس", "التينيا", "هيمنولبس نانا", "الإسكارس", "الأنكلستوما", "الأكسيورس", "تركيورس تركيورا", "Strongyloides stercoralis", "Entamoeba histolytica", "Giardia lamblia", "الفحوصات الطفيلية والتشخيصية", "فحص البول (بلهارسيا المجاري البولية)", "فحص البراز (طفيليات المعوية)", "ط طرق فحص البراز المعتمدة", "الترسيب", "التعويم", "اللطخة المباشرة", "التصفية الغشائية", "Kato-Katz", "تحضير وعزل العينات", "أسئلة الصور والأشكال المجهرية"
        ]
        sub_q_manage_tabs = st.tabs(["➕ إضافة وتعديل وحذف فردي", "🏢 بنوك الأقسام الإدارية"])
        # Scoped banks are attached to real section IDs; legacy questions remain in the global bank.
        with sub_q_manage_tabs[1]:
            st.markdown("#### 🏢 بنك أسئلة مستقل لكل قسم إداري")
            st.caption("يمكن لقسم المديرية أو قسم الإدارة إضافة أسئلته يدويًا، سواء بسؤال نصي أو سؤال مصحوب بصورة. الأسئلة لا تظهر في الاختبار إلا عند اختيار نطاق إداري مطابق في نموذج الامتحان.")
            scope_now = current_user_trainee_scope()
            with db() as c:
                ds_rows = [dict(r) for r in c.execute("SELECT ds.id, ds.name, d.name AS directorate FROM directorate_sections ds JOIN directorates d ON d.id=ds.directorate_id WHERE ds.hidden=0 AND d.hidden=0 ORDER BY d.name, ds.name").fetchall()]
                as_rows = [dict(r) for r in c.execute("SELECT s.id, s.name, a.name AS administration, d.name AS directorate FROM administration_sections s JOIN departments a ON a.id=s.department_id JOIN directorates d ON d.id=a.directorate_id WHERE s.hidden=0 AND a.hidden=0 AND d.hidden=0 ORDER BY d.name, a.name, s.name").fetchall()]
            if not is_owner() and not scope_now.get("scope_all"):
                if scope_now.get("_scope_denied"):
                    ds_rows, as_rows = [], []
                else:
                    if scope_now.get("scope_authority"):
                        ds_rows = [r for r in ds_rows if r["directorate"] == scope_now["scope_authority"]]
                        as_rows = [r for r in as_rows if r["directorate"] == scope_now["scope_authority"]]
                    if scope_now.get("scope_directorate_section"):
                        ds_rows = [r for r in ds_rows if r["name"] == scope_now["scope_directorate_section"]]
                    if scope_now.get("scope_administration"):
                        as_rows = [r for r in as_rows if r["administration"] == scope_now["scope_administration"]]
                    if scope_now.get("scope_administration_section"):
                        as_rows = [r for r in as_rows if r["name"] == scope_now["scope_administration_section"]]
            bank_directorate_tab, bank_admin_tab = st.tabs(["🏢 بنك قسم المديرية", "🏥 بنك قسم الإدارة"])
            with bank_directorate_tab:
                if not ds_rows:
                    st.info("لا توجد أقسام مديرية متاحة ضمن نطاق صلاحيتك. أضف الأقسام من الهيكل الإداري أولًا.")
                else:
                    ds_map = {f"{r['directorate']} — {r['name']}": r["id"] for r in ds_rows}
                    chosen_ds_label = st.selectbox("قسم المديرية صاحب البنك:", list(ds_map), key="qbank_directorate_section")
                    chosen_ds_id = int(ds_map[chosen_ds_label])
                    with db() as c:
                        ds_bank = [dict(r) for r in c.execute("SELECT id, difficulty, category, question, options_json, answer FROM questions WHERE scope_type='directorate_section' AND scope_id=? ORDER BY id DESC", (chosen_ds_id,)).fetchall()]
                    st.caption(f"عدد أسئلة هذا القسم: {len(ds_bank)}")
                    with st.form("add_directorate_section_question", clear_on_submit=True):
                        qcat = st.selectbox("التصنيف:", categories_list_opts, key="ds_q_cat")
                        qdiff = st.selectbox("الصعوبة:", ["سهل", "متوسط", "صعب"], key="ds_q_diff")
                        qtext = st.text_area("نص السؤال:", key="ds_q_text")
                        qimage = st.file_uploader("صورة السؤال (اختياري):", type=["png", "jpg", "jpeg"], key="ds_q_image")
                        qopts = [st.text_input(f"الخيار {i}:", key=f"ds_q_opt{i}") for i in range(1,5)]
                        qcorrect = st.text_input("الإجابة الصحيحة:", key="ds_q_correct")
                        if st.form_submit_button("💾 حفظ السؤال في بنك قسم المديرية", use_container_width=True):
                            opts = [x.strip() for x in qopts if x.strip()]
                            if qtext.strip() and qcorrect.strip():
                                if qcorrect.strip() not in opts: opts.append(qcorrect.strip())
                                final_text = qtext.strip()
                                if qimage:
                                    import base64
                                    mime = qimage.type or "image/png"
                                    final_text = f"IMAGE:data:{mime};base64," + base64.b64encode(qimage.getvalue()).decode("utf-8") + "\n\n" + final_text
                                ans = opts.index(qcorrect.strip())
                                fp = hashlib.sha256((final_text+"|"+"|".join(opts)+f"|directorate_section|{chosen_ds_id}").encode("utf-8")).hexdigest()
                                try:
                                    with db() as c:
                                        c.execute("INSERT INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at,scope_type,scope_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (qdiff,qcat,final_text,json.dumps(opts,ensure_ascii=False),ans,1,fp,now(),"directorate_section",chosen_ds_id))
                                    st.success("تم حفظ السؤال في بنك القسم."); st.rerun()
                                except sqlite3.IntegrityError:
                                    st.error("هذا السؤال مسجل بالفعل في البنك.")
                            else: st.error("اكتب نص السؤال والإجابة الصحيحة على الأقل.")
                    if ds_bank:
                        st.dataframe(pd.DataFrame([{**r, "question": clean_question_text(r["question"]), "options_json": r["options_json"]} for r in ds_bank])[ ["id","difficulty","category","question","options_json","answer"] ], use_container_width=True, hide_index=True)
                    st.markdown("##### 📥 استيراد ودمج أسئلة لهذا القسم")
                    ds_excel = st.file_uploader("اختر ملف Excel أو CSV لقسم المديرية:", type=["xlsx", "xls", "csv"], key=f"ds_excel_{chosen_ds_id}")
                    if ds_excel is not None:
                        try:
                            ds_import_df = pd.read_csv(ds_excel) if ds_excel.name.lower().endswith('.csv') else pd.read_excel(ds_excel)
                            st.dataframe(ds_import_df.head(5), use_container_width=True, hide_index=True)
                            if st.button("🚀 دمج الأسئلة في بنك هذا القسم", key=f"ds_import_btn_{chosen_ds_id}", use_container_width=True):
                                added = skipped = 0
                                with db() as c:
                                    for _, row in ds_import_df.iterrows():
                                        diff = str(row.get("difficulty", row.get("الصعوبة", "متوسط"))).strip()
                                        cat = str(row.get("category", row.get("المجال", categories_list_opts[0]))).strip()
                                        qt = str(row.get("question", row.get("السؤال", ""))).strip()
                                        raw_opts = row.get("options_json", row.get("الخيارات", '["نعم", "لا"]'))
                                        try: opts = json.loads(raw_opts) if isinstance(raw_opts, str) and raw_opts.strip().startswith("[") else [x.strip() for x in str(raw_opts).split(",") if x.strip()]
                                        except Exception: opts = ["نعم", "لا"]
                                        try: ans = int(row.get("answer", row.get("رقم الإجابة الصحيحة", 0)))
                                        except Exception: ans = 0
                                        if qt and opts:
                                            ans = max(0, min(ans, len(opts)-1))
                                            fp = hashlib.sha256((qt+"|"+"|".join(map(str,opts))+f"|directorate_section|{chosen_ds_id}").encode()).hexdigest()
                                            try:
                                                c.execute("INSERT INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at,scope_type,scope_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (diff,cat,qt,json.dumps(opts,ensure_ascii=False),ans,1,fp,now(),"directorate_section",chosen_ds_id)); added += 1
                                            except sqlite3.IntegrityError: skipped += 1
                                st.success(f"تمت إضافة {added} سؤال وتخطي {skipped} سؤال مكرر."); st.rerun()
                        except Exception as e: st.error(f"تعذر قراءة الملف: {e}")
                    with db() as c:
                        ds_export_df = pd.read_sql_query("SELECT id,difficulty,category,question,options_json,answer FROM questions WHERE scope_type='directorate_section' AND scope_id=? ORDER BY id", c, params=(chosen_ds_id,))
                    if not ds_export_df.empty:
                        ds_out = io.BytesIO()
                        with pd.ExcelWriter(ds_out, engine="openpyxl") as writer: ds_export_df.to_excel(writer, index=False, sheet_name="QuestionBank")
                        st.download_button("📤 تصدير بنك هذا القسم Excel", data=ds_out.getvalue(), file_name=f"directorate_section_{chosen_ds_id}_questions.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"ds_export_{chosen_ds_id}")
                    with st.form(f"ds_clear_bank_{chosen_ds_id}", clear_on_submit=True):
                        ds_confirm = st.text_input("لتفريغ بنك هذا القسم فقط اكتب: حذف البنك", key=f"ds_clear_confirm_{chosen_ds_id}")
                        if st.form_submit_button("🗑 تفريغ بنك قسم المديرية"):
                            if ds_confirm.strip() == "حذف البنك":
                                with db() as c: c.execute("DELETE FROM questions WHERE scope_type='directorate_section' AND scope_id=?", (chosen_ds_id,))
                                st.success("تم تفريغ بنك هذا القسم فقط."); st.rerun()
                            else: st.warning("اكتب عبارة التأكيد بشكل صحيح.")
            with bank_admin_tab:
                if not as_rows:
                    st.info("لا توجد أقسام إدارة متاحة ضمن نطاق صلاحيتك. أضف أقسام الإدارة من الهيكل الإداري أولًا.")
                else:
                    as_map = {f"{r['directorate']} — {r['administration']} — {r['name']}": r["id"] for r in as_rows}
                    chosen_as_label = st.selectbox("قسم الإدارة صاحب البنك:", list(as_map), key="qbank_administration_section")
                    chosen_as_id = int(as_map[chosen_as_label])
                    with db() as c:
                        as_bank = [dict(r) for r in c.execute("SELECT id, difficulty, category, question, options_json, answer FROM questions WHERE scope_type='administration_section' AND scope_id=? ORDER BY id DESC", (chosen_as_id,)).fetchall()]
                    st.caption(f"عدد أسئلة هذا القسم: {len(as_bank)}")
                    with st.form("add_administration_section_question", clear_on_submit=True):
                        qcat2 = st.selectbox("التصنيف:", categories_list_opts, key="as_q_cat")
                        qdiff2 = st.selectbox("الصعوبة:", ["سهل", "متوسط", "صعب"], key="as_q_diff")
                        qtext2 = st.text_area("نص السؤال:", key="as_q_text")
                        qimage2 = st.file_uploader("صورة السؤال (اختياري):", type=["png", "jpg", "jpeg"], key="as_q_image")
                        qopts2 = [st.text_input(f"الخيار {i}:", key=f"as_q_opt{i}") for i in range(1,5)]
                        qcorrect2 = st.text_input("الإجابة الصحيحة:", key="as_q_correct")
                        if st.form_submit_button("💾 حفظ السؤال في بنك قسم الإدارة", use_container_width=True):
                            opts2 = [x.strip() for x in qopts2 if x.strip()]
                            if qtext2.strip() and qcorrect2.strip():
                                if qcorrect2.strip() not in opts2: opts2.append(qcorrect2.strip())
                                final_text2 = qtext2.strip()
                                if qimage2:
                                    import base64
                                    mime2 = qimage2.type or "image/png"
                                    final_text2 = f"IMAGE:data:{mime2};base64," + base64.b64encode(qimage2.getvalue()).decode("utf-8") + "\n\n" + final_text2
                                ans2 = opts2.index(qcorrect2.strip())
                                fp2 = hashlib.sha256((final_text2+"|"+"|".join(opts2)+f"|administration_section|{chosen_as_id}").encode("utf-8")).hexdigest()
                                try:
                                    with db() as c:
                                        c.execute("INSERT INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at,scope_type,scope_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (qdiff2,qcat2,final_text2,json.dumps(opts2,ensure_ascii=False),ans2,1,fp2,now(),"administration_section",chosen_as_id))
                                    st.success("تم حفظ السؤال في بنك القسم."); st.rerun()
                                except sqlite3.IntegrityError:
                                    st.error("هذا السؤال مسجل بالفعل في البنك.")
                            else: st.error("اكتب نص السؤال والإجابة الصحيحة على الأقل.")
                    if as_bank:
                        st.dataframe(pd.DataFrame([{**r, "question": clean_question_text(r["question"])} for r in as_bank])[ ["id","difficulty","category","question","options_json","answer"] ], use_container_width=True, hide_index=True)
                    st.markdown("##### 📥 استيراد ودمج أسئلة لهذا القسم")
                    as_excel = st.file_uploader("اختر ملف Excel أو CSV لقسم الإدارة:", type=["xlsx", "xls", "csv"], key=f"as_excel_{chosen_as_id}")
                    if as_excel is not None:
                        try:
                            as_import_df = pd.read_csv(as_excel) if as_excel.name.lower().endswith('.csv') else pd.read_excel(as_excel)
                            st.dataframe(as_import_df.head(5), use_container_width=True, hide_index=True)
                            if st.button("🚀 دمج الأسئلة في بنك هذا القسم", key=f"as_import_btn_{chosen_as_id}", use_container_width=True):
                                added = skipped = 0
                                with db() as c:
                                    for _, row in as_import_df.iterrows():
                                        diff = str(row.get("difficulty", row.get("الصعوبة", "متوسط"))).strip()
                                        cat = str(row.get("category", row.get("المجال", categories_list_opts[0]))).strip()
                                        qt = str(row.get("question", row.get("السؤال", ""))).strip()
                                        raw_opts = row.get("options_json", row.get("الخيارات", '["نعم", "لا"]'))
                                        try: opts = json.loads(raw_opts) if isinstance(raw_opts, str) and raw_opts.strip().startswith("[") else [x.strip() for x in str(raw_opts).split(",") if x.strip()]
                                        except Exception: opts = ["نعم", "لا"]
                                        try: ans = int(row.get("answer", row.get("رقم الإجابة الصحيحة", 0)))
                                        except Exception: ans = 0
                                        if qt and opts:
                                            ans = max(0, min(ans, len(opts)-1))
                                            fp = hashlib.sha256((qt+"|"+"|".join(map(str,opts))+f"|administration_section|{chosen_as_id}").encode()).hexdigest()
                                            try:
                                                c.execute("INSERT INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at,scope_type,scope_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (diff,cat,qt,json.dumps(opts,ensure_ascii=False),ans,1,fp,now(),"administration_section",chosen_as_id)); added += 1
                                            except sqlite3.IntegrityError: skipped += 1
                                st.success(f"تمت إضافة {added} سؤال وتخطي {skipped} سؤال مكرر."); st.rerun()
                        except Exception as e: st.error(f"تعذر قراءة الملف: {e}")
                    with db() as c:
                        as_export_df = pd.read_sql_query("SELECT id,difficulty,category,question,options_json,answer FROM questions WHERE scope_type='administration_section' AND scope_id=? ORDER BY id", c, params=(chosen_as_id,))
                    if not as_export_df.empty:
                        as_out = io.BytesIO()
                        with pd.ExcelWriter(as_out, engine="openpyxl") as writer: as_export_df.to_excel(writer, index=False, sheet_name="QuestionBank")
                        st.download_button("📤 تصدير بنك هذا القسم Excel", data=as_out.getvalue(), file_name=f"administration_section_{chosen_as_id}_questions.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"as_export_{chosen_as_id}")
                    with st.form(f"as_clear_bank_{chosen_as_id}", clear_on_submit=True):
                        as_confirm = st.text_input("لتفريغ بنك هذا القسم فقط اكتب: حذف البنك", key=f"as_clear_confirm_{chosen_as_id}")
                        if st.form_submit_button("🗑 تفريغ بنك قسم الإدارة"):
                            if as_confirm.strip() == "حذف البنك":
                                with db() as c: c.execute("DELETE FROM questions WHERE scope_type='administration_section' AND scope_id=?", (chosen_as_id,))
                                st.success("تم تفريغ بنك هذا القسم فقط."); st.rerun()
                            else: st.warning("اكتب عبارة التأكيد بشكل صحيح.")

        with sub_q_manage_tabs[0]:
            if has_subtab_permission('⚙ إدارة الأسئلة', '➕ إضافة وتعديل وحذف فردي'):
                sub_img_tabs = st.tabs(["➕ إضافة", "✏ تعديل", "🗑 حذف"])
                with sub_img_tabs[0]:
                    if has_subtab_permission('⚙ إدارة الأسئلة', '➕ إضافة'):
                        if st.session_state.add_success_msg:
                            st.success(st.session_state.add_success_msg)
                            st.session_state.add_success_msg = ""
                        with st.form(key=f"add_q_form_{st.session_state.form_key}", clear_on_submit=True):
                            selected_cat = st.selectbox("المجال / القسم:", categories_list_opts)
                            c_text = st.text_area("نص السؤال:", value="")
                            c_diff = st.selectbox("الصعوبة:", ["سهل", "متوسط", "صعب"])
                            uploaded_img = st.file_uploader("رفع صورة مجهرية / توضيحية (اختياري):", type=["png", "jpg", "jpeg"])
                            opt1, opt2 = st.text_input("خيار 1:", value=""), st.text_input("خيار 2:", value="")
                            opt3, opt4 = st.text_input("خيار 3:", value=""), st.text_input("خيار 4:", value="")
                            correct_ans_text = st.text_input("الإجابة الصحيحة:", value="")
                            if st.form_submit_button("حفظ", use_container_width=True):
                                if c_text and correct_ans_text:
                                    img_uri_final = f"data:image/{uploaded_img.type.split('/')[-1]};base64," + __import__("base64").b64encode(uploaded_img.read()).decode("utf-8") if uploaded_img else ""
                                    full_q_str = f"IMAGE:{img_uri_final}\n\n{c_text}" if img_uri_final else c_text
                                    opts_list = [o for o in [opt1, opt2, opt3, opt4] if o.strip() != ""]
                                    if correct_ans_text not in opts_list:
                                        opts_list.append(correct_ans_text)
                                    ans_idx = opts_list.index(correct_ans_text)
                                    fp = hashlib.sha256((full_q_str + "|" + "|".join(opts_list)).encode("utf-8")).hexdigest()
                                    with db() as c:
                                        c.execute("INSERT INTO questions(difficulty,category,question,options_json,answer,active,fingerprint,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                                  (c_diff, selected_cat, full_q_str, json.dumps(opts_list, ensure_ascii=False), ans_idx, 1, fp, now()))
                                    st.session_state.add_success_msg = "✅ تم الإضافة!"
                                    st.session_state.form_key += 1
                                    st.rerun()
                with sub_img_tabs[1]:
                    if has_subtab_permission('⚙ إدارة الأسئلة', '✏ تعديل'):
                        with db() as c:
                            all_questions = c.execute("SELECT id, question, category FROM questions WHERE COALESCE(scope_type,'global')='global' ORDER BY id ASC").fetchall()
                        if all_questions:
                            q_options_map = {f"سؤال ({q['id']}) - {q['question'][:40]}...": q['id'] for q in all_questions}
                            selected_q_label = st.selectbox("اختر السؤال:", list(q_options_map.keys()))
                            selected_q_id = q_options_map[selected_q_label]
                            with db() as c:
                                q_data = c.execute("SELECT * FROM questions WHERE id=? AND COALESCE(scope_type,'global')='global'", (selected_q_id,)).fetchone()
                            if q_data:
                                current_opts = json.loads(q_data["options_json"])
                                while len(current_opts) < 4:
                                    current_opts.append("")
                                with st.form(f"edit_q_{selected_q_id}", clear_on_submit=True):
                                    e_cat = st.selectbox("المجال / القسم:", categories_list_opts, index=categories_list_opts.index(q_data["category"]) if q_data["category"] in categories_list_opts else 0)
                                    e_diff = st.selectbox("الصعوبة:", ["سهل", "متوسط", "صعب"], index=["سهل", "متوسط", "صعب"].index(q_data["difficulty"]) if q_data["difficulty"] in ["سهل", "متوسط", "صعب"] else 0)
                                    raw_q_db = q_data["question"]
                                    actual_text_editable = raw_q_db.replace("IMAGE:", "").split("\n\n")[-1] if "IMAGE:" in raw_q_db else raw_q_db
                                    e_text = st.text_area("نص السؤال:", value=actual_text_editable)
                                    e_o1, e_o2 = st.text_input("خيار 1:", value=str(current_opts[0])), st.text_input("خيار 2:", value=str(current_opts[1]))
                                    e_o3, e_o4 = st.text_input("خيار 3:", value=str(current_opts[2])), st.text_input("خيار 4:", value=str(current_opts[3]))
                                    e_correct = st.text_input("الإجابة الصحيحة:", value=current_opts[q_data["answer"]] if 0 <= q_data["answer"] < len(current_opts) else "")
                                    if st.form_submit_button("💾 حفظ", use_container_width=True):
                                        updated_opts = [o for o in [e_o1, e_o2, e_o3, e_o4] if o.strip() != ""]
                                        if e_correct not in updated_opts:
                                            updated_opts.append(e_correct)
                                        new_ans_idx = updated_opts.index(e_correct)
                                        prefix_img = raw_q_db.split("\n\n")[0] + "\n\n" if "IMAGE:" in raw_q_db else ""
                                        final_str = prefix_img + e_text
                                        new_fp = hashlib.sha256((final_str + "|" + "|".join(updated_opts)).encode("utf-8")).hexdigest()
                                        with db() as c:
                                            c.execute("UPDATE questions SET difficulty=?, category=?, question=?, options_json=?, answer=?, fingerprint=? WHERE id=?",
                                                      (e_diff, e_cat, final_str, json.dumps(updated_opts, ensure_ascii=False), new_ans_idx, new_fp, selected_q_id))
                                        st.success("✅ تم التعديل!")
                                        st.rerun()
                with sub_img_tabs[2]:
                    if has_subtab_permission('⚙ إدارة الأسئلة', '🗑 حذف'):
                        with db() as c:
                            all_questions_del = c.execute("SELECT id, question FROM questions WHERE COALESCE(scope_type,'global')='global' ORDER BY id ASC").fetchall()
                        if all_questions_del:
                            q_del_map = {f"سؤال رقم {q['id']} - {q['question'][:40]}": q['id'] for q in all_questions_del}
                            with st.form("delete_single_question_form", clear_on_submit=True):
                                selected_del_label = st.selectbox("اختر السؤال للحذف:", list(q_del_map.keys()))
                                if st.form_submit_button("🗑 حذف السؤال المحدد وإعادة الترتيب", use_container_width=True):
                                    with db() as c:
                                        c.execute("DELETE FROM questions WHERE id=? AND COALESCE(scope_type,'global')='global'", (q_del_map[selected_del_label],))
                                    reindex_questions()
                                    st.success("✅ تم الحذف وإعادة ترقيم بنك الأسئلة بنجاح!")
                                    st.rerun()

    elif selected_menu == "🧑‍🔬 المتدربين والنماذج":
        st.subheader("🧑🔬 إدارة واعتماد المتدربين والنماذج المرتبطة بهم")
        with db() as c:
            all_tpls_records = c.execute("SELECT * FROM exam_templates WHERE active=1 ORDER BY name ASC").fetchall()
        if all_tpls_records:
            tpl_names_list = [f"{row['name']} ({row['exam_type'] or 'قبل التدريب'}) | المهنة: {professions_display(row['profession'])} | {template_scope_text(dict(row))}" for row in all_tpls_records]
            tpl_map_dict = {f"{row['name']} ({row['exam_type'] or 'قبل التدريب'}) | المهنة: {professions_display(row['profession'])} | {template_scope_text(dict(row))}": row["id"] for row in all_tpls_records}
        else:
            tpl_names_list = ["لا توجد نماذج اختبارات مسجلة"]
            tpl_map_dict = {}
        sub_tabs = st.tabs(["📅 مواعيد الامتحانات والهيكل الإداري", "🆕 قبول المسجلين الجدد", "جميع المتدربين (إدارة وإخفاء/إظهار/حذف)", "📝 طباعة نموذج امتحان الممتحن"])
        with sub_tabs[0]:
            st.markdown("#### 📅 تحديد مواعيد الامتحانات وربطها بالهيكل الإداري")
            st.caption("يُحفظ الموعد لكل نموذج ولكل نطاق إداري بصورة مستقلة. واجهة الممتحن تعتمد هذه المواعيد تلقائياً؛ لن يظهر الاختبار قبل وقت البدء أو بعد وقت الانتهاء، ويُراعى الهيكل الإداري ومهنة المتدرب.")
            with db() as c:
                schedule_templates = [dict(r) for r in c.execute("SELECT * FROM exam_templates WHERE active=1 ORDER BY name ASC, id ASC").fetchall()]
            if not schedule_templates:
                st.info("أنشئ نموذج امتحان أولاً من تبويب «إنشاء و تعديل و حذف النماذج».")
            else:
                schedule_template_map = {f"{t['name']} [{t.get('exam_type') or 'قبل التدريب'}] — رقم {t['id']}": t for t in schedule_templates}
                schedule_template_label = st.selectbox("نموذج الامتحان:", list(schedule_template_map.keys()), key="trainee_schedule_template_v1")
                schedule_template = schedule_template_map[schedule_template_label]
                if str(schedule_template.get("exam_type") or "") == "قبل وبعد التدريب (نفس النموذج)":
                    schedule_stage = st.selectbox("مرحلة هذا الموعد:", ["قبل التدريب", "بعد التدريب"], key=f"trainee_sched_stage_{schedule_template['id']}")
                else:
                    schedule_stage = str(schedule_template.get("exam_type") or "قبل التدريب")
                    st.caption(f"مرحلة النموذج: {schedule_stage}")
                schedule_scope = hierarchy_scope_widget("الهيكل الإداري المستهدف للامتحان:", f"trainee_schedule_scope_{schedule_template['id']}")
                schedule_scope_keys = ("scope_governorate", "scope_authority", "scope_directorate_section", "scope_center", "scope_administration", "scope_administration_section", "scope_facility")
                schedule_scope_values = {k: str(schedule_scope.get(k) or "").strip() for k in schedule_scope_keys}
                with db() as c:
                    schedules_for_template = [dict(r) for r in c.execute("SELECT * FROM exam_schedules WHERE template_id=? AND active=1 ORDER BY id DESC", (schedule_template['id'],)).fetchall()]
                matched_schedule = next((r for r in schedules_for_template if str(r.get('stage') or '') == schedule_stage and all(str(r.get(k) or '').strip() == schedule_scope_values[k] for k in schedule_scope_keys)), None)
                def _trainee_schedule_dt(value, fallback):
                    try:
                        dt = datetime.fromisoformat(str(value))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=CAIRO_TZ)
                        return dt.astimezone(CAIRO_TZ)
                    except Exception:
                        return fallback
                schedule_now = now_cairo()
                start_default = _trainee_schedule_dt(matched_schedule.get('start_time') if matched_schedule else None, schedule_now + timedelta(days=1))
                end_default = _trainee_schedule_dt(matched_schedule.get('end_time') if matched_schedule else None, schedule_now + timedelta(days=1, hours=1))
                with st.form(f"trainee_schedule_form_{schedule_template['id']}", clear_on_submit=False):
                    st.markdown("##### بداية إتاحة الامتحان")
                    sc1, sc2 = st.columns(2)
                    def _time12_controls(label, dt_value, key_prefix):
                        st.markdown(f"**{label} (نظام 12 ساعة)**")
                        hour24 = dt_value.hour
                        hour12_default = hour24 % 12 or 12
                        ampm_default = "مساءً" if hour24 >= 12 else "صباحًا"
                        tc1, tc2, tc3 = st.columns([1, 1, 1])
                        with tc1:
                            h12 = st.selectbox("الساعة", list(range(1, 13)), index=hour12_default-1, key=f"{key_prefix}_h")
                        with tc2:
                            minute = st.selectbox("الدقيقة", list(range(0, 60)), index=dt_value.minute, format_func=lambda x: f"{x:02d}", key=f"{key_prefix}_m")
                        with tc3:
                            ampm = st.selectbox("الفترة", ["صباحًا", "مساءً"], index=["صباحًا", "مساءً"].index(ampm_default), key=f"{key_prefix}_ampm")
                        h24 = (h12 % 12) + (12 if ampm == "مساءً" else 0)
                        return datetime_time(hour=h24, minute=minute)
                    with sc1:
                        schedule_start_date = st.date_input("تاريخ البدء", value=start_default.date(), key=f"trainee_sched_sd_{schedule_template['id']}")
                        schedule_start_time = _time12_controls("وقت البدء", start_default, f"trainee_sched_st_{schedule_template['id']}")
                    with sc2:
                        schedule_end_date = st.date_input("تاريخ الانتهاء", value=end_default.date(), key=f"trainee_sched_ed_{schedule_template['id']}")
                        schedule_end_time = _time12_controls("وقت الانتهاء", end_default, f"trainee_sched_et_{schedule_template['id']}")
                    schedule_profession_options = list(get_print_settings().get("professions_list", ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"]))
                    for _existing_prof in parse_professions(matched_schedule.get('profession') if matched_schedule else ""):
                        if _existing_prof not in schedule_profession_options:
                            schedule_profession_options.append(_existing_prof)
                    selected_schedule_professions = st.multiselect("المهن المسموح لها بأداء الامتحان (اتركها فارغة لكل المهن):", schedule_profession_options, default=parse_professions(matched_schedule.get('profession') if matched_schedule else ""), key=f"trainee_sched_prof_{schedule_template['id']}")
                    save_schedule = st.form_submit_button("💾 حفظ / تحديث موعد الامتحان", use_container_width=True)
                if save_schedule:
                    if not any(schedule_scope_values.values()):
                        st.error("اختر هيكلاً إدارياً محدداً قبل حفظ الموعد.")
                    else:
                        start_iso = datetime.combine(schedule_start_date, schedule_start_time, tzinfo=CAIRO_TZ).isoformat(timespec="seconds")
                        end_iso = datetime.combine(schedule_end_date, schedule_end_time, tzinfo=CAIRO_TZ).isoformat(timespec="seconds")
                        if datetime.fromisoformat(end_iso) <= datetime.fromisoformat(start_iso):
                            st.error("تاريخ ووقت الانتهاء يجب أن يكونا بعد تاريخ ووقت البدء.")
                        else:
                            profession_json = json.dumps(selected_schedule_professions, ensure_ascii=False) if selected_schedule_professions else ""
                            with db() as c:
                                current_match = c.execute("SELECT id FROM exam_schedules WHERE template_id=? AND active=1 AND stage=? AND scope_governorate=? AND scope_authority=? AND scope_center=? AND scope_administration=? AND scope_facility=? AND scope_directorate_section=? AND scope_administration_section=? ORDER BY id DESC LIMIT 1", (schedule_template['id'], schedule_stage, schedule_scope_values.get("scope_governorate", ""), schedule_scope_values.get("scope_authority", ""), schedule_scope_values.get("scope_center", ""), schedule_scope_values.get("scope_administration", ""), schedule_scope_values.get("scope_facility", ""), schedule_scope_values.get("scope_directorate_section", ""), schedule_scope_values.get("scope_administration_section", ""))).fetchone()
                                if current_match:
                                    c.execute("UPDATE exam_schedules SET start_time=?, end_time=?, profession=?, stage=?, scope_directorate_section=?, scope_administration_section=?, updated_at=? WHERE id=?", (start_iso, end_iso, profession_json, schedule_stage, schedule_scope_values.get("scope_directorate_section", ""), schedule_scope_values.get("scope_administration_section", ""), now(), current_match['id']))
                                else:
                                    c.execute("INSERT INTO exam_schedules(template_id,scope_governorate,scope_authority,scope_center,scope_administration,scope_facility,scope_directorate_section,scope_administration_section,start_time,end_time,profession,stage,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)", (schedule_template['id'], schedule_scope_values.get("scope_governorate", ""), schedule_scope_values.get("scope_authority", ""), schedule_scope_values.get("scope_center", ""), schedule_scope_values.get("scope_administration", ""), schedule_scope_values.get("scope_facility", ""), schedule_scope_values.get("scope_directorate_section", ""), schedule_scope_values.get("scope_administration_section", ""), start_iso, end_iso, profession_json, schedule_stage, now(), now()))
                            st.success("تم حفظ موعد الامتحان وربطه بالنموذج والهيكل الإداري المحددين.")
                            st.rerun()
                if schedules_for_template:
                    st.markdown("##### المواعيد المسجلة لهذا النموذج")
                    for sched in schedules_for_template:
                        scope_desc = " / ".join(str(sched.get(k) or "").strip() for k in schedule_scope_keys if str(sched.get(k) or "").strip()) or "غير محدد"
                        def _schedule_display_dt(value):
                            try:
                                parsed = datetime.fromisoformat(str(value))
                                if parsed.tzinfo is None:
                                    parsed = parsed.replace(tzinfo=CAIRO_TZ)
                                return parsed.astimezone(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p").replace("AM", "صباحاً").replace("PM", "مساءً")
                            except Exception:
                                return str(value or "غير محدد")
                        start_display = _schedule_display_dt(sched.get('start_time'))
                        end_display = _schedule_display_dt(sched.get('end_time'))
                        st.markdown(f"**{scope_desc}** — من <span dir='ltr'>{esc(start_display)}</span> إلى <span dir='ltr'>{esc(end_display)}</span> — المرحلة: {esc(sched.get('stage') or 'غير محددة')} — المهن: {esc(professions_display(sched.get('profession')) if sched.get('profession') else 'كل المهن')}", unsafe_allow_html=True)
                        if st.button("🗑 حذف هذا الموعد", key=f"delete_trainee_schedule_{sched['id']}"):
                            with db() as c:
                                c.execute("DELETE FROM exam_schedules WHERE id=?", (sched['id'],))
                            st.success("تم حذف الموعد المحدد.")
                            st.rerun()

        with sub_tabs[1]:
            if has_subtab_permission('🧑\u200d🔬 المتدربين والنماذج', '🆕 قبول المسجلين الجدد'):
                st.markdown("#### 🆕 قبول المسجلين الجدد وتعديل بياناتهم")
                st.caption("يمكن البحث بالرقم القومي، تعديل بيانات الطلب قبل الاعتماد، ثم اختيار نموذج الاختبار وفق الهيكل الإداري.")
                search_nid = st.text_input("🔎 بحث عن متدرب بالرقم القومي:", value="", max_chars=14, key="pending_nid_search")
                search_digits = normalize_national_id(search_nid)
                if search_digits:
                    search_scope_pred, search_scope_args = hierarchy_filter_for_trainees(current_user_trainee_scope(), "t")
                    with db() as c:
                        search_rows = c.execute(f"SELECT t.* FROM trainees t WHERE t.national_id=? AND {search_scope_pred} ORDER BY t.id DESC", (search_digits, *search_scope_args)).fetchall()
                    if search_rows:
                        st.success(f"تم العثور على {len(search_rows)} سجل مطابق للرقم القومي.")
                        for sr in search_rows:
                            st.info(f"ID: {sr['id']} | الاسم: {sr['name']} | الهاتف: {sr['phone']} | الحالة: {sr['status']} | الجهة: {sr['facility']}")
                    elif len(search_digits) == 14:
                        st.warning("لا يوجد متدرب مسجل بهذا الرقم القومي.")

                df_pend = trainees_df("pending", include_hidden=False)
                if df_pend.empty:
                    st.info("لا توجد طلبات تسجيل جديدة معلقة حالياً.")
                else:
                    for _, r in df_pend.iterrows():
                        with st.container(border=True):
                            st.markdown(f"### 👤 طلب تسجيل رقم {int(r['id'])}")
                            with st.form(f"approve_edit_form_{int(r['id'])}", clear_on_submit=True):
                                edit_name = st.text_input("اسم المتدرب:", value=str(r.get('name') or ''), key=f"pend_name_{int(r['id'])}")
                                ec1, ec2 = st.columns(2)
                                with ec1:
                                    edit_nid = st.text_input("الرقم القومي:", value=str(r.get('national_id') or ''), max_chars=14, key=f"pend_nid_{int(r['id'])}")
                                with ec2:
                                    edit_phone = st.text_input("رقم الهاتف / المعرف الرئيسي:", value=str(r.get('phone') or ''), key=f"pend_phone_{int(r['id'])}")
                                ec3, ec4 = st.columns(2)
                                with ec3:
                                    edit_prof = st.text_input("الوظيفة:", value=str(r.get('profession') or 'أخصائي الأمراض المتوطنة'), key=f"pend_prof_{int(r['id'])}")
                                with ec4:
                                    edit_facility = st.text_input("جهة العمل / المنشأة:", value=str(r.get('facility') or ''), key=f"pend_fac_{int(r['id'])}")
                                applicable_tpls = [t for t in all_tpls_records if template_matches_facility(t, edit_facility)]
                                applicable_labels = [f"{t['name']} ({t['exam_type'] or 'قبل التدريب'}) | {template_scope_text(dict(t))}" for t in applicable_tpls] or ["لا يوجد نموذج ضمن نطاق هذه الجهة"]
                                applicable_map = {f"{t['name']} ({t['exam_type'] or 'قبل التدريب'}) | {template_scope_text(dict(t))}": t['id'] for t in applicable_tpls}
                                chosen_tpl = st.selectbox("نموذج الاختبار المخصص حسب الهيكل الإداري:", applicable_labels, key=f"app_tpl_{int(r['id'])}")
                                bc1, bc2, bc3 = st.columns(3)
                                with bc1:
                                    save_data_btn = st.form_submit_button("💾 حفظ تعديل البيانات", use_container_width=True)
                                with bc2:
                                    app_btn = st.form_submit_button("✅ اعتماد", use_container_width=True)
                                with bc3:
                                    rej_btn = st.form_submit_button("❌ رفض", use_container_width=True)
                                if save_data_btn or app_btn:
                                    digits_nid = normalize_national_id(edit_nid)
                                    phone_norm = normalize_egyptian_phone(edit_phone)
                                    if not edit_name.strip() or not phone_norm or not edit_facility.strip():
                                        st.error("⚠ يجب استكمال الاسم والهاتف وجهة العمل.")
                                    elif not is_valid_egyptian_national_id(digits_nid):
                                        st.error("⚠ الرقم القومي غير صحيح؛ راجع 14 رقماً وتاريخ الميلاد وكود المحافظة.")
                                    elif not is_valid_egyptian_mobile(phone_norm):
                                        st.error("⚠ رقم الموبايل المصري غير صحيح.")
                                    else:
                                        try:
                                            update_trainee_data(int(r['id']), edit_facility.strip(), edit_name.strip(), phone_norm, digits_nid, edit_prof.strip())
                                            if app_btn:
                                                if applicable_map and chosen_tpl in applicable_map:
                                                    set_trainee_status_and_template(int(r['id']), "approved", applicable_map[chosen_tpl])
                                                    st.success("✅ تم حفظ البيانات واعتماد المتدرب بنجاح.")
                                                    st.rerun()
                                                else:
                                                    st.warning("⚠ تم حفظ البيانات، لكن يجب تحديد نموذج اختبار صحيح للاعتماد.")
                                            else:
                                                st.success("✅ تم حفظ تعديلات بيانات المتدرب بنجاح.")
                                                st.rerun()
                                        except ValueError as e:
                                            if str(e) == "DUPLICATE_TRAINEE_PHONE":
                                                st.error("❌ رقم الهاتف مستخدم بالفعل لمتدرب آخر، ولا يمكن تكراره.")
                                            elif str(e) == "DUPLICATE_TRAINEE_NATIONAL_ID":
                                                st.error("❌ الرقم القومي مستخدم بالفعل لمتدرب آخر، ولا يمكن تكراره.")
                                            elif str(e) == "INVALID_TRAINEE_PHONE":
                                                st.error("❌ رقم الموبايل المصري غير صحيح.")
                                            elif str(e) == "INVALID_TRAINEE_NATIONAL_ID":
                                                st.error("❌ الرقم القومي غير صحيح.")
                                            else:
                                                st.error(f"تعذر حفظ البيانات: {e}")
                                if rej_btn:
                                    set_trainee_status_and_template(int(r['id']), "rejected", r.get('assigned_template_id'))
                                    st.warning("تم رفض طلب التسجيل.")
                                    st.rerun()
        with sub_tabs[2]:
            if has_subtab_permission('🧑\u200d🔬 المتدربين والنماذج', 'جميع المتدربين (إدارة وإخفاء/إظهار/حذف)'):
                st.markdown("#### 🏥 فلترة المتدربين حسب الهيكل الإداري")
                tr_scope_manage = hierarchy_scope_widget("نطاق المتدربين:", "trainees_manage_scope_v1")
                tr_scope_pred, tr_scope_args = hierarchy_filter_for_trainees(tr_scope_manage, "t")
                with db() as c:
                    scoped_ids = [r[0] for r in c.execute(f"SELECT t.id FROM trainees t WHERE {tr_scope_pred}", tuple(tr_scope_args)).fetchall()]
                df_all_tr = trainees_df(include_hidden=True)
                if not df_all_tr.empty and any(str(tr_scope_manage.get(k) or "").strip() for k in ("scope_governorate", "scope_authority", "scope_directorate_section", "scope_center", "scope_administration", "scope_administration_section", "scope_facility")):
                    df_all_tr = df_all_tr[df_all_tr["id"].isin(scoped_ids)]
                if df_all_tr.empty:
                    st.info("لا توجد بيانات متدربين مسجلة.")
                else:
                    st.dataframe(df_all_tr[['id', 'name', 'profession', 'facility', 'status']], use_container_width=True, hide_index=True)
                    with st.form("manage_trainee_action_form", clear_on_submit=True):
                        tr_map_options = {f"ID ({row['id']}) - {row['name']} [{row['status']}]": row['id'] for _, row in df_all_tr.iterrows()}
                        selected_tr_label = st.selectbox("اختر المتدرب للإدارة والتعديل:", list(tr_map_options.keys()))
                        target_tr_id = tr_map_options[selected_tr_label]
                        target_chosen_tpl = st.selectbox("تعديل نموذج الاختبار للمتدرب:", tpl_names_list, key="mod_tr_tpl_sel")
                        col_u1, col_u2, col_u3, col_u4 = st.columns(4)
                        with col_u1:
                            upd_t_btn = st.form_submit_button("💾 تحديث", use_container_width=True)
                        with col_u2:
                            hide_t_btn = st.form_submit_button("👁🗨 إخفاء", use_container_width=True)
                        with col_u3:
                            show_t_btn = st.form_submit_button("✅ إظهار", use_container_width=True)
                        with col_u4:
                            del_t_btn = st.form_submit_button("🗑 حذف", use_container_width=True)
                        if upd_t_btn:
                            if tpl_map_dict and target_chosen_tpl in tpl_map_dict:
                                set_trainee_status_and_template(int(target_tr_id), "approved", tpl_map_dict[target_chosen_tpl])
                                st.success("✅ تم تحديث نموذج المتدرب بنجاح!")
                                st.rerun()
                        if hide_t_btn:
                            with db() as c:
                                enforce_trainee_scope_or_raise(int(target_tr_id), c)
                                c.execute("UPDATE trainees SET hidden=1 WHERE id=?", (int(target_tr_id),))
                            st.success("✅ تم إخفاء المتدرب بنجاح!")
                            st.rerun()
                        if show_t_btn:
                            with db() as c:
                                enforce_trainee_scope_or_raise(int(target_tr_id), c)
                                c.execute("UPDATE trainees SET hidden=0 WHERE id=?", (int(target_tr_id),))
                            st.success("✅ تم إظهار المتدرب بنجاح!")
                            st.rerun()
                        if del_t_btn:
                            with db() as c:
                                c.execute("PRAGMA foreign_keys=OFF;")
                                c.execute("DELETE FROM trainees WHERE id=?", (int(target_tr_id),))
                                c.execute("DELETE FROM exam_sessions WHERE trainee_id=?", (int(target_tr_id),))
                                c.execute("PRAGMA foreign_keys=ON;")
                            reindex_trainees()
                            st.success("✅ تم الحذف وإعادة الترتيب بنجاح!")
                            st.rerun()
        with sub_tabs[3]:
            if has_subtab_permission('🧑\u200d🔬 المتدربين والنماذج', '📝 طباعة نموذج امتحان الممتحن'):
                st.markdown("#### 📝 طباعة نموذج امتحان الإجابة والأسئلة لممتحن أدى الامتحان على البرنامج:")
                exam_print_scope = hierarchy_scope_widget("نطاق طباعة نماذج الإجابة:", "exam_print_scope_v1")
                exam_scope_pred, exam_scope_args = hierarchy_filter_for_trainees(exam_print_scope, "t")
                with db() as c:
                    completed_sessions = c.execute(f"""
                        SELECT s.id, t.name trainee_name, t.facility, t.profession trainee_profession, s.submitted_at, s.started_at, e.name template_name, e.exam_type
                        FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id
                        WHERE s.status='submitted' AND t.hidden=0 AND {exam_scope_pred} ORDER BY s.id DESC
                    """, tuple(exam_scope_args)).fetchall()
                if not completed_sessions:
                    st.info("لا توجد اختبارات مكتملة مسجلة للممتحنين الظاهرين حتى الآن.")
                else:
                    exam_records_map = {f"المتدرب: {r['trainee_name']} | الوظيفة: {r['trainee_profession']} | الجهة: {r['facility']} | الاختبار: {r['template_name'] or 'موافق'} ({r['exam_type'] or 'قبل التدريب'}) | التاريخ: {r['submitted_at'] or r['started_at']} (ID: {r['id']})": r['id'] for r in completed_sessions}
                    sel_exam_rec_label = st.selectbox("اختر الممتحن وتاريخ الامتحان:", list(exam_records_map.keys()))
                    chosen_exam_session_id = exam_records_map[sel_exam_rec_label]
                    trainee_exam_sheet_html = generate_trainee_exam_sheet_html(chosen_exam_session_id)
                    st.markdown("<br>", unsafe_allow_html=True)
                    render_print_button_only(trainee_exam_sheet_html, f"نموذج إجابة الامتحان للممتحن رقم {chosen_exam_session_id}")

    elif selected_menu == "🧪 إنشاء و تعديل و حذف النماذج":
        st.subheader("🧪 إنشاء و تعديل و حذف النماذج")
        sub_tpl_mode = st.radio("القسم:", ["📋 عرض النماذج وطباعة الأسئلة", "➕ إنشاء نموذج جديد", "✏️ تعديل نموذج", "🗑 حذف نموذج"], horizontal=True)
        if sub_tpl_mode == "📋 عرض النماذج وطباعة الأسئلة":
            st.markdown("#### 🏥 فلترة طباعة النماذج حسب الهيكل الإداري")
            tpl_print_scope = hierarchy_scope_widget("نطاق طباعة نماذج الاختبار:", "template_print_scope_v1")
            scope_keys = ("scope_governorate", "scope_authority", "scope_directorate_section", "scope_center", "scope_administration", "scope_administration_section", "scope_facility")
            scope_values = [str(tpl_print_scope.get(k) or "").strip() for k in scope_keys]
            with db() as c:
                all_tpl_rows = [dict(r) for r in c.execute("SELECT * FROM exam_templates ORDER BY name ASC, id ASC").fetchall()]
            def _template_in_print_scope(template_row):
                if not any(scope_values):
                    return True
                template_scope_values = [str(template_row.get(k) or "").strip() for k in ("scope_governorate", "scope_authority", "scope_directorate_section", "scope_center", "scope_administration", "scope_administration_section", "scope_facility")]

                if not any(template_scope_values):
                    return True
                return all(not template_scope_values[i] or template_scope_values[i] == scope_values[i] for i in range(len(scope_values))) and all(not scope_values[i] or not template_scope_values[i] or template_scope_values[i] == scope_values[i] for i in range(len(scope_values)))
            tpls = [t for t in all_tpl_rows if _template_in_print_scope(t)]
            if not tpls:
                st.info("لا توجد نماذج اختبارات مسجلة حتى الآن.")
            else:
                tpl_dropdown_map = {f"نموذج ({t['id']}) - {t['name']} [{t['exam_type']}] | {template_scope_text(dict(t))}": t for t in tpls}
                selected_dropdown_label = st.selectbox("🔍 اختر نموذج الاختبار من القائمة المنسدلة لعرضه وطباعته:", list(tpl_dropdown_map.keys()))
                if selected_dropdown_label:
                    t_dict = dict(tpl_dropdown_map[selected_dropdown_label])
                    num_q_display = "مفتوح" if int(t_dict.get('num_questions', 999999)) >= 999900 else t_dict.get('num_questions')
                    s_t = t_dict.get('start_time') or "غير محدد"
                    e_t = t_dict.get('end_time') or "غير محدد"
                    exam_type_badge = t_dict.get('exam_type', 'قبل التدريب')
                    def format_12h(iso_str):
                        if not iso_str or "T" not in iso_str:
                            return iso_str
                        try:
                            dt = datetime.fromisoformat(iso_str)
                            return dt.strftime("%Y-%m-%d %I:%M %p").replace("AM", "صباحاً").replace("PM", "مساءً")
                        except:
                            return iso_str
                    with st.container(border=True):
                        st.markdown(f"#### 🏷 نموذج ({t_dict.get('id')}): {t_dict.get('name')} &nbsp;|&nbsp; <span style='color: #059669; font-size: 14px;'>[{exam_type_badge}]</span>", unsafe_allow_html=True)
                        st.write(f"🔹 البدء: `{format_12h(s_t)}` | 🔸 النهاية: `{format_12h(e_t)}` | 📝 الأسئلة: {num_q_display}")
                        st.info(f"👷 المهنة المخصصة: **{professions_display(t_dict.get('profession'))}**  \n\n🏥 نطاق الهيكل الإداري للنموذج: **{template_scope_text(t_dict)}**")
                        exam_template_html_out = generate_exam_template_print_html(t_dict.get('id'), hierarchy_scope=tpl_print_scope)
                        render_print_button_only(exam_template_html_out, f"نموذج امتحان رقم {t_dict.get('id')}")
        elif sub_tpl_mode == "➕ إنشاء نموذج جديد":
            categories_pool_opts = [
                "الاستراتيجية العامة ومكافحة البلهارسيا", "البلهارسيا", "علاج البلهارسيا", "الفاشيولا", "علاج الفاشيولا", "الهتروفيس", "التينيا", "هيمنولبس نانا", "الإسكارس", "الأنكلستوما", "الأكسيورس", "تركيورس تركيورا", "Strongyloides stercoralis", "Entamoeba histolytica", "Giardia lamblia", "الفحوصات الطفيلية والتشخيصية", "فحص البول (بلهارسيا المجاري البولية)", "فحص البراز (طفيليات المعوية)", "طرق فحص البراز المعتمدة", "الترسيب", "التعويم", "اللطخة المباشرة", "التصفية الغشائية", "Kato-Katz", "تحضير وعزل العينات", "أسئلة الصور والأشكال المجهرية"
            ]
            tpl_profession_options = ["كل الوظائف"] + list(get_print_settings().get("professions_list", ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"]))
            with st.form("create_template_schedule_form", clear_on_submit=True):
                new_tpl_name = st.text_input("اسم النموذج:", value="")
                new_tpl_professions = st.multiselect("المهن المسموح لها بأداء هذا الاختبار:", tpl_profession_options, default=["كل الوظائف"], help="يمكن اختيار أكثر من مهنة. اختيار «كل الوظائف» يتيح النموذج لجميع المهن.")
                st.markdown("#### 🎯 تحديد تصنيف نموذج الاختبار:")
                new_exam_type = st.radio("نوع النموذج:", ["قبل التدريب", "بعد التدريب", "تقييم شامل", "قبل وبعد التدريب (نفس النموذج)"], horizontal=True, help="اختيار قبل وبعد يتيح للمتدرب أداء النموذج نفسه في المرحلتين، وتُحفظ كل محاولة بمرحلتها.")
                is_open_questions = st.checkbox("عدد أسئلة مفتوح (كامل البنك)", value=True)
                new_tpl_num_q = st.number_input("عدد الأسئلة:", min_value=1, max_value=5000, value=50)
                new_tpl_duration = st.number_input("المدة (بالدقائق):", min_value=5, max_value=300, value=60)
                new_tpl_pass = st.number_input("نسبة النجاح %:", min_value=0.0, max_value=100.0, value=60.0, step=1.0, help="استخدم + و− لزيادة أو تقليل نسبة النجاح من 0 إلى 100%.")
                new_tpl_cats = st.multiselect("المجالات / الأقسام:", categories_pool_opts)
                if st.form_submit_button("💾 حفظ النموذج", use_container_width=True):
                    if new_tpl_name.strip():
                        with db() as c:
                            if new_tpl_cats:
                                placeholders = ','.join(['?'] * len(new_tpl_cats))
                                img_q_cnt = c.execute(f"SELECT COUNT(*) FROM questions WHERE active=1 AND category IN ({placeholders}) AND question LIKE '%IMAGE:%'", new_tpl_cats).fetchone()[0]
                            else:
                                img_q_cnt = c.execute("SELECT COUNT(*) FROM questions WHERE active=1 AND question LIKE '%IMAGE:%'").fetchone()[0]
                        
                        if "أسئلة الصور والأشكال المجهرية" in new_tpl_cats and img_q_cnt < 4:
                            st.warning(f"⚠ عذراً، عدد الأسئلة المصورة المتاحة في النطاق المحدد هو ({img_q_cnt}), ويجب ألا يقل عن 4 أسئلة مصورة عند اختيار تصنيف الأشكال والصور.")
                        else:
                            final_num_q = 999999 if is_open_questions else int(new_tpl_num_q)
                            with db() as c:
                                c.execute("""INSERT INTO exam_templates(
                                    name, exam_type, num_questions, duration_minutes, pass_percent, categories_json,
                                    start_time, end_time, created_at, scope_governorate, scope_authority, scope_center,
                                    scope_administration, scope_facility, scope_directorate_section, scope_administration_section, profession
                                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                          (new_tpl_name.strip(), new_exam_type, final_num_q, int(new_tpl_duration), float(new_tpl_pass),
                                           json.dumps(new_tpl_cats, ensure_ascii=False), None, None, now(), "", "", "", "", "", "", "",
                                           "" if not new_tpl_professions or "كل الوظائف" in new_tpl_professions else json.dumps(new_tpl_professions, ensure_ascii=False)))
                            st.success("✅ تم إنشاء نموذج الاختبار بنجاح. حدّد موعد إتاحته والهيكل الإداري من أول قسم في تبويب (المتدربين والنماذج).")
                            st.rerun()
        elif sub_tpl_mode == "✏️ تعديل نموذج":
            with db() as c:
                editable_templates = [dict(r) for r in c.execute("SELECT * FROM exam_templates ORDER BY name ASC, id ASC").fetchall()]
            if not editable_templates:
                st.info("لا توجد نماذج لتعديلها. أنشئ نموذجًا أولاً.")
            else:
                edit_tpl_map = {f"نموذج ({t['id']}) - {t['name']} [{t['exam_type']}]": t for t in editable_templates}
                chosen_edit_label = st.selectbox("اختر النموذج المراد تعديله:", list(edit_tpl_map.keys()), key="edit_template_pick_v1")
                edit_tpl = edit_tpl_map[chosen_edit_label]
                categories_pool_opts = [
                    "الاستراتيجية العامة ومكافحة البلهارسيا", "البلهارسيا", "علاج البلهارسيا", "الفاشيولا", "علاج الفاشيولا", "الهتروفيس", "التينيا", "هيمنولبس نانا", "الإسكارس", "الأنكلستوما", "الأكسيورس", "تركيورس تركيورا", "Strongyloides stercoralis", "Entamoeba histolytica", "Giardia lamblia", "الفحوصات الطفيلية والتشخيصية", "فحص البول (بلهارسيا المجاري البولية)", "فحص البراز (طفيليات المعوية)", "طرق فحص البراز المعتمدة", "الترسيب", "التعويم", "اللطخة المباشرة", "التصفية الغشائية", "Kato-Katz", "تحضير وعزل العينات", "أسئلة الصور والأشكال المجهرية"
                ]
                tpl_profession_options = ["كل الوظائف"] + list(get_print_settings().get("professions_list", ["أخصائي الأمراض المتوطنة", "طبيب بيطري", "أخصائي ميكروبيولوجي", "فني صحي متوطنة", "فني تمريض", "مسؤول وحدة متوطنة", "مراقب صحي", "أخصائي پاراتاسيتولوجي (طفيليات متوطنة)"]))
                try:
                    saved_categories = json.loads(edit_tpl.get("categories_json") or "[]")
                except Exception:
                    saved_categories = []
                try:
                    saved_professions = json.loads(edit_tpl.get("profession") or "[]") if edit_tpl.get("profession") else ["كل الوظائف"]
                except Exception:
                    saved_professions = ["كل الوظائف"]
                saved_professions = [p for p in saved_professions if p in tpl_profession_options]
                if not saved_professions:
                    saved_professions = ["كل الوظائف"]
                try:
                    saved_num_q = int(edit_tpl.get("num_questions") or 50)
                except Exception:
                    saved_num_q = 50
                is_open_saved = saved_num_q >= 999900
                with st.form("edit_exam_template_form_v1", clear_on_submit=False):
                    edit_tpl_name = st.text_input("اسم النموذج:", value=str(edit_tpl.get("name") or ""))
                    edit_tpl_professions = st.multiselect("المهن المسموح لها بأداء هذا الاختبار:", tpl_profession_options, default=saved_professions, help="يمكن اختيار أكثر من مهنة. اختيار «كل الوظائف» يتيح النموذج لجميع المهن.")
                    exam_types = ["قبل التدريب", "بعد التدريب", "تقييم شامل", "قبل وبعد التدريب (نفس النموذج)"]
                    current_exam_type = edit_tpl.get("exam_type") if edit_tpl.get("exam_type") in exam_types else "قبل التدريب"
                    edit_exam_type = st.radio("نوع النموذج:", exam_types, index=exam_types.index(current_exam_type), horizontal=True)
                    edit_is_open = st.checkbox("عدد أسئلة مفتوح (كامل البنك)", value=is_open_saved)
                    edit_num_q = st.number_input("عدد الأسئلة:", min_value=1, max_value=5000, value=min(5000, max(1, saved_num_q if not is_open_saved else 50)))
                    edit_duration = st.number_input("المدة (بالدقائق):", min_value=5, max_value=300, value=min(300, max(5, int(edit_tpl.get("duration_minutes") or 60))))
                    edit_pass = st.number_input("نسبة النجاح %:", min_value=0.0, max_value=100.0, value=min(100.0, max(0.0, float(edit_tpl.get("pass_percent") or 60))), step=1.0)
                    edit_cats = st.multiselect("المجالات / الأقسام:", categories_pool_opts, default=[x for x in saved_categories if x in categories_pool_opts])
                    if st.form_submit_button("💾 حفظ تعديلات النموذج", use_container_width=True):
                        if not edit_tpl_name.strip():
                            st.warning("اكتب اسم النموذج أولاً.")
                        elif not edit_tpl_professions:
                            st.warning("اختر مهنة واحدة على الأقل أو اختر كل الوظائف.")
                        else:
                            with db() as c:
                                if edit_cats:
                                    placeholders = ",".join(["?"] * len(edit_cats))
                                    img_q_cnt = c.execute(f"SELECT COUNT(*) FROM questions WHERE active=1 AND category IN ({placeholders}) AND question LIKE '%IMAGE:%'", edit_cats).fetchone()[0]
                                else:
                                    img_q_cnt = c.execute("SELECT COUNT(*) FROM questions WHERE active=1 AND question LIKE '%IMAGE:%'").fetchone()[0]
                                if "أسئلة الصور والأشكال المجهرية" in edit_cats and img_q_cnt < 4:
                                    st.warning(f"⚠ عدد الأسئلة المصورة المتاحة هو ({img_q_cnt})، ويجب ألا يقل عن 4 عند اختيار تصنيف الصور.")
                                else:
                                    final_edit_num_q = 999999 if edit_is_open else int(edit_num_q)
                                    profession_value = "" if "كل الوظائف" in edit_tpl_professions else json.dumps(edit_tpl_professions, ensure_ascii=False)
                                    c.execute("""UPDATE exam_templates SET name=?, exam_type=?, num_questions=?, duration_minutes=?, pass_percent=?, categories_json=?, profession=? WHERE id=?""",
                                              (edit_tpl_name.strip(), edit_exam_type, final_edit_num_q, int(edit_duration), float(edit_pass), json.dumps(edit_cats, ensure_ascii=False), profession_value, int(edit_tpl["id"])))
                            st.success("تم حفظ تعديلات نموذج الاختبار بنجاح.")
                            st.rerun()
        else:
            with db() as c:
                tpls_del = c.execute("SELECT id, name, exam_type FROM exam_templates ORDER BY name ASC, id ASC").fetchall()
            if tpls_del:
                tpl_map = {f"نموذج رقم {t['id']} - {t['name']} [{t['exam_type']}] | {template_scope_text(dict(t))}": t['id'] for t in tpls_del}
                with st.form("delete_template_form", clear_on_submit=True):
                    selected_tpl_label = st.selectbox("اختر النموذج للحذف:", list(tpl_map.keys()))
                    if st.form_submit_button("🗑 حذف نموذج الاختبار وإعادة الترتيب", use_container_width=True):
                        with db() as c:
                            c.execute("PRAGMA foreign_keys=OFF;")
                            c.execute("DELETE FROM exam_templates WHERE id=?", (tpl_map[selected_tpl_label],))
                            c.execute("PRAGMA foreign_keys=ON;")
                        reindex_templates()
                        st.success("✅ تم الحذف وإعادة الترتيب التلقائي بنجاح!")
                        st.rerun()

    elif selected_menu in ("✍ تسجيل نتيجة يدوي", "✍ التسجيل اليدوي للاختبارات و التقييم الواقعي"):
        st.subheader("✍ التسجيل اليدوي للاختبارات و التقييم الواقعي")
        manual_exam_tab, facility_assessment_tab = st.tabs(["📝 التسجيل اليدوي للاختبارات", "🏥 التقييم الواقعي للمنشآت"])

        with manual_exam_tab:
            st.markdown("#### 🏢 تحديد الهيكل الإداري والوظيفي للاختبار")
            manual_scope = hierarchy_scope_widget("الهيكل الإداري للمتدرب:", "manual_exam_hierarchy_v1")
            manual_profession_list = get_print_settings().get("professions_list", ["أخصائي الأمراض المتوطنة", "طبيب بيطري"])
            manual_profession = st.selectbox("الوظيفة / التخصص:", manual_profession_list, key="manual_exam_profession_v1")
            hier_data = get_hierarchical_data(include_hidden=False)
            def _scope_matches_row(row, scope):
                return hierarchy_row_matches_scope(row, scope, allow_shared_section_rows=True)
            matching_hier = [h for h in hier_data if _scope_matches_row(h, manual_scope)]
            facility_choices = hierarchy_ordered_unique(h.get("facility_name") for h in matching_hier)
            if facility_choices:
                selected_manual_facility = st.selectbox("المنشأة:", facility_choices, key="manual_exam_facility_choice_v2")
            else:
                selected_manual_facility = str(manual_scope.get("scope_facility") or "")
            user_scope_pred, user_scope_args = hierarchy_filter_for_trainees(current_user_trainee_scope(), "t")
            with db() as c:
                facility_trainees = [dict(r) for r in c.execute(f"SELECT t.id,t.name,t.facility,t.profession,t.status FROM trainees t WHERE COALESCE(t.hidden,0)=0 AND {user_scope_pred} ORDER BY t.name COLLATE NOCASE", tuple(user_scope_args)).fetchall()]
            eligible_manual_trainees = [t for t in facility_trainees if (not selected_manual_facility or str(t.get("facility") or "").strip() == selected_manual_facility) and (not manual_profession or str(t.get("profession") or "").strip() == manual_profession)]
            manual_trainee_labels = {f"{t['name']} — {t['profession']} (#{t['id']})": t["id"] for t in eligible_manual_trainees}
            manual_selected_label = st.selectbox("اسم المتدرب (إجباري من قاعدة البيانات):", ["-- اختر متدربًا --"] + list(manual_trainee_labels.keys()), key="manual_exam_trainee_required_v3", help="يتم اختيار الاسم من المتدربين المسجلين المطابقين للهيكل الإداري والمنشأة والمهنة فقط.")
            default_fac_str = selected_manual_facility or str(manual_scope.get("scope_facility") or (hier_data[0]["facility_name"] if hier_data else ""))
            print_st_m = get_print_settings()
            prof_manual_list = print_st_m.get("professions_list", ["أخصائي الأمراض المتوطنة", "طبيب بيطري"])
            with db() as c:
                all_tpls_records = c.execute("SELECT id, name, exam_type, profession FROM exam_templates ORDER BY name ASC").fetchall()
            scope_tpls = []
            for row in all_tpls_records:
                rowd = dict(row)
                if rowd.get("profession") and rowd.get("profession") != manual_profession:
                    continue
                scope_tpls.append(rowd)
            manual_tpl_choices = {f"{row['name']} ({row['exam_type']})": row["id"] for row in scope_tpls} if scope_tpls else {}
            manual_tpl_keys = list(manual_tpl_choices.keys()) if manual_tpl_choices else ["لا توجد نماذج اختبارات متوافقة مع الوظيفة"]
            with st.form("manual_score_form_enhanced", clear_on_submit=True):
                m_trainee_name = st.text_input("اسم المتدرب:", value=(manual_selected_label.split(" — ")[0] if manual_selected_label != "-- اختر متدربًا --" else ""), disabled=True)
                m_facility_name = st.text_input("وحدة الأمراض المتوطنة / جهة العمل:", value=default_fac_str, disabled=True)
                m_profession = st.text_input("الوظيفة / التخصص:", value=manual_profession, disabled=True)
                selected_manual_tpl_name = st.selectbox("اختر قالب/نموذج الاختبار:", manual_tpl_keys)
                c1, c2 = st.columns(2)
                with c1:
                    manual_score = st.number_input("الدرجة الحاصل عليها:", min_value=0, max_value=9999, value=45)
                with c2:
                    manual_max = st.number_input("الدرجة الكلية:", min_value=1, max_value=9999, value=50)
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
                    if manual_selected_label == "-- اختر متدربًا --" or manual_selected_label not in manual_trainee_labels:
                        st.warning("⚠ يجب اختيار متدرب موجود من القائمة المرتبطة بالهيكل الإداري.")
                    elif not manual_tpl_choices:
                        st.warning("⚠ يرجى إنشاء نموذج اختبار متوافق مع الوظيفة أولاً.")
                    else:
                        with db() as c:
                            tpl_id_val = manual_tpl_choices.get(selected_manual_tpl_name)
                            selected_ids = [manual_trainee_labels[manual_selected_label]]

                            selected_row = c.execute("SELECT id,name,facility,profession,hidden FROM trainees WHERE id=?", (selected_ids[0],)).fetchone()
                            if not selected_row or selected_row["hidden"] or selected_row["facility"] != (selected_manual_facility or str(manual_scope.get("scope_facility") or "")) or selected_row["profession"] != manual_profession:
                                st.error("❌ المتدرب المختار لا يطابق الهيكل الإداري أو المنشأة أو المهنة المحددة.")
                                st.stop()
                            passed_flag = 1 if manual_passed == "اجتزت بنجاح" else 0
                            cert_codes = []
                            for selected_tid in selected_ids:
                                c.execute("UPDATE trainees SET status='completed', assigned_template_id=?, updated_at=? WHERE id=?", (tpl_id_val, now(), selected_tid))
                                cur_sess = c.execute("INSERT INTO exam_sessions(trainee_id,template_id,started_at,expires_at,submitted_at,status,score,max_score,percent,passed) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                                     (selected_tid, tpl_id_val, now(), now(), now(), "submitted", manual_score, manual_max, calc_pct, passed_flag))
                                new_sid = cur_sess.lastrowid
                                cert_code = generate_individual_certificate_code(new_sid, selected_tid, tpl_id_val)
                                cert_codes.append(cert_code)
                                c.execute("UPDATE exam_sessions SET certificate_id=? WHERE id=?", (cert_code, new_sid))
                                all_bank_qs = c.execute("SELECT id, answer FROM questions WHERE active=1").fetchall()
                                for pos, q_item in enumerate(all_bank_qs):
                                    q_id, correct_ans = q_item["id"], q_item["answer"]
                                    is_wrong = q_id in selected_wrong_q_ids
                                    selected_option = (correct_ans + 1) % 4 if is_wrong else correct_ans
                                    c.execute("INSERT INTO exam_questions(session_id, question_id, position, option_order_json, selected_option, is_correct) VALUES(?,?,?,?,?,?)",
                                              (new_sid, q_id, pos, json.dumps([0,1,2,3]), selected_option, 0 if is_wrong else 1))
                        st.success(f"✅ تم تسجيل نتيجة {len(selected_ids)} متدرب/متدربين بنجاح. أرقام الشهادات: **{', '.join(cert_codes)}**")
                        manual_print_rows = "".join(
                            f"<tr><td>{esc(tid)}</td><td>{esc(next((t['name'] for t in facility_trainees if t['id']==tid), m_trainee_name))}</td><td>{esc(m_profession)}</td><td>{esc(m_facility_name)}</td><td>{manual_score}/{manual_max}</td><td>{calc_pct:.1f}%</td><td>{esc(manual_passed)}</td></tr>"
                            for tid in selected_ids
                        )
                        manual_print_html = f"<table class='table' style='width:100%;border-collapse:collapse' border='1'><thead><tr><th>رقم</th><th>الاسم</th><th>الوظيفة</th><th>المنشأة</th><th>الدرجة</th><th>النسبة</th><th>الحالة</th></tr></thead><tbody>{manual_print_rows}</tbody></table>"
                        render_print_button_only(generate_general_report_html("التسجيل اليدوي لنتائج الاختبارات", manual_print_html), "🖨 طباعة نتائج التسجيل اليدوي")

        with facility_assessment_tab:
            st.markdown("#### 🏥 نموذج التقييم الواقعي للمنشآت")
            st.caption("اختر الهيكل الإداري والوظيفة أولاً، ثم قيّم عناصر الزيارة الميدانية وفق النموذج.")
            assessment_scope = hierarchy_scope_widget("الهيكل الإداري للمنشأة:", "real_assessment_hierarchy_v1")
            assessment_professions = get_print_settings().get("professions_list", ["أخصائي الأمراض المتوطنة", "طبيب بيطري"])
            assessment_profession = st.selectbox("الوظيفة / التخصص المسؤول عن التقييم:", assessment_professions, key="real_assessment_profession_v1")
            assessment_hier = get_hierarchical_data(include_hidden=False)
            assessment_matching_hier = [h for h in assessment_hier if _scope_matches_row(h, assessment_scope)]
            assessment_facility_choices = hierarchy_ordered_unique(h.get("facility_name") for h in assessment_matching_hier)
            assessment_facility_default = str(assessment_scope.get("scope_facility") or "")
            if assessment_facility_choices:
                assessment_facility_default = st.selectbox("المنشأة محل التقييم:", assessment_facility_choices, key="real_assessment_facility_choice_v2")
            elif not assessment_facility_default and assessment_hier:
                assessment_facility_default = assessment_hier[0].get("facility_name", "")
            with db() as c:
                assessment_scope_pred, assessment_scope_args = hierarchy_filter_for_trainees(current_user_trainee_scope(), "t")
                assessment_trainees = [dict(r) for r in c.execute(f"SELECT t.id,t.name,t.profession,t.facility FROM trainees t WHERE COALESCE(t.hidden,0)=0 AND {assessment_scope_pred} ORDER BY t.name COLLATE NOCASE", tuple(assessment_scope_args)).fetchall()]
            facility_assessment_trainees = [t for t in assessment_trainees if (not assessment_facility_default or str(t.get("facility") or "").strip() == assessment_facility_default) and (not assessment_profession or str(t.get("profession") or "").strip() == assessment_profession)]
            st.multiselect("المتدربون المسجلون بهذه المنشأة (اختياري):", [f"{t['name']} — {t['profession']}" for t in facility_assessment_trainees], key="real_assessment_trainees_v2", help="تظهر الأسماء المسجلة في المنشأة المختارة حسب الوظيفة.")
            assessment_items = [
                "توافر أدوات ومستلزمات الفحص",
                "الالتزام بإجراءات جمع العينات",
                "الالتزام بإجراءات الفحص المعملي",
                "تطبيق قواعد مكافحة العدوى",
                "تسجيل النتائج وحفظ السجلات",
                "تطبيق إجراءات ضبط الجودة",
                "توافر العاملين المدربين",
                "تنفيذ التوصيات السابقة",
            ]
            with st.form("facility_real_assessment_form_v1", clear_on_submit=True):
                visit_date = st.date_input("تاريخ الزيارة:", value=date.today(), key="real_assessment_date_v1")
                assessment_facility = st.text_input("اسم المنشأة:", value=assessment_facility_default, key="real_assessment_facility_v1")
                assessment_responsible = st.text_input("اسم مسؤول المنشأة / التقييم:", key="real_assessment_responsible_v1")
                st.markdown("##### تقييم عناصر الزيارة")
                item_results = {}
                for i, item in enumerate(assessment_items):
                    left, right = st.columns([3, 2])
                    with left:
                        st.write(item)
                    with right:
                        item_results[item] = st.selectbox("الحالة", ["مطابق", "غير مطابق", "يحتاج إلى تحسين", "لا ينطبق"], key=f"real_assess_item_{i}", label_visibility="collapsed")
                assessment_notes = st.text_area("الملاحظات والتوصيات:", key="real_assessment_notes_v1")
                if st.form_submit_button("💾 حفظ التقييم الواقعي للمنشأة", use_container_width=True):
                    if not assessment_facility.strip():
                        st.error("يرجى تحديد اسم المنشأة من الهيكل الإداري أو إدخاله.")
                    else:
                        with db() as c:
                            c.execute("INSERT INTO facility_real_assessments(visit_date,governorate,authority,administration,facility,profession,responsible_person,items_json,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                      (visit_date.isoformat(), assessment_scope.get("scope_governorate", ""), assessment_scope.get("scope_authority", ""), assessment_scope.get("scope_administration", ""), assessment_facility, assessment_profession, assessment_responsible, json.dumps(item_results, ensure_ascii=False), assessment_notes, now()))
                        st.success("تم حفظ التقييم الواقعي للمنشأة بنجاح.")
            with db() as c:
                saved_assessments = c.execute("SELECT * FROM facility_real_assessments ORDER BY id DESC LIMIT 100").fetchall()
            if saved_assessments:
                st.markdown("#### 📋 التقييمات الواقعية المسجلة")
                saved_assessment_view = [{"التاريخ": r["visit_date"], "المديرية / الجهة": r["authority"], "الإدارة": r["administration"], "المنشأة": r["facility"], "الوظيفة": r["profession"], "مسؤول التقييم": r["responsible_person"]} for r in saved_assessments]
                st.dataframe(saved_assessment_view, use_container_width=True, hide_index=True)
                assess_table_html = pd.DataFrame(saved_assessment_view).to_html(index=False, border=1, classes="table")
                render_print_button_only(generate_general_report_html("التقييمات الواقعية المسجلة", assess_table_html), "🖨 طباعة التقييمات الواقعية")


    elif selected_menu == "📊 التقارير":
        st.subheader("📊 تقارير أداء وحدات الأمراض المتوطنة وتحليل النتائج (تستبعد المخفيين تلقائياً)")

        st.markdown("#### 🏥 تحديد نطاق التقارير حسب الهيكل الإداري")
        rep_scope = hierarchy_scope_widget("نطاق التقارير:", "reports_scope_v12")
        rep_scope_sql, rep_scope_args = hierarchy_scope_sql("h", rep_scope)
        st.caption("جميع التقارير والرسوم البيانية والنتائج أسفل الصفحة ستلتزم بهذا النطاق الإداري.")

        rep_tab1, rep_tab2, rep_tab3, rep_tab4, rep_tab5, rep_tab6 = st.tabs([
            "👤 تقرير فردي (لمتدرب مع فلترة ومقارنة فترات)",
            "🏢 تقرير جماعي (لوحدة متوطنة مع فلترة ومقارنة فترات)",
            "📋 تقرير النتائج الشامل",
            "📈 تقرير أداء الجهات",
            "🏆 عرض النتائج والفلترة والأعلى تقييماً",
            "🏥 تقارير التقييم الواقعي ومقارنة الفترات"
        ])


        def _report_date_ok(d1, d2):
            if d1 > d2:
                st.warning("⚠️ تاريخ البداية يجب أن يكون قبل أو مساوياً لتاريخ النهاية.")
                return False
            return True

        def _pct(v):
            try:
                return float(v or 0.0)
            except Exception:
                return 0.0

        def _status(v):
            return "اجتزت بنجاح" if v == 1 else ("لم تجتز" if v is not None else "لا توجد نتيجة")

        def _excel_download(df, label, filename, key):
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Report")
            st.download_button(
                label, data=out.getvalue(), file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=key
            )

        with rep_tab1:
            if has_subtab_permission('📊 التقارير', '👤 تقرير فردي (لمتدرب مع فلترة ومقارنة فترات)'):
                st.markdown("#### 👤 التقرير الفردي للمتدرب (مع تحديد المدى الزمني ومقارنة فترتين)")
                with db() as c:
                    tr_list_rep = c.execute(
                        f"SELECT DISTINCT t.id, t.name, t.facility, t.profession FROM trainees t "
                        f"LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name) "
                        f"WHERE COALESCE(t.hidden,0)=0 AND {rep_scope_sql} ORDER BY t.id DESC",
                        tuple(rep_scope_args)
                    ).fetchall()

                if not tr_list_rep:
                    st.info("لا توجد بيانات متدربين ظاهرة متاحة.")
                else:
                    tr_choices_rep = {
                        f"متدرب: {t['name'] or ''} - الوظيفة: {t['profession'] or ''} - "
                        f"الجهة: {t['facility'] or ''} (ID: {t['id']})": t['id']
                        for t in tr_list_rep
                    }
                    sel_tr_rep_label = st.selectbox(
                        "اختر المتدرب لاستعراض تقريره الفردي:",
                        list(tr_choices_rep.keys()), key="sel_ind_tr_rep_v7"
                    )
                    chosen_tr_id = tr_choices_rep[sel_tr_rep_label]
                    enforce_trainee_scope_or_raise(chosen_tr_id)
                    today = now_cairo().date()

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("##### 📅 الفترة الأولى (التقرير الأساسي)")
                        d_start_1 = st.date_input("من تاريخ الفترة الأولى", today-timedelta(days=30), key="rep_ds1_v7")
                        d_end_1 = st.date_input("إلى تاريخ الفترة الأولى", today, key="rep_de1_v7")
                    with c2:
                        st.markdown("##### 📅 الفترة الثانية (للمقارنة)")
                        d_start_2 = st.date_input("من تاريخ الفترة الثانية", today-timedelta(days=60), key="rep_ds2_v7")
                        d_end_2 = st.date_input("إلى تاريخ الفترة الثانية", today-timedelta(days=31), key="rep_de2_v7")

                    if _report_date_ok(d_start_1, d_end_1) and _report_date_ok(d_start_2, d_end_2):
                        with db() as c:
                            ind_tr_data = c.execute(
                                "SELECT id,name,facility,profession FROM trainees WHERE id=? AND COALESCE(hidden,0)=0",
                                (chosen_tr_id,)
                            ).fetchone()
                            q = """
                                SELECT s.id,s.score,s.max_score,s.percent,s.passed,s.submitted_at,
                                       e.name AS tpl_name,e.exam_type
                                FROM exam_sessions s
                                LEFT JOIN exam_templates e ON e.id=s.template_id
                                WHERE s.trainee_id=? AND s.status='submitted'
                                  AND date(s.submitted_at)>=date(?) AND date(s.submitted_at)<=date(?)
                                ORDER BY s.id DESC LIMIT 1
                            """
                            s_q1 = c.execute(q, (chosen_tr_id,d_start_1.isoformat(),d_end_1.isoformat())).fetchone()
                            s_q2 = c.execute(q, (chosen_tr_id,d_start_2.isoformat(),d_end_2.isoformat())).fetchone()

                        if ind_tr_data:
                            def _score_text(row):
                                if not row or row["score"] is None:
                                    return "لا توجد نتيجة في هذه الفترة"
                                return (
                                    f"{row['score'] or 0}/{row['max_score'] or 0} "
                                    f"({_pct(row['percent']):.1f}%) — "
                                    f"{row['tpl_name'] or 'اختبار معتمد'} "
                                    f"({row['exam_type'] or 'قبل التدريب'})"
                                )

                            p1_score = _score_text(s_q1)
                            p2_score = _score_text(s_q2)
                            p1_status = _status(s_q1["passed"] if s_q1 else None)
                            p2_status = _status(s_q2["passed"] if s_q2 else None)
                            p1_pct = _pct(s_q1["percent"] if s_q1 else 0)
                            p2_pct = _pct(s_q2["percent"] if s_q2 else 0)
                            individual_delta = p2_pct - p1_pct
                            individual_delta_text = f"{individual_delta:+.1f} نقطة مئوية (الفترة الثانية − الأولى)"

                            individual_report_html = f"""
                            <div style="font-family:'Cairo',sans-serif;direction:rtl;padding:10px;">
                                <h3 style="color:#047857;text-align:center;">تقرير أداء ونتيجة متدرب (مع مقارنة الفترات)</h3>
                                <hr style="border:1px solid #059669;">
                                <p><b>اسم المتدرب:</b> {esc(ind_tr_data['name'] or '')} |
                                   <b>الوظيفة:</b> {esc(ind_tr_data['profession'] or '')} |
                                   <b>جهة العمل:</b> {esc(ind_tr_data['facility'] or '')}</p>
                                <table style="width:100%;border-collapse:collapse;margin-top:15px;font-size:10pt;">
                                    <tr><th style="border:1px solid #cbd5e1;padding:8px;background:#059669;color:white;">فترة المقارنة</th>
                                        <th style="border:1px solid #cbd5e1;padding:8px;background:#059669;color:white;">النتيجة والنسبة والتصنيف</th>
                                        <th style="border:1px solid #cbd5e1;padding:8px;background:#059669;color:white;">حالة الاجتياز</th></tr>
                                    <tr><td style="border:1px solid #cbd5e1;padding:8px;font-weight:bold;">الفترة الأولى ({d_start_1} إلى {d_end_1})</td>
                                        <td style="border:1px solid #cbd5e1;padding:8px;">{p1_score}</td>
                                        <td style="border:1px solid #cbd5e1;padding:8px;">{p1_status}</td></tr>
                                    <tr><td style="border:1px solid #cbd5e1;padding:8px;font-weight:bold;">الفترة الثانية ({d_start_2} إلى {d_end_2})</td>
                                        <td style="border:1px solid #cbd5e1;padding:8px;">{p2_score}</td>
                                        <td style="border:1px solid #cbd5e1;padding:8px;">{p2_status}</td></tr>
                                    <tr><td colspan="3" style="border:1px solid #059669;padding:8px;background:#ecfdf5;font-weight:900;color:#065f46;text-align:center;">الفارق بين الفترتين: {individual_delta_text}</td></tr>
                                </table>
                            </div>"""
                            st.markdown(individual_report_html, unsafe_allow_html=True)
                            st.markdown("##### 📊 الرسم البياني لمقارنة الفترتين")
                            chart_ind = pd.DataFrame({"الفترة": ["الفترة الأولى", "الفترة الثانية"], "النسبة %": [_pct(s_q1["percent"] if s_q1 else 0), _pct(s_q2["percent"] if s_q2 else 0)]}).set_index("الفترة")
                            st.bar_chart(chart_ind, use_container_width=True)
                            chart_ind_html = report_chart_html("الرسم البياني — مقارنة الفترتين", ["الفترة الأولى", "الفترة الثانية"], [p1_pct, p2_pct], "%")
                            render_print_button_only(generate_general_report_html("الرسم البياني لمقارنة أداء المتدرب", chart_ind_html), f"طباعة رسم مقارنة المتدرب {chosen_tr_id}")

                            df_ind = pd.DataFrame([{
                                "اسم المتدرب": ind_tr_data["name"] or "",
                                "الوظيفة": ind_tr_data["profession"] or "",
                                "جهة العمل": ind_tr_data["facility"] or "",
                                "الفترة الأولى": f"{d_start_1} إلى {d_end_1}",
                                "نتيجة الفترة الأولى": p1_score,
                                "حالة الفترة الأولى": p1_status,
                                "الفترة الثانية": f"{d_start_2} إلى {d_end_2}",
                                "نتيجة الفترة الثانية": p2_score,
                                "حالة الفترة الثانية": p2_status,
                                "الفارق بين الفترتين (الثانية - الأولى)": f"{individual_delta:+.1f} نقطة مئوية"
                            }])
                            _excel_download(df_ind,"📥 تحميل التقرير الفردي (.xlsx)",f"individual_report_{chosen_tr_id}.xlsx","dl_ind_report_v7")
                            render_print_button_only(
                                generate_general_report_html(f"مقارنة أداء المتدرب: {ind_tr_data['name'] or ''}", individual_report_html),
                                f"مقارنة فترات المتدرب {chosen_tr_id}"
                            )

        with rep_tab2:
            if has_subtab_permission('📊 التقارير', '🏢 تقرير جماعي (لوحدة متوطنة مع فلترة ومقارنة فترات)'):
                st.markdown("#### 🏢 التقرير الجماعي لوحدة الأمراض المتوطنة (مقارنة فترتين)")
                with db() as c:
                    facs_list_rep = [
                        r[0] for r in c.execute(
                            f"SELECT DISTINCT t.facility FROM trainees t "
                            f"LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name) "
                            f"WHERE t.facility IS NOT NULL AND TRIM(t.facility)<>'' AND COALESCE(t.hidden,0)=0 AND {rep_scope_sql} ORDER BY t.facility",
                            tuple(rep_scope_args)
                        ).fetchall()
                    ]

                    _report_hier_rows = get_hierarchical_data(include_hidden=False)
                    _report_facility_order = hierarchy_ordered_unique(r.get("facility_name") for r in _report_hier_rows)
                    _report_facility_set = set(facs_list_rep)
                    facs_list_rep = [f for f in _report_facility_order if f in _report_facility_set] + [
                        f for f in hierarchy_ordered_unique(facs_list_rep) if f not in _report_facility_order
                    ]
                if not facs_list_rep:
                    st.info("لا توجد وحدات أو جهات ظاهرة مسجلة.")
                else:
                    sel_fac_rep = st.selectbox("اختر الوحدة الصحية / جهة العمل:", facs_list_rep, key="sel_group_fac_rep_v7")
                    today = now_cairo().date()
                    g1,g2=st.columns(2)
                    with g1:
                        gf_start_1=st.date_input("من تاريخ الفترة الأولى",today-timedelta(days=30),key="gfs1_v7")
                        gf_end_1=st.date_input("إلى تاريخ الفترة الأولى",today,key="gfe1_v7")
                    with g2:
                        gf_start_2=st.date_input("من تاريخ الفترة الثانية",today-timedelta(days=60),key="gfs2_v7")
                        gf_end_2=st.date_input("إلى تاريخ الفترة الثانية",today-timedelta(days=31),key="gfe2_v7")

                    if _report_date_ok(gf_start_1,gf_end_1) and _report_date_ok(gf_start_2,gf_end_2):
                        with db() as c:
                            sql="""
                            SELECT COUNT(DISTINCT t.id) AS total_tr,
                                   COUNT(s.id) AS exams,
                                   COALESCE(AVG(s.percent),0) AS avg_pct,
                                   COALESCE(SUM(CASE WHEN s.passed=1 THEN 1 ELSE 0 END),0) AS passed_cnt
                            FROM trainees t JOIN exam_sessions s ON s.trainee_id=t.id
                            LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name)
                            WHERE s.status='submitted' AND COALESCE(t.hidden,0)=0 AND t.facility=?
                              AND {rep_scope_sql}
                              AND date(s.submitted_at)>=date(?) AND date(s.submitted_at)<=date(?)
                            """
                            p1=c.execute(sql.format(rep_scope_sql=rep_scope_sql), tuple([sel_fac_rep] + rep_scope_args + [gf_start_1.isoformat(),gf_end_1.isoformat()])).fetchone()
                            p2=c.execute(sql.format(rep_scope_sql=rep_scope_sql), tuple([sel_fac_rep] + rep_scope_args + [gf_start_2.isoformat(),gf_end_2.isoformat()])).fetchone()

                        def _stat(row):
                            return (int(row["total_tr"] or 0),int(row["exams"] or 0),int(row["passed_cnt"] or 0),_pct(row["avg_pct"]))
                        a=_stat(p1); b=_stat(p2)
                        group_delta_pct = b[3] - a[3]
                        group_delta_tr = b[0] - a[0]
                        group_delta_exams = b[1] - a[1]
                        group_delta_passed = b[2] - a[2]
                        group_compare_html=f"""
                        <div style="font-family:'Cairo',sans-serif;direction:rtl;padding:10px;">
                        <h3 style="color:#047857;text-align:center;">تقرير مقارنة أداء وحدة الأمراض المتوطنة: {esc(sel_fac_rep)}</h3>
                        <table style="width:100%;border-collapse:collapse;font-size:10pt;">
                        <tr><th>الفترة</th><th>إجمالي المتدربين</th><th>الاختبارات</th><th>المجتازون</th><th>متوسط النسبة %</th></tr>
                        <tr><td>{gf_start_1} إلى {gf_end_1}</td><td>{a[0]}</td><td>{a[1]}</td><td>{a[2]}</td><td>{a[3]:.1f}%</td></tr>
                        <tr><td>{gf_start_2} إلى {gf_end_2}</td><td>{b[0]}</td><td>{b[1]}</td><td>{b[2]}</td><td>{b[3]:.1f}%</td></tr>
                        <tr><td colspan="5" style="border:1px solid #059669;padding:7px;background:#ecfdf5;font-weight:900;color:#065f46;text-align:center;">الفارق (الثانية − الأولى): المتدربون {group_delta_tr:+d} | الاختبارات {group_delta_exams:+d} | المجتازون {group_delta_passed:+d} | متوسط النسبة {group_delta_pct:+.1f} نقطة مئوية</td></tr>
                        </table></div>"""
                        st.markdown(group_compare_html,unsafe_allow_html=True)
                        st.markdown("##### 📊 الرسم البياني لمقارنة أداء الوحدة")
                        chart_group = pd.DataFrame({"الفترة": ["الفترة الأولى", "الفترة الثانية"], "متوسط النسبة %": [a[3], b[3]]}).set_index("الفترة")
                        st.bar_chart(chart_group, use_container_width=True)
                        chart_group_html = report_chart_html("الرسم البياني — مقارنة أداء الوحدة", ["الفترة الأولى", "الفترة الثانية"], [a[3], b[3]], "%")
                        render_print_button_only(generate_general_report_html("الرسم البياني لمقارنة أداء الوحدة", chart_group_html), f"طباعة رسم مقارنة الوحدة {sel_fac_rep}")
                        df_group=pd.DataFrame([
                            {"وحدة الأمراض المتوطنة":sel_fac_rep,"الفترة":f"{gf_start_1} إلى {gf_end_1}","إجمالي المتدربين":a[0],"الاختبارات":a[1],"المجتازون":a[2],"متوسط النسبة %":f"{a[3]:.1f}%"},
                            {"وحدة الأمراض المتوطنة":sel_fac_rep,"الفترة":f"{gf_start_2} إلى {gf_end_2}","إجمالي المتدربين":b[0],"الاختبارات":b[1],"المجتازون":b[2],"متوسط النسبة %":f"{b[3]:.1f}%","الفارق (الثانية - الأولى)":f"{group_delta_pct:+.1f} نقطة مئوية"}
                        ])
                        _excel_download(df_group,"📥 تحميل التقرير الجماعي للوحدة (.xlsx)",f"facility_report_{sel_fac_rep}.xlsx","dl_group_report_v7")
                        render_print_button_only(generate_general_report_html(f"مقارنة أداء وحدة الأمراض المتوطنة: {sel_fac_rep}",group_compare_html),f"مقارنة فترات وحدة {sel_fac_rep}")

        with rep_tab3:
            if has_subtab_permission('📊 التقارير', '📋 تقرير النتائج الشامل'):
                st.markdown("#### 📋 التقرير الشامل لجميع نتائج المتدربين الظاهرين")
                with db() as c:
                    rows=c.execute("""
                        SELECT t.id,t.name,t.profession,t.facility,
                               s.score,s.max_score,s.percent,s.passed,s.submitted_at,
                               e.exam_type,e.name AS template_name
                        FROM trainees t
                        LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name)
                        LEFT JOIN exam_sessions s ON s.trainee_id=t.id AND s.status='submitted'
                        LEFT JOIN exam_templates e ON e.id=s.template_id
                        WHERE COALESCE(t.hidden,0)=0 AND {rep_scope_sql}
                        ORDER BY t.id DESC,s.id DESC
                    """.format(rep_scope_sql=rep_scope_sql), tuple(rep_scope_args)).fetchall()

                    cols=[r[1] for r in c.execute("PRAGMA table_info(exam_sessions)").fetchall()]
                    has_cert="certificate_id" in cols
                    if has_cert:
                        rows=c.execute("""
                            SELECT t.id,t.name,t.profession,t.facility,s.score,s.max_score,s.percent,s.passed,
                                   s.certificate_id,s.submitted_at,e.exam_type,e.name AS template_name
                            FROM trainees t
                            LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name)
                            LEFT JOIN exam_sessions s ON s.trainee_id=t.id AND s.status='submitted'
                            LEFT JOIN exam_templates e ON e.id=s.template_id
                            WHERE COALESCE(t.hidden,0)=0 AND {rep_scope_sql} ORDER BY t.id DESC,s.id DESC
                        """.format(rep_scope_sql=rep_scope_sql), tuple(rep_scope_args)).fetchall()

                data=[]
                for r in rows:
                    data.append({
                        "مسلسل":r["id"],"اسم المتدرب":r["name"] or "","الوظيفة":r["profession"] or "",
                        "وحدة الأمراض المتوطنة":r["facility"] or "","تصنيف الاختبار":r["exam_type"] or "-",
                        "الدرجة":f"{r['score'] or 0}/{r['max_score'] or 0}" if r["score"] is not None else "-",
                        "النسبة المئوية %":f"{_pct(r['percent']):.1f}%" if r["percent"] is not None else "-",
                        "الحالة":_status(r["passed"]),"رقم الشهادة":(r["certificate_id"] or "-") if has_cert else "-",
                        "التاريخ":r["submitted_at"] or "-"
                    })
                df_rep=pd.DataFrame(data)
                if df_rep.empty: st.info("لا توجد بيانات متدربين ظاهرة لعرضها في التقرير.")
                else:
                    st.dataframe(df_rep,use_container_width=True,hide_index=True)
                    st.markdown("##### 📊 الرسم البياني لحالة النتائج")
                    pass_count = int(sum(1 for r in data if r["الحالة"] == "اجتزت بنجاح"))
                    fail_count = int(sum(1 for r in data if r["الحالة"] == "لم تجتز"))
                    no_result_count = int(sum(1 for r in data if r["الحالة"] == "لا توجد نتيجة"))
                    chart_all = pd.DataFrame({"الحالة": ["اجتزت بنجاح", "لم تجتز", "لا توجد نتيجة"], "العدد": [pass_count, fail_count, no_result_count]}).set_index("الحالة")
                    st.bar_chart(chart_all, use_container_width=True)
                    chart_all_html = report_chart_html("الرسم البياني — حالة النتائج", ["اجتاز بنجاح", "لم يجتز", "لا توجد نتيجة"], [pass_count, fail_count, no_result_count], "")
                    render_print_button_only(generate_general_report_html("الرسم البياني لحالة النتائج", chart_all_html), "طباعة رسم حالة النتائج")
                    _excel_download(df_rep,"📥 تحميل تقرير النتائج الشامل (.xlsx)","all_trainees_results.xlsx","dl_all_results_v7")
                    table_html=df_rep.to_html(index=False,border=0,classes="table")
                    render_print_button_only(generate_general_report_html("تقرير نتائج المتدربين الشامل",f"<div>{table_html}</div>"),"تقرير النتائج الشامل")

        with rep_tab4:
            if has_subtab_permission('📊 التقارير', '📈 تقرير أداء الجهات'):
                st.markdown("#### 📈 تحليل أداء جميع الجهات والوحدات")
                with db() as c:
                    rows=c.execute("""
                        SELECT t.facility AS facility,
                               COUNT(DISTINCT t.id) AS trainees_count,
                               COUNT(s.id) AS exams_count,
                               COALESCE(SUM(CASE WHEN s.passed=1 THEN 1 ELSE 0 END),0) AS passed_count,
                               COALESCE(AVG(s.percent),0) AS avg_pct
                        FROM trainees t
                        LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name)
                        LEFT JOIN exam_sessions s ON s.trainee_id=t.id AND s.status='submitted'
                        WHERE COALESCE(t.hidden,0)=0 AND t.facility IS NOT NULL AND TRIM(t.facility)<>'' AND {rep_scope_sql}
                        GROUP BY t.facility ORDER BY avg_pct DESC,t.facility
                    """.format(rep_scope_sql=rep_scope_sql), tuple(rep_scope_args)).fetchall()
                df_fac=pd.DataFrame([{
                    "وحدة الأمراض المتوطنة / الجهة":r["facility"] or "",
                    "إجمالي المتدربين":int(r["trainees_count"] or 0),
                    "إجمالي الاختبارات":int(r["exams_count"] or 0),
                    "المجتازون":int(r["passed_count"] or 0),
                    "متوسط النسبة %":round(_pct(r["avg_pct"]),1)
                } for r in rows])
                if df_fac.empty: st.info("لا توجد بيانات جهات أو وحدات لتحليلها.")
                else:
                    st.dataframe(df_fac,use_container_width=True,hide_index=True)
                    st.markdown("##### 📊 الرسم البياني لمتوسط أداء الجهات")
                    chart_fac = df_fac[["وحدة الأمراض المتوطنة / الجهة", "متوسط النسبة %"]].set_index("وحدة الأمراض المتوطنة / الجهة")
                    st.bar_chart(chart_fac, use_container_width=True)
                    chart_fac_html = report_chart_html("الرسم البياني — متوسط أداء الجهات", df_fac["وحدة الأمراض المتوطنة / الجهة"].tolist(), df_fac["متوسط النسبة %"].tolist(), "%")
                    render_print_button_only(generate_general_report_html("الرسم البياني لمتوسط أداء الجهات", chart_fac_html), "طباعة رسم أداء الجهات")
                    _excel_download(df_fac,"📥 تحميل تقرير أداء الجهات ووحدات المتوطنة (.xlsx)","facilities_performance_report.xlsx","dl_fac_report_v7")
                    table_fac_html=df_fac.to_html(index=False,border=0,classes="table")
                    render_print_button_only(generate_general_report_html("تقرير أداء وحدات الأمراض المتوطنة والجهات",f"<div>{table_fac_html}</div>"),"تقرير أداء الجهات")

        with rep_tab5:
            if has_subtab_permission('📊 التقارير', '🏆 عرض النتائج والفلترة والأعلى تقييماً'):
                st.markdown("#### 🏆 عرض نتائج الاختبارات مع الفلترة والطباعة الفردية والجماعية")
                with db() as c:
                    all_sessions_results=c.execute("""
                        SELECT s.id AS session_id,t.name AS trainee_name,t.facility,t.profession AS trainee_profession,
                               s.score,s.max_score,s.percent,s.passed,e.name AS template_name,e.exam_type,s.submitted_at
                        FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id
                        LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name)
                        LEFT JOIN exam_templates e ON e.id=s.template_id
                        WHERE s.status='submitted' AND COALESCE(t.hidden,0)=0 AND {rep_scope_sql}
                        ORDER BY COALESCE(s.percent,0) DESC,s.id DESC
                    """.format(rep_scope_sql=rep_scope_sql), tuple(rep_scope_args)).fetchall()
                if not all_sessions_results:
                    st.info("لا توجد اختبارات مكتملة أو نتائج مسجلة حتى الآن.")
                else:
                    st.markdown("##### 📊 الرسم البياني العام للنتائج")
                    chart_results_base = pd.DataFrame([{
                        "الفئة": "مجتازون",
                        "العدد": int(sum(1 for r in all_sessions_results if r["passed"] == 1))
                    }, {
                        "الفئة": "غير مجتازين",
                        "العدد": int(sum(1 for r in all_sessions_results if r["passed"] == 0))
                    }]).set_index("الفئة")
                    st.bar_chart(chart_results_base, use_container_width=True)
                    chart_results_html = report_chart_html("الرسم البياني — النتائج العامة", ["مجتازون", "غير مجتازين"], [int(sum(1 for r in all_sessions_results if r["passed"] == 1)), int(sum(1 for r in all_sessions_results if r["passed"] == 0))], "")
                    render_print_button_only(generate_general_report_html("الرسم البياني العام للنتائج", chart_results_html), "طباعة الرسم البياني العام")
                    filter_mode=st.radio("فلترة النتائج:",["عرض الكل (مرتبة تنازلياً)","فقط الأعلى تقييماً (النسبة >= 85%)","فقط المجتازين بنجاح"],horizontal=True,key="rep_filter_mode_v7")
                    filtered_sessions=[]
                    for r in all_sessions_results:
                        pct=_pct(r["percent"]); passed=(r["passed"]==1)
                        if "الأعلى تقييماً" in filter_mode and pct<85: continue
                        if "المجتازين بنجاح" in filter_mode and not passed: continue
                        filtered_sessions.append(r)
                    st.write(f"📊 عدد النتائج المعروضة بعد الفلترة: **{len(filtered_sessions)}** نتيجة.")
                    if filtered_sessions:
                        df_res=pd.DataFrame([{
                            "رقم الاختبار":r["session_id"],"المتدرب":r["trainee_name"] or "","الوظيفة":r["trainee_profession"] or "",
                            "وحدة الأمراض المتوطنة":r["facility"] or "","الاختبار":f"{r['template_name'] or 'اختبار معتمد'} ({r['exam_type'] or 'قبل التدريب'})",
                            "الدرجة":f"{r['score'] or 0}/{r['max_score'] or 0}","النسبة %":f"{_pct(r['percent']):.1f}%",
                            "الحالة":_status(r["passed"]),"التاريخ":r["submitted_at"] or "-"
                        } for r in filtered_sessions])
                        st.dataframe(df_res,use_container_width=True,hide_index=True)
                        _excel_download(df_res,"📥 تحميل النتائج المفلترة (.xlsx)","filtered_results.xlsx","dl_filtered_results_v7")

                        st.markdown("---")
                        print_choice_mode=st.radio("اختر نوع طباعة النتائج:",["طباعة نتيجة ممتحن فردي محدد","طباعة نتائج جميع الممتحنين الظاهرين (القائمة المعروضة)"],horizontal=True,key="rep_print_mode_v7")
                        if "فردي محدد" in print_choice_mode:
                            single_map={f"المتدرب: {r['trainee_name'] or ''} | النسبة: {_pct(r['percent']):.1f}% | الجهة: {r['facility'] or ''} (ID: {r['session_id']})":r["session_id"] for r in filtered_sessions}
                            sel_single=st.selectbox("اختر الممتحن لطباعة تقرير نتيجته المفصلة:",list(single_map.keys()),key="rep_print_session_v7")
                            render_print_button_only(generate_trainee_exam_sheet_html(single_map[sel_single]),f"تقرير نتيجة الممتحن رقم {single_map[sel_single]}")
                        else:
                            combined="".join(generate_trainee_exam_sheet_html(r["session_id"])+"<div style='page-break-after:always;'></div>" for r in filtered_sessions)
                            render_print_button_only(combined,"طباعة نتائج جميع الممتحنين")
                    else:
                        st.warning("⚠️ لا توجد نتائج تطابق شروط الفلترة المحددة.")

        with rep_tab6:
            if has_subtab_permission('📊 التقارير', '🏥 تقارير التقييم الواقعي ومقارنة الفترات'):
                st.markdown("#### 🏥 حساب التقييم الواقعي للفرد أو المجموعة أو المنشأة")
                today_assess = now_cairo().date()
                scope_assess_report = hierarchy_scope_widget("نطاق التقييم الواقعي:", "real_assessment_report_scope_v1")
                assess_professions_report = get_print_settings().get("professions_list", ["أخصائي الأمراض المتوطنة", "طبيب بيطري"])
                profession_filter = st.selectbox("فلترة الوظيفة:", ["كل الوظائف"] + list(assess_professions_report), key="real_assess_report_prof_v1")
                with db() as c:
                    assessment_records = [dict(r) for r in c.execute("SELECT * FROM facility_real_assessments ORDER BY visit_date, id").fetchall()]
                def _assessment_in_scope(r, scope):
                    pairs = [("scope_governorate", "governorate"), ("scope_authority", "authority"), ("scope_administration", "administration"), ("scope_facility", "facility")]
                    return all(not str(scope.get(sk) or "").strip() or str(r.get(rk) or "").strip() == str(scope.get(sk) or "").strip() for sk, rk in pairs)
                filtered_assessments = [r for r in assessment_records if _assessment_in_scope(r, scope_assess_report) and (profession_filter == "كل الوظائف" or r.get("profession") == profession_filter)]
                report_kind = st.radio("نوع التقرير:", ["منشأة", "فرد / مسؤول تقييم", "مجموعة منشآت"], horizontal=True, key="real_assess_report_kind_v1")
                if report_kind == "منشأة":

                    _hierarchy_order_rows = get_hierarchical_data(include_hidden=False)
                    _hierarchy_facility_order = hierarchy_ordered_unique(
                        r.get("facility_name") for r in _hierarchy_order_rows
                    )
                    _assessment_facilities = {str(r.get("facility") or "").strip() for r in filtered_assessments if str(r.get("facility") or "").strip()}
                    facility_options = [f for f in _hierarchy_facility_order if f in _assessment_facilities]
                    facility_options += [f for f in hierarchy_ordered_unique(r.get("facility", "") for r in filtered_assessments) if f not in facility_options]
                    chosen_facility = st.selectbox("اختر المنشأة:", facility_options or ["لا توجد منشآت مسجلة"], key="real_assess_report_fac_v1")
                    filtered_assessments = [r for r in filtered_assessments if r.get("facility") == chosen_facility]
                elif report_kind == "فرد / مسؤول تقييم":
                    person_options = sorted({r.get("responsible_person", "") for r in filtered_assessments if r.get("responsible_person")})
                    chosen_person = st.selectbox("اختر الفرد / مسؤول التقييم:", person_options or ["لا توجد أسماء مسجلة"], key="real_assess_report_person_v1")
                    filtered_assessments = [r for r in filtered_assessments if r.get("responsible_person") == chosen_person]
                else:
                    st.caption("سيتم تجميع التقييمات لكل المنشآت المطابقة للهيكل الإداري المختار.")
                st.markdown("##### 📅 تحديد فترة التقرير")
                ad1, ad2 = st.columns(2)
                with ad1:
                    assess_from = st.date_input("من تاريخ:", today_assess - timedelta(days=30), key="real_assess_report_from_v1")
                with ad2:
                    assess_to = st.date_input("إلى تاريخ:", today_assess, key="real_assess_report_to_v1")
                def _assessment_summary(records):
                    counts = {"مطابق": 0, "غير مطابق": 0, "يحتاج إلى تحسين": 0, "لا ينطبق": 0}
                    total = 0
                    for rec in records:
                        try: items = json.loads(rec.get("items_json") or "{}")
                        except Exception: items = {}
                        for status in items.values():
                            if status in counts: counts[status] += 1
                            if status in ("مطابق", "غير مطابق", "يحتاج إلى تحسين"): total += 1
                    score = (counts["مطابق"] / total * 100) if total else 0.0
                    return counts, total, score
                def _assessment_table_html(records, title):
                    rows_html = []
                    for rec in records:
                        try: items = json.loads(rec.get("items_json") or "{}")
                        except Exception: items = {}
                        cts = {"مطابق": 0, "غير مطابق": 0, "يحتاج إلى تحسين": 0, "لا ينطبق": 0}
                        for value in items.values():
                            if value in cts: cts[value] += 1
                        denom = cts["مطابق"] + cts["غير مطابق"] + cts["يحتاج إلى تحسين"]
                        pct = cts["مطابق"] * 100 / denom if denom else 0
                        rows_html.append(f"<tr><td>{esc(rec.get('visit_date'))}</td><td>{esc(rec.get('authority'))}</td><td>{esc(rec.get('administration'))}</td><td>{esc(rec.get('facility'))}</td><td>{esc(rec.get('profession'))}</td><td>{cts['مطابق']}</td><td>{cts['غير مطابق']}</td><td>{cts['يحتاج إلى تحسين']}</td><td>{pct:.1f}%</td><td>{esc(rec.get('responsible_person'))}</td></tr>")
                    return f"<h3>{esc(title)}</h3><table class='table' style='width:100%;border-collapse:collapse' border='1'><thead><tr><th>التاريخ</th><th>الجهة</th><th>الإدارة</th><th>المنشأة</th><th>الوظيفة</th><th>مطابق</th><th>غير مطابق</th><th>تحسين</th><th>النسبة</th><th>مسؤول التقييم</th></tr></thead><tbody>{''.join(rows_html)}</tbody></table>"
                if assess_from > assess_to:
                    st.warning("تاريخ البداية يجب ألا يتجاوز تاريخ النهاية.")
                else:
                    period_records = [r for r in filtered_assessments if str(assess_from) <= str(r.get("visit_date") or "") <= str(assess_to)]
                    if not period_records:
                        st.info("لا توجد تقييمات واقعية في الفترة المحددة وضمن الفلاتر المختارة.")
                    else:
                        counts, denominator, score = _assessment_summary(period_records)
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("عدد التقييمات", len(period_records))
                        m2.metric("متوسط نسبة المطابقة", f"{score:.1f}%")
                        m3.metric("عناصر مطابقة", counts["مطابق"])
                        m4.metric("عناصر غير مطابقة", counts["غير مطابق"])
                        view_html = _assessment_table_html(period_records, f"تقرير التقييم الواقعي من {assess_from} إلى {assess_to}")
                        view_rows = []
                        for rec in period_records:
                            try: items = json.loads(rec.get("items_json") or "{}")
                            except Exception: items = {}
                            cc = {"مطابق": 0, "غير مطابق": 0, "يحتاج إلى تحسين": 0, "لا ينطبق": 0}
                            for value in items.values():
                                if value in cc: cc[value] += 1
                            den = cc["مطابق"] + cc["غير مطابق"] + cc["يحتاج إلى تحسين"]
                            view_rows.append({"التاريخ":rec.get("visit_date"),"الجهة":rec.get("authority"),"الإدارة":rec.get("administration"),"المنشأة":rec.get("facility"),"الوظيفة":rec.get("profession"),"مطابق":cc["مطابق"],"غير مطابق":cc["غير مطابق"],"يحتاج إلى تحسين":cc["يحتاج إلى تحسين"],"نسبة المطابقة %":round(cc["مطابق"]*100/den,1) if den else 0,"مسؤول التقييم":rec.get("responsible_person")})
                        st.dataframe(pd.DataFrame(view_rows), use_container_width=True, hide_index=True)
                        render_print_button_only(generate_general_report_html("تقرير التقييم الواقعي", view_html), "🖨 طباعة تقرير التقييم الواقعي")
                        _excel_download(pd.DataFrame(view_rows), "📥 تحميل تقرير التقييم الواقعي Excel", "real_assessment_report.xlsx", "dl_real_assess_report_v1")
                st.markdown("---")
                st.markdown("#### 📊 مقارنة التقييم الواقعي بين فترتين")
                p1, p2 = st.columns(2)
                with p1:
                    compare_from_1 = st.date_input("بداية الفترة الأولى:", today_assess - timedelta(days=60), key="real_assess_cmp_from1_v1")
                    compare_to_1 = st.date_input("نهاية الفترة الأولى:", today_assess - timedelta(days=31), key="real_assess_cmp_to1_v1")
                with p2:
                    compare_from_2 = st.date_input("بداية الفترة الثانية:", today_assess - timedelta(days=30), key="real_assess_cmp_from2_v1")
                    compare_to_2 = st.date_input("نهاية الفترة الثانية:", today_assess, key="real_assess_cmp_to2_v1")
                if compare_from_1 > compare_to_1 or compare_from_2 > compare_to_2:
                    st.warning("يرجى التأكد من أن بداية كل فترة تسبق نهايتها.")
                else:
                    recs1 = [r for r in filtered_assessments if str(compare_from_1) <= str(r.get("visit_date") or "") <= str(compare_to_1)]
                    recs2 = [r for r in filtered_assessments if str(compare_from_2) <= str(r.get("visit_date") or "") <= str(compare_to_2)]
                    c1s, n1, score1 = _assessment_summary(recs1)
                    c2s, n2, score2 = _assessment_summary(recs2)
                    comp_df = pd.DataFrame([
                        {"المؤشر": "عدد التقييمات", "الفترة الأولى": len(recs1), "الفترة الثانية": len(recs2), "التغير": len(recs2)-len(recs1)},
                        {"المؤشر": "نسبة المطابقة %", "الفترة الأولى": round(score1,1), "الفترة الثانية": round(score2,1), "التغير": round(score2-score1,1)},
                        {"المؤشر": "عناصر مطابقة", "الفترة الأولى": c1s["مطابق"], "الفترة الثانية": c2s["مطابق"], "التغير": c2s["مطابق"]-c1s["مطابق"]},
                        {"المؤشر": "عناصر غير مطابقة", "الفترة الأولى": c1s["غير مطابق"], "الفترة الثانية": c2s["غير مطابق"], "التغير": c2s["غير مطابق"]-c1s["غير مطابق"]},
                        {"المؤشر": "يحتاج إلى تحسين", "الفترة الأولى": c1s["يحتاج إلى تحسين"], "الفترة الثانية": c2s["يحتاج إلى تحسين"], "التغير": c2s["يحتاج إلى تحسين"]-c1s["يحتاج إلى تحسين"]},
                    ])
                    st.dataframe(comp_df, use_container_width=True, hide_index=True)
                    comp_html = comp_df.to_html(index=False, border=1, classes="table")
                    render_print_button_only(generate_general_report_html("مقارنة التقييم الواقعي بين فترتين", comp_html), "🖨 طباعة مقارنة الفترتين")
                    _excel_download(comp_df, "📥 تحميل مقارنة الفترتين Excel", "real_assessment_period_comparison.xlsx", "dl_real_assess_cmp_v1")

    elif selected_menu == "📈 خطط العمل":
        st.subheader("📈 خطط العمل التدريبية ومعالجة نقاط الضعف بالأمراض المتوطنة (مع إمكانية الحذف)")
        plan_tabs = st.tabs(["➕ إنشاء وتحديث خطة عمل ذكية", "📋 استعراض وإدارة خطط العمل المسجلة", "📄 محاضر التدريب"])
        with plan_tabs[0]:
            if has_subtab_permission('📈 خطط العمل', '➕ إنشاء وتحديث خطة عمل ذكية'):
                st.markdown("#### 🏥 تحديد نطاق خطة العمل حسب الهيكل الإداري")
                plan_scope = hierarchy_scope_widget("نطاق خطة العمل:", "plan_scope_v12")
                plan_scope_sql, plan_scope_args = hierarchy_scope_sql("h", plan_scope)
                with db() as c:
                    all_tr_list = c.execute(
                        f"SELECT DISTINCT t.id, t.name, t.facility, t.profession FROM trainees t LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name) WHERE t.hidden=0 AND {plan_scope_sql} ORDER BY t.id ASC",
                        tuple(plan_scope_args)
                    ).fetchall()
                    all_fac_list = [row[0] for row in c.execute(
                        f"SELECT DISTINCT t.facility FROM trainees t LEFT JOIN hierarchical_facilities h ON (t.facility=h.facility_name OR t.facility LIKE '%' || h.authority || ' - ' || h.administration || ' - ' || h.facility_name OR t.facility LIKE '%' || h.governorate || ' - ' || h.authority || ' - ' || h.center || ' - ' || h.administration || ' - ' || h.facility_name) WHERE t.facility IS NOT NULL AND t.facility != '' AND t.hidden=0 AND {plan_scope_sql} ORDER BY t.facility",
                        tuple(plan_scope_args)
                    ).fetchall()]
                with st.form("create_action_plan_form", clear_on_submit=True):
                    target_category = st.radio("نطاق الخطة:", ["فرد (متدرب محدد)", "جماعة (وحدة الأمراض المتوطنة بالكامل)"], horizontal=True)
                    auto_weakness_text = ""
                    auto_steps_text = ""
                    if "فرد" in target_category:
                        if not all_tr_list:
                            st.warning("⚠ لا توجد بيانات متدربين ظاهرة مسجلة بعد.")
                            target_name = ""
                        else:
                            tr_choices = {f"{t['name']} - الوظيفة: {t['profession']} - الجهة: {t['facility']} (ID: {t['id']})": t for t in all_tr_list}
                            sel_tr_label = st.selectbox("اختر المتدرب لاستخراج نقاط ضعفه تلقائياً:", list(tr_choices.keys()))
                            chosen_tr_obj = tr_choices[sel_tr_label]
                            target_name = chosen_tr_obj['name']
                            with db() as c:
                                incorrect_qs = c.execute("""
                                    SELECT q.category, q.question, eq.selected_option, q.answer
                                    FROM exam_questions eq JOIN questions q ON q.id=eq.question_id
                                    JOIN exam_sessions s ON s.id=eq.session_id
                                    WHERE s.trainee_id=? AND eq.is_correct=0
                                """, (chosen_tr_obj['id'],)).fetchall()
                            if incorrect_qs:
                                failed_cats = list(set([r['category'] for r in incorrect_qs]))
                                auto_weakness_text = f"تم رصد إخفاقات للمتدرب {target_name} في الأقسام التالية بناءً على نتائج الاختبارات الأخيرة:\n- " + "\n- ".join(failed_cats)
                                auto_steps_text = f"1. عقد جلسة تدريب مركزة ومكثفة للأقسام التالية: {', '.join(failed_cats)}.\n2. إعادة الاختبار العملي والنظري بعد استكمال البرنامج العلاجي.\n3. متابعة أداء المتدرب الميداني داخل الوحدة."
                            else:
                                auto_weakness_text = "لم يتم رصد إخفاقات واضحة أو اجتاز المتدرب كافة الأسئلة بنجاح."
                                auto_steps_text = "1. استمرار المتابعة الدورية وتحفيز المتدرب.\n2. إدراج المتدرب في دورات تنشيطية متقدمة للأمراض المتوطنة."
                    else:
                        if not all_fac_list:
                            st.warning("⚠ لا توجد وحدات أو جهات ظاهرة مسجلة بعد.")
                            target_name = ""
                        else:
                            target_name = st.selectbox("اختر وحدة الأمراض المتوطنة المستهدفة:", all_fac_list)
                            with db() as c:
                                fac_incorrect = c.execute("""
                                    SELECT q.category FROM exam_questions eq
                                    JOIN questions q ON q.id=eq.question_id
                                    JOIN exam_sessions s ON s.id=eq.session_id
                                    JOIN trainees t ON t.id=s.trainee_id
                                    WHERE t.facility=? AND t.hidden=0 AND eq.is_correct=0
                                """, (target_name,)).fetchall()
                            if fac_incorrect:
                                fac_cats = list(set([r['category'] for r in fac_incorrect]))
                                auto_weakness_text = f"تم رصد نقاط ضعف متكررة لكوادر وحدة ({target_name}) في الأقسام التالية:\n- " + "\n- ".join(fac_cats)
                                auto_steps_text = f"1. تنفيذ برنامج تدريبي جماعي للعاملين بالوحدة يركز على: {', '.join(fac_cats)}.\n2. توفير الأدلة الإرشادية والمواد التعليمية داخل وحدة الأمراض المتوطنة.\n3. تقييم العاملين بعد أسبوعين من تاريخ الخطة."
                            else:
                                auto_weakness_text = "مستوى العاملين بالوحدة مستقر وتجتاز الاختبارات بكفاءة."
                                auto_steps_text = "1. الحفاظ على مستوى الأداء المتميز.\n2. إجراء تقييم فصلي دوري."
                    st.markdown("---")
                    st.markdown("#### 🎯 نقاط الضعف (تم استنتاجها وتحليلها تلقائياً):")
                    weak_areas = st.text_area("أبرز نقاط الضعف والأقسام المرصودة:", value=auto_weakness_text)
                    st.markdown("#### 🛠 الخطوات الإجرائية والبرنامج التدريبي المقترح:")
                    action_steps = st.text_area("الخطوات العلاجية:", value=auto_steps_text)
                    st.markdown("---")
                    current_online_dt = now_cairo().date()
                    st.markdown("#### 📅 تحديد الإطار الزمني للخطة (من تاريخ إلى تاريخ):")
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        plan_start_date = st.date_input("من تاريخ البدء:", current_online_dt)
                    with col_d2:
                        plan_end_date = st.date_input("إلى تاريخ النهاية:", current_online_dt + timedelta(days=30))
                    with db() as c:
                        all_plan_templates = [dict(r) for r in c.execute("SELECT * FROM exam_templates WHERE active=1 ORDER BY name ASC").fetchall()]
                    applicable_plan_templates = [t for t in all_plan_templates if template_matches_scope(t, plan_scope)]
                    plan_template_options = {"بدون نموذج اختبار محدد": None}
                    for t in applicable_plan_templates:
                        plan_template_options[f"{t['name']} ({t.get('exam_type') or 'اختبار'}) — {template_scope_text(t)} | رقم {t['id']}"] = int(t['id'])
                    selected_plan_template_label = st.selectbox("نموذج الاختبار المرتبط بخطة العمل:", list(plan_template_options.keys()), key="action_plan_template_choice")
                    selected_plan_template_id = plan_template_options[selected_plan_template_label]
                    if st.form_submit_button("💾 حفظ وإنشاء خطة العمل الذكية", use_container_width=True):
                        if not target_name.strip() or not weak_areas.strip():
                            st.warning("⚠ يرجى استكمال البيانات.")
                        else:
                            with db() as c:
                                c.execute("""INSERT INTO action_plans(
                                    target_type, target_name, weakness_areas, action_steps, time_frame_type, start_date, end_date, created_at,
                                    scope_governorate, scope_authority, scope_center, scope_administration, scope_facility, scope_directorate_section, scope_administration_section, template_id
                                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                          (target_category, target_name, weak_areas.strip(), action_steps.strip(), "من تاريخ إلى تاريخ",
                                           plan_start_date.isoformat(), plan_end_date.isoformat(), now(),
                                           plan_scope["scope_governorate"], plan_scope["scope_authority"], plan_scope["scope_center"],
                                           plan_scope["scope_administration"], plan_scope["scope_facility"], plan_scope.get("scope_directorate_section", ""), plan_scope.get("scope_administration_section", ""), selected_plan_template_id))
                            st.success("✅ تم حفظ خطة العمل بناءً على التحليل التلقائي بنجاح!")
                            st.rerun()
        with plan_tabs[1]:
            if has_subtab_permission('📈 خطط العمل', '📋 استعراض وإدارة خطط العمل المسجلة'):
                with db() as c:
                    plans_list = c.execute(
                        f"SELECT * FROM action_plans WHERE " + " AND ".join([f"{k}=?" for k in ["scope_governorate","scope_authority","scope_center","scope_administration","scope_facility"] if str(plan_scope.get(k) or "").strip()]) + " ORDER BY id DESC",
                        tuple(str(plan_scope.get(k) or "").strip() for k in ["scope_governorate","scope_authority","scope_center","scope_administration","scope_facility"] if str(plan_scope.get(k) or "").strip())
                    ).fetchall() if any(str(plan_scope.get(k) or "").strip() for k in ["scope_governorate","scope_authority","scope_center","scope_administration","scope_facility"]) else c.execute("SELECT * FROM action_plans ORDER BY id DESC").fetchall()
                if not plans_list:
                    st.info("لا توجد خطط عمل مسجلة حتى الآن.")
                else:
                    plan_map = {f"خطة رقم ({p['id']}) - [{p['target_type']}] المستهدف: {p['target_name']} | الهيكل: {template_scope_text(dict(p))} (من {p['start_date']} إلى {p['end_date']})": p['id'] for p in plans_list}
                    sel_plan_label = st.selectbox("اختر خطة العمل للمعاينة والطباعة الذكية:", list(plan_map.keys()))
                    chosen_plan_id = plan_map[sel_plan_label]
                    with db() as c:
                        p_data = dict(c.execute("SELECT * FROM action_plans WHERE id=?", (chosen_plan_id,)).fetchone())
                    plan_tpl_name = "بدون نموذج اختبار محدد"
                    if p_data.get("template_id"):
                        with db() as c:
                            plan_tpl_row = c.execute("SELECT name, exam_type FROM exam_templates WHERE id=?", (p_data["template_id"],)).fetchone()
                        if plan_tpl_row:
                            plan_tpl_name = f"{plan_tpl_row['name']} ({plan_tpl_row['exam_type'] or 'اختبار'})"
                    plan_detail_html = f"""
                    <div style="font-family: 'Cairo', sans-serif; direction: rtl; padding: 5px; page-break-inside: avoid; break-inside: avoid;">
                        <h3 style="color: #047857; text-align: center; font-size: 14pt; margin: 5px 0;">خطة عمل لعلاج نقاط الضعف وتحسين الأداء بوحدات الأمراض المتوطنة</h3>
                        <hr style="border: 1px solid #059669; margin: 8px 0;">
                        <p style="font-size: 9.5pt; margin: 4px 0;"><b>نوع النطاق:</b> {esc(p_data['target_type'])} | <b>المستهدف:</b> {esc(p_data['target_name'])} | <b>الهيكل الإداري:</b> {esc(template_scope_text(p_data))} | <b>نموذج الاختبار:</b> {esc(plan_tpl_name)} | <b>الفترة الزمنية:</b> من {esc(p_data['start_date'])} إلى {esc(p_data['end_date'])}</p>
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
                    full_plan_print_html = generate_action_plan_report_html(f"خطة عمل - {p_data['target_name']}", plan_detail_html, header_text=hierarchy_header_html(p_data), hierarchy_scope=p_data)
                    render_print_button_only(full_plan_print_html, f"خطة عمل رقم {chosen_plan_id}")
                    if st.button("🗑 حذف خططة العمل المحددة", use_container_width=True):
                        with db() as c:
                            c.execute("DELETE FROM action_plans WHERE id=?", (chosen_plan_id,))
                        st.success("✅ تم حذف خطة العمل بنجاح!")
                        st.rerun()

        with plan_tabs[2]:
            if has_subtab_permission('📈 خطط العمل', '📄 محاضر التدريب'):
                st.markdown("#### 📄 طباعة وتعديل محضر التدريب:")

                minutes_scope = hierarchy_scope_widget("الهيكل الإداري لمحضر التدريب:", "training_minutes_scope_v1")
                with db() as c:
                    all_tpls_for_minutes = [dict(r) for r in c.execute("SELECT * FROM exam_templates ORDER BY name ASC").fetchall()]
                all_tpls_for_minutes = [t for t in all_tpls_for_minutes if template_matches_scope(t, minutes_scope)]
                if not all_tpls_for_minutes:
                    st.info("لا توجد نماذج اختبارات مسجلة تطابق الهيكل الإداري المحدد.")
                else:
                    minutes_tpl_map = {f"نموذج ({t['id']}) - {t['name']} [{t['exam_type']}] | {template_scope_text(t)}": t['id'] for t in all_tpls_for_minutes}
                    sel_min_tpl_label = st.selectbox("اختر نموذج الاختبار لإنشاء أو تعديل محضر التدريب الخاص به:", list(minutes_tpl_map.keys()), key="sel_min_tpl")
                    chosen_min_tpl_id = minutes_tpl_map[sel_min_tpl_label]

                    with db() as c:
                        existing_min = c.execute("SELECT * FROM training_minutes WHERE template_id=?", (chosen_min_tpl_id,)).fetchone()
                        tpl_rec = c.execute("SELECT * FROM exam_templates WHERE id=?", (chosen_min_tpl_id,)).fetchone()


                    tpl_dict_for_minutes = dict(tpl_rec) if tpl_rec else {}

                    # سجل مستقل للعاملين بالهيكل الوظيفي؛ لا يشترط تسجيلهم كمتدربين.
                    hierarchy_rows_minutes = get_hierarchical_data(include_hidden=False)
                    staff_scope_rows = [h for h in hierarchy_rows_minutes
                        if (not minutes_scope.get('scope_authority') or h.get('authority') == minutes_scope.get('scope_authority'))
                        and (not minutes_scope.get('scope_administration') or h.get('administration') == minutes_scope.get('scope_administration'))
                        and (not minutes_scope.get('scope_facility') or h.get('facility_name') == minutes_scope.get('scope_facility'))
                        and (not minutes_scope.get('scope_directorate_section') or h.get('directorate_section') == minutes_scope.get('scope_directorate_section'))
                        and (not minutes_scope.get('scope_administration_section') or h.get('administration_section') == minutes_scope.get('scope_administration_section'))]
                    staff_facilities = sorted({str(h.get('facility_name') or '').strip() for h in staff_scope_rows if str(h.get('facility_name') or '').strip()})
                    if staff_facilities:
                        with st.expander('👥 إدارة أفراد الهيكل الوظيفي لكشف التوقيعات (لا يشترط تسجيلهم كمتدربين)', expanded=False):
                            with st.form('functional_staff_add_form_v1', clear_on_submit=True):
                                fs_name = st.text_input('اسم العامل')
                                fs_profession = st.text_input('الوظيفة / التخصص', value=professions_display(tpl_dict_for_minutes.get('profession') or '') if tpl_dict_for_minutes.get('profession') else '')
                                fs_facility = st.selectbox('المنشأة التابعة', staff_facilities, key='functional_staff_facility_v1')
                                fs_submit = st.form_submit_button('➕ إضافة العامل للهيكل الوظيفي', use_container_width=True)
                            if fs_submit:
                                if not fs_name.strip() or not fs_profession.strip():
                                    st.warning('اكتب اسم العامل والوظيفة قبل الحفظ.')
                                else:
                                    with db() as c:
                                        c.execute('INSERT INTO functional_staff(name, profession, facility, active, created_at) VALUES(?,?,?,?,?)',
                                                  (fs_name.strip(), fs_profession.strip(), fs_facility, 1, datetime.now().isoformat(timespec='seconds')))
                                    st.success('تمت إضافة العامل إلى الهيكل الوظيفي، وسيظهر في كشف التوقيعات المطابق.')
                                    st.rerun()
                            with db() as c:
                                scoped_staff = [dict(r) for r in c.execute(
                                    'SELECT id, name, profession, facility FROM functional_staff WHERE active=1 ORDER BY facility, name COLLATE NOCASE').fetchall()
                                ]
                            scoped_staff = [r for r in scoped_staff if r['facility'] in staff_facilities]
                            if scoped_staff:
                                st.caption(f'عدد العاملين المسجلين في الهيكل الوظيفي ضمن النطاق الحالي: {len(scoped_staff)}')
                                del_choices = {f"{r['name']} — {r['profession']} — {r['facility']} (رقم {r['id']})": r['id'] for r in scoped_staff}
                                selected_staff_del = st.selectbox('حذف عامل من الهيكل الوظيفي (اختياري)', ['— بدون حذف —'] + list(del_choices), key='functional_staff_delete_choice_v1')
                                if st.button('🗑 حذف العامل المحدد', key='functional_staff_delete_btn_v1', use_container_width=True) and selected_staff_del != '— بدون حذف —':
                                    with db() as c:
                                        c.execute('UPDATE functional_staff SET active=0 WHERE id=?', (del_choices[selected_staff_del],))
                                    st.success('تم حذف العامل من قائمة الهيكل الوظيفي.')
                                    st.rerun()
                    minute_scope_parts = [str(tpl_dict_for_minutes.get(k) or '').strip() for k in ('scope_authority', 'scope_administration', 'scope_facility')]
                    minute_scope_parts = [x for x in minute_scope_parts if x]
                    if not minute_scope_parts:
                        minute_scope_parts = [str(minutes_scope.get(k) or '').strip() for k in ('scope_authority', 'scope_administration', 'scope_facility')]
                        minute_scope_parts = [x for x in minute_scope_parts if x]
                    default_facility_val = " - ".join(minute_scope_parts) if minute_scope_parts else "كل الهيكل الإداري"
                    # توليد بنود وأهداف محضر التدريب من موضوعات الأسئلة الفعلية المرتبطة بالنموذج المحدد؛ لا يُدرج اسم النموذج في النص.
                    profession_label = str(tpl_dict_for_minutes.get('profession') or '').strip() or 'العاملين المستهدفين'
                    default_min_text = (
                        f"في إطار رفع كفاءة العاملين بوحدات الأمراض المتوطنة، عُقدت جلسة تدريبية للعاملين "
                        f"ضمن النطاق الإداري: {default_facility_val}. وركزت الجلسة على مراجعة وتطبيق الموضوعات "
                        "الفنية والإجرائية التي تتناولها أسئلة التقييم ذات الصلة بمهام العمل، مع مناقشة الإجابات "
                        "الصحيحة وأسبابها والأخطاء الشائعة، وتوضيح التطبيق العملي للإجراءات المعتمدة."
                    )
                    try:
                        selected_categories = json.loads(tpl_dict_for_minutes.get('categories_json') or '[]')
                        if not isinstance(selected_categories, list):
                            selected_categories = []
                    except Exception:
                        selected_categories = []
                    with db() as c:
                        if selected_categories:
                            placeholders = ','.join(['?'] * len(selected_categories))
                            question_rows_minutes = [dict(r) for r in c.execute(
                                f"SELECT category, question FROM questions WHERE active=1 AND category IN ({placeholders}) ORDER BY category, id",
                                tuple(selected_categories)).fetchall()]
                        else:
                            question_rows_minutes = [dict(r) for r in c.execute(
                                "SELECT category, question FROM questions WHERE active=1 ORDER BY category, id").fetchall()]
                    question_topics_by_category = {}
                    for qr in question_rows_minutes:
                        category = str(qr.get('category') or '').strip() or 'موضوعات فنية عامة'
                        qtext = clean_question_text(qr.get('question') or '')
                        qtext = re.sub(r'IMAGE:[^\s]+', '', qtext, flags=re.IGNORECASE)
                        qtext = re.sub(r'<[^>]+>', ' ', qtext)
                        qtext = re.sub(r'\s+', ' ', qtext).strip(' ؟?؛;:.')
                        if not qtext:
                            continue
                        bucket = question_topics_by_category.setdefault(category, [])
                        if qtext not in bucket:
                            bucket.append(qtext)
                    generated_items = []
                    generated_goals = []
                    for cat_index, (category, topics) in enumerate(question_topics_by_category.items(), 1):
                        # صياغة البند من موضوعات الأسئلة، مع تجنب نسخ اسم النموذج أو عرضه.
                        topic_text = '؛ '.join(topics[:6])
                        if len(topics) > 6:
                            topic_text += f"؛ ومراجعة بقية الموضوعات المرتبطة ({len(topics) - 6} موضوعات إضافية)"
                        generated_items.append(
                            f"{cat_index}. مراجعة وشرح وتطبيق موضوعات «{category}» التي تقيسها أسئلة التقييم، "
                            f"بما يشمل: {topic_text}. مع مناقشة الإجابات الصحيحة وأسبابها والأخطاء الشائعة والتطبيق العملي."
                        )
                        generated_goals.append(
                            f"{cat_index}. أن يتمكن المشارك من فهم وتطبيق موضوعات «{category}» الواردة في أسئلة التقييم، "
                            "وتفسير الإجابة الصحيحة وتجنب الأخطاء المرتبطة بها أثناء أداء العمل."
                        )
                    if generated_items:
                        default_items_text = '\n'.join(generated_items)
                        default_goals_text = '\n'.join(generated_goals)
                    else:
                        default_items_text = "لا توجد أسئلة نشطة مرتبطة بالمجالات المحددة؛ يرجى مراجعة تصنيفات الأسئلة المرتبطة بالنموذج وإضافة الأسئلة المطلوبة."
                        default_goals_text = "تُحدد أهداف التدريب بعد ربط النموذج بأسئلة نشطة وتصنيفات صحيحة في بنك الأسئلة."
                    default_date_val = now_cairo().strftime('%Y-%m-%d')

                    cur_min_text = existing_min["minutes_text"] if existing_min and existing_min["minutes_text"] else default_min_text
                    cur_items_text = existing_min["training_items"] if existing_min and existing_min["training_items"] else default_items_text
                    cur_goals_text = existing_min["training_goals"] if existing_min and existing_min["training_goals"] else default_goals_text
                    # تحديث النصوص الافتراضية القديمة تلقائيًا فقط؛ لا نمسّ أي محتوى كتبه المستخدم يدويًا.
                    if existing_min and existing_min["training_items"] and ("التعريف بأهداف ومتطلبات نموذج الاختبار" in existing_min["training_items"] or "نموذج الاختبار (" in existing_min["training_items"] or "مراجعة دورة العمل والإجراءات القياسية" in existing_min["training_items"]):
                        cur_items_text = default_items_text
                    if existing_min and existing_min["training_goals"] and ("وفق متطلبات النموذج" in existing_min["training_goals"] or "نموذج الاختبار" in existing_min["training_goals"] or "أن يطبق المشارك دورة العمل والإجراءات القياسية" in existing_min["training_goals"]):
                        cur_goals_text = default_goals_text
                    if existing_min and existing_min["minutes_text"] and "وبناءً على نموذج الاختبار (" in existing_min["minutes_text"]:
                        cur_min_text = default_min_text
                    cur_date_val = existing_min["training_date"] if existing_min and existing_min["training_date"] else default_date_val

                    cur_facility_val = default_facility_val

                    hierarchy_rows_for_minutes = get_hierarchical_data(include_hidden=False)
                    hierarchy_paths_for_minutes = []
                    for hr in hierarchy_rows_for_minutes:
                        path_parts = [str(hr.get(k) or '').strip() for k in ('authority', 'directorate_section', 'administration', 'administration_section', 'facility_name') if str(hr.get(k) or '').strip()]
                        path_label = " - ".join(path_parts)
                        if path_label and path_label not in hierarchy_paths_for_minutes:
                            hierarchy_paths_for_minutes.append(path_label)
                    if not hierarchy_paths_for_minutes:
                        hierarchy_paths_for_minutes = [cur_facility_val or "كل الهيكل الإداري"]
                    if cur_facility_val not in hierarchy_paths_for_minutes and cur_facility_val != "كل الهيكل الإداري":
                        hierarchy_paths_for_minutes.insert(0, cur_facility_val)
                    facility_default_index = hierarchy_paths_for_minutes.index(cur_facility_val) if cur_facility_val in hierarchy_paths_for_minutes else 0
                    with st.form(f"edit_training_minutes_form_{chosen_min_tpl_id}", clear_on_submit=True):
                        st.markdown("##### ✏ تعديل محضر التدريب والبنود والأهداف:")
                        edited_facility_input = st.selectbox("الهيكل الإداري / المنشأة:", hierarchy_paths_for_minutes, index=facility_default_index, key=f"minutes_facility_hierarchy_{chosen_min_tpl_id}")
                        edited_date_input = st.text_input("تاريخ محضر التدريب:", value=cur_date_val)
                        edited_minutes_input = st.text_area("1. محضر التدريب:", value=cur_min_text, height=120)
                        edited_items_input = st.text_area("2. بنود التدريب:", value=cur_items_text, height=140)
                        edited_goals_input = st.text_area("3. الأهداف من التدريب:", value=cur_goals_text, height=140)

                        if st.form_submit_button("💾 حفظ التعديلات على محضر التدريب", use_container_width=True):
                            with db() as c:
                                c.execute("""INSERT INTO training_minutes(template_id, minutes_text, training_items, training_goals, training_date, facility_name, updated_at) VALUES(?,?,?,?,?,?,?)
                                           ON CONFLICT(template_id) DO UPDATE SET minutes_text=excluded.minutes_text, training_items=excluded.training_items, training_goals=excluded.training_goals, training_date=excluded.training_date, facility_name=excluded.facility_name, updated_at=excluded.updated_at""",
                                          (chosen_min_tpl_id, edited_minutes_input.strip(), edited_items_input.strip(), edited_goals_input.strip(), edited_date_input.strip(), edited_facility_input.strip(), now()))
                            st.success("✅ تم حفظ وتعديل محضر التدريب بنجاح!")
                            st.rerun()

                    st.markdown("---")
                    st.markdown("##### 🖨 معاينة وطباعة محضر التدريب:")
                    print_sett_m = get_print_settings()

                    line_sp_m = print_sett_m.get('line_spacing', 1.25)


                    user_scope_pred, user_scope_args = hierarchy_filter_for_trainees(current_user_trainee_scope(), "t")
                    with db() as c:
                        all_minutes_trainees = [dict(r) for r in c.execute(
                            f"SELECT t.id, t.name, t.profession, t.facility, t.assigned_template_id FROM trainees t WHERE COALESCE(t.hidden,0)=0 AND {user_scope_pred} ORDER BY t.name COLLATE NOCASE", tuple(user_scope_args)
                        ).fetchall()]
                    hierarchy_rows_minutes = get_hierarchical_data(include_hidden=False)
                    matching_minutes_trainees = []
                    minutes_has_scope = any(str(minutes_scope.get(k) or '').strip() for k in ('scope_authority', 'scope_administration', 'scope_facility'))
                    template_has_scope = any(str(tpl_dict_for_minutes.get(k) or '').strip() for k in ('scope_authority', 'scope_administration', 'scope_facility'))
                    for trainee_row in all_minutes_trainees:
                        if not template_matches_profession(tpl_dict_for_minutes, trainee_row.get('profession')):
                            continue
                        assigned_id = trainee_row.get('assigned_template_id')
                        if assigned_id not in (None, 0, chosen_min_tpl_id):
                            continue
                        if trainee_row.get('assigned_template_id') not in (None, 0, chosen_min_tpl_id):
                            continue
                        if not minutes_has_scope and not template_has_scope:

                            matching_minutes_trainees.append(trainee_row)
                            continue
                        matching_scope_rows = [hrow for hrow in hierarchy_rows_minutes
                            if (not minutes_scope.get('scope_authority') or hrow.get('authority') == minutes_scope.get('scope_authority'))
                            and (not minutes_scope.get('scope_administration') or hrow.get('administration') == minutes_scope.get('scope_administration'))
                            and (not minutes_scope.get('scope_facility') or hrow.get('facility_name') == minutes_scope.get('scope_facility'))
                            and (not tpl_dict_for_minutes.get('scope_authority') or hrow.get('authority') == tpl_dict_for_minutes.get('scope_authority'))
                            and (not tpl_dict_for_minutes.get('scope_administration') or hrow.get('administration') == tpl_dict_for_minutes.get('scope_administration'))
                            and (not tpl_dict_for_minutes.get('scope_facility') or hrow.get('facility_name') == tpl_dict_for_minutes.get('scope_facility'))]
                        if any(trainee_matches_hierarchy(trainee_row.get('facility'), hrow) for hrow in matching_scope_rows):
                            matching_minutes_trainees.append(trainee_row)

                    # اربط كشف التوقيعات بسجل العاملين الفعلي في الهيكل الوظيفي، بمن فيهم غير المسجلين كمتدربين.
                    with db() as c:
                        functional_staff_rows = [dict(r) for r in c.execute(
                            "SELECT id, name, profession, facility FROM functional_staff WHERE active=1 ORDER BY name COLLATE NOCASE"
                        ).fetchall()]
                    for staff_row in functional_staff_rows:
                        if not template_matches_profession(tpl_dict_for_minutes, staff_row.get('profession')):
                            continue
                        if not minutes_has_scope and not template_has_scope:
                            matching_minutes_trainees.append(staff_row)
                            continue
                        staff_matching_scope_rows = [hrow for hrow in hierarchy_rows_minutes
                            if (not minutes_scope.get('scope_authority') or hrow.get('authority') == minutes_scope.get('scope_authority'))
                            and (not minutes_scope.get('scope_administration') or hrow.get('administration') == minutes_scope.get('scope_administration'))
                            and (not minutes_scope.get('scope_facility') or hrow.get('facility_name') == minutes_scope.get('scope_facility'))
                            and (not minutes_scope.get('scope_directorate_section') or hrow.get('directorate_section') == minutes_scope.get('scope_directorate_section'))
                            and (not minutes_scope.get('scope_administration_section') or hrow.get('administration_section') == minutes_scope.get('scope_administration_section'))
                            and (not tpl_dict_for_minutes.get('scope_authority') or hrow.get('authority') == tpl_dict_for_minutes.get('scope_authority'))
                            and (not tpl_dict_for_minutes.get('scope_administration') or hrow.get('administration') == tpl_dict_for_minutes.get('scope_administration'))
                            and (not tpl_dict_for_minutes.get('scope_facility') or hrow.get('facility_name') == tpl_dict_for_minutes.get('scope_facility'))]
                        if any(trainee_matches_hierarchy(staff_row.get('facility'), hrow) for hrow in staff_matching_scope_rows):
                            matching_minutes_trainees.append(staff_row)

                    # إزالة التكرار إذا كان العامل موجودًا في سجل المتدربين والهيكل الوظيفي معًا.
                    unique_minutes_people = []
                    seen_minutes_people = set()
                    for person in matching_minutes_trainees:
                        person_key = (normalize_text(person.get('name')), normalize_text(person.get('profession')), normalize_text(person.get('facility')))
                        if person_key not in seen_minutes_people:
                            seen_minutes_people.add(person_key)
                            unique_minutes_people.append(person)
                    matching_minutes_trainees = unique_minutes_people

                    final_min_t = edited_minutes_input if 'edited_minutes_input' in locals() else cur_min_text
                    final_items_t = edited_items_input if 'edited_items_input' in locals() else cur_items_text
                    final_goals_t = edited_goals_input if 'edited_goals_input' in locals() else cur_goals_text
                    final_date_t = edited_date_input if 'edited_date_input' in locals() else cur_date_val
                    final_fac_t = edited_facility_input if 'edited_facility_input' in locals() else cur_facility_val

                    days_ar = {
                        'Monday': 'الإثنين', 'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء',
                        'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت', 'Sunday': 'الأحد'
                    }
                    day_name_str = ""
                    try:
                        parsed_dt = datetime.strptime(final_date_t.strip(), "%Y-%m-%d")
                        eng_day = parsed_dt.strftime("%A")
                        day_name_str = days_ar.get(eng_day, "")
                    except:
                        pass
                
                    date_display_block = (f"<b>اليوم:</b> {day_name_str}<br>" if day_name_str else "") + f"<b>التاريخ:</b> {final_date_t}"

                    def build_minutes_signature_rows(trainee_slice, start_index):
                        """إنشاء صف توقيع لكل فرد مطابق، دون حد ثابت لعدد الصفوف."""
                        rows_html = ""
                        for offset, trainee_row in enumerate(trainee_slice):
                            row_num = start_index + offset
                            trainee_name = esc(trainee_row.get('name') or '')
                            rows_html += f"""
                            <tr>
                                <td style="border: 1px solid #059669; padding: 3px; text-align: center; font-size: 10pt; width: 12%;">{row_num}</td>
                                <td style="border: 1px solid #059669; padding: 3px; text-align: right; font-size: 10pt; width: 50%;">{trainee_name}</td>
                                <td style="border: 1px solid #059669; padding: 3px; text-align: right; font-size: 10pt; width: 38%;">&nbsp;</td>
                            </tr>
                            """
                        return rows_html

                    # تقسيم جميع الأفراد المطابقين على الكشفين (أ) و(ب)، مع إنشاء صف لكل فرد.
                    # بذلك يزيد عدد الصفوف تلقائيًا حسب عدد العاملين/المتدربين في النطاق الوظيفي المحدد.
                    signature_split_at = (len(matching_minutes_trainees) + 1) // 2
                    signatures_rows_html = build_minutes_signature_rows(matching_minutes_trainees[:signature_split_at], 1)
                    signatures_rows_b_html = build_minutes_signature_rows(matching_minutes_trainees[signature_split_at:], signature_split_at + 1)
                    if matching_minutes_trainees:
                        st.caption(f"تم العثور على {len(matching_minutes_trainees)} فردًا مطابقًا للهيكل الإداري والمهنة ونموذج الاختبار. سيظهر جميع الأفراد في كشف التوقيع تلقائيًا.")
                    else:
                        st.info("لا توجد أسماء متدربين مطابقة لنطاق هذا النموذج ومهنته؛ سيظل كشف التوقيع فارغًا ويمكن تعبئته يدويًا.")

                    side_by_side_tables_html = f"""
                    <div style="display: flex; flex-direction: row; align-items:flex-start; gap: 4mm; width: 100%; margin-top: 3mm; margin-bottom: 3mm;">
                        <div style="flex: 1;">
                            <div style="font-weight: bold; color: #047857; font-size: 10.5pt; margin-bottom: 1mm; text-align: center;">كشف توقيع المتدربين (أ)</div>
                            <table style="width: 100%; border-collapse: collapse;">
                                <thead>
                                    <tr style="background-color: #059669; color: white;">
                                        <th style="border: 1px solid #059669; padding: 5px; font-size: 10pt; text-align: center;">م</th>
                                        <th style="border: 1px solid #059669; padding: 5px; font-size: 10pt; text-align: center;">اسم المتدرب</th>
                                        <th style="border: 1px solid #059669; padding: 5px; font-size: 10pt; text-align: center;">التوقيع</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {signatures_rows_html}
                                </tbody>
                            </table>
                        </div>
                        <div style="flex: 1;">
                            <div style="font-weight: bold; color: #047857; font-size: 10.5pt; margin-bottom: 1mm; text-align: center;">كشف توقيع المتدربين (ب)</div>
                            <table style="width: 100%; border-collapse: collapse;">
                                <thead>
                                    <tr style="background-color: #059669; color: white;">
                                        <th style="border: 1px solid #059669; padding: 5px; font-size: 10pt; text-align: center;">م</th>
                                        <th style="border: 1px solid #059669; padding: 5px; font-size: 10pt; text-align: center;">اسم المتدرب</th>
                                        <th style="border: 1px solid #059669; padding: 5px; font-size: 10pt; text-align: center;">التوقيع</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {signatures_rows_b_html}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    """

                    minutes_print_html = f"""
                    <!DOCTYPE html>
                    <html lang="ar" dir="rtl">
                    <head>
                    <meta charset="UTF-8">
                    <style>
                    @page {{ size: A4 landscape; margin: 10mm 8mm 18mm 8mm !important; }}
                    body {{ font-family: 'Cairo', 'Tahoma', sans-serif; background: #ffffff; color: #111827; margin: 0 !important; padding: 0 !important; direction: rtl; -webkit-print-color-adjust: exact; line-height: {line_sp_m}; }}
                    .report-wrapper {{ width: 281mm; max-width: 281mm; margin: 0 auto !important; padding: 0 !important; position: relative; box-sizing: border-box; }}
                    .print-admin-header {{ display:flex; flex-direction:row; align-items:flex-start; justify-content:space-between; gap:5mm; width:100%; margin:0; padding:0; border:0; box-sizing:border-box; direction:ltr; }}
                    .print-admin-logos {{ display:flex; flex:0 0 auto; flex-direction:row; align-items:flex-start; justify-content:flex-start; gap:2mm; min-width:16mm; }}
                    .print-admin-hierarchy {{ flex:1; text-align:right; font-size:8.5pt; font-weight:700; line-height:1.25; color:#1f2937; }}
                    .print-hierarchy-line {{ margin:0 0 0.5mm 0; }} .print-hierarchy-label {{ color:#475569; font-weight:900; }} .print-target-line {{ box-sizing:border-box; width:50%; margin:1.5mm auto 0 auto; padding:1.2mm 2mm; border:1px solid #065f46; border-radius:1.5mm; text-align:center; color:#065f46; font-size:10.5pt; font-weight:900; }}
                    h2 {{ text-align: center; color: #047857; font-size: 16pt; margin: 0 0 2mm 0 !important; }}
                    .meta-info {{ display: flex; flex-direction: row; direction: ltr; justify-content: space-between; align-items: center; font-size: 11.5pt; font-weight: bold; color: #065f46; background: #f0fdf4; border: 1px solid #059669; padding: 2.5mm 5mm; border-radius: 4px; margin-bottom: 3mm; }}
                    .meta-info .meta-entity {{ direction: rtl; text-align: left; width: 50%; box-sizing: border-box; }}
                    .meta-info .meta-date {{ direction: rtl; text-align: right; width: 50%; box-sizing: border-box; }}
                    .section-box {{ background: #f8fafc; border: 1px solid #059669; padding: 4mm; border-radius: 5px; font-size: 12pt; white-space: pre-wrap; line-height: 1.5; margin-bottom: 3mm; }}
                    .section-title {{ font-weight: bold; color: #047857; font-size: 13pt; margin-bottom: 1mm; border-bottom: 1px dashed #059669; padding-bottom: 1mm; }}
                    </style>
                    </head>
                    <body>
                    <div class="report-wrapper">
                        {hierarchy_header_html(st.session_state.get("_last_hierarchy_scope", {}))}
                        <h2>محضر تدريب</h2>
                        <div class="meta-info">
                            <div class="meta-entity">المنشأة / الجهة: {esc(final_fac_t)}</div>
                            <div class="meta-date">{date_display_block}</div>
                        </div>
                    
                        <div class="section-title">1. محضر التدريب</div>
                        <div class="section-box">{esc(final_min_t)}</div>

                        <div class="section-title">2. بنود التدريب</div>
                        <div class="section-box">{esc(final_items_t)}</div>

                        <div class="section-title">3. الأهداف من التدريب</div>
                        <div class="section-box">{esc(final_goals_t)}</div>

                        {side_by_side_tables_html}
                    </div>
                    </body>
                    </html>
                    """
                    render_print_button_only(minutes_print_html, f"محضر تدريب نموذج رقم {chosen_min_tpl_id}")

    elif selected_menu == "📚 قاعدة بيانات المتدربين":
        st.subheader("📚 قاعدة بيانات المتدربين — عرض وتعديل وطباعة وتصدير")
        st.warning("تحتوي هذه الصفحة على بيانات شخصية حساسة. استخدمها للمخولين فقط، وتأكد من مراجعة البيانات قبل تصديرها أو طباعتها.")
        all_scope = hierarchy_scope_widget("فلترة البيانات حسب الهيكل الإداري:", "trainee_db_scope_v1")
        all_scope_pred, all_scope_args = hierarchy_filter_for_trainees(all_scope, "t")
        with db() as c:
            rows = c.execute(f"SELECT t.* FROM trainees t WHERE {all_scope_pred} ORDER BY t.id DESC", tuple(all_scope_args)).fetchall()
            templates_db = c.execute("SELECT id, name, exam_type FROM exam_templates ORDER BY name").fetchall()
        df_db = pd.DataFrame([dict(r) for r in rows])
        if df_db.empty:
            st.info("لا توجد بيانات متدربين ضمن النطاق المحدد.")
        else:
            search_db = st.text_input("🔎 بحث بالاسم أو الرقم القومي أو الهاتف أو رقم السجل:", key="trainee_db_search_v1")
            status_options = ["الكل"] + sorted({str(x) for x in df_db.get("status", pd.Series(dtype=str)).dropna().tolist()})
            status_db = st.selectbox("حالة التسجيل:", status_options, key="trainee_db_status_v1")
            if status_db != "الكل":
                df_db = df_db[df_db["status"].astype(str) == status_db]
            if search_db.strip():
                q_norm = normalize_text(search_db)
                q_digits = normalize_digits(search_db)
                mask = df_db.apply(lambda row: (
                    q_norm in normalize_text(row.get("name", ""))
                    or (bool(q_digits) and q_digits in normalize_national_id(row.get("national_id", "")))
                    or (bool(q_digits) and q_digits in normalize_egyptian_phone(row.get("phone", "")))
                    or q_norm == str(row.get("id", ""))
                ), axis=1)
                df_db = df_db[mask]
            status_labels = {"pending":"في انتظار اعتماد الإدارة", "approved":"معتمد ومصرح بالدخول", "active":"اختبار جارٍ", "completed":"مكتمل", "rejected":"مرفوض"}
            display_columns = [
                ("id", "رقم السجل"), ("name", "الاسم"), ("national_id", "الرقم القومي"), ("phone", "رقم الهاتف"),
                ("profession", "الوظيفة / التخصص"), ("facility", "الجهة الإدارية / المنشأة"),
                ("work_start_date", "تاريخ استلام العمل"), ("status", "حالة التسجيل"),
                ("assigned_template_id", "رقم نموذج الاختبار"), ("created_at", "تاريخ التسجيل"),
                ("approved_at", "تاريخ الاعتماد"), ("updated_at", "آخر تحديث"), ("hidden", "مخفي")
            ]
            export_df = df_db.copy()
            for col, label in display_columns:
                if col not in export_df.columns:
                    export_df[col] = ""
            export_df = export_df[[c for c, _ in display_columns]].rename(columns={c: label for c, label in display_columns})
            if "حالة التسجيل" in export_df.columns:
                export_df["حالة التسجيل"] = export_df["حالة التسجيل"].map(lambda x: status_labels.get(str(x), x))
            st.caption(f"عدد السجلات المطابقة: {len(export_df)}")
            st.dataframe(export_df, use_container_width=True, hide_index=True)
            dl1, dl2 = st.columns(2)
            with dl1:
                csv_data = export_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button("📥 تصدير CSV", data=csv_data, file_name="trainees_database.csv", mime="text/csv", use_container_width=True, key="trainees_db_csv_v1")
            with dl2:
                xlsx_out = io.BytesIO()
                with pd.ExcelWriter(xlsx_out, engine="openpyxl") as writer:
                    export_df.to_excel(writer, index=False, sheet_name="Trainees")
                st.download_button("📥 تصدير Excel", data=xlsx_out.getvalue(), file_name="trainees_database.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="trainees_db_xlsx_v1")
            printable_rows = "".join("<tr>" + "".join(f"<td style='border:1px solid #bbb;padding:5px'>{esc('' if pd.isna(v) else str(v))}</td>" for v in row) + "</tr>" for row in export_df.fillna("").itertuples(index=False, name=None))
            printable_headers = "".join(f"<th style='border:1px solid #bbb;padding:6px;background:#e5e7eb'>{esc(str(col))}</th>" for col in export_df.columns)
            printable_html = generate_general_report_html("قاعدة بيانات المتدربين", f"<table style='border-collapse:collapse;width:100%;font-size:8pt'><thead><tr>{printable_headers}</tr></thead><tbody>{printable_rows}</tbody></table>", target_pages=0)
            render_print_button_only(printable_html, "طباعة قاعدة بيانات المتدربين")

            st.markdown("---")
            st.markdown("#### ✏️ تعديل بيانات متدرب")
            row_choices = {f"سجل {int(r['id'])} — {r.get('name','')} — {r.get('phone','')}": int(r["id"]) for _, r in df_db.iterrows()}
            if row_choices:
                selected_record_label = st.selectbox("اختر المتدرب للتعديل:", list(row_choices.keys()), key="trainee_db_edit_pick_v1")
                selected_record_id = row_choices[selected_record_label]
                selected_record = df_db[df_db["id"].astype(int) == selected_record_id].iloc[0].to_dict()
                try:
                    current_work_date = date.fromisoformat(str(selected_record.get("work_start_date") or ""))
                except Exception:
                    current_work_date = now_cairo().date()
                current_status = str(selected_record.get("status") or "pending")
                current_template = selected_record.get("assigned_template_id")
                template_labels = ["بدون نموذج"] + [f"{t['name']} ({t['exam_type'] or 'قبل التدريب'}) — ID {t['id']}" for t in templates_db]
                template_ids = [None] + [int(t["id"]) for t in templates_db]
                current_template_index = template_ids.index(int(current_template)) if current_template is not None and int(current_template) in template_ids else 0
                with st.form("trainee_db_edit_form_v1", clear_on_submit=True):
                    ed_name = st.text_input("الاسم:", value=str(selected_record.get("name") or ""))
                    ed_nid = st.text_input("الرقم القومي:", value=str(selected_record.get("national_id") or ""), max_chars=14)
                    ed_phone = st.text_input("رقم الهاتف:", value=str(selected_record.get("phone") or ""))
                    ed_prof = st.text_input("الوظيفة / التخصص:", value=str(selected_record.get("profession") or ""))
                    ed_facility = st.text_input("الجهة الإدارية / المنشأة:", value=str(selected_record.get("facility") or ""))
                    ed_work_date = st.date_input("تاريخ استلام العمل:", value=current_work_date, max_value=now_cairo().date(), format="DD/MM/YYYY")
                    status_values = ["pending", "approved", "active", "completed", "rejected"]
                    status_labels_list = [status_labels[x] for x in status_values]
                    status_index = status_values.index(current_status) if current_status in status_values else 0
                    ed_status_label = st.selectbox("حالة التسجيل:", status_labels_list, index=status_index)
                    ed_template_label = st.selectbox("نموذج الاختبار المخصص:", template_labels, index=current_template_index)
                    ed_hidden = st.checkbox("إخفاء السجل من القوائم العامة", value=bool(selected_record.get("hidden", 0)))
                    save_trainee_db = st.form_submit_button("💾 حفظ جميع التعديلات", use_container_width=True)
                if save_trainee_db:
                    if not user_can_access_trainee_id(selected_record_id):
                        st.error("⛔ لا يمكنك تعديل متدرب خارج نطاق الهيكل الإداري المخصص لك.")
                        st.stop()
                    ed_nid_norm = normalize_national_id(ed_nid)
                    ed_phone_norm = normalize_egyptian_phone(ed_phone)
                    if not ed_name.strip() or not ed_facility.strip():
                        st.error("أدخل الاسم وجهة العمل.")
                    elif not is_valid_egyptian_national_id(ed_nid_norm):
                        st.error("الرقم القومي غير صحيح؛ راجع 14 رقماً وتاريخ الميلاد وكود المحافظة.")
                    elif not is_valid_egyptian_mobile(ed_phone_norm):
                        st.error("رقم الموبايل المصري غير صحيح.")
                    else:
                        try:
                            update_trainee_data(selected_record_id, ed_facility, ed_name, ed_phone_norm, ed_nid_norm, ed_prof, ed_work_date.isoformat())
                            chosen_status = status_values[status_labels_list.index(ed_status_label)]
                            chosen_tpl_id = template_ids[template_labels.index(ed_template_label)]
                            with db() as c:
                                c.execute("UPDATE trainees SET status=?, assigned_template_id=?, hidden=?, updated_at=? WHERE id=?", (chosen_status, chosen_tpl_id, int(ed_hidden), now(), selected_record_id))
                            st.success("تم حفظ بيانات المتدرب بنجاح.")
                            st.rerun()
                        except ValueError as e:
                            errors = {"DUPLICATE_TRAINEE_PHONE":"رقم الهاتف مستخدم في سجل آخر.", "DUPLICATE_TRAINEE_NATIONAL_ID":"الرقم القومي مستخدم في سجل آخر.", "INVALID_TRAINEE_PHONE":"رقم الهاتف غير صحيح.", "INVALID_TRAINEE_NATIONAL_ID":"الرقم القومي غير صحيح."}
                            st.error(errors.get(str(e), f"تعذر حفظ البيانات: {e}"))

    elif selected_menu == "💾 النسخ الاحتياطي":
        st.subheader("💾 النسخ الاحتياطي واستعادة قاعدة البيانات والدمج")
        st.warning("⚠️ التصفير يحذف المتدربين والأسئلة والنماذج والمواعيد والهيكل الإداري ونتائج الامتحانات والخطط والتقارير. سيظل حساب المالك وإعدادات الطباعة محفوظين.")
        with st.form("owner_confirm_full_database_reset_v2", clear_on_submit=False):
            reset_owner_username = st.text_input("اسم دخول المالك للتأكيد:", value="", key="reset_owner_username_v2")
            reset_owner_password = st.text_input("كلمة مرور المالك الحالية:", type="password", value="", key="reset_owner_password_v2")
            reset_phrase = st.text_input("اكتب العبارة التالية كما هي: تصفير قاعدة البيانات", value="", key="reset_phrase_v2")
            reset_submit = st.form_submit_button("🗑️ تأكيد تصفير قاعدة البيانات بالكامل", use_container_width=True)
        if reset_submit:
            if not is_owner():
                st.error("هذه العملية متاحة لحساب المالك فقط.")
            elif reset_phrase.strip() != "تصفير قاعدة البيانات":
                st.error("اكتب عبارة التأكيد المطلوبة بشكل صحيح.")
            elif normalize_text(reset_owner_username) != normalize_text(st.session_state.get("username", "")):
                st.error("اسم الدخول يجب أن يطابق حساب المالك المسجل دخوله حاليًا.")
            else:
                with db() as c:
                    owner_row = c.execute("SELECT * FROM users WHERE username=? AND role='admin' AND active=1", (st.session_state.get("username", ""),)).fetchone()
                    if not owner_row or not verify_password(reset_owner_password, owner_row["password_hash"]):
                        st.error("كلمة مرور المالك غير صحيحة؛ لم يتم حذف أي بيانات.")
                    else:

                        for table in ("exam_questions", "exam_sessions", "exam_schedules", "training_minutes", "facility_real_assessments", "action_plans", "trainees", "questions", "exam_templates", "hierarchical_facilities", "audit_logs"):
                            if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                                c.execute(f'DELETE FROM "{table}"')

                        c.execute("DELETE FROM users WHERE role<>'admin'")
                        seq_tables = ("hierarchical_facilities", "exam_templates", "exam_schedules", "trainees", "questions", "exam_sessions", "exam_questions", "action_plans", "facility_real_assessments", "audit_logs", "training_minutes")
                        for table in seq_tables:
                            try:
                                c.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))
                            except sqlite3.OperationalError:
                                pass
                        st.success("تم تصفير بيانات التشغيل بنجاح. حُفظ حساب المالك وإعدادات الطباعة، وأصبحت قاعدة البيانات جاهزة للبدء من جديد.")
                        st.rerun()
        col_bk1, col_bk2 = st.columns(2)
        with col_bk1:
            with open(DB_PATH, "rb") as f:
                db_bytes = f.read()
            st.download_button("📥 تحميل النسخة (.db)", data=db_bytes, file_name="endemic_labs_exam_v1_0.db", mime="application/octet-stream", use_container_width=True)
        with col_bk2:
            uploaded_db_file = st.file_uploader("رفع ملف قاعدة بيانات (.db):", type=["db"], key="restore_db_uploader")
            if uploaded_db_file is not None:
                c_btn_res, c_btn_merge = st.columns(2)
                with c_btn_res:
                    if st.button("⚠ استبدال القاعدة الحالية بالكامل", use_container_width=True):
                        try:
                            with open(DB_PATH, "wb") as f_out:
                                f_out.write(uploaded_db_file.getbuffer())
                            st.success("✅ تمت الاستعادة بنجاح!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"خطأ: {e}")
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
                                    exists = dest_conn.execute("SELECT 1 FROM hierarchical_facilities WHERE governorate=? AND authority=? AND center=? AND administration=? AND facility_name=?",
                                                               (h["governorate"], h["authority"], h["center"], h["administration"], h["facility_name"])).fetchone()
                                    if not exists:
                                        dest_conn.execute("INSERT INTO hierarchical_facilities(governorate, authority, center, administration, facility_name, created_at, hidden) VALUES(?,?,?,?,?,?,?)",
                                                          (h["governorate"], h["authority"], h["center"], h["administration"], h["facility_name"], h["created_at"], h["hidden"] if h["hidden"] is not None else 0))
                                        merged_h_count += 1
                            src_conn.close()
                            if os.path.exists(temp_db_path):
                                os.remove(temp_db_path)
                            reindex_hierarchical_facilities()
                            st.success(f"🎉 تم الدمج بنجاح! (تم إضافة {merged_q_count} سؤالاً، و {merged_h_count} وحدة متوطنة جديدة دون فقدان البيانات السابقة).")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"خطأ أثناء الدمج: {e}")

    elif selected_menu == "👥 إدارة المستخدمين":
        st.subheader("👥 إدارة المستخدمين وصلاحياتهم وتعديل بيانات الاعتماد (مع إمكانية الحذف)")
        tab_u1, tab_u2, tab_u3, tab_u4 = st.tabs(["➕ إضافة مستخدم", "⚙ الصلاحيات والحذف", "🔑 تعديل اسم وكلمة المرور", "🛠 إدارة أسماء الصلاحيات"])
        with tab_u1:
            if has_subtab_permission('👥 إدارة المستخدمين', '➕ إضافة مستخدم'):
                with st.form("add_user_form_v1_0", clear_on_submit=True):
                    new_u_name = st.text_input("اسم المستخدم:", value="")
                    new_u_pass = st.text_input("كلمة المرور (8 أحرف/أرقام على الأقل):", type="password", value="")
                    new_u_job_title = st.text_input("الوظيفة / المسمى الوظيفي للمستخدم:", value="", placeholder="مثال: مدير إدارة، طبيب، فني معمل")
                    available_role_labels = get_role_labels()
                    assignable_roles = [rk for rk in available_role_labels if rk != "admin"]
                    if not assignable_roles:
                        assignable_roles = ["exam_manager", "viewer"]
                    new_u_role = st.selectbox("مستوى الصلاحية داخل النظام:", assignable_roles, format_func=lambda x: f"{available_role_labels.get(x, x)} — الوظيفة: {new_u_job_title.strip()}" if new_u_job_title.strip() else available_role_labels.get(x, x))
                    st.markdown("#### صلاحيات الأقسام والتبويبات الداخلية")
                    selected_modules_checkboxes = {}
                    selected_subtabs_checkboxes = {}
                    for mod_key, mod_desc in ALL_MENU_MODULES.items():
                        with st.container():
                            selected_modules_checkboxes[mod_key] = st.checkbox(f"السماح بالقسم الرئيسي: {mod_key}", value=True, key=f"new_main_perm_{mod_key}")
                            for tab_label in SUBTAB_PERMISSION_CATALOG.get(mod_key, []):
                                selected_subtabs_checkboxes[subtab_permission_key(mod_key, tab_label)] = st.checkbox(f"تبويب: {tab_label}", value=True, key=f"new_sub_perm_{mod_key}_{tab_label}")
                    st.markdown("#### 🏥 تحديد نطاق الهيكل الإداري للمستخدم")
                    st.caption("الأقسام فروع مستقلة: أقسام المديرية والإدارات تتبع المديرية، وأقسام الإدارة والمنشآت تتبع الإدارة.")
                    add_scope_rows = get_hierarchical_data(include_hidden=False)
                    add_scope_level = st.selectbox("نطاق صلاحية المستخدم:", ["كل الهيكل الإداري", "المديرية / الجهة", "قسم داخل المديرية", "الإدارة", "قسم داخل الإدارة", "المنشأة"], key="add_user_scope_level")
                    add_user_scope = {"scope_governorate":"", "scope_authority":"", "scope_center":"", "scope_administration":"", "scope_facility":"", "scope_directorate_section":"", "scope_administration_section":""}
                    if add_scope_level != "كل الهيكل الإداري":
                        auth_vals = hierarchy_ordered_unique(rr.get("authority") for rr in add_scope_rows if rr.get("authority"))
                        if auth_vals:
                            chosen_auth = st.selectbox("المديرية / الجهة المسموح بها:", auth_vals, key="add_user_scope_authority")
                            add_user_scope["scope_authority"] = chosen_auth
                            auth_rows = [rr for rr in add_scope_rows if str(rr.get("authority") or "").strip() == chosen_auth]
                            if add_scope_level == "قسم داخل المديرية":
                                vals = hierarchy_ordered_unique(rr.get("directorate_section") for rr in auth_rows if rr.get("directorate_section"))
                                if vals:
                                    add_user_scope["scope_directorate_section"] = st.selectbox("قسم المديرية المسموح به:", vals, key="add_user_scope_directorate_section")
                            elif add_scope_level in ("الإدارة", "قسم داخل الإدارة", "المنشأة"):
                                vals = hierarchy_ordered_unique(rr.get("administration") for rr in auth_rows if rr.get("administration"))
                                if vals:
                                    chosen_admin = st.selectbox("الإدارة المسموح بها:", vals, key="add_user_scope_administration")
                                    add_user_scope["scope_administration"] = chosen_admin
                                    admin_rows = [rr for rr in auth_rows if str(rr.get("administration") or "").strip() == chosen_admin]
                                    if add_scope_level == "قسم داخل الإدارة":
                                        vals = hierarchy_ordered_unique(rr.get("administration_section") for rr in admin_rows if rr.get("administration_section"))
                                        if vals:
                                            add_user_scope["scope_administration_section"] = st.selectbox("قسم الإدارة المسموح به:", vals, key="add_user_scope_administration_section")
                                    elif add_scope_level == "المنشأة":
                                        vals = hierarchy_ordered_unique(rr.get("facility_name") for rr in admin_rows if rr.get("facility_name"))
                                        if vals:
                                            add_user_scope["scope_facility"] = st.selectbox("المنشأة المسموح بها:", vals, key="add_user_scope_facility")
                    if st.form_submit_button("💾 حفظ", use_container_width=True):
                        if new_u_name.strip() and new_u_pass.strip() and len(new_u_pass) >= 8:
                            assigned_perms = [k for k, v in selected_modules_checkboxes.items() if v] + [k for k, v in selected_subtabs_checkboxes.items() if v]
                            with db() as c:
                                try:
                                    if not any(str(add_user_scope.get(k) or "").strip() for k in ("scope_governorate", "scope_authority", "scope_directorate_section", "scope_center", "scope_administration", "scope_administration_section", "scope_facility")):
                                        add_user_scope["scope_all"] = True
                                    c.execute("INSERT INTO users(username, display_name, job_title, password_hash, role, permissions_json, hierarchy_scope_json, active, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                                              (new_u_name.strip(), new_u_name.strip(), new_u_job_title.strip(), hash_password(new_u_pass), new_u_role, json.dumps(assigned_perms, ensure_ascii=False), json.dumps(add_user_scope, ensure_ascii=False), 1, now()))
                                    st.success("✅ تم الإضافة!")
                                except sqlite3.IntegrityError:
                                    st.error("مستخدم مسبقاً.")
                        elif new_u_pass.strip() and len(new_u_pass) < 8:
                            st.warning("كلمة المرور يجب ألا تقل عن 8 أحرف أو أرقام.")
                        else:
                            st.warning("أدخل اسم المستخدم وكلمة المرور.")
        with tab_u2:
            if has_subtab_permission('👥 إدارة المستخدمين', '⚙ الصلاحيات والحذف'):
                with db() as c:
                    all_users = c.execute("SELECT id, username, role, permissions_json, hierarchy_scope_json FROM users WHERE role != 'admin'").fetchall()
                if not all_users:
                    st.info("لا توجد مستخدمين.")
                else:
                    user_map = {f"مستخدم: {u['username']}": u for u in all_users}
                    sel_user_label = st.selectbox("اختر المستخدم:", list(user_map.keys()))
                    target_user = user_map[sel_user_label]
                    try:
                        curr_user_perms = json.loads(target_user["permissions_json"]) if target_user["permissions_json"] else []
                    except:
                        curr_user_perms = []
                    try:
                        curr_hierarchy_scope = json.loads(target_user["hierarchy_scope_json"] or "{}")
                    except Exception:
                        curr_hierarchy_scope = {}
                    st.markdown("#### 🏥 نطاق الهيكل الإداري المسموح للمستخدم")
                    edit_scope_rows = get_hierarchical_data(include_hidden=False)
                    existing_scope_level = "كل الهيكل الإداري"
                    if curr_hierarchy_scope.get("scope_facility"):
                        existing_scope_level = "المنشأة"
                    elif curr_hierarchy_scope.get("scope_administration"):
                        existing_scope_level = "الإدارة"
                    elif curr_hierarchy_scope.get("scope_administration_section"):
                        existing_scope_level = "قسم داخل الإدارة"
                    elif curr_hierarchy_scope.get("scope_directorate_section"):
                        existing_scope_level = "قسم داخل المديرية"
                    elif curr_hierarchy_scope.get("scope_authority"):
                        existing_scope_level = "المديرية / الجهة"
                    edit_scope_level = st.selectbox("نطاق صلاحية المستخدم:", ["كل الهيكل الإداري", "المديرية / الجهة", "قسم داخل المديرية", "الإدارة", "قسم داخل الإدارة", "المنشأة"], index=["كل الهيكل الإداري", "المديرية / الجهة", "قسم داخل المديرية", "الإدارة", "قسم داخل الإدارة", "المنشأة"].index(existing_scope_level), key=f"edit_user_scope_level_{target_user['id']}")
                    edit_user_scope = {"scope_governorate":"", "scope_authority":"", "scope_center":"", "scope_administration":"", "scope_facility":"", "scope_directorate_section":"", "scope_administration_section":""}
                    if edit_scope_level != "كل الهيكل الإداري":
                        auth_vals = hierarchy_ordered_unique(rr.get("authority") for rr in edit_scope_rows if rr.get("authority"))
                        if auth_vals:
                            old_value = str(curr_hierarchy_scope.get("scope_authority") or "")
                            idx = auth_vals.index(old_value) if old_value in auth_vals else 0
                            chosen_auth = st.selectbox("المديرية / الجهة المسموح بها:", auth_vals, index=idx, key=f"edit_user_scope_{target_user['id']}_authority")
                            edit_user_scope["scope_authority"] = chosen_auth
                            auth_rows = [rr for rr in edit_scope_rows if str(rr.get("authority") or "").strip() == chosen_auth]
                            if edit_scope_level == "قسم داخل المديرية":
                                vals = hierarchy_ordered_unique(rr.get("directorate_section") for rr in auth_rows if rr.get("directorate_section"))
                                if vals:
                                    old_value = str(curr_hierarchy_scope.get("scope_directorate_section") or "")
                                    idx = vals.index(old_value) if old_value in vals else 0
                                    edit_user_scope["scope_directorate_section"] = st.selectbox("قسم المديرية المسموح به:", vals, index=idx, key=f"edit_user_scope_{target_user['id']}_directorate_section")
                            elif edit_scope_level in ("الإدارة", "قسم داخل الإدارة", "المنشأة"):
                                vals = hierarchy_ordered_unique(rr.get("administration") for rr in auth_rows if rr.get("administration"))
                                if vals:
                                    old_value = str(curr_hierarchy_scope.get("scope_administration") or "")
                                    idx = vals.index(old_value) if old_value in vals else 0
                                    chosen_admin = st.selectbox("الإدارة المسموح بها:", vals, index=idx, key=f"edit_user_scope_{target_user['id']}_administration")
                                    edit_user_scope["scope_administration"] = chosen_admin
                                    admin_rows = [rr for rr in auth_rows if str(rr.get("administration") or "").strip() == chosen_admin]
                                    if edit_scope_level == "قسم داخل الإدارة":
                                        vals = hierarchy_ordered_unique(rr.get("administration_section") for rr in admin_rows if rr.get("administration_section"))
                                        if vals:
                                            old_value = str(curr_hierarchy_scope.get("scope_administration_section") or "")
                                            idx = vals.index(old_value) if old_value in vals else 0
                                            edit_user_scope["scope_administration_section"] = st.selectbox("قسم الإدارة المسموح به:", vals, index=idx, key=f"edit_user_scope_{target_user['id']}_administration_section")
                                    elif edit_scope_level == "المنشأة":
                                        vals = hierarchy_ordered_unique(rr.get("facility_name") for rr in admin_rows if rr.get("facility_name"))
                                        if vals:
                                            old_value = str(curr_hierarchy_scope.get("scope_facility") or "")
                                            idx = vals.index(old_value) if old_value in vals else 0
                                            edit_user_scope["scope_facility"] = st.selectbox("المنشأة المسموح بها:", vals, index=idx, key=f"edit_user_scope_{target_user['id']}_facility")
                    with st.form(f"edit_user_perms_{target_user['id']}", clear_on_submit=True):
                        st.markdown("#### صلاحيات الأقسام والتبويبات الداخلية")
                        edit_checkboxes = {}
                        for mod_key, mod_desc in ALL_MENU_MODULES.items():
                            with st.container():
                                edit_checkboxes[mod_key] = st.checkbox(f"السماح بالقسم الرئيسي: {mod_key}", value=(mod_key in curr_user_perms), key=f"mod_chk_{target_user['id']}_{mod_key}")
                                for tab_label in SUBTAB_PERMISSION_CATALOG.get(mod_key, []):
                                    sub_key = subtab_permission_key(mod_key, tab_label)
                                    edit_checkboxes[sub_key] = st.checkbox(f"تبويب: {tab_label}", value=(sub_key in curr_user_perms or mod_key in curr_user_perms), key=f"sub_chk_{target_user['id']}_{mod_key}_{tab_label}")
                        c_save, c_del = st.columns(2)
                        with c_save:
                            save_btn = st.form_submit_button("💾 حفظ", use_container_width=True)
                        with c_del:
                            del_btn = st.form_submit_button("🗑 حذف المستخدم", use_container_width=True)
                        if save_btn:
                            new_assigned = [k for k, v in edit_checkboxes.items() if v]
                            if not any(str(edit_user_scope.get(k) or "").strip() for k in ("scope_governorate", "scope_authority", "scope_directorate_section", "scope_center", "scope_administration", "scope_administration_section", "scope_facility")):
                                edit_user_scope["scope_all"] = True
                            with db() as c:
                                c.execute("UPDATE users SET permissions_json=?, hierarchy_scope_json=? WHERE id=?", (json.dumps(new_assigned, ensure_ascii=False), json.dumps(edit_user_scope, ensure_ascii=False), target_user["id"]))
                            st.success("✅ تم التحديث!")
                            st.rerun()
                        if del_btn:
                            with db() as c:
                                c.execute("DELETE FROM users WHERE id=?", (target_user["id"],))
                            st.success("✅ تم الحذف بنجاح!")
                            st.rerun()
        with tab_u3:
            if has_subtab_permission('👥 إدارة المستخدمين', '🔑 تعديل اسم وكلمة المرور'):
                st.markdown("#### 🔐 تعديل بيانات المالك والمستخدمين")
                st.warning("تنبيه أمني: لا يتم قبول كلمة مرور الحساب المستهدف بدلًا من كلمة مرورك. يجب أن تكون مسجلًا بحساب المالك، وتأكيد كلمة مرور حساب المالك الحالي. لا توجد كلمة مرور افتراضية أو استثناء ثابت داخل شاشة التعديل.")
                with db() as c:
                    all_sys_users = c.execute("SELECT id, username, display_name, job_title, role FROM users ORDER BY CASE WHEN role='admin' THEN 0 ELSE 1 END, username").fetchall()
                if not all_sys_users:
                    st.info("لا توجد حسابات.")
                else:
                    sys_user_choices = {f"{(u['display_name'] or u['username'])} — دخول: {u['username']} — الوظيفة: {(u['job_title'] or role_label(u['role']))} — الصلاحية: {role_label(u['role'])}": u for u in all_sys_users}
                    with st.form("edit_credentials_form_v2", clear_on_submit=True):
                        sel_target_user_label = st.selectbox("اختر الحساب المراد تعديله:", list(sys_user_choices.keys()))
                        chosen_target = sys_user_choices[sel_target_user_label]
                        new_display_name = st.text_input("الاسم الظاهر:", value=(chosen_target["display_name"] or chosen_target["username"]))
                        new_username_input = st.text_input("اسم الدخول الجديد:", value=chosen_target["username"])
                        new_job_title_input = st.text_input("الوظيفة / المسمى الوظيفي:", value=(chosen_target["job_title"] or ""), placeholder="مثال: مدير إدارة، طبيب، فني معمل")
                        current_password_input = st.text_input("كلمة مرور حساب المالك المسجل دخوله حاليًا للتأكيد:", type="password", value="")
                        new_password_input = st.text_input("كلمة المرور الجديدة (اتركها فارغة للاحتفاظ بالحالية):", type="password", value="")
                        submit_credentials = st.form_submit_button("🔒 تحديث بيانات الحساب", use_container_width=True)
                    if submit_credentials:
                        new_display_clean = new_display_name.strip()
                        new_uname_clean = new_username_input.strip()
                        new_job_title_clean = new_job_title_input.strip()
                        if not current_password_input:
                            st.warning("يرجى إدخال كلمة مرور المالك الحالية للتأكيد.")
                        elif not new_display_clean or not new_uname_clean:
                            st.error("الاسم الظاهر واسم الدخول لا يمكن أن يكونا فارغين.")
                        elif new_password_input and len(new_password_input) < 8:
                            st.error("كلمة المرور الجديدة يجب ألا تقل عن 8 أحرف أو أرقام.")
                        else:
                            with db() as c:
                                actor_user = c.execute("SELECT * FROM users WHERE username=? AND active=1", (st.session_state.username,)).fetchone()


                                chosen_row = c.execute("SELECT * FROM users WHERE id=?", (chosen_target["id"],)).fetchone()
                                is_authorized_owner = bool(actor_user and actor_user["role"] == "admin" and verify_password(current_password_input, actor_user["password_hash"]))
                                if not is_authorized_owner:
                                    st.error("تعذر التحقق: كلمة مرور المالك الحالية غير صحيحة، أو أن الجلسة ليست جلسة مالك.")
                                elif not chosen_row:
                                    st.error("الحساب المحدد لم يعد موجودًا. حدّث الصفحة ثم أعد المحاولة.")
                                else:
                                    try:
                                        if new_password_input:
                                            c.execute("UPDATE users SET username=?, display_name=?, job_title=?, password_hash=? WHERE id=?", (new_uname_clean, new_display_clean, new_job_title_clean, hash_password(new_password_input), chosen_target["id"]))
                                        else:
                                            c.execute("UPDATE users SET username=?, display_name=?, job_title=? WHERE id=?", (new_uname_clean, new_display_clean, new_job_title_clean, chosen_target["id"]))
                                        c.commit()
                                        is_editing_self = int(chosen_target["id"]) == int(actor_user["id"])
                                        if is_editing_self:
                                            st.session_state.logged_in = False
                                            st.session_state.username = ""
                                            st.session_state.role = ""
                                            st.session_state.permissions = []
                                            st.success("تم تحديث بيانات المالك بنجاح. سجّل الدخول باستخدام اسم الدخول وكلمة المرور الجديدة.")
                                            st.rerun()
                                        else:
                                            st.success("تم تحديث بيانات الحساب والوظيفة بنجاح. لم تتغير جلسة المالك.")
                                            st.rerun()
                                    except sqlite3.IntegrityError:
                                        st.error("اسم الدخول الجديد مستخدم بالفعل؛ اختر اسمًا آخر.")

        with tab_u4:
            if has_subtab_permission('👥 إدارة المستخدمين', '🛠 إدارة أسماء الصلاحيات'):
                st.markdown("#### 🛠 تعديل اسم الصلاحية أو إضافة صلاحية جديدة")
                st.caption("تغيير الاسم هنا يغيّر الاسم الظاهر فقط، ولا يغيّر صلاحيات الوصول. صلاحيات الوصول الفعلية تُضبط من تبويب «الصلاحيات والحذف». لا يمكن إنشاء أو تعديل مفتاح مالك المنصة من هذه الشاشة.")
                role_labels_now = get_role_labels()
                editable_role_keys = [k for k in role_labels_now if k != "admin"]
                if editable_role_keys:
                    role_to_edit = st.selectbox("اختر الصلاحية لتعديل اسمها:", editable_role_keys, format_func=lambda k: role_labels_now.get(k, k), key="role_label_edit_select")
                    with st.form("edit_role_label_form"):
                        updated_role_label = st.text_input("اسم الصلاحية الجديد:", value=role_labels_now.get(role_to_edit, role_to_edit), max_chars=80)
                        save_role_label = st.form_submit_button("💾 حفظ اسم الصلاحية")
                    if save_role_label:
                        cleaned_label = updated_role_label.strip()
                        if not cleaned_label:
                            st.error("اكتب اسمًا للصلاحية.")
                        else:
                            with db() as c:
                                c.execute("INSERT INTO role_labels(role_key, role_label) VALUES(?, ?) ON CONFLICT(role_key) DO UPDATE SET role_label=excluded.role_label", (role_to_edit, cleaned_label))
                            st.success("تم تحديث اسم الصلاحية.")
                            st.rerun()
                else:
                    st.info("لا توجد صلاحيات قابلة للتعديل.")
                st.divider()
                st.markdown("##### ➕ إضافة صلاحية جديدة")
                with st.form("add_custom_role_form"):
                    new_role_label = st.text_input("اسم الصلاحية الجديدة:", placeholder="مثال: مشرف التدريب", max_chars=80)
                    st.caption("بعد إنشاء الصلاحية، اخترها عند إضافة المستخدم، ثم حدّد له الشاشات المسموح بها من تبويب «الصلاحيات والحذف».")
                    add_role_submit = st.form_submit_button("➕ إنشاء الصلاحية")
                if add_role_submit:
                    cleaned_new_label = new_role_label.strip()
                    existing_labels_norm = {v.strip().casefold() for v in role_labels_now.values()}
                    if not cleaned_new_label:
                        st.error("اكتب اسم الصلاحية الجديدة.")
                    elif cleaned_new_label.casefold() in existing_labels_norm:
                        st.error("اسم الصلاحية موجود بالفعل.")
                    else:
                        new_role_key = "custom_" + secrets.token_hex(6)
                        with db() as c:
                            c.execute("INSERT INTO role_labels(role_key, role_label) VALUES(?, ?)", (new_role_key, cleaned_new_label))
                        st.success("تم إنشاء الصلاحية. ستظهر في قائمة مستوى الصلاحية عند إضافة مستخدم جديد.")
                        st.rerun()

    elif selected_menu == "🧾 سجل التدقيق":
        st.subheader("🧾 سجل التدقيق")
        with db() as c:
            df_audit = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100", c)
        st.dataframe(df_audit, use_container_width=True, hide_index=True)

def trainee_portal():
    with db() as c:
        tr = c.execute("SELECT * FROM trainees WHERE id=? AND hidden=0", (st.session_state.trainee_id,)).fetchone()
    if not tr:
        st.session_state.trainee_id = ""
        st.rerun()
    header()
    if tr["status"] == "pending":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #064e3b, #047857); color: #ffffff; padding: 35px; border-radius: 16px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-top: 40px; font-family: 'Cairo', sans-serif;">
            <div style="font-size: 26px; font-weight: 900; margin-bottom: 10px;">⏳ حسابك في انتظار اعتماد الإدارة</div>
            <p style="font-size: 15px; color: #d1fae5;">جاري تحديث الصفحة تلقائياً حتى يتم اعتمادك وتفعيل الاختبار...</p>
        </div>
        """, unsafe_allow_html=True)


        if st.button("🔄 تحديث الصفحة يدوياً", use_container_width=True):
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state.trainee_id = ""
            st.rerun()
        return

    assigned_tpl_id = tr["assigned_template_id"]
    with db() as c:
        matching_template = c.execute("SELECT * FROM exam_templates WHERE id=?", (assigned_tpl_id,)).fetchone() if assigned_tpl_id else None

    is_exam_open = False
    if matching_template:
        t_dict = dict(matching_template)
        trainee_schedule = get_schedule_for_trainee(tr["id"], t_dict.get("id"))
        start_t = trainee_schedule.get("start_time") if trainee_schedule else None
        end_t = trainee_schedule.get("end_time") if trainee_schedule else None
        if start_t and end_t:
            try:
                dt_now = now_cairo()
                dt_start = datetime.fromisoformat(str(start_t))
                dt_end = datetime.fromisoformat(str(end_t))

                if dt_start.tzinfo is None:
                    dt_start = dt_start.replace(tzinfo=CAIRO_TZ)
                else:
                    dt_start = dt_start.astimezone(CAIRO_TZ)
                if dt_end.tzinfo is None:
                    dt_end = dt_end.replace(tzinfo=CAIRO_TZ)
                else:
                    dt_end = dt_end.astimezone(CAIRO_TZ)
                if dt_start <= dt_now <= dt_end:
                    is_exam_open = True
            except:
                pass

    if not is_exam_open:

        upcoming_schedule = None
        upcoming_start = None
        upcoming_end = None
        if matching_template:
            try:
                upcoming_schedule = get_schedule_for_trainee(tr["id"], matching_template["id"])
                if upcoming_schedule and upcoming_schedule.get("start_time") and upcoming_schedule.get("end_time"):
                    upcoming_start = datetime.fromisoformat(str(upcoming_schedule["start_time"]))
                    upcoming_end = datetime.fromisoformat(str(upcoming_schedule["end_time"]))
                    if upcoming_start.tzinfo is None:
                        upcoming_start = upcoming_start.replace(tzinfo=CAIRO_TZ)
                    if upcoming_end.tzinfo is None:
                        upcoming_end = upcoming_end.replace(tzinfo=CAIRO_TZ)
            except Exception:
                upcoming_schedule = None
        if upcoming_start and upcoming_end and now_cairo() < upcoming_start:
            start_label = upcoming_start.astimezone(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p").replace("AM", "صباحاً").replace("PM", "مساءً")
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1e3a8a,#2563eb);color:white;padding:32px;border-radius:16px;text-align:center;margin:35px auto;max-width:900px;font-family:'Cairo',sans-serif">
              <div style="font-size:28px;font-weight:900">⏳ الامتحان لم يبدأ بعد</div>
              <div style="font-size:18px;margin-top:12px">سيُفتح الامتحان تلقائياً في الموعد المحدد</div>
              <div style="font-size:17px;margin-top:8px">موعد البدء: <b>{esc(start_label)}</b> — بتوقيت مصر</div>
              <div style="margin-top:10px;font-size:14px">سيتم تحديث الشاشة تلقائياً دون الحاجة إلى تسجيل الخروج.</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔄 تحديث الموعد", key="trainee_refresh_upcoming", use_container_width=True):
                st.rerun()
        elif upcoming_end and now_cairo() > upcoming_end:
            st.warning("انتهت فترة إتاحة الامتحان المحددة لهذا النموذج. يرجى مراجعة الإدارة.")

        else:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #064e3b, #047857); color: #ffffff; padding: 45px; border-radius: 16px; text-align: center; box-shadow: 0 6px 20px rgba(0,0,0,0.15); border: 3px solid #059669; margin-top: 50px; margin-bottom: 30px; font-family: 'Cairo', sans-serif;">
                <div style="font-size: 34px; font-weight: 900; letter-spacing: 1px;">🚫 لا يوجد امتحانات متوفرة الان</div>
                <div style="font-size:16px;margin-top:12px">ستُحدّث الشاشة تلقائياً للتحقق من الموعد.</div>
            </div>
            """, unsafe_allow_html=True)


            refresh_col, home_col = st.columns(2)
            with refresh_col:
                if st.button("🔄 تحديث الصفحة الآن", key="trainee_refresh_no_exam", use_container_width=True):
                    st.rerun()
            with home_col:
                if st.button("🏠 العودة للشاشة الرئيسية", key="trainee_home_no_exam", use_container_width=True):
                    st.session_state.trainee_id = ""
                    st.session_state.pop("exam_session_id", None)
                    st.rerun()
    else:
        t_dict = dict(matching_template)
        tpl_name_str = t_dict.get("name", "اختبار معتمد")
        exam_type_str = t_dict.get("exam_type", "قبل التدريب")
        start_t = trainee_schedule.get("start_time") if trainee_schedule else None
        end_t = trainee_schedule.get("end_time") if trainee_schedule else None
        def format_12h(iso_str):
            if not iso_str or "T" not in iso_str:
                return iso_str
            try:
                dt = datetime.fromisoformat(iso_str)
                return dt.strftime("%Y-%m-%d %I:%M %p").replace("AM", "صباحاً").replace("PM", "مساءً")
            except:
                return iso_str
        st.markdown(f"""
        <div style="background-color: #059669; color: #ffffff; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin: 15px auto; max-width: 900px; border: 2px solid #34d399;">
            <h2 style="margin: 0 0 6px 0; font-size: 20px; font-weight: 900; color: #ffffff;">نظام تقييم واختبار العاملين بالأمراض المتوطنة</h2>
            <p style="margin: 0; font-size: 14px; color: #d1fae5;">المتدرب: <b>{esc(tr["name"])}</b> &nbsp;|&nbsp; الوظيفة: <b>{esc(tr['profession'] if tr['profession'] is not None else '')}</b> &nbsp;|&nbsp; الاختبار المخصص: <b>{esc(tpl_name_str)}</b> [{esc(exam_type_str)}]</p>
        </div>
        """, unsafe_allow_html=True)
        with st.container(border=True):
            format_s = format_12h(start_t)
            format_e = format_12h(end_t)
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.markdown(f"🟢 **وقت البدء:**\n`{format_s}`")
            with col_s2:
                st.markdown(f"🔴 **و وقت النهاية:**\n`{format_e}`")
        st.success("🟢 **الاختبار مفتوح ومتاح الآن للتنفيذ!**")
        exam_stage_choice = exam_type_str
        if exam_type_str == "قبل وبعد التدريب (نفس النموذج)":
            exam_stage_choice = st.radio("حدد مرحلة أداء النموذج نفسه:", ["قبل التدريب", "بعد التدريب"], horizontal=True, key=f"exam_stage_choice_{tr['id']}_{matching_template['id']}")
            st.caption("يمكن أداء النموذج نفسه قبل التدريب وبعده. تُسجَّل كل مرحلة منفصلة للمقارنة بين النتائج.")
        try:
            sid = start_session(tr["id"], matching_template["id"], exam_stage_choice)
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
            st.session_state.trainee_id = ""
            st.rerun()



if hasattr(st, "fragment"):
    trainee_portal = st.fragment(run_every="3s")(trainee_portal)

def render_readonly_trainee_exam_review(session_id):
    """Show the trainee's own submitted exam and selected answers read-only until review expiry; never expose answer key."""
    with db() as c:
        session = c.execute("SELECT s.*, t.name trainee_name, t.facility, e.name template_name FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.id=? AND t.hidden=0", (int(session_id),)).fetchone()
        if not session:
            st.warning("نموذج المراجعة غير متاح.")
            return
        enforce_session_access_or_raise(session_id, c)
        expiry_raw = session["review_expires_at"]
        if not expiry_raw:

            try:
                tpl = c.execute("SELECT duration_minutes FROM exam_templates WHERE id=?", (session["template_id"],)).fetchone()
                mins = max(1, int(tpl["duration_minutes"] or 60)) if tpl else 60
                sub_dt = datetime.fromisoformat(session["submitted_at"] or session["expires_at"])
                if sub_dt.tzinfo is None: sub_dt = sub_dt.replace(tzinfo=CAIRO_TZ)
                expiry_raw = (sub_dt + timedelta(minutes=mins)).isoformat(timespec="seconds")
                c.execute("UPDATE exam_sessions SET review_expires_at=? WHERE id=? AND review_expires_at IS NULL", (expiry_raw, int(session_id)))
            except Exception:
                expiry_raw = None
        try:
            review_expiry = datetime.fromisoformat(expiry_raw) if expiry_raw else None
            if review_expiry and review_expiry.tzinfo is None: review_expiry = review_expiry.replace(tzinfo=CAIRO_TZ)
        except Exception:
            review_expiry = None
        if not review_expiry or now_cairo() >= review_expiry:
            st.info("انتهت مدة عرض نموذج الامتحان الخاص بك.")
            return
        rows = c.execute("SELECT eq.position, eq.selected_option, eq.option_order_json, q.question, q.options_json FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=? ORDER BY eq.position", (int(session_id),)).fetchall()
        trainee_name = session["trainee_name"]
        template_name = session["template_name"] or "الاختبار"
    remaining = max(0, int((review_expiry - now_cairo()).total_seconds()))
    st.markdown(f"""<div style="border:2px solid #0f766e;border-radius:12px;padding:16px;margin:12px 0;background:#f0fdfa;color:#134e4a;text-align:center">
    <h3>📘 نموذج امتحانك — للعرض فقط</h3><b>المتدرب:</b> {esc(trainee_name)} &nbsp; | &nbsp; <b>النموذج:</b> {esc(template_name)}<br>
    <b>متبقي لعرض النموذج:</b> <span id="review-timer">{remaining // 60:02d}:{remaining % 60:02d}</span><br><small>لن يمكنك تعديل الإجابات، ولا يعرض هذا النموذج مفتاح الإجابات الصحيحة.</small></div>""", unsafe_allow_html=True)

    components.html(f"""<script>(function(){{let s={remaining};const el=window.parent.document.getElementById('review-timer');function tick(){{if(s<=0){{window.parent.location.reload();return;}}if(el)el.textContent=String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');s--;setTimeout(tick,1000);}}tick();}})();</script>""", height=0)
    for idx, row in enumerate(rows, start=1):
        try: opts = json.loads(row["options_json"] or "[]")
        except Exception: opts = []
        try: order = json.loads(row["option_order_json"] or "[]")
        except Exception: order = list(range(len(opts)))
        if sorted(order) != list(range(len(opts))): order = list(range(len(opts)))
        selected = row["selected_option"]
        option_lines=[]
        for oi in order:
            chosen = selected is not None and int(oi) == int(selected)
            option_lines.append(f"<div style='padding:6px 10px;margin:4px 0;border:1px solid {'#0f766e' if chosen else '#d1d5db'};border-radius:6px;background:{'#ccfbf1' if chosen else '#fff'}'>{'☑' if chosen else '☐'} {esc(opts[oi] if oi < len(opts) else '')}</div>")
        qtext = clean_question_text(row["question"] or "")
        st.markdown(f"<div style='border:1px solid #cbd5e1;border-radius:10px;padding:12px;margin:10px 0'><b>السؤال {idx}:</b> {esc(qtext)}{''.join(option_lines)}</div>", unsafe_allow_html=True)

def exam_interface(session_id):
    header()
    with db() as c:
        session = c.execute("""SELECT s.*, t.facility, t.id AS scoped_trainee_id, t.name AS scoped_trainee_name,
                                    et.start_time AS legacy_scheduled_start_time, et.end_time AS legacy_scheduled_end_time
                             FROM exam_sessions s
                             JOIN trainees t ON t.id=s.trainee_id
                             LEFT JOIN exam_templates et ON et.id=s.template_id
                             WHERE s.id=? AND t.hidden=0""", (int(session_id),)).fetchone()
        if not session:
            st.error("جلسة الاختبار غير موجودة أو غير متاحة.")
            return

        enforce_session_access_or_raise(session_id, c)
        if session["status"] != "active":
            st.error("هذه الجلسة غير نشطة أو تم تسليمها بالفعل.")
            return



        active_schedule = get_schedule_for_trainee(session["trainee_id"], session["template_id"]) if session["template_id"] else None
        schedule_start_raw = active_schedule.get("start_time") if active_schedule else None
        schedule_end_raw = active_schedule.get("end_time") if active_schedule else None
        try:
            if not schedule_start_raw or not schedule_end_raw:
                raise ValueError("وقت الجدولة غير محدد")
            schedule_start = datetime.fromisoformat(schedule_start_raw)
            schedule_end = datetime.fromisoformat(schedule_end_raw)
            if schedule_start.tzinfo is None:
                schedule_start = schedule_start.replace(tzinfo=CAIRO_TZ)
            if schedule_end.tzinfo is None:
                schedule_end = schedule_end.replace(tzinfo=CAIRO_TZ)
            schedule_now = now_cairo()
            if schedule_now < schedule_start:
                st.warning("⏳ لم يحن موعد الاختبار بعد. سيظهر الامتحان في الموعد المحدد فقط.")
                st.caption("موعد البدء: " + schedule_start.strftime("%Y-%m-%d %I:%M %p").replace("AM", "صباحاً").replace("PM", "مساءً"))
                st.caption("سيُعاد فحص الموعد تلقائياً دون إعادة تحميل المتصفح.")
                return
            if schedule_now > schedule_end:
                st.warning("انتهت الفترة المحددة لإتاحة الاختبار. سيتم اعتماد الإجابات المحفوظة وإغلاق الجلسة.")
                submit_session(session_id)
                st.session_state.last_result_id = int(session_id)
                st.session_state.exam_session_id = None
                st.rerun()
                return
        except Exception as schedule_error:
            if isinstance(schedule_error, ValueError) and str(schedule_error) == "وقت الجدولة غير محدد":
                st.error("الاختبار غير متاح لأن الإدارة لم تحدد وقت البدء والنهاية بشكل صحيح.")
                return

            st.error("تعذر التحقق من موعد الاختبار؛ لن يتم عرض الأسئلة حتى تصحيح موعد النموذج.")
            return

        try:
            exam_expiry = datetime.fromisoformat(session["expires_at"])
            if exam_expiry.tzinfo is None:
                exam_expiry = exam_expiry.replace(tzinfo=CAIRO_TZ)
        except Exception:
            exam_expiry = now_cairo() - timedelta(seconds=1)
        exam_is_expired = now_cairo() >= exam_expiry
        rows = c.execute("SELECT eq.*, q.question, q.options_json FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.session_id=? ORDER BY eq.position", (int(session_id),)).fetchall()


    st.markdown(
        f"<div style='position:sticky;top:0;z-index:9999;background:rgba(255,255,255,.96);border:1px solid #b91c1c;color:#991b1b;padding:8px;text-align:center;font-weight:800;pointer-events:none;'>نسخة مخصصة للمتدرب: {esc(session['scoped_trainee_name'])} | رقم الجلسة: {int(session_id)} | يمنع تداول محتوى الاختبار</div>",
        unsafe_allow_html=True,
    )
    remaining_seconds = max(0, int((exam_expiry - now_cairo()).total_seconds()))
    st.markdown(f"""<div style="position:sticky;top:42px;z-index:9998;background:#fff7ed;border:2px solid #ea580c;color:#9a3412;border-radius:10px;padding:10px;text-align:center;font-weight:900;margin:10px 0">
    ⏱ الوقت المتبقي: <span id="exam-countdown">{remaining_seconds // 60:02d}:{remaining_seconds % 60:02d}</span>
    </div>""", unsafe_allow_html=True)
    components.html(f"""<script>(function(){{let s={remaining_seconds};function tick(){{const d=window.parent.document.getElementById('exam-countdown');if(s<=0){{if(d)d.textContent='00:00';window.parent.location.reload();return;}}if(d)d.textContent=String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');s--;setTimeout(tick,1000);}}tick();}})();</script>""", height=0)
    if exam_is_expired:
        st.warning("انتهى الوقت المحدد للاختبار. يتم الآن اعتماد الإجابات المحفوظة تلقائياً.")
        auto_result = submit_session(session_id)
        if auto_result is not None:
            st.session_state.last_result_id = int(session_id)
            st.session_state.exam_session_id = None
            st.rerun()
        return

    answered = 0
    for idx, row in enumerate(rows, start=1):
        try:
            opts = json.loads(row["options_json"])
        except Exception:
            opts = ["نعم", "لا"]
        try:
            order = json.loads(row["option_order_json"])
            if sorted(order) != list(range(len(opts))):
                order = list(range(len(opts)))
        except Exception:
            order = list(range(len(opts)))
        disp_opts = [opts[i] for i in order]
        curr_idx = None
        if row["selected_option"] is not None:
            try:
                curr_idx = disp_opts.index(opts[row["selected_option"]])
            except Exception:
                pass
        question_text = esc(clean_question_text(row["question"]))
        st.markdown(f'<div class="question"><strong style="color:#065f46;">({idx})</strong> {question_text}</div>', unsafe_allow_html=True)
        choice = st.radio("اختر الإجابة:", disp_opts, index=curr_idx, key=f"q_{row['id']}", label_visibility="collapsed", disabled=exam_is_expired)
        if choice and not exam_is_expired:
            sel = order[disp_opts.index(choice)]
            with db() as c:
                enforce_session_access_or_raise(session_id, c)
                c.execute("""UPDATE exam_questions
                             SET selected_option=?, is_correct=CASE WHEN ?=(SELECT answer FROM questions WHERE id=question_id) THEN 1 ELSE 0 END
                             WHERE id=? AND session_id=? AND EXISTS (
                                 SELECT 1 FROM exam_sessions s WHERE s.id=? AND s.status='active'
                             )""", (sel, sel, int(row["id"]), int(session_id), int(session_id)))
            answered += 1
    st.progress(answered / len(rows) if rows else 0)
    if st.button("تسليم الاختبار نهائياً", use_container_width=True):
        res = submit_session(session_id)
        if res is not None:
            st.session_state.last_result_id = int(session_id)
            st.session_state.exam_session_id = None
            st.rerun()




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
        try:
            enforce_session_access_or_raise(sid)
        except PermissionError:
            st.session_state.last_result_id = None
            st.error("لا يمكنك الوصول إلى نتيجة تخص متدربًا آخر.")
            st.stop()
        header()
        with db() as c:
            result_row = c.execute("SELECT s.*, t.name trainee_name, e.duration_minutes FROM exam_sessions s JOIN trainees t ON t.id=s.trainee_id LEFT JOIN exam_templates e ON e.id=s.template_id WHERE s.id=?", (int(sid),)).fetchone()
        if not result_row:
            st.error("تعذر العثور على نتيجة الاختبار.")
            st.stop()
        if int(result_row["passed"] or 0) == 1:
            st.success(f"🎉 ألف مبروك يا {esc(result_row['trainee_name'])}! لقد اجتزت الاختبار بنجاح.")
            st.balloons()
        else:
            st.warning(f"💪 حظ أوفر المرة القادمة يا {esc(result_row['trainee_name'])}. لا تيأس، واصل التعلم والمحاولة.")
        st.markdown(f"**النتيجة:** {float(result_row['score'] or 0):g} من {float(result_row['max_score'] or 0):g} — **النسبة:** {float(result_row['percent'] or 0):.1f}%")
        st.caption("تم تسليم الاختبار أو اعتماده تلقائيًا عند انتهاء الوقت. نموذج الامتحان التالي للعرض فقط، ولن يؤثر على النتيجة.")
        render_readonly_trainee_exam_review(sid)
        curr_sett = get_print_settings()
        cert_html = generate_customizable_certificate_html(sid, curr_sett.get("default_cert_title"), curr_sett.get("default_cert_notes"))
        if int(result_row["passed"] or 0) == 1:
            render_print_button_only(cert_html, f"الشهادة المعتمدة {sid}")
        if st.button("العودة للرئيسية"):
            st.session_state.trainee_id = ""
            st.session_state.last_result_id = None
            st.rerun()
    else:
        trainee_portal()
elif not st.session_state.logged_in:
    login_portal()
else:
    admin_dashboard()
