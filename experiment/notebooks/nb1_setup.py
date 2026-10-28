# Databricks notebook source
# MAGIC %md
# MAGIC # Ask the Owner experiment v2, notebook 1: data, answer key, agents
# MAGIC Creates `workspace.sales2` (attach to agents), `workspace.sales2_answers` (never attach), and four Genie agents C1-C4.
# MAGIC Run all cells top to bottom. Safe to re-run.

# COMMAND ----------

SCHEMA = "workspace.sales2"
ANSWERS = "workspace.sales2_answers"
AGENTS = {
    "C1": "v2 C1 - one-line definitions",
    "C2": "v2 C2 - one-liners + ask the user",
    "C3": "v2 C3 - improved by analyst",
    "C4": "v2 C4 - improved by owner",
}

# COMMAND ----------

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

spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.sales2")
spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.sales2_answers")
for st in setup_statements(SCHEMA):
    spark.sql(st)
display(spark.sql(f"""SELECT (SELECT count(*) FROM {SCHEMA}.customers) customers,
  (SELECT count(*) FROM {SCHEMA}.customers WHERE is_internal) internal_accounts,
  (SELECT count(*) FROM {SCHEMA}.orders) orders,
  (SELECT count(*) FROM {SCHEMA}.orders WHERE status <> 'completed') refunded_or_cancelled,
  (SELECT count(*) FROM {SCHEMA}.orders WHERE datediff(invoice_date, order_date) >= 10) late_invoices"""))

# COMMAND ----------

# ===== Experiment v2 core: definitions, questions, answer key, scoring =====
import re, json, datetime as _dt
import pandas as pd

# ---------- Definitions ----------
OWNER_DEFINITIONS = """Business definitions (confirmed by Sales Ops and Finance):
- Active customer: a customer with at least one completed order billed (invoice_date) in the last 90 days. Refunded and cancelled orders never count. Internal test accounts (is_internal = true) are never customers.
- Churned customer (lost): a customer whose most recent completed order was billed 91 to 180 days ago, with no completed order billed since. Customers who left longer ago are not counted. Exclude internal test accounts.
- Enterprise account: a customer with $50,000 or more of completed orders billed in the last 365 days. Exclude internal test accounts.
- Revenue: the sum of amount_usd for completed orders, recognized on invoice_date. Refunded and cancelled orders are not revenue. Internal test accounts are excluded.
- Recurring revenue: revenue from the Subscription and Support plan product lines.
- Fiscal year: starts February 1. Q1 = Feb-Apr, Q2 = May-Jul, Q3 = Aug-Oct, Q4 = Nov-Jan. Fiscal periods use invoice_date.
- Time periods (last 12 months, a calendar month) use invoice_date."""

ONE_LINERS = """Business definitions from Sales Ops and Finance:
- Active customer: bought in the last 90 days.
- Churned customer: a customer we lost.
- Enterprise account: spends $50K or more a year.
- Revenue: total sales.
- Recurring revenue: revenue from subscriptions.
- Our fiscal year starts in February."""

ASK_FIRST_RULE = """

If a question uses a business term in a way that could mean more than one thing (for example revenue, recurring revenue, active, churned, enterprise, fiscal periods), ask the user which definition they mean before answering. Do not assume."""

# What an analyst would plausibly answer to Improve with Genie's questions (written before any run)
ANALYST_SHEET = {
    "date": "Use order_date (when the customer bought).",
    "refunds": "Only completed orders count; exclude refunded and cancelled.",
    "tests": "Exclude internal test accounts.",
    "churn": "Churned = no completed order in the last 90 days (any time before that).",
    "enterprise": "Enterprise = $50,000+ of completed orders in the last 365 days by order_date.",
    "recurring": "Recurring revenue = Subscription product line only.",
    "fiscal": "Fiscal year starts Feb 1; use order_date.",
    "revenue": "Revenue = amount_usd of completed orders by order_date.",
}
OWNER_SHEET = {
    "date": "Use invoice_date (when the order was billed).",
    "refunds": "Only completed orders count; refunded and cancelled never count.",
    "tests": "Exclude internal test accounts everywhere.",
    "churn": "Churned = last completed order billed 91-180 days ago; older leavers are not counted.",
    "enterprise": "Enterprise = $50,000+ of completed orders billed in the last 365 days.",
    "recurring": "Recurring revenue = Subscription and Support plan product lines.",
    "fiscal": "Fiscal year starts Feb 1; fiscal periods use invoice_date.",
    "revenue": "Revenue = amount_usd of completed orders, recognized on invoice_date.",
}

