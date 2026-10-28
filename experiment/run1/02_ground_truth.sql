-- =====================================================================
-- Ground truth: the business owner's intended definitions, written as SQL.
-- Lives in workspace.sales_answers. NEVER attach this schema to a Genie agent.
-- Run on the same day as the Genie questions.
-- =====================================================================
USE CATALOG workspace;

-- Customer-level status under the owner's full definitions
CREATE OR REPLACE VIEW sales_answers.customer_truth AS
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

-- ---------------------------------------------------------------------
-- Answers to the 20 test questions (ids match questions.csv)
-- ---------------------------------------------------------------------
-- A1 How many active customers do we have?
SELECT 'A1' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE is_active;
-- A2 How many active customers are in EMEA?
SELECT 'A2' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE is_active AND region = 'EMEA';
-- A3 Show active customers by region.
SELECT 'A3' AS q, region, count(*) AS active_customers FROM sales_answers.customer_truth WHERE is_active GROUP BY region ORDER BY region;
-- A4 How many customers in North America are currently active?
SELECT 'A4' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE is_active AND region = 'North America';
-- A5 What percentage of our customers are active? (denominator: non-internal customers)
SELECT 'A5' AS q, round(100.0 * count_if(is_active) / count_if(NOT is_internal), 1) AS pct_active FROM sales_answers.customer_truth;
-- A6 List the active customers in LATAM. (score the number of rows returned)
SELECT 'A6' AS q, count(*) AS rows_expected FROM sales_answers.customer_truth WHERE is_active AND region = 'LATAM';
-- A7 How many active customers are billed in Germany?
SELECT 'A7' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE is_active AND billing_country = 'Germany';
-- C1 How many churned customers do we have?
SELECT 'C1' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE is_churned;
-- C2 Show churned customers by region.
SELECT 'C2' AS q, region, count(*) AS churned_customers FROM sales_answers.customer_truth WHERE is_churned GROUP BY region ORDER BY region;
-- C3 How many customers in EMEA have churned?
SELECT 'C3' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE is_churned AND region = 'EMEA';
-- C4 How many customers have we lost recently? (intended meaning: churned)
SELECT 'C4' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE is_churned;
-- C5 Which region has the most churned customers?
SELECT 'C5' AS q, region, count(*) AS churned_customers FROM sales_answers.customer_truth WHERE is_churned GROUP BY region ORDER BY churned_customers DESC LIMIT 1;
-- C6 How many large companies have churned?
SELECT 'C6' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE is_churned AND company_size = 'Large';
-- E1 How many enterprise accounts do we have?
SELECT 'E1' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE is_enterprise;
-- E2 Show enterprise accounts by region.
SELECT 'E2' AS q, region, count(*) AS enterprise_accounts FROM sales_answers.customer_truth WHERE is_enterprise GROUP BY region ORDER BY region;
-- E3 How many enterprise accounts are in APAC?
SELECT 'E3' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE is_enterprise AND region = 'APAC';
-- E4 Which region has the most enterprise accounts?
SELECT 'E4' AS q, region, count(*) AS enterprise_accounts FROM sales_answers.customer_truth WHERE is_enterprise GROUP BY region ORDER BY enterprise_accounts DESC LIMIT 1;
-- E5 How many enterprise accounts are currently active?
SELECT 'E5' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE is_enterprise AND is_active;
-- E6 How many mid-market companies are enterprise accounts?
SELECT 'E6' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE is_enterprise AND company_size = 'Mid-market';
-- X1 How many customers are neither active nor churned? (excluding internal test accounts)
SELECT 'X1' AS q, count(*) AS answer FROM sales_answers.customer_truth WHERE NOT is_internal AND NOT is_active AND NOT is_churned;

-- ---------------------------------------------------------------------
-- Trap check: how far apart are the "wrong but plausible" readings?
-- If these numbers are close to the truth, the dataset isn't stressing Genie.
-- ---------------------------------------------------------------------
SELECT
  count_if(is_active) AS truth_active,
  -- wrong reading 1: order_date instead of invoice_date
  (SELECT count(DISTINCT o.customer_id) FROM sales.orders o JOIN sales.customers c USING (customer_id)
    WHERE NOT c.is_internal AND o.status = 'completed' AND o.order_date >= date_sub(current_date(), 90)) AS using_order_date,
  -- wrong reading 2: any status (includes refunded / cancelled)
  (SELECT count(DISTINCT o.customer_id) FROM sales.orders o JOIN sales.customers c USING (customer_id)
    WHERE NOT c.is_internal AND o.invoice_date >= date_sub(current_date(), 90)) AS any_status,
  -- wrong reading 3: forgets to exclude internal accounts
  (SELECT count(DISTINCT o.customer_id) FROM sales.orders o
    WHERE o.status = 'completed' AND o.invoice_date >= date_sub(current_date(), 90)) AS includes_internal
FROM sales_answers.customer_truth;
