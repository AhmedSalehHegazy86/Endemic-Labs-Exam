import base64
import os
import requests

# ============================================================
# GitHub Auto Sync
# Endemic Labs Exam
# ============================================================

GITHUB_OWNER = "AhmedSalehHegazy86"
GITHUB_REPO = "Endemic-Labs-Exam"
BRANCH = "main"

# ضع GitHub Personal Access Token في متغير البيئة:
# Windows:
# set GITHUB_TOKEN=xxxxxxxx
#
# Linux / Streamlit / Mac:
# export GITHUB_TOKEN=xxxxxxxx

TOKEN = os.getenv("GITHUB_TOKEN")

if not TOKEN:
    raise SystemExit(
        "\n❌ لم يتم العثور على GITHUB_TOKEN.\n"
        "أنشئ GitHub Personal Access Token وضعه في متغير البيئة.\n"
    )

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

BASE_URL = (
    f"https://api.github.com/repos/"
    f"{GITHUB_OWNER}/{GITHUB_REPO}/contents"
)

# ============================================================
# الملفات التي سيتم استبدالها
# ============================================================

FILES = {
    "app_professional_v2_2_FINAL.py": "app.py",
    "requirements_professional_v2_2_FINAL.txt": "requirements.txt",
    "README_v2_2_FINAL.md": "README.md",
}

# ملفات قد تكون مطلوبة للتطبيق ولا يتم حذفها
KEEP_FILES = {
    "logo.jpg",
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
}

# ملفات لا نريد رفعها إلى GitHub
FORBIDDEN_FILES = {
    "endemic_labs_exam_v2_2.db",
    "endemic_labs_exam.db",
    ".env",
}


def github_get(path):
    url = f"{BASE_URL}/{path}"
    response = requests.get(
        url,
        headers=HEADERS,
        params={"ref": BRANCH},
        timeout=30,
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


def replace_file(local_file, github_file):
    if not os.path.exists(local_file):
        raise FileNotFoundError(
            f"الملف غير موجود: {local_file}"
        )

    if github_file in FORBIDDEN_FILES:
        raise RuntimeError(
            f"تم منع رفع الملف الحساس: {github_file}"
        )

    with open(local_file, "rb") as f:
        content = f.read()

    encoded = base64.b64encode(content).decode("utf-8")

    existing = github_get(github_file)

    payload = {
        "message": f"Auto replace {github_file} with Professional v2.2 FINAL",
        "content": encoded,
        "branch": BRANCH,
    }

    if existing:
        payload["sha"] = existing["sha"]

    url = f"{BASE_URL}/{github_file}"

    response = requests.put(
        url,
        headers=HEADERS,
        json=payload,
        timeout=60,
    )

    if not response.ok:
        print("\n❌ فشل تحديث:", github_file)
        print(response.text)
        response.raise_for_status()

    result = response.json()

    print(
        f"✅ تم استبدال {github_file}"
        f" | Commit: {result['commit']['sha'][:8]}"
    )


def main():

    print("=" * 60)
    print(" Endemic Labs Exam - GitHub Auto Sync")
    print("=" * 60)

    print(f"\nRepository: {GITHUB_OWNER}/{GITHUB_REPO}")
    print(f"Branch: {BRANCH}\n")

    # --------------------------------------------------------
    # تحديث الملفات الرئيسية
    # --------------------------------------------------------

    for local_file, github_file in FILES.items():

        replace_file(
            local_file,
            github_file
        )

    print("\n" + "=" * 60)
    print("✅ اكتملت عملية الاستبدال تلقائيًا")
    print("=" * 60)

    print("\nالملفات النهائية:")
    print("  ✓ app.py")
    print("  ✓ requirements.txt")
    print("  ✓ README.md")

    print("\nقاعدة البيانات:")
    print("  ✓ لن يتم رفع قاعدة البيانات إلى GitHub")

    print("\nجاهز للتشغيل على Streamlit Cloud.")


if __name__ == "__main__":
    main()