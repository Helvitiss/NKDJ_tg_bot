## NKDJ Telegram Daily Survey Bot

Production-ready Telegram bot for daily team surveys with automatic scoring and admin reporting.

### Stack
- Python 3.12
- aiogram v3
- SQLAlchemy 2.0 (async)
- PostgreSQL
- APScheduler
- FSM (aiogram)
- Docker / docker-compose

### Quick start
1. Clone repository.
2. Create `.env` from example:
   ```bash
   cp .env.example .env
   ```
3. Fill required variables:
   - `BOT_TOKEN`
   - `ADMIN_ID`
   - `DATABASE_URL` (optional; default Compose DB is provided)
4. Run:
   ```bash
   docker compose up --build
   ```

Bot starts polling immediately after database is healthy and tables are created.

### Architecture
- `bot/handlers` — Telegram interaction only
- `bot/services` — business logic
- `bot/repositories` — database access
- `bot/domain` — scoring engine
- `bot/scheduler` — daily scheduling and overdue checks
- `bot/keyboards` — Telegram UI keyboards
- `bot/config` — pydantic settings

### Survey flow
Daily at 20:00 in each user's stored timezone:
1. Mood (🟢 / 🟡 / 🔴)
2. Campaigns count
3. GEO count
4. Creatives approaches count
5. Accounts count

After completion:
- User gets own results and final status.
- Admin gets raw answers + calculated colors + итог.

If user did not answer within 12 hours, admin receives reminder.

### Timezone
User sets timezone by command:
```bash
/timezone Europe/Moscow
```
Default timezone is `UTC`.
