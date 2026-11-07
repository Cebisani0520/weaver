-- Fraud features, one row per transaction, written to `txn-features`.
--
-- Event time is `$rowtime`, the Kafka record timestamp, which producers set to
-- the event's event_time. The environment root sets the source tables'
-- watermark to `$rowtime` minus a short delay (watermark_delay_ms), so an event
-- read just after a newer one on another partition is not dropped as late.
--
-- Flink requires every OVER aggregate in one SELECT to use the same window, so
-- each window is its own CTE. The CTEs are re-joined per transaction with
-- interval joins on equal event time, which keep only a moment of state.
--
-- Tables are CMF's inferred tables: a leading raw `key` BYTES column (only value
-- schemas are registered), then the value schema's fields, all nullable.
--
-- SAST is UTC+2 with no daylight saving. The statement pins the session time
-- zone to UTC (table.local-time-zone), so the night flag adds two hours.
INSERT INTO `txn-features`
WITH
txn AS (
  SELECT transaction_id, customer_id, device_id, beneficiary_id, channel, province,
         amount_cents, `$rowtime` AS ts
  FROM `transactions`
),
acct AS (
  SELECT customer_id, event_type, device_id, beneficiary_id, `$rowtime` AS ts
  FROM `account-events`
),
-- Transactions and account events in one stream, so account-event flags can be
-- computed with OVER windows that end at each transaction.
events AS (
  SELECT customer_id, transaction_id, device_id, beneficiary_id,
         CAST(NULL AS STRING) AS event_type, ts
  FROM txn
  UNION ALL
  SELECT customer_id, CAST(NULL AS STRING) AS transaction_id, device_id, beneficiary_id,
         event_type, ts
  FROM acct
),
w_1h AS (
  SELECT transaction_id, ts,
         COUNT(*) OVER w AS txn_count_1h
  FROM txn
  WINDOW w AS (PARTITION BY customer_id ORDER BY ts
               RANGE BETWEEN INTERVAL '1' HOUR PRECEDING AND CURRENT ROW)
),
w_24h AS (
  SELECT transaction_id, ts,
         COUNT(*) OVER w AS txn_count_24h,
         COUNT(DISTINCT province) OVER w AS distinct_provinces_24h
  FROM txn
  WINDOW w AS (PARTITION BY customer_id ORDER BY ts
               RANGE BETWEEN INTERVAL '24' HOUR PRECEDING AND CURRENT ROW)
),
w_30d AS (
  SELECT transaction_id, ts,
         AVG(CAST(amount_cents AS DOUBLE)) OVER w AS avg_amount_30d_cents
  FROM txn
  WINDOW w AS (PARTITION BY customer_id ORDER BY ts
               RANGE BETWEEN INTERVAL '30' DAY PRECEDING AND CURRENT ROW)
),
sim_swap AS (
  SELECT transaction_id, ts, sim_swap_72h
  FROM (
    SELECT transaction_id, ts,
           MAX(CASE WHEN event_type = 'SIM_SWAP' THEN 1 ELSE 0 END) OVER w AS sim_swap_72h
    FROM events
    WINDOW w AS (PARTITION BY customer_id ORDER BY ts
                 RANGE BETWEEN INTERVAL '72' HOUR PRECEDING AND CURRENT ROW)
  )
  WHERE transaction_id IS NOT NULL
),
new_beneficiary AS (
  SELECT transaction_id, ts, beneficiary_added_24h
  FROM (
    SELECT transaction_id, ts,
           MAX(CASE WHEN event_type = 'BENEFICIARY_ADDED' THEN 1 ELSE 0 END) OVER w
             AS beneficiary_added_24h
    FROM events
    WINDOW w AS (PARTITION BY customer_id, beneficiary_id ORDER BY ts
                 RANGE BETWEEN INTERVAL '24' HOUR PRECEDING AND CURRENT ROW)
  )
  WHERE transaction_id IS NOT NULL
),
new_device AS (
  SELECT transaction_id, ts, device_login_24h
  FROM (
    SELECT transaction_id, ts,
           MAX(CASE WHEN event_type = 'NEW_DEVICE_LOGIN' THEN 1 ELSE 0 END) OVER w
             AS device_login_24h
    FROM events
    WINDOW w AS (PARTITION BY customer_id, device_id ORDER BY ts
                 RANGE BETWEEN INTERVAL '24' HOUR PRECEDING AND CURRENT ROW)
  )
  WHERE transaction_id IS NOT NULL
)
SELECT
  -- Inferred tables start with the raw message key (no key schema is
  -- registered). Key by customer, like the source topics.
  ENCODE(t.customer_id, 'UTF-8') AS `key`,
  t.transaction_id,
  t.customer_id,
  t.ts AS event_time,
  t.amount_cents,
  t.channel,
  t.province,
  a.txn_count_1h,
  b.txn_count_24h,
  b.distinct_provinces_24h,
  COALESCE(c.avg_amount_30d_cents, CAST(t.amount_cents AS DOUBLE)) AS avg_amount_30d_cents,
  CAST(t.amount_cents AS DOUBLE)
    / COALESCE(c.avg_amount_30d_cents, CAST(t.amount_cents AS DOUBLE)) AS amount_to_avg_30d,
  t.beneficiary_id IS NOT NULL AND COALESCE(n.beneficiary_added_24h, 0) = 1 AS is_new_beneficiary,
  COALESCE(s.sim_swap_72h, 0) = 1 AS sim_swap_72h,
  t.device_id IS NOT NULL AND COALESCE(d.device_login_24h, 0) = 1 AS is_new_device,
  HOUR(TIMESTAMPADD(HOUR, 2, CAST(t.ts AS TIMESTAMP(3)))) < 5 AS is_night_sast,
  'v1' AS feature_version
FROM txn t
JOIN w_1h a            ON a.transaction_id = t.transaction_id AND a.ts = t.ts
JOIN w_24h b           ON b.transaction_id = t.transaction_id AND b.ts = t.ts
JOIN w_30d c           ON c.transaction_id = t.transaction_id AND c.ts = t.ts
JOIN sim_swap s        ON s.transaction_id = t.transaction_id AND s.ts = t.ts
JOIN new_beneficiary n ON n.transaction_id = t.transaction_id AND n.ts = t.ts
JOIN new_device d      ON d.transaction_id = t.transaction_id AND d.ts = t.ts;
