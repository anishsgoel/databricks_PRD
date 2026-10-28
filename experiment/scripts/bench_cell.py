import json, uuid
from databricks.sdk import WorkspaceClient
api = WorkspaceClient().api_client
BENCH = [
  ('How many active customers do we have?', "SELECT COUNT(DISTINCT o.customer_id) AS active_customers FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal AND o.invoice_date >= date_sub(current_date(), 90)"),
  ('How many active customers are in EMEA?', "SELECT COUNT(DISTINCT o.customer_id) AS active_customers FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal AND c.region = 'EMEA' AND o.invoice_date >= date_sub(current_date(), 90)"),
  ('How many churned customers do we have?', "WITH last AS (SELECT o.customer_id, MAX(o.invoice_date) AS last_billed FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal GROUP BY o.customer_id) SELECT COUNT(*) AS churned_customers FROM last WHERE last_billed < date_sub(current_date(), 90) AND last_billed >= date_sub(current_date(), 180)"),
  ('How many customers have we lost recently?', "WITH last AS (SELECT o.customer_id, MAX(o.invoice_date) AS last_billed FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal GROUP BY o.customer_id) SELECT COUNT(*) AS churned_customers FROM last WHERE last_billed < date_sub(current_date(), 90) AND last_billed >= date_sub(current_date(), 180)"),
  ('How many enterprise accounts do we have?', "WITH s AS (SELECT o.customer_id, SUM(o.amount_usd) AS spend FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal AND o.invoice_date >= date_sub(current_date(), 365) GROUP BY o.customer_id) SELECT COUNT(*) AS enterprise_accounts FROM s WHERE spend >= 50000"),
  ('How many enterprise accounts are in APAC?', "WITH s AS (SELECT o.customer_id, SUM(o.amount_usd) AS spend FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal AND o.invoice_date >= date_sub(current_date(), 365) AND c.region = 'APAC' GROUP BY o.customer_id) SELECT COUNT(*) AS enterprise_accounts FROM s WHERE spend >= 50000"),
  ('What was our revenue in the last 12 months?', "SELECT SUM(o.amount_usd) AS revenue FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal AND o.invoice_date >= date_sub(current_date(), 365)"),
  ('How much did we make in the last 12 months?', "SELECT SUM(o.amount_usd) AS revenue FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal AND o.invoice_date >= date_sub(current_date(), 365)"),
  ('What was our recurring revenue in the last 12 months?', "SELECT SUM(o.amount_usd) AS recurring_revenue FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal AND o.product_line IN ('Subscription', 'Support plan') AND o.invoice_date >= date_sub(current_date(), 365)"),
  ('How much recurring revenue came from EMEA in the last 12 months?', "SELECT SUM(o.amount_usd) AS recurring_revenue FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal AND c.region = 'EMEA' AND o.product_line IN ('Subscription', 'Support plan') AND o.invoice_date >= date_sub(current_date(), 365)"),
  ('What is our revenue so far this fiscal year?', "SELECT SUM(o.amount_usd) AS revenue FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal AND o.invoice_date >= DATE'2026-02-01' AND o.invoice_date <= current_date()"),
  ('What was revenue last fiscal quarter?', "SELECT SUM(o.amount_usd) AS revenue FROM workspace.sales2.orders o JOIN workspace.sales2.customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND NOT c.is_internal AND o.invoice_date >= DATE'2026-05-01' AND o.invoice_date < DATE'2026-08-01'")
]
SPACES = {"C1": "01f1d291fd5415d98301c67eebe87489", "C3": "01f1d291fd9617eab34e958f469b876a", "C4": "01f1d291fdbc173b8dc2ed49bb23bdf5"}
for c, sid in SPACES.items():
    r = api.do("GET", f"/api/2.0/genie/spaces/{sid}", query={"include_serialized_space": "true"})
    ser = json.loads(r["serialized_space"])
    ser["benchmarks"] = {"questions": [{"id": uuid.uuid4().hex, "question": [q], "answer": [{"format": "SQL", "content": [sql]}]} for q, sql in BENCH]}
    try:
        api.do("PATCH", f"/api/2.0/genie/spaces/{sid}", body={"serialized_space": json.dumps(ser)})
        r2 = api.do("GET", f"/api/2.0/genie/spaces/{sid}", query={"include_serialized_space": "true"})
        print(c, "BENCHMARKS NOW", len(json.loads(r2["serialized_space"]).get("benchmarks", {}).get("questions", [])))
    except Exception as e:
        print(c, "FAILED", str(e)[:400])
for q, sql in BENCH:
    print("GT", q, spark.sql(sql).collect()[0][0])
