-- Ali Kuryer unified platform foundation (PostgreSQL)
-- Apply once with: psql "$DATABASE_URL" -f backend/migrations/002_unified_platform.sql
BEGIN;

ALTER TABLE customers ADD COLUMN IF NOT EXISTS firebase_uid TEXT UNIQUE;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_firebase_uid TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS kitchen_id UUID;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS contact_closed_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS kitchens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_uid TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  phone TEXT NOT NULL,
  logo_url TEXT,
  address TEXT NOT NULL,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  location_verified_at TIMESTAMPTZ,
  active BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE orders ADD CONSTRAINT orders_kitchen_id_fk
  FOREIGN KEY (kitchen_id) REFERENCES kitchens(id) ON DELETE SET NULL;

ALTER TABLE products ADD COLUMN IF NOT EXISTS kitchen_id UUID REFERENCES kitchens(id) ON DELETE CASCADE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS ingredients TEXT NOT NULL DEFAULT '';
ALTER TABLE products ADD COLUMN IF NOT EXISTS photo_source TEXT NOT NULL DEFAULT 'upload'
  CHECK (photo_source IN ('camera','upload','legacy'));
ALTER TABLE products ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS staff_profiles (
  firebase_uid TEXT PRIMARY KEY,
  role TEXT NOT NULL CHECK (role IN ('courier','kitchen','admin')),
  kitchen_id UUID REFERENCES kitchens(id) ON DELETE SET NULL,
  display_name TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS support_tickets_v2 (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
  sender_uid TEXT,
  sender_role TEXT NOT NULL CHECK (sender_role IN ('customer','courier','kitchen','admin')),
  subject TEXT NOT NULL,
  message TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','in_progress','resolved','closed')),
  assigned_role TEXT CHECK (assigned_role IN ('admin','courier','kitchen')),
  assigned_uid TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS support_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_id UUID NOT NULL REFERENCES support_tickets_v2(id) ON DELETE CASCADE,
  sender_uid TEXT NOT NULL,
  sender_role TEXT NOT NULL CHECK (sender_role IN ('customer','courier','kitchen','admin')),
  body TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 5000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS private_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
  customer_uid TEXT NOT NULL,
  courier_uid TEXT,
  kitchen_id UUID REFERENCES kitchens(id) ON DELETE SET NULL,
  courier_rating SMALLINT CHECK (courier_rating BETWEEN 1 AND 5),
  food_rating SMALLINT CHECK (food_rating BETWEEN 1 AND 5),
  courier_comment TEXT NOT NULL DEFAULT '',
  food_comment TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Access to private_reviews must be enforced in API: author, Super Admin, and the
-- order's kitchen may read; courier and public catalogue must never expose comments.

CREATE TABLE IF NOT EXISTS order_chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  sender_uid TEXT NOT NULL,
  sender_role TEXT NOT NULL CHECK (sender_role IN ('customer','courier')),
  body TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 4000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_call_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  caller_uid TEXT NOT NULL,
  callee_uid TEXT NOT NULL,
  call_type TEXT NOT NULL DEFAULT 'audio' CHECK (call_type = 'audio'),
  status TEXT NOT NULL DEFAULT 'ringing' CHECK (status IN ('ringing','accepted','rejected','ended','expired')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ
);
-- Only audio/VoIP calls. No video-call feature is part of this platform.

CREATE TABLE IF NOT EXISTS courier_live_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  courier_uid TEXT NOT NULL,
  check_type TEXT NOT NULL CHECK (check_type IN ('person','scooter')),
  media_url TEXT NOT NULL,
  capture_method TEXT NOT NULL CHECK (capture_method = 'in_app_camera'),
  captured_at TIMESTAMPTZ NOT NULL,
  reviewed_by_uid TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
  review_note TEXT,
  reviewed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS courier_presence (
  courier_uid TEXT PRIMARY KEY,
  is_online BOOLEAN NOT NULL DEFAULT false,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  accuracy_m DOUBLE PRECISION,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS telegram_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_user_id TEXT NOT NULL UNIQUE,
  customer_uid TEXT,
  linked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform_settings (
  setting_key TEXT PRIMARY KEY,
  setting_value JSONB NOT NULL,
  updated_by_uid TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_uid TEXT NOT NULL,
  actor_role TEXT NOT NULL,
  action TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT,
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS kitchens_owner_idx ON kitchens(owner_uid);
CREATE INDEX IF NOT EXISTS products_kitchen_idx ON products(kitchen_id, available);
CREATE INDEX IF NOT EXISTS tickets_v2_status_idx ON support_tickets_v2(status, created_at DESC);
CREATE INDEX IF NOT EXISTS support_messages_ticket_idx ON support_messages(ticket_id, created_at);
CREATE INDEX IF NOT EXISTS order_chat_order_idx ON order_chat_messages(order_id, created_at);
CREATE INDEX IF NOT EXISTS order_calls_order_idx ON order_call_sessions(order_id, created_at DESC);
CREATE INDEX IF NOT EXISTS courier_presence_online_idx ON courier_presence(is_online, updated_at);
CREATE INDEX IF NOT EXISTS courier_checks_status_idx ON courier_live_checks(status, captured_at DESC);
CREATE INDEX IF NOT EXISTS private_reviews_kitchen_idx ON private_reviews(kitchen_id, created_at DESC);

COMMIT;
