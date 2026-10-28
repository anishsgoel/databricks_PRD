# Databricks notebook: rerun the 6 vague questions on agent V AFTER "Improve with Genie" (V2)
# --------------------------------------------------------------------------------
# New notebook (Python, serverless) -> paste this whole file into one cell -> run.
# Run it TODAY (dates are relative to current_date), takes about 2 minutes.
# Saves to workspace.sales_answers.genie_runs_v2 and prints answers next to predictions and truth.

import time, json, re
import pandas as pd
from databricks.sdk import WorkspaceClient

AGENT_TITLE = "V - vague text"   # the agent that Improve with Genie edited in place

QUESTIONS = [
    ("A1", "How many active customers do we have?",        "227",      261),
    ("A2", "How many active customers are in EMEA?",       "68",       83),
    ("C1", "How many churned customers do we have?",       "319",      152),
    ("C3", "How many customers in EMEA have churned?",     "89",       38),
    ("E1", "How many enterprise accounts do we have?",     "112 or 125", 113),
    ("E3", "How many enterprise accounts are in APAC?",    "25 or 30", 26),
]
SECONDS_BETWEEN_QUESTIONS = 13
MAX_WAIT_SECONDS = 240

w = WorkspaceClient()
api = w.api_client

spaces, token = [], None
while True:
    resp = api.do("GET", "/api/2.0/genie/spaces", query={"page_size": 100, **({"page_token": token} if token else {})})
    spaces += resp.get("spaces", [])
    token = resp.get("next_page_token")
    if not token:
        break
by_title = {s.get("title"): s.get("space_id") for s in spaces}
if AGENT_TITLE not in by_title:
    raise ValueError(f"Couldn't find agent titled '{AGENT_TITLE}'. Agents found: {list(by_title)}")
SPACE_ID = by_title[AGENT_TITLE]
print("Agent:", AGENT_TITLE, SPACE_ID)

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


def headline_number(rows, text):
    # single-value answer -> that value; one-row-per-customer answer -> row count; else first number in the text
    if isinstance(rows, list) and len(rows) == 1 and len(rows[0]) == 1:
        try:
            return float(rows[0][0])
        except (TypeError, ValueError):
            pass
    if isinstance(rows, list) and len(rows) > 1:
        return float(len(rows))
    m = re.search(r"\*\*([\d,\.]+)", text or "") or re.search(r"([\d,]+)", text or "")
    return float(m.group(1).replace(",", "")) if m else None

runs = []
for i, (qid, q, predicted, truth) in enumerate(QUESTIONS, start=1):
    print(f"[{i}/{len(QUESTIONS)}] {qid}: {q}")
    try:
        out = ask(SPACE_ID, q)
    except Exception as e:
        out = {"status": "ERROR", "error": str(e)}
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print("  rate limited, waiting 60s and retrying once")
            time.sleep(60)
            try:
                out = ask(SPACE_ID, q)
            except Exception as e2:
                out = {"status": "ERROR", "error": str(e2)}
    rows = json.loads(out["result_rows"]) if out.get("result_rows") else None
    got = headline_number(rows if isinstance(rows, list) else None, out.get("response_text"))
    runs.append({"agent": "V2", "question_id": qid, "question": q, "run": 1,
                 "answer": got, "predicted": predicted, "truth": truth, **out})
    print("  ->", out.get("status"), "| answer:", got, "| predicted:", predicted, "| truth:", truth)
    time.sleep(SECONDS_BETWEEN_QUESTIONS)

pdf = pd.DataFrame(runs)
for col in ["status","conversation_id","response_text","sql","sql_description","result_columns","result_rows","row_count","asked_clarification","error"]:
    if col not in pdf.columns:
        pdf[col] = None
spark.createDataFrame(pdf.astype(str)).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("workspace.sales_answers.genie_runs_v2")
display(spark.table("workspace.sales_answers.genie_runs_v2"))
