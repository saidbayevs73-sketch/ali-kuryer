import { readFile } from "node:fs/promises";
import pg from "pg";

const { Client } = pg;
const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  console.error("XATO: DATABASE_URL muhit o'zgaruvchisi berilmagan.");
  process.exit(1);
}

const expectedTables = [
  "customers", "saved_addresses", "couriers", "categories", "products",
  "orders", "order_items", "promo_codes", "reviews", "delivery_zones",
  "courier_locations", "courier_shifts", "order_status_history",
  "notifications", "support_tickets", "admin_users", "audit_log"
];

const client = new Client({
  connectionString,
  ssl: { rejectUnauthorized: false },
  connectionTimeoutMillis: 15000
});

try {
  await client.connect();

  const check = await client.query(
    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = ANY($1::text[])",
    [expectedTables]
  );

  if (check.rows.length > 0) {
    console.error("TO'XTATILDI: bazada loyiha jadvallaridan ayrimlari allaqachon mavjud:");
    for (const row of check.rows) console.error("- " + row.tablename);
    console.error("Hech qanday SQL bajarilmadi. Avval mavjud jadvallar tekshirilsin.");
    process.exitCode = 2;
  } else {
    const schema = await readFile(new URL("../schema.sql", import.meta.url), "utf8");
    await client.query("BEGIN");
    try {
      await client.query(schema);
      await client.query("COMMIT");
      console.log("MUVAFFAQIYAT: test bazasiga sxema o'rnatildi.");
      console.log("Jadvallar: " + expectedTables.length);
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    }
  }
} catch (error) {
  console.error("Migratsiya bajarilmadi:", error.message);
  process.exitCode = 1;
} finally {
  await client.end().catch(() => {});
}
