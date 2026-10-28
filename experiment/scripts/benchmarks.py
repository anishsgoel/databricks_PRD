# Owner ground-truth SQL for the benchmark subset (sales2). Same logic as the answer key.
B = "FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal"
def churn(extra=""):
    return ("WITH last AS (SELECT o.customer_id, MAX(o.invoice_date) AS last_billed " + B + extra +
            " GROUP BY o.customer_id) SELECT COUNT(*) AS churned_customers FROM last "
            "WHERE last_billed < date_sub(current_date(), 90) AND last_billed >= date_sub(current_date(), 180)")
def ent(extra=""):
    return ("WITH s AS (SELECT o.customer_id, SUM(o.amount_usd) AS spend " + B +
            " AND o.invoice_date >= date_sub(current_date(), 365)" + extra +
            " GROUP BY o.customer_id) SELECT COUNT(*) AS enterprise_accounts FROM s WHERE spend >= 50000")
BENCH = [
 ("A1", "How many active customers do we have?", "SELECT COUNT(DISTINCT o.customer_id) AS active_customers " + B + " AND o.invoice_date >= date_sub(current_date(), 90)"),
 ("A2", "How many active customers are in EMEA?", "SELECT COUNT(DISTINCT o.customer_id) AS active_customers " + B + " AND c.region = 'EMEA' AND o.invoice_date >= date_sub(current_date(), 90)"),
 ("C1", "How many churned customers do we have?", churn()),
 ("C4", "How many customers have we lost recently?", churn()),
 ("E1", "How many enterprise accounts do we have?", ent()),
 ("E3", "How many enterprise accounts are in APAC?", ent(" AND c.region = 'APAC'")),
 ("R1", "What was our revenue in the last 12 months?", "SELECT SUM(o.amount_usd) AS revenue " + B + " AND o.invoice_date >= date_sub(current_date(), 365)"),
 ("R8", "How much did we make in the last 12 months?", "SELECT SUM(o.amount_usd) AS revenue " + B + " AND o.invoice_date >= date_sub(current_date(), 365)"),
 ("RR1", "What was our recurring revenue in the last 12 months?", "SELECT SUM(o.amount_usd) AS recurring_revenue " + B + " AND o.product_line IN ('Subscription', 'Support plan') AND o.invoice_date >= date_sub(current_date(), 365)"),
 ("RR3", "How much recurring revenue came from EMEA in the last 12 months?", "SELECT SUM(o.amount_usd) AS recurring_revenue " + B + " AND c.region = 'EMEA' AND o.product_line IN ('Subscription', 'Support plan') AND o.invoice_date >= date_sub(current_date(), 365)"),
 ("F1", "What is our revenue so far this fiscal year?", "SELECT SUM(o.amount_usd) AS revenue " + B + " AND o.invoice_date >= DATE'2026-02-01' AND o.invoice_date <= current_date()"),
 ("F2", "What was revenue last fiscal quarter?", "SELECT SUM(o.amount_usd) AS revenue " + B + " AND o.invoice_date >= DATE'2026-05-01' AND o.invoice_date < DATE'2026-08-01'"),
]
