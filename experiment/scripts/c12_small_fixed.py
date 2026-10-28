SCHEMA = "workspace.sales2"; ANSWERS = "workspace.sales2_answers"
AGENTS = {"C1": "v2 C1 - one-line definitions", "C2": "v2 C2 - one-liners + ask the user",
          "C3": "v2 C3 - improved by analyst", "C4": "v2 C4 - improved by owner"}
RUNS = [1, 2]
SECONDS_BETWEEN = 13
MAX_WAIT = 240
UNSURE_REPLY = "I'm not sure which one. Just use our standard definition."
ONLY = ["C1","C2"]


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

import time, json, datetime
from databricks.sdk import WorkspaceClient
w = WorkspaceClient(); api = w.api_client
spaces, tok = [], None
while True:
    r = api.do("GET", "/api/2.0/genie/spaces", query={"page_size": 100, **({"page_token": tok} if tok else {})})
    spaces += r.get("spaces", []); tok = r.get("next_page_token")
    if not tok: break
by_title = {s.get("title"): s.get("space_id") for s in spaces}
SPACE = {c: by_title[t] for c, t in AGENTS.items()}
print(SPACE)

def wait_msg(sid, conv, mid):
    t0 = time.time()
    while True:
        m = api.do("GET", f"/api/2.0/genie/spaces/{sid}/conversations/{conv}/messages/{mid}")
        if m.get("status") in ("COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"): return m
        if time.time() - t0 > MAX_WAIT: m["status"] = "TIMEOUT"; return m
        time.sleep(3)

def read(sid, conv, mid, m):
    text, sql, rows, cols = [], None, None, None
    for att in m.get("attachments", []) or []:
        if att.get("text"): text.append(att["text"].get("content", ""))
        if att.get("query"):
            sql = att["query"].get("query"); aid = att.get("attachment_id") or att.get("id")
            try:
                qr = api.do("GET", f"/api/2.0/genie/spaces/{sid}/conversations/{conv}/messages/{mid}/attachments/{aid}/query-result")
                sr = qr.get("statement_response", {})
                cols = [c.get("name") for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
                rows = sr.get("result", {}).get("data_array")
            except Exception as e:
                rows = None
    return "\n".join(t for t in text if t), sql, rows, cols

def ask(sid, question):
    st = api.do("POST", f"/api/2.0/genie/spaces/{sid}/start-conversation", body={"content": question})
    conv = st.get("conversation_id") or st.get("conversation", {}).get("id")
    mid = st.get("message_id") or st.get("message", {}).get("id") or st.get("message", {}).get("message_id")
    m = wait_msg(sid, conv, mid); text, sql, rows, cols = read(sid, conv, mid, m)
    first_text, asked = text, (sql is None and text.strip().endswith("?"))
    if asked:   # the person typing doesn't know the rule
        r2 = api.do("POST", f"/api/2.0/genie/spaces/{sid}/conversations/{conv}/messages", body={"content": UNSURE_REPLY})
        mid2 = r2.get("message_id") or r2.get("id") or r2.get("message", {}).get("id")
        m = wait_msg(sid, conv, mid2); text, sql, rows, cols = read(sid, conv, mid2, m)
    return dict(status=m.get("status"), conversation_id=conv, asked_first=asked, first_text=first_text[:2000],
                response_text=(text or "")[:4000], sql=sql, result_columns=json.dumps(cols), result_rows=json.dumps(rows)[:20000] if rows is not None else None)


RAW = f"{ANSWERS}.runs_raw"
try: done = {(r.condition, r.qid, int(r.run)) for r in spark.table(RAW).select("condition","qid","run").collect()}
except Exception: done = set()
plan = [(c, q[0], q[3], n) for n in RUNS for q in QUESTIONS for c in AGENTS if (ONLY is None or c in ONLY)]
todo = [p for p in plan if (p[0], p[1], p[3]) not in done]
print(f"{len(done)} done, {len(todo)} to go")
for i, (c, qid, text, n) in enumerate(todo, 1):
    t0 = time.time()
    try:
        out = ask(SPACE[c], text)
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "rate" in str(e).lower():
            print("  rate limited; waiting 60s"); time.sleep(60)
            try: out = ask(SPACE[c], text)
            except Exception as e2: out = dict(status="ERROR", response_text=str(e2)[:2000])
        else:
            out = dict(status="ERROR", response_text=str(e)[:2000])
    row = dict(condition=c, qid=qid, question=text, run=n, asked_at=datetime.datetime.now().isoformat(timespec="seconds"), **out)
    from pyspark.sql.types import StructType, StructField, StringType
    _schema = StructType([StructField(k, StringType(), True) for k in row])
    try:
        spark.createDataFrame([[None if v is None else str(v) for v in row.values()]], _schema).write.mode("append").option("mergeSchema","true").saveAsTable(RAW)
    except Exception as e:
        print("  save failed:", str(e)[:200])
    print(f"[{i}/{len(todo)}] {c} {qid} run {n}: {out.get('status')} asked_first={out.get('asked_first')} ({time.time()-t0:.0f}s)")
    time.sleep(SECONDS_BETWEEN)


