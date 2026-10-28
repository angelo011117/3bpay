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

## Ubuntu production deployment

Production uses [docker-compose.production.yml](docker-compose.production.yml), which is deliberately separate from the Windows development stack. It creates only the `3bpay` project, `3bpay_app_net` network and `3bpay_*` volumes. PostgreSQL, backend and frontend have no published ports. The only published listener is the 3BPay proxy on `127.0.0.1:${THREEBPAY_PROXY_PORT}`; it never uses host ports 80 or 443, so Apache and existing Docker applications are untouched. Mailpit is not part of this Compose file.

### 1. Server inventory

Run the following on Ubuntu before selecting the proxy port or changing Cloudflare. It is read-only and does not print environment variables:

```bash
sudo bash /opt/3bpay/deploy/server-inventory.sh
```

Review listening ports, Apache virtual hosts, Docker names/networks, available capacity, the `cloudflared` installation/service, and usable directories. Pick an unused loopback port (the example uses `18080`) only after this output confirms it is free. Do not run `docker compose down -v`, `docker system prune`, or alter Apache while deploying 3BPay.

### 2. Files and secrets

On the server, clone/copy this repository into `/opt/3bpay`, then create the production environment file locally with restrictive permissions:

```bash
cd /opt/3bpay
cp deploy/production.env.example .env.production
chmod 600 .env.production
chmod 700 deploy
```

Fill only `.env.production`; it is ignored by Git. Set strong unique PostgreSQL and Django secrets, `DJANGO_DEBUG=0`, `PUBLIC_BASE_URL=https://pay.3bsmartsolution.com`, and the port confirmed by inventory. Initial safe values are intentional:

```dotenv
EMAIL_DELIVERY_MODE=disabled
MICROSOFT_GRAPH_ENABLED=false
VERCEL_ENABLED=false
VERCEL_MODE=simulation
```

`EMAIL_DELIVERY_MODE=disabled` is a real no-delivery mode: the scheduler preserves pending outbox rows without creating attempts, marking messages as sent, or retrying them. It must be used instead of `mailpit` on a server where Mailpit is absent.

### 3. Data migration from Docker Desktop

Stop the Windows scheduler first, leaving the application stack otherwise intact. Do not run another Graph reader or sender on Windows after the final backup. Create a consistent database dump and copy uploaded media (including the QR) from Windows:

```powershell
docker compose exec db sh -c 'pg_dump -U threebpay -Fc threebpay > /tmp/3bpay.dump'
docker compose cp db:/tmp/3bpay.dump .\3bpay.dump
docker compose exec db rm /tmp/3bpay.dump
docker compose cp backend:/app/media .\3bpay-media
```

Transfer the dump, `3bpay-media` directory, and the production `.env.production` over an encrypted channel such as `scp`; never commit any of them. On Ubuntu, start only PostgreSQL, restore the dump, and restore media before starting the application:

```bash
cd /opt/3bpay
docker compose --env-file .env.production -f docker-compose.production.yml up -d db
docker compose --env-file .env.production -f docker-compose.production.yml exec -T db \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists < /secure-transfer/3bpay.dump
docker compose --env-file .env.production -f docker-compose.production.yml run --rm backend python manage.py migrate --noinput
docker compose --env-file .env.production -f docker-compose.production.yml run --rm backend python manage.py collectstatic --noinput
docker compose --env-file .env.production -f docker-compose.production.yml up -d backend
docker compose --env-file .env.production -f docker-compose.production.yml cp /secure-transfer/3bpay-media/. backend:/app/media/
```

The `$POSTGRES_*` variables in the shell command must be loaded from the protected environment file first (`set -a; . ./.env.production; set +a`) or entered as their non-secret database/user names. Do **not** run `load_demo` in production. Before cutover, review demo candidates rather than deleting anything automatically: `Acme Demo LLC`, `acme.example`, `avery@example.test`, and transaction ID `DEMO-ZELLE-001` are created only by the development loader.

Verify preservation without printing payment details:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml exec db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 'clients',count(*) FROM billing_client UNION ALL SELECT 'services',count(*) FROM billing_service UNION ALL SELECT 'charges',count(*) FROM billing_charge UNION ALL SELECT 'payments',count(*) FROM billing_payment UNION ALL SELECT 'allocations',count(*) FROM billing_paymentallocation;"
docker compose --env-file .env.production -f docker-compose.production.yml exec backend sh -c 'find /app/media -type f | wc -l'
```

### 4. Start and tunnel cutover

Build and start the web stack; the scheduler is in an explicit profile and remains stopped:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
docker compose --env-file .env.production -f docker-compose.production.yml ps
curl -fsS http://127.0.0.1:18080/healthz
```

Check login/session/CSRF locally through the loopback proxy and a known secure portal URL, then configure Cloudflare only after the inventory establishes how `cloudflared` is run:

- If `cloudflared` is a host systemd service, set the `pay.3bsmartsolution.com` ingress service to `http://127.0.0.1:18080`.
- If it runs in a container, `127.0.0.1` means that container, not the Ubuntu host. Attach that connector to `3bpay_app_net` and use `http://proxy:80`, or use the host gateway explicitly after confirming its configuration.

Keep the Windows ingress untouched until external `https://pay.3bsmartsolution.com/login` and a portal URL return successfully from the Ubuntu route. At cutover, ensure exactly one connector/rule can serve this hostname; two connectors pointing to different databases are not an acceptable failover method. Revert by restoring the prior Cloudflare service target to Windows, then decide how to preserve records created on Ubuntu before allowing Windows to write again.

After HTTPS verification, start scheduler processing only with the safe values above:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml --profile scheduler up -d scheduler
docker compose --env-file .env.production -f docker-compose.production.yml logs --tail=100 scheduler
```

It may read Graph only after `MICROSOFT_GRAPH_ENABLED=true` is deliberately configured; no Graph live sending or Vercel live action is enabled by this deployment procedure.

### 5. Backups, restore checks, updates and rollback

The backup script creates a PostgreSQL custom-format dump plus media archive, SHA-256 checksums, and configurable retention. Example daily cron (run as the deploy user):

```cron
15 2 * * * BACKUP_RETENTION_DAYS=14 /opt/3bpay/deploy/backup.sh >> /opt/3bpay/backups/backup.log 2>&1
```

Test every backup in an isolated disposable PostgreSQL container; it does not touch the production database or volumes:

```bash
/opt/3bpay/deploy/verify-restore-isolated.sh /opt/3bpay/backups/20260101T020000Z
```

For updates, backup first, pull/copy the reviewed release, then build, migrate explicitly and recreate only this project:

```bash
./deploy/backup.sh
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
docker compose --env-file .env.production -f docker-compose.production.yml run --rm backend python manage.py migrate --noinput
docker compose --env-file .env.production -f docker-compose.production.yml run --rm backend python manage.py collectstatic --noinput
```

Rollback code or routing only after taking a final backup. If any new payments, Graph messages, portal claims, or outbox rows arrived after cutover, do not point Windows at its old database: export/reconcile those records first or keep the Ubuntu database authoritative. Verify Susy Soirées and Cesar Brothers with their existing health URLs/Apache virtual-host routes before and after the change; 3BPay commands never stop Apache or other Compose projects.
