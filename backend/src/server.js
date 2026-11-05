import express from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import pg from "pg";
import { z } from "zod";
import { randomBytes } from "node:crypto";
import { getFirebaseAdminAuth } from "./firebase-admin.js";
import { createStaffRouter } from "./staff-routes.js";
import { createKitchenRouter } from "./kitchen-routes.js";
import { createCourierRouter } from "./courier-routes.js";
import { createOrderCommunicationRouter } from "./order-communication-routes.js";
import { createSupportReviewRouter } from "./support-review-routes.js";
import { startDispatchWorker } from "./dispatch-worker.js";

const { Pool } = pg;
const app = express();
const port = Number(process.env.PORT || 10000);
const pool = process.env.DATABASE_URL ? new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_SSL === "false" ? false : { rejectUnauthorized: false },
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000
}) : null;

app.disable("x-powered-by");
app.use(helmet());
app.use(cors({ origin: (process.env.ALLOWED_ORIGINS || "").split(",").filter(Boolean).length
  ? (process.env.ALLOWED_ORIGINS || "").split(",").map(x => x.trim())
  : true }));
app.use(express.json({ limit: "32kb" }));
app.use("/api", rateLimit({ windowMs: 60_000, limit: 120, standardHeaders: "draft-7", legacyHeaders: false }));
app.use("/api/v1", createStaffRouter());
app.use("/api/v1", createKitchenRouter(pool));
app.use("/api/v1", createCourierRouter(pool));
app.use("/api/v1", createOrderCommunicationRouter(pool));
app.use("/api/v1", createSupportReviewRouter(pool));

const asyncRoute = fn => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
const requireDb = (req, res, next) => {
  if (!pool) return res.status(503).json({ error: "database_not_configured", message: "Server bazasi hali ulanmagan." });
  next();
};

app.get("/health", asyncRoute(async (req, res) => {
  if (!pool) return res.status(503).json({ ok: false, service: "ali-kuryer-api", database: "not_configured" });
  try {
    await pool.query("SELECT 1");
    return res.json({ ok: true, service: "ali-kuryer-api", database: "connected" });
  } catch (error) {
    console.error("Database health check failed:", error.message);
    return res.status(503).json({ ok: false, service: "ali-kuryer-api", database: "connection_failed" });
  }
}));
app.get("/api/v1/catalog", requireDb, asyncRoute(async (req, res) => {
  const { rows } = await pool.query(`
    SELECT c.id AS category_id, c.name AS category_name, c.slug,
           p.id, p.name, p.description, p.price_uzs, p.image_url
    FROM categories c LEFT JOIN products p ON p.category_id=c.id AND p.available=true
    WHERE c.active=true ORDER BY c.sort_order, p.name
  `);
  const grouped = new Map();
  for (const row of rows) {
    if (!grouped.has(row.category_id)) grouped.set(row.category_id, { id: row.category_id, name: row.category_name, slug: row.slug, products: [] });
    if (row.id) grouped.get(row.category_id).products.push({ id: row.id, name: row.name, description: row.description, price: Number(row.price_uzs), imageUrl: row.image_url });
  }
  res.json({ categories: [...grouped.values()] });
}));

async function requireCustomer(req, res, next) {
  try {
    const auth = getFirebaseAdminAuth();
    if (!auth) return res.status(503).json({ error: "firebase_admin_not_configured" });
    const token = (req.headers.authorization || "").startsWith("Bearer ") ? req.headers.authorization.slice(7) : "";
    if (!token) return res.status(401).json({ error: "google_login_required", message: "Buyurtma berish uchun Google hisobingizga kiring." });
    const decoded = await auth.verifyIdToken(token, true);
    if (!decoded.uid || !decoded.email || decoded.firebase?.sign_in_provider !== "google") return res.status(403).json({ error: "verified_google_account_required", message: "Faqat Google hisobi orqali kirish mumkin." });
    req.customerAuth = decoded;
    next();
  } catch { return res.status(401).json({ error: "invalid_token", message: "Google hisobingizga qayta kiring." }); }
}

