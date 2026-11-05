# Ali Kuryer API

Node.js 20+, Express and PostgreSQL backend for the customer website and courier API.

## Local setup

1. Install Node.js 20+ and PostgreSQL.
2. Run `npm install`.
3. Apply the complete `schema.sql` to the target database.
4. Configure the environment variables below.
5. Run `npm start`.

## Required environment

- `PORT`: Render supplies this automatically.
- `DATABASE_URL`: PostgreSQL connection string.
- `DATABASE_SSL`: use `false` only for local PostgreSQL.
- `ALLOWED_ORIGINS`: comma-separated exact website origins.
- `FIREBASE_SERVICE_ACCOUNT_JSON`: Firebase Admin service-account JSON as a secret environment variable. Never commit this value or a service-account file.
- `ADMIN_EMAILS`: comma-separated admin email allow-list for the courier-link/dispatch endpoints.

The Firebase web configuration in the customer website is not a substitute for the Admin SDK service account. Do not put the service-account private key in website code, Android resources, or GitHub source files.

## Current API

- `GET /health`: API and database status.
- `GET /api/v1/catalog`: active categories and available products.
- `POST /api/v1/orders`: validates product IDs and prices on the server and creates a cash-on-delivery order.
- `GET /api/v1/orders/:code`: public order status lookup.
- `POST /api/v1/admin/couriers/link`: links a Firebase UID to a courier record; requires a verified admin token.
- `POST /api/v1/courier/orders/:id/accept`: accepts an existing, unexpired dispatch offer; requires a courier token.
- `POST /api/v1/courier/orders/:id/decline`: declines an existing, unexpired dispatch offer.
- `GET /api/v1/courier/orders/mine`: lists assigned/in-progress orders for the authenticated courier.
- `PATCH /api/v1/courier/orders/:id/status`: advances an assigned order through pickup, en-route and delivered states.
- `POST /api/v1/courier/presence`: records courier online state and GPS coordinates.

## Important integration status

The Firebase Admin SDK initialization and courier router mounting are present in this working branch. The schema now includes courier identity links, dispatch-offer storage and courier presence storage.

This is not a production-ready launch. The current branch still needs an authenticated admin order-dispatch workflow that creates courier offers, full admin order-management endpoints, a kitchen/staff application and role rules, customer session ownership for private order history, end-to-end live tracking, and device/server integration tests. The existing website admin and courier pages are demo pages and are not converted into secure operational dashboards by these API changes.

Before deployment, set the environment secrets in the hosting provider, apply the schema migration to a backup-protected database, verify Firebase token claims/roles, and run end-to-end tests. Do not use real customer data until these gates pass.