# ---------- Questions (written before any run) ----------
# kind: scalar | by_region | top_region | pct
QUESTIONS = [
 ("A1","active","scalar","How many active customers do we have?"),
 ("A2","active","scalar","How many active customers are in EMEA?"),
 ("A3","active","by_region","Show active customers by region."),
 ("A4","active","pct","What percentage of our customers are active?"),
 ("A5","active","scalar","How many large companies are active customers?"),
 ("A6","active","top_region","Which region has the most active customers?"),
 ("A7","active","scalar","How many mid-market customers are active?"),
 ("A8","active","scalar","How many active customers are in APAC?"),
 ("C1","churn","scalar","How many churned customers do we have?"),
 ("C2","churn","by_region","Show churned customers by region."),
 ("C3","churn","scalar","How many customers in EMEA have churned?"),
 ("C4","churn","scalar","How many customers have we lost recently?"),
 ("C5","churn","top_region","Which region has the most churned customers?"),
 ("C6","churn","scalar","How many large companies have churned?"),
 ("C7","churn","pct","What percentage of our customers have churned?"),
 ("C8","churn","scalar","How many customers in APAC have churned?"),
 ("E1","enterprise","scalar","How many enterprise accounts do we have?"),
 ("E2","enterprise","by_region","Show enterprise accounts by region."),
 ("E3","enterprise","scalar","How many enterprise accounts are in APAC?"),
 ("E4","enterprise","top_region","Which region has the most enterprise accounts?"),
 ("E5","enterprise","scalar","How many enterprise accounts are currently active?"),
 ("E6","enterprise","scalar","How many mid-market companies are enterprise accounts?"),
 ("E7","enterprise","pct","What percentage of our customers are enterprise accounts?"),
 ("E8","enterprise","scalar","How many enterprise accounts are in North America?"),
 ("R1","revenue","scalar","What was our revenue in the last 12 months?"),
 ("R2","revenue","by_region","Show revenue by region for the last 12 months."),
 ("R3","revenue","scalar","How much revenue came from EMEA in the last 12 months?"),
 ("R4","revenue","top_region","Which region generated the most revenue in the last 12 months?"),
 ("R5","revenue","scalar","What was revenue from large companies in the last 12 months?"),
 ("R6","revenue","scalar","What was our revenue in September 2026?"),
 ("R7","revenue","pct","What share of revenue in the last 12 months came from APAC?"),
 ("R8","revenue","scalar","How much did we make in the last 12 months?"),
 ("RR1","recurring","scalar","What was our recurring revenue in the last 12 months?"),
 ("RR2","recurring","by_region","Show recurring revenue by region for the last 12 months."),
 ("RR3","recurring","scalar","How much recurring revenue came from EMEA in the last 12 months?"),
 ("RR4","recurring","top_region","Which region had the most recurring revenue in the last 12 months?"),
 ("RR5","recurring","pct","What share of revenue in the last 12 months was recurring?"),
 ("RR6","recurring","scalar","What was recurring revenue from large companies in the last 12 months?"),
 ("RR7","recurring","scalar","What was our recurring revenue in September 2026?"),
 ("RR8","recurring","scalar","How much recurring revenue came from North America in the last 12 months?"),
 ("F1","fiscal","scalar","What is our revenue so far this fiscal year?"),
 ("F2","fiscal","scalar","What was revenue last fiscal quarter?"),
 ("F3","fiscal","by_region","Show revenue by region for this fiscal year so far."),
 ("F4","fiscal","scalar","How much revenue came from EMEA this fiscal year?"),
 ("F5","fiscal","scalar","What is our recurring revenue this fiscal year so far?"),
 ("F6","fiscal","top_region","Which region has the most revenue this fiscal year?"),
 ("F7","fiscal","scalar","What was revenue in the first quarter of this fiscal year?"),
 ("F8","fiscal","scalar","What was revenue from large companies this fiscal year so far?"),
]
Q = {q[0]: q for q in QUESTIONS}
PAGES_SUBSET = ["A1","A6","C1","C4","E1","E3","R1","R8","RR1","RR5","F1","F2"]
REGIONS = ["North America","EMEA","APAC","LATAM"]

