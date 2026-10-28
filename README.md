# Ask the Owner

Prototype and experiment for my Databricks APM mini-PRD, *Genie Answers That Match What the Business Means*.

A Genie agent's instructions often hold one-line business definitions, like "an active customer bought in the last 90 days." They leave out details: does a refunded order count, and does "bought" mean the order date or the billing date? Genie fills those gaps itself, and the analyst who built the agent usually can't answer them either. **Ask the Owner** is a proposed option in Improve with Genie that sends each gap to the person who owns the definition, such as the head of Sales Ops. She settles it in Genie One by judging example customers, and every answer after that follows her confirmed definition.

- **Clickable prototype:** https://anishsgoel.github.io/databricks_PRD/ (about 3 minutes; click the highlighted button or press Next)
- **Narrated walkthrough:** https://youtu.be/nuKayaOnDps (3.5 minutes)

## What's in this repo

| Path | What it is |
|---|---|
| `index.html` | The prototype: one HTML file, no build step. Served by GitHub Pages. |
| `experiment/` | Data, Genie answers, scripts, screenshots and results from the Databricks Free Edition experiment behind the PRD |

## The experiment

I built a mock sales dataset in Databricks Free Edition: 600 customers and 2,110 orders, with refunded orders, invoices billed weeks after the order, and internal test accounts. Acting as Sales Ops, I wrote complete definitions for six terms and worked out the right answer to 48 questions. Four Genie agents then started from the same one-line definitions and differed only in who filled the gaps. Each one answered all 48 questions twice, for 384 answers.

| Who filled the gaps | Answers matching Sales Ops' definitions |
|---|---|
| Nobody (Genie guessed) | 12% |
| The person asking, with an "ask if a term is unclear" rule | 12% |
| The analyst, through Improve with Genie | 18% |
| Sales Ops, through Improve with Genie | 70% |

Databricks' own benchmark tool scored a 12-question subset the same way: 0, 1 and 6 of 12. With Sales Ops' full definitions written into Pages, Genie One still got 7 of 8 questions wrong.

Full results, the per-term breakdown and caveats are in [`experiment/experiment-v2-results.md`](experiment/experiment-v2-results.md).

The mock data, the answer key, all 384 Genie answers with their SQL, the scored results, the scripts and screenshots are in [`experiment/`](experiment/). To rerun it, import the two notebooks in `experiment/notebooks/` into a Free Edition workspace and run `nb1_setup.py`, then `nb2_run.py`. The second one takes about 100 minutes and skips answers it has already saved.

## Notes

- All data is made up. Dates count back from the day you run the setup notebook.
- One person played both the analyst and the owner, answering from sheets written before any run.
- This is an independent concept for a take-home assignment and isn't affiliated with or endorsed by Databricks.
