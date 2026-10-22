from __future__ import annotations

from typing import Annotated, Optional
from livekit.agents import llm
from db_driver import DatabaseDriver


class AssistantFnc(llm.FunctionContext):
    """Function context exposing Receptionist tools to the Multimodal Agent.
    All outputs and descriptions support strict Arabic voice interactions.
    """

    def __init__(self, db: Optional[DatabaseDriver] = None):
        super().__init__()
        self.db = db or DatabaseDriver()

    @llm.ai_callable(description="تسجيل ملاحظة أو رسالة من المتصل للأطباء أو الإدارة في عيادة الأسنان. (Take and record a note or message from a caller)")
    async def take_note(
        self,
        caller_name: Annotated[str, llm.TypeInfo(description="اسم المريض أو المتصل صاحب الرسالة")],
        content: Annotated[str, llm.TypeInfo(description="محتوى الملاحظة أو تفاصيل الرسالة والاستفسار")],
        phone_number: Annotated[str, llm.TypeInfo(description="رقم هاتف المتصل للتواصل معه لاحقاً")] = "",
        category: Annotated[str, llm.TypeInfo(description="تصنيف الرسالة مثل: استفسار، طارئ، إعادة اتصال، رسالة للطبيب")] = "عام",
        is_urgent: Annotated[bool, llm.TypeInfo(description="هل الرسالة تتطلب اهتماماً عاجلاً")] = False,
    ) -> str:
        """Records a note in the receptionist system."""
        print(f"\n[AGENT ACTION] Taking note from: {caller_name} (Phone: {phone_number})")
        result = self.db.add_note(
            caller_name=caller_name,
            content=content,
            phone_number=phone_number,
            category=category,
            is_urgent=is_urgent,
        )
        print(f"[AGENT RESULT] Note #{result['note_id']} recorded successfully.\n")
        return f"تم تسجيل الملاحظة بنجاح للمتصل {caller_name}. رقم الملاحظة: #{result['note_id']}."

    @llm.ai_callable(description="حجز وتأكيد موعد كشف أو استشارة في عيادة الأسنان وتقويم الأسنان. استدعاء هذه الأداة إلزامي أثناء المكالمة لتأكيد الحجز. (Schedule an appointment in calendar and database)")
    async def schedule_appointment(
        self,
        client_name: Annotated[str, llm.TypeInfo(description="اسم المريض بالكامل لحجز الموعد")],
        start_time: Annotated[str, llm.TypeInfo(description="تاريخ ووقت بدء الموعد بصيغة ISO القياسية (مثال: 2026-10-18T12:00:00)")],
        end_time: Annotated[str, llm.TypeInfo(description="تاريخ ووقت انتهاء الموعد بصيغة ISO القياسية (مثال: 2026-10-18T13:00:00)")],
        title: Annotated[str, llm.TypeInfo(description="عنوان أو سبب الموعد (مثال: كشف أسنان، استشارة تقويم، حشو عصب)")] = "كشف أسنان",
        description: Annotated[str, llm.TypeInfo(description="تفاصيل إضافية أو ملاحظات عن حالة المريض")] = "",
        client_email: Annotated[str, llm.TypeInfo(description="البريد الإلكتروني للمريض (اختياري، يمكن تركه فارغاً تماماً)")] = "",
        client_phone: Annotated[str, llm.TypeInfo(description="رقم هاتف المريض للتواصل والتأكيد")] = "",
    ) -> str:
        """Schedules a new appointment."""
        print(f"\n[AGENT ACTION] Executing schedule_appointment: {client_name} ({start_time} to {end_time}) | Phone: {client_phone} | Email: {client_email}")
        res = self.db.schedule_appointment(
            client_name=client_name,
            start_time=start_time,
            end_time=end_time,
            title=title,
            description=description,
            client_email=client_email,
            client_phone=client_phone,
        )
        print(f"[AGENT RESULT] Appointment #{res['appointment_id']} created. Sync status: {res['calendar_sync_status']}\n")
        return (
            f"تم تأكيد حجز الموعد بنجاح للمريض {client_name} في عيادة نوفا لطب الأسنان "
            f"بتاريخ {start_time} إلى {end_time}. رقم الموعد: #{res['appointment_id']}."
        )

    @llm.ai_callable(description="الاستعلام والتحقق من المواعيد المتاحة أو القادمة في جدول العيادة. (List or check upcoming appointments)")
    async def check_appointments(
        self,
        date_filter: Annotated[str, llm.TypeInfo(description="تاريخ محدد للاستعلام عنه بصيغة YYYY-MM-DD (مثال: 2026-10-18) أو تركه فارغاً")] = "",
        limit: Annotated[int, llm.TypeInfo(description="الحد الأقصى لعدد المواعيد المسترجعة")] = 5,
    ) -> str:
        """Checks appointments on schedule."""
        print(f"\n[AGENT ACTION] Checking appointments (Filter: '{date_filter}', Limit: {limit})")
        appointments = self.db.list_appointments(limit=limit, date_filter=date_filter or None)
        if not appointments:
            print("[AGENT RESULT] No appointments found for filter.\n")
            return "لا توجد مواعيد أخرى مسجلة في هذا التوقيت، والجدول متاح لاستقبال المريض."

        summary_lines = []
        for app in appointments:
            summary_lines.append(
                f"- موعد #{app['id']}: {app['title']} للمريض {app['client_name']} من {app['start_time']} إلى {app['end_time']}"
            )
        print(f"[AGENT RESULT] Found {len(appointments)} appointment(s).\n")
        return "المواعيد المحجوزة حالياً:\n" + "\n".join(summary_lines)

    @llm.ai_callable(description="إلغاء موعد كشف مسجل مسبقاً باستخدام رقم الموعد. (Cancel an existing appointment by ID)")
    async def cancel_appointment(
        self,
        appointment_id: Annotated[int, llm.TypeInfo(description="رقم الموعد المراد إلغاؤه (Appointment ID)")],
    ) -> str:
        """Cancels an appointment."""
        print(f"\n[AGENT ACTION] Cancelling appointment #{appointment_id}")
        res = self.db.cancel_appointment(appointment_id)
        print(f"[AGENT RESULT] {res['message']}\n")
        return f"تم إلغاء الموعد رقم #{appointment_id} بنجاح."

    @llm.ai_callable(description="البحث في دليل أطباء العيادة وتخصصاتهم ومواعيد تواجدهم. (Search clinic doctors and staff directory)")
    async def search_directory(
        self,
        query: Annotated[str, llm.TypeInfo(description="اسم الطبيب أو التخصص المراد البحث عنه مثل: زراعة، تقويم، أطفال، عصب، حشو")] = "",
    ) -> str:
        """Finds staff or department information in the directory."""
        print(f"\n[AGENT ACTION] Searching directory for: '{query}'")
        results = self.db.search_directory(query)
        if not results:
            print("[AGENT RESULT] No directory entries found.\n")
            return f"لم يتم العثور على أطباء أو تخصصات تطابق '{query}'. يمكنك حجز موعد كشف عام مع طبيب الأسنان المناوب."

        entries = []
        for r in results:
            entries.append(
                f"- {r['name']} ({r['role']} - قسم {r['department']}) | هاتف: {r['phone']} | أوقات التواجد: {r['notes']}"
            )
        print(f"[AGENT RESULT] Found {len(results)} directory match(es).\n")
        return "أطباء العيادة المتاحون:\n" + "\n".join(entries)

    @llm.ai_callable(description="تسجيل ملخص المكالمة الهاتفية عند الانتهاء. هذه الأداة للأرشفة فقط ولا تقوم بحجز المواعيد. (Log the summary of the call)")
    async def log_call(
        self,
        caller_name: Annotated[str, llm.TypeInfo(description="اسم المريض أو المتصل")],
        summary: Annotated[str, llm.TypeInfo(description="ملخص سريع باللغة العربية لما دار في المكالمة وما تم الاتفاق عليه")],
        action_items: Annotated[str, llm.TypeInfo(description="أي إجراءات متابعة مطلوبة (مثال: تأكيد الموعد عبر واتساب، تجهيز ملف الأشعة)")] = "",
        phone_number: Annotated[str, llm.TypeInfo(description="رقم هاتف المتصل")] = "",
    ) -> str:
        """Logs the call summary."""
        print(f"\n[AGENT ACTION] Logging call for {caller_name}: {summary} | Actions: {action_items}")
        res = self.db.log_call(
            caller_name=caller_name,
            phone_number=phone_number,
            summary=summary,
            action_items=action_items,
        )
        print(f"[AGENT RESULT] Call log #{res['call_log_id']} saved.\n")
        return f"تم حفظ وتوثيق ملخص المكالمة رقم #{res['call_log_id']} بنجاح للمتصل {caller_name}."