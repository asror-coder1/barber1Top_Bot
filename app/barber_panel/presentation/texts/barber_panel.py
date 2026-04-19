from __future__ import annotations

from app.barber_panel.application.dtos import (
    AnalyticsView,
    BookingCard,
    DashboardMetrics,
    ProfileView,
    ReviewSummary,
    ScheduleView,
)


def format_money(value: int) -> str:
    return f"{value:,} so'm".replace(",", " ")


def dashboard_text(metrics: DashboardMetrics) -> str:
    return (
        "<b>Barber AI • Barber Panel</b>\n"
        "Premium dark + clean workflow\n\n"
        f"📅 Bugungi bronlar: <b>{metrics.today_bookings}</b>\n"
        f"⏳ Kutilayotgan so'rovlar: <b>{metrics.pending_requests}</b>\n"
        f"💰 Oylik tushum: <b>{format_money(metrics.monthly_revenue)}</b>\n"
        f"⭐ Reyting: <b>{metrics.average_rating:.1f}</b>\n"
        f"💬 O'qilmagan chatlar: <b>{metrics.unread_chats}</b>\n\n"
        "Kerakli bo'limni pastdagi dashboard kartalaridan tanlang."
    )


def booking_card_text(card: BookingCard) -> str:
    status_map = {
        "pending": "Kutilmoqda",
        "accepted": "Tasdiqlangan",
        "completed": "Yakunlangan",
        "cancelled": "Bekor qilingan",
    }
    return (
        f"<b>#{card.booking_id} • {card.client_name}</b>\n"
        f"✂️ Xizmat: {card.service_name}\n"
        f"📅 Sana: {card.date_label}\n"
        f"🕒 Vaqt: {card.time_label}\n"
        f"📞 Telefon: {card.phone_number}\n"
        f"📌 Status: {status_map.get(card.status, card.status)}"
    )


def profile_text(profile: ProfileView) -> str:
    return (
        "<b>👤 Barber Profile</b>\n\n"
        f"Ism: <b>{profile.full_name}</b>\n"
        f"Salon: {profile.salon_name}\n"
        f"Telefon: {profile.phone_number}\n"
        f"Manzil: {profile.address}\n"
        f"Tajriba: {profile.experience}\n"
        f"Bio: {profile.about_me or '-'}\n"
        f"Portfolio: {len(profile.portfolio_images)} ta rasm"
    )


def services_text(services: list) -> str:
    if not services:
        return "<b>✂️ Xizmatlar</b>\n\nHozircha xizmatlar kiritilmagan."
    parts = ["<b>✂️ Xizmatlar</b>"]
    for service in services:
        state = "aktiv" if service.is_active else "arxiv"
        parts.append(
            f"\n<b>{service.name}</b>\n"
            f"{service.description or '-'}\n"
            f"⏱ {service.duration_minutes} daqiqa • 💰 {format_money(service.price)} • {state}"
        )
    return "\n".join(parts)


def pricing_text(services: list) -> str:
    if not services:
        return "<b>💰 Narxlar</b>\n\nNarxlar hali sozlanmagan."
    lines = ["<b>💰 Narxlar boshqaruvi</b>"]
    for service in services:
        lines.append(f"{service.name}: <b>{format_money(service.price)}</b>")
    lines.append("\nBulk update orqali barcha narxlarni bir marta yangilashingiz mumkin.")
    return "\n".join(lines)


def schedule_text(schedule: ScheduleView) -> str:
    weekdays = ["Du", "Se", "Cho", "Pay", "Ju", "Sha", "Yak"]
    active_days = ", ".join(weekdays[index] for index in schedule.working_days) or "yo'q"
    break_text = (
        f"{schedule.break_start} - {schedule.break_end}"
        if schedule.break_start and schedule.break_end
        else "yo'q"
    )
    vacation_text = "yoqilgan" if schedule.vacation_mode else "o'chirilgan"
    return (
        "<b>🕒 Ish jadvali</b>\n\n"
        f"Ish kunlari: {active_days}\n"
        f"Soat: {schedule.start_time} - {schedule.end_time}\n"
        f"Tanaffus: {break_text}\n"
        f"Vacation mode: {vacation_text}\n"
        f"Band sanalar: {len(schedule.unavailable_dates)}\n"
        f"Open slotlar: {len(schedule.custom_open_slots)}\n"
        f"Closed slotlar: {len(schedule.custom_closed_slots)}"
    )


def reviews_text(summary: ReviewSummary) -> str:
    lines = [
        "<b>⭐ Sharhlar</b>",
        f"O'rtacha reyting: <b>{summary.average_rating:.1f}</b>",
        f"Jami sharhlar: <b>{summary.total_reviews}</b>",
        f"Tasdiqlangan sharhlar: <b>{summary.verified_reviews}</b>",
    ]
    for review in summary.reviews[:5]:
        verified = "✅" if review.is_verified else "▫️"
        reply = f"\n↩️ {review.reply_text}" if review.reply_text else ""
        lines.append(
            f"\n{verified} <b>{review.client_name}</b> • {review.rating}/5 • {review.created_at_label}\n"
            f"{review.comment or '-'}{reply}"
        )
    return "\n".join(lines)


def analytics_text(stats: AnalyticsView) -> str:
    return (
        "<b>📈 Statistika</b>\n\n"
        f"Bugungi bronlar: <b>{stats.today_bookings}</b>\n"
        f"Haftalik bronlar: <b>{stats.weekly_bookings}</b>\n"
        f"Oylik bronlar: <b>{stats.monthly_bookings}</b>\n"
        f"Oylik revenue: <b>{format_money(stats.monthly_revenue)}</b>\n"
        f"Jami mijozlar: <b>{stats.total_customers}</b>\n"
        f"O'rtacha reyting: <b>{stats.average_rating:.1f}</b>\n"
        f"Qaytgan mijozlar: <b>{stats.repeat_customers}</b>"
    )


def chat_inbox_text(threads: list) -> str:
    if not threads:
        return "<b>💬 Chat inbox</b>\n\nHozircha xabarlar yo'q."
    lines = ["<b>💬 Chat inbox</b>"]
    for thread in threads:
        badge = f" • {thread.unread_count} unread" if thread.unread_count else ""
        booking = f" • Bron {thread.booking_reference}" if thread.booking_reference else ""
        premium = " • booking chat" if thread.booking_related else ""
        lines.append(f"{thread.client_name}{badge}{booking}{premium}\n{thread.preview}")
    return "\n\n".join(lines)


def chat_thread_text(thread, messages: list[str]) -> str:
    history = "\n".join(messages) if messages else "Suhbat hali bo'sh."
    booking = f"\nBron: {thread.booking_reference}" if thread.booking_reference else ""
    return f"<b>💬 {thread.client_name}</b>{booking}\n\n{history}"


def settings_text(notifications_enabled: bool, theme: str) -> str:
    return (
        "<b>⚙️ Sozlamalar</b>\n\n"
        f"Bildirishnomalar: {'yoqilgan' if notifications_enabled else 'o‘chirilgan'}\n"
        f"Tema: {theme}\n"
        "Mini App uslubi: rounded buttons, clean cards"
    )