const orderSchema = z.object({
  customerName: z.string().trim().min(2).max(100),
  customerPhone: z.string().trim().regex(/^\+?[0-9 ()-]{9,20}$/),
  address: z.string().trim().min(5).max(500),
  latitude: z.number().min(-90).max(90).optional(),
  longitude: z.number().min(-180).max(180).optional(),
  landmark: z.string().max(200).optional(),
  notes: z.string().max(500).optional(),
  deliveryFee: z.number().int().min(0).max(100000).default(0),
  items: z.array(z.object({ productId: z.string().uuid(), quantity: z.number().int().min(1).max(50) })).min(1).max(40),
  paymentMethod: z.literal("cash").default("cash")
});

app.post("/api/v1/orders", requireDb, requireCustomer, asyncRoute(async (req, res) => {
  const parsed = orderSchema.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ error: "invalid_order", details: parsed.error.flatten() });
  const input = parsed.data;
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const { rows: existingCustomers } = await client.query("SELECT id,firebase_uid FROM customers WHERE phone=$1 FOR UPDATE", [input.customerPhone]);
    let customerId;
    if (existingCustomers[0]) {
      if (existingCustomers[0].firebase_uid && existingCustomers[0].firebase_uid !== req.customerAuth.uid) {
        await client.query("ROLLBACK");
        return res.status(409).json({ error: "phone_already_linked", message: "Bu telefon boshqa hisobga biriktirilgan." });
      }
      customerId = existingCustomers[0].id;
      await client.query("UPDATE customers SET full_name=$1,firebase_uid=$2,email=$3 WHERE id=$4", [input.customerName, req.customerAuth.uid, req.customerAuth.email, customerId]);
    } else {
      const { rows: [customer] } = await client.query("INSERT INTO customers(full_name,phone,firebase_uid,email) VALUES($1,$2,$3,$4) RETURNING id", [input.customerName, input.customerPhone, req.customerAuth.uid, req.customerAuth.email]);
      customerId = customer.id;
    }
    const ids = input.items.map(x => x.productId);
    const { rows: products } = await client.query(
      "SELECT id,name,price_uzs,kitchen_id FROM products WHERE id=ANY($1::uuid[]) AND available=true FOR SHARE", [ids]);
    if (products.length !== new Set(ids).size) {
      await client.query("ROLLBACK");
      return res.status(400).json({ error: "product_unavailable", message: "Ayrim mahsulotlar mavjud emas." });
    }
    const byId = new Map(products.map(p => [p.id, p]));
    const subtotal = input.items.reduce((sum, item) => sum + Number(byId.get(item.productId).price_uzs) * item.quantity, 0);
    const total = subtotal + input.deliveryFee;
    const kitchenIds = [...new Set(products.map(p => p.kitchen_id).filter(Boolean))];
    if (kitchenIds.length > 1) { await client.query("ROLLBACK"); return res.status(400).json({ error: "multiple_kitchens", message: "Har bir buyurtma bitta oshxonadan bo‘lishi kerak." }); }
    const kitchenId = kitchenIds[0] || null;
    const publicCode = "AK-" + randomBytes(9).toString("hex").toUpperCase();
    const { rows: [order] } = await client.query(`
      INSERT INTO orders(public_code,customer_id,customer_firebase_uid,customer_name,customer_phone,delivery_address,latitude,longitude,landmark,notes,subtotal_uzs,delivery_fee_uzs,total_uzs,payment_method,kitchen_id)
      VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,'cash',$14) RETURNING id,public_code,status,total_uzs,created_at
    `, [publicCode,customerId,req.customerAuth.uid,input.customerName,input.customerPhone,input.address,input.latitude ?? null,input.longitude ?? null,input.landmark ?? null,input.notes ?? null,subtotal,input.deliveryFee,total,kitchenId]);
    for (const item of input.items) {
      const p = byId.get(item.productId);
      await client.query("INSERT INTO order_items(order_id,product_id,product_name,quantity,unit_price_uzs) VALUES($1,$2,$3,$4,$5)",
        [order.id,p.id,p.name,item.quantity,p.price_uzs]);
    }
    await client.query("COMMIT");
    res.status(201).json({ order: { id: order.id, code: order.public_code, status: order.status, total: Number(order.total_uzs), createdAt: order.created_at } });
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally { client.release(); }
}));

