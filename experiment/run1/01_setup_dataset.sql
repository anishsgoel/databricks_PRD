-- =====================================================================
-- Genie definition experiment: synthetic sales dataset
-- Run in a Databricks Free Edition SQL editor (or notebook %sql cell).
-- Creates:
--   workspace.sales.customers   (600 rows)  -- attach to the Genie agent
--   workspace.sales.orders      (~2,100 rows) -- attach to the Genie agent
--   workspace.sales_answers.*   ground truth -- DO NOT attach to the agent
-- Dates are relative to current_date(): run setup, answers and Genie
-- questions on the SAME day.
-- Built-in traps (each one maps to a part of a definition):
--   * order_date vs invoice_date differ by 10-24 days for ~30% of orders
--   * ~35% of customers have their last order 75-105 days ago (90-day boundary)
--   * ~12% of orders are refunded or cancelled
--   * ~8% of customers are internal test accounts
-- =====================================================================

USE CATALOG workspace;
CREATE SCHEMA IF NOT EXISTS sales;
CREATE SCHEMA IF NOT EXISTS sales_answers;

CREATE OR REPLACE TABLE sales.customers
COMMENT 'One row per customer account.'
AS
SELECT
  CAST(id + 1 AS INT)                                        AS customer_id,
  CASE WHEN pmod(hash(id, 'i'), 100) < 8
       THEN concat('Internal Test ', CAST(id + 1 AS STRING))
       ELSE concat(element_at(array('Acme','Globex','Initech','Umbrella','Stark','Wayne','Hooli','Vandelay','Soylent','Wonka','Tyrell','Cyberdyne'), CAST(pmod(hash(id,'n1'),12) + 1 AS INT)),
                   ' ',
                   element_at(array('Labs','Corp','Group','Partners','Systems','Holdings','Foods','Logistics'), CAST(pmod(hash(id,'n2'),8) + 1 AS INT)),
                   ' ', CAST(id + 1 AS STRING))
  END                                                        AS customer_name,
  element_at(array('North America','EMEA','APAC','LATAM'), CAST(pmod(hash(id, 'r'), 4) + 1 AS INT)) AS region,
  CASE pmod(hash(id, 'r'), 4)
    WHEN 0 THEN element_at(array('United States','Canada'), CAST(pmod(hash(id,'c'),2) + 1 AS INT))
    WHEN 1 THEN element_at(array('United Kingdom','Germany','France','Greece'), CAST(pmod(hash(id,'c'),4) + 1 AS INT))
    WHEN 2 THEN element_at(array('Japan','Australia','Singapore','India'), CAST(pmod(hash(id,'c'),4) + 1 AS INT))
    ELSE        element_at(array('Brazil','Mexico','Chile'), CAST(pmod(hash(id,'c'),3) + 1 AS INT))
  END                                                        AS billing_country,
  pmod(hash(id, 'i'), 100) < 8                               AS is_internal,
  CASE WHEN pmod(hash(id, 'sz'), 10) < 2 THEN 'Large'
       WHEN pmod(hash(id, 'sz'), 10) < 6 THEN 'Mid-market'
       ELSE 'Small' END                                      AS company_size,
  date_sub(current_date(), 400 + CAST(pmod(hash(id, 'cr'), 900) AS INT)) AS created_date
FROM range(600);

CREATE OR REPLACE TABLE sales.orders
COMMENT 'One row per order. order_date is when the order was placed; invoice_date is when it was billed.'
AS
WITH base AS (
  SELECT
    id,
    -- recency of the customer''s most recent order
    CASE
      WHEN pmod(hash(id, 'b'), 20) < 7  THEN CAST(pmod(hash(id, 'd'), 60) AS INT)            -- clearly recent: 0-59 days
      WHEN pmod(hash(id, 'b'), 20) < 14 THEN 75 + CAST(pmod(hash(id, 'd'), 31) AS INT)       -- boundary: 75-105 days
      ELSE 120 + CAST(pmod(hash(id, 'd'), 280) AS INT)                                        -- older: 120-399 days
    END AS recency_days,
    1 + CAST(pmod(hash(id, 'n'), 6) AS INT) AS n_orders,
    CASE WHEN pmod(hash(id, 'sz'), 10) < 2 THEN 6 WHEN pmod(hash(id, 'sz'), 10) < 6 THEN 2 ELSE 1 END AS size_mult
  FROM range(600)
),
exploded AS (
  SELECT id, recency_days, size_mult, k
  FROM base
  LATERAL VIEW explode(sequence(0, n_orders - 1)) t AS k
)
SELECT
  CAST(row_number() OVER (ORDER BY id, k) AS INT)                      AS order_id,
  CAST(id + 1 AS INT)                                                   AS customer_id,
  date_sub(current_date(), recency_days + k * 35 + CAST(pmod(hash(id, k, 'j'), 20) AS INT)) AS order_date,
  date_add(
    date_sub(current_date(), recency_days + k * 35 + CAST(pmod(hash(id, k, 'j'), 20) AS INT)),
    CASE WHEN pmod(hash(id, k, 'l'), 10) < 3
         THEN 10 + CAST(pmod(hash(id, k, 'l2'), 15) AS INT)                -- late invoice: 10-24 days after order
         ELSE CAST(pmod(hash(id, k, 'l2'), 4) AS INT) END                 -- normal: 0-3 days after order
  )                                                                     AS invoice_date,
  CAST(round((800 + pmod(hash(id, k, 'a'), 9000)) * size_mult, 2) AS DECIMAL(12,2)) AS amount_usd,
  CASE WHEN pmod(hash(id, k, 's'), 100) < 8  THEN 'refunded'
       WHEN pmod(hash(id, k, 's'), 100) < 12 THEN 'cancelled'
       ELSE 'completed' END                                             AS status
FROM exploded;

-- Sanity check
SELECT
  (SELECT count(*) FROM sales.customers)                                AS customers,
  (SELECT count(*) FROM sales.customers WHERE is_internal)              AS internal_accounts,
  (SELECT count(*) FROM sales.orders)                                   AS orders,
  (SELECT count(*) FROM sales.orders WHERE status <> 'completed')       AS refunded_or_cancelled,
  (SELECT count(*) FROM sales.orders WHERE datediff(invoice_date, order_date) >= 10) AS late_invoices;
