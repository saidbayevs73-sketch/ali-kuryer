import { Router } from "express";
import { z } from "zod";
import { getFirebaseAdminAuth } from "./firebase-admin.js";

const wrap = fn => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

async function verifyFirebase(req, res, next) {
  try {
    const auth = getFirebaseAdminAuth();
    if (!auth) return res.status(503).json({ error: "firebase_admin_not_configured" });
    const header = req.headers.authorization || "";
    if (!header.startsWith("Bearer ")) return res.status(401).json({ error: "missing_token" });
    req.identity = await auth.verifyIdToken(header.slice(7), true);
    if (req.identity.active === false) return res.status(403).json({ error: "account_disabled" });
    next();
  } catch {
    return res.status(401).json({ error: "invalid_token" });
  }
}

function hasAdminAccess(identity) {
  const email = String(identity?.email || "").toLowerCase();
  const allowed = new Set((process.env.ADMIN_EMAILS || "").split(",").map(x => x.trim().toLowerCase()).filter(Boolean));
  return identity?.role === "admin" || (email && allowed.has(email));
}
const adminOnly = (req, res, next) => hasAdminAccess(req.identity)
  ? next()
  : res.status(403).json({ error: "admin_only" });
const kitchenOnly = (req, res, next) => req.identity?.role === "kitchen"
  ? next()
  : res.status(403).json({ error: "kitchen_only" });

