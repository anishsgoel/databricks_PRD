# Results: Experiments 1 and 2 (run Oct 26, 2026, Free Edition, Chat mode via Conversation API)

51 runs, all completed. Each scored by reading the SQL, not just the number. Per-run verdicts and notes: `final_scored_runs.csv`.

## Scores

| Agent | Correct | Accuracy | Notes |
| --- | --- | --- | --- |
| A: full text definitions | 19/20 | 95% | 1 definition error (C6). E3 and E6 gave the right number in text but a malformed table (26 rows of "1"). |
| B: confirmed SQL view | 18/20 | 90% | Both misses (A5, X1) counted the 39 internal test accounts as customers. |
| V: vague text | 0/6 | 0% | 6/6 silent guesses, 0 clarifying questions. |

Consistency: the 5 repeat runs in A matched the first run exactly (5/5).

## Hypotheses

| | Hypothesis | Result |
| --- | --- | --- |
| H1 | Text accuracy ≤90% | **Not supported.** 95% when definitions are written precisely. |
| H2 | Confirmed SQL ≥95% and clearly better | **Not supported as designed.** 90%. The segment flags were never wrong; the base population was. |
| H3 | Genie silently guesses on vague definitions in ≥ half of answers | **Strongly supported.** 6/6, no questions asked. |
| H4 | Owners catch errors better from examples than from SQL | Not yet run. |

## What the pre-set decision rules say

- "A ≥95% → reframe around E2 and E3." Triggered.
- "B not better than A → rethink the solution." Triggered, with a specific diagnosis: both B misses came from the same gap. The confirmed view defined *which customers are active/churned* but nobody confirmed *who counts as a customer at all*. Internal test accounts leaked into the denominator.

## The three findings worth putting in the PRD

1. **Precise definitions mostly work; nobody writes precise definitions.** The same three definitions written the way a busy owner writes them produced 6 wrong answers out of 6, with errors from −12% to +153%, and Genie never asked which date, which statuses or which window.
2. **The most dangerous wrong answer looks right.** Vague "active customers" returned 258 vs a true 261, built on the wrong date column, the wrong statuses and internal accounts included. No one reviewing the number would catch it.
3. **Even a precise text definition breaks when combined with another filter.** Agent A applied the churn definition correctly for "churned customers" (152) and "customers lost recently" (152), then got "large companies that churned" wrong (63 vs 23). The confirmed view got it right (23). Confirmation fixes composition; it does not fix scope it was never given (the population).

## Errors by type

| Code | Count | Where |
| --- | --- | --- |
| DATE | 5 | V A1, A2, C1, C3, E3 |
| STATUS | 6 | all V |
| INTERNAL | 7 | all V, B X1 |
| CHURN_LOGIC | 3 | A C6, V C1, V C3 |
| WINDOW | 2 | V E1, E3 |
| DENOM | 1 | B A5 |

## Hero screenshots to capture

- V A1 (258, looks right) next to the SQL showing `order_date` and no status filter.
- V C1 (342 vs 152): "churned" read as anyone who didn't buy in 90 days.
- A C6 (63) next to B C6 (23), same question.
- B A5 (43.5%): the confirmed flags were right, the population wasn't.

## Limits

Synthetic data, one dataset, 20 questions, one run per question (except 5 repeats), traps designed by the experimenter, Chat mode only.

---

# Experiment 2b: the same vague agent after "Improve with Genie" (run Oct 26, 2026)

**Setup.** On agent V, clicked Improve with Genie. It found four gaps (churn window, status, date column, internal accounts), asked about three, and decided the date column itself (order_date, unmarked). It never flagged "$50k a year." Answered as a busy analyst would without asking Sales Ops: "completed only, 90 days, exclude internal." It saved the rewrite, two filters and column descriptions, then offered to add a benchmark "with the expected answer computed with these rules." Predictions were written before the rerun (`PREDICTIONS_V2_improved.md`).

| Q | Improved agent | Predicted | Owner's truth | Off by |
| --- | --- | --- | --- | --- |
| Active customers | 227 | 227 | 261 | −13% |
| Active in EMEA | 68 | 68 | 83 | −18% |
| Churned customers | 319 | 319 | 152 | +110% |
| Churned in EMEA | 89 | 89 | 38 | +134% |
| Enterprise accounts | 125 | 112 or 125 | 113 | +11% |
| Enterprise in APAC | 30 | 25 or 30 | 26 | +15% |

**0/6 match the owner. 6/6 match the prediction.** Genie followed the improved instructions exactly; the instructions were wrong.

Other observations:
- Two answers added a question *after* answering. Churn: "a different window, such as 60 or 120 days?" (still no lookback, so no option fits the owner's definition). Enterprise in APAC: "a rolling 12-month period instead of calendar years?" (that is the owner's version, offered to whoever asked, not to the owner).
- Enterprise was read as "any calendar year" both times, a gap the improve step never raised.
- The suggested benchmark would grade answers against the analyst's guesses, so it would pass.

**Implication.** Precise definitions get followed (A: 95%; V2: 6/6 as predicted). Databricks' assistant finds most gaps. The failure is who answers them: an analyst's sensible guesses produced 13–134% errors that every check in the workflow would pass. The missing step is routing the gap questions to the definition's owner, in terms they can judge.
