import flet as ft
import sqlite3
import urllib.parse
import json
import requests
import asyncio

# ==========================================
# 1. إعدادات الذكاء الاصطناعي وقاعدة البيانات
# ==========================================
# 🔑 مفتاح apifreellm الجديد
API_KEY = "apf_latf3gbtnq3h13gzw0mlom3z"

DB_NAME = "smart_health_luxury.db"

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, phone TEXT, condition TEXT, 
            test_type TEXT, ai_result TEXT
        )
    ''')
    conn.commit()
    return conn

# ==========================================
# 2. محرك الذكاء الاصطناعي (apifreellm)
# ==========================================
def analyze_condition_ai(condition_text):
    prompt = f"""
    أنت استشاري طبي خبير. حلل الحالة التالية: "{condition_text}"
    يجب أن يكون الرد بصيغة JSON حصراً وباللغة العربية كالتالي:
    {{
        "assessment": "تقييم مبدئي دقيق ومختصر",
        "risk_level": "منخفض أو متوسط أو مرتفع",
        "advice": "توجيه طبي احترافي ومباشر"
    }}
    """
    
    # 🌟 استخدام API الجديد apifreellm.com
    url = "https://apifreellm.com/api/v1/chat"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }
    payload = {
        "message": prompt
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get("success"):
            raw_text = response_data['response'].strip()
            # تنظيف الرد في حال أضاف النموذج علامات Markdown حول الـ JSON
            if raw_text.startswith("```json"):
                raw_text = raw_text.strip("`").replace("json\n", "", 1)
            elif raw_text.startswith("```"):
                raw_text = raw_text.strip("`")
            return json.loads(raw_text)
            
        elif response.status_code == 401:
            return {"error": True, "assessment": "مفتاح API غير صالح", "risk_level": "خطأ 401", "advice": "يرجى التحقق من صحة المفتاح المستخدم."}
        elif response.status_code == 429:
            return {"error": True, "assessment": "تم تجاوز حد الطلبات.", "risk_level": "خطأ 429", "advice": "الرجاء الانتظار 40 ثانية والمحاولة مرة أخرى."}
        elif response.status_code == 400:
            return {"error": True, "assessment": "طلب غير صالح.", "risk_level": "خطأ 400", "advice": "هناك مشكلة في البيانات المرسلة."}
        else:
            return {"error": True, "assessment": f"خطأ الخادم: {response.status_code}", "risk_level": "غير محدد", "advice": "حدث خطأ غير معروف."}
    except Exception as e:
        return {"error": True, "assessment": "تعذر الاتصال بالإنترنت أو قراءة الرد.", "risk_level": "غير محدد", "advice": str(e)}

# ==========================================
# 3. الواجهة الرئيسية والتطبيق
# ==========================================
def main(page: ft.Page):
    page.title = "Smart Clinic - Luxury Edition"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F8FAFC"
    page.rtl = True
    page.window.width = 480
    page.window.max_width = 500
    page.window.height = 850
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    db_conn = init_db()

    def format_phone_number(phone):
        safe_phone = phone.replace("+", "").replace(" ", "").strip()
        if len(safe_phone) == 9 and safe_phone.startswith("7"):
            safe_phone = f"967{safe_phone}"
        return safe_phone

    def premium_input(label, icon, is_multiline=False, is_phone=False):
        return ft.TextField(
            label=label, prefix_icon=icon, border_color=ft.Colors.TRANSPARENT,
            filled=True, bgcolor="#F1F5F9", border_radius=12, color="#0F172A",
            cursor_color="#1E3A8A", multiline=is_multiline, min_lines=3 if is_multiline else 1,
            keyboard_type=ft.KeyboardType.PHONE if is_phone else ft.KeyboardType.TEXT,
            content_padding=18 
        )

    btn_style = ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), padding=18)

    # 🌟 الدالة السحرية والمطابقة 100% لإصدار Flet 0.90 لفتح الروابط
    async def open_url(url_str):
        try:
            await ft.UrlLauncher().launch_url(url_str)
        except Exception as e:
            import webbrowser
            webbrowser.open(url_str)

    # ==========================================
    # الخانة 1: التحليل الذكي
    # ==========================================
    name_input = premium_input("اسم المريض", ft.Icons.PERSON)
    phone_input = premium_input("رقم الهاتف", ft.Icons.PHONE, is_phone=True)
    cond_input = premium_input("وصف الحالة / الأعراض", ft.Icons.MEDICAL_SERVICES, is_multiline=True)

    loading_dialog = ft.AlertDialog(
        modal=True, shape=ft.RoundedRectangleBorder(radius=20),
        content=ft.Container(padding=20, content=ft.Row([
            ft.ProgressRing(color="#1E3A8A", stroke_width=4),
            ft.Text("جاري تحليل الحالة...", weight="bold", size=16, color="#1E3A8A")
        ], spacing=20))
    )

    # ==========================================
    # الخانة 2: التقرير (الذكاء الاصطناعي)
    # ==========================================
    report_info = ft.Text(size=14, color="#334155", weight="w500")
    report_assessment = ft.Text(size=16, weight="bold", color="#1E3A8A")
    report_risk = ft.Container(padding=10, border_radius=20)
    report_risk_text = ft.Text(size=13, weight="bold", color=ft.Colors.WHITE)
    report_risk.content = report_risk_text
    report_advice = ft.Text(size=14, color="#475569", italic=True)

    # دوال الإرسال لقسم التقرير
    def on_report_wa_click(e):
        safe_phone = format_phone_number(phone_input.value)
        msg = f"مرحباً {name_input.value} 💙\nإليك تقريرك الطبي المبدئي:\n\n🧠 التقييم: {report_assessment.value}\n💡 نصيحة: {report_advice.value}\n\nنتمنى لك الشفاء العاجل."
        url = f"https://wa.me/{safe_phone}?text={urllib.parse.quote(msg)}"
        page.run_task(open_url, url)

    def on_report_sms_click(e):
        safe_phone = format_phone_number(phone_input.value)
        msg = f"مرحباً {name_input.value} 💙\nإليك تقريرك الطبي المبدئي:\n\n🧠 التقييم: {report_assessment.value}\n💡 نصيحة: {report_advice.value}\n\nنتمنى لك الشفاء العاجل."
        url = f"sms:{safe_phone}?body={urllib.parse.quote(msg)}"
        page.run_task(open_url, url)

    btn_wa_report = ft.Button(content=ft.Row([ft.Icon(ft.Icons.CHAT, color=ft.Colors.WHITE), ft.Text("WhatsApp", color=ft.Colors.WHITE, weight="bold")], alignment=ft.MainAxisAlignment.CENTER), bgcolor="#10B981", style=btn_style, expand=True, on_click=on_report_wa_click)
    btn_sms_report = ft.Button(content=ft.Row([ft.Icon(ft.Icons.SMS, color=ft.Colors.WHITE), ft.Text("SMS", color=ft.Colors.WHITE, weight="bold")], alignment=ft.MainAxisAlignment.CENTER), bgcolor="#3B82F6", style=btn_style, expand=True, on_click=on_report_sms_click)

    empty_report_msg = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.DOCUMENT_SCANNER, size=80, color="#CBD5E1"),
            ft.Text("لا يوجد تقرير حالياً", size=22, weight="bold", color="#94A3B8"),
            ft.Text("قم بإجراء فحص جديد لإصدار التقرير الطبي", color="#94A3B8", size=13)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
        alignment=ft.Alignment(0, 0), expand=True
    )

    report_content = ft.Container(
        visible=False, padding=25, bgcolor=ft.Colors.WHITE, border_radius=25,
        shadow=ft.BoxShadow(blur_radius=30, color="#E2E8F0", offset=ft.Offset(0, 10)),
        content=ft.Column([
            ft.Row([
                ft.Container(content=ft.Icon(ft.Icons.VERIFIED, color="#10B981", size=24), bgcolor="#D1FAE5", padding=8, border_radius=50),
                ft.Text("التقرير الطبي المدعوم بالذكاء الاصطناعي", size=16, weight="bold", color="#0F172A")
            ], spacing=10),
            ft.Divider(color="#F1F5F9", height=20, thickness=2),
            ft.Container(bgcolor="#F8FAFC", padding=15, border_radius=15, content=report_info, width=float('inf')),
            ft.Container(
                padding=10,
                content=ft.Column([
                    ft.Text("التشخيص المبدئي", size=12, color="#94A3B8", weight="bold"),
                    report_assessment,
                    ft.Row([ft.Text("مستوى الخطورة:", size=13, weight="bold", color="#64748B"), report_risk], spacing=10),
                    ft.Divider(color="#F1F5F9", height=10, thickness=1),
                    ft.Row([ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, color="#F59E0B", size=20), report_advice], expand=True)
                ], spacing=8)
            ),
            ft.Divider(color="#F1F5F9", height=20, thickness=2),
            ft.Text("مشاركة التقرير:", weight="bold", color="#64748B", size=13),
            ft.Row([btn_wa_report, btn_sms_report], spacing=15)
        ], spacing=10)
    )

    # ==========================================
    # الخانة 3: الإرسال اليدوي
    # ==========================================
    manual_name = premium_input("اسم المريض", ft.Icons.PERSON)
    manual_phone = premium_input("رقم الهاتف", ft.Icons.PHONE, is_phone=True)
    manual_test = premium_input("نوع الفحص", ft.Icons.BIOTECH)
    manual_result = premium_input("النتيجة", ft.Icons.FACT_CHECK, is_multiline=True)

    # دوال الإرسال لقسم الإرسال اليدوي
    def on_manual_wa_click(e):
        safe_phone = format_phone_number(manual_phone.value)
        msg = f"مرحباً {manual_name.value} 💙\nإليك نتيجة الفحص الخاص بك:\n\n🧪 نوع الفحص: {manual_test.value}\n📋 النتيجة: {manual_result.value}\n\nنتمنى لك دوام الصحة والعافية."
        url = f"https://wa.me/{safe_phone}?text={urllib.parse.quote(msg)}"
        page.run_task(open_url, url)

    def on_manual_sms_click(e):
        safe_phone = format_phone_number(manual_phone.value)
        msg = f"مرحباً {manual_name.value} 💙\nإليك نتيجة الفحص الخاص بك:\n\n🧪 نوع الفحص: {manual_test.value}\n📋 النتيجة: {manual_result.value}\n\nنتمنى لك دوام الصحة والعافية."
        url = f"sms:{safe_phone}?body={urllib.parse.quote(msg)}"
        page.run_task(open_url, url)

    btn_wa_manual = ft.Button(content=ft.Row([ft.Icon(ft.Icons.CHAT, color=ft.Colors.WHITE), ft.Text("إرسال WhatsApp", color=ft.Colors.WHITE, weight="bold")], alignment=ft.MainAxisAlignment.CENTER), bgcolor="#10B981", style=btn_style, expand=True, on_click=on_manual_wa_click)
    btn_sms_manual = ft.Button(content=ft.Row([ft.Icon(ft.Icons.SMS, color=ft.Colors.WHITE), ft.Text("إرسال SMS", color=ft.Colors.WHITE, weight="bold")], alignment=ft.MainAxisAlignment.CENTER), bgcolor="#3B82F6", style=btn_style, expand=True, on_click=on_manual_sms_click)

    # ==========================================
    # الخانة 4: الأرشيف
    # ==========================================
    archive_list = ft.ListView(expand=True, spacing=15)

    def update_archive():
        archive_list.controls.clear()
        cursor = db_conn.cursor()
        cursor.execute("SELECT name, condition, test_type, ai_result FROM patients ORDER BY id DESC LIMIT 20")
        for row in cursor.fetchall():
            res = json.loads(row[3]) if row[3] else {}
            archive_list.controls.append(
                ft.Container(
                    bgcolor=ft.Colors.WHITE, padding=20, border_radius=15,
                    shadow=ft.BoxShadow(blur_radius=15, color="#F1F5F9", offset=ft.Offset(0, 5)),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(content=ft.Text(row[0][0], color=ft.Colors.WHITE, weight="bold"), bgcolor="#1E3A8A", width=40, height=40, border_radius=20, alignment=ft.Alignment(0,0)),
                            ft.Text(row[0], weight="bold", size=16, color="#0F172A")
                        ], spacing=15),
                        ft.Text(f"الفحص: {row[2]} | الشكوى: {row[1]}", size=12, color="#64748B"),
                        ft.Text(f"النتيجة: {res.get('assessment', 'إرسال يدوي')}", size=13, weight="w600", color="#3B82F6"),
                    ], spacing=8)
                )
            )

    # ==========================================
    # دالة زر التحليل الذكي
    # ==========================================
    def show_toast(msg, is_error=False):
        color = "#EF4444" if is_error else "#10B981"
        page.snack_bar = ft.SnackBar(ft.Text(msg, color=ft.Colors.WHITE, weight="bold", text_align=ft.TextAlign.CENTER), bgcolor=color, shape=ft.RoundedRectangleBorder(radius=10), behavior=ft.SnackBarBehavior.FLOATING, margin=20)
        page.snack_bar.open = True
        page.update()

    def on_analyze_click(e):
        if not all([name_input.value, phone_input.value, cond_input.value]):
            show_toast("يرجى تعبئة جميع الحقول قبل التحليل!", True)
            return

        page.dialog = loading_dialog
        loading_dialog.open = True
        page.update()

        ai_res = analyze_condition_ai(cond_input.value)
        
        loading_dialog.open = False
        page.update()

        if ai_res.get("error"):
            show_toast(ai_res.get("advice", "حدث خطأ في الاتصال، راجع التقرير."), True)
            report_risk.bgcolor = "#EF4444"
            report_risk_text.value = "مرفوض"
        else:
            show_toast("تم استخراج التقرير الذكي بنجاح!")
            risk = ai_res.get("risk_level", "")
            
            if "منخفض" in risk:
                report_risk.bgcolor = "#10B981" 
                report_risk_text.value = "آمن"
            elif "متوسط" in risk:
                report_risk.bgcolor = "#F59E0B" 
                report_risk_text.value = "يحتاج انتباه"
            else:
                report_risk.bgcolor = "#EF4444" 
                report_risk_text.value = "حرج"

            cursor = db_conn.cursor()
            cursor.execute(
                "INSERT INTO patients (name, phone, condition, test_type, ai_result) VALUES (?, ?, ?, ?, ?)",
                (name_input.value, phone_input.value, cond_input.value, "تحليل ذكي", json.dumps(ai_res))
            )
            db_conn.commit()
            update_archive()
        
        report_info.value = f"المريض: {name_input.value}\nالهاتف: {phone_input.value}\nالشكوى: {cond_input.value}"
        report_assessment.value = f"{ai_res.get('assessment')}"
        report_advice.value = f"{ai_res.get('advice')}"

        empty_report_msg.visible = False
        report_content.visible = True
        
        page.navigation_bar.selected_index = 1
        switch_view(1)

    # ==========================================
    # إعداد الحاويات الرئيسية والهيدر 
    # ==========================================
    app_header = ft.Container(
        gradient=ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1), colors=["#1E3A8A", "#0284C7"]),
        padding=25, border_radius=30, shadow=ft.BoxShadow(blur_radius=20, color="#BAE6FD", offset=ft.Offset(0, 10)),
        content=ft.Row([
            ft.Container(content=ft.Icon(ft.Icons.MEDICAL_SERVICES, size=35, color="#1E3A8A"), bgcolor=ft.Colors.WHITE, padding=12, border_radius=20),
            ft.Column([
                ft.Text("Smart Clinic", size=24, weight="900", color=ft.Colors.WHITE),
                ft.Text("Powered by AI", size=12, color="#E0F2FE", italic=True)
            ], spacing=0)
        ], spacing=15)
    )

    luxury_analyze_btn = ft.Container(
        content=ft.Row([ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.WHITE), ft.Text("تحليل الحالة بالذكاء الاصطناعي", size=16, weight="bold", color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.CENTER),
        gradient=ft.LinearGradient(begin=ft.Alignment(-1, 0), end=ft.Alignment(1, 0), colors=["#1E3A8A", "#3B82F6"]),
        padding=18, border_radius=15, ink=True, on_click=on_analyze_click, shadow=ft.BoxShadow(blur_radius=15, color="#93C5FD", offset=ft.Offset(0, 8))
    )

    view_analysis = ft.Container(
        padding=25,
        content=ft.Column([
            ft.Text("تحليل حالة المريض", size=18, weight="800", color="#0F172A"),
            name_input, phone_input, cond_input,
            ft.Divider(color=ft.Colors.TRANSPARENT, height=10),
            luxury_analyze_btn
        ], spacing=15)
    )

    view_report = ft.Container(padding=25, content=ft.Column([empty_report_msg, report_content], expand=True))
    
    view_manual_send = ft.Container(
        padding=25,
        content=ft.Column([
            ft.Text("إرسال نتيجة فحص (يدوي)", size=18, weight="800", color="#0F172A"),
            manual_name, manual_phone, manual_test, manual_result,
            ft.Divider(color=ft.Colors.TRANSPARENT, height=10),
            ft.Row([btn_wa_manual, btn_sms_manual], spacing=15)
        ], spacing=15)
    )

    view_archive = ft.Container(padding=25, content=ft.Column([ft.Text("أرشيف الحالات", size=18, weight="800", color="#0F172A"), archive_list], expand=True))

    main_content = ft.Column([view_analysis], expand=True)

    def switch_view(index):
        main_content.controls.clear()
        if index == 0: main_content.controls.append(view_analysis)
        elif index == 1: main_content.controls.append(view_report)
        elif index == 2: main_content.controls.append(view_manual_send)
        elif index == 3: main_content.controls.append(view_archive)
        page.update()

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.AUTO_AWESOME_OUTLINED, selected_icon=ft.Icons.AUTO_AWESOME, label="التحليل"),
            ft.NavigationBarDestination(icon=ft.Icons.DOCUMENT_SCANNER_OUTLINED, selected_icon=ft.Icons.DOCUMENT_SCANNER, label="التقرير"),
            ft.NavigationBarDestination(icon=ft.Icons.SEND_OUTLINED, selected_icon=ft.Icons.SEND, label="إرسال يدوي"),
            ft.NavigationBarDestination(icon=ft.Icons.ARCHIVE_OUTLINED, selected_icon=ft.Icons.ARCHIVE, label="الأرشيف"),
        ],
        selected_index=0, bgcolor=ft.Colors.WHITE, indicator_color="#DBEAFE",
        on_change=lambda e: switch_view(e.control.selected_index)
    )

    update_archive()
    page.add(ft.Column([app_header, main_content], expand=True, spacing=0))

if __name__ == "__main__":
    ft.run(main)
