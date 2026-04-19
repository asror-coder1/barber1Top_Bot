# Barber AI

Uzbekistan bozori uchun premium barber booking bot.

## Barber Panel

Yangi `barber panel` moduli alohida clean architecture qatlamida yaratildi:

- `app/barber_panel/domain` - enum va xatoliklar
- `app/barber_panel/infrastructure` - SQLAlchemy ORM modellari va repository
- `app/barber_panel/application` - service layer va DTO
- `app/barber_panel/presentation` - aiogram handler, FSM, middleware, premium keyboard/text UI
- `alembic/` - PostgreSQL migratsiyalari

Panel funksiyalari:

- booking management: `today`, `upcoming`, `pending`, `completed`, `cancelled`
- full barber profile management
- services CRUD
- pricing management va bulk update
- schedule management, vacation mode, unavailable/custom slots
- reviews + review replies
- analytics dashboard
- barber-client chat inbox

Reschedule flowda sana tugmalari `12-aprel` ko‘rinishida, vaqt slotlari esa 2 bo‘limga ajratilgan.

## Local setup

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`.env.example` dan `.env` yarating va kamida quyidagilarni to'ldiring:

- `TELEGRAM_BOT_TOKEN`
- `ADMIN_IDS`
- `BARBER_IDS`
- `BARBER_PANEL_ENABLED`
- `BARBER_PANEL_DATABASE_URL`
- `REDIS_URL`

Botni ishga tushirish:

```powershell
.\.venv\Scripts\python.exe main.py
```

Barber panelga kirish:

```text
/barber
```

## Docker

```powershell
docker compose up --build
```

Migratsiya uchun:

```powershell
alembic upgrade head
```

## Notes

- Legacy `app/database/repository.py` SQLite oqimi saqlab qolindi.
- Yangi barber panel PostgreSQL + SQLAlchemy + Alembic + Redis stack uchun scaffold qilingan.
- Production deploydan oldin `bp_barbers` jadvaliga barber profillarini seed qilish kerak.
