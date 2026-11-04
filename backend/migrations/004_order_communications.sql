BEGIN;
CREATE TABLE IF NOT EXISTS order_call_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  call_id UUID NOT NULL REFERENCES order_call_sessions(id) ON DELETE CASCADE,
  sender_uid TEXT NOT NULL,
  signal_type TEXT NOT NULL CHECK (signal_type IN ('offer','answer','ice','hangup')),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS order_call_signals_call_idx ON order_call_signals(call_id,created_at);

-- Prevent two simultaneous calls for the same order. Expired calls are cleaned
-- by the API before creating or retrieving an active call.
CREATE UNIQUE INDEX IF NOT EXISTS order_call_one_active_per_order_idx
  ON order_call_sessions(order_id)
  WHERE status IN ('ringing','accepted');
COMMIT;
