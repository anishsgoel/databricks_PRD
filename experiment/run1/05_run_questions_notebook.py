# Databricks notebook: run the experiment questions through the Genie Conversation API
# --------------------------------------------------------------------------------
# How to use:
#   1. Sidebar -> Workspace -> Create -> Notebook (Python, serverless).
#   2. Paste this whole file into one cell and run it.
#   3. Results land in the table workspace.sales_answers.genie_runs and are shown at the end.
#      Use the download button under the final table to save a CSV, and send it to Claude for scoring.
#
# Each question starts a NEW conversation, in standard chat mode (the API default).
# Free Edition limits the API to roughly 5 questions per minute, so this paces itself.
# Expect about 12-15 minutes for all 51 runs.

import time, json
from databricks.sdk import WorkspaceClient

# ---- 1. Agent titles: must match the titles in Genie exactly ----
AGENT_TITLES = {
    "A": "A - text definitions",
    "B": "B - confirmed sql",
    "V": "V - vague text",
}

QUESTIONS = [
    ("A1", "How many active customers do we have?"),
    ("A2", "How many active customers are in EMEA?"),
    ("A3", "Show active customers by region."),
    ("A4", "How many customers in North America are currently active?"),
    ("A5", "What percentage of our customers are active?"),
    ("A6", "List the active customers in LATAM."),
    ("A7", "How many active customers are billed in Germany?"),
    ("C1", "How many churned customers do we have?"),
    ("C2", "Show churned customers by region."),
    ("C3", "How many customers in EMEA have churned?"),
    ("C4", "How many customers have we lost recently?"),
    ("C5", "Which region has the most churned customers?"),
    ("C6", "How many large companies have churned?"),
    ("E1", "How many enterprise accounts do we have?"),
    ("E2", "Show enterprise accounts by region."),
    ("E3", "How many enterprise accounts are in APAC?"),
    ("E4", "Which region has the most enterprise accounts?"),
    ("E5", "How many enterprise accounts are currently active?"),
    ("E6", "How many mid-market companies are enterprise accounts?"),
    ("X1", "How many customers are neither active nor churned?"),
]
REPEATS = ["A1", "A5", "C1", "C4", "E1"]          # second run in agent A, for consistency
VAGUE = ["A1", "A2", "C1", "C3", "E1", "E3"]      # asked of agent V

PLAN = ([("A", qid, q, 1) for qid, q in QUESTIONS]
        + [("A", qid, q, 2) for qid, q in QUESTIONS if qid in REPEATS]
        + [("B", qid, q, 1) for qid, q in QUESTIONS]
        + [("V", qid, q, 1) for qid, q in QUESTIONS if qid in VAGUE])

SECONDS_BETWEEN_QUESTIONS = 13   # stays under ~5 questions/minute
MAX_WAIT_SECONDS = 240

w = WorkspaceClient()
api = w.api_client

# ---- 2. Find the agent (space) ids by title ----
spaces, token = [], None
while True:
    resp = api.do("GET", "/api/2.0/genie/spaces", query={"page_size": 100, **({"page_token": token} if token else {})})
    spaces += resp.get("spaces", [])
    token = resp.get("next_page_token")
    if not token:
        break
by_title = {s.get("title"): s.get("space_id") for s in spaces}
SPACE_IDS = {}
for key, title in AGENT_TITLES.items():
    if title not in by_title:
        raise ValueError(f"Couldn't find agent titled '{title}'. Agents found: {list(by_title)}")
    SPACE_IDS[key] = by_title[title]
print("Agents:", SPACE_IDS)

# ---- 3. Ask one question in a fresh conversation ----
def ask(space_id, question):
    start = api.do("POST", f"/api/2.0/genie/spaces/{space_id}/start-conversation", body={"content": question})
    conv_id = start.get("conversation_id") or start.get("conversation", {}).get("id")
    msg_id = start.get("message_id") or start.get("message", {}).get("id") or start.get("message", {}).get("message_id")
    t0 = time.time()
    while True:
        msg = api.do("GET", f"/api/2.0/genie/spaces/{space_id}/conversations/{conv_id}/messages/{msg_id}")
        status = msg.get("status")
        if status in ("COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"):
            break
        if time.time() - t0 > MAX_WAIT_SECONDS:
            status = "TIMEOUT"
            break
        time.sleep(3)

    text_parts, sql, sql_desc, result_cols, result_rows = [], None, None, None, None
    for att in msg.get("attachments", []) or []:
        if att.get("text"):
            text_parts.append(att["text"].get("content", ""))
        if att.get("query"):
            sql = att["query"].get("query")
            sql_desc = att["query"].get("description")
            att_id = att.get("attachment_id") or att.get("id")
            try:
                qr = api.do("GET", f"/api/2.0/genie/spaces/{space_id}/conversations/{conv_id}/messages/{msg_id}/attachments/{att_id}/query-result")
                sr = qr.get("statement_response", {})
                result_cols = [c.get("name") for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
                result_rows = sr.get("result", {}).get("data_array")
            except Exception as e:
                result_rows = f"could not fetch result: {e}"
    text = "\n".join(t for t in text_parts if t)
    asked_clarification = (sql is None) and text.strip().endswith("?")
    return {
        "status": status,
        "conversation_id": conv_id,
        "response_text": text,
        "sql": sql,
        "sql_description": sql_desc,
        "result_columns": json.dumps(result_cols),
        "result_rows": json.dumps(result_rows)[:5000] if result_rows is not None else None,
        "row_count": len(result_rows) if isinstance(result_rows, list) else None,
        "asked_clarification": asked_clarification,
        "error": json.dumps(msg.get("error")) if msg.get("error") else None,
    }

# ---- 4. Run the plan ----
runs = []
for i, (agent, qid, q, run_no) in enumerate(PLAN, start=1):
    print(f"[{i}/{len(PLAN)}] agent {agent} {qid} run {run_no}: {q}")
    try:
        out = ask(SPACE_IDS[agent], q)
    except Exception as e:
        out = {"status": "ERROR", "error": str(e)}
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print("  rate limited, waiting 60s and retrying once")
            time.sleep(60)
            try:
                out = ask(SPACE_IDS[agent], q)
            except Exception as e2:
                out = {"status": "ERROR", "error": str(e2)}
    runs.append({"agent": agent, "question_id": qid, "question": q, "run": run_no, **out})
    print("  ->", out.get("status"), "| rows:", out.get("row_count"), "| clarify:", out.get("asked_clarification"))
    time.sleep(SECONDS_BETWEEN_QUESTIONS)

# ---- 5. Save and show ----
import pandas as pd
pdf = pd.DataFrame(runs)
for col in ["status","conversation_id","response_text","sql","sql_description","result_columns","result_rows","row_count","asked_clarification","error"]:
    if col not in pdf.columns:
        pdf[col] = None
pdf = pdf.astype({"row_count": "float"})
df = spark.createDataFrame(pdf.astype(str))
df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("workspace.sales_answers.genie_runs")
display(spark.table("workspace.sales_answers.genie_runs"))
