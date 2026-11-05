CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS customers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name TEXT NOT NULL,
  phone TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS saved_addresses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  label TEXT NOT NULL DEFAULT 'Uy',
  address TEXT NOT NULL,
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  landmark TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS couriers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name TEXT NOT NULL,
  phone TEXT NOT NULL UNIQUE,
  active BOOLEAN NOT NULL DEFAULT false,
  rating NUMERIC(3,2) NOT NULL DEFAULT 5.00,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  slug TEXT NOT NULL UNIQUE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  active BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category_id UUID REFERENCES categories(id),
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  price_uzs BIGINT NOT NULL CHECK (price_uzs >= 0),
  image_url TEXT,
  available BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  public_code TEXT NOT NULL UNIQUE,
  customer_id UUID REFERENCES customers(id),
  customer_name TEXT NOT NULL,
  customer_phone TEXT NOT NULL,
  delivery_address TEXT NOT NULL,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  landmark TEXT,
  notes TEXT,
  subtotal_uzs BIGINT NOT NULL CHECK (subtotal_uzs >= 0),
  delivery_fee_uzs BIGINT NOT NULL DEFAULT 0 CHECK (delivery_fee_uzs >= 0),
  total_uzs BIGINT NOT NULL CHECK (total_uzs >= 0),
  payment_method TEXT NOT NULL DEFAULT 'cash' CHECK (payment_method IN ('cash')),
  payment_status TEXT NOT NULL DEFAULT 'pending' CHECK (payment_status IN ('pending','paid','refunded')),
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','accepted','preparing','ready','assigned','picked_up','on_the_way','delivered','cancelled')),
  courier_id UUID REFERENCES couriers(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id UUID REFERENCES products(id),
  product_name TEXT NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unit_price_uzs BIGINT NOT NULL CHECK (unit_price_uzs >= 0)
);

CREATE TABLE IF NOT EXISTS promo_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL UNIQUE,
  discount_type TEXT NOT NULL CHECK (discount_type IN ('fixed','percent')),
  discount_value BIGINT NOT NULL CHECK (discount_value > 0),
  active BOOLEAN NOT NULL DEFAULT true,
  starts_at TIMESTAMPTZ,
  ends_at TIMESTAMPTZ,
  usage_limit INTEGER,
  used_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL UNIQUE REFERENCES orders(id),
  customer_id UUID REFERENCES customers(id),
  rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS orders_status_created_idx ON orders(status, created_at DESC);
CREATE INDEX IF NOT EXISTS orders_courier_idx ON orders(courier_id, status);
CREATE INDEX IF NOT EXISTS products_category_idx ON products(category_id, available);
CREATE INDEX IF NOT EXISTS addresses_customer_idx ON saved_addresses(customer_id);
-- Operational features prepared for the next integration stage.
CREATE TABLE IF NOT EXISTS delivery_zones (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),name TEXT NOT NULL,fee_uzs BIGINT NOT NULL DEFAULT 12000 CHECK(fee_uzs>=0),min_order_uzs BIGINT NOT NULL DEFAULT 0 CHECK(min_order_uzs>=0),eta_min INTEGER NOT NULL DEFAULT 25 CHECK(eta_min>0),eta_max INTEGER NOT NULL DEFAULT 50 CHECK(eta_max>=eta_min),active BOOLEAN NOT NULL DEFAULT true);
CREATE TABLE IF NOT EXISTS courier_locations (courier_id UUID PRIMARY KEY REFERENCES couriers(id) ON DELETE CASCADE,latitude DOUBLE PRECISION NOT NULL,longitude DOUBLE PRECISION NOT NULL,heading DOUBLE PRECISION,updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS courier_shifts (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),courier_id UUID NOT NULL REFERENCES couriers(id),started_at TIMESTAMPTZ NOT NULL DEFAULT now(),ended_at TIMESTAMPTZ,start_cash_uzs BIGINT NOT NULL DEFAULT 0,end_cash_uzs BIGINT);
CREATE TABLE IF NOT EXISTS order_status_history (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,old_status TEXT,new_status TEXT NOT NULL,changed_by_role TEXT NOT NULL CHECK(changed_by_role IN ('system','admin','courier')),changed_by_id UUID,note TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS notifications (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,courier_id UUID REFERENCES couriers(id) ON DELETE CASCADE,title TEXT NOT NULL,body TEXT NOT NULL,read_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),CHECK(customer_id IS NOT NULL OR courier_id IS NOT NULL));
CREATE TABLE IF NOT EXISTS support_tickets (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),order_id UUID REFERENCES orders(id),customer_id UUID REFERENCES customers(id),phone TEXT NOT NULL,subject TEXT NOT NULL,message TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','in_progress','resolved','closed')),created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS admin_users (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),full_name TEXT NOT NULL,phone TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('owner','manager','dispatcher','support','finance')),active BOOLEAN NOT NULL DEFAULT true,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS audit_log (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),actor_type TEXT NOT NULL CHECK(actor_type IN ('admin','courier','system')),actor_id UUID,action TEXT NOT NULL,entity_type TEXT NOT NULL,entity_id UUID,metadata JSONB NOT NULL DEFAULT '{}'::jsonb,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS order_history_order_idx ON order_status_history(order_id,created_at);
CREATE INDEX IF NOT EXISTS notifications_customer_idx ON notifications(customer_id,read_at,created_at DESC);
CREATE INDEX IF NOT EXISTS tickets_status_idx ON support_tickets(status,created_at DESC);
CREATE INDEX IF NOT EXISTS courier_location_updated_idx ON courier_locations(updated_at);

-- Firebase courier identity and dispatch tables used by courier-routes.js.
CREATE TABLE IF NOT EXISTS courier_staff_links (
  firebase_uid TEXT PRIMARY KEY,
  courier_id UUID NOT NULL UNIQUE REFERENCES couriers(id) ON DELETE CASCADE,
  linked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS courier_dispatch_offers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  courier_id UUID NOT NULL REFERENCES couriers(id) ON DELETE CASCADE,
  courier_uid TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'offered' CHECK (status IN ('offered','accepted','declined','expired')),
  offered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '2 minutes'),
  responded_at TIMESTAMPTZ,
  UNIQUE(order_id, courier_uid)
);
CREATE INDEX IF NOT EXISTS courier_offers_lookup_idx
  ON courier_dispatch_offers(order_id, courier_uid, status, expires_at);

CREATE TABLE IF NOT EXISTS courier_presence (
  courier_uid TEXT PRIMARY KEY,
  is_online BOOLEAN NOT NULL DEFAULT false,
  latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
  longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
  accuracy_m DOUBLE PRECISION CHECK (accuracy_m IS NULL OR accuracy_m >= 0),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS contact_closed_at TIMESTAMPTZ;


-- Kitchen actions are recorded in the shared order timeline.
ALTER TABLE order_status_history DROP CONSTRAINT IF EXISTS order_status_history_changed_by_role_check;
ALTER TABLE order_status_history ADD CONSTRAINT order_status_history_changed_by_role_check
  CHECK (changed_by_role IN ('system','admin','kitchen','courier'));
CREATE INDEX IF NOT EXISTS courier_presence_online_idx
  ON courier_presence(is_online, updated_at DESC);
