-- =====================================================================
-- Variant B: the definitions as confirmed SQL.
-- This view stands in for "owner-confirmed SQL" in the experiment.
-- Attach ONLY to the Variant B Genie agent (alongside the two base tables).
-- =====================================================================
USE CATALOG workspace;

CREATE OR REPLACE VIEW sales.customer_segments
COMMENT 'Confirmed business definitions, one row per customer. is_active, is_churned and is_enterprise are signed off by Sales Ops; use these flags for any question about active, churned or enterprise customers.'
AS
SELECT
  c.customer_id, c.customer_name, c.region, c.billing_country, c.company_size, c.is_internal,
  -- Active: not internal, at least one COMPLETED order INVOICED in the last 90 days
  (NOT c.is_internal AND EXISTS (
     SELECT 1 FROM sales.orders o
     WHERE o.customer_id = c.customer_id AND o.status = 'completed'
       AND o.invoice_date >= date_sub(current_date(), 90))) AS is_active,
  -- Churned: not internal, a completed order invoiced 91-180 days ago, none in the last 90
  (NOT c.is_internal
   AND EXISTS (
     SELECT 1 FROM sales.orders o
     WHERE o.customer_id = c.customer_id AND o.status = 'completed'
       AND o.invoice_date <  date_sub(current_date(), 90)
       AND o.invoice_date >= date_sub(current_date(), 180))
   AND NOT EXISTS (
     SELECT 1 FROM sales.orders o
     WHERE o.customer_id = c.customer_id AND o.status = 'completed'
       AND o.invoice_date >= date_sub(current_date(), 90))) AS is_churned,
  -- Enterprise: not internal, completed orders invoiced in the last 365 days total >= $50,000
  (NOT c.is_internal AND COALESCE((
     SELECT sum(o.amount_usd) FROM sales.orders o
     WHERE o.customer_id = c.customer_id AND o.status = 'completed'
       AND o.invoice_date >= date_sub(current_date(), 365)), 0) >= 50000) AS is_enterprise
FROM sales.customers c;
