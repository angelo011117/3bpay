# 3B Smart Solutions Billing (Sprint 1)

Private maintenance-billing app. The UI and API are English-language; operational times are America/New_York and database timestamps are UTC. Vercel and Microsoft 365 are deliberately simulated/not connected.

## Delivery and provider safety

`EMAIL_DELIVERY_MODE=mailpit` is the default and sends only to Mailpit. `graph_test` requires an HTTPS `PUBLIC_BASE_URL`, `MICROSOFT_GRAPH_SENDER`, and a comma-separated `MICROSOFT_GRAPH_TEST_RECIPIENTS` allowlist; every recipient must be in that list. `graph_live` is deliberately not selected automatically. Graph acceptance only means that Microsoft Graph accepted the request, not that a recipient has delivered/read it. Assign `Application Mail.Send` through Exchange Application RBAC scoped to the sender mailbox; setting a sender address alone does not scope an application permission.

Vercel remains `VERCEL_ENABLED=false` and `VERCEL_MODE=simulation`. Before any live action, set an explicit project ID on one service and validate it against a non-client test project. Do not use client projects for the first pause/resume test.

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

## Microsoft 365 / Microsoft Graph (Sprint 2)

Graph is disabled by default. Copy the `MICROSOFT_GRAPH_*` names in `.env.example` to `.env`, fill them locally, then restart only the services that read them: `docker compose up -d --force-recreate backend scheduler`.

Register an Entra application using **application** (not delegated) authentication and grant `Mail.Read` application permission, followed by tenant-wide admin consent. Use client credentials with the `.default` scope; the backend obtains a token for each synchronization and never exposes it to the UI or logs it. `MICROSOFT_GRAPH_MAILBOX` chooses the Graph target but does **not** restrict the application permission. In Exchange Online, create and assign an Application Access Policy (or the current Exchange Application RBAC equivalent) that scopes the Entra application to a mail-enabled security group containing only the authorized mailbox; test the policy with Exchange Online PowerShell before enabling production sync.

The scheduler uses Graph delta sync, stores its cursor and imports every Graph message identity at most once. Imported messages remain in manual review. If Graph is disabled or incomplete, the app starts normally and makes no Graph requests. A real connection is not validated until credentials are supplied and a successful sync is recorded.

## Scheduler and safety

`run_scheduler` is safe to repeat: database constraints protect charges by service/period and transaction ID/account pairs. Grace ends after seven complete local days (a Nov 10 due charge may suspend from Nov 18 00:00 New York). Suspensions are blocked when an explicitly linked payment remains in review. Production requires a strong secret, TLS, allowed hosts, secure cookies, backups, real mail configuration, and a reviewed provider integration. There are no production default passwords.

## Sprint-2 items

Microsoft 365 ingestion, real Vercel calls, production delivery/retry policies, formal localization catalog, full CRUD panel/detail histories, official AmEx QR upload/configuration, and a controlled development clock command remain to be completed.
