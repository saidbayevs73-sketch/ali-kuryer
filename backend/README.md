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
- `GET /api/v1/orders/:code`: basic public order status lookup.\n- `GET /api/v1/orders/:code/tracking?phone=...`: customer tracking; requires the phone number on the order and returns status history plus courier GPS when assigned.
- `GET /api/v1/admin/orders`: admin order board with items and courier assignment.\n- `POST /api/v1/admin/orders/:id/dispatch`: offers a ready order to a recently-online courier.\n- `POST /api/v1/admin/couriers/link`: links a Firebase UID to a courier record; requires a verified admin token.\n- `GET /api/v1/kitchen/orders`: kitchen queue for new/accepted/preparing orders.\n- `PATCH /api/v1/kitchen/orders/:id/status`: kitchen moves orders through accepted, preparing and ready.
- `POST /api/v1/courier/orders/:id/accept`: accepts an existing, unexpired dispatch offer; requires a courier token.
- `POST /api/v1/courier/orders/:id/decline`: declines an existing, unexpired dispatch offer.
- `GET /api/v1/courier/orders/mine`: lists assigned/in-progress orders for the authenticated courier.
- `PATCH /api/v1/courier/orders/:id/status`: advances an assigned order through pickup, en-route and delivered states.
- `POST /api/v1/courier/presence`: records courier online state and GPS coordinates.

## Important integration status

The Firebase Admin SDK initialization, courier router and operations router are present in this working branch. The schema includes courier identity links, dispatch offers, courier presence and a shared status history that records kitchen actions. Customer tracking checks both order code and the phone number attached to the order. The clients must refresh these endpoints periodically (for example every 3–5 seconds) until a push/realtime transport is added.

This is not a production-ready launch. The current branch still needs the admin, kitchen and courier interfaces to be connected to these routes, Firebase custom claims for kitchen/courier/admin accounts, customer Google-session ownership for private order history, end-to-end live tracking on devices, and device/server integration tests. Courier GPS updates are stored through the courier presence endpoint; the courier app must send fresh coordinates while on an active delivery. The existing website admin and courier pages are demo pages and are not converted into secure operational dashboards by these API changes.

Before deployment, set the environment secrets in the hosting provider, apply the schema migration to a backup-protected database, verify Firebase token claims/roles, and run end-to-end tests. Do not use real customer data until these gates pass.