# ---------- Variants ----------
OWNER = dict(date="invoice", status="completed", tests="excluded", churn="91-180", lines="sub+support", fy="feb")
ANALYST = dict(date="order", status="completed", tests="excluded", churn="90+", lines="sub", fy="feb")
def all_variants(term):
    out = []
    for d in ("invoice","order"):
        for s in ("completed","all"):
            for t in ("excluded","included"):
                base = dict(date=d, status=s, tests=t, churn="91-180", lines="sub+support", fy="feb")
                if term == "churn":
                    for c in ("91-180","90+"): out.append({**base, "churn": c})
                elif term in ("recurring",):
                    for l in ("sub+support","sub"): out.append({**base, "lines": l})
                elif term == "fiscal":
                    for f in ("feb","jan"):
                        for l in ("sub+support","sub"): out.append({**base, "fy": f, "lines": l})
                else:
                    out.append(base)
    return out
def vkey(p, term):
    k = f"{p['date']}|{p['status']}|tests-{p['tests']}"
    if term == "churn": k += f"|{p['churn']}"
    if term == "recurring": k += f"|{p['lines']}"
    if term == "fiscal": k += f"|fy-{p['fy']}|{p['lines']}"
    return k

# ---------- Answer computation (pandas) ----------
def _filt(orders, customers, p):
    o = orders.merge(customers[["customer_id","region","company_size","is_internal"]], on="customer_id")
    if p["status"] == "completed": o = o[o.status == "completed"]
    if p["tests"] == "excluded": o = o[~o.is_internal.astype(bool)]
    o = o.copy(); o["d"] = pd.to_datetime(o.invoice_date if p["date"] == "invoice" else o.order_date)
    return o
def _cust(customers, p):
    c = customers
    if p["tests"] == "excluded": c = c[~c.is_internal.astype(bool)]
    return c