export function createOperationsRouter(pool) {
  const router = Router();
  router.use((req, res, next) => pool ? next() : res.status(503).json({ error: "database_not_configured" }));

  // Admin: one operational view for all orders, kitchen progress and courier assignment.
  router.get("/admin/orders", verifyFirebase, adminOnly, wrap(async (req, res) => {
    const { rows } = await pool.query(`
      SELECT o.id,o.public_code,o.customer_name,o.customer_phone,o.delivery_address,
             o.latitude,o.longitude,o.status,o.total_uzs,o.created_at,o.updated_at,
             c.full_name AS courier_name,c.phone AS courier_phone,
             COALESCE(json_agg(json_build_object(
               'name',oi.product_name,'quantity',oi.quantity,'unitPrice',oi.unit_price_uzs
             )) FILTER (WHERE oi.id IS NOT NULL),'[]'::json) AS items
      FROM orders o
      LEFT JOIN couriers c ON c.id=o.courier_id
      LEFT JOIN order_items oi ON oi.order_id=o.id
      GROUP BY o.id,c.full_name,c.phone
      ORDER BY o.created_at DESC LIMIT 300
    `);
    res.json({ orders: rows });
  }));

  // Kitchen: only the active production queue is exposed.
  router.get("/kitchen/orders", verifyFirebase, kitchenOnly, wrap(async (req, res) => {
    const { rows } = await pool.query(`
      SELECT o.id,o.public_code,o.customer_name,o.notes,o.status,o.created_at,
             COALESCE(json_agg(json_build_object(
               'name',oi.product_name,'quantity',oi.quantity,'notes',o.notes
             )) FILTER (WHERE oi.id IS NOT NULL),'[]'::json) AS items
      FROM orders o LEFT JOIN order_items oi ON oi.order_id=o.id
      WHERE o.status=ANY($1::text[])
      GROUP BY o.id ORDER BY o.created_at ASC
    `, [["new","accepted","preparing"]]);
    res.json({ orders: rows });
  }));

  router.patch("/kitchen/orders/:id/status", verifyFirebase, kitchenOnly, wrap(async (req, res) => {
    const parsed = z.enum(["accepted","preparing","ready"]).safeParse(req.body.status);
    if (!parsed.success) return res.status(400).json({ error: "invalid_status" });
    const allowedPrevious = { accepted: ["new"], preparing: ["accepted"], ready: ["preparing"] };
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      const { rows } = await client.query(
        "UPDATE orders SET status=$1,updated_at=now() WHERE id=$2 AND status=ANY($3::text[]) RETURNING id,public_code,status",
        [parsed.data, req.params.id, allowedPrevious[parsed.data]]
      );
      if (!rows[0]) {
        await client.query("ROLLBACK");
        return res.status(409).json({ error: "invalid_order_transition" });
      }
      const previous = allowedPrevious[parsed.data][0];
      await client.query(
        "INSERT INTO order_status_history(order_id,old_status,new_status,changed_by_role,note) VALUES($1,$2,$3,'kitchen',$4)",
        [rows[0].id, previous, parsed.data, "Oshxona holatni yangiladi"]
      );
      await client.query("COMMIT");
      res.json({ order: rows[0] });
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }));

  // Admin dispatches a ready order to the nearest recently-online courier.
  router.post("/admin/orders/:id/dispatch", verifyFirebase, adminOnly, wrap(async (req, res) => {
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      const { rows: [order] } = await client.query(
        "SELECT id,public_code,latitude,longitude,status FROM orders WHERE id=$1 FOR UPDATE",
        [req.params.id]
      );
      if (!order) {
        await client.query("ROLLBACK");
        return res.status(404).json({ error: "order_not_found" });
      }
      if (order.status !== "ready") {
        await client.query("ROLLBACK");
        return res.status(409).json({ error: "order_not_ready", message: "Buyurtma avval oshxonada tayyor bo‘lishi kerak." });
      }
      const { rows: couriers } = await client.query(`
        SELECT l.firebase_uid,l.courier_id,c.full_name,c.phone,p.latitude,p.longitude
        FROM courier_staff_links l
        JOIN couriers c ON c.id=l.courier_id AND c.active=true
        JOIN courier_presence p ON p.courier_uid=l.firebase_uid AND p.is_online=true AND p.updated_at>now()-interval '90 seconds'
        WHERE NOT EXISTS (
          SELECT 1 FROM courier_dispatch_offers d
          WHERE d.order_id=$1 AND d.courier_uid=l.firebase_uid AND d.status='offered' AND d.expires_at>now()
        )
        ORDER BY CASE WHEN $2::double precision IS NULL OR $3::double precision IS NULL THEN 0
          ELSE (p.latitude-$2)*(p.latitude-$2)+(p.longitude-$3)*(p.longitude-$3) END ASC,
          p.updated_at DESC
        LIMIT 5
        FOR UPDATE OF c SKIP LOCKED
      `, [order.id, order.latitude, order.longitude]);
      if (!couriers.length) {
        await client.query("ROLLBACK");
        return res.status(409).json({ error: "no_online_couriers", message: "Hozircha onlayn kuryer topilmadi." });
      }
      const selected = couriers[0];
      await client.query(
        "INSERT INTO courier_dispatch_offers(order_id,courier_id,courier_uid,status,expires_at) VALUES($1,$2,$3,'offered',now()+interval '2 minutes') ON CONFLICT(order_id,courier_uid) DO UPDATE SET status='offered',offered_at=now(),expires_at=now()+interval '2 minutes',responded_at=NULL",
        [order.id, selected.courier_id, selected.firebase_uid]
      );
      await client.query(
        "INSERT INTO audit_log(actor_type,action,entity_type,entity_id,metadata) VALUES('admin','dispatch_order','order',$1,$2::jsonb)",
        [order.id, JSON.stringify({ courierId: selected.courier_id })]
      );
      await client.query("COMMIT");
      res.json({ ok: true, orderCode: order.public_code, offeredTo: { name: selected.full_name }, expiresInSeconds: 120 });
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }));

  // Customer tracking: public order code alone is not enough; phone must match.
  router.get("/orders/:code/tracking", wrap(async (req, res) => {
    const phone = String(req.query.phone || "").trim();
    if (phone.length < 7) return res.status(400).json({ error: "phone_required" });
    const { rows: [order] } = await pool.query(`
      SELECT o.id,o.public_code,o.status,o.delivery_address,o.latitude AS destination_latitude,
             o.longitude AS destination_longitude,o.created_at,o.updated_at,
             p.latitude AS courier_latitude,p.longitude AS courier_longitude,p.updated_at AS courier_updated_at,
             c.full_name AS courier_name,c.phone AS courier_phone
      FROM orders o
      LEFT JOIN courier_staff_links l ON l.courier_id=o.courier_id
      LEFT JOIN courier_presence p ON p.courier_uid=l.firebase_uid AND p.is_online=true
      LEFT JOIN couriers c ON c.id=o.courier_id
      WHERE o.public_code=$1 AND regexp_replace(o.customer_phone,'[^0-9]','','g')=regexp_replace($2,'[^0-9]','','g')
    `, [req.params.code, phone]);
    if (!order) return res.status(404).json({ error: "order_not_found" });
    const { rows: history } = await pool.query(
      "SELECT new_status,created_at,note FROM order_status_history WHERE order_id=$1 ORDER BY created_at ASC",
      [order.id]
    );
    res.json({ order: { code: order.public_code,status: order.status,address: order.delivery_address,
      destination: order.destination_latitude == null ? null : { latitude: order.destination_latitude, longitude: order.destination_longitude },
      courier: order.courier_latitude == null ? null : { name: order.courier_name,phone: order.courier_phone,latitude: order.courier_latitude,longitude: order.courier_longitude,updatedAt: order.courier_updated_at },
      createdAt: order.created_at,updatedAt: order.updated_at,history } });
  }));

  return router;
}
