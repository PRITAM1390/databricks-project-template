-- Bronze orders table. Re-runnable: safe to execute on every deploy.
-- Bronze orders table
CREATE TABLE IF NOT EXISTS IDENTIFIER(:catalog || '.' || :schema || '.orders') (
  order_id    BIGINT,
  customer    STRING,
  amount      DOUBLE,
  status      STRING,
  _ingest_ts  TIMESTAMP,
  _source     STRING
)
COMMENT 'Raw orders from sample source';
