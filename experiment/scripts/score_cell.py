# Score all API runs (C1-C4) and print a compact summary. Self-contained: paste into any cell and run.
import json, pandas as pd
ANSWERS = "workspace.sales2_answers"; RAW = f"{ANSWERS}.runs_raw"
REGIONS = ["North America","EMEA","APAC","LATAM"]
TERM = lambda q: {"A":"active","C":"churn","E":"enterprise","R":"revenue","F":"fiscal"}[q[0]] if not q.startswith("RR") else "recurring"

def _nums(rows):
    out = []
    for r in rows or []:
        for v in (r if isinstance(r, list) else [r]):
            try: out.append(float(str(v).replace(",", "")))
            except Exception: pass
    return out
def _close(a, b, tol=0.005): return abs(a - b) <= max(tol * abs(b), 0.5 if abs(b) < 1000 else 1.0)
def matches(kind, ans, rows, text):
    if kind == "scalar": return any(_close(x, ans) for x in _nums(rows))
    if kind == "pct": return any(_close(x, ans, 0.01) or _close(x * 100, ans, 0.01) for x in _nums(rows))
    if kind == "top_region":
        first = json.dumps(rows[0]) if rows else ""
        return (ans in first) or (not rows and ans in (text or ""))
    if kind == "by_region":
        if not rows: return False
        got = {}
        for r in rows:
            r = r if isinstance(r, list) else [r]
            reg = next((x for x in r if x in REGIONS), None); n = _nums([r])
            if reg and n: got[reg] = n
        return all(reg in got and any(_close(x, v) for x in got[reg]) for reg, v in ans.items())
    return False

key = spark.table(f"{ANSWERS}.answer_key").toPandas()
key["is_owner"] = key.is_owner.astype(str) == "True"; key["is_analyst"] = key.is_analyst.astype(str) == "True"
raw = spark.table(RAW).toPandas()
raw = raw.sort_values("asked_at").drop_duplicates(["condition","qid","run"], keep="last")
out = []
for r in raw.to_dict("records"):
    try: rows = json.loads(r["result_rows"]) if r.get("result_rows") not in (None, "None", "") else None
    except Exception: rows = None
    k = key[key.qid == r["qid"]]; kind = k.kind.iloc[0]
    own = json.loads(k[k.is_owner].answer.iloc[0]); ana = json.loads(k[k.is_analyst].answer.iloc[0])
    ok = matches(kind, own, rows, r.get("response_text"))
    matched = [v for v, a in zip(k.variant, k.answer) if matches(kind, json.loads(a), rows, r.get("response_text"))]
    first = (_nums(rows) or [None])[0]
    pct = round(100.0 * (first - own) / own, 1) if (kind == "scalar" and not ok and first is not None and own) else None
    out.append(dict(c=r["condition"], q=r["qid"], run=r["run"], term=TERM(r["qid"]), ok=ok,
                    analyst=matches(kind, ana, rows, r.get("response_text")), asked=str(r.get("asked_first")) == "True",
                    status=r.get("status"), got=first, own=own if kind == "scalar" else None, pct=pct, v="; ".join(matched)[:80]))
s = pd.DataFrame(out)
spark.createDataFrame(s.astype(str)).write.mode("overwrite").option("overwriteSchema","true").saveAsTable(f"{ANSWERS}.runs_scored_v2")
print("ROWS", len(s), "by condition:", s.groupby("c").size().to_dict())
summ = s.groupby("c").agg(n=("q","size"), correct=("ok","sum"), analyst_match=("analyst","sum"), asked=("asked","sum"),
                          errors=("status", lambda x: (x != "COMPLETED").sum()))
summ["acc%"] = (100 * summ.correct / summ.n).round(1)
print(summ.to_string())
print(s.pivot_table(index="term", columns="c", values="ok", aggfunc="mean").round(2).to_string())
# consistency: did run 1 and run 2 agree on correctness?
p = s.pivot_table(index=["c","q"], columns="run", values="ok", aggfunc="first")
if p.shape[1] == 2: print("run1==run2 share by condition:", (p.iloc[:,0] == p.iloc[:,1]).groupby(level=0).mean().round(2).to_dict())
print("MEDIAN |pct off| on misses:", s[s.pct.notna()].assign(a=lambda d: d.pct.abs()).groupby("c").a.median().to_dict())
print("COMPACT")
for r in s.sort_values(["q","c","run"]).itertuples():
    print(f"{r.c}|{r.q}|{r.run}|{int(r.ok)}|{int(r.analyst)}|{int(r.asked)}|{r.got}|{r.pct}|{r.v}")
