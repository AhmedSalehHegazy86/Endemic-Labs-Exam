def render_print_button_only(html_content, label_prefix=""):
    print_sett = get_print_settings()
    m_top = "12mm"
    m_right = "8mm"
    m_left = "8mm"
    
    repeated_print_css = f"""
    <style>
    @page {{
        size: A4 portrait;
        margin: {m_top} {m_right} 16mm {m_left} !important;
    }}
    @media print {{
        html, body {{
            margin: 0 !important;
            padding: 0 !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}
        @page {{
            @bottom-center {{
                content: "صفحة " counter(page) " من " counter(pages);
            }}
        }}
        body {{
            counter-reset: page;
        }}
        .print-footer-dynamic {{
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            right: 0 !important;
            width: 100% !important;
            background: #ffffff !important;
            border-top: 2px solid #059669;
            padding: 4px 4px !important;
            font-family: 'Cairo', Tahoma, sans-serif;
            font-size: 10pt;
            font-weight: 900;
            color: #065f46;
            box-sizing: border-box;
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}
        /* في الصفحة الأخيرة، يتحرك التذييل ليتبع نهاية المتن مباشرة */
        .print-footer-container {{
            display: block;
            page-break-inside: avoid;
        }}
        .report-wrapper {{
            margin-bottom: 0 !important;
            padding-bottom: 15mm !important;
        }}
        .print-footer-dynamic:last-of-type {{
            position: relative !important;
            bottom: auto !important;
            margin-top: 10px !important;
            page-break-inside: avoid !important;
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
        width: 100% !important;
        background: #ffffff !important;
        border-top: 2px solid #059669;
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
    
    footer_bar_html = f"""
    <div class="print-footer-container">
        <div class="print-footer-dynamic">
            <div class="print-footer-top-row">
                <div style="text-align: center; width: 100%;">جميع الحقوق محفوظة © 2026 | تطوير Dr/Ahmed.S.Hegazy</div>
                <div class="page-number-box" style="position: absolute; left: 4px;"></div>
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
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        orient_key = f"orient_{hash(label_prefix) & 0xffffffff}"
        chosen_orient = st.selectbox("اتجاه الورق للطباعة (مقاس A4):", ["رأسي (Portrait)", "أفقي (Landscape)"], key=orient_key)
    with col_opt2:
        copies_key = f"copies_{hash(label_prefix) & 0xffffffff}"
        num_pages_to_print = st.number_input("عدد الأوراق / النسخ المطلوبة:", min_value=1, max_value=50, value=1, key=copies_key)

    js_code = """
    <div style="margin: 4px 0;">
        <button onclick="printDoc()" style="width: 100%; background-color: #059669; color: white; padding: 8px 12px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-family: 'Cairo', sans-serif; font-size: 13pt;">
            🖨 طباعة / حفظ المستند (A4 """ + chosen_orient + """ - """ + label_prefix + """)
        </button>
    </div>
    <script>
    function printDoc() {
        var win = window.open('', '_blank');
        var styledHtml = """ + encoded_html + """;
        win.document.write(styledHtml);
        win.document.close();
        win.focus();
        setTimeout(function(){
            win.print();
        }, 600);
    }
    </script>
    """
    components.html(js_code, height=100)
