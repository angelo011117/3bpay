# 3B Smart Solutions Billing (Sprint 1)

Private maintenance-billing app. The UI and API are English-language; operational times are America/New_York and database timestamps are UTC. Vercel and Microsoft 365 are deliberately simulated/not connected.

## Start

1. In PowerShell: `Copy-Item .env.example .env` and replace the development values.
2. `docker compose up --build -d`
3. Apply migrations explicitly before using the app: `docker compose exec backend python manage.py migrate`.
4. Create an administrator: `docker compose exec backend python manage.py createsuperuser`
5. Load demo data (development only): `docker compose exec backend python manage.py load_demo`
6. Run immediately: `docker compose exec backend python manage.py run_scheduler`

Open `http://localhost` for the app, `http://localhost/admin/` for Django admin, and `http://localhost:8025` for Mailpit. Login is session/CSRF based; no tokens are stored in local storage.

## Demo flow

Load demo, run the scheduler, inspect Mailpit, copy the generated portal path from the email, then open **Payments to review** and confirm `DEMO-ZELLE-001`. The design stores payments separately from allocations and does not reduce balances until confirmation and allocation. The simulated provider records pause/resume actions only; it never contacts Vercel.

Use **Manage** to create clients, aliases, services and payments; client/service detail pages manage aliases, extensions and automation. Use **Settings** for the Zelle contact and an official AmEx QR (PNG/JPEG/WebP, maximum 2 MB). The portal only displays that uploaded image and never fabricates a QR.

### Development clock

In development only, open **Settings**, set the test timestamp, and run the scheduler. It applies to charge generation, grace and simulated actions. Reset returns to the real clock. The endpoint does not exist when `DJANGO_DEBUG=0`.

### Checks

Run backend checks with `docker compose exec backend python manage.py test billing`. Build independently with `docker compose run --rm frontend npm run build`. No command removes Docker volumes.

## Scheduler and safety

`run_scheduler` is safe to repeat: database constraints protect charges by service/period and transaction ID/account pairs. Grace ends after seven complete local days (a Nov 10 due charge may suspend from Nov 18 00:00 New York). Suspensions are blocked when an explicitly linked payment remains in review. Production requires a strong secret, TLS, allowed hosts, secure cookies, backups, real mail configuration, and a reviewed provider integration. There are no production default passwords.

## Sprint-2 items

Microsoft 365 ingestion, real Vercel calls, production delivery/retry policies, formal localization catalog, full CRUD panel/detail histories, official AmEx QR upload/configuration, and a controlled development clock command remain to be completed.
