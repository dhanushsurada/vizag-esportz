#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# Render Build Script — Vizag Esportz
# ─────────────────────────────────────────────────────────────────
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# ── Ensure super admin account is provisioned
python manage.py create_admin

# ── Seed initial tournaments and headliners
python manage.py seed_data

# ── Unlock any unverified accounts
python manage.py shell -c "
from accounts.models import NSRITUser
updated = NSRITUser.objects.filter(email_verified=False).update(email_verified=True)
print(f'Unlocked {updated} unverified accounts')
"
