# Experiment v2 results: who fills the definition gaps

Run Oct 28, 2026 in Databricks Free Edition. Data: synthetic `sales2` and `sales3` tables (600 customers, 2,110 orders). Each term has traps: billing date vs. order date, 257 refunded or cancelled orders, 39 internal test accounts, Subscription vs. Support plan, and a fiscal year that starts Feb 1.

The question in every setup: does Genie's answer match the definition the business owner would give?

## Headline

| Setup | Who filled the gaps | Correct | Median miss when wrong |
|---|---|---|---|
| C1: Agent with one-line definitions | Nobody; Genie guessed | 11 of 96 (12%) | 25% |
| C2: C1 plus Databricks' "ask the user if a term is ambiguous" rule | The person asking | 11 of 96 (12%) | 25% |
| C3: Improve with Genie, analyst answers its questions | Analyst (best guesses) | 17 of 96 (18%) | 13% |
| C4: Improve with Genie, owner answers its questions | Business owner | 67 of 96 (70%) | 1.7% |
| P1: Genie One with one-line Pages | Owner, one line | 0 of 8 | 7.7% to 110% |
| P2: Genie One with the owner's full definitions in Pages | Owner, complete | 1 of 8 | 6% to 110% |

There were 48 questions per agent, each asked twice through the Genie Conversation API (384 runs, 0 errors). P1 and P2 used 8 of the same questions in Genie One. Charts: `charts/fig_v2_accuracy_by_condition.png`, `charts/fig_v2_accuracy_by_term.png`.

## What it shows

1. **The answers follow whoever fills the gaps.** In C3, 72 of 96 answers matched the analyst's guesses exactly. Improve with Genie captured the analyst's guesses faithfully, and the guesses were wrong. With the owner answering the same questions (C4), accuracy rose from 18% to 70%, and the remaining misses were small (median 1.7%).
2. **"Ask the user" doesn't help when the user doesn't know the rule.** C2 asked a clarifying question on 8 of 96 runs. Told "just use our standard definition," it still guessed. Accuracy was identical to C1 (12%).
3. **Left alone, Genie picks the widest reading.** C1 and C2 mostly counted every order (refunds included), used order date, and kept test accounts. Examples: churned customers 342 vs. 152 (+125%); revenue in the last 12 months $23.6M vs. $19.1M (+23%).
4. **The analyst's guesses are plausible and still wrong.** Using order date with Subscription only: recurring revenue came out −31%, active customers −13%, churn +120%.
5. **Some errors survive even with the owner answering.** Churn was right 4 of 16 times (Genie's SQL returned 140 vs. 152). Revenue answers sometimes went back to order date (−0.8%). One "last fiscal quarter" answer used the current, unfinished quarter (−39%). These are the cases where confirming against real customers would catch what a written answer misses.
6. **Pages don't fix it on their own.** With full owner definitions in Pages, Genie One still got 7 of 8 wrong.
   - In 3 cases it reused an earlier chat ("I found the exact same question from earlier today") and never opened the corrected Page.
   - In all 4 revenue answers it read the Page and still kept internal test accounts.
   - Full definitions shrank the errors (last fiscal quarter −40% → +7%; recurring revenue +23% → +6%) but didn't eliminate them.
7. **Genie One treats agent chats as its own history.** The experiment's API questions to the test agents appear in the Genie One sidebar, and Genie One reuses them as past answers. A wrong answer from one agent becomes a precedent for the next question.
8. **Consistency.** C1–C3 gave the same right-or-wrong result on both runs 98% of the time; C4 did so 90% of the time. Genie is consistently wrong in the same way, so repeated asking doesn't surface the error.

## By term (share matching the owner, 16 answers each)

| Term | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| Active customer | 25% | 25% | 12% | 100% |
| Churned customer | 0% | 0% | 0% | 25% |
| Enterprise account | 6% | 6% | 50% | 100% |
| Revenue | 25% | 25% | 25% | 62% |
| Recurring revenue | 0% | 0% | 0% | 100% |
| Fiscal periods | 12% | 12% | 19% | 31% |

## Improve with Genie sessions (C3 and C4)

- Found 6 gaps, but missed the billing-date and Support-plan questions.
- Decided some gaps on its own (order date, Subscription only) without asking.
- Asked multiple-choice questions that auto-skip after 30 seconds.
- In C3 it marked the analyst's 90-day churn guess as confirmed, removing its own "provisional, flag for Sales Ops" note.
- In C4, after the owner answered 4 questions, it still chose order date and per-fiscal-year enterprise until the owner sent corrections.

## Caveats

- One person played both analyst and owner, working from policy sheets written before any run.
- Synthetic data; Free Edition; Pages is in Beta.
- Some question types (top region, shares) match under several readings, so C1's correct answers include coincidental matches.
- Genie One's chat history includes the experiment's own runs, which affected P1 and P2. This also reflects how a real workspace accumulates history.
- The first notebook crashed at 49/192 on a save bug, was fixed, and resumed. No answers were lost.

## Evidence (`screenshots/` folder)

01–03 C3 Improve with Genie: misses gaps, decides alone, marks the analyst's guess as confirmed · 04–06 C4: churn options don't match the owner, 30-second auto-skip, owner answers ignored on date and fiscal year · 07–11 Genie One with one-line Pages: picks an agent as authoritative, picks the "most common" definition (227, labeled "Sales Ops"), sees the correct churn definition and picks the other, recurring revenue $13.3M vs. $10.8M, last fiscal quarter −40% · 12–14 Genie One with full Pages: reuses a past chat over the Page (319 churned), reads the Revenue Page but counts test accounts while saying it follows the definition, "how much did we make" skips the Page entirely.

## Genie benchmarks (Databricks' own scoring)

Same agents, 12 of the 48 questions (two per term), each with ground-truth SQL from the owner's definitions, run with Genie's Benchmark feature in Chat mode on Oct 28, 2026.

| Agent | Benchmark accuracy | My scoring, same 12 questions |
|---|---|---|
| One-line definitions (Genie guessed) | 0 of 12 | 0 of 12 (both runs) |
| Improve with Genie, analyst answers | 1 of 12 | 0 and 1 of 12 |
| Improve with Genie, owner answers | 6 of 12 | 8 and 6 of 12 |

- Databricks' scoring matches mine within run-to-run variation.
- Genie's own failure analysis names the cause. For one-line definitions: "does not exclude internal customers, does not limit to completed orders, and uses a fiscal year window instead of the last 365 days" (screenshot 15).
- Of the owner agent's six misses:
  - Three were details nobody had settled: whether "last 12 months" includes invoices dated after today (my mock data has some), and 365 days vs. one calendar year back.
  - Two came from Genie's own rewrite of the owner's churn answer. "With no orders since" was read as any order, not completed orders (screenshot 16).
  - Both point to the same requirement: the owner should confirm the written definition against example customers, not just answer questions.

## Assumptions and what holds at scale

- **Role-play:** one person played analyst and owner from sheets written before any run. The analyst sheet is plausible but unvalidated. The 18% shows that Genie applies whatever answers it gets; it is not an estimate of how often real analysts guess wrong.
- **Role-free results:**
  - With nobody answering, Genie asked 0 clarifying questions in 96 answers, and 8 in 96 with the "ask if ambiguous" rule.
  - On 35 of 36 numeric questions, the plausible readings differ by more than 10% (a wrong reading misses by a median of 16%; churn by a median of 87%).
- **At scale:** any agent built from short definitions silently picks one reading, and every user of that agent inherits it.
