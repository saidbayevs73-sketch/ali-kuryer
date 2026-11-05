BEGIN;

CREATE TABLE IF NOT EXISTS courier_dispatch_offers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  courier_id UUID NOT NULL REFERENCES couriers(id) ON DELETE CASCADE,
  courier_uid TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'offered' CHECK (status IN ('offered','accepted','declined','expired')),
  offered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '30 seconds'),
  responded_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS dispatch_offer_expiry_idx
  ON courier_dispatch_offers(status, expires_at);
CREATE INDEX IF NOT EXISTS dispatch_offer_order_idx
  ON courier_dispatch_offers(order_id, offered_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS dispatch_one_open_offer_per_order_idx
  ON courier_dispatch_offers(order_id) WHERE status='offered';

CREATE TABLE IF NOT EXISTS dispatch_queue_alerts (
  order_id UUID PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
  alerted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  cleared_at TIMESTAMPTZ
);

COMMIT;
