-- Baseline for the deployable relational boundary. Apply with the approved
-- migration runner; the SQLite schema in ag_datovka.app is fixture-only.
CREATE TABLE IF NOT EXISTS schema_migrations (
  version varchar(100) PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now(),
  checksum varchar(71) NOT NULL
);

CREATE TABLE IF NOT EXISTS durable_outbox (
  operation_id uuid PRIMARY KEY,
  tenant_id varchar(100) NOT NULL,
  payload jsonb NOT NULL,
  state varchar(32) NOT NULL CHECK (state IN ('pending','published','failed')),
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  available_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS durable_outbox_ready_idx
  ON durable_outbox (available_at, created_at) WHERE state = 'pending';

CREATE TABLE IF NOT EXISTS content_manifests (
  content_id uuid PRIMARY KEY,
  tenant_id varchar(100) NOT NULL,
  object_key varchar(512) NOT NULL UNIQUE,
  byte_length bigint NOT NULL CHECK (byte_length >= 0),
  sha256 char(64) NOT NULL,
  media_type varchar(255) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

