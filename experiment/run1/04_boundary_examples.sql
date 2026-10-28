-- =====================================================================
-- Boundary examples for the usability test (Experiment 3).
-- Shows customers that a FLAWED draft of "active customer" gets wrong.
-- Flawed draft (two planted errors): uses ORDER date instead of invoice date,
-- and counts orders of ANY status (incl. refunded / cancelled).
-- Pick 8 rows across the buckets below for the example cards.
-- =====================================================================
USE CATALOG workspace;

WITH last_dates AS (
  SELECT
    c.customer_id, c.customer_name, c.region, c.is_internal,
    max(CASE WHEN o.status = 'completed' THEN o.invoice_date END) AS last_completed_invoice,
    max(o.order_date)                                              AS last_order_any_status,
    max(CASE WHEN o.status = 'completed' THEN o.order_date END)   AS last_completed_order
  FROM sales.customers c JOIN sales.orders o USING (customer_id)
  GROUP BY ALL
),
flags AS (
  SELECT *,
    datediff(current_date(), last_completed_invoice) AS days_since_completed_invoice,
    datediff(current_date(), last_order_any_status)  AS days_since_any_order,
    (NOT is_internal AND last_completed_invoice >= date_sub(current_date(), 90)) AS truly_active,
    (NOT is_internal AND last_order_any_status  >= date_sub(current_date(), 90)) AS draft_says_active
  FROM last_dates
),
bucketed AS (
SELECT
  CASE
    WHEN truly_active AND draft_says_active AND days_since_completed_invoice < 40 THEN '1 clearly active (both agree)'
    WHEN truly_active AND NOT draft_says_active                                      THEN '2 late invoice: truly active, draft misses it'
    WHEN NOT truly_active AND draft_says_active AND NOT is_internal                  THEN '3 refunded/cancelled only: draft wrongly includes'
    WHEN is_internal AND last_completed_invoice >= date_sub(current_date(), 90)      THEN '4 internal test account (both exclude)'
    WHEN NOT truly_active AND NOT draft_says_active AND days_since_any_order BETWEEN 91 AND 110 THEN '5 just outside 90 days (both exclude)'
  END AS bucket,
  customer_name, region,
  days_since_completed_invoice, days_since_any_order,
  truly_active, draft_says_active, customer_id
FROM flags
)
SELECT bucket, customer_name, region, days_since_completed_invoice, days_since_any_order, truly_active, draft_says_active
FROM bucketed
WHERE bucket IS NOT NULL
QUALIFY row_number() OVER (PARTITION BY bucket ORDER BY customer_id) <= 3
ORDER BY bucket, customer_name;
