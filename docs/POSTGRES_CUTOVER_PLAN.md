# Ali Kuryer — xavfsiz PostgreSQL o'tish rejasi

## Hozirgi holat (2026-10-10)

- `ali-kuryer-1`: eski Telegram bot, oshxona/admin/kuryer panellari, SQLite.
- **Render persistent disk**: `/var/data`. Eski xizmatda
  `DB_PATH=/var/data/ali_kuryer.db` va `DATA_DIR=/var/data` sozlanmoqda.
- `ali-kuryer`: FastAPI, Android mijoz API, alohida SQLite (hozircha).
- `ali-kuryer-postgres`: yangi PostgreSQL 17 bazasi (Oregon), **hali ulanmagan**.
- Ikkala serverdagi jadvallar bir-biridan farq qiladi. Faqat `DATABASE_URL`
  almashtirish eski oshxona, kuryer va buyurtmalarni birlashtirmaydi.

## Qat'iy qoidalar

1. **Do not delete** the legacy service, disk, SQLite file or its backups.
2. Do not publish, commit or log PostgreSQL passwords or connection URLs.
3. Back up legacy SQLite using the sqlite3 online backup API; verify integrity.
4. Inspect **all** legacy tables and compare counts before/after mapping.
5. Existing legacy staff accounts use different password hashing mechanisms.
   Never reinterpret old password hashes as bcrypt or silently activate accounts.
   Re-provision staff identities with a verified password reset.
6. Do not direct live checkout to PostgreSQL until all participating client,
   restaurant, courier and admin systems use the same canonical order store.
7. Test actual restaurant acceptance, courier claiming, support chat, GPS
   tracking and cancellation against an isolated, non-production test order.
8. Switch public website and mobile clients only after reconciled tests and
   independent confirmation. Keep rollback path.

## Preparatory automation

The script `scripts/migrate_legacy_to_postgres.py` has a safe dry-run mode.
It creates a verified SQLite snapshot **on the server**, prints only aggregate
counts, and never alters PostgreSQL without explicit `--apply` confirmation
and a verified old-server maintenance freeze. Production data cannot be read
from the GitHub Actions runner; migration must execute where the legacy
persistent disk is mounted and the private PostgreSQL connection is available.

The legacy handler supports opt-in maintenance freeze via
`ALI_LEGACY_WRITES_FROZEN=1`; **do not set it yet**. Its write-freeze
implementation also guards direct sqlite write attempts.

`app/routers/commerce.py` requires
`ALI_COMMERCE_CUTOVER_ENABLED=1` in production before new order/checkouts can
be accepted; **do not enable it yet**.

## Safe execution checklist (operator with approved Render access)

- Verify `ALI_LEGACY_MIGRATION_READINESS` Render logs:
  `storage_persistent: true` and `backup_verified: true`.
- Confirm real production SQLite counts and save an integrity-verified backup.
- Connect new FastAPI service's **secret** `DATABASE_URL` to the new managed
  PostgreSQL database without exposing credentials; verify connectivity.
- Arrange a short maintenance window for legacy writes and freeze them.
- Run the migration in *dry-run*; verify source tables and every foreign key.
- Run `--apply` once against a fresh empty PostgreSQL target. Do not rerun
  automatically; it refuses non-empty target core tables.
- Reconcile entity, item, order and delivery-detail counts, and legacy
  image assets separately (the migration does not copy image files).
- Migrate or rebuild legacy web staff panels onto the canonical PostgreSQL
  APIs; initialize authorized staff credentials via secure reset.
- Run E2E live flow in an isolated environment; activate cutover gate only
  after passing all tests.
- Keep source backup + old service until rollback window closes.

## Current blocker

Render's linked tools expose service metadata, deployments, logging and
environment **updates**, but do not provide a read/write shell, existing
environment **secret reads**, or an authenticated cross-database data copy.
Do not guess a PostgreSQL connection URL or export private data through a
public endpoint. Complete the secret linkage/verified migration with an
authorized Render cloud browser / shell in ChatGPT Work, or with an operator
following this playbook.
