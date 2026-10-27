# Vizag Esportz UI relaunch

This update rebrands the public-facing site from an NSRIT-specific esports arena into **Vizag Esportz**, an independent city-wide gaming community.

## What changed
- Rebuilt the homepage around the provided Vizag Esportz brand direction: dark midnight surfaces, magenta/cyan neon accents, prominent brand mark, community-first messaging, feature cards, dynamic tournament cards, leaderboard preview and community CTA.
- Updated the shared navigation, footer, page metadata and Django admin branding.
- Added the supplied Vizag Esportz logo at `static/images/vizag-esportz-logo.png`.
- Kept the existing Django URL names, views, models, registration routes, tournament data, payment integrations and other application logic unchanged. Homepage tournament and leaderboard sections continue to use the existing view context.
- Responsive layouts are included for desktop, tablet and mobile widths.

## Important operational note
The backend account and tournament rules have intentionally not been changed as requested. Before publicly onboarding non-NSRIT players, review `accounts/forms.py`, `accounts/models.py` and account-related views to confirm whether existing account validation still requires NSRIT-specific identifiers or email domains. A visual rebrand alone does not make those backend rules city-wide.

## Verification
A Django system check could not be run in the editing environment because Django is not installed there (`ModuleNotFoundError: django`). Install the project's pinned dependencies and run:

```bash
python -m pip install -r requirements.txt
python manage.py check
python manage.py test
```

Also smoke-test login, registration, tournament detail/registration, team pages, leaderboard and Razorpay payment flow in a staging environment before deployment.
