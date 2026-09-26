import streamlit as st
import time

# إعدادات الصفحة
st.set_page_config(page_title="اختبار أونلاين بمؤقت", page_icon="📝", layout="centered")

# بيانات الأسئلة والإجابات
quiz_data = [
    {
        "question": "ما هي عاصمة جمهورية مصر العربية؟",
        "options": ["الإسكندرية", "القاهرة", "الجيزة", "الأقصر"],
        "correct": "القاهرة"
    },
    {
        "question": "أي من اللغات التالية تُستخدم للذكاء الاصطناعي وعلوم البيانات بشكل واسع؟",
        "options": ["HTML", "Python", "CSS", "C++"],
        "correct": "Python"
    },
    {
        "question": "كم عدد كواكب المجموعة الشمسية؟",
        "options": ["7", "8", "9", "10"],
        "correct": "8"
    }
]

# مدة الاختبار بالثواني (مثلاً 3 دقائق = 180 ثانية)
EXAM_DURATION = 180

# تهيئة متغيرات الجلسة (Session State)
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}

st.title("📝 نظام الاختبارات الإلكترونية")

# شاشة البداية
if st.session_state.start_time is None:
    student_name = st.text_input("أدخل اسمك بالكامل للبدء:")
    if st.button("بدء الاختبار الآن 🚀"):
        if student_name.strip() == "":
            st.warning("يرجى إدخال الاسم أولاً.")
        else:
            st.session_state.student_name = student_name
            st.session_state.start_time = time.time()
            st.rerun()

# شاشة الاختبار والنتائج
else:
    # حساب الوقت المتبقي
    elapsed_time = int(time.time() - st.session_state.start_time)
    remaining_time = EXAM_DURATION - elapsed_time

    # التحقق من انتهاء الوقت
    if remaining_time <= 0 and not st.session_state.submitted:
        st.session_state.submitted = True
        st.error("⏰ انتهى الوقت المحدد للاختبار!")

    # عرض المؤقت والاسم إذا لم يتم التسليم بعد
    if not st.session_state.submitted:
        mins, secs = divmod(remaining_time, 60)
        st.info(f"👤 الطالب: **{st.session_state.student_name}** | ⏳ الوقت المتبقي: **{mins:02d}:{secs:02d}**")

        st.divider()

        # عرض الأسئلة
        with st.form("quiz_form"):
            for idx, q in enumerate(quiz_data):
                st.subheader(f"س{idx + 1}: {q['question']}")
                st.session_state.user_answers[idx] = st.radio(
                    "اختر الإجابة الصحيحة:",
                    q["options"],
                    key=f"q_{idx}",
                    index=None
                )
                st.write("---")

            submit_btn = st.form_submit_button("تسليم الاختبار ✅")
            if submit_btn:
                st.session_state.submitted = True
                st.rerun()

    # شاشة النتيجة النهائية
    if st.session_state.submitted:
        st.success("تم إكمال الاختبار بنجاح!")
        
        # حساب الدرجة
        score = 0
        for idx, q in enumerate(quiz_data):
            if st.session_state.user_answers.get(idx) == q["correct"]:
                score += 1

        total = len(quiz_data)
        percentage = (score / total) * 100

        st.metric(label="النتيجة النهائية", value=f"{score} / {total}", delta=f"{percentage:.1f}%")

        if percentage >= 50:
            st.balloons()
            st.success("🎉 مبروك! لقد اجتزت الاختبار.")
        else:
            st.error("❌ لم تتجاوز الاختبار، حاول مرة أخرى!")

        if st.button("إعادة الاختبار 🔄"):
            st.session_state.start_time = None
            st.session_state.submitted = False
            st.session_state.user_answers = {}
            st.rerun()