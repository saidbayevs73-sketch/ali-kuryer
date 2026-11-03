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