app.get("/api/v1/orders/:code/tracking", requireDb, requireCustomer, asyncRoute(async (req, res) => {
  const { rows: [order] } = await pool.query(
    `SELECT o.public_code,o.status,o.updated_at,o.contact_closed_at,
            cp.latitude,cp.longitude,cp.accuracy_m,cp.updated_at AS location_updated_at
       FROM orders o
       LEFT JOIN courier_staff_links l ON l.courier_id=o.courier_id
       LEFT JOIN courier_presence cp ON cp.courier_uid=l.firebase_uid
      WHERE o.public_code=$1 AND o.customer_firebase_uid=$2
      LIMIT 1`,
    [req.params.code, req.customerAuth.uid]
  );
  if (!order) return res.status(404).json({ error: "not_found" });
  const active = ["assigned","picked_up","on_the_way"].includes(order.status) && !order.contact_closed_at;
  const fresh = order.location_updated_at && Date.now() - new Date(order.location_updated_at).getTime() <= 120000;
  res.json({
    order: { code: order.public_code, status: order.status, updatedAt: order.updated_at },
    tracking: active && fresh && order.latitude !== null ? {
      latitude: Number(order.latitude), longitude: Number(order.longitude),
      accuracy: order.accuracy_m === null ? null : Number(order.accuracy_m),
      updatedAt: order.location_updated_at
    } : null,
    contactClosed: !active
  });
}));

app.get("/api/v1/orders/:code", requireDb, requireCustomer, asyncRoute(async (req, res) => {
  const { rows: [order] } = await pool.query("SELECT public_code,status,total_uzs,created_at,updated_at FROM orders WHERE public_code=$1 AND customer_firebase_uid=$2", [req.params.code, req.customerAuth.uid]);
  if (!order) return res.status(404).json({ error: "not_found" });
  res.json({ order: { code: order.public_code, status: order.status, total: Number(order.total_uzs), createdAt: order.created_at, updatedAt: order.updated_at } });
}));

async function requireAdmin(req, res, next) {
  try {
    const auth = getFirebaseAdminAuth();
    if (!auth) return res.status(503).json({ error: "firebase_admin_not_configured" });
    const token = (req.headers.authorization || "").startsWith("Bearer ") ? req.headers.authorization.slice(7) : "";
    if (!token) return res.status(401).json({ error: "missing_token" });
    const decoded = await auth.verifyIdToken(token, true);
    const allowed = new Set((process.env.ADMIN_EMAILS || "").split(",").map(x => x.trim().toLowerCase()).filter(Boolean));
    if (decoded.role !== "admin" && !allowed.has(String(decoded.email || "").toLowerCase())) {
      return res.status(403).json({ error: "admin_only" });
    }
    req.adminAuth = decoded;
    next();
  } catch {
    return res.status(401).json({ error: "invalid_token" });
  }
}

app.get("/api/v1/admin/dispatch/queue", requireDb, requireAdmin, asyncRoute(async (req, res) => {
  const { rows } = await pool.query(`
    SELECT o.id,o.public_code,o.delivery_address,o.created_at,
           CASE WHEN o.latitude IS NULL OR o.longitude IS NULL THEN 'missing_location'
                ELSE 'no_available_courier' END AS reason,
           a.alerted_at
      FROM orders o
      JOIN dispatch_queue_alerts a ON a.order_id=o.id AND a.cleared_at IS NULL
     WHERE o.status='ready'
     ORDER BY a.alerted_at ASC
  `);
  res.json({ queue: rows });
}));

