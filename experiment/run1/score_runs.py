"""Score Genie experiment runs against ground truth.
Usage: python3 score_runs.py genie_runs.csv
Writes scored_runs.csv and prints a summary.
"""
import sys, json, re
import pandas as pd

EXPECTED = {
    "A1": {"type": "num", "value": 261},
    "A2": {"type": "num", "value": 83},
    "A3": {"type": "groups", "value": {"APAC": 56, "EMEA": 83, "LATAM": 60, "North America": 62}},
    "A4": {"type": "num", "value": 62},
    "A5": {"type": "pct", "value": 46.5},
    "A6": {"type": "rows", "value": 60},
    "A7": {"type": "num", "value": 29},
    "C1": {"type": "num", "value": 152},
    "C2": {"type": "groups", "value": {"APAC": 49, "EMEA": 38, "LATAM": 24, "North America": 41}},
    "C3": {"type": "num", "value": 38},
    "C4": {"type": "num", "value": 152},
    "C5": {"type": "top", "value": "APAC"},
    "C6": {"type": "num", "value": 23},
    "E1": {"type": "num", "value": 113},
    "E2": {"type": "groups", "value": {"APAC": 26, "EMEA": 30, "LATAM": 28, "North America": 29}},
    "E3": {"type": "num", "value": 26},
    "E4": {"type": "top", "value": "EMEA"},
    "E5": {"type": "num", "value": 76},
    "E6": {"type": "num", "value": 34},
    "X1": {"type": "num", "value": 148},
}
REGIONS = ["APAC", "EMEA", "LATAM", "North America"]


def parse_rows(s):
    try:
        v = json.loads(s)
        return v if isinstance(v, list) else None
    except Exception:
        return None


def numbers_in(rows):
    out = []
    for r in rows or []:
        for c in r:
            try:
                out.append(float(c))
            except (TypeError, ValueError):
                pass
    return out


def check(qid, rows, text):
    exp = EXPECTED[qid]
    if rows is None:
        return None, "no result"
    t = exp["type"]
    nums = numbers_in(rows)
    if t == "num":
        ok = any(abs(n - exp["value"]) < 0.5 for n in nums) and len(rows) == 1
        return ok, f"got {nums[:4]}"
    if t == "pct":
        ok = any(abs(n - exp["value"]) <= 0.15 or abs(n * 100 - exp["value"]) <= 0.15 for n in nums)
        return ok, f"got {nums[:4]}"
    if t == "rows":
        return len(rows) == exp["value"], f"{len(rows)} rows"
    if t == "groups":
        got = {}
        for r in rows:
            reg = next((c for c in r if c in REGIONS), None)
            vals = [float(c) for c in r if c not in REGIONS and _isnum(c)]
            if reg and vals:
                got[reg] = vals[0]
        ok = all(abs(got.get(k, -1) - v) < 0.5 for k, v in exp["value"].items())
        return ok, f"got {got}"
    if t == "top":
        first = rows[0] if rows else []
        ok = exp["value"] in first or (exp["value"] in (text or "") and len(rows) <= 4 and _top_from_groups(rows) == exp["value"])
        if not ok and len(rows) > 1:
            ok = _top_from_groups(rows) == exp["value"] and exp["value"] in (text or "")
        return ok, f"first row {first}"
    return None, "unknown"


def _isnum(c):
    try:
        float(c); return True
    except (TypeError, ValueError):
        return False


def _top_from_groups(rows):
    best, bv = None, -1
    for r in rows:
        reg = next((c for c in r if c in REGIONS), None)
        vals = [float(c) for c in r if c not in REGIONS and _isnum(c)]
        if reg and vals and vals[0] > bv:
            best, bv = reg, vals[0]
    return best


def sql_signals(sql):
    s = (sql or "").lower()
    return {
        "uses_segments_view": "customer_segments" in s,
        "uses_invoice_date": "invoice_date" in s,
        "uses_order_date": "order_date" in s,
        "filters_completed": bool(re.search(r"status\s*(=|in)\s*\(?\s*'completed'", s)),
        "excludes_internal": "is_internal" in s,
        "window_days": sorted(set(re.findall(r"\b(30|60|90|91|180|365)\b", s))),
        "distinct_customers": "distinct" in s,
    }


def main(path):
    df = pd.read_csv(path)
    out = []
    for _, r in df.iterrows():
        rows = parse_rows(r.get("result_rows"))
        ok, detail = check(r["question_id"], rows, r.get("response_text"))
        sig = sql_signals(r.get("sql"))
        out.append({**r.to_dict(), "correct": ok, "detail": detail, **sig})
    s = pd.DataFrame(out)
    s.to_csv("scored_runs.csv", index=False)
    first = s[s["run"].astype(str) == "1"]
    print(first.groupby("agent")["correct"].agg(["sum", "count", "mean"]))
    rep = s[s["agent"] == "A"].pivot_table(index="question_id", columns="run", values="detail", aggfunc="first")
    print(rep.dropna())


if __name__ == "__main__":
    main(sys.argv[1])
