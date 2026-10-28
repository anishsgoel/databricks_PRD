# Experiment

Everything behind the numbers in the PRD. The main experiment ran in Databricks Free Edition on October 28, 2026. An earlier, smaller run from October 26 is in `run1/`.

## Results

| File | What it is |
|---|---|
| `experiment-v2-results.md` | Summary: accuracy by setup and by term, what Improve with Genie did, Databricks benchmark scores, caveats |
| `pages_runs.md` | Genie One answers with the definitions written into Pages, first as one-liners, then in full |
| `screenshots/` | 16 screenshots from the runs and the Benchmark tab, named by what each one shows |

## Data (exported from the Databricks workspace)

| File | Rows | What it is |
|---|---|---|
| `data/customers.csv` | 600 | Mock customer accounts, including 39 internal test accounts |
| `data/orders.csv` | 2,110 | Mock orders with order date, invoice (billing) date, status and product line |
| `data/answer_key.csv` | 704 | For each question, the answer under every reading (billing vs. order date, refunds in or out, test accounts in or out). `is_owner` marks Sales Ops' answer and `is_analyst` the analyst's. |
| `data/genie_answers_raw.csv` | 384 | Every Genie answer: question, setup, run, response text, SQL and result |
| `data/genie_answers_scored.csv` | 384 | Each answer scored against the answer key, with the reading it matched |

The Pages runs used a copy of the same tables (`workspace.sales3`) so Genie One wouldn't reuse the agents' chats. The rows are identical, so the copy isn't included.

## Code

| File | What it does |
|---|---|
| `notebooks/nb1_setup.py` | Builds the mock data, the answer key and the four Genie agents |
| `notebooks/nb2_run.py` | Asks 48 questions x 4 agents x 2 runs through the Genie Conversation API, saves each answer and scores it |
| `scripts/core.py` | Definitions, questions, answer key and scoring logic shared by the notebooks |
| `scripts/setup_sql.py` | SQL that creates the mock tables |
| `scripts/c12_small_fixed.py`, `scripts/c34_small_fixed.py` | Runner cells used for the final runs (setups C1 and C2, then C3 and C4) after fixing a save bug |
| `scripts/score_cell.py` | Re-scores all saved answers |
| `scripts/benchmarks.py`, `scripts/bench_cell.py` | The 12 benchmark questions with Sales Ops' SQL, and the cell that adds them to each agent's Benchmark tab |
| `scripts/localtest.py`, `scripts/scoretest.py` | Local checks of the answer key and scoring with PySpark |

In the results, C1 to C4 are the four setups: one-line definitions, one-liners plus an "ask the user" rule, Improve with Genie answered by the analyst, and Improve with Genie answered by Sales Ops.

## Run 1 (October 26)

The first run tested whether Genie follows definitions at all. With complete written definitions, it matched 19 of 20 answers. With vague ones, it guessed silently on all 6 questions. Files: setup and answer-key SQL, the run and scoring scripts, scored results (`final_scored_runs.csv`) and a summary (`RESULTS_E1_E2.md`).
