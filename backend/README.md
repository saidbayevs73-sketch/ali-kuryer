# Ali Kuryer API

Node.js + Express + PostgreSQL backend foundation for the customer app, courier tools and admin panel.

## Local setup
1. Install Node.js 20+ and PostgreSQL.
2. Run `npm install`.
3. Create a database and apply `schema.sql`.
4. Set `DATABASE_URL` and optionally `DATABASE_SSL=false`.
5. Run `npm start`.

## Environment
- `PORT`: Render supplies this automatically.
- `DATABASE_URL`: PostgreSQL connection string (required for data endpoints).
- `DATABASE_SSL`: set to `false` only for local PostgreSQL.
- `ALLOWED_ORIGINS`: comma-separated allowed website origins.

## Endpoints
- `GET /health`: service status.
- `GET /api/v1/catalog`: active categories and products.
- `POST /api/v1/orders`: validate product IDs and prices on the server, then create a cash-on-delivery order.
- `GET /api/v1/orders/:code`: public order status.

## Deliberate launch gates
SMS OTP, customer sessions, admin RBAC, courier assignment and live GPS must be completed before production use. Admin data endpoints are intentionally disabled until authentication and role permissions are in place. Online payment and restaurant integrations are out of scope for this phase.


## Staff authentication (Firebase)

Customers continue to use Google sign-in on the customer site. Staff accounts are **not self-registered**:
- Admin signs in with Google.
- Only an email listed in `ADMIN_EMAILS` (comma-separated) can open the staff manager.
- Admin creates Firebase Email/Password accounts and assigns exactly one role: `courier` or `kitchen`.
- Firebase custom claims store the role and active state. The API verifies Firebase ID tokens and checks the role on every staff request.
- Admin can disable or re-enable staff accounts. Disabled accounts are rejected by Firebase token verification and the staff profile endpoint.

### Required Render environment variables

- `FIREBASE_SERVICE_ACCOUNT_JSON`: the full Firebase service-account JSON object, stored as a secret environment variable. Generate it in Firebase Console → Project settings → Service accounts. **Never commit this JSON file or paste it into chat.**
- `ADMIN_EMAILS`: the exact Google email address(es) allowed to administer staff accounts, separated by commas.
- `ALLOWED_ORIGINS`: the exact HTTPS website origin(s), comma-separated, for example the deployed customer-site origin.

The website must use the Firebase **Web app** configuration for `ali-kuryer-9d6bb` and the API base URL must point to the deployed backend. Do not use an Android app ID as the Web app ID. Configure these values in the hosting environment before testing.

### Endpoints

- `GET /api/v1/staff/me`: confirms that the signed-in user is an active courier or kitchen staff member.
- `GET /api/v1/admin/staff`: admin-only staff list.
- `POST /api/v1/admin/staff`: admin-only account creation; requires `email`, `password` (10+ characters), `displayName`, and `role` (`courier` or `kitchen`).
- `PATCH /api/v1/admin/staff/:uid`: admin-only account blocking/unblocking.

No staff registration endpoint is exposed. The staff login pages are `/courier.html` and `/kitchen.html`; the manager is `/admin.html`.
