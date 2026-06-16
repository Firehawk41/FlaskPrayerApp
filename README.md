# Flask Prayer App

A social prayer tracking web application built with Flask and PostgreSQL.

## What It Does

Users log in to see a daily prayer feed — their own requests plus their friends' public prayers. Each prayer can be ticked off as prayed each day.

Key features:
- User authentication (register, login, logout)
- Create prayer requests as public or private, with 14 category tags
- Schedule prayers for specific days of the week
- Friends' public prayers appear in your feed
- Mark prayers as answered — the app then prompts daily gratitude reminders for a configurable number of days (default 7)
- Persistent history tracking per prayer per day
- Timezone-aware timestamps and per-user timezone settings

## Stack

- **Backend**: Python 3.11 / Flask 3.0
- **Database**: PostgreSQL (SQLite for local dev fallback)
- **ORM**: SQLAlchemy with Flask-Migrate (Alembic)
- **Auth**: Flask-Login with bcrypt password hashing
- **Forms**: Flask-WTF with CSRF protection
- **Server**: Gunicorn (production), Waitress (alternative)
- **Containerization**: Docker / Docker Compose

## Running Locally

### With Docker

1. Copy the example environment file and fill in your values:

```bash
cp .env.example .env
# Edit .env with your SECRET_KEY and POSTGRES_PASSWORD
```

2. Start the containers:

```bash
docker-compose up --build
```

App runs at `http://localhost:5000`

### Without Docker

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

export SECRET_KEY=your-secret-key
export DATABASE_URL=postgresql://user:password@localhost/prayerapp
# Or omit DATABASE_URL to use SQLite for local dev

flask db upgrade
flask run
```

## Deploying to Render

1. Create a new **Web Service** pointing to this repo.
2. Set the **Build Command**: `pip install -r requirements.txt`
3. Set the **Start Command**: `gunicorn app:app`
4. Add a **PostgreSQL** database from the Render dashboard.
5. Set the following environment variables in Render:
   - `SECRET_KEY` — a long random string (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `DATABASE_URL` — provided automatically by Render's PostgreSQL add-on
6. Run migrations on first deploy:
   ```bash
   flask db upgrade
   ```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Flask session signing key. Must be a long random string in production. |
| `DATABASE_URL` | Yes (production) | PostgreSQL connection string. Defaults to SQLite locally. |
| `GUNICORN_WORKERS` | No | Number of Gunicorn worker processes (default: 2). |
| `GUNICORN_THREADS` | No | Threads per worker (default: 4). |

## Security Notes

This project was built as a learning exercise. Known areas for improvement before treating this as a hardened production app:

- **Rate limiting**: Login and signup routes have no brute-force protection. Adding `Flask-Limiter` would fix this.
- **Password rules**: The minimum password length is currently set to 3 characters. Raise this to at least 8 for real users.
- **Password reset**: There is no "forgot password" flow. Users cannot recover compromised accounts.
- **Session cookies**: In production behind HTTPS, set `SESSION_COOKIE_SECURE = True` and `SESSION_COOKIE_HTTPONLY = True` in your Flask config.
- **CSRF**: Flask-WTF CSRF protection is enabled on all forms.
- **Passwords at rest**: bcrypt with salt — correct.
- **SQL injection**: SQLAlchemy ORM parameterized queries throughout — no raw SQL.

## Background

Built as a personal project to learn Flask, Docker, and cloud deployment. The answered-prayer gratitude feature was the core design motivation — shifting focus from requests to thankfulness over time.
