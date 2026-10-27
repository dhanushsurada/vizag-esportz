# Vizag Esportz — Test & Local Run Report

**Date:** 27 Oct 2026 · **Environment:** Python 3.12, Django 4.2.11, SQLite (dev)

## What was run

- `pip install -r requirements.txt` (fresh virtualenv)
- `manage.py check` → **0 issues**
- `manage.py migrate` → all migrations apply cleanly
- `manage.py makemigrations --check` → models and migrations **in sync** (after fixes below)
- `manage.py test` → **0 tests found** (the project contains no test suite — see recommendations)
- Live server smoke tests (`smoke_test.sh`, `journey_test.sh`):
  - Public pages: home, login, register, password reset, tournaments, leaderboard, teams → all 200
  - Tournament detail pages (all 5 seeded) → 200 after fix below
  - Per-tournament matches: `/matches/<slug>/bracket|schedule|leaderboard|results` → 200
  - Registration → login → create player profile → dashboard → free-tournament registration → my-registrations → paid payment page → payment history → logout: **all pass**
  - Duplicate registration correctly blocked with "⚠️ You are already registered!" (1 row created)
  - Wrong password → "Invalid credentials. N attempt(s) remaining…"; account lockout logic intact
  - `collectstatic` → 127 files collected; logo and static assets serve correctly

## Issues found and fixed

### 1. Fresh installs crash: PostgreSQL-only migration (critical)
`tournaments/migrations/0003_registration_notes.py` used
`ALTER TABLE registrations ADD COLUMN IF NOT EXISTS notes …`, which SQLite rejects
(`OperationalError: near "EXISTS": syntax error`) and bypasses Django's schema machinery.
**Fixed:** replaced with a standard, database-agnostic `migrations.AddField`.

### 2. Models out of sync with migrations (critical on deploy)
`makemigrations --check` reported pending changes: removed `Registration.seed_number` /
`Registration.team` / `Tournament.updated_at`, new `unique_player_tournament` constraint,
altered fields in `accounts`, `matches`, `teams`. Any fresh deploy would have run with a
schema that didn't match the code.
**Fixed:** generated and applied 4 migrations
(`accounts/0004`, `matches/0003`, `teams/0003`, `tournaments/0004`).

### 3. Tournament detail page returned HTTP 500 (critical)
`templates/tournaments/detail.html` had `{% load static %}` *before*
`{% extends 'base.html' %}` → `TemplateSyntaxError: ExtendsNode must be the first tag`.
**Fixed:** reordered the tags. All 5 tournament pages now return 200.

### 4. `razorpay==1.4.1` breaks on modern Python environments (deploy blocker)
It imports `pkg_resources`, which was removed in setuptools ≥ 81 (current venvs ship
setuptools 84+).
**Fixed:** added `setuptools<81` to `requirements.txt`. (Longer-term: upgrade the
`razorpay` package, which no longer needs `pkg_resources`.)

### 5. Leftover "NSRIT eSports Arena" branding across ~30 templates (relaunch gap)
Page titles, login/register copy, email subjects, from-name, verification/password-reset
email bodies and footers still referenced NSRIT, `@nsrit.edu.in`, roll-number hints, etc.
**Fixed:** all templates and `accounts/utils.py` now say **Vizag Esportz**; email copy is
city-wide and email-domain-neutral.

### 6. UPI payment fallback pointed at the old VPA
`settings.UPI_ID` defaulted to `nsritesports@upi` and was undocumented in `.env.example`.
**Fixed:** default changed to `vizagesportz@upi` and `UPI_ID` added to `.env.example`
(set it to your real VPA before launch).

## Things you should still decide / do

1. **No automated tests exist.** `manage.py test` runs 0 tests. I left my scripts at
   `~/vizag-esportz/smoke_test.sh` and `~/vizag-esportz/journey_test.sh`, but proper
   Django unit tests for auth, registration and payment webhooks are strongly recommended.
2. **`seed_data` command is dangerous in production:** it creates a superuser
   `ADMIN001 / nsrit@admin2024` and NSRIT-branded demo tournaments. Never run it on a
   live database (the seeded demo tournaments still show "NSRIT" text — that's seed data,
   not templates).
3. **Razorpay flow untested end-to-end** (needs real test keys `RAZORPAY_KEY_ID/SECRET`
   in `.env`); the payment page and history render correctly.
4. **Email verification is intentionally disabled** (users are auto-verified on
   registration for launch) — re-enable before scale if spoofed signups are a concern.
5. The old `create_admin.py` management command hardcodes `25nu1a4436@nsrit.edu.in`.

## Fixed files

- `tournaments/migrations/0003_registration_notes.py`
- `tournaments/migrations/0004_…` (new), `accounts/migrations/0004_…` (new),
  `matches/migrations/0003_…` (new), `teams/migrations/0003_…` (new)
- `templates/tournaments/detail.html`
- All `templates/**` with branding + `accounts/utils.py`
- `requirements.txt`, `.env.example`, `nsrit_esports/settings.py` (UPI default)

## How to run locally

```bash
cd nsrit-esports-main
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver   # http://127.0.0.1:8000
```