app.get("/api/v1/admin/orders", requireDb, requireAdmin, asyncRoute(async (req, res) => {
  const status = req.query.status;
  const allowedStatuses = ["new","accepted","preparing","ready","assigned","picked_up","on_the_way","delivered","cancelled"];
  if (status && !allowedStatuses.includes(status)) return res.status(400).json({ error: "invalid_status" });
  const params = status ? [status] : [];
  const { rows } = await pool.query(`
    SELECT o.id,o.public_code,o.customer_name,o.customer_phone,o.delivery_address,
           o.status,o.total_uzs,o.payment_status,o.created_at,o.updated_at,
           o.courier_id,c.full_name AS courier_name,c.phone AS courier_phone,
           k.name AS kitchen_name
      FROM orders o
      LEFT JOIN couriers c ON c.id=o.courier_id
      LEFT JOIN kitchens k ON k.id=o.kitchen_id
     ${status ? "WHERE o.status=$1" : ""}
     ORDER BY o.created_at DESC LIMIT 200
  `, params);
  const ids = rows.map(x => x.id);
  const items = ids.length ? await pool.query(
    "SELECT order_id,product_name,quantity,unit_price_uzs FROM order_items WHERE order_id=ANY($1::uuid[]) ORDER BY product_name",
    [ids]
  ) : { rows: [] };
  const grouped = new Map();
  for (const item of items.rows) {
    if (!grouped.has(item.order_id)) grouped.set(item.order_id, []);
    grouped.get(item.order_id).push({ name: item.product_name, quantity: item.quantity, unitPrice: Number(item.unit_price_uzs) });
  }
  res.json({ orders: rows.map(o => ({
    id:o.id, code:o.public_code, customerName:o.customer_name, customerPhone:o.customer_phone,
    address:o.delivery_address, status:o.status, total:Number(o.total_uzs), paymentStatus:o.payment_status,
    createdAt:o.created_at, updatedAt:o.updated_at, courierId:o.courier_id,
    courierName:o.courier_name, courierPhone:o.courier_phone, kitchenName:o.kitchen_name,
    items:grouped.get(o.id)||[]
  })) });
}));

app.patch("/api/v1/admin/orders/:id", requireDb, requireAdmin, asyncRoute(async (req, res) => {
  const parsed = z.object({
    status: z.enum(["new","accepted","preparing","ready","assigned","picked_up","on_the_way","delivered","cancelled"])
  }).safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ error: "invalid_order_update" });
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const { rows:[current] } = await client.query(
      "SELECT id,status FROM orders WHERE id=$1 FOR UPDATE", [req.params.id]
    );
    if (!current) { await client.query("ROLLBACK"); return res.status(404).json({ error:"order_not_found" }); }
    const nextStatus = parsed.data.status;
    const closesContact = ["delivered","cancelled"].includes(nextStatus);
    const { rows:[updated] } = await client.query(
      "UPDATE orders SET status=$1,updated_at=now(),delivered_at=CASE WHEN $1='delivered' THEN COALESCE(delivered_at,now()) ELSE delivered_at END,contact_closed_at=CASE WHEN $2 THEN COALESCE(contact_closed_at,now()) ELSE contact_closed_at END WHERE id=$3 RETURNING id,public_code,status,updated_at,contact_closed_at",
      [nextStatus,closesContact,req.params.id]
    );
    await client.query(
      "INSERT INTO order_status_history(order_id,old_status,new_status,changed_by_role,note) VALUES($1,$2,$3,'admin','Admin panel orqali yangilandi')",
      [updated.id,current.status,nextStatus]
    );
    await client.query("COMMIT");
    res.json({ order:updated });
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally { client.release(); }
}));

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: "internal_error", message: "Serverda xatolik yuz berdi." });
});

app.listen(port, () => {
  console.log(`Ali Kuryer API listening on ${port}`);
  if (pool) startDispatchWorker(pool);
});
