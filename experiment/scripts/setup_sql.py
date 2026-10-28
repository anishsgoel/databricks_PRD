# Dataset v2: same customers as v1, orders gain product_line. Tables go in SCHEMA (e.g. workspace.sales2).
def setup_statements(SCHEMA):
    return [
f"""CREATE OR REPLACE TABLE {SCHEMA}.customers
COMMENT 'One row per customer account.'
AS SELECT
  CAST(id + 1 AS INT) AS customer_id,
  CASE WHEN pmod(hash(id, 'i'), 100) < 8 THEN concat('Internal Test ', CAST(id + 1 AS STRING))
       ELSE concat(element_at(array('Acme','Globex','Initech','Umbrella','Stark','Wayne','Hooli','Vandelay','Soylent','Wonka','Tyrell','Cyberdyne'), CAST(pmod(hash(id,'n1'),12) + 1 AS INT)), ' ',
                   element_at(array('Labs','Corp','Group','Partners','Systems','Holdings','Foods','Logistics'), CAST(pmod(hash(id,'n2'),8) + 1 AS INT)), ' ', CAST(id + 1 AS STRING))
  END AS customer_name,
  element_at(array('North America','EMEA','APAC','LATAM'), CAST(pmod(hash(id, 'r'), 4) + 1 AS INT)) AS region,
  pmod(hash(id, 'i'), 100) < 8 AS is_internal,
  CASE WHEN pmod(hash(id, 'sz'), 10) < 2 THEN 'Large' WHEN pmod(hash(id, 'sz'), 10) < 6 THEN 'Mid-market' ELSE 'Small' END AS company_size,
  date_sub(current_date(), 400 + CAST(pmod(hash(id, 'cr'), 900) AS INT)) AS created_date
FROM range(600)""",
f"""CREATE OR REPLACE TABLE {SCHEMA}.orders
COMMENT 'One row per order. order_date is when the order was placed; invoice_date is when it was billed. product_line is what was sold.'
AS WITH base AS (
  SELECT id,
    CASE WHEN pmod(hash(id, 'b'), 20) < 7 THEN CAST(pmod(hash(id, 'd'), 60) AS INT)
         WHEN pmod(hash(id, 'b'), 20) < 14 THEN 75 + CAST(pmod(hash(id, 'd'), 31) AS INT)
         ELSE 120 + CAST(pmod(hash(id, 'd'), 280) AS INT) END AS recency_days,
    1 + CAST(pmod(hash(id, 'n'), 6) AS INT) AS n_orders,
    CASE WHEN pmod(hash(id, 'sz'), 10) < 2 THEN 6 WHEN pmod(hash(id, 'sz'), 10) < 6 THEN 2 ELSE 1 END AS size_mult
  FROM range(600)),
exploded AS (SELECT id, recency_days, size_mult, k FROM base LATERAL VIEW explode(sequence(0, n_orders - 1)) t AS k)
SELECT
  CAST(row_number() OVER (ORDER BY id, k) AS INT) AS order_id,
  CAST(id + 1 AS INT) AS customer_id,
  date_sub(current_date(), recency_days + k * 35 + CAST(pmod(hash(id, k, 'j'), 20) AS INT)) AS order_date,
  date_add(date_sub(current_date(), recency_days + k * 35 + CAST(pmod(hash(id, k, 'j'), 20) AS INT)),
    CASE WHEN pmod(hash(id, k, 'l'), 10) < 3 THEN 10 + CAST(pmod(hash(id, k, 'l2'), 15) AS INT) ELSE CAST(pmod(hash(id, k, 'l2'), 4) AS INT) END) AS invoice_date,
  CAST(round((800 + pmod(hash(id, k, 'a'), 9000)) * size_mult, 2) AS DECIMAL(12,2)) AS amount_usd,
  CASE WHEN pmod(hash(id, k, 's'), 100) < 8 THEN 'refunded' WHEN pmod(hash(id, k, 's'), 100) < 12 THEN 'cancelled' ELSE 'completed' END AS status,
  CASE WHEN pmod(hash(id, k, 'p'), 100) < 40 THEN 'Subscription' WHEN pmod(hash(id, k, 'p'), 100) < 55 THEN 'Support plan'
       WHEN pmod(hash(id, k, 'p'), 100) < 80 THEN 'Services' ELSE 'Hardware' END AS product_line
FROM exploded"""]
