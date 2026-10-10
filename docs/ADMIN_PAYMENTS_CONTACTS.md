# Admin settings, payment readiness, contacts, and customer registry

This is a **staged implementation**, not authorization to cut over live data or enable online payment.

## Admin access
After safe Postgres migration and verified staff bootstrap, set \`ENABLE_STAFF_WEB_PANELS=1\` on the FastAPI service. The separate URL \`/admin/settings\` is otherwise 404. Use the previously created admin telephone and password. All settings/customer endpoints verify an authenticated active \`admin\` role.

Admin may update:
- Contact phone, support email, office address, Telegram username link.
- Planned Click, Payme, bank card provider: public merchant label/ID, contract status, requested activation.
- Registered customer list and number; admin-only, max 100 rows per page.

The public read-only API \`GET /api/public/platform-config\` returns only contact information and safe payment availability flags. Users can see a disabled "Karta qo‘shish" placeholder in their signed-in profile. Online payments stay **off** even if admin marks a signed contract. Cash is the only implemented checkout option.

## Security
- No PAN, CVV, PIN, payment provider API secret or password is collected or saved in this feature. Providers must tokenize cards in their own PCI-compliant hosted flow; this has NOT been integrated yet.
- Any later Click/Payme/card enabling requires a bank contract, merchant verification, trusted server-to-server notifications (signature/auth checks), idempotent ledger updates, refunds/reconciliation, and testing.
- API secrets are stored as Render secret env vars, never in GitHub or admin settings.
- Settings writes and customer registry reads reject production SQLite. Do not change DB_URL or flip readiness flags before reconciling the legacy data.
- Current registration and Google sign-in write to \`users\` via SQLAlchemy. Database durability is not assured on Render without tested PostgreSQL connectivity. Anonymous site visitors are not customer accounts.
- Do not place an "all customers" directory on the public site; it is strictly admin-only.

## Safe rollout
1. Verify backup and restore of legacy SQLite and FastAPI local SQLite/support data.
2. Check PostgreSQL connectivity in private Render network and run isolated migrations.
3. Test newly created settings table and admin login, then test customer registration.
4. Test old and new data parity before applying a production cutover.
5. Only after confirmed safe conditions, opt in to private admin settings page.
6. Integrate bank PSPs separately. Do not treat a requested-enabled toggle as payment activation.
