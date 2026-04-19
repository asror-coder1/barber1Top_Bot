from __future__ import annotations

BOOK_APPOINTMENT = "✂️ Navbat olish"
CHOOSE_BARBER = "👨‍🦱 Usta tanlash"
FREE_SLOTS = "🕒 Bo'sh vaqtlar"
PRICES = "💈 Narxlar"
AI_RECOMMENDATION = "🤖 AI style tavsiya"
BONUSES = "🎁 Bonuslar"
LOCATION = "📍 Lokatsiya"
REVIEW = "⭐ Sharh qoldirish"
BECOME_BARBER = "💼 Sartarosh bo'lish"

FACE_SHAPES = [
    "Oval",
    "Dumaloq",
    "To'rtburchak",
    "Yuraksimon",
    "Uzunchoq",
]

HAIR_LENGTHS = [
    "Qisqa",
    "O'rtacha",
    "Uzun",
]

STYLE_GOALS = [
    "Clean va office",
    "Zamonaviy va trend",
    "Premium va elegant",
    "Minimal parvarish",
    "Creative va ajralib turadigan",
]

MAINTENANCE_LEVELS = [
    "Past",
    "O'rta",
    "Yuqori",
]

BEARD_STYLES = [
    "Toza qirilgan",
    "Qisqa stubble",
    "To'liq soqol",
]

BUSINESS_HOURS = {
    "start_hour": 9,
    "end_hour": 21,
    "slot_step_minutes": 60,
}

DEFAULT_BARBERS = [
    {
        "name": "Azizbek",
        "specialty": "Fade, skin fade, premium beard styling",
        "experience_years": 7,
    },
    {
        "name": "Jasur",
        "specialty": "Classic cuts, student cuts, quick clean-ups",
        "experience_years": 5,
    },
    {
        "name": "Sardor",
        "specialty": "Textured crop, modern mullet, creative styling",
        "experience_years": 6,
    },
]

DEFAULT_SERVICES = [
    {
        "name": "Classic haircut",
        "description": "Toza va professional klassik soch olish",
        "duration_minutes": 60,
        "price": 70000,
    },
    {
        "name": "Skin fade",
        "description": "Aniq o'tishlar va zamonaviy fade uslubi",
        "duration_minutes": 60,
        "price": 90000,
    },
    {
        "name": "Haircut + beard",
        "description": "Soch olish va soqolni forma berish",
        "duration_minutes": 90,
        "price": 120000,
    },
    {
        "name": "VIP styling",
        "description": "Konsultatsiya, styling va premium xizmat",
        "duration_minutes": 90,
        "price": 150000,
    },
]