def answer(qid, p, orders, customers, today):
    _, term, kind, text = Q[qid]
    today = pd.Timestamp(today)
    o = _filt(orders, customers, p); c = _cust(customers, p)
    d90, d180, d365 = today - pd.Timedelta(days=90), today - pd.Timedelta(days=180), today - pd.Timedelta(days=365)
    def active_ids(): return set(o[o.d >= d90].customer_id)
    def churn_ids():
        last = o.groupby("customer_id").d.max()
        m = last < d90
        if p["churn"] == "91-180": m &= last >= d180
        return set(last[m].index)
    def ent_ids():
        s = o[o.d >= d365].groupby("customer_id").amount_usd.sum()
        return set(s[s >= 50000].index)
    fy_year = today.year if today.month >= 2 else today.year - 1
    fy_start = pd.Timestamp(fy_year, 2 if p.get("fy","feb") == "feb" else 1, 1)
    def fq_bounds(n):  # fiscal quarter n (1-4) of current FY
        s = fy_start + pd.DateOffset(months=3*(n-1)); return s, s + pd.DateOffset(months=3)
    def rev(df): return float(df.amount_usd.sum())
    lines = {"sub+support": {"Subscription","Support plan"}, "sub": {"Subscription"}}[p.get("lines","sub+support")]
    cmeta = customers.set_index("customer_id")
    def count_by(ids, col, val): return sum(1 for i in ids if cmeta.loc[i, col] == val)
    if term in ("active","churn","enterprise"):
        ids = {"active": active_ids, "churn": churn_ids, "enterprise": ent_ids}[term]()
        if qid == "E5": ids = ids & active_ids()
        if kind == "scalar":
            if "EMEA" in text: return count_by(ids, "region", "EMEA")
            if "APAC" in text: return count_by(ids, "region", "APAC")
            if "North America" in text: return count_by(ids, "region", "North America")
            if "large" in text: return count_by(ids, "company_size", "Large")
            if "mid-market" in text: return count_by(ids, "company_size", "Mid-market")
            return len(ids)
        if kind == "by_region": return {r: count_by(ids, "region", r) for r in REGIONS}
        if kind == "top_region":
            br = {r: count_by(ids, "region", r) for r in REGIONS}; return max(br, key=br.get)
        if kind == "pct": return round(100.0 * len(ids) / len(c), 2)
    # revenue terms
    if term == "revenue" or term == "recurring":
        w = o[o.d >= d365] if "12 months" in text else o[(o.d >= "2026-09-01") & (o.d < "2026-10-01")]
        if qid == "RR5":
            return round(100.0 * rev(w[w.product_line.isin(lines)]) / rev(w), 2)
        if term == "recurring": w = w[w.product_line.isin(lines)]
    if term == "fiscal":
        if qid == "F2":
            # last completed fiscal quarter
            cur_n = ((today.year - fy_start.year) * 12 + today.month - fy_start.month) // 3 + 1
            s, e = fq_bounds(cur_n - 1) if cur_n > 1 else (fy_start - pd.DateOffset(months=3), fy_start)
            w = o[(o.d >= s) & (o.d < e)]
        elif qid == "F7":
            s, e = fq_bounds(1); w = o[(o.d >= s) & (o.d < e)]
        else:
            w = o[(o.d >= fy_start) & (o.d <= today)]
        if qid == "F5": w = w[w.product_line.isin(lines)]
    if kind == "scalar":
        if "EMEA" in text: w = w[w.region == "EMEA"]
        if "North America" in text: w = w[w.region == "North America"]
        if "large" in text: w = w[w.company_size == "Large"]
        return round(rev(w), 2)
    if kind == "by_region": return {r: round(rev(w[w.region == r]), 2) for r in REGIONS}
    if kind == "top_region":
        br = {r: rev(w[w.region == r]) for r in REGIONS}; return max(br, key=br.get)
    if kind == "pct": return round(100.0 * rev(w[w.region == "APAC"]) / rev(w), 2)
    raise ValueError(qid)

def answer_key(orders, customers, today):
    rows = []
    for qid, term, kind, text in QUESTIONS:
        seen = {}
        for p in all_variants(term):
            k = vkey(p, term)
            if k in seen: continue
            a = answer(qid, p, orders, customers, today); seen[k] = 1
            rows.append(dict(qid=qid, term=term, kind=kind, variant=k,
                             is_owner=(vkey(p, term) == vkey(OWNER, term)),
                             is_analyst=(vkey(p, term) == vkey(ANALYST, term)),
                             answer=json.dumps(a)))
    return pd.DataFrame(rows)

# ---------- Scoring ----------
def _nums(rows):
    out = []
    for r in rows or []:
        for v in (r if isinstance(r, list) else [r]):
            try: out.append(float(str(v).replace(",", "")))
            except Exception: pass
    return out
def _close(a, b, tol=0.005):
    return abs(a - b) <= max(tol * abs(b), 0.5 if abs(b) < 1000 else 1.0)
def matches(kind, ans, rows, text):
    if kind in ("scalar",):
        return any(_close(x, ans) for x in _nums(rows))
    if kind == "pct":
        return any(_close(x, ans, 0.01) or _close(x * 100, ans, 0.01) for x in _nums(rows))
    if kind == "top_region":
        blob = json.dumps(rows) if rows else ""
        first = json.dumps(rows[0]) if rows else ""
        return (ans in first) or (not rows and ans in (text or ""))
    if kind == "by_region":
        if not rows: return False
        got = {}
        for r in rows:
            r = r if isinstance(r, list) else [r]
            reg = next((x for x in r if x in REGIONS), None)
            nums = _nums([r])
            if reg and nums: got[reg] = nums
        return all(reg in got and any(_close(x, v) for x in got[reg]) for reg, v in ans.items())
    return False

