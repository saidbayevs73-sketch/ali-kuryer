BEGIN;
CREATE TABLE IF NOT EXISTS courier_staff_links (
  firebase_uid TEXT PRIMARY KEY,
  courier_id UUID NOT NULL UNIQUE REFERENCES couriers(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS courier_staff_links_courier_idx ON courier_staff_links(courier_id);
COMMIT;
