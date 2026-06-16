# FlaskPrayerApp — Claude Context

## Project Overview

Social prayer tracking web app. Users see a daily feed of their own prayers and friends' public prayers, tick them off each day, and get gratitude reminders after marking a prayer answered.

Single-file Flask app (`app.py`, ~700 lines). No blueprints. Models, forms, and routes all in one file.

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | Everything: models, WTForms, routes, Flask-Login config |
| `templates/` | Jinja2 HTML templates |
| `static/js/prayerActions.js` | AJAX handlers for prayer checkbox interactions |
| `static/css/styles.css` | Styling |
| `requirements.txt` | Python dependencies |
| `gunicorn_config.py` | Gunicorn worker/thread settings |
| `docker-compose.yml` | Local dev orchestration (web + db services) |
| `instance/` | SQLite DB for local dev; SQL dumps — **not committed in production** |

## Data Models (app.py)

- **User**: email (unique), firstname, lastname, password (bcrypt bytes), timezone, thankfulness_length
- **Prayer**: user_id, title, description, tag_id, answered, answered_at, archived, created_at, sharable, day booleans (mon–sun)
- **Tag**: 14 predefined categories (Thanksgiving, Lament, Praise, etc.)
- **PrayerHistory**: prayer_id, user_id, date_prayed — one row per prayer-per-day
- **FriendRequest**: sender_id, receiver_id, status (Pending/Accepted/Declined)

## Auth

Flask-Login with bcrypt. `@login_required` on all protected routes. No password reset flow exists. No email verification. Minimum password length is 3 (should be raised to 8+).

## Known Issues / Technical Debt

### Security (address before treating as production-hardened)

1. **No rate limiting** on `/login` or `/signup` — brute-force possible. Fix: add `Flask-Limiter`.
2. **Weak password minimum** — 3 characters (`app.py:57`). Raise to 8+.
3. **Password change is broken** — `account_settings` form has password fields but the route never applies them (`app.py:427-459`). Users cannot change passwords.
4. **No session cookie hardening** — should set `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True` in production config.
5. **`SECRET_KEY` not validated** — if env var missing, Flask uses `None` and sessions are unsigned. Add a startup assertion or fallback error.
6. **Forwarded IPs trust `'*'`** in `gunicorn_config.py` — should restrict to your proxy's IP in a real deployment.

### Bugs

7. **Dead code in `update_account`** (`app.py:465-467`): `if request.method == ['POST']:` compares to a list — always False. Route just redirects; nothing executes.
8. **Email uniqueness not checked on account update** — DB has a UNIQUE constraint but there's no app-level error message if a duplicate email is submitted.

### Deployment / Config

9. **Port mismatch** — `gunicorn_config.py` binds to `8080`, Dockerfile exposes `5000`. On Render this is resolved by Render's routing, but worth cleaning up for clarity.
10. **No `.gitignore`** — `.env`, `*.pem`, `*.log`, and `instance/` should all be excluded. The existing `app.log` and historical `.env` / PEM files should not be in version control.
11. **Database migrations** — Flask-Migrate is installed but no `migrations/` folder is tracked. Schema is managed via manual SQL dumps in `instance/`. Should set up a proper Alembic migrations directory.
12. **`instance/updated_database.sql`** contains real email addresses (PII). Do not commit this file.

### Code Quality

13. Magic number for default gratitude period — `7` appears hardcoded in the home route logic alongside the user's `thankfulness_length` setting. Worth consolidating.
14. Prayer categories are defined in two places (model seed data + form choices). A single constant would remove the duplication.

## Development Workflow

```bash
# Install deps
pip install -r requirements.txt

# Set required env vars
export SECRET_KEY=dev-secret-key
export DATABASE_URL=postgresql://...   # or omit for SQLite

# Run migrations
flask db upgrade

# Start dev server
flask run
```

For Docker:
```bash
docker-compose up --build
```

## Render Deployment Checklist

- [ ] `SECRET_KEY` env var set (long random string)
- [ ] `DATABASE_URL` env var set (from Render PostgreSQL add-on)
- [ ] `flask db upgrade` run on first deploy (or as a release command)
- [ ] Start command: `gunicorn app:app`
- [ ] `SESSION_COOKIE_SECURE = True` added to Flask config (HTTPS enforced by Render)
- [ ] No `.env` or PEM files in the repo

## What Works Well

- CSRF protection on all forms (Flask-WTF)
- bcrypt password hashing with salt
- SQLAlchemy ORM throughout — no raw SQL, no injection risk
- Timezone-aware timestamps via pytz
- Comprehensive logging
- `@login_required` + ownership checks before any mutation