def score(run_rows, key_df):
    """run_rows: list of dicts with qid, result_rows (list), response_text. Adds correct + matched_variant."""
    out = []
    for r in run_rows:
        k = key_df[key_df.qid == r["qid"]]
        kind = k.kind.iloc[0]
        rows = r.get("result_rows_parsed")
        own = json.loads(k[k.is_owner].answer.iloc[0])
        ok = matches(kind, own, rows, r.get("response_text"))
        matched = [v for v, a in zip(k.variant, k.answer) if matches(kind, json.loads(a), rows, r.get("response_text"))]
        # percent off for scalar questions, using Genie's first number
        pct_off = None
        if kind == "scalar" and not ok:
            n = _nums(rows)
            if n: pct_off = round(100.0 * (n[0] - own) / own, 1) if own else None
        out.append({**r, "correct": ok, "owner_answer": json.dumps(own), "matched_variants": "; ".join(matched), "pct_off": pct_off})
    return out


# COMMAND ----------

import datetime
orders = spark.table(f"{SCHEMA}.orders").toPandas(); customers = spark.table(f"{SCHEMA}.customers").toPandas()
orders["amount_usd"] = orders.amount_usd.astype(float)
key = answer_key(orders, customers, datetime.date.today())
spark.createDataFrame(key.astype(str)).write.mode("overwrite").option("overwriteSchema","true").saveAsTable(f"{ANSWERS}.answer_key")
print("answer key rows:", len(key))
display(key[key.is_owner | key.is_analyst])

# COMMAND ----------

# Create (or update) the four agents through the Genie API, copying the format of an existing agent.
import json, uuid
from databricks.sdk import WorkspaceClient
w = WorkspaceClient(); api = w.api_client

def list_spaces():
    out, tok = [], None
    while True:
        r = api.do("GET", "/api/2.0/genie/spaces", query={"page_size": 100, **({"page_token": tok} if tok else {})})
        out += r.get("spaces", []); tok = r.get("next_page_token")
        if not tok: return out

spaces = list_spaces()
template = next(s for s in spaces if s.get("title") == "V - vague text")
tpl = api.do("GET", f"/api/2.0/genie/spaces/{template['space_id']}", query={"include_serialized_space": "true"})
ser = json.loads(tpl["serialized_space"])
print("template keys:", list(tpl.keys()))
print("serialized keys:", json.dumps({k: (list(v.keys()) if isinstance(v, dict) else type(v).__name__) for k, v in ser.items()}))
WAREHOUSE = tpl.get("warehouse_id")

def build(instructions):
    s = json.loads(json.dumps(ser))
    s.setdefault("data_sources", {})["tables"] = [{"identifier": f"{SCHEMA}.customers"}, {"identifier": f"{SCHEMA}.orders"}]
    ins = s.setdefault("instructions", {})
    ins["text_instructions"] = [{"id": uuid.uuid4().hex, "content": [instructions]}]
    for k in ("example_question_sqls", "sql_functions", "join_specs", "sql_snippets"):
        if k in ins: ins[k] = []
    if "config" in s and isinstance(s["config"], dict): s["config"]["sample_questions"] = []
    return json.dumps(s)

TEXT = {"C1": ONE_LINERS, "C2": ONE_LINERS + ASK_FIRST_RULE, "C3": ONE_LINERS, "C4": ONE_LINERS}
by_title = {s.get("title"): s.get("space_id") for s in spaces}
created = {}
for cid, title in AGENTS.items():
    body = {"title": title, "description": f"Ask the Owner experiment v2, condition {cid}", "warehouse_id": WAREHOUSE, "serialized_space": build(TEXT[cid])}
    try:
        if title in by_title:
            sid = by_title[title]
            if cid in ("C3", "C4"):
                print(cid, "exists, left unchanged (it holds Improve with Genie edits):", sid); created[cid] = sid; continue
            api.do("PATCH", f"/api/2.0/genie/spaces/{sid}", body=body); created[cid] = sid; print(cid, "updated", sid)
        else:
            r = api.do("POST", "/api/2.0/genie/spaces", body=body); created[cid] = r.get("space_id"); print(cid, "created", created[cid])
    except Exception as e:
        print(cid, "FAILED:", str(e)[:500])
host = spark.conf.get("spark.databricks.workspaceUrl", "")
for cid, sid in created.items():
    print(cid, AGENTS[cid], f"https://{host}/genie/rooms/{sid}")
